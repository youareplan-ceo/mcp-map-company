#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
StockPilot 다중 프로바이더 페일오버 시스템
Yahoo Finance, Reuters, Bloomberg 다중화 및 자동 페일오버 로직
"""

import asyncio
import aiohttp
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import random
from urllib.parse import urlencode
import hashlib

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/stockpilot/multi_provider.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DataSourceType(Enum):
    """데이터 소스 유형"""
    MARKET_DATA = "market_data"
    NEWS = "news"
    FINANCIAL_REPORTS = "financial_reports"
    ECONOMIC_DATA = "economic_data"

class ProviderStatus(Enum):
    """프로바이더 상태"""
    ACTIVE = "active"
    DEGRADED = "degraded"
    FAILED = "failed"
    MAINTENANCE = "maintenance"

@dataclass
class ProviderConfig:
    """프로바이더 설정"""
    name: str
    base_url: str
    api_key: Optional[str]
    timeout: float
    retry_count: int
    priority: int  # 낮을수록 우선순위 높음
    rate_limit: int  # 초당 요청 제한
    data_types: List[DataSourceType]
    health_check_endpoint: str
    quality_weight: float  # 품질 가중치 (0-1)

@dataclass
class ProviderMetrics:
    """프로바이더 메트릭"""
    provider_name: str
    success_count: int
    failure_count: int
    avg_response_time: float
    last_success: datetime
    last_failure: Optional[datetime]
    current_status: ProviderStatus
    quality_score: float
    uptime_percentage: float

@dataclass
class DataRequest:
    """데이터 요청"""
    data_type: DataSourceType
    symbol: str
    parameters: Dict[str, Any]
    max_age_seconds: int = 300  # 캐시 최대 수명
    require_realtime: bool = False

@dataclass
class DataResponse:
    """데이터 응답"""
    provider_name: str
    data: Any
    timestamp: datetime
    response_time: float
    quality_score: float
    is_cached: bool = False

class MultiProviderFailover:
    """다중 프로바이더 페일오버 매니저"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.providers = self._init_providers()
        self.provider_metrics = {p.name: self._init_metrics(p) for p in self.providers}
        self.cache = {}
        self.rate_limiters = {p.name: {'requests': [], 'window': 1.0} for p in self.providers}
        self.circuit_breakers = {p.name: {'failures': 0, 'last_failure': None, 'state': 'closed'} for p in self.providers}
        
        # 백그라운드 작업
        self.health_check_task = None
        self.metrics_cleanup_task = None
        
    def _init_providers(self) -> List[ProviderConfig]:
        """프로바이더 초기화"""
        return [
            # Yahoo Finance (1순위 - 무료, 안정적)
            ProviderConfig(
                name="yahoo_finance",
                base_url="https://query1.finance.yahoo.com/v8/finance/chart",
                api_key=None,
                timeout=10.0,
                retry_count=3,
                priority=1,
                rate_limit=200,  # 초당 200요청
                data_types=[DataSourceType.MARKET_DATA],
                health_check_endpoint="/",
                quality_weight=0.8
            ),
            
            # Alpha Vantage (2순위)
            ProviderConfig(
                name="alpha_vantage",
                base_url="https://www.alphavantage.co/query",
                api_key="demo",  # 실제 환경에서는 실제 API 키 사용
                timeout=15.0,
                retry_count=2,
                priority=2,
                rate_limit=5,  # 초당 5요청
                data_types=[DataSourceType.MARKET_DATA, DataSourceType.FINANCIAL_REPORTS],
                health_check_endpoint="",
                quality_weight=0.9
            ),
            
            # Reuters (뉴스 데이터)
            ProviderConfig(
                name="reuters_news",
                base_url="https://reuters.com/pf/api/v3/content/fetch",
                api_key=None,
                timeout=12.0,
                retry_count=2,
                priority=1,
                rate_limit=50,
                data_types=[DataSourceType.NEWS],
                health_check_endpoint="/",
                quality_weight=0.95
            ),
            
            # NewsAPI (뉴스 백업)
            ProviderConfig(
                name="newsapi",
                base_url="https://newsapi.org/v2",
                api_key="demo",
                timeout=10.0,
                retry_count=3,
                priority=2,
                rate_limit=100,
                data_types=[DataSourceType.NEWS],
                health_check_endpoint="/",
                quality_weight=0.7
            ),
            
            # FRED (경제 데이터)
            ProviderConfig(
                name="fred_economic",
                base_url="https://api.stlouisfed.org/fred",
                api_key="demo",
                timeout=8.0,
                retry_count=2,
                priority=1,
                rate_limit=120,
                data_types=[DataSourceType.ECONOMIC_DATA],
                health_check_endpoint="/",
                quality_weight=0.85
            ),
            
            # 한국 데이터 소스들
            ProviderConfig(
                name="krx_data",
                base_url="http://data.krx.co.kr/comm",
                api_key=None,
                timeout=15.0,
                retry_count=2,
                priority=1,
                rate_limit=30,
                data_types=[DataSourceType.MARKET_DATA],
                health_check_endpoint="/",
                quality_weight=0.75
            ),
            
            ProviderConfig(
                name="dart_api",
                base_url="https://opendart.fss.or.kr/api",
                api_key="demo",
                timeout=20.0,
                retry_count=2,
                priority=1,
                rate_limit=10,
                data_types=[DataSourceType.FINANCIAL_REPORTS],
                health_check_endpoint="/",
                quality_weight=0.9
            )
        ]
    
    def _init_metrics(self, provider: ProviderConfig) -> ProviderMetrics:
        """프로바이더 메트릭 초기화"""
        return ProviderMetrics(
            provider_name=provider.name,
            success_count=0,
            failure_count=0,
            avg_response_time=0.0,
            last_success=datetime.now(timezone.utc),
            last_failure=None,
            current_status=ProviderStatus.ACTIVE,
            quality_score=provider.quality_weight,
            uptime_percentage=100.0
        )
    
    async def get_data(self, request: DataRequest) -> Optional[DataResponse]:
        """데이터 조회 (페일오버 로직 포함)"""
        logger.info(f"데이터 요청: {request.data_type.value} - {request.symbol}")
        
        # 캐시 확인
        if not request.require_realtime:
            cached_response = self._get_from_cache(request)
            if cached_response:
                logger.info(f"캐시에서 데이터 반환: {request.symbol}")
                return cached_response
        
        # 요청 유형에 맞는 프로바이더들 선택
        eligible_providers = self._get_eligible_providers(request.data_type)
        
        if not eligible_providers:
            logger.error(f"사용 가능한 프로바이더가 없습니다: {request.data_type.value}")
            return None
        
        # 프로바이더 우선순위 정렬
        sorted_providers = self._sort_providers_by_priority(eligible_providers)
        
        # 각 프로바이더 순차 시도
        for provider in sorted_providers:
            if not self._can_make_request(provider):
                logger.warning(f"요청 제한 또는 회로 차단기로 인해 {provider.name} 스킵")
                continue
            
            try:
                response = await self._fetch_from_provider(provider, request)
                if response:
                    # 성공 메트릭 업데이트
                    self._update_success_metrics(provider.name, response.response_time)
                    
                    # 캐시 저장
                    self._save_to_cache(request, response)
                    
                    logger.info(f"데이터 조회 성공: {provider.name} - {request.symbol}")
                    return response
                    
            except Exception as e:
                logger.warning(f"{provider.name}에서 데이터 조회 실패: {str(e)}")
                self._update_failure_metrics(provider.name, str(e))
                continue
        
        logger.error(f"모든 프로바이더에서 데이터 조회 실패: {request.symbol}")
        return None
    
    def _get_eligible_providers(self, data_type: DataSourceType) -> List[ProviderConfig]:
        """데이터 유형에 맞는 프로바이더 선택"""
        eligible = []
        
        for provider in self.providers:
            if data_type in provider.data_types:
                metrics = self.provider_metrics[provider.name]
                
                # 상태 확인
                if metrics.current_status in [ProviderStatus.ACTIVE, ProviderStatus.DEGRADED]:
                    eligible.append(provider)
        
        return eligible
    
    def _sort_providers_by_priority(self, providers: List[ProviderConfig]) -> List[ProviderConfig]:
        """프로바이더 우선순위 정렬"""
        def priority_score(provider: ProviderConfig) -> float:
            metrics = self.provider_metrics[provider.name]
            
            # 기본 우선순위
            score = provider.priority
            
            # 품질 점수 반영 (높을수록 좋음)
            score -= metrics.quality_score * 2
            
            # 응답 시간 반영 (낮을수록 좋음)
            score += metrics.avg_response_time / 1000
            
            # 성공률 반영
            total_requests = metrics.success_count + metrics.failure_count
            if total_requests > 0:
                success_rate = metrics.success_count / total_requests
                score -= success_rate * 3
            
            # 최근 실패 패널티
            if metrics.last_failure and metrics.last_failure > datetime.now(timezone.utc) - timedelta(minutes=5):
                score += 5
            
            return score
        
        return sorted(providers, key=priority_score)
    
    def _can_make_request(self, provider: ProviderConfig) -> bool:
        """요청 가능 여부 확인 (Rate Limiting, Circuit Breaker)"""
        now = time.time()
        
        # Circuit Breaker 확인
        circuit_breaker = self.circuit_breakers[provider.name]
        if circuit_breaker['state'] == 'open':
            # 5분 후 half-open 상태로 전환
            if circuit_breaker['last_failure'] and now - circuit_breaker['last_failure'] > 300:
                circuit_breaker['state'] = 'half-open'
                circuit_breaker['failures'] = 0
                logger.info(f"{provider.name} 회로 차단기: half-open 상태로 전환")
            else:
                return False
        
        # Rate Limiting 확인
        rate_limiter = self.rate_limiters[provider.name]
        
        # 시간 윈도우 내 요청 수 정리
        rate_limiter['requests'] = [
            req_time for req_time in rate_limiter['requests']
            if now - req_time < rate_limiter['window']
        ]
        
        # 요청 제한 확인
        if len(rate_limiter['requests']) >= provider.rate_limit:
            return False
        
        # 요청 시간 기록
        rate_limiter['requests'].append(now)
        return True
    
    async def _fetch_from_provider(self, provider: ProviderConfig, request: DataRequest) -> Optional[DataResponse]:
        """특정 프로바이더에서 데이터 조회"""
        start_time = time.time()
        
        try:
            if provider.name == "yahoo_finance":
                data = await self._fetch_yahoo_finance(provider, request)
            elif provider.name == "alpha_vantage":
                data = await self._fetch_alpha_vantage(provider, request)
            elif provider.name == "reuters_news":
                data = await self._fetch_reuters_news(provider, request)
            elif provider.name == "newsapi":
                data = await self._fetch_newsapi(provider, request)
            elif provider.name == "fred_economic":
                data = await self._fetch_fred_economic(provider, request)
            elif provider.name == "krx_data":
                data = await self._fetch_krx_data(provider, request)
            elif provider.name == "dart_api":
                data = await self._fetch_dart_api(provider, request)
            else:
                logger.warning(f"알 수 없는 프로바이더: {provider.name}")
                return None
            
            response_time = (time.time() - start_time) * 1000
            
            if data:
                # 데이터 품질 점수 계산
                quality_score = self._calculate_quality_score(data, provider)
                
                return DataResponse(
                    provider_name=provider.name,
                    data=data,
                    timestamp=datetime.now(timezone.utc),
                    response_time=response_time,
                    quality_score=quality_score,
                    is_cached=False
                )
            
            return None
            
        except Exception as e:
            logger.error(f"{provider.name} 데이터 조회 오류: {str(e)}")
            raise
    
    async def _fetch_yahoo_finance(self, provider: ProviderConfig, request: DataRequest) -> Optional[Dict]:
        """Yahoo Finance 데이터 조회"""
        try:
            url = f"{provider.base_url}/{request.symbol}"
            params = {
                'interval': request.parameters.get('interval', '1d'),
                'range': request.parameters.get('range', '1mo'),
                'events': 'div,split'
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=provider.timeout)) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if 'chart' in data and 'result' in data['chart'] and data['chart']['result']:
                            result = data['chart']['result'][0]
                            return {
                                'symbol': request.symbol,
                                'timestamp': result.get('timestamp', []),
                                'indicators': result.get('indicators', {}),
                                'meta': result.get('meta', {}),
                                'source': 'yahoo_finance'
                            }
                    
                    logger.warning(f"Yahoo Finance API 오류: HTTP {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Yahoo Finance 조회 오류: {str(e)}")
            return None
    
    async def _fetch_alpha_vantage(self, provider: ProviderConfig, request: DataRequest) -> Optional[Dict]:
        """Alpha Vantage 데이터 조회"""
        try:
            params = {
                'function': request.parameters.get('function', 'TIME_SERIES_DAILY'),
                'symbol': request.symbol,
                'apikey': provider.api_key
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=provider.timeout)) as session:
                async with session.get(provider.base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if 'Error Message' not in data and 'Note' not in data:
                            return {
                                'symbol': request.symbol,
                                'data': data,
                                'source': 'alpha_vantage'
                            }
                    
                    logger.warning(f"Alpha Vantage API 오류: HTTP {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Alpha Vantage 조회 오류: {str(e)}")
            return None
    
    async def _fetch_reuters_news(self, provider: ProviderConfig, request: DataRequest) -> Optional[Dict]:
        """Reuters 뉴스 데이터 조회"""
        try:
            # Reuters API는 실제로는 복잡한 인증이 필요하므로 시뮬레이션
            await asyncio.sleep(0.5)  # 네트워크 지연 시뮬레이션
            
            # 실제 구현에서는 Reuters API를 호출
            mock_news = [
                {
                    'title': f'{request.symbol} Stock Analysis Update',
                    'summary': f'Latest market analysis for {request.symbol}',
                    'published': datetime.now(timezone.utc).isoformat(),
                    'url': f'https://reuters.com/markets/{request.symbol.lower()}',
                    'sentiment': random.choice(['positive', 'neutral', 'negative']),
                    'relevance': random.uniform(0.7, 1.0)
                }
                for _ in range(random.randint(3, 8))
            ]
            
            return {
                'symbol': request.symbol,
                'articles': mock_news,
                'total_count': len(mock_news),
                'source': 'reuters_news'
            }
            
        except Exception as e:
            logger.error(f"Reuters 뉴스 조회 오류: {str(e)}")
            return None
    
    async def _fetch_newsapi(self, provider: ProviderConfig, request: DataRequest) -> Optional[Dict]:
        """NewsAPI 데이터 조회"""
        try:
            params = {
                'q': f'{request.symbol} stock',
                'apiKey': provider.api_key,
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': request.parameters.get('limit', 20)
            }
            
            url = f"{provider.base_url}/everything"
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=provider.timeout)) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get('status') == 'ok':
                            return {
                                'symbol': request.symbol,
                                'articles': data.get('articles', []),
                                'total_results': data.get('totalResults', 0),
                                'source': 'newsapi'
                            }
                    
                    logger.warning(f"NewsAPI 오류: HTTP {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"NewsAPI 조회 오류: {str(e)}")
            return None
    
    async def _fetch_fred_economic(self, provider: ProviderConfig, request: DataRequest) -> Optional[Dict]:
        """FRED 경제 데이터 조회"""
        try:
            params = {
                'series_id': request.symbol,
                'api_key': provider.api_key,
                'file_type': 'json'
            }
            
            url = f"{provider.base_url}/series/observations"
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=provider.timeout)) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if 'observations' in data:
                            return {
                                'series_id': request.symbol,
                                'observations': data['observations'],
                                'source': 'fred_economic'
                            }
                    
                    logger.warning(f"FRED API 오류: HTTP {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"FRED 조회 오류: {str(e)}")
            return None
    
    async def _fetch_krx_data(self, provider: ProviderConfig, request: DataRequest) -> Optional[Dict]:
        """KRX 데이터 조회"""
        try:
            # KRX API 시뮬레이션 (실제로는 복잡한 POST 요청 필요)
            await asyncio.sleep(0.8)
            
            mock_data = {
                'symbol': request.symbol,
                'price': random.uniform(10000, 100000),
                'change': random.uniform(-5, 5),
                'volume': random.randint(100000, 10000000),
                'market_cap': random.uniform(1000000000, 100000000000),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'source': 'krx_data'
            }
            
            return mock_data
            
        except Exception as e:
            logger.error(f"KRX 데이터 조회 오류: {str(e)}")
            return None
    
    async def _fetch_dart_api(self, provider: ProviderConfig, request: DataRequest) -> Optional[Dict]:
        """DART API 데이터 조회"""
        try:
            params = {
                'crtfc_key': provider.api_key,
                'corp_code': request.symbol,
                'bsns_year': request.parameters.get('year', '2024'),
                'reprt_code': request.parameters.get('report_code', '11011')
            }
            
            url = f"{provider.base_url}/fnlttSinglAcntAll.json"
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=provider.timeout)) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get('status') == '000':
                            return {
                                'corp_code': request.symbol,
                                'financial_data': data.get('list', []),
                                'source': 'dart_api'
                            }
                    
                    logger.warning(f"DART API 오류: HTTP {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"DART API 조회 오류: {str(e)}")
            return None
    
    def _calculate_quality_score(self, data: Dict, provider: ProviderConfig) -> float:
        """데이터 품질 점수 계산"""
        score = provider.quality_weight
        
        if not data or not isinstance(data, dict):
            return 0.0
        
        # 데이터 완전성 확인
        required_fields = ['symbol', 'source']
        present_fields = sum(1 for field in required_fields if field in data and data[field])
        completeness = present_fields / len(required_fields)
        
        # 데이터 크기 확인
        data_size_score = min(len(str(data)) / 1000, 1.0)  # 1KB 기준으로 정규화
        
        # 최종 점수 계산
        final_score = score * (0.6 * completeness + 0.4 * data_size_score)
        
        return min(max(final_score, 0.0), 1.0)
    
    def _get_from_cache(self, request: DataRequest) -> Optional[DataResponse]:
        """캐시에서 데이터 조회"""
        cache_key = self._generate_cache_key(request)
        
        if cache_key in self.cache:
            cached_item = self.cache[cache_key]
            
            # 캐시 유효성 확인
            age = (datetime.now(timezone.utc) - cached_item['timestamp']).total_seconds()
            if age <= request.max_age_seconds:
                response = cached_item['response']
                response.is_cached = True
                return response
            else:
                # 만료된 캐시 삭제
                del self.cache[cache_key]
        
        return None
    
    def _save_to_cache(self, request: DataRequest, response: DataResponse):
        """캐시에 데이터 저장"""
        cache_key = self._generate_cache_key(request)
        
        self.cache[cache_key] = {
            'timestamp': datetime.now(timezone.utc),
            'response': response
        }
        
        # 캐시 크기 제한 (최대 1000개 항목)
        if len(self.cache) > 1000:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]['timestamp'])
            del self.cache[oldest_key]
    
    def _generate_cache_key(self, request: DataRequest) -> str:
        """캐시 키 생성"""
        key_data = f"{request.data_type.value}:{request.symbol}:{json.dumps(request.parameters, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _update_success_metrics(self, provider_name: str, response_time: float):
        """성공 메트릭 업데이트"""
        metrics = self.provider_metrics[provider_name]
        
        metrics.success_count += 1
        metrics.last_success = datetime.now(timezone.utc)
        
        # 평균 응답 시간 업데이트 (지수 평활법)
        alpha = 0.3
        metrics.avg_response_time = alpha * response_time + (1 - alpha) * metrics.avg_response_time
        
        # 가용성 계산
        total_requests = metrics.success_count + metrics.failure_count
        metrics.uptime_percentage = (metrics.success_count / total_requests) * 100
        
        # 상태 업데이트
        if metrics.uptime_percentage >= 95:
            metrics.current_status = ProviderStatus.ACTIVE
        elif metrics.uptime_percentage >= 80:
            metrics.current_status = ProviderStatus.DEGRADED
        else:
            metrics.current_status = ProviderStatus.FAILED
        
        # Circuit Breaker 재설정
        circuit_breaker = self.circuit_breakers[provider_name]
        if circuit_breaker['state'] == 'half-open':
            circuit_breaker['state'] = 'closed'
            circuit_breaker['failures'] = 0
    
    def _update_failure_metrics(self, provider_name: str, error: str):
        """실패 메트릭 업데이트"""
        metrics = self.provider_metrics[provider_name]
        
        metrics.failure_count += 1
        metrics.last_failure = datetime.now(timezone.utc)
        
        # 가용성 계산
        total_requests = metrics.success_count + metrics.failure_count
        metrics.uptime_percentage = (metrics.success_count / total_requests) * 100
        
        # 상태 업데이트
        if metrics.uptime_percentage < 80:
            metrics.current_status = ProviderStatus.FAILED
        elif metrics.uptime_percentage < 95:
            metrics.current_status = ProviderStatus.DEGRADED
        
        # Circuit Breaker 업데이트
        circuit_breaker = self.circuit_breakers[provider_name]
        circuit_breaker['failures'] += 1
        circuit_breaker['last_failure'] = time.time()
        
        # 5회 연속 실패시 회로 차단
        if circuit_breaker['failures'] >= 5:
            circuit_breaker['state'] = 'open'
            logger.warning(f"{provider_name} 회로 차단기 활성화 (5회 연속 실패)")
    
    async def health_check_all_providers(self):
        """모든 프로바이더 헬스 체크"""
        logger.info("전체 프로바이더 헬스 체크 시작")
        
        tasks = []
        for provider in self.providers:
            task = asyncio.create_task(self._health_check_provider(provider))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        healthy_count = sum(1 for result in results if result is True)
        logger.info(f"헬스 체크 완료: {healthy_count}/{len(self.providers)} 프로바이더 정상")
        
        return results
    
    async def _health_check_provider(self, provider: ProviderConfig) -> bool:
        """개별 프로바이더 헬스 체크"""
        try:
            start_time = time.time()
            
            # 간단한 헬스 체크 요청
            test_request = DataRequest(
                data_type=provider.data_types[0],
                symbol="AAPL",  # 테스트용 심볼
                parameters={},
                max_age_seconds=0  # 캐시 사용 안 함
            )
            
            response = await self._fetch_from_provider(provider, test_request)
            response_time = (time.time() - start_time) * 1000
            
            if response:
                self._update_success_metrics(provider.name, response_time)
                logger.debug(f"{provider.name} 헬스 체크 성공 ({response_time:.1f}ms)")
                return True
            else:
                self._update_failure_metrics(provider.name, "Health check failed")
                logger.warning(f"{provider.name} 헬스 체크 실패")
                return False
                
        except Exception as e:
            self._update_failure_metrics(provider.name, f"Health check error: {str(e)}")
            logger.error(f"{provider.name} 헬스 체크 오류: {str(e)}")
            return False
    
    def get_provider_status(self) -> Dict[str, Dict]:
        """모든 프로바이더 상태 조회"""
        status_report = {}
        
        for provider in self.providers:
            metrics = self.provider_metrics[provider.name]
            circuit_breaker = self.circuit_breakers[provider.name]
            
            status_report[provider.name] = {
                'status': metrics.current_status.value,
                'uptime_percentage': round(metrics.uptime_percentage, 2),
                'success_count': metrics.success_count,
                'failure_count': metrics.failure_count,
                'avg_response_time': round(metrics.avg_response_time, 2),
                'quality_score': round(metrics.quality_score, 2),
                'last_success': metrics.last_success.isoformat() if metrics.last_success else None,
                'last_failure': metrics.last_failure.isoformat() if metrics.last_failure else None,
                'circuit_breaker_state': circuit_breaker['state'],
                'data_types': [dt.value for dt in provider.data_types],
                'priority': provider.priority
            }
        
        return status_report
    
    async def start_background_tasks(self):
        """백그라운드 작업 시작"""
        logger.info("백그라운드 작업 시작")
        
        # 헬스 체크 작업 (5분마다)
        self.health_check_task = asyncio.create_task(self._periodic_health_check())
        
        # 메트릭 정리 작업 (1시간마다)
        self.metrics_cleanup_task = asyncio.create_task(self._periodic_metrics_cleanup())
    
    async def _periodic_health_check(self):
        """주기적 헬스 체크"""
        while True:
            try:
                await asyncio.sleep(300)  # 5분 대기
                await self.health_check_all_providers()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"주기적 헬스 체크 오류: {str(e)}")
    
    async def _periodic_metrics_cleanup(self):
        """주기적 메트릭 정리"""
        while True:
            try:
                await asyncio.sleep(3600)  # 1시간 대기
                
                # 오래된 캐시 정리
                now = datetime.now(timezone.utc)
                expired_keys = []
                
                for key, item in self.cache.items():
                    age = (now - item['timestamp']).total_seconds()
                    if age > 3600:  # 1시간 이상 된 캐시 삭제
                        expired_keys.append(key)
                
                for key in expired_keys:
                    del self.cache[key]
                
                if expired_keys:
                    logger.info(f"만료된 캐시 {len(expired_keys)}개 정리 완료")
                
                # Rate Limiter 정리
                current_time = time.time()
                for provider_name, rate_limiter in self.rate_limiters.items():
                    rate_limiter['requests'] = [
                        req_time for req_time in rate_limiter['requests']
                        if current_time - req_time < rate_limiter['window']
                    ]
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"주기적 메트릭 정리 오류: {str(e)}")
    
    async def stop_background_tasks(self):
        """백그라운드 작업 중단"""
        logger.info("백그라운드 작업 중단")
        
        if self.health_check_task:
            self.health_check_task.cancel()
        
        if self.metrics_cleanup_task:
            self.metrics_cleanup_task.cancel()

