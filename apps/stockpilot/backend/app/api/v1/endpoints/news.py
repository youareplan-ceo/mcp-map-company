"""
뉴스 및 감정 분석 관련 API 엔드포인트
주식 관련 뉴스 수집, AI 감정 분석, 시장 영향도 평가
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from loguru import logger

from app.models import (
    NewsArticle, NewsSentiment, NewsCategory, TrendingKeyword,
    PaginatedResponse, NewsRequest
)
from app.config import get_settings
from app.services.news_service import NewsService

router = APIRouter()
settings = get_settings()


@router.get("/", response_model=PaginatedResponse)
async def get_news(
    category: Optional[NewsCategory] = Query(None, description="뉴스 카테고리"),
    sentiment: Optional[NewsSentiment] = Query(None, description="감정 분석 결과"),
    symbols: Optional[str] = Query(None, description="관련 종목 (쉼표로 구분)"),
    sources: Optional[str] = Query(None, description="뉴스 소스 (쉼표로 구분)"),
    keywords: Optional[str] = Query(None, description="키워드 검색 (쉼표로 구분)"),
    hours: int = Query(default=24, ge=1, le=168, description="최근 몇 시간"),
    min_impact: Optional[float] = Query(None, ge=0, le=10, description="최소 영향도 점수"),
    page: int = Query(default=1, ge=1, description="페이지 번호"),
    size: int = Query(default=20, ge=1, le=100, description="페이지 크기")
) -> PaginatedResponse:
    """
    뉴스 목록 조회
    카테고리, 감정, 관련 종목별 필터링 지원
    """
    try:
        logger.info(f"뉴스 조회 - 카테고리: {category}, 감정: {sentiment}, 기간: {hours}시간")
        
        # 필터 파라미터 파싱
        symbol_list = None
        if symbols:
            symbol_list = [s.strip() for s in symbols.split(",")]
        
        source_list = None
        if sources:
            source_list = [s.strip() for s in sources.split(",")]
        
        keyword_list = None
        if keywords:
            keyword_list = [k.strip() for k in keywords.split(",")]
        
        news_service = NewsService()
        result = await news_service.get_news(
            category=category,
            sentiment=sentiment,
            symbols=symbol_list,
            sources=source_list,
            keywords=keyword_list,
            hours=hours,
            min_impact=min_impact,
            page=page,
            size=size
        )
        
        logger.info(f"뉴스 {len(result.data)}개 반환 (전체 {result.total}개)")
        return result
        
    except Exception as e:
        logger.error(f"뉴스 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"뉴스 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/{news_id}", response_model=NewsArticle)
async def get_news_detail(news_id: str) -> NewsArticle:
    """
    특정 뉴스 상세 정보 조회
    """
    try:
        logger.info(f"뉴스 상세 조회: {news_id}")
        
        news_service = NewsService()
        article = await news_service.get_news_by_id(news_id)
        
        if not article:
            raise HTTPException(status_code=404, detail=f"뉴스를 찾을 수 없습니다: {news_id}")
        
        return article
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"뉴스 상세 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"뉴스 상세 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/sentiment/analysis")
async def get_sentiment_analysis(
    symbol: Optional[str] = Query(None, description="특정 종목 분석"),
    hours: int = Query(default=24, ge=1, le=168, description="분석 기간")
):
    """
    감정 분석 요약
    특정 종목 또는 전체 시장의 뉴스 감정 분석 결과
    """
    try:
        logger.info(f"감정 분석 요약 - 종목: {symbol}, 기간: {hours}시간")
        
        news_service = NewsService()
        sentiment_summary = await news_service.get_sentiment_analysis(
            symbol=symbol,
            hours=hours
        )
        
        return {
            "symbol": symbol,
            "period_hours": hours,
            "sentiment_summary": sentiment_summary,
            "generated_at": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"감정 분석 요약 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"감정 분석 요약 중 오류가 발생했습니다: {str(e)}")


@router.get("/impact/high", response_model=List[NewsArticle])
async def get_high_impact_news(
    hours: int = Query(default=24, ge=1, le=168, description="조회 기간"),
    min_score: float = Query(default=7.0, ge=0, le=10, description="최소 영향도 점수"),
    limit: int = Query(default=20, ge=1, le=50, description="최대 결과 수")
) -> List[NewsArticle]:
    """
    고영향도 뉴스 조회
    시장에 큰 영향을 줄 수 있는 중요 뉴스
    """
    try:
        logger.info(f"고영향도 뉴스 조회 - 기간: {hours}시간, 최소점수: {min_score}")
        
        news_service = NewsService()
        high_impact_news = await news_service.get_high_impact_news(
            hours=hours,
            min_score=min_score,
            limit=limit
        )
        
        logger.info(f"고영향도 뉴스 {len(high_impact_news)}개 반환")
        return high_impact_news
        
    except Exception as e:
        logger.error(f"고영향도 뉴스 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"고영향도 뉴스 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/trending/keywords", response_model=List[TrendingKeyword])
async def get_trending_keywords(
    hours: int = Query(default=24, ge=1, le=168, description="분석 기간"),
    limit: int = Query(default=20, ge=1, le=100, description="최대 키워드 수")
) -> List[TrendingKeyword]:
    """
    트렌딩 키워드 조회
    최근 뉴스에서 자주 등장하는 키워드
    """
    try:
        logger.info(f"트렌딩 키워드 조회 - 기간: {hours}시간")
        
        news_service = NewsService()
        trending_keywords = await news_service.get_trending_keywords(
            hours=hours,
            limit=limit
        )
        
        return trending_keywords
        
    except Exception as e:
        logger.error(f"트렌딩 키워드 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"트렌딩 키워드 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/summary/{symbol}")
async def get_news_summary(
    symbol: str,
    hours: int = Query(default=24, ge=1, le=168, description="요약 기간")
):
    """
    종목별 뉴스 요약
    특정 종목 관련 뉴스의 AI 요약
    """
    try:
        logger.info(f"뉴스 요약 생성 - 종목: {symbol}, 기간: {hours}시간")
        
        news_service = NewsService()
        summary = await news_service.generate_news_summary(
            symbol=symbol,
            hours=hours
        )
        
        return {
            "symbol": symbol,
            "period_hours": hours,
            "summary": summary,
            "generated_at": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"뉴스 요약 생성 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"뉴스 요약 생성 중 오류가 발생했습니다: {str(e)}")


@router.get("/sources/")
async def get_news_sources():
    """
    뉴스 소스 목록 조회
    지원하는 뉴스 제공업체 목록
    """
    try:
        logger.info("뉴스 소스 목록 조회")
        
        news_service = NewsService()
        sources = await news_service.get_news_sources()
        
        return {
            "sources": sources,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"뉴스 소스 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"뉴스 소스 조회 중 오류가 발생했습니다: {str(e)}")


@router.post("/analyze")
async def analyze_custom_text(
    text: str,
    context: Optional[str] = None
):
    """
    사용자 제공 텍스트 감정 분석
    """
    try:
        logger.info("사용자 텍스트 감정 분석")
        
        news_service = NewsService()
        analysis = await news_service.analyze_text_sentiment(
            text=text,
            context=context
        )
        
        return {
            "text": text[:100] + "..." if len(text) > 100 else text,
            "context": context,
            "analysis": analysis,
            "analyzed_at": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"텍스트 감정 분석 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"텍스트 감정 분석 중 오류가 발생했습니다: {str(e)}")


@router.get("/market/sentiment")
async def get_market_sentiment(
    market: Optional[str] = Query(None, description="시장 구분 (KOSPI, KOSDAQ)"),
    hours: int = Query(default=24, ge=1, le=168, description="분석 기간")
):
    """
    전체 시장 감정 지수
    시장 전체의 뉴스 감정 분석 결과
    """
    try:
        logger.info(f"시장 감정 지수 조회 - 시장: {market}, 기간: {hours}시간")
        
        news_service = NewsService()
        market_sentiment = await news_service.get_market_sentiment(
            market=market,
            hours=hours
        )
        
        return {
            "market": market,
            "period_hours": hours,
            "sentiment_index": market_sentiment,
            "generated_at": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"시장 감정 지수 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"시장 감정 지수 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/categories/")
async def get_news_categories():
    """
    뉴스 카테고리 목록
    지원하는 뉴스 카테고리 및 설명
    """
    try:
        categories = [
            {
                "code": "MARKET",
                "name": "시장동향",
                "description": "전반적인 주식시장 동향 및 지수 관련 뉴스"
            },
            {
                "code": "ECONOMY",
                "name": "경제",
                "description": "경제 정책, 금리, 환율 등 거시경제 뉴스"
            },
            {
                "code": "CORPORATE",
                "name": "기업",
                "description": "개별 기업의 실적, 사업 전략, IR 관련 뉴스"
            },
            {
                "code": "POLICY",
                "name": "정책",
                "description": "정부 정책, 규제 변화 등 정책 관련 뉴스"
            },
            {
                "code": "INTERNATIONAL",
                "name": "해외",
                "description": "해외 시장 동향 및 국제 경제 뉴스"
            }
        ]
        
        return {
            "categories": categories,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"뉴스 카테고리 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"뉴스 카테고리 조회 중 오류가 발생했습니다: {str(e)}")