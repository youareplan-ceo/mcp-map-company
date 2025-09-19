"""
기본 백엔드 테스트 파일
FastAPI와 헬스체크 API의 기본 동작 검증
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="StockPilot AI API",
    version="1.0.0",
    description="AI 기반 투자 코파일럿 서비스"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "StockPilot AI API", "version": "1.0.0", "status": "running"}

@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "StockPilot AI API",
        "version": "1.0.0",
        "timestamp": "2024-09-09T12:00:00Z"
    }

@app.get("/api/v1/status")
async def service_status():
    return {
        "overall_status": "operational",
        "services": {
            "api": "online",
            "database": "unknown",
            "ai_engine": "unknown",
            "websocket": "unknown",
            "batch_system": "unknown",
            "usage_tracking": "unknown",
            "external_apis": "unknown"
        },
        "last_updated": "2024-09-09T12:00:00Z",
        "health_check_available": True,
        "detailed_check_url": "/api/v1/health/",
        "system_info": {
            "version": "1.0.0",
            "environment": "test",
            "uptime_seconds": 120,
            "services_monitored": 7
        }
    }

@app.get("/api/v1/usage/stats")
async def usage_stats():
    return {
        "daily_usage": {
            "2024-09-09": {
                "date": "2024-09-09",
                "total_requests": 150,
                "total_tokens": 5000,
                "total_cost": 2.5,
                "success_requests": 145,
                "failed_requests": 5,
                "cost_usage_percent": 25.0,
                "success_rate_percent": 96.7,
                "avg_response_time_ms": 150.0
            }
        },
        "current_limits": {
            "daily_limit": 10.0,
            "monthly_limit": 300.0,
            "alert_threshold": 0.8
        },
        "summary": {
            "total_days_tracked": 1,
            "total_cost_to_date": 2.5,
            "total_requests_to_date": 150,
            "avg_daily_cost": 2.5,
            "avg_success_rate": 96.7
        }
    }

@app.get("/api/v1/batch/jobs")
async def batch_jobs():
    return {
        "jobs": [
            {
                "job_id": "daily_stock_update",
                "name": "일일 주식 데이터 업데이트",
                "description": "매일 주식 시장 데이터를 수집하고 업데이트",
                "priority": "HIGH",
                "enabled": True,
                "max_retries": 3,
                "timeout": 3600,
                "dependencies": [],
                "last_status": "success",
                "last_run": "2024-09-09T06:00:00Z"
            },
            {
                "job_id": "ai_signal_generation",
                "name": "AI 투자 시그널 생성",
                "description": "AI 모델을 사용하여 투자 시그널을 생성",
                "priority": "NORMAL",
                "enabled": True,
                "max_retries": 2,
                "timeout": 1800,
                "dependencies": ["daily_stock_update"],
                "last_status": "running",
                "last_run": "2024-09-09T07:00:00Z"
            }
        ]
    }

@app.get("/api/v1/batch/executions/recent")
async def recent_executions():
    return {
        "executions": [
            {
                "execution_id": "exec-123",
                "job_id": "daily_stock_update",
                "job_name": "일일 주식 데이터 업데이트",
                "status": "success",
                "start_time": "2024-09-09T06:00:00Z",
                "end_time": "2024-09-09T06:05:00Z",
                "duration": 300.0,
                "error_message": None,
                "retry_count": 0,
                "items_processed": 1500,
                "throughput_per_second": 5.0,
                "memory_peak_mb": 256.0,
                "cpu_usage_percent": 45.0,
                "warnings": [],
                "progress_percentage": 100.0
            }
        ],
        "total_count": 1,
        "limit": 50
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)