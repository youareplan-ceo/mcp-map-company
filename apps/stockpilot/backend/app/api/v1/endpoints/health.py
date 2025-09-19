"""
확장된 헬스체크 API 엔드포인트
의존성 서비스 상태 점검 및 종합 상태 관리
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.services.health_service import get_health_service, HealthStatus
from app.models.health_models import (
    ComprehensiveHealthResponse, QuickHealthResponse, ServiceStatusResponse,
    MetricsResponse, AlertsResponse, OverallStatus, ServiceHealthDetail,
    SystemSummary, HealthAlert
)

router = APIRouter()


async def _get_current_alerts(health_service) -> List[HealthAlert]:
    """현재 활성 알림 목록 생성"""
    alerts = []
    
    for name, health in health_service.service_healths.items():
        if health.status == HealthStatus.UNHEALTHY:
            alerts.append(HealthAlert(
                service_name=name,
                alert_level="critical",
                message=health.error_message or f"{name} 서비스가 응답하지 않습니다",
                timestamp=health.last_check or datetime.now(),
                resolved=False
            ))
        elif health.status == HealthStatus.DEGRADED:
            alerts.append(HealthAlert(
                service_name=name,
                alert_level="warning",
                message=health.error_message or f"{name} 서비스 성능이 저하되었습니다",
                timestamp=health.last_check or datetime.now(),
                resolved=False
            ))
    
    return alerts


class HealthCheckResponse(BaseModel):
    """헬스체크 응답 모델"""
    overall_status: str
    check_duration: str
    last_check: str
    summary: Dict[str, int]
    services: Dict[str, Dict[str, Any]]


class ServiceHealthResponse(BaseModel):
    """개별 서비스 헬스 응답 모델"""
    name: str
    status: str
    response_time: Optional[str] = None
    last_check: Optional[str] = None
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@router.get("/", response_model=ComprehensiveHealthResponse)
async def comprehensive_health_check():
    """종합 헬스체크 - 모든 의존성 서비스 상태 점검 (표준화된 스키마)"""
    try:
        health_service = get_health_service()
        result = await health_service.perform_full_health_check()
        
        # 표준화된 응답 형식으로 변환
        return ComprehensiveHealthResponse(
            overall_status=OverallStatus(result["overall_status"]),
            last_updated=health_service.last_full_check,
            check_duration_ms=float(result["check_duration"].rstrip('s')) * 1000,
            summary=SystemSummary(
                total_services=result["summary"]["total_services"],
                healthy_services=result["summary"]["healthy"],
                degraded_services=result["summary"]["degraded"],
                unhealthy_services=result["summary"]["unhealthy"],
                system_availability_percentage=(result["summary"]["healthy"] / result["summary"]["total_services"] * 100) if result["summary"]["total_services"] > 0 else 0
            ),
            services={
                name: ServiceHealthDetail(
                    name=name,
                    status=service["status"],
                    response_time_ms=float(service["response_time"].rstrip('s')) * 1000 if service["response_time"] else None,
                    last_check=datetime.fromisoformat(service["last_check"]) if service["last_check"] else None,
                    error_message=service["error_message"],
                    custom_metrics=service["details"]
                )
                for name, service in result["services"].items()
            },
            active_alerts=await _get_current_alerts(health_service)
        )
        
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"헬스체크 실패: {str(e)}")


@router.get("/quick", response_model=QuickHealthResponse)
async def quick_health_check():
    """빠른 헬스체크 - 기본 상태만 확인 (표준화된 스키마)"""
    try:
        health_service = get_health_service()
        overall_status = health_service.get_overall_status()
        
        # 상태 매핑
        status_mapping = {
            HealthStatus.HEALTHY: OverallStatus.OPERATIONAL,
            HealthStatus.DEGRADED: OverallStatus.DEGRADED,
            HealthStatus.UNHEALTHY: OverallStatus.CRITICAL,
            HealthStatus.UNKNOWN: OverallStatus.UNKNOWN
        }
        
        # 건강한 서비스 비율 계산
        total_services = len(health_service.service_healths)
        healthy_services = sum(1 for h in health_service.service_healths.values() if h.status == HealthStatus.HEALTHY)
        healthy_percentage = (healthy_services / total_services * 100) if total_services > 0 else 0
        
        return QuickHealthResponse(
            overall_status=status_mapping.get(overall_status, OverallStatus.UNKNOWN),
            last_updated=health_service.last_full_check or datetime.now(),
            is_operational=overall_status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED],
            services_count=total_services,
            healthy_percentage=healthy_percentage
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"빠른 헬스체크 실패: {str(e)}")


@router.get("/services/{service_name}", response_model=ServiceHealthResponse)
async def get_service_health(service_name: str):
    """개별 서비스 헬스 상태 조회"""
    try:
        health_service = get_health_service()
        service_health = health_service.get_service_health(service_name)
        
        if not service_health:
            raise HTTPException(status_code=404, detail=f"서비스를 찾을 수 없습니다: {service_name}")
        
        return ServiceHealthResponse(
            name=service_health.name,
            status=service_health.status.value,
            response_time=f"{service_health.response_time:.3f}s" if service_health.response_time else None,
            last_check=service_health.last_check.isoformat() if service_health.last_check else None,
            error_message=service_health.error_message,
            details=service_health.details
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서비스 상태 조회 실패: {str(e)}")


@router.get("/services")
async def list_services():
    """모니터링 대상 서비스 목록 조회"""
    try:
        health_service = get_health_service()
        
        services = []
        for name, health in health_service.service_healths.items():
            services.append({
                "name": name,
                "status": health.status.value,
                "last_check": health.last_check.isoformat() if health.last_check else None,
                "has_error": health.error_message is not None
            })
        
        return {
            "services": services,
            "total_count": len(services),
            "last_updated": health_service.last_full_check.isoformat() if health_service.last_full_check else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서비스 목록 조회 실패: {str(e)}")


@router.post("/check/{service_name}")
async def check_specific_service(service_name: str):
    """특정 서비스 헬스체크 수행"""
    try:
        health_service = get_health_service()
        
        # 서비스별 개별 체크 메서드 매핑
        check_methods = {
            "openai_api": health_service.check_openai_service,
            "database": health_service.check_database_service,
            "redis": health_service.check_redis_service,
            "external_apis": health_service.check_external_apis,
            "websocket": health_service.check_websocket_service,
            "batch_system": health_service.check_batch_system,
            "usage_tracking": health_service.check_usage_tracking
        }
        
        if service_name not in check_methods:
            raise HTTPException(status_code=404, detail=f"지원되지 않는 서비스: {service_name}")
        
        # 개별 서비스 체크 수행
        service_health = await check_methods[service_name]()
        health_service.service_healths[service_name] = service_health
        
        return {
            "service": service_name,
            "status": service_health.status.value,
            "response_time": f"{service_health.response_time:.3f}s" if service_health.response_time else None,
            "check_time": service_health.last_check.isoformat() if service_health.last_check else None,
            "error_message": service_health.error_message,
            "details": service_health.details
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서비스 체크 실패: {str(e)}")


@router.post("/refresh")
async def refresh_health_checks(background_tasks: BackgroundTasks):
    """헬스체크 새로고침 (백그라운드 실행)"""
    try:
        health_service = get_health_service()
        
        # 백그라운드에서 전체 헬스체크 수행
        background_tasks.add_task(health_service.perform_full_health_check)
        
        return {
            "message": "헬스체크 새로고침 시작",
            "status": "initiated",
            "estimated_duration": "10-30초"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"헬스체크 새로고침 실패: {str(e)}")


@router.get("/status")
async def get_status_summary():
    """상태 요약 정보"""
    try:
        health_service = get_health_service()
        overall_status = health_service.get_overall_status()
        
        # 서비스별 상태 집계
        status_counts = {
            "healthy": 0,
            "degraded": 0,
            "unhealthy": 0,
            "unknown": 0
        }
        
        for health in health_service.service_healths.values():
            status_counts[health.status.value] += 1
        
        # 시스템 가용성 계산
        total_services = len(health_service.service_healths)
        healthy_services = status_counts["healthy"]
        availability = (healthy_services / total_services * 100) if total_services > 0 else 0
        
        return {
            "overall_status": overall_status.value,
            "system_availability": f"{availability:.1f}%",
            "is_operational": overall_status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED],
            "status_breakdown": status_counts,
            "total_services": total_services,
            "last_check": health_service.last_full_check.isoformat() if health_service.last_full_check else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"상태 요약 조회 실패: {str(e)}")


@router.get("/alerts")
async def get_health_alerts():
    """현재 헬스체크 알림/경고 조회"""
    try:
        health_service = get_health_service()
        
        alerts = []
        warnings = []
        
        for name, health in health_service.service_healths.items():
            if health.status == HealthStatus.UNHEALTHY:
                alerts.append({
                    "service": name,
                    "level": "critical",
                    "message": health.error_message or f"{name} 서비스가 응답하지 않습니다",
                    "since": health.last_check.isoformat() if health.last_check else None
                })
            elif health.status == HealthStatus.DEGRADED:
                warnings.append({
                    "service": name,
                    "level": "warning", 
                    "message": health.error_message or f"{name} 서비스 성능이 저하되었습니다",
                    "since": health.last_check.isoformat() if health.last_check else None
                })
        
        return {
            "alerts": alerts,
            "warnings": warnings,
            "total_issues": len(alerts) + len(warnings),
            "system_status": health_service.get_overall_status().value,
            "requires_attention": len(alerts) > 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"알림 조회 실패: {str(e)}")


@router.get("/metrics")
async def get_health_metrics():
    """헬스체크 메트릭스 조회"""
    try:
        health_service = get_health_service()
        
        metrics = {}
        
        for name, health in health_service.service_healths.items():
            metrics[name] = {
                "status": health.status.value,
                "response_time_ms": health.response_time * 1000 if health.response_time else None,
                "is_healthy": health.status == HealthStatus.HEALTHY,
                "last_check_ago": (
                    (health_service.last_full_check - health.last_check).total_seconds()
                    if health_service.last_full_check and health.last_check
                    else None
                )
            }
            
            # 서비스별 추가 메트릭스
            if health.details:
                metrics[name]["details"] = health.details
        
        return {
            "timestamp": health_service.last_full_check.isoformat() if health_service.last_full_check else None,
            "overall_health_score": len([h for h in health_service.service_healths.values() if h.status == HealthStatus.HEALTHY]) / len(health_service.service_healths) * 100 if health_service.service_healths else 0,
            "metrics": metrics
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"메트릭스 조회 실패: {str(e)}")