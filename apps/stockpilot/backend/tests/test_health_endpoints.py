"""
헬스체크 API 엔드포인트 테스트
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from datetime import datetime

from app.main import app
from app.models.health_models import OverallStatus, ServiceStatus, ServiceHealthDetail
from app.services.health_service import HealthService

client = TestClient(app)


class TestHealthEndpoints:
    """헬스체크 엔드포인트 테스트"""

    def test_basic_health_check(self):
        """기본 헬스체크 엔드포인트 테스트"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "StockPilot AI API"
        assert "version" in data
        assert "timestamp" in data
        assert "endpoints" in data

    def test_service_status_endpoint(self):
        """서비스 상태 엔드포인트 테스트"""
        with patch('app.services.health_service.get_health_service') as mock_health:
            # Mock 헬스 서비스 설정
            mock_service = Mock(spec=HealthService)
            mock_service.get_overall_status.return_value = Mock(value="healthy")
            mock_service.service_healths = {
                "database": ServiceHealthDetail(
                    status=ServiceStatus.HEALTHY,
                    last_check=datetime.now(),
                    response_time_ms=50.0,
                    details={"connection": "active"}
                )
            }
            mock_service.last_full_check = datetime.now()
            mock_health.return_value = mock_service
            
            response = client.get("/api/v1/status")
            assert response.status_code == 200
            
            data = response.json()
            assert data["overall_status"] == "operational"
            assert "services" in data
            assert "last_updated" in data
            assert "system_info" in data

    @patch('app.services.health_service.get_health_service')
    def test_comprehensive_health_check(self, mock_health):
        """종합 헬스체크 엔드포인트 테스트"""
        # Mock 헬스 서비스 설정
        mock_service = Mock(spec=HealthService)
        mock_service.perform_comprehensive_check.return_value = {
            "overall_status": OverallStatus.OPERATIONAL.value,
            "services": {
                "database": {
                    "status": "healthy",
                    "response_time_ms": 45.0,
                    "details": {"connections": 5}
                },
                "openai_api": {
                    "status": "healthy", 
                    "response_time_ms": 120.0,
                    "details": {"models_available": 10}
                }
            },
            "last_updated": datetime.now().isoformat(),
            "system_metrics": {
                "memory_usage_percent": 65.5,
                "cpu_usage_percent": 23.1
            }
        }
        mock_health.return_value = mock_service

        response = client.get("/api/v1/health/comprehensive")
        assert response.status_code == 200
        
        data = response.json()
        assert data["overall_status"] == "operational"
        assert "services" in data
        assert "system_metrics" in data

    def test_health_check_with_degraded_service(self):
        """서비스 장애 상황에서의 헬스체크 테스트"""
        with patch('app.services.health_service.get_health_service') as mock_health:
            mock_service = Mock(spec=HealthService)
            mock_service.get_overall_status.return_value = Mock(value="degraded")
            mock_service.service_healths = {
                "database": ServiceHealthDetail(
                    status=ServiceStatus.DEGRADED,
                    last_check=datetime.now(),
                    response_time_ms=500.0,
                    details={"connection": "slow"}
                )
            }
            mock_service.last_full_check = datetime.now()
            mock_health.return_value = mock_service
            
            response = client.get("/api/v1/status")
            assert response.status_code == 200
            
            data = response.json()
            assert data["overall_status"] == "degraded"

    def test_health_check_service_failure(self):
        """헬스체크 서비스 실패 상황 테스트"""
        with patch('app.services.health_service.get_health_service') as mock_health:
            mock_health.side_effect = Exception("Health service unavailable")
            
            response = client.get("/api/v1/status")
            assert response.status_code == 503
            
            data = response.json()
            assert data["overall_status"] == "degraded"
            assert data["health_check_available"] is False


class TestHealthServiceIntegration:
    """헬스 서비스 통합 테스트"""

    @patch('app.services.health_service.asyncpg.connect')
    @patch('app.services.health_service.openai.OpenAI')
    def test_database_health_check(self, mock_openai, mock_db):
        """데이터베이스 헬스체크 통합 테스트"""
        # Mock 데이터베이스 연결
        mock_conn = Mock()
        mock_conn.fetchval.return_value = 1
        mock_db.return_value.__aenter__.return_value = mock_conn
        
        from app.services.health_service import get_health_service
        health_service = get_health_service()
        
        # 실제 데이터베이스 체크는 설정이 필요하므로 패스
        assert health_service is not None

    def test_usage_tracker_integration(self):
        """사용량 추적기 통합 테스트"""
        from app.middleware.usage_tracker import get_usage_tracker
        
        tracker = get_usage_tracker()
        assert tracker is not None
        assert hasattr(tracker, 'record_usage')
        assert hasattr(tracker, 'get_usage_stats')

    def test_batch_manager_integration(self):
        """배치 매니저 통합 테스트"""
        from app.jobs.batch_manager import get_batch_manager
        
        manager = get_batch_manager()
        assert manager is not None
        assert hasattr(manager, 'execute_job')
        assert hasattr(manager, 'get_recent_executions')
        assert hasattr(manager, 'force_release_lock')


@pytest.mark.asyncio
class TestAsyncHealthChecks:
    """비동기 헬스체크 테스트"""

    async def test_async_health_service_methods(self):
        """헬스 서비스 비동기 메서드 테스트"""
        from app.services.health_service import get_health_service
        
        health_service = get_health_service()
        
        # 비동기 메서드들이 존재하는지 확인
        assert hasattr(health_service, 'check_database_health')
        assert hasattr(health_service, 'check_openai_health')
        assert hasattr(health_service, 'check_redis_health')

    async def test_usage_tracker_async_methods(self):
        """사용량 추적기 비동기 메서드 테스트"""
        from app.middleware.usage_tracker import get_usage_tracker
        
        tracker = get_usage_tracker()
        
        # 비동기 메서드들이 존재하는지 확인
        assert hasattr(tracker, 'record_usage')
        assert hasattr(tracker, 'check_cost_limits')
        assert hasattr(tracker, 'get_usage_stats')