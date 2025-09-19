"""
StockPilot 통합 헬스체크 및 모니터링 서비스
모든 마이크로서비스의 상태를 모니터링하고 알림을 제공
"""

import asyncio
import aiohttp
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import json
import os
import sys
from pathlib import Path

# 로깅 설정
logger = logging.getLogger(__name__)

@dataclass
class ServiceHealth:
    """서비스 헬스 상태"""
    service_name: str
    endpoint: str
    status: str  # 'healthy', 'unhealthy', 'warning', 'unknown'
    response_time_ms: float
    last_check: datetime
    error_message: Optional[str] = None
    uptime_seconds: Optional[float] = None
    version: Optional[str] = None
    dependencies: List[str] = None

@dataclass
class SystemMetrics:
    """시스템 메트릭"""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_io: Dict[str, int]
    process_count: int
    load_average: List[float]
    timestamp: datetime

@dataclass
class AlertEvent:
    """알림 이벤트"""
    id: str
    severity: str  # 'critical', 'warning', 'info'
    service: str
    message: str
    timestamp: datetime
    resolved: bool = False
    acknowledged: bool = False

class HealthMonitorService:
    """통합 헬스체크 및 모니터링 서비스"""
    
    def __init__(self):
        self.session = None
        self.alert_history = []
        self.health_history = {}
        
        # 모니터링 대상 서비스들
        self.services = {
            "websocket": {
                "name": "WebSocket 서버",
                "url": "http://localhost:8765/health",
                "timeout": 10,
                "critical": True
            },
            "auth_api": {
                "name": "인증 API",
                "url": "http://localhost:8002/health",
                "timeout": 5,
                "critical": True
            },
            "dashboard_api": {
                "name": "대시보드 API", 
                "url": "http://localhost:8003/health",
                "timeout": 5,
                "critical": False
            },
            "redis": {
                "name": "Redis 캐시",
                "url": "redis://localhost:6379",
                "timeout": 3,
                "critical": True
            },
            "postgres": {
                "name": "PostgreSQL",
                "url": "postgresql://localhost:5432",
                "timeout": 5,
                "critical": True
            }
        }
        
        # 알림 설정
        self.alert_thresholds = {
            "cpu_threshold": 80.0,
            "memory_threshold": 85.0,
            "disk_threshold": 90.0,
            "response_time_threshold": 5000,  # 5초
            "error_rate_threshold": 0.05  # 5%
        }
        
        # Slack 웹훅 URL (환경변수에서 가져오기)
        self.slack_webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self.session:
            await self.session.close()

    async def check_http_service(self, service_key: str) -> ServiceHealth:
        """HTTP 서비스 헬스체크"""
        service = self.services[service_key]
        start_time = datetime.now()
        
        try:
            async with self.session.get(
                service["url"], 
                timeout=aiohttp.ClientTimeout(total=service["timeout"])
            ) as response:
                response_time = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    try:
                        data = await response.json()
                        return ServiceHealth(
                            service_name=service["name"],
                            endpoint=service["url"],
                            status="healthy",
                            response_time_ms=response_time,
                            last_check=datetime.now(),
                            uptime_seconds=data.get("uptime_seconds"),
                            version=data.get("version")
                        )
                    except:
                        # JSON 응답이 아닌 경우에도 200이면 healthy로 간주
                        return ServiceHealth(
                            service_name=service["name"],
                            endpoint=service["url"],
                            status="healthy",
                            response_time_ms=response_time,
                            last_check=datetime.now()
                        )
                else:
                    return ServiceHealth(
                        service_name=service["name"],
                        endpoint=service["url"],
                        status="unhealthy",
                        response_time_ms=response_time,
                        last_check=datetime.now(),
                        error_message=f"HTTP {response.status}"
                    )
                    
        except asyncio.TimeoutError:
            return ServiceHealth(
                service_name=service["name"],
                endpoint=service["url"],
                status="unhealthy",
                response_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                last_check=datetime.now(),
                error_message="Timeout"
            )
        except Exception as e:
            return ServiceHealth(
                service_name=service["name"],
                endpoint=service["url"],
                status="unhealthy",
                response_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                last_check=datetime.now(),
                error_message=str(e)
            )

    async def check_redis_service(self) -> ServiceHealth:
        """Redis 서비스 헬스체크"""
        try:
            import redis.asyncio as redis
            
            redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
            start_time = datetime.now()
            
            # Redis ping 테스트
            pong = await redis_client.ping()
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if pong:
                # Redis 정보 가져오기
                info = await redis_client.info()
                uptime = info.get('uptime_in_seconds', 0)
                
                await redis_client.close()
                
                return ServiceHealth(
                    service_name="Redis 캐시",
                    endpoint="redis://localhost:6379",
                    status="healthy",
                    response_time_ms=response_time,
                    last_check=datetime.now(),
                    uptime_seconds=uptime,
                    version=info.get('redis_version')
                )
            else:
                await redis_client.close()
                return ServiceHealth(
                    service_name="Redis 캐시",
                    endpoint="redis://localhost:6379",
                    status="unhealthy",
                    response_time_ms=response_time,
                    last_check=datetime.now(),
                    error_message="Redis ping failed"
                )
                
        except Exception as e:
            return ServiceHealth(
                service_name="Redis 캐시",
                endpoint="redis://localhost:6379",
                status="unhealthy",
                response_time_ms=0,
                last_check=datetime.now(),
                error_message=str(e)
            )

    async def check_postgres_service(self) -> ServiceHealth:
        """PostgreSQL 서비스 헬스체크"""
        try:
            import asyncpg
            
            start_time = datetime.now()
            
            # PostgreSQL 연결 테스트
            conn = await asyncpg.connect(
                host='localhost',
                port=5432,
                user=os.getenv('POSTGRES_USER', 'postgres'),
                password=os.getenv('POSTGRES_PASSWORD', ''),
                database=os.getenv('POSTGRES_DB', 'postgres'),
                timeout=5
            )
            
            # 간단한 쿼리 실행
            result = await conn.fetchval('SELECT version()')
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            await conn.close()
            
            return ServiceHealth(
                service_name="PostgreSQL",
                endpoint="postgresql://localhost:5432",
                status="healthy",
                response_time_ms=response_time,
                last_check=datetime.now(),
                version=result.split()[1] if result else None
            )
            
        except Exception as e:
            return ServiceHealth(
                service_name="PostgreSQL",
                endpoint="postgresql://localhost:5432", 
                status="unhealthy",
                response_time_ms=0,
                last_check=datetime.now(),
                error_message=str(e)
            )

    def get_system_metrics(self) -> SystemMetrics:
        """시스템 메트릭 수집"""
        try:
            # CPU 사용률
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 메모리 사용률
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 디스크 사용률
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # 네트워크 I/O
            network = psutil.net_io_counters()
            network_io = {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv
            }
            
            # 프로세스 수
            process_count = len(psutil.pids())
            
            # 로드 애버리지 (Unix 시스템만)
            try:
                load_average = list(os.getloadavg())
            except (OSError, AttributeError):
                load_average = [0.0, 0.0, 0.0]
            
            return SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_percent=disk_percent,
                network_io=network_io,
                process_count=process_count,
                load_average=load_average,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"시스템 메트릭 수집 오류: {e}")
            return SystemMetrics(
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_percent=0.0,
                network_io={},
                process_count=0,
                load_average=[0.0, 0.0, 0.0],
                timestamp=datetime.now()
            )

    async def check_all_services(self) -> Dict[str, ServiceHealth]:
        """모든 서비스 헬스체크"""
        results = {}
        
        # HTTP 서비스들 병렬 체크
        http_services = ["websocket", "auth_api", "dashboard_api"]
        http_tasks = [self.check_http_service(service) for service in http_services]
        http_results = await asyncio.gather(*http_tasks, return_exceptions=True)
        
        for service, result in zip(http_services, http_results):
            if isinstance(result, ServiceHealth):
                results[service] = result
            else:
                results[service] = ServiceHealth(
                    service_name=self.services[service]["name"],
                    endpoint=self.services[service]["url"],
                    status="unhealthy",
                    response_time_ms=0,
                    last_check=datetime.now(),
                    error_message=str(result)
                )
        
        # Redis 체크
        results["redis"] = await self.check_redis_service()
        
        # PostgreSQL 체크
        results["postgres"] = await self.check_postgres_service()
        
        # 결과를 히스토리에 저장
        for service_key, health in results.items():
            if service_key not in self.health_history:
                self.health_history[service_key] = []
            
            self.health_history[service_key].append(health)
            
            # 최근 100개만 유지
            if len(self.health_history[service_key]) > 100:
                self.health_history[service_key] = self.health_history[service_key][-100:]
        
        return results

    def generate_alerts(self, service_health: Dict[str, ServiceHealth], system_metrics: SystemMetrics) -> List[AlertEvent]:
        """알림 이벤트 생성"""
        alerts = []
        
        # 서비스 다운 알림
        for service_key, health in service_health.items():
            service_config = self.services[service_key]
            
            if health.status == "unhealthy" and service_config["critical"]:
                alert = AlertEvent(
                    id=f"service_down_{service_key}_{int(datetime.now().timestamp())}",
                    severity="critical",
                    service=health.service_name,
                    message=f"{health.service_name}이 응답하지 않습니다. 오류: {health.error_message}",
                    timestamp=datetime.now()
                )
                alerts.append(alert)
            
            # 응답 시간 경고
            elif health.response_time_ms > self.alert_thresholds["response_time_threshold"]:
                alert = AlertEvent(
                    id=f"slow_response_{service_key}_{int(datetime.now().timestamp())}",
                    severity="warning", 
                    service=health.service_name,
                    message=f"{health.service_name}의 응답 시간이 느립니다: {health.response_time_ms:.0f}ms",
                    timestamp=datetime.now()
                )
                alerts.append(alert)
        
        # 시스템 리소스 알림
        if system_metrics.cpu_percent > self.alert_thresholds["cpu_threshold"]:
            alert = AlertEvent(
                id=f"high_cpu_{int(datetime.now().timestamp())}",
                severity="warning",
                service="System",
                message=f"CPU 사용률이 높습니다: {system_metrics.cpu_percent:.1f}%",
                timestamp=datetime.now()
            )
            alerts.append(alert)
        
        if system_metrics.memory_percent > self.alert_thresholds["memory_threshold"]:
            alert = AlertEvent(
                id=f"high_memory_{int(datetime.now().timestamp())}",
                severity="warning",
                service="System",
                message=f"메모리 사용률이 높습니다: {system_metrics.memory_percent:.1f}%",
                timestamp=datetime.now()
            )
            alerts.append(alert)
        
        if system_metrics.disk_percent > self.alert_thresholds["disk_threshold"]:
            alert = AlertEvent(
                id=f"high_disk_{int(datetime.now().timestamp())}",
                severity="critical",
                service="System",
                message=f"디스크 사용률이 높습니다: {system_metrics.disk_percent:.1f}%",
                timestamp=datetime.now()
            )
            alerts.append(alert)
        
        # 알림 히스토리에 추가
        self.alert_history.extend(alerts)
        
        # 최근 1000개 알림만 유지
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]
        
        return alerts

    async def send_slack_alert(self, alert: AlertEvent) -> bool:
        """Slack 알림 전송"""
        if not self.slack_webhook_url:
            logger.warning("Slack webhook URL이 설정되지 않았습니다.")
            return False
        
        try:
            # Slack 메시지 포맷
            color = "#ff0000" if alert.severity == "critical" else "#ffaa00"
            
            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": f"🚨 StockPilot 알림 - {alert.severity.upper()}",
                        "fields": [
                            {
                                "title": "서비스",
                                "value": alert.service,
                                "short": True
                            },
                            {
                                "title": "시간",
                                "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                                "short": True
                            },
                            {
                                "title": "메시지",
                                "value": alert.message,
                                "short": False
                            }
                        ],
                        "footer": "StockPilot 모니터링",
                        "ts": int(alert.timestamp.timestamp())
                    }
                ]
            }
            
            async with self.session.post(
                self.slack_webhook_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    logger.info(f"Slack 알림 전송 성공: {alert.id}")
                    return True
                else:
                    logger.error(f"Slack 알림 전송 실패: HTTP {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Slack 알림 전송 오류: {e}")
            return False

    async def get_comprehensive_health_report(self) -> Dict[str, Any]:
        """종합 헬스 리포트 생성"""
        try:
            # 서비스 헬스체크
            service_health = await self.check_all_services()
            
            # 시스템 메트릭
            system_metrics = self.get_system_metrics()
            
            # 알림 생성
            alerts = self.generate_alerts(service_health, system_metrics)
            
            # 전체 상태 결정
            overall_status = "healthy"
            critical_services_down = 0
            
            for service_key, health in service_health.items():
                if health.status == "unhealthy":
                    if self.services[service_key]["critical"]:
                        critical_services_down += 1
                        overall_status = "critical"
                    elif overall_status == "healthy":
                        overall_status = "warning"
            
            # 시스템 리소스 기반 상태 조정
            if (system_metrics.cpu_percent > 90 or 
                system_metrics.memory_percent > 95 or 
                system_metrics.disk_percent > 95):
                if overall_status == "healthy":
                    overall_status = "warning"
            
            # 새로운 critical 알림이 있다면 Slack으로 전송
            for alert in alerts:
                if alert.severity == "critical":
                    await self.send_slack_alert(alert)
            
            # 리포트 구성
            report = {
                "timestamp": datetime.now().isoformat(),
                "overall_status": overall_status,
                "services": {
                    key: {
                        "name": health.service_name,
                        "status": health.status,
                        "response_time_ms": health.response_time_ms,
                        "last_check": health.last_check.isoformat(),
                        "error_message": health.error_message,
                        "uptime_seconds": health.uptime_seconds,
                        "version": health.version
                    }
                    for key, health in service_health.items()
                },
                "system_metrics": {
                    "cpu_percent": system_metrics.cpu_percent,
                    "memory_percent": system_metrics.memory_percent,
                    "disk_percent": system_metrics.disk_percent,
                    "network_io": system_metrics.network_io,
                    "process_count": system_metrics.process_count,
                    "load_average": system_metrics.load_average
                },
                "alerts": {
                    "active_alerts": len([a for a in alerts if not a.resolved]),
                    "recent_alerts": [
                        {
                            "id": alert.id,
                            "severity": alert.severity,
                            "service": alert.service,
                            "message": alert.message,
                            "timestamp": alert.timestamp.isoformat()
                        }
                        for alert in alerts[-10:]  # 최근 10개
                    ]
                },
                "summary": {
                    "total_services": len(service_health),
                    "healthy_services": len([h for h in service_health.values() if h.status == "healthy"]),
                    "unhealthy_services": len([h for h in service_health.values() if h.status == "unhealthy"]),
                    "critical_services_down": critical_services_down,
                    "average_response_time": sum(h.response_time_ms for h in service_health.values()) / len(service_health)
                }
            }
            
            return report
            
        except Exception as e:
            logger.error(f"헬스 리포트 생성 오류: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "overall_status": "error",
                "error": str(e)
            }

# 헬스 모니터 서비스 인스턴스 생성용 팩토리 함수
async def create_health_monitor():
    """헬스 모니터 서비스 인스턴스 생성"""
    monitor = HealthMonitorService()
    await monitor.__aenter__()
    return monitor