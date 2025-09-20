import os
from fastapi import APIRouter, Query
from typing import Any, Dict, List
from .news_score import get_news_score

router = APIRouter(tags=["recommendations"])

TECH_WEIGHT = float(os.getenv("TECH_WEIGHT", "0.7"))
NEWS_WEIGHT = float(os.getenv("NEWS_WEIGHT", "0.3"))
RECOMMEND_THRESHOLD = float(os.getenv("RECOMMEND_THRESHOLD", "2.5"))
WARN_THRESHOLD = float(os.getenv("WARN_THRESHOLD", "-2.5"))

@router.get("/recommendations")
def get_recommendations(
    exchange: str = Query("NASDAQ"),
    limit: int = Query(5, ge=1, le=50)
) -> Dict[str, Any]:
    tech_baseline: Dict[str, float] = {
        "AAPL": 3.2,
        "NVDA": 3.8,
        "TSLA": 2.6,
    }
    candidates: List[str] = list(tech_baseline.keys())
    items: List[Dict[str, Any]] = []
    for symbol in candidates:
        tech = float(tech_baseline.get(symbol, 0.0))
        news = float(get_news_score(symbol))
        final = TECH_WEIGHT * tech + NEWS_WEIGHT * news
        why = [
            f"기술:{tech:.2f}×{TECH_WEIGHT:.1f}",
            f"뉴스:{news:.2f}×{NEWS_WEIGHT:.1f}",
            f"합산:{final:.2f}",
        ]
        if final >= RECOMMEND_THRESHOLD:
            items.append({"symbol": symbol, "score": round(final, 2), "why": why})
    items.sort(key=lambda x: x["score"], reverse=True)
    items = items[:limit]
    return {
        "ok": True,
        "exchange": exchange,
        "items": items,
        "meta": {
            "tech_weight": TECH_WEIGHT,
            "news_weight": NEWS_WEIGHT,
            "recommend_threshold": RECOMMEND_THRESHOLD,
            "warn_threshold": WARN_THRESHOLD,
            "mode": "TECH+NEWS",
        },
    }