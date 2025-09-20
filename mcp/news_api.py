from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Dict
from .news_score import upsert_news_score, get_news_score

router = APIRouter(tags=["news"])

class UpsertReq(BaseModel):
    symbol: str = Field(..., description="티커 (예: AAPL)")
    score: float = Field(..., ge=-5.0, le=5.0, description="뉴스 점수(내부 척도)")

@router.post("/upsert")
def upsert_news(req: UpsertReq) -> Dict:
    upsert_news_score(req.symbol, req.score)
    return {"ok": True, "symbol": req.symbol.upper(), "score": float(req.score)}

@router.get("/impact")
def impact(symbol: str) -> Dict:
    return {"ok": True, "symbol": symbol.upper(), "score": float(get_news_score(symbol))}
