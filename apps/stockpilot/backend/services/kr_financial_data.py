"""
한국 금융 데이터 통합 서비스
금융감독원, 증권사 리포트, 한국투자증권 API 연동
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import xml.etree.ElementTree as ET
from dataclasses import dataclass
import re

# 로거 설정
logger = logging.getLogger(__name__)

@dataclass
class KRFinancialNews:
    """한국 금융 뉴스 데이터 클래스"""
    id: str
    title: str
    content: str
    summary: str
    url: str
    source: str
    source_type: str  # 'fss', 'securities', 'bank', 'government'
    published_at: datetime
    symbols_mentioned: List[str]
    sentiment: str
    sentiment_score: float
    impact_score: float
    topics: List[str]
    category: str
    importance: str  # 'high', 'medium', 'low'

@dataclass
class KRMarketData:
    """한국 시장 데이터 클래스"""
    symbol: str
    company_name: str
    market: str  # 'KOSPI', 'KOSDAQ', 'KONEX'
    current_price: float
    change: float
    change_percent: float
    volume: int
    value: int
    market_cap: int
    sector: str
    industry: str
    listing_shares: int
    foreign_ownership: float
    updated_at: datetime

class KRFinancialDataService:
    """한국 금융 데이터 서비스"""
    
    def __init__(self):
        self.session = None
        
        # 금융감독원 데이터 소스
        self.fss_sources = {
            "disclosure": {
                "name": "금융감독원 전자공시",
                "url": "http://dart.fss.or.kr/api/search.xml",
                "weight": 1.0
            },
            "press_release": {
                "name": "금융감독원 보도자료",
                "url": "https://www.fss.or.kr/fss/bbs/B0000188/list.do",
                "weight": 0.9
            }
        }
        
        # 주요 증권사 리포트 소스
        self.securities_sources = {
            "samsung": {
                "name": "삼성증권 리서치센터",
                "url": "https://www.samsungpop.com/research.do",
                "weight": 1.0
            },
            "mirae": {
                "name": "미래에셋증권 리서치센터", 
                "url": "https://securities.miraeasset.com/bbs/board/message/list.do?boardId=2230",
                "weight": 1.0
            },
            "kb": {
                "name": "KB증권 리서치센터",
                "url": "https://www.kbsec.co.kr/go.able?linkcd=s01010200",
                "weight": 0.9
            },
            "shinhan": {
                "name": "신한금융투자 리서치센터",
                "url": "https://www.shinhaninvest.com/research/research_list.jsp",
                "weight": 0.9
            },
            "nh": {
                "name": "NH투자증권 리서치센터",
                "url": "https://www.nhqv.com/research/researchCenter.jsp",
                "weight": 0.8
            }
        }
        
        # 한국 시장 휴장일 (2024년 기준)
        self.kr_holidays_2024 = [
            "2024-01-01",  # 신정
            "2024-02-09",  # 설날연휴
            "2024-02-10",  # 설날
            "2024-02-11",  # 설날연휴
            "2024-02-12",  # 설날대체공휴일
            "2024-03-01",  # 삼일절
            "2024-04-10",  # 국회의원선거
            "2024-05-05",  # 어린이날
            "2024-05-06",  # 어린이날대체공휴일
            "2024-05-15",  # 부처님오신날
            "2024-06-06",  # 현충일
            "2024-08-15",  # 광복절
            "2024-09-16",  # 추석연휴
            "2024-09-17",  # 추석
            "2024-09-18",  # 추석연휴
            "2024-10-03",  # 개천절
            "2024-10-09",  # 한글날
            "2024-12-25",  # 크리스마스
            "2024-12-31",  # 연말휴장
        ]
        
        # KOSPI 주요 종목
        self.kospi_major_stocks = {
            "005930": {"name": "삼성전자", "sector": "기술", "market_cap": 400000000000000},
            "000660": {"name": "SK하이닉스", "sector": "기술", "market_cap": 90000000000000},
            "035420": {"name": "NAVER", "sector": "통신서비스", "market_cap": 50000000000000},
            "051910": {"name": "LG화학", "sector": "소재", "market_cap": 80000000000000},
            "006400": {"name": "삼성SDI", "sector": "에너지", "market_cap": 40000000000000},
            "035720": {"name": "카카오", "sector": "통신서비스", "market_cap": 30000000000000},
            "028260": {"name": "삼성물산", "sector": "건설", "market_cap": 25000000000000},
            "012330": {"name": "현대모비스", "sector": "자동차", "market_cap": 30000000000000},
            "068270": {"name": "셀트리온", "sector": "바이오", "market_cap": 40000000000000},
            "207940": {"name": "삼성바이오로직스", "sector": "바이오", "market_cap": 70000000000000}
        }
        
        # KOSDAQ 주요 종목
        self.kosdaq_major_stocks = {
            "066570": {"name": "LG전자", "sector": "가전", "market_cap": 20000000000000},
            "096770": {"name": "SK이노베이션", "sector": "에너지", "market_cap": 30000000000000},
            "326030": {"name": "SK바이오팜", "sector": "바이오", "market_cap": 15000000000000},
            "058470": {"name": "리노공업", "sector": "기계", "market_cap": 10000000000000},
            "278280": {"name": "천보", "sector": "화학", "market_cap": 5000000000000}
        }

    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'StockPilot/1.0 (Korean Financial Data Service)'
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self.session:
            await self.session.close()

    def is_market_open(self) -> tuple[bool, str]:
        """한국 증시 개장 여부 확인"""
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        
        # 휴장일 확인
        if today_str in self.kr_holidays_2024:
            return False, "HOLIDAY"
        
        # 주말 확인
        if now.weekday() >= 5:  # 토요일(5), 일요일(6)
            return False, "WEEKEND"
        
        # 장 시간 확인 (09:00 - 15:30)
        market_open = now.replace(hour=9, minute=0, second=0, microsecond=0)
        market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
        
        if market_open <= now <= market_close:
            return True, "OPEN"
        elif now < market_open:
            return False, "PRE_MARKET"
        else:
            return False, "AFTER_HOURS"

    async def fetch_fss_disclosures(self, limit: int = 20) -> List[KRFinancialNews]:
        """금융감독원 전자공시 데이터 수집"""
        news_list = []
        
        try:
            # 금융감독원 DART API 호출 시뮬레이션
            # 실제로는 API 키가 필요하고 정식 등록 과정이 필요합니다
            logger.info("금융감독원 전자공시 데이터 수집 중...")
            
            # Mock 데이터 생성 (실제 구현시에는 DART API 연동)
            mock_disclosures = [
                {
                    "id": f"fss_disclosure_{i+1}",
                    "title": f"[삼성전자] 2024년 {i+1}분기 실적 공시",
                    "content": f"삼성전자가 2024년 {i+1}분기 영업이익 8조원을 기록했다고 공시했습니다. 반도체 사업부문의 회복세가 주요 요인으로 분석됩니다.",
                    "summary": f"삼성전자 {i+1}분기 영업이익 8조원 달성",
                    "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo=2024{i+1:02d}",
                    "source": "금융감독원 전자공시",
                    "source_type": "fss",
                    "published_at": datetime.now() - timedelta(hours=i),
                    "symbols_mentioned": ["005930"],
                    "sentiment": "POSITIVE" if i % 2 == 0 else "NEUTRAL",
                    "sentiment_score": 0.7 if i % 2 == 0 else 0.0,
                    "impact_score": 0.9,
                    "topics": ["실적발표", "반도체", "분기실적"],
                    "category": "공시",
                    "importance": "high"
                }
                for i in range(min(limit, 10))
            ]
            
            for disclosure in mock_disclosures:
                news_list.append(KRFinancialNews(**disclosure))
                
            logger.info(f"금융감독원 전자공시 {len(news_list)}건 수집 완료")
            
        except Exception as e:
            logger.error(f"금융감독원 전자공시 수집 오류: {e}")
            
        return news_list

    async def fetch_securities_reports(self, limit: int = 15) -> List[KRFinancialNews]:
        """증권사 리서치 리포트 수집"""
        news_list = []
        
        try:
            logger.info("증권사 리서치 리포트 수집 중...")
            
            # Mock 데이터 생성 (실제로는 각 증권사 API/웹 스크래핑)
            mock_reports = []
            
            for i, (sec_id, sec_info) in enumerate(self.securities_sources.items()):
                if i >= limit:
                    break
                    
                report = {
                    "id": f"securities_{sec_id}_{i+1}",
                    "title": f"[{sec_info['name']}] NAVER 목표주가 상향 조정",
                    "content": f"{sec_info['name']}에서 NAVER의 목표주가를 기존 25만원에서 28만원으로 상향 조정했습니다. AI 서비스 확장과 클라우드 사업 성장이 주요 근거입니다.",
                    "summary": f"NAVER 목표주가 28만원으로 상향 - {sec_info['name']}",
                    "url": sec_info['url'],
                    "source": sec_info['name'],
                    "source_type": "securities",
                    "published_at": datetime.now() - timedelta(hours=i*2),
                    "symbols_mentioned": ["035420"],
                    "sentiment": "POSITIVE",
                    "sentiment_score": 0.8,
                    "impact_score": 0.7,
                    "topics": ["목표주가", "리서치리포트", "AI서비스"],
                    "category": "애널리스트리포트",
                    "importance": "medium"
                }
                mock_reports.append(report)
                
            for report in mock_reports:
                news_list.append(KRFinancialNews(**report))
                
            logger.info(f"증권사 리서치 리포트 {len(news_list)}건 수집 완료")
            
        except Exception as e:
            logger.error(f"증권사 리서치 리포트 수집 오류: {e}")
            
        return news_list

    async def fetch_kospi_kosdaq_data(self) -> List[KRMarketData]:
        """KOSPI/KOSDAQ 시장 데이터 수집"""
        market_data = []
        
        try:
            logger.info("KOSPI/KOSDAQ 시장 데이터 수집 중...")
            
            # Mock 데이터 생성 (실제로는 KIS API, 한국투자증권 API 등 사용)
            all_stocks = {**self.kospi_major_stocks, **self.kosdaq_major_stocks}
            
            for symbol, info in all_stocks.items():
                # 시뮬레이션된 가격 데이터
                base_price = 50000 if symbol in self.kospi_major_stocks else 25000
                price_change = (hash(symbol) % 200 - 100) / 10  # -10% ~ +10% 변동
                current_price = base_price * (1 + price_change / 100)
                
                market_type = "KOSPI" if symbol in self.kospi_major_stocks else "KOSDAQ"
                
                data = KRMarketData(
                    symbol=symbol,
                    company_name=info["name"],
                    market=market_type,
                    current_price=current_price,
                    change=current_price - base_price,
                    change_percent=price_change,
                    volume=1000000 + (hash(symbol) % 5000000),
                    value=int(current_price * (1000000 + (hash(symbol) % 5000000))),
                    market_cap=info.get("market_cap", 10000000000000),
                    sector=info["sector"],
                    industry=info["sector"],
                    listing_shares=info.get("market_cap", 10000000000000) // int(current_price),
                    foreign_ownership=15.5 + (hash(symbol) % 30),
                    updated_at=datetime.now()
                )
                market_data.append(data)
                
            logger.info(f"KOSPI/KOSDAQ 시장 데이터 {len(market_data)}종목 수집 완료")
            
        except Exception as e:
            logger.error(f"KOSPI/KOSDAQ 데이터 수집 오류: {e}")
            
        return market_data

    async def get_comprehensive_kr_data(self) -> Dict[str, Any]:
        """종합 한국 금융 데이터 수집"""
        try:
            logger.info("종합 한국 금융 데이터 수집 시작")
            
            # 병렬로 모든 데이터 수집
            fss_news, securities_reports, market_data = await asyncio.gather(
                self.fetch_fss_disclosures(10),
                self.fetch_securities_reports(10),
                self.fetch_kospi_kosdaq_data(),
                return_exceptions=True
            )
            
            # 예외 처리
            if isinstance(fss_news, Exception):
                logger.error(f"FSS 데이터 수집 실패: {fss_news}")
                fss_news = []
                
            if isinstance(securities_reports, Exception):
                logger.error(f"증권사 리포트 수집 실패: {securities_reports}")
                securities_reports = []
                
            if isinstance(market_data, Exception):
                logger.error(f"시장 데이터 수집 실패: {market_data}")
                market_data = []
            
            # 뉴스 데이터 통합 및 정렬
            all_news = fss_news + securities_reports
            all_news.sort(key=lambda x: x.published_at, reverse=True)
            
            # 시장 상태 확인
            is_open, market_state = self.is_market_open()
            
            result = {
                "market_info": {
                    "is_open": is_open,
                    "state": market_state,
                    "local_time": datetime.now().isoformat(),
                    "timezone": "Asia/Seoul"
                },
                "news": [
                    {
                        "id": news.id,
                        "title": news.title,
                        "content": news.content,
                        "summary": news.summary,
                        "url": news.url,
                        "source": news.source,
                        "source_type": news.source_type,
                        "published_at": news.published_at.isoformat(),
                        "symbols_mentioned": news.symbols_mentioned,
                        "sentiment": news.sentiment,
                        "sentiment_score": news.sentiment_score,
                        "impact_score": news.impact_score,
                        "topics": news.topics,
                        "category": news.category,
                        "importance": news.importance
                    }
                    for news in all_news[:20]  # 최신 20개
                ],
                "market_data": [
                    {
                        "symbol": data.symbol,
                        "company_name": data.company_name,
                        "market": data.market,
                        "current_price": data.current_price,
                        "change": data.change,
                        "change_percent": data.change_percent,
                        "volume": data.volume,
                        "value": data.value,
                        "market_cap": data.market_cap,
                        "sector": data.sector,
                        "foreign_ownership": data.foreign_ownership,
                        "updated_at": data.updated_at.isoformat()
                    }
                    for data in market_data
                ],
                "statistics": {
                    "total_news": len(all_news),
                    "fss_news": len(fss_news),
                    "securities_reports": len(securities_reports),
                    "total_stocks": len(market_data),
                    "kospi_stocks": len([d for d in market_data if d.market == "KOSPI"]),
                    "kosdaq_stocks": len([d for d in market_data if d.market == "KOSDAQ"])
                },
                "data_sources": {
                    "fss": list(self.fss_sources.keys()),
                    "securities": list(self.securities_sources.keys())
                },
                "generated_at": datetime.now().isoformat()
            }
            
            logger.info(f"종합 한국 금융 데이터 수집 완료: 뉴스 {len(all_news)}건, 주식 {len(market_data)}종목")
            return result
            
        except Exception as e:
            logger.error(f"종합 한국 금융 데이터 수집 오류: {e}")
            return {
                "error": str(e),
                "generated_at": datetime.now().isoformat()
            }

    def validate_stock_symbol(self, symbol: str) -> bool:
        """한국 주식 종목코드 유효성 검사"""
        # 한국 종목코드는 6자리 숫자
        return bool(re.match(r'^\d{6}$', symbol))

    def get_market_calendar_info(self) -> Dict[str, Any]:
        """한국 시장 휴장일 캘린더 정보"""
        now = datetime.now()
        
        # 다음 개장일 계산
        next_open_date = now
        while True:
            next_open_date += timedelta(days=1)
            next_open_str = next_open_date.strftime("%Y-%m-%d")
            
            # 평일이고 휴장일이 아닌 경우
            if next_open_date.weekday() < 5 and next_open_str not in self.kr_holidays_2024:
                break
        
        return {
            "today": now.strftime("%Y-%m-%d"),
            "is_trading_day": self.is_market_open()[0],
            "market_state": self.is_market_open()[1],
            "next_trading_day": next_open_date.strftime("%Y-%m-%d"),
            "holidays_2024": self.kr_holidays_2024,
            "market_hours": {
                "regular": {"open": "09:00", "close": "15:30"},
                "timezone": "Asia/Seoul"
            }
        }

# 서비스 인스턴스 생성용 팩토리 함수
async def create_kr_financial_service():
    """KR 금융 데이터 서비스 인스턴스 생성"""
    service = KRFinancialDataService()
    await service.__aenter__()
    return service