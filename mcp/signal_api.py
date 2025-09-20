from fastapi import APIRouter, Query
from typing import Any, Dict, List

router = APIRouter(prefix="/api/v1", tags=["signals"])

@router.get("/stock/signals")
def get_signals(
    exchange: str = Query("NASDAQ"),
    limit: int = Query(40, ge=1, le=500),
    batch_size: int = Query(40, ge=1, le=500),
) -> Dict[str, Any]:
    """
    임시 스텁: 서버 기동을 위해 최소 형태만 반환.
    추후 실제 엔진 결과로 교체.
    """
    return {
        "ok": True,
        "exchange": exchange,
        "limit": limit,
        "batch_size": batch_size,
        "summary": {"buy": 0, "sell": 0, "hold": 0, "reasons": {}, "duration_ms": 0, "mode": "STUB"},
        "items": [],  # 실제 신호 리스트는 다음 배치에서 연결
    }
