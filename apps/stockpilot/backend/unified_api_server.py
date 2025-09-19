#!/usr/bin/env python3
import os
import logging
from datetime import datetime
import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
from dotenv import load_dotenv
import uvicorn

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="StockPilot AI Analysis API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WATCHLIST = {
    "US": ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"],
    "KR": ["005930.KS", "000660.KS", "035420.KS", "035720.KS"],
}

class ConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

@app.get("/")
async def root():
    return {
        "service": "StockPilot AI Analysis",
        "status": "running",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/stocks/{symbol}")
async def get_stock_analysis(symbol: str):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        history = ticker.history(period="1d")
        
        if history.empty:
            return {"error": "No data", "symbol": symbol}
        
        current_price = float(history['Close'].iloc[-1])
        
        return {
            "symbol": symbol,
            "name": info.get('longName', symbol),
            "price": current_price,
            "previousClose": info.get('previousClose', 0),
            "dayHigh": float(history['High'].max()),
            "dayLow": float(history['Low'].min()),
            "volume": int(history['Volume'].iloc[-1]),
            "timestamp": datetime.now().isoformat(),
            "disclaimer": "본 정보는 투자 참고 자료이며, 투자 결정은 이용자 책임입니다"
        }
    except Exception as e:
        return {"error": str(e), "symbol": symbol}

@app.get("/api/watchlist")
async def get_watchlist():
    result = {"US": [], "KR": []}
    
    for market, symbols in WATCHLIST.items():
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                history = ticker.history(period="1d")
                
                if not history.empty:
                    current_price = float(history['Close'].iloc[-1])
                    prev_close = info.get('previousClose', current_price)
                    change_percent = ((current_price - prev_close) / prev_close * 100) if prev_close else 0
                    
                    result[market].append({
                        "symbol": symbol,
                        "name": info.get('longName', symbol),
                        "price": current_price,
                        "changePercent": change_percent,
                        "disclaimer": "본 정보는 투자 참고 자료이며, 투자 결정은 이용자 책임입니다"
                    })
            except:
                pass
    
    return result

@app.get("/api/analysis/{symbol}")
async def get_analysis(symbol: str):
    """AI 기반 기술적 분석 제공 (투자 권유 아님)"""
    try:
        ticker = yf.Ticker(symbol)
        history = ticker.history(period="30d")

        if history.empty:
            return {"error": "분석 데이터 없음", "symbol": symbol}

        # 기술적 지표 계산
        recent_price = float(history['Close'].iloc[-1])
        avg_price = float(history['Close'].mean())

        # 단순한 분석 신호 생성
        if recent_price > avg_price * 1.05:
            signal_type = "상승 신호"
            signal_strength = "강함"
        elif recent_price < avg_price * 0.95:
            signal_type = "하락 신호"
            signal_strength = "주의"
        else:
            signal_type = "중립 신호"
            signal_strength = "보통"

        return {
            "symbol": symbol,
            "analysis_type": signal_type,
            "signal_strength": signal_strength,
            "current_price": recent_price,
            "resistance_level": recent_price * 1.1,  # 저항선
            "support_level": recent_price * 0.9,     # 지지선
            "timestamp": datetime.now().isoformat(),
            "disclaimer": "본 정보는 투자 참고 자료이며, 투자 결정은 이용자 책임입니다"
        }
    except Exception as e:
        return {"error": str(e), "symbol": symbol, "disclaimer": "본 정보는 투자 참고 자료이며, 투자 결정은 이용자 책임입니다"}

@app.get("/api/signals")
async def get_market_signals():
    """시장 전체 분석 신호 제공"""
    signals = []

    for market, symbols in WATCHLIST.items():
        for symbol in symbols[:3]:  # 각 시장에서 3개만
            try:
                ticker = yf.Ticker(symbol)
                history = ticker.history(period="5d")

                if not history.empty:
                    recent_price = float(history['Close'].iloc[-1])
                    prev_price = float(history['Close'].iloc[-2]) if len(history) > 1 else recent_price

                    change_pct = ((recent_price - prev_price) / prev_price * 100) if prev_price else 0

                    if abs(change_pct) > 2:  # 2% 이상 변동시만 신호 생성
                        signal_type = "상승 지표" if change_pct > 0 else "하락 지표"
                        signals.append({
                            "symbol": symbol,
                            "signal": signal_type,
                            "change_percent": round(change_pct, 2),
                            "current_price": recent_price
                        })
            except:
                continue

    return {
        "signals": signals,
        "total_count": len(signals),
        "timestamp": datetime.now().isoformat(),
        "disclaimer": "본 정보는 투자 참고 자료이며, 투자 결정은 이용자 책임입니다"
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.on_event("startup")
async def startup_event():
    logger.info("StockPilot AI Analysis Server Started")

if __name__ == "__main__":
    logger.info("Starting StockPilot AI Analysis Server")
    uvicorn.run(app, host="0.0.0.0", port=8000)
