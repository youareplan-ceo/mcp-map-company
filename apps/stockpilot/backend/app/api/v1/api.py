"""
API v1 라우터 통합
모든 API 엔드포인트를 하나의 라우터로 통합
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime

from app.api.v1.endpoints import stocks, signals, news, portfolio, market, dashboard, usage, batch, health
from app.services.health_service import get_health_service
from app.models.health_models import ServiceStatusResponse, OverallStatus

# API v1 메인 라우터
api_router = APIRouter()

# 각 기능별 라우터 등록
api_router.include_router(
    stocks.router,
    prefix="/stocks",
    tags=["stocks"],
    responses={404: {"description": "종목을 찾을 수 없습니다"}}
)

api_router.include_router(
    signals.router,
    prefix="/signals",
    tags=["signals"],
    responses={404: {"description": "시그널을 찾을 수 없습니다"}}
)

api_router.include_router(
    news.router,
    prefix="/news",
    tags=["news"],
    responses={404: {"description": "뉴스를 찾을 수 없습니다"}}
)

api_router.include_router(
    portfolio.router,
    prefix="/portfolio",
    tags=["portfolio"],
    responses={404: {"description": "포트폴리오를 찾을 수 없습니다"}}
)

api_router.include_router(
    market.router,
    prefix="/market",
    tags=["market"],
    responses={503: {"description": "시장 데이터 서비스를 사용할 수 없습니다"}}
)

api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["dashboard"],
    responses={503: {"description": "대시보드 서비스를 사용할 수 없습니다"}}
)

api_router.include_router(
    usage.router,
    prefix="/usage",
    tags=["usage"],
    responses={403: {"description": "사용량 추적 기능을 사용할 수 없습니다"}}
)

api_router.include_router(
    batch.router,
    prefix="/batch",
    tags=["batch"],
    responses={503: {"description": "배치 시스템을 사용할 수 없습니다"}}
)

api_router.include_router(
    health.router,
    prefix="/health",
    tags=["health"],
    responses={503: {"description": "헬스체크 서비스를 사용할 수 없습니다"}}
)


@api_router.get("/health")
async def health_check():
    """
    API 헬스체크
    서비스 상태 및 버전 정보
    """
    return {
        "status": "healthy",
        "service": "StockPilot AI API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "stocks": "주식 정보 및 분석",
            "signals": "AI 투자 시그널",
            "news": "뉴스 및 감정 분석",
            "portfolio": "포트폴리오 관리",
            "market": "시장 정보",
            "dashboard": "대시보드 요약",
            "usage": "OpenAI 사용량 및 비용 추적",
            "batch": "배치 작업 관리",
            "health": "시스템 헬스체크 (확장)"
        }
    }


@api_router.get("/status", response_model=ServiceStatusResponse)
async def service_status():
    """
    서비스 상태 확인 - 확장된 헬스체크 통합 (표준화된 스키마)
    각 서비스 컴포넌트의 상태
    """
    try:
        health_service = get_health_service()
        
        # 빠른 상태 확인 (캐시된 결과 사용)
        overall_status = health_service.get_overall_status()
        
        # 서비스별 간단한 상태 요약
        services_summary = {}
        for name, health in health_service.service_healths.items():
            if health.status.value == "healthy":
                services_summary[name] = "online"
            elif health.status.value == "degraded":
                services_summary[name] = "degraded"
            else:
                services_summary[name] = "offline"
        
        # 기본 서비스들이 체크되지 않은 경우 기본값 (프론트엔드 대시보드 호환)
        default_services = {
            "api": "online",
            "database": services_summary.get("database", "unknown"),
            "ai_engine": services_summary.get("openai_api", "unknown"),
            "websocket": services_summary.get("websocket", "unknown"),
            "batch_system": services_summary.get("batch_system", "unknown"),
            "usage_tracking": services_summary.get("usage_tracking", "unknown"),
            "external_apis": services_summary.get("external_apis", "unknown")
        }
        
        # 전체 상태 매핑
        status_mapping = {
            "healthy": OverallStatus.OPERATIONAL,
            "degraded": OverallStatus.DEGRADED,
            "unhealthy": OverallStatus.CRITICAL,
            "unknown": OverallStatus.UNKNOWN
        }
        
        # 시스템 정보 추가
        system_info = {
            "version": "1.0.0",
            "environment": "production",
            "uptime_seconds": (datetime.now() - health_service.last_full_check).total_seconds() if health_service.last_full_check else 0,
            "services_monitored": len(health_service.service_healths)
        }
        
        return ServiceStatusResponse(
            overall_status=status_mapping.get(overall_status.value, OverallStatus.UNKNOWN),
            services=default_services,
            last_updated=health_service.last_full_check or datetime.now(),
            health_check_available=True,
            detailed_check_url="/api/v1/health/",
            system_info=system_info
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "overall_status": "degraded",
                "services": {},
                "last_updated": datetime.now().isoformat(),
                "health_check_available": False,
                "detailed_check_url": "/api/v1/health/",
                "system_info": {"error": str(e)}
            }
        )


@api_router.get("/metrics")
async def get_metrics():
    """
    API 메트릭스
    사용량, 응답 시간 등의 통계
    """
    return {
        "api_version": "v1",
        "uptime": "계산 필요",  # 실제 구현 필요
        "request_count": "계산 필요",  # 실제 구현 필요
        "avg_response_time": "계산 필요",  # 실제 구현 필요
        "active_connections": "계산 필요",  # WebSocket 연결 수
        "timestamp": datetime.now().isoformat()
    }