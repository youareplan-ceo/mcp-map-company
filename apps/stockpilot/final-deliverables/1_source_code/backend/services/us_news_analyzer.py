"""
미국 시장 뉴스 수집 및 AI 감성 분석 서비스
Reuters, Yahoo Finance 등 미국 뉴스 소스에서 데이터 수집
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

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class USNewsItem:
    """미국 뉴스 아이템 클래스"""
    id: str
    title: str
    content: str
    summary: str
    url: str
    source: str
    published_at: str
    symbols_mentioned: List[str]
    sentiment: str  # POSITIVE, NEGATIVE, NEUTRAL
    sentiment_score: float  # -1.0 ~ 1.0
    impact_score: float  # 0.0 ~ 1.0 (시장 영향도)
    topics: List[str]  # 주요 토픽들
    language: str = "en"
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return asdict(self)

class USNewsAnalyzer:
    """미국 뉴스 수집 및 분석 서비스"""
    
    # 미국 뉴스 소스 RSS 피드
    NEWS_SOURCES = {
        "yahoo_finance": {
            "name": "Yahoo Finance",
            "rss_url": "https://feeds.finance.yahoo.com/rss/2.0/headline",
            "weight": 0.8
        },
        "reuters_business": {
            "name": "Reuters Business",
            "rss_url": "http://feeds.reuters.com/reuters/businessNews",
            "weight": 0.9
        },
        "reuters_markets": {
            "name": "Reuters Markets",
            "rss_url": "http://feeds.reuters.com/reuters/marketsNews",
            "weight": 0.9
        },
        "cnbc": {
            "name": "CNBC",
            "rss_url": "https://feeds.nbcnews.com/feeds/topstories",
            "weight": 0.7
        }
    }
    
    # 주요 미국 종목 키워드 매핑
    STOCK_KEYWORDS = {
        "AAPL": ["Apple", "iPhone", "iPad", "Mac", "Tim Cook"],
        "MSFT": ["Microsoft", "Windows", "Azure", "Office", "Satya Nadella"],
        "GOOGL": ["Google", "Alphabet", "YouTube", "Android", "Sundar Pichai"],
        "AMZN": ["Amazon", "AWS", "Prime", "Bezos", "Andy Jassy"],
        "TSLA": ["Tesla", "Elon Musk", "Model 3", "Model Y", "Cybertruck", "SpaceX"],
        "META": ["Meta", "Facebook", "Instagram", "WhatsApp", "Mark Zuckerberg"],
        "NVDA": ["NVIDIA", "AI chips", "GPU", "Jensen Huang", "data center"],
        "NFLX": ["Netflix", "streaming", "Reed Hastings"],
    }
    
    def __init__(self, openai_api_key: str):
        self.openai_client = openai.AsyncOpenAI(api_key=openai_api_key)
        self.session: Optional[aiohttp.ClientSession] = None
        # 뉴스 분석용 최적화기 (5분 캐시 TTL)
        self.openai_optimizer = get_openai_optimizer(daily_budget=3.0)
        # 뉴스 분석용 캐시 TTL을 5분으로 설정
        self.openai_optimizer.cache_ttl = 300  # 5분 = 300초
        
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'StockPilot-AI/1.0'}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self.session:
            await self.session.close()

    def extract_mentioned_symbols(self, title: str, content: str) -> List[str]:
        """뉴스에서 언급된 주식 심볼 추출"""
        mentioned = []
        text = f"{title} {content}".upper()
        
        for symbol, keywords in self.STOCK_KEYWORDS.items():
            for keyword in keywords:
                if keyword.upper() in text:
                    if symbol not in mentioned:
                        mentioned.append(symbol)
                    break
                    
        return mentioned

    async def analyze_sentiment_with_gpt(self, title: str, content: str) -> Dict[str, Any]:
        """GPT를 사용한 뉴스 감성 분석"""
        try:
            prompt = f"""
            다음 영어 금융 뉴스를 분석해주세요:
            
            제목: {title}
            내용: {content[:500]}...
            
            다음 JSON 형식으로 답변해주세요:
            {{
                "sentiment": "POSITIVE/NEGATIVE/NEUTRAL",
                "sentiment_score": -1.0 ~ 1.0 사이 숫자,
                "impact_score": 0.0 ~ 1.0 사이 숫자 (시장 영향도),
                "topics": ["주요", "토픽", "목록"],
                "reasoning": "분석 근거"
            }}
            
            sentiment_score는 -1.0(매우 부정적) ~ 1.0(매우 긍정적) 사이
            impact_score는 0.0(영향없음) ~ 1.0(큰 영향) 사이
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

    async def fetch_rss_news(self, source_key: str, limit: int = 10) -> List[Dict[str, Any]]:
        """RSS 피드에서 뉴스 수집"""
        try:
            source = self.NEWS_SOURCES[source_key]
            rss_url = source["rss_url"]
            
            logger.info(f"{source['name']}에서 뉴스 수집 중...")
            
            async with self.session.get(rss_url) as response:
                if response.status != 200:
                    logger.warning(f"RSS 요청 실패 {rss_url}: {response.status}")
                    return []
                
                rss_content = await response.text()
                
            # RSS 파싱
            feed = feedparser.parse(rss_content)
            news_items = []
            
            for entry in feed.entries[:limit]:
                try:
                    # 기본 정보 추출
                    title = entry.get('title', '')
                    link = entry.get('link', '')
                    summary = entry.get('summary', '')
                    published = entry.get('published', '')
                    
                    # HTML 태그 제거
                    content = BeautifulSoup(summary, 'html.parser').get_text()
                    
                    # 발행일 파싱
                    try:
                        if published:
                            from dateutil.parser import parse
                            published_dt = parse(published)
                            published_iso = published_dt.isoformat()
                        else:
                            published_iso = datetime.now().isoformat()
                    except:
                        published_iso = datetime.now().isoformat()
                    
                    news_items.append({
                        'title': title,
                        'content': content,
                        'url': link,
                        'source': source['name'],
                        'published_at': published_iso,
                        'weight': source['weight']
                    })
                    
                except Exception as e:
                    logger.warning(f"뉴스 아이템 파싱 오류: {e}")
                    continue
                    
            logger.info(f"{source['name']}에서 {len(news_items)}개 뉴스 수집 완료")
            return news_items
            
        except Exception as e:
            logger.error(f"RSS 뉴스 수집 오류 {source_key}: {e}")
            return []

    async def analyze_news_item(self, news_data: Dict[str, Any]) -> USNewsItem:
        """개별 뉴스 아이템 분석"""
        try:
            # 언급된 종목 추출
            symbols = self.extract_mentioned_symbols(news_data['title'], news_data['content'])
            
            # GPT 감성 분석
            analysis = await self.analyze_sentiment_with_gpt(news_data['title'], news_data['content'])
            
            # 고유 ID 생성
            import hashlib
            news_id = hashlib.md5(f"{news_data['url']}{news_data['published_at']}".encode()).hexdigest()
            
            return USNewsItem(
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
            logger.error(f"뉴스 분석 오류: {e}")
            # 오류 발생시 기본 뉴스 아이템 반환
            import hashlib
            news_id = hashlib.md5(f"{news_data.get('url', '')}{datetime.now().isoformat()}".encode()).hexdigest()
            
            return USNewsItem(
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

    async def get_latest_us_news(self, limit: int = 20) -> List[USNewsItem]:
        """최신 미국 뉴스 수집 및 분석"""
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
            logger.warning("수집된 뉴스가 없습니다.")
            return []
        
        # 발행일 기준 정렬
        all_news.sort(key=lambda x: x.get('published_at', ''), reverse=True)
        
        # 상위 뉴스만 선택
        top_news = all_news[:limit]
        
        # 병렬로 뉴스 분석
        logger.info(f"{len(top_news)}개 뉴스 AI 분석 중...")
        analysis_tasks = [self.analyze_news_item(news) for news in top_news]
        analyzed_news = await asyncio.gather(*analysis_tasks, return_exceptions=True)
        
        # 성공적으로 분석된 뉴스만 반환
        valid_news = []
        for result in analyzed_news:
            if isinstance(result, USNewsItem):
                valid_news.append(result)
            elif isinstance(result, Exception):
                logger.error(f"뉴스 분석 실패: {result}")
        
        logger.info(f"{len(valid_news)}개 뉴스 분석 완료")
        return valid_news

    async def get_symbol_news(self, symbol: str, limit: int = 10) -> List[USNewsItem]:
        """특정 종목 관련 뉴스 조회"""
        all_news = await self.get_latest_us_news(limit * 3)  # 여유있게 수집
        
        # 해당 종목이 언급된 뉴스만 필터링
        symbol_news = [
            news for news in all_news 
            if symbol in news.symbols_mentioned
        ]
        
        # 영향도 순으로 정렬
        symbol_news.sort(key=lambda x: x.impact_score, reverse=True)
        
        return symbol_news[:limit]

# 테스트 함수
async def test_us_news_analyzer():
    """미국 뉴스 분석기 테스트"""
    # OpenAI API 키가 필요합니다
    import os
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("OPENAI_API_KEY 환경변수가 필요합니다.")
        return
    
    async with USNewsAnalyzer(api_key) as analyzer:
        print("=== 미국 뉴스 분석 서비스 테스트 ===")
        
        # 1. 최신 뉴스 수집
        print("\n1. 최신 미국 뉴스 수집 및 분석:")
        news_list = await analyzer.get_latest_us_news(5)
        
        for news in news_list:
            print(f"\n제목: {news.title}")
            print(f"소스: {news.source}")
            print(f"감성: {news.sentiment} ({news.sentiment_score:.2f})")
            print(f"영향도: {news.impact_score:.2f}")
            print(f"언급 종목: {', '.join(news.symbols_mentioned) if news.symbols_mentioned else '없음'}")
            print(f"주제: {', '.join(news.topics) if news.topics else '없음'}")
        
        # 2. 애플 관련 뉴스
        print("\n2. AAPL 관련 뉴스:")
        aapl_news = await analyzer.get_symbol_news("AAPL", 3)
        
        for news in aapl_news:
            print(f"\n제목: {news.title}")
            print(f"감성: {news.sentiment} ({news.sentiment_score:.2f})")
            print(f"영향도: {news.impact_score:.2f}")

if __name__ == "__main__":
    asyncio.run(test_us_news_analyzer())