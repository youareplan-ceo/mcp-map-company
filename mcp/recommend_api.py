from fastapi import APIRouter, Query
from typing import List, Dict, Any
from .news_score import get_news_score

router = APIRouter(prefix="/api/v1", tags=["recommendations"])

@router.get("/stock/recommendations")
def get_recommendations(
    exchange: str = Query("NASDAQ"),
    limit: int = Query(10, ge=1, le=50),
    tech_weight: float = 0.7,
    news_weight: float = 0.3,
    recommend_threshold: float = 2.5,
    warn_threshold: float = -2.5,
) -> Dict[str, Any]:
    """
    뼈대만: 지금은 실제 계산 없이 빈 리스트(또는 목업) 반환.
    다음 배치에서: 기존 기술점수 + get_news_score(symbol) 결합해 상위 N개만 리턴.
    """
    return {
        "ok": True,
        "exchange": exchange,
        "items": [],  # 다음 배치에서 채움
        "meta": {
            "tech_weight": tech_weight,
            "news_weight": news_weight,
            "recommend_threshold": recommend_threshold,
            "warn_threshold": warn_threshold,
        },
    }
