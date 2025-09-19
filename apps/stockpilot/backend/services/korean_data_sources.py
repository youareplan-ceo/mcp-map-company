#!/usr/bin/env python3
"""
StockPilot KR 데이터 소스 확장 시스템
전자공시 세부 정보 파싱, 증권사 리포트 자동 수집, 캘린더 데이터 이중화 및 품질 검증
"""

import asyncio
import aiohttp
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import xml.etree.ElementTree as ET
import sqlite3
from pathlib import Path
import hashlib
import aioredis
from bs4 import BeautifulSoup
import feedparser
from urllib.parse import urljoin, urlparse
import time

# 로깅 설정
logger = logging.getLogger(__name__)

class DataSourceType(Enum):
    """데이터 소스 타입"""
    DART_DISCLOSURE = "dart_disclosure"
    SECURITIES_REPORT = "securities_report"
    CALENDAR_DATA = "calendar_data"
    PRICE_DATA = "price_data"
    NEWS_DATA = "news_data"

class DataQuality(Enum):
    """데이터 품질 등급"""
    EXCELLENT = "excellent"  # 90점 이상
    GOOD = "good"           # 70-89점
    FAIR = "fair"           # 50-69점
    POOR = "poor"           # 50점 미만

@dataclass
class DataSource:
    """데이터 소스 정보"""
    source_id: str
    source_type: DataSourceType
    name: str
    url: str
    update_frequency_hours: int
    priority: int = 1  # 1(높음) ~ 5(낮음)
    enabled: bool = True
    last_updated: Optional[datetime] = None
    quality_score: float = 0.0
    error_count: int = 0

@dataclass
class DataItem:
    """데이터 아이템"""
    item_id: str
    source_id: str
    title: str
    content: str
    published_at: datetime
    category: str
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    quality_score: float = 0.0
    processed_at: datetime = field(default_factory=datetime.now)

@dataclass
class QualityReport:
    """데이터 품질 리포트"""
    source_id: str
    timestamp: datetime
    total_items: int
    valid_items: int
    duplicate_items: int
    missing_fields: int
    quality_score: float
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