async def main():
    """테스트 실행"""
    try:
        logger.info("다중 프로바이더 페일오버 시스템 테스트 시작")
        
        failover = MultiProviderFailover()
        
        # 백그라운드 작업 시작
        await failover.start_background_tasks()
        
        # 다양한 데이터 요청 테스트
        test_requests = [
            DataRequest(DataSourceType.MARKET_DATA, "AAPL", {"interval": "1d"}),
            DataRequest(DataSourceType.MARKET_DATA, "005930", {"interval": "1d"}),  # 삼성전자
            DataRequest(DataSourceType.NEWS, "TSLA", {"limit": 10}),
            DataRequest(DataSourceType.ECONOMIC_DATA, "GDP", {}),
            DataRequest(DataSourceType.FINANCIAL_REPORTS, "MSFT", {"year": "2024"})
        ]
        
        print("\n" + "="*60)
        print("다중 프로바이더 페일오버 시스템 테스트")
        print("="*60)
        
        for i, request in enumerate(test_requests, 1):
            print(f"\n{i}. 테스트 요청: {request.data_type.value} - {request.symbol}")
            
            response = await failover.get_data(request)
            if response:
                print(f"   ✓ 성공: {response.provider_name}")
                print(f"   응답 시간: {response.response_time:.1f}ms")
                print(f"   품질 점수: {response.quality_score:.2f}")
                print(f"   캐시 여부: {'Yes' if response.is_cached else 'No'}")
            else:
                print("   ✗ 실패: 모든 프로바이더에서 데이터 조회 실패")
        
        # 프로바이더 상태 출력
        print(f"\n{'='*60}")
        print("프로바이더 상태 요약")
        print("="*60)
        
        status_report = failover.get_provider_status()
        for provider_name, status in status_report.items():
            status_emoji = {
                'active': '🟢',
                'degraded': '🟡',
                'failed': '🔴',
                'maintenance': '🔧'
            }.get(status['status'], '⚪')
            
            print(f"\n{status_emoji} {provider_name}:")
            print(f"   상태: {status['status']}")
            print(f"   가동율: {status['uptime_percentage']:.1f}%")
            print(f"   성공/실패: {status['success_count']}/{status['failure_count']}")
            print(f"   평균 응답시간: {status['avg_response_time']:.1f}ms")
            print(f"   품질 점수: {status['quality_score']:.2f}")
            print(f"   회로 차단기: {status['circuit_breaker_state']}")
        
        # 잠시 대기 후 헬스 체크
        print(f"\n{'='*60}")
        print("전체 프로바이더 헬스 체크 실행...")
        
        health_results = await failover.health_check_all_providers()
        healthy_count = sum(1 for result in health_results if result is True)
        
        print(f"헬스 체크 결과: {healthy_count}/{len(health_results)} 프로바이더 정상")
        
        # 백그라운드 작업 중단
        await failover.stop_background_tasks()
        
        print(f"\n{'='*60}")
        print("다중 프로바이더 페일오버 시스템 테스트 완료")
        print("="*60)
        
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"테스트 실행 중 오류 발생: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())