"""
뉴스 및 감정 분석 서비스
주식 관련 뉴스 수집 및 AI 감정 분석
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from loguru import logger
import uuid

from app.models import (
    NewsArticle, NewsSentiment, NewsCategory, TrendingKeyword,
    PaginatedResponse, StockInfo, MarketType
)
from app.config import get_settings

settings = get_settings()


class NewsService:
    """뉴스 및 감정 분석 서비스"""
    
    def __init__(self):
        # 샘플 뉴스 데이터 생성
        self.sample_news = self._generate_sample_news()
        logger.info("뉴스 서비스 초기화 완료")
    
    def _generate_sample_news(self) -> List[NewsArticle]:
        """샘플 뉴스 데이터 생성"""
        sample_data = [
            {
                "title": "삼성전자, 3분기 실적 발표... 반도체 부문 회복세",
                "summary": "삼성전자가 3분기 실적에서 메모리 반도체 가격 상승으로 수익성이 개선되었다고 발표했습니다.",
                "category": NewsCategory.CORPORATE,
                "sentiment": NewsSentiment.POSITIVE,
                "sentiment_score": 0.7,
                "related_stocks": [("005930.KS", "삼성전자")],
                "impact_score": 8.5
            },
            {
                "title": "한국은행, 기준금리 동결... 경제성장률 전망 하향",
                "summary": "한국은행이 기준금리를 현 수준으로 유지하며 경제성장률 전망을 하향 조정했습니다.",
                "category": NewsCategory.POLICY,
                "sentiment": NewsSentiment.NEGATIVE,
                "sentiment_score": -0.4,
                "related_stocks": [],
                "impact_score": 9.0
            },
            {
                "title": "2차전지 관련주 급등... LG화학·삼성SDI 상승세",
                "summary": "전기차 시장 성장 기대감으로 2차전지 관련주들이 강세를 보이고 있습니다.",
                "category": NewsCategory.MARKET,
                "sentiment": NewsSentiment.POSITIVE,
                "sentiment_score": 0.8,
                "related_stocks": [("051910.KS", "LG화학"), ("006400.KS", "삼성SDI")],
                "impact_score": 7.5
            }
        ]
        
        articles = []
        for i, data in enumerate(sample_data):
            related_stocks = []
            for symbol, name in data.get("related_stocks", []):
                stock_info = StockInfo(
                    symbol=symbol,
                    name=name,
                    market=MarketType.KOSPI,
                    sector="Technology"
                )
                related_stocks.append(stock_info)
            
            article = NewsArticle(
                id=str(uuid.uuid4()),
                title=data["title"],
                summary=data["summary"],
                url=f"https://example.com/news/{i+1}",
                source="샘플뉴스",
                published_at=datetime.now() - timedelta(hours=i),
                sentiment=data["sentiment"],
                sentiment_score=data["sentiment_score"],
                category=data["category"],
                related_stocks=related_stocks,
                impact_score=data["impact_score"],
                keywords=[]
            )
            articles.append(article)
        
        return articles
    
    async def get_news(
        self,
        category: Optional[NewsCategory] = None,
        sentiment: Optional[NewsSentiment] = None,
        symbols: Optional[List[str]] = None,
        sources: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        hours: int = 24,
        min_impact: Optional[float] = None,
        page: int = 1,
        size: int = 20
    ) -> PaginatedResponse:
        """뉴스 목록 조회"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            filtered_news = [
                article for article in self.sample_news
                if article.published_at >= cutoff_time
            ]
            
            if category:
                filtered_news = [a for a in filtered_news if a.category == category]
            
            if sentiment:
                filtered_news = [a for a in filtered_news if a.sentiment == sentiment]
            
            if symbols:
                filtered_news = [
                    a for a in filtered_news
                    if any(stock.symbol in symbols for stock in a.related_stocks)
                ]
            
            if min_impact:
                filtered_news = [
                    a for a in filtered_news
                    if a.impact_score and a.impact_score >= min_impact
                ]
            
            total = len(filtered_news)
            start_idx = (page - 1) * size
            end_idx = start_idx + size
            paginated_news = filtered_news[start_idx:end_idx]
            
            return PaginatedResponse(
                data=paginated_news,
                total=total,
                page=page,
                size=size,
                has_next=end_idx < total
            )
            
        except Exception as e:
            logger.error(f"뉴스 조회 오류: {str(e)}")
            return PaginatedResponse(data=[], total=0, page=page, size=size)
    
    async def get_stock_related_news(self, symbol: str, hours: int = 24) -> List[Dict[str, Any]]:
        """종목 관련 뉴스 조회"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        related_news = [
            {
                "title": article.title,
                "summary": article.summary,
                "sentiment": article.sentiment.value,
                "sentiment_score": article.sentiment_score
            }
            for article in self.sample_news
            if (article.published_at >= cutoff_time and 
                any(stock.symbol == symbol for stock in article.related_stocks))
        ]
        
        return related_news