"""
삼성전자(005930) 주식 분석 API 테스트
End-to-End 기능 테스트용 모의 데이터 제공
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta

app = FastAPI(
    title="StockPilot AI API - Samsung Test",
    version="1.0.0",
    description="삼성전자 분석 테스트용 API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "StockPilot AI API - Samsung Test", "version": "1.0.0", "status": "running"}

@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "StockPilot AI API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/status")
async def service_status():
    return {
        "overall_status": "operational",
        "services": {
            "api": "online",
            "database": "online",
            "ai_engine": "online",
            "websocket": "online",
            "batch_system": "online"
        },
        "last_updated": datetime.now().isoformat(),
        "system_info": {
            "version": "1.0.0",
            "environment": "test"
        }
    }

@app.get("/api/v1/stocks/005930")
async def get_samsung_stock():
    """삼성전자 주식 정보"""
    return {
        "symbol": "005930",
        "name": "삼성전자",
        "market": "KOSPI",
        "current_price": 75800,
        "change": 1200,
        "change_rate": 1.61,
        "volume": 12560000,
        "market_cap": 455000000000000,
        "high_52w": 89000,
        "low_52w": 56000,
        "dividend_yield": 2.1,
        "per": 18.5,
        "pbr": 1.2,
        "last_updated": datetime.now().isoformat()
    }

@app.get("/api/v1/analysis/005930")
async def get_samsung_analysis():
    """삼성전자 AI 분석 결과"""
    return {
        "symbol": "005930",
        "name": "삼성전자",
        "analysis": {
            "overall_score": 85,
            "recommendation": "BUY",
            "confidence": 0.87,
            "target_price": 85000,
            "risk_level": "MEDIUM",
            "analysis_date": datetime.now().isoformat()
        },
        "technical_analysis": {
            "trend": "BULLISH",
            "support_levels": [72000, 68000, 65000],
            "resistance_levels": [78000, 82000, 85000],
            "rsi": 58.4,
            "macd": "POSITIVE",
            "moving_averages": {
                "ma_5": 74500,
                "ma_20": 72800,
                "ma_60": 70200
            }
        },
        "fundamental_analysis": {
            "revenue_growth": 8.2,
            "profit_margin": 15.6,
            "debt_ratio": 18.2,
            "roe": 12.4,
            "sector_comparison": "OUTPERFORM"
        },
        "ai_insights": [
            "반도체 업황 회복으로 수익성 개선 전망",
            "메모리 반도체 가격 상승으로 마진 확대 예상",
            "글로벌 스마트폰 시장 회복세로 수요 증가",
            "AI 반도체 시장 진출로 신성장동력 확보"
        ]
    }

@app.get("/api/v1/signals")
async def get_investment_signals():
    """투자 시그널 목록"""
    return {
        "signals": [
            {
                "id": "signal_001",
                "symbol": "005930",
                "name": "삼성전자",
                "signal": "BUY",
                "strength": "HIGH",
                "confidence": 0.89,
                "generated_at": datetime.now().isoformat(),
                "reason": "기술적 지표 상향 돌파, AI 분석 점수 상승"
            },
            {
                "id": "signal_002", 
                "symbol": "000660",
                "name": "SK하이닉스",
                "signal": "HOLD",
                "strength": "MEDIUM",
                "confidence": 0.72,
                "generated_at": (datetime.now() - timedelta(minutes=15)).isoformat(),
                "reason": "반도체 업황 개선 기대감 반영"
            }
        ],
        "total": 2,
        "updated_at": datetime.now().isoformat()
    }

@app.get("/api/v1/usage/stats")
async def usage_stats():
    """사용량 통계"""
    return {
        "daily_usage": {
            datetime.now().strftime("%Y-%m-%d"): {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "total_requests": 45,
                "total_tokens": 1850,
                "total_cost": 0.92,
                "success_requests": 43,
                "failed_requests": 2,
                "cost_usage_percent": 9.2,
                "success_rate_percent": 95.6,
                "avg_response_time_ms": 180.0
            }
        },
        "current_limits": {
            "daily_limit": 10.0,
            "monthly_limit": 300.0,
            "alert_threshold": 0.8
        },
        "summary": {
            "total_days_tracked": 1,
            "total_cost_to_date": 0.92,
            "total_requests_to_date": 45,
            "avg_daily_cost": 0.92,
            "avg_success_rate": 95.6
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)