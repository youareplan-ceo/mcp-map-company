# mcp/run.py
"""
Thin MCP Flow Runner + FastAPI entrypoint (Render/Local compatible)

- FastAPI 앱: /health, /api/v1/ai/signals (더미 데이터) 제공
- CORS 허용: Vercel(프론트)에서 Render(백엔드) 호출 가능
- 로컬 실행: uvicorn으로 바로 구동
- (옵션) 간단한 flow 실행 스텁 run_flow() 포함
"""
from __future__ import annotations

import os
import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------
# Logging
# ---------------------------------
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("mcp.run")

# ---------------------------------
# FastAPI (Render entrypoint)
# ---------------------------------
app = FastAPI(title="mcp-map-company", version="0.2.0")

# CORS (Vercel 등 프론트에서 호출 허용)
# 필요 시 allow_origins=["https://mcp-map.vercel.app"] 처럼 도메인 제한 가능
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 초기 개발 단계는 * 허용. 운영 전 도메인 고정 권장.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------
# Schemas
# ---------------------------------
class Signal(BaseModel):
    symbol: str
    action: str  # "buy" | "sell" | "hold" 등
    message: Optional[str] = None
    quantity: Optional[float] = None
    price: Optional[float] = None

class Recommendation(BaseModel):
    type: str
    symbol: str
    reason: Optional[str] = None
    currentPrice: Optional[float] = None
    targetPrice: Optional[float] = None
    action: Optional[str] = None

class Portfolio(BaseModel):
    totalValue: float
    profit: float
    profitPercentage: float
    stockCount: int
    cashRatio: float
    monthlyReturn: float
    riskLevel: str

class SignalsResponse(BaseModel):
    portfolio: Portfolio
    signals: List[Signal]
    recommendations: List[Recommendation]

# ---------------------------------
# Health & Meta
# ---------------------------------
@app.get("/health")
def health() -> Dict[str, Any]:
    return {"ok": True}

@app.get("/")
def root() -> Dict[str, Any]:
    return {
        "service": "mcp-map-company",
        "version": app.version,
        "endpoints": ["/health", "/api/v1/ai/signals"],
    }

# ---------------------------------
# Signals (stub data for UI)
# ---------------------------------
@app.get("/api/v1/ai/signals", response_model=SignalsResponse)
def get_signals() -> Dict[str, Any]:
    """
    프론트(UI) 연결 확인용 더미 시그널 응답.
    실제 연동 시 여기에 실시간 계산/MCP 호출/DB 조회 등을 붙이면 됩니다.
    """
    data = {
        "portfolio": {
            "totalValue": 120_000_000,
            "profit": 24_000_000,
            "profitPercentage": 25.0,
            "stockCount": 12,
            "cashRatio": 15,
            "monthlyReturn": 8.5,
            "riskLevel": "중간",
        },
        "signals": [
            {"symbol": "AAPL", "action": "buy",  "message": "추세 개선",     "quantity": 3, "price": 180.5},
            {"symbol": "MSFT", "action": "sell", "message": "차익 실현 검토", "quantity": 2, "price": 410.2},
        ],
        "recommendations": [
            {
                "type": "hold",
                "symbol": "AAPL",
                "reason": "모멘텀 양호",
                "currentPrice": 180.5,
                "targetPrice": 200.0,
                "action": "보유 지속",
            }
        ],
    }
    return data

# ---------------------------------
# (옵션) 매우 단순한 Flow Runner 스텁
# ---------------------------------
def run_flow(flow_path: str) -> None:
    """
    .flow YAML을 읽어 steps 나열 정도만 수행(실행은 추후 확장)
    운영용이 아니라, 구조 확인/확장 포인트만 남겨둠.
    """
    try:
        import yaml  # lazy import
    except Exception:
        log.warning("PyYAML 미설치. `pip install pyyaml` 하면 flow 파싱 가능.")
        return

    from pathlib import Path
    p = Path(flow_path)
    if not p.exists():
        log.error("flow 파일이 없음: %s", p)
        return

    with p.open("r", encoding="utf-8") as f:
        spec = yaml.safe_load(f) or {}

    name = spec.get("name", p.stem)
    steps = spec.get("steps", [])
    log.info("Flow: %s (총 %d steps)", name, len(steps))
    for i, step in enumerate(steps, 1):
        log.info("  %d) %s", i, json.dumps(step, ensure_ascii=False))

# ---------------------------------
# Local run
# ---------------------------------
if __name__ == "__main__":
    # 로컬 실행 시: uvicorn으로 서버 구동
    import uvicorn
    port = int(os.getenv("PORT", "8088"))  # Render는 PORT를 주입, 로컬은 8088 기본
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