class KoreanDataManager:
    """한국 데이터 소스 관리자"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client = None
        self.data_sources: Dict[str, DataSource] = {}
        self.db_path = Path("data/korean_data.db")
        self.cache_ttl = {
            DataSourceType.DART_DISCLOSURE: 3600,      # 1시간
            DataSourceType.SECURITIES_REPORT: 21600,   # 6시간
            DataSourceType.CALENDAR_DATA: 1800,        # 30분
            DataSourceType.PRICE_DATA: 300,            # 5분
            DataSourceType.NEWS_DATA: 1800             # 30분
        }
        
        # 데이터베이스 초기화
        self._init_database()
        
        # 기본 데이터 소스 등록
        self._setup_default_data_sources()

    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        self.redis_client = await aioredis.from_url(self.redis_url, decode_responses=True)
        logger.info("한국 데이터 매니저 초기화 완료")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self.redis_client:
            await self.redis_client.close()
        logger.info("한국 데이터 매니저 종료")

    def _init_database(self):
        """SQLite 데이터베이스 초기화"""
        try:
            self.db_path.parent.mkdir(exist_ok=True)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 데이터 소스 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS data_sources (
                    source_id TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    update_frequency_hours INTEGER NOT NULL,
                    priority INTEGER DEFAULT 1,
                    enabled BOOLEAN DEFAULT TRUE,
                    last_updated DATETIME,
                    quality_score REAL DEFAULT 0.0,
                    error_count INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 데이터 아이템 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS data_items (
                    item_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT,
                    published_at DATETIME NOT NULL,
                    category TEXT,
                    tags TEXT,
                    metadata TEXT,
                    quality_score REAL DEFAULT 0.0,
                    processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_id) REFERENCES data_sources(source_id)
                )
            """)
            
            # 품질 리포트 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quality_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    total_items INTEGER NOT NULL,
                    valid_items INTEGER NOT NULL,
                    duplicate_items INTEGER DEFAULT 0,
                    missing_fields INTEGER DEFAULT 0,
                    quality_score REAL NOT NULL,
                    issues TEXT,
                    recommendations TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 인덱스 생성
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_data_items_source ON data_items(source_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_data_items_published ON data_items(published_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_quality_reports_source ON quality_reports(source_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_quality_reports_timestamp ON quality_reports(timestamp)")
            
            conn.commit()
            conn.close()
            logger.info("데이터베이스 초기화 완료")
            
        except Exception as e:
            logger.error(f"데이터베이스 초기화 오류: {e}")

    def _setup_default_data_sources(self):
        """기본 데이터 소스 설정"""
        default_sources = [
            DataSource(
                source_id="dart_main",
                source_type=DataSourceType.DART_DISCLOSURE,
                name="DART 전자공시시스템 - 주요공시",
                url="https://dart.fss.or.kr",
                update_frequency_hours=1,
                priority=1
            ),
            DataSource(
                source_id="krx_market_data",
                source_type=DataSourceType.PRICE_DATA,
                name="한국거래소 시장정보",
                url="http://data.krx.co.kr",
                update_frequency_hours=1,
                priority=1
            ),
            DataSource(
                source_id="kap_calendar",
                source_type=DataSourceType.CALENDAR_DATA,
                name="한국거래소 기업일정",
                url="http://kind.krx.co.kr",
                update_frequency_hours=6,
                priority=2
            ),
            DataSource(
                source_id="yonhap_finance",
                source_type=DataSourceType.NEWS_DATA,
                name="연합뉴스 경제",
                url="https://www.yonhapnews.co.kr/economy",
                update_frequency_hours=2,
                priority=3
            ),
            DataSource(
                source_id="mirae_research",
                source_type=DataSourceType.SECURITIES_REPORT,
                name="미래에셋증권 리서치",
                url="https://securities.miraeasset.com",
                update_frequency_hours=12,
                priority=2
            ),
            DataSource(
                source_id="samsung_research",
                source_type=DataSourceType.SECURITIES_REPORT,
                name="삼성증권 리서치센터",
                url="https://www.samsungpop.com",
                update_frequency_hours=12,
                priority=2
            )
        ]
        
        for source in default_sources:
            self.data_sources[source.source_id] = source
        
        logger.info(f"{len(default_sources)}개 기본 데이터 소스 등록 완료")

    async def fetch_dart_disclosure_details(self, corp_code: str, report_nm: str) -> Dict[str, Any]:
        """DART 전자공시 세부 정보 파싱"""
        try:
            # DART API를 통한 세부 정보 조회
            api_key = "xxxxxxxx"  # 실제 DART API 키로 교체 필요
            base_url = "https://opendart.fss.or.kr/api"
            
            async with aiohttp.ClientSession() as session:
                # 공시검색 API 호출
                params = {
                    'crtfc_key': api_key,
                    'corp_code': corp_code,
                    'report_nm': report_nm,
                    'pblntf_ty': 'A',  # 정기공시
                    'page_no': '1',
                    'page_count': '10'
                }
                
                async with session.get(f"{base_url}/list.json", params=params) as response:
                    if response.status != 200:
                        logger.error(f"DART API 호출 실패: {response.status}")
                        return {}
                    
                    data = await response.json()
                    
                    if data.get('status') != '000':
                        logger.error(f"DART API 오류: {data.get('message', 'Unknown error')}")
                        return {}
                    
                    disclosure_items = []
                    
                    for item in data.get('list', []):
                        # 상세 공시 정보 파싱
                        detail = {
                            'rcept_no': item.get('rcept_no'),
                            'corp_cls': item.get('corp_cls'),
                            'corp_name': item.get('corp_name'),
                            'corp_code': item.get('corp_code'),
                            'stock_code': item.get('stock_code'),
                            'report_nm': item.get('report_nm'),
                            'rcept_dt': item.get('rcept_dt'),
                            'flr_nm': item.get('flr_nm'),
                            'rm': item.get('rm')
                        }
                        
                        # 추가 세부 정보 수집
                        if item.get('rcept_no'):
                            detail_info = await self._fetch_disclosure_document(
                                session, api_key, item.get('rcept_no')
                            )
                            detail.update(detail_info)
                        
                        disclosure_items.append(detail)
                        
                        # 품질 점수 계산
                        quality_score = self._calculate_disclosure_quality(detail)
                        detail['quality_score'] = quality_score
                    
                    return {
                        'items': disclosure_items,
                        'total_count': len(disclosure_items),
                        'timestamp': datetime.now().isoformat()
                    }
                    
        except Exception as e:
            logger.error(f"DART 전자공시 파싱 오류: {e}")
            return {}

    async def _fetch_disclosure_document(self, session: aiohttp.ClientSession, 
                                       api_key: str, rcept_no: str) -> Dict[str, Any]:
        """공시문서 세부 내용 조회"""
        try:
            params = {
                'crtfc_key': api_key,
                'rcept_no': rcept_no
            }
            
            async with session.get(
                "https://opendart.fss.or.kr/api/document.json", 
                params=params
            ) as response:
                if response.status != 200:
                    return {}
                
                data = await response.json()
                
                if data.get('status') != '000':
                    return {}
                
                # HTML 문서 파싱
                html_content = data.get('html_content', '')
                if html_content:
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # 주요 섹션 추출
                    sections = {
                        'summary': self._extract_summary(soup),
                        'financial_highlights': self._extract_financial_highlights(soup),
                        'business_summary': self._extract_business_summary(soup),
                        'risk_factors': self._extract_risk_factors(soup)
                    }
                    
                    return sections
                
                return {}
                
        except Exception as e:
            logger.error(f"공시문서 조회 오류: {e}")
            return {}

    def _extract_summary(self, soup: BeautifulSoup) -> str:
        """공시 요약 정보 추출"""
        try:
            # 요약 섹션 찾기
            summary_tags = soup.find_all(['div', 'p'], 
                                       string=re.compile(r'요약|개요|Summary', re.IGNORECASE))
            
            for tag in summary_tags:
                parent = tag.find_parent()
                if parent:
                    # 다음 형제 요소들에서 텍스트 수집
                    summary_text = ""
                    for sibling in parent.find_next_siblings():
                        if sibling.name in ['p', 'div']:
                            summary_text += sibling.get_text(strip=True) + " "
                        if len(summary_text) > 500:
                            break
                    
                    if summary_text.strip():
                        return summary_text.strip()
            
            # 대체: 첫 번째 문단
            first_p = soup.find('p')
            if first_p:
                return first_p.get_text(strip=True)
            
            return ""
            
        except Exception as e:
            logger.error(f"요약 추출 오류: {e}")
            return ""

    def _extract_financial_highlights(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """재무 하이라이트 추출"""
        try:
            highlights = {}
            
            # 테이블에서 재무 데이터 찾기
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        
                        # 숫자가 포함된 재무 지표들
                        if any(keyword in key for keyword in ['매출', '순이익', '자산', '부채', '자본']):
                            # 숫자 추출 및 정규화
                            numbers = re.findall(r'[\d,]+', value)
                            if numbers:
                                highlights[key] = numbers[0].replace(',', '')
            
            return highlights
            
        except Exception as e:
            logger.error(f"재무 하이라이트 추출 오류: {e}")
            return {}

    def _extract_business_summary(self, soup: BeautifulSoup) -> str:
        """사업 개요 추출"""
        try:
            # 사업 관련 섹션 찾기
            business_keywords = ['사업의 내용', '사업 개요', '주요 사업', 'Business']
            
            for keyword in business_keywords:
                tags = soup.find_all(string=re.compile(keyword, re.IGNORECASE))
                for tag in tags:
                    parent = tag.find_parent()
                    if parent:
                        next_elements = parent.find_next_siblings()[:3]  # 다음 3개 요소
                        business_text = ""
                        
                        for element in next_elements:
                            if element.name in ['p', 'div']:
                                business_text += element.get_text(strip=True) + " "
                        
                        if len(business_text.strip()) > 50:
                            return business_text.strip()[:1000]  # 최대 1000자
            
            return ""
            
        except Exception as e:
            logger.error(f"사업 개요 추출 오류: {e}")
            return ""

    def _extract_risk_factors(self, soup: BeautifulSoup) -> List[str]:
        """위험 요인 추출"""
        try:
            risk_factors = []
            
            # 위험 요인 섹션 찾기
            risk_keywords = ['위험요인', '위험 요인', '리스크', 'Risk']
            
            for keyword in risk_keywords:
                tags = soup.find_all(string=re.compile(keyword, re.IGNORECASE))
                for tag in tags:
                    parent = tag.find_parent()
                    if parent:
                        # 리스트 형태로 위험 요인들 수집
                        lists = parent.find_next_siblings(['ul', 'ol'])
                        for list_elem in lists:
                            items = list_elem.find_all('li')
                            for item in items:
                                risk_text = item.get_text(strip=True)
                                if len(risk_text) > 20:  # 의미있는 길이의 텍스트만
                                    risk_factors.append(risk_text)
                            
                            if len(risk_factors) >= 5:  # 최대 5개
                                break
                        
                        if risk_factors:
                            break
            
            return risk_factors
            
        except Exception as e:
            logger.error(f"위험 요인 추출 오류: {e}")
            return []

    def _calculate_disclosure_quality(self, detail: Dict[str, Any]) -> float:
        """공시 품질 점수 계산"""
        score = 0.0
        max_score = 100.0
        
        # 필수 필드 존재 여부 (40점)
        required_fields = ['corp_name', 'report_nm', 'rcept_dt', 'rcept_no']
        present_fields = sum(1 for field in required_fields if detail.get(field))
        score += (present_fields / len(required_fields)) * 40
        
        # 세부 정보 충실도 (30점)
        detail_fields = ['summary', 'financial_highlights', 'business_summary']
        detail_score = 0
        for field in detail_fields:
            if field in detail and detail[field]:
                if isinstance(detail[field], str) and len(detail[field]) > 50:
                    detail_score += 10
                elif isinstance(detail[field], dict) and len(detail[field]) > 0:
                    detail_score += 10
        score += detail_score
        
        # 날짜 유효성 (15점)
        rcept_dt = detail.get('rcept_dt')
        if rcept_dt:
            try:
                dt = datetime.strptime(rcept_dt, '%Y%m%d')
                days_ago = (datetime.now() - dt).days
                if days_ago <= 30:  # 최근 30일 이내
                    score += 15
                elif days_ago <= 90:  # 90일 이내
                    score += 10
                else:
                    score += 5
            except:
                score += 0
        
        # 기업 정보 완성도 (15점)
        if detail.get('corp_code') and detail.get('stock_code'):
            score += 10
        if detail.get('flr_nm'):  # 공시대상회사
            score += 5
        
        return min(score, max_score)

    async def collect_securities_reports(self, source_id: str) -> List[DataItem]:
        """증권사 리포트 자동 수집"""
        try:
            source = self.data_sources.get(source_id)
            if not source or source.source_type != DataSourceType.SECURITIES_REPORT:
                logger.error(f"유효하지 않은 증권사 리포트 소스: {source_id}")
                return []
            
            reports = []
            
            if source_id == "mirae_research":
                reports = await self._collect_mirae_reports()
            elif source_id == "samsung_research":
                reports = await self._collect_samsung_reports()
            else:
                logger.warning(f"지원되지 않는 증권사 소스: {source_id}")
                return []
            
            # 데이터베이스에 저장
            await self._save_data_items(reports)
            
            # 캐시 업데이트
            await self._update_cache(source_id, reports)
            
            return reports
            
        except Exception as e:
            logger.error(f"증권사 리포트 수집 오류 ({source_id}): {e}")
            return []

    async def _collect_mirae_reports(self) -> List[DataItem]:
        """미래에셋증권 리포트 수집"""
        try:
            reports = []
            base_url = "https://securities.miraeasset.com"
            
            async with aiohttp.ClientSession() as session:
                # RSS 피드나 API 엔드포인트 호출
                # 실제 구현에서는 미래에셋 API 정보가 필요
                
                # 임시 데이터 (실제로는 API 응답 파싱)
                sample_reports = [
                    {
                        'title': '2024년 4분기 시장 전망',
                        'content': '4분기 주식시장 전망 및 추천 종목',
                        'author': '미래에셋증권 리서치센터',
                        'published_date': datetime.now().strftime('%Y-%m-%d'),
                        'category': '시장전망',
                        'tags': ['시장전망', '4분기', '추천종목']
                    }
                ]
                
                for report_data in sample_reports:
                    item = DataItem(
                        item_id=f"mirae_{hashlib.md5(report_data['title'].encode()).hexdigest()[:10]}",
                        source_id="mirae_research",
                        title=report_data['title'],
                        content=report_data['content'],
                        published_at=datetime.strptime(report_data['published_date'], '%Y-%m-%d'),
                        category=report_data['category'],
                        tags=report_data['tags'],
                        metadata={
                            'author': report_data['author'],
                            'source_url': base_url
                        }
                    )
                    
                    # 품질 점수 계산
                    item.quality_score = self._calculate_report_quality(item)
                    reports.append(item)
            
            return reports
            
        except Exception as e:
            logger.error(f"미래에셋 리포트 수집 오류: {e}")
            return []

    async def _collect_samsung_reports(self) -> List[DataItem]:
        """삼성증권 리포트 수집"""
        try:
            reports = []
            base_url = "https://www.samsungpop.com"
            
            async with aiohttp.ClientSession() as session:
                # 삼성증권 리서치 페이지 크롤링
                # 실제 구현에서는 삼성증권의 API나 RSS 피드 활용
                
                sample_reports = [
                    {
                        'title': 'K-반도체 업황 분석',
                        'content': '한국 반도체 산업 현황 및 향후 전망',
                        'author': '삼성증권 리서치센터',
                        'published_date': datetime.now().strftime('%Y-%m-%d'),
                        'category': '업종분석',
                        'tags': ['반도체', '업종분석', 'K-반도체']
                    }
                ]
                
                for report_data in sample_reports:
                    item = DataItem(
                        item_id=f"samsung_{hashlib.md5(report_data['title'].encode()).hexdigest()[:10]}",
                        source_id="samsung_research",
                        title=report_data['title'],
                        content=report_data['content'],
                        published_at=datetime.strptime(report_data['published_date'], '%Y-%m-%d'),
                        category=report_data['category'],
                        tags=report_data['tags'],
                        metadata={
                            'author': report_data['author'],
                            'source_url': base_url
                        }
                    )
                    
                    item.quality_score = self._calculate_report_quality(item)
                    reports.append(item)
            
            return reports
            
        except Exception as e:
            logger.error(f"삼성증권 리포트 수집 오류: {e}")
            return []

    def _calculate_report_quality(self, item: DataItem) -> float:
        """리포트 품질 점수 계산"""
        score = 0.0
        
        # 제목 품질 (20점)
        if item.title and len(item.title.strip()) >= 10:
            score += 20
        
        # 내용 품질 (40점)
        if item.content:
            content_len = len(item.content.strip())
            if content_len >= 500:
                score += 40
            elif content_len >= 200:
                score += 30
            elif content_len >= 100:
                score += 20
            else:
                score += 10
        
        # 메타데이터 완성도 (20점)
        if item.metadata.get('author'):
            score += 10
        if item.metadata.get('source_url'):
            score += 10
        
        # 태그 및 카테고리 (10점)
        if item.tags and len(item.tags) > 0:
            score += 5
        if item.category:
            score += 5
        
        # 발행일 유효성 (10점)
        if item.published_at:
            days_ago = (datetime.now() - item.published_at).days
            if days_ago <= 7:
                score += 10
            elif days_ago <= 30:
                score += 7
            else:
                score += 3
        
        return min(score, 100.0)

    async def setup_calendar_redundancy(self) -> bool:
        """캘린더 데이터 이중화 설정"""
        try:
            # 기본 캘린더 소스들
            primary_sources = [
                {
                    'source_id': 'kap_calendar_primary',
                    'name': '한국거래소 기업일정 (주)',
                    'url': 'http://kind.krx.co.kr/corpgeneral/corplist.do',
                    'priority': 1
                },
                {
                    'source_id': 'dart_calendar_backup',
                    'name': 'DART 공시일정 (백업)',
                    'url': 'https://dart.fss.or.kr/api/schedule.json',
                    'priority': 2
                },
                {
                    'source_id': 'fnguide_calendar_backup',
                    'name': 'FnGuide 기업일정 (백업)',
                    'url': 'https://comp.fnguide.com/SVO2/ASP/SVD_Calendar.asp',
                    'priority': 3
                }
            ]
            
            # 이중화 소스 등록
            for source_config in primary_sources:
                source = DataSource(
                    source_id=source_config['source_id'],
                    source_type=DataSourceType.CALENDAR_DATA,
                    name=source_config['name'],
                    url=source_config['url'],
                    update_frequency_hours=6,  # 6시간마다 업데이트
                    priority=source_config['priority']
                )
                
                self.data_sources[source.source_id] = source
                
                # 데이터베이스에 저장
                await self._save_data_source(source)
            
            # Redis에 이중화 설정 저장
            redundancy_config = {
                'primary_source': 'kap_calendar_primary',
                'backup_sources': ['dart_calendar_backup', 'fnguide_calendar_backup'],
                'failover_threshold_minutes': 30,  # 30분 지연 시 백업 소스 사용
                'data_validation_enabled': True,
                'cross_validation_required': True
            }
            
            await self.redis_client.hset(
                "calendar_redundancy_config",
                mapping={k: json.dumps(v) if isinstance(v, (list, dict, bool)) else str(v) 
                        for k, v in redundancy_config.items()}
            )
            
            logger.info("캘린더 데이터 이중화 설정 완료")
            return True
            
        except Exception as e:
            logger.error(f"캘린더 이중화 설정 오류: {e}")
            return False

    async def configure_cache_ttl(self) -> bool:
        """캐시 TTL 설정"""
        try:
            # 데이터 소스별 캐시 TTL 구성
            ttl_configs = {}
            
            for source_type, ttl_seconds in self.cache_ttl.items():
                # 기본 TTL
                base_key = f"cache_ttl:{source_type.value}"
                ttl_configs[base_key] = ttl_seconds
                
                # 시간대별 동적 TTL
                current_hour = datetime.now().hour
                
                if source_type == DataSourceType.PRICE_DATA:
                    # 장중(9-15시): 짧은 TTL, 장후: 긴 TTL
                    if 9 <= current_hour <= 15:
                        ttl_configs[f"{base_key}:trading"] = 300  # 5분
                    else:
                        ttl_configs[f"{base_key}:after_hours"] = 3600  # 1시간
                
                elif source_type == DataSourceType.NEWS_DATA:
                    # 뉴스 시간대별 TTL 조정
                    if 6 <= current_hour <= 22:  # 주요 뉴스 시간대
                        ttl_configs[f"{base_key}:active"] = 900  # 15분
                    else:
                        ttl_configs[f"{base_key}:quiet"] = 3600  # 1시간
            
            # Redis에 TTL 설정 저장
            pipe = self.redis_client.pipeline()
            for key, ttl in ttl_configs.items():
                pipe.hset("cache_ttl_config", key, ttl)
            await pipe.execute()
            
            logger.info(f"{len(ttl_configs)}개 캐시 TTL 설정 완료")
            return True
            
        except Exception as e:
            logger.error(f"캐시 TTL 설정 오류: {e}")
            return False

    async def run_quality_validation(self, source_id: Optional[str] = None) -> List[QualityReport]:
        """데이터 품질 검증 실행"""
        try:
            reports = []
            
            # 검증 대상 소스 결정
            sources_to_validate = [source_id] if source_id else list(self.data_sources.keys())
            
            for src_id in sources_to_validate:
                if src_id not in self.data_sources:
                    continue
                
                source = self.data_sources[src_id]
                
                # 최근 데이터 조회
                recent_items = await self._get_recent_data_items(src_id, hours=24)
                
                if not recent_items:
                    logger.warning(f"소스 {src_id}에 최근 데이터가 없음")
                    continue
                
                # 품질 검증 실행
                report = await self._validate_data_quality(source, recent_items)
                reports.append(report)
                
                # 리포트 저장
                await self._save_quality_report(report)
                
                # 품질 점수 업데이트
                source.quality_score = report.quality_score
                await self._update_source_quality(src_id, report.quality_score)
            
            logger.info(f"{len(reports)}개 소스 품질 검증 완료")
            return reports
            
        except Exception as e:
            logger.error(f"품질 검증 오류: {e}")
            return []

    async def _validate_data_quality(self, source: DataSource, items: List[DataItem]) -> QualityReport:
        """개별 소스 데이터 품질 검증"""
        try:
            total_items = len(items)
            valid_items = 0
            duplicate_items = 0
            missing_fields = 0
            issues = []
            recommendations = []
            
            # 중복 검사용 해시 세트
            content_hashes = set()
            
            for item in items:
                item_valid = True
                
                # 필수 필드 검사
                required_fields = ['title', 'content', 'published_at']
                for field in required_fields:
                    if not getattr(item, field, None):
                        missing_fields += 1
                        item_valid = False
                        issues.append(f"아이템 {item.item_id}: {field} 필드 누락")
                
                # 내용 품질 검사
                if item.content:
                    if len(item.content.strip()) < 50:
                        item_valid = False
                        issues.append(f"아이템 {item.item_id}: 내용이 너무 짧음")
                    
                    # 중복 검사
                    content_hash = hashlib.md5(item.content.encode()).hexdigest()
                    if content_hash in content_hashes:
                        duplicate_items += 1
                        issues.append(f"아이템 {item.item_id}: 중복 내용 감지")
                    else:
                        content_hashes.add(content_hash)
                
                # 날짜 유효성 검사
                if item.published_at:
                    if item.published_at > datetime.now():
                        item_valid = False
                        issues.append(f"아이템 {item.item_id}: 미래 날짜")
                    elif (datetime.now() - item.published_at).days > 365:
                        issues.append(f"아이템 {item.item_id}: 오래된 데이터")
                
                if item_valid:
                    valid_items += 1
            
            # 품질 점수 계산
            completeness_score = (valid_items / total_items) * 50 if total_items > 0 else 0
            duplication_penalty = min((duplicate_items / total_items) * 20, 20) if total_items > 0 else 0
            missing_fields_penalty = min((missing_fields / (total_items * 3)) * 30, 30) if total_items > 0 else 0
            
            quality_score = max(completeness_score - duplication_penalty - missing_fields_penalty, 0)
            
            # 권장사항 생성
            if duplicate_items > 0:
                recommendations.append("중복 데이터 제거 로직 강화 필요")
            
            if missing_fields > total_items * 0.1:  # 10% 이상 필드 누락
                recommendations.append("데이터 수집 프로세스 점검 필요")
            
            if quality_score < 70:
                recommendations.append("데이터 소스 검토 및 개선 필요")
            
            return QualityReport(
                source_id=source.source_id,
                timestamp=datetime.now(),
                total_items=total_items,
                valid_items=valid_items,
                duplicate_items=duplicate_items,
                missing_fields=missing_fields,
                quality_score=quality_score,
                issues=issues,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"품질 검증 실행 오류: {e}")
            return QualityReport(
                source_id=source.source_id,
                timestamp=datetime.now(),
                total_items=0,
                valid_items=0,
                duplicate_items=0,
                missing_fields=0,
                quality_score=0.0,
                issues=[f"품질 검증 실행 오류: {str(e)}"],
                recommendations=["시스템 점검 필요"]
            )

    async def _get_recent_data_items(self, source_id: str, hours: int = 24) -> List[DataItem]:
        """최근 데이터 아이템 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since_time = datetime.now() - timedelta(hours=hours)
            
            cursor.execute("""
                SELECT item_id, source_id, title, content, published_at, category, tags, metadata, quality_score, processed_at
                FROM data_items 
                WHERE source_id = ? AND processed_at >= ?
                ORDER BY processed_at DESC
            """, (source_id, since_time))
            
            items = []
            for row in cursor.fetchall():
                item = DataItem(
                    item_id=row[0],
                    source_id=row[1],
                    title=row[2],
                    content=row[3],
                    published_at=datetime.fromisoformat(row[4]) if row[4] else datetime.now(),
                    category=row[5],
                    tags=json.loads(row[6]) if row[6] else [],
                    metadata=json.loads(row[7]) if row[7] else {},
                    quality_score=row[8],
                    processed_at=datetime.fromisoformat(row[9]) if row[9] else datetime.now()
                )
                items.append(item)
            
            conn.close()
            return items
            
        except Exception as e:
            logger.error(f"최근 데이터 조회 오류: {e}")
            return []

    async def _save_data_items(self, items: List[DataItem]):
        """데이터 아이템들을 데이터베이스에 저장"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for item in items:
                cursor.execute("""
                    INSERT OR REPLACE INTO data_items
                    (item_id, source_id, title, content, published_at, category, tags, metadata, quality_score, processed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item.item_id,
                    item.source_id,
                    item.title,
                    item.content,
                    item.published_at.isoformat(),
                    item.category,
                    json.dumps(item.tags, ensure_ascii=False),
                    json.dumps(item.metadata, ensure_ascii=False),
                    item.quality_score,
                    item.processed_at.isoformat()
                ))
            
            conn.commit()
            conn.close()
            logger.info(f"{len(items)}개 데이터 아이템 저장 완료")
            
        except Exception as e:
            logger.error(f"데이터 아이템 저장 오류: {e}")

    async def _save_data_source(self, source: DataSource):
        """데이터 소스를 데이터베이스에 저장"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO data_sources
                (source_id, source_type, name, url, update_frequency_hours, priority, enabled, last_updated, quality_score, error_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                source.source_id,
                source.source_type.value,
                source.name,
                source.url,
                source.update_frequency_hours,
                source.priority,
                source.enabled,
                source.last_updated.isoformat() if source.last_updated else None,
                source.quality_score,
                source.error_count
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"데이터 소스 저장 오류: {e}")

    async def _save_quality_report(self, report: QualityReport):
        """품질 리포트를 데이터베이스에 저장"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO quality_reports
                (source_id, timestamp, total_items, valid_items, duplicate_items, missing_fields, quality_score, issues, recommendations)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report.source_id,
                report.timestamp.isoformat(),
                report.total_items,
                report.valid_items,
                report.duplicate_items,
                report.missing_fields,
                report.quality_score,
                json.dumps(report.issues, ensure_ascii=False),
                json.dumps(report.recommendations, ensure_ascii=False)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"품질 리포트 저장 오류: {e}")

    async def _update_cache(self, source_id: str, items: List[DataItem]):
        """캐시 업데이트"""
        try:
            source = self.data_sources.get(source_id)
            if not source:
                return
            
            cache_key = f"data_cache:{source_id}"
            ttl = self.cache_ttl.get(source.source_type, 3600)
            
            # 아이템들을 JSON으로 직렬화
            cache_data = {
                'items': [
                    {
                        'item_id': item.item_id,
                        'title': item.title,
                        'content': item.content[:500],  # 내용은 500자만 캐시
                        'published_at': item.published_at.isoformat(),
                        'category': item.category,
                        'tags': item.tags,
                        'quality_score': item.quality_score
                    }
                    for item in items
                ],
                'cached_at': datetime.now().isoformat(),
                'source_id': source_id
            }
            
            await self.redis_client.set(
                cache_key,
                json.dumps(cache_data, ensure_ascii=False),
                ex=ttl
            )
            
            logger.info(f"소스 {source_id} 캐시 업데이트 완료 (TTL: {ttl}초)")
            
        except Exception as e:
            logger.error(f"캐시 업데이트 오류: {e}")

    async def _update_source_quality(self, source_id: str, quality_score: float):
        """소스 품질 점수 업데이트"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE data_sources 
                SET quality_score = ?, last_updated = ?
                WHERE source_id = ?
            """, (quality_score, datetime.now().isoformat(), source_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"소스 품질 점수 업데이트 오류: {e}")

    async def get_data_source_status(self) -> Dict[str, Any]:
        """데이터 소스 상태 조회"""
        try:
            status = {
                'total_sources': len(self.data_sources),
                'active_sources': sum(1 for s in self.data_sources.values() if s.enabled),
                'sources': {},
                'quality_summary': {
                    'excellent': 0,  # 90점 이상
                    'good': 0,       # 70-89점
                    'fair': 0,       # 50-69점
                    'poor': 0        # 50점 미만
                },
                'last_updated': datetime.now().isoformat()
            }
            
            for source_id, source in self.data_sources.items():
                # 최근 데이터 수 조회
                recent_count = len(await self._get_recent_data_items(source_id, 24))
                
                source_status = {
                    'name': source.name,
                    'type': source.source_type.value,
                    'enabled': source.enabled,
                    'priority': source.priority,
                    'quality_score': source.quality_score,
                    'last_updated': source.last_updated.isoformat() if source.last_updated else None,
                    'recent_items_24h': recent_count,
                    'error_count': source.error_count
                }
                
                status['sources'][source_id] = source_status
                
                # 품질 등급 집계
                if source.quality_score >= 90:
                    status['quality_summary']['excellent'] += 1
                elif source.quality_score >= 70:
                    status['quality_summary']['good'] += 1
                elif source.quality_score >= 50:
                    status['quality_summary']['fair'] += 1
                else:
                    status['quality_summary']['poor'] += 1
            
            return status
            
        except Exception as e:
            logger.error(f"데이터 소스 상태 조회 오류: {e}")
            return {'error': str(e)}

# 전역 데이터 매니저 인스턴스
korean_data_manager = None

async def create_korean_data_manager(redis_url: str = "redis://localhost:6379") -> KoreanDataManager:
    """한국 데이터 매니저 생성"""
    global korean_data_manager
    if korean_data_manager is None:
        korean_data_manager = KoreanDataManager(redis_url)
        await korean_data_manager.__aenter__()
    return korean_data_manager

async def run_data_collection_cycle():
    """데이터 수집 사이클 실행"""
    try:
        manager = await create_korean_data_manager()
        
        # 모든 활성 소스에 대해 데이터 수집
        for source_id, source in manager.data_sources.items():
            if not source.enabled:
                continue
            
            try:
                if source.source_type == DataSourceType.SECURITIES_REPORT:
                    await manager.collect_securities_reports(source_id)
                elif source.source_type == DataSourceType.DART_DISCLOSURE:
                    # DART 공시 수집 (별도 구현 필요)
                    pass
                
                # 수집 완료 후 품질 검증 실행
                await manager.run_quality_validation(source_id)
                
                logger.info(f"소스 {source_id} 데이터 수집 및 검증 완료")
                
            except Exception as e:
                logger.error(f"소스 {source_id} 처리 오류: {e}")
                source.error_count += 1
        
        logger.info("데이터 수집 사이클 완료")
        
    except Exception as e:
        logger.error(f"데이터 수집 사이클 오류: {e}")

if __name__ == "__main__":
    asyncio.run(run_data_collection_cycle())