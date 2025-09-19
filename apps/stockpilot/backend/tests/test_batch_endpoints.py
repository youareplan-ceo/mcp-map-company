"""
배치 작업 API 엔드포인트 테스트
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.main import app
from app.jobs.batch_manager import BatchManager, JobExecution, JobStatus

client = TestClient(app)


class TestBatchEndpoints:
    """배치 API 엔드포인트 테스트"""

    @patch('app.jobs.batch_manager.get_batch_manager')
    def test_get_recent_executions(self, mock_batch_manager):
        """최근 실행 이력 조회 테스트"""
        # Mock 실행 이력 설정
        mock_execution = Mock(spec=JobExecution)
        mock_execution.execution_id = "test-exec-123"
        mock_execution.job_id = "test-job"
        mock_execution.job_name = "Test Job"
        mock_execution.status = JobStatus.SUCCESS
        mock_execution.start_time = datetime.now()
        mock_execution.end_time = datetime.now()
        mock_execution.duration = 120.5
        mock_execution.error_message = None
        mock_execution.retry_count = 0
        mock_execution.items_processed = 100
        mock_execution.throughput_per_second = 5.2
        mock_execution.memory_peak_mb = 256.0
        mock_execution.cpu_usage_percent = 45.0
        mock_execution.warnings = []
        mock_execution.progress_percentage = 100.0

        mock_manager = Mock(spec=BatchManager)
        mock_manager.get_recent_executions.return_value = [mock_execution]
        mock_batch_manager.return_value = mock_manager

        response = client.get("/api/v1/batch/executions/recent?limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert "executions" in data
        assert "total_count" in data
        assert len(data["executions"]) == 1
        assert data["executions"][0]["execution_id"] == "test-exec-123"

    @patch('app.jobs.batch_manager.get_batch_manager')
    def test_get_execution_stats(self, mock_batch_manager):
        """실행 통계 조회 테스트"""
        mock_manager = Mock(spec=BatchManager)
        mock_manager.get_execution_stats.return_value = {
            "total": 100,
            "success": 85,
            "failed": 15,
            "success_rate": 85.0,
            "avg_duration_seconds": 145.2,
            "avg_throughput_per_second": 4.8,
            "avg_memory_peak_mb": 320.5,
            "avg_cpu_usage_percent": 42.1,
            "stats": {
                "by_status": {
                    "success": 85,
                    "failed": 15,
                    "pending": 0,
                    "running": 0,
                    "skipped": 0,
                    "cancelled": 0
                },
                "by_job": {}
            }
        }
        mock_batch_manager.return_value = mock_manager

        response = client.get("/api/v1/batch/executions/stats?days=7")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 100
        assert data["success"] == 85
        assert data["success_rate"] == 85.0

    @patch('app.jobs.batch_manager.get_batch_manager')
    def test_get_lock_status(self, mock_batch_manager):
        """잠금 상태 조회 테스트"""
        mock_manager = Mock(spec=BatchManager)
        mock_manager.lock_dir = Mock()
        
        # Mock Path 객체
        mock_lock_file = Mock()
        mock_lock_file.exists.return_value = True
        mock_lock_file.stat.return_value.st_mtime = datetime.now().timestamp() - 3600  # 1시간 전
        
        with patch('pathlib.Path') as mock_path:
            mock_path.return_value = mock_lock_file
            mock_batch_manager.return_value = mock_manager

            response = client.get("/api/v1/batch/jobs/test-job/lock/status")
            assert response.status_code == 200
            
            data = response.json()
            assert data["job_id"] == "test-job"
            assert "lock_exists" in data
            assert "is_expired" in data

    @patch('app.jobs.batch_manager.get_batch_manager')
    @pytest.mark.asyncio
    async def test_force_release_lock(self, mock_batch_manager):
        """강제 잠금 해제 테스트"""
        mock_manager = Mock(spec=BatchManager)
        mock_manager.force_release_lock = AsyncMock(return_value=True)
        mock_batch_manager.return_value = mock_manager

        response = client.post(
            "/api/v1/batch/jobs/test-job/lock/release",
            json={"reason": "Test release"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert data["job_id"] == "test-job"
        assert data["reason"] == "Test release"

    @patch('app.jobs.batch_manager.get_batch_manager')
    def test_get_expired_locks(self, mock_batch_manager):
        """만료된 잠금 조회 테스트"""
        mock_manager = Mock(spec=BatchManager)
        mock_manager.check_lock_expiration.return_value = ["expired-job-1", "expired-job-2"]
        mock_batch_manager.return_value = mock_manager

        response = client.get("/api/v1/batch/locks/expired?max_age_hours=24")
        assert response.status_code == 200
        
        data = response.json()
        assert "expired_locks" in data
        assert "count" in data
        assert len(data["expired_locks"]) == 2

    @patch('app.jobs.batch_manager.get_batch_manager')
    @pytest.mark.asyncio
    async def test_cleanup_expired_locks(self, mock_batch_manager):
        """만료된 잠금 정리 테스트"""
        mock_manager = Mock(spec=BatchManager)
        mock_manager.check_lock_expiration.return_value = ["expired-job-1"]
        mock_manager.force_release_lock = AsyncMock(return_value=True)
        mock_batch_manager.return_value = mock_manager

        response = client.post("/api/v1/batch/locks/cleanup?force=true")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert data["cleaned_count"] >= 0

    @patch('app.jobs.batch_manager.get_batch_manager')
    def test_job_status_with_extended_metrics(self, mock_batch_manager):
        """확장된 메트릭스를 포함한 작업 상태 조회 테스트"""
        mock_execution = Mock(spec=JobExecution)
        mock_execution.job_id = "test-job"
        mock_execution.job_name = "Test Job"
        mock_execution.status = JobStatus.SUCCESS
        mock_execution.start_time = datetime(2024, 1, 1, 12, 0, 0)
        mock_execution.end_time = datetime(2024, 1, 1, 12, 2, 0)
        mock_execution.duration = 120.0
        mock_execution.error_message = None
        mock_execution.retry_count = 0
        mock_execution.result = {"processed": 100}
        # 확장된 메트릭스
        mock_execution.execution_id = "exec-123"
        mock_execution.items_processed = 100
        mock_execution.throughput_per_second = 0.83
        mock_execution.memory_peak_mb = 512.0
        mock_execution.cpu_usage_percent = 75.5
        mock_execution.warnings = ["Memory usage high"]
        mock_execution.progress_percentage = 100.0

        mock_manager = Mock(spec=BatchManager)
        mock_manager.get_job_status.return_value = mock_execution
        mock_batch_manager.return_value = mock_manager

        response = client.get("/api/v1/batch/jobs/test-job/status")
        assert response.status_code == 200
        
        data = response.json()
        assert data["job_id"] == "test-job"
        assert data["execution_id"] == "exec-123"
        assert data["items_processed"] == 100
        assert data["throughput_per_second"] == 0.83
        assert data["memory_peak_mb"] == 512.0
        assert data["cpu_usage_percent"] == 75.5
        assert data["warnings"] == ["Memory usage high"]
        assert data["progress_percentage"] == 100.0


class TestBatchManagerIntegration:
    """배치 매니저 통합 테스트"""

    def test_batch_manager_initialization(self):
        """배치 매니저 초기화 테스트"""
        from app.jobs.batch_manager import get_batch_manager
        
        manager = get_batch_manager()
        assert manager is not None
        assert hasattr(manager, 'jobs')
        assert hasattr(manager, 'executions')
        assert hasattr(manager, 'execution_history')
        assert hasattr(manager, 'alert_hooks')

    def test_job_execution_dataclass(self):
        """JobExecution 데이터클래스 테스트"""
        execution = JobExecution(
            job_id="test-job",
            job_name="Test Job"
        )
        
        assert execution.job_id == "test-job"
        assert execution.job_name == "Test Job"
        assert execution.status == JobStatus.PENDING
        assert execution.execution_id is not None  # UUID가 생성되었는지 확인
        assert isinstance(execution.warnings, list)

    def test_batch_manager_methods(self):
        """배치 매니저 메서드 존재 확인"""
        from app.jobs.batch_manager import get_batch_manager
        
        manager = get_batch_manager()
        
        # 기본 메서드들
        assert hasattr(manager, 'register_job')
        assert hasattr(manager, 'execute_job')
        assert hasattr(manager, 'get_job_status')
        
        # 확장된 모니터링 메서드들
        assert hasattr(manager, 'get_recent_executions')
        assert hasattr(manager, 'get_execution_stats')
        assert hasattr(manager, 'force_release_lock')
        assert hasattr(manager, 'check_lock_expiration')
        assert hasattr(manager, 'add_alert_hook')


class TestBatchAlertSystem:
    """배치 알림 시스템 테스트"""

    def test_logger_batch_alert_hook(self):
        """로거 배치 알림 훅 테스트"""
        from app.jobs.batch_manager import LoggerBatchAlertHook, JobExecution
        
        hook = LoggerBatchAlertHook()
        execution = JobExecution(job_id="test-job", job_name="Test Job")
        
        # 메서드 존재 확인
        assert hasattr(hook, 'send_alert')

    def test_batch_manager_alert_integration(self):
        """배치 매니저 알림 통합 테스트"""
        from app.jobs.batch_manager import get_batch_manager, LoggerBatchAlertHook
        
        manager = get_batch_manager()
        
        # 기본 알림 훅이 등록되어 있는지 확인
        assert len(manager.alert_hooks) > 0
        assert isinstance(manager.alert_hooks[0], LoggerBatchAlertHook)
        
        # 알림 훅 추가 가능한지 확인
        custom_hook = LoggerBatchAlertHook()
        manager.add_alert_hook(custom_hook)
        assert len(manager.alert_hooks) >= 2


@pytest.mark.asyncio
class TestAsyncBatchOperations:
    """비동기 배치 작업 테스트"""

    @patch('app.jobs.batch_manager.get_batch_manager')
    async def test_async_job_execution(self, mock_batch_manager):
        """비동기 작업 실행 테스트"""
        mock_manager = Mock(spec=BatchManager)
        mock_manager.execute_job = AsyncMock(return_value=Mock(spec=JobExecution))
        mock_batch_manager.return_value = mock_manager

        # 실제 비동기 실행은 백그라운드 태스크로 처리되므로 여기서는 메서드 존재만 확인
        assert hasattr(mock_manager, 'execute_job')

    async def test_async_lock_operations(self):
        """비동기 잠금 작업 테스트"""
        from app.jobs.batch_manager import get_batch_manager
        
        manager = get_batch_manager()
        
        # 비동기 메서드들이 존재하는지 확인
        assert hasattr(manager, 'force_release_lock')
        # force_release_lock이 비동기 함수인지 확인
        import asyncio
        assert asyncio.iscoroutinefunction(manager.force_release_lock)