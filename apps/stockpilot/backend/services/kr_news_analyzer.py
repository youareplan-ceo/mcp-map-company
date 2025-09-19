"""
한국 시장 뉴스 수집 및 AI 감성 분석 서비스 (확장된 버전)
네이버 뉴스, 다음 뉴스, 금융감독원, 증권사 리포트 등 종합 데이터 수집
"""

import asyncio
import aiohttp
import openai
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import json
import re
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup
import feedparser
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.openai_optimizer import get_openai_optimizer
from services.kr_financial_data import KRFinancialDataService, create_kr_financial_service

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class KRNewsItem:
    """한국 뉴스 아이템 클래스"""
    id: str
    title: str
    content: str
    summary: str
    url: str
    source: str
    published_at: str
    symbols_mentioned: List[str]  # 언급된 종목코드들
    sentiment: str  # POSITIVE, NEGATIVE, NEUTRAL
    sentiment_score: float  # -1.0 ~ 1.0
    impact_score: float  # 0.0 ~ 1.0 (시장 영향도)
    topics: List[str]  # 주요 토픽들
    language: str = "ko"
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return asdict(self)

class KRNewsAnalyzer:
    """한국 뉴스 수집 및 분석 서비스"""
    
    # 한국 뉴스 소스 RSS 피드
    NEWS_SOURCES = {
        "naver_economy": {
            "name": "네이버 경제뉴스",
            "rss_url": "https://news.naver.com/main/rss/read.naver?mode=LSD&mid=shm&sid1=101",
            "weight": 0.9
        },
        "naver_stock": {
            "name": "네이버 증권뉴스", 
            "rss_url": "https://news.naver.com/main/rss/read.naver?mode=LSD&mid=shm&sid1=101&sid2=258",
            "weight": 1.0
        },
        "daum_economy": {
            "name": "다음 경제뉴스",
            "rss_url": "https://media.daum.net/rss/channel/economy/",
            "weight": 0.8
        },
        "hankyoreh_economy": {
            "name": "한겨레 경제",
            "rss_url": "https://www.hani.co.kr/rss/economy/",
            "weight": 0.7
        }
    }
    
    # 주요 한국 종목 키워드 매핑
    STOCK_KEYWORDS = {
        "005930": ["삼성전자", "삼성", "반도체", "갤럭시", "Samsung"],
        "000660": ["SK하이닉스", "하이닉스", "메모리", "DRAM", "NAND"],
        "035420": ["NAVER", "네이버", "검색", "웹툰", "클라우드"],
        "051910": ["LG화학", "화학", "배터리", "이차전지"],
        "035720": ["카카오", "카카오톡", "메신저", "게임", "핀테크"],
        "006400": ["삼성SDI", "SDI", "배터리", "전기차"],
        "028260": ["삼성물산", "물산", "건설", "무역"],
        "096770": ["SK이노베이션", "이노베이션", "정유", "화학"],
        "105560": ["KB금융", "국민은행", "금융지주"],
        "055550": ["신한지주", "신한은행", "금융"],
        "017670": ["SK텔레콤", "SKT", "통신", "5G"],
        "030200": ["KT", "통신", "인터넷"],
        "012330": ["현대모비스", "모비스", "자동차부품"],
        "015760": ["한국전력", "한전", "전력", "전기"],
        "009150": ["삼성전기", "전기", "부품", "MLCC"]
    }
    
    def __init__(self, openai_api_key: str):
        self.openai_client = openai.AsyncOpenAI(api_key=openai_api_key)
        self.session: Optional[aiohttp.ClientSession] = None
        # 한국 뉴스 분석용 최적화기 (5분 캐시 TTL)
        self.openai_optimizer = get_openai_optimizer(daily_budget=2.0)
        # 한국 뉴스 분석용 캐시 TTL을 5분으로 설정
        self.openai_optimizer.cache_ttl = 300  # 5분 = 300초
        
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'StockPilot-KR/1.0'}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self.session:
            await self.session.close()

    def extract_mentioned_symbols(self, title: str, content: str) -> List[str]:
        """뉴스에서 언급된 주식 심볼 추출"""
        mentioned = []
        text = f"{title} {content}".replace(" ", "").upper()
        
        for symbol, keywords in self.STOCK_KEYWORDS.items():
            for keyword in keywords:
                keyword_clean = keyword.replace(" ", "").upper()
                if keyword_clean in text:
                    if symbol not in mentioned:
                        mentioned.append(symbol)
                    break
                    
        return mentioned

    async def analyze_sentiment_with_gpt(self, title: str, content: str) -> Dict[str, Any]:
        """GPT를 사용한 한국 뉴스 감성 분석"""
        try:
            prompt = f"""
            다음 한국 금융/경제 뉴스를 분석해주세요:
            
            제목: {title}
            내용: {content[:500]}...
            
            다음 JSON 형식으로 답변해주세요:
            {{
                "sentiment": "POSITIVE/NEGATIVE/NEUTRAL",
                "sentiment_score": -1.0 ~ 1.0 사이 숫자,
                "impact_score": 0.0 ~ 1.0 사이 숫자 (시장 영향도),
                "topics": ["주요", "토픽", "목록"],
                "reasoning": "분석 근거 (한국어)"
            }}
            
            sentiment_score는 -1.0(매우 부정적) ~ 1.0(매우 긍정적) 사이
            impact_score는 0.0(영향없음) ~ 1.0(큰 영향) 사이
            한국 주식시장과 경제에 미치는 영향을 중점적으로 분석해주세요.
            """
            
            # OpenAI 최적화기 사용 (5분 캐시 + 백오프 + 비용 모니터링)
            response = await self.openai_optimizer.optimize_chat_completion(
                self.openai_client,
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.3
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # JSON 파싱 시도
            try:
                result = json.loads(result_text)
                return {
                    "sentiment": result.get("sentiment", "NEUTRAL"),
                    "sentiment_score": float(result.get("sentiment_score", 0.0)),
                    "impact_score": float(result.get("impact_score", 0.0)),
                    "topics": result.get("topics", []),
                    "reasoning": result.get("reasoning", "")
                }
            except json.JSONDecodeError:
                # JSON 파싱 실패시 기본값
                logger.warning(f"GPT 응답 JSON 파싱 실패: {result_text}")
                return {
                    "sentiment": "NEUTRAL",
                    "sentiment_score": 0.0,
                    "impact_score": 0.0,
                    "topics": [],
                    "reasoning": "분석 오류"
                }
                
        except Exception as e:
            logger.error(f"GPT 감성분석 오류: {e}")
            return {
                "sentiment": "NEUTRAL",
                "sentiment_score": 0.0,
                "impact_score": 0.0,
                "topics": [],
                "reasoning": f"분석 오류: {str(e)}"
            }

    def _generate_mock_news(self, count: int = 5) -> List[Dict[str, Any]]:
        """Mock 한국 뉴스 데이터 생성"""
        import random
        
        mock_titles = [
            "삼성전자, 3분기 반도체 업황 회복으로 실적 개선 전망",
            "SK하이닉스 HBM 메모리 공급 확대로 AI 시장 선점",
            "네이버 클라우드 사업 성장세 지속, 매출 30% 증가",
            "LG화학 전기차 배터리 수주 늘며 주가 상승세",
            "카카오 핀테크 사업 확장, 카카오페이 IPO 추진",
            "현대모비스 자율주행 기술 개발로 미래차 시장 대응",
            "KB금융 디지털 전환 가속화로 수익성 개선",
            "SK텔레콤 5G 가입자 증가로 통신 매출 성장",
            "한국전력 신재생에너지 투자 확대 계획 발표",
            "삼성SDI 배터리 생산능력 확충으로 글로벌 시장 확대"
        ]
        
        mock_sources = ["네이버 경제뉴스", "다음 경제뉴스", "한겨레 경제", "매일경제"]
        
        news_list = []
        for i in range(count):
            title = random.choice(mock_titles)
            sentiment_score = random.uniform(-0.8, 0.8)
            sentiment = "POSITIVE" if sentiment_score > 0.2 else "NEGATIVE" if sentiment_score < -0.2 else "NEUTRAL"
            
            news_item = {
                'title': title,
                'content': f"{title}에 대한 상세 내용입니다. " * 3,
                'url': f"https://news.example.com/article/{i+1}",
                'source': random.choice(mock_sources),
                'published_at': (datetime.now() - timedelta(hours=random.randint(1, 24))).isoformat(),
                'sentiment': sentiment,
                'sentiment_score': sentiment_score,
                'impact_score': random.uniform(0.3, 0.9),
                'weight': 1.0
            }
            news_list.append(news_item)
        
        return news_list

    async def fetch_rss_news(self, source_key: str, limit: int = 10) -> List[Dict[str, Any]]:
        """RSS 피드에서 한국 뉴스 수집"""
        try:
            source = self.NEWS_SOURCES[source_key]
            
            logger.info(f"{source['name']}에서 뉴스 수집 시도 중...")
            
            # Mock 데이터 사용 (실제 RSS 연동 시 주석 해제)
            return self._generate_mock_news(limit)
            
            # TODO: 실제 RSS 연동 구현
            # async with self.session.get(source["rss_url"]) as response:
            #     if response.status != 200:
            #         logger.warning(f"RSS 요청 실패 {source['rss_url']}: {response.status}")
            #         return self._generate_mock_news(limit)
            #     
            #     rss_content = await response.text()
            #     feed = feedparser.parse(rss_content)
            #     # RSS 파싱 및 뉴스 아이템 생성
            
        except Exception as e:
            logger.error(f"RSS 뉴스 수집 오류 {source_key}: {e}")
            return self._generate_mock_news(limit)

    async def analyze_news_item(self, news_data: Dict[str, Any]) -> KRNewsItem:
        """개별 뉴스 아이템 분석"""
        try:
            # 언급된 종목 추출
            symbols = self.extract_mentioned_symbols(news_data['title'], news_data['content'])
            
            # GPT 감성 분석 (Mock 데이터인 경우 기존 값 사용)
            if 'sentiment' in news_data:
                analysis = {
                    "sentiment": news_data['sentiment'],
                    "sentiment_score": news_data['sentiment_score'],
                    "impact_score": news_data['impact_score'],
                    "topics": ["경제", "주식"],
                    "reasoning": "Mock 데이터"
                }
            else:
                analysis = await self.analyze_sentiment_with_gpt(news_data['title'], news_data['content'])
            
            # 고유 ID 생성
            import hashlib
            news_id = hashlib.md5(f"{news_data['url']}{news_data['published_at']}".encode()).hexdigest()
            
            return KRNewsItem(
                id=news_id,
                title=news_data['title'],
                content=news_data['content'],
                summary=news_data['content'][:200] + "..." if len(news_data['content']) > 200 else news_data['content'],
                url=news_data['url'],
                source=news_data['source'],
                published_at=news_data['published_at'],
                symbols_mentioned=symbols,
                sentiment=analysis['sentiment'],
                sentiment_score=analysis['sentiment_score'],
                impact_score=analysis['impact_score'] * news_data.get('weight', 1.0),  # 소스 가중치 적용
                topics=analysis['topics']
            )
            
        except Exception as e:
            logger.error(f"한국 뉴스 분석 오류: {e}")
            # 오류 발생시 기본 뉴스 아이템 반환
            import hashlib
            news_id = hashlib.md5(f"{news_data.get('url', '')}{datetime.now().isoformat()}".encode()).hexdigest()
            
            return KRNewsItem(
                id=news_id,
                title=news_data.get('title', 'Unknown'),
                content=news_data.get('content', ''),
                summary=news_data.get('content', '')[:200],
                url=news_data.get('url', ''),
                source=news_data.get('source', 'Unknown'),
                published_at=news_data.get('published_at', datetime.now().isoformat()),
                symbols_mentioned=[],
                sentiment="NEUTRAL",
                sentiment_score=0.0,
                impact_score=0.0,
                topics=[]
            )

    async def get_latest_kr_news(self, limit: int = 15) -> List[KRNewsItem]:
        """최신 한국 뉴스 수집 및 분석"""
        all_news = []
        
        # 모든 소스에서 뉴스 수집
        for source_key in self.NEWS_SOURCES.keys():
            try:
                source_news = await self.fetch_rss_news(source_key, limit // len(self.NEWS_SOURCES) + 2)
                all_news.extend(source_news)
            except Exception as e:
                logger.error(f"소스 {source_key} 뉴스 수집 실패: {e}")
                continue
        
        if not all_news:
            logger.warning("수집된 한국 뉴스가 없습니다.")
            return []
        
        # 발행일 기준 정렬
        all_news.sort(key=lambda x: x.get('published_at', ''), reverse=True)
        
        # 상위 뉴스만 선택
        top_news = all_news[:limit]
        
        # 병렬로 뉴스 분석
        logger.info(f"{len(top_news)}개 한국 뉴스 AI 분석 중...")
        analysis_tasks = [self.analyze_news_item(news) for news in top_news]
        analyzed_news = await asyncio.gather(*analysis_tasks, return_exceptions=True)
        
        # 성공적으로 분석된 뉴스만 반환
        valid_news = []
        for result in analyzed_news:
            if isinstance(result, KRNewsItem):
                valid_news.append(result)
            elif isinstance(result, Exception):
                logger.error(f"한국 뉴스 분석 실패: {result}")
        
        logger.info(f"{len(valid_news)}개 한국 뉴스 분석 완료")
        return valid_news

    async def get_symbol_news(self, symbol: str, limit: int = 10) -> List[KRNewsItem]:
        """특정 종목 관련 한국 뉴스 조회"""
        all_news = await self.get_latest_kr_news(limit * 2)  # 여유있게 수집
        
        # 해당 종목이 언급된 뉴스만 필터링
        symbol_news = [
            news for news in all_news 
            if symbol in news.symbols_mentioned
        ]
        
        # 영향도 순으로 정렬
        symbol_news.sort(key=lambda x: x.impact_score, reverse=True)
        
        return symbol_news[:limit]

    async def get_comprehensive_kr_data(self) -> Dict[str, Any]:
        """종합 한국 금융 데이터 수집 (뉴스 + 금융감독원 + 증권사)"""
        try:
            logger.info("종합 한국 금융 데이터 수집 시작")
            
            # 금융 데이터 서비스 인스턴스 생성
            financial_service = await create_kr_financial_service()
            
            # 병렬로 모든 데이터 수집
            results = await asyncio.gather(
                self.get_latest_kr_news(15),  # 기존 뉴스
                financial_service.get_comprehensive_kr_data(),  # 금융감독원 + 증권사 데이터
                return_exceptions=True
            )
            
            # 결과 처리
            news_data = results[0] if not isinstance(results[0], Exception) else []
            financial_data = results[1] if not isinstance(results[1], Exception) else {}
            
            # 금융 서비스 정리
            await financial_service.__aexit__(None, None, None)
            
            # 뉴스 데이터 통합
            all_news_items = []
            
            # 기존 뉴스 추가
            for news in news_data:
                all_news_items.append(news.to_dict())
            
            # 금융감독원/증권사 뉴스 추가
            if 'news' in financial_data:
                for news in financial_data['news']:
                    # 중복 제거를 위한 ID 체크
                    existing_ids = [item['id'] for item in all_news_items]
                    if news['id'] not in existing_ids:
                        all_news_items.append(news)
            
            # 발행일 기준 정렬
            all_news_items.sort(key=lambda x: x.get('published_at', ''), reverse=True)
            
            # 최종 응답 구성
            response = {
                "success": True,
                "market_info": financial_data.get('market_info', {}),
                "news": all_news_items[:25],  # 최신 25개
                "market_data": financial_data.get('market_data', []),
                "statistics": {
                    "total_news": len(all_news_items),
                    "traditional_news": len(news_data),
                    "financial_news": len(financial_data.get('news', [])),
                    "market_stocks": len(financial_data.get('market_data', []))
                },
                "data_sources": {
                    "traditional": list(self.NEWS_SOURCES.keys()),
                    "financial": financial_data.get('data_sources', {})
                },
                "generated_at": datetime.now().isoformat()
            }
            
            logger.info(f"종합 한국 데이터 수집 완료: 뉴스 {len(all_news_items)}건, 주식 {len(financial_data.get('market_data', []))}종목")
            return response
            
        except Exception as e:
            logger.error(f"종합 한국 데이터 수집 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "news": [],
                "market_data": [],
                "generated_at": datetime.now().isoformat()
            }

    async def validate_kr_market_data(self) -> Dict[str, Any]:
        """한국 시장 데이터 품질 검증"""
        try:
            logger.info("한국 시장 데이터 품질 검증 시작")
            
            # 금융 데이터 서비스로 시장 데이터 수집
            financial_service = await create_kr_financial_service()
            market_data = await financial_service.fetch_kospi_kosdaq_data()
            await financial_service.__aexit__(None, None, None)
            
            # 검증 메트릭
            validation_results = {
                "total_stocks": len(market_data),
                "kospi_stocks": len([stock for stock in market_data if stock.market == "KOSPI"]),
                "kosdaq_stocks": len([stock for stock in market_data if stock.market == "KOSDAQ"]),
                "data_quality": {
                    "valid_prices": 0,
                    "valid_volumes": 0,
                    "valid_market_caps": 0,
                    "complete_data": 0
                },
                "price_ranges": {
                    "kospi_avg_price": 0,
                    "kosdaq_avg_price": 0,
                    "highest_price": 0,
                    "lowest_price": float('inf')
                },
                "validation_errors": []
            }
            
            for stock in market_data:
                # 가격 유효성 검증
                if stock.current_price > 0:
                    validation_results["data_quality"]["valid_prices"] += 1
                    
                    # 가격 범위 계산
                    if stock.current_price > validation_results["price_ranges"]["highest_price"]:
                        validation_results["price_ranges"]["highest_price"] = stock.current_price
                    if stock.current_price < validation_results["price_ranges"]["lowest_price"]:
                        validation_results["price_ranges"]["lowest_price"] = stock.current_price
                else:
                    validation_results["validation_errors"].append(f"잘못된 가격: {stock.symbol}")
                
                # 거래량 유효성 검증
                if stock.volume > 0:
                    validation_results["data_quality"]["valid_volumes"] += 1
                
                # 시가총액 유효성 검증
                if stock.market_cap > 0:
                    validation_results["data_quality"]["valid_market_caps"] += 1
                
                # 완전한 데이터 확인
                if all([stock.current_price > 0, stock.volume > 0, stock.market_cap > 0]):
                    validation_results["data_quality"]["complete_data"] += 1
            
            # 평균 가격 계산
            kospi_stocks = [s for s in market_data if s.market == "KOSPI"]
            kosdaq_stocks = [s for s in market_data if s.market == "KOSDAQ"]
            
            if kospi_stocks:
                validation_results["price_ranges"]["kospi_avg_price"] = sum(s.current_price for s in kospi_stocks) / len(kospi_stocks)
            
            if kosdaq_stocks:
                validation_results["price_ranges"]["kosdaq_avg_price"] = sum(s.current_price for s in kosdaq_stocks) / len(kosdaq_stocks)
            
            # 품질 점수 계산 (0-100)
            quality_score = 0
            if validation_results["total_stocks"] > 0:
                price_quality = (validation_results["data_quality"]["valid_prices"] / validation_results["total_stocks"]) * 30
                volume_quality = (validation_results["data_quality"]["valid_volumes"] / validation_results["total_stocks"]) * 30
                completeness = (validation_results["data_quality"]["complete_data"] / validation_results["total_stocks"]) * 40
                quality_score = price_quality + volume_quality + completeness
            
            validation_results["quality_score"] = round(quality_score, 2)
            validation_results["validation_status"] = "PASS" if quality_score >= 80 else "WARNING" if quality_score >= 60 else "FAIL"
            validation_results["validated_at"] = datetime.now().isoformat()
            
            logger.info(f"데이터 품질 검증 완료: 점수 {quality_score:.2f}, 상태 {validation_results['validation_status']}")
            return validation_results
            
        except Exception as e:
            logger.error(f"한국 시장 데이터 검증 오류: {e}")
            return {
                "validation_status": "ERROR",
                "error": str(e),
                "validated_at": datetime.now().isoformat()
            }

    async def get_kr_market_calendar(self) -> Dict[str, Any]:
        """한국 시장 휴장일 캘린더 정보"""
        try:
            financial_service = await create_kr_financial_service()
            calendar_info = financial_service.get_market_calendar_info()
            await financial_service.__aexit__(None, None, None)
            
            return calendar_info
            
        except Exception as e:
            logger.error(f"한국 시장 캘린더 조회 오류: {e}")
            return {
                "error": str(e),
                "generated_at": datetime.now().isoformat()
            }

# 테스트 함수
async def test_kr_news_analyzer():
    """한국 뉴스 분석기 테스트"""
    # OpenAI API 키가 필요합니다
    import os
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("OPENAI_API_KEY 환경변수가 필요합니다. Mock 데이터로 테스트합니다.")
        api_key = "mock-key"
    
    async with KRNewsAnalyzer(api_key) as analyzer:
        print("=== 한국 뉴스 분석 서비스 테스트 ===")
        
        # 1. 최신 뉴스 수집
        print("\n1. 최신 한국 뉴스 수집 및 분석:")
        news_list = await analyzer.get_latest_kr_news(5)
        
        for news in news_list:
            print(f"\n제목: {news.title}")
            print(f"소스: {news.source}")
            print(f"감성: {news.sentiment} ({news.sentiment_score:.2f})")
            print(f"영향도: {news.impact_score:.2f}")
            print(f"언급 종목: {', '.join(news.symbols_mentioned) if news.symbols_mentioned else '없음'}")
            print(f"주제: {', '.join(news.topics) if news.topics else '없음'}")
        
        # 2. 삼성전자 관련 뉴스
        print("\n2. 삼성전자(005930) 관련 뉴스:")
        samsung_news = await analyzer.get_symbol_news("005930", 3)
        
        for news in samsung_news:
            print(f"\n제목: {news.title}")
            print(f"감성: {news.sentiment} ({news.sentiment_score:.2f})")
            print(f"영향도: {news.impact_score:.2f}")

if __name__ == "__main__":
    asyncio.run(test_kr_news_analyzer())