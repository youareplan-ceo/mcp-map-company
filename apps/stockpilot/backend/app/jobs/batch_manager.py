"""
배치 작업 관리자
일일 배치 작업의 실행, 중복 방지, 오류 처리 관리
"""

import asyncio
import time
import hashlib
import uuid
import psutil
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
import fcntl
from loguru import logger

from app.config import get_settings

settings = get_settings()


class JobStatus(Enum):
    """작업 상태"""
    PENDING = "pending"
    RUNNING = "running" 
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class JobPriority(Enum):
    """작업 우선순위"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


@dataclass
class JobExecution:
    """작업 실행 정보 - 확장된 모니터링"""
    job_id: str
    job_name: str
    status: JobStatus = JobStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    result: Optional[Dict[str, Any]] = None
    lock_file_path: Optional[str] = None
    # 추가 모니터링 메트릭스
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    items_processed: Optional[int] = None
    throughput_per_second: Optional[float] = None
    memory_peak_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    warnings: List[str] = field(default_factory=list)
    progress_percentage: Optional[float] = None


@dataclass
class BatchJob:
    """배치 작업 정의"""
    job_id: str
    name: str
    description: str
    func: Callable
    priority: JobPriority = JobPriority.NORMAL
    max_retries: int = 3
    timeout: int = 3600  # 1시간 기본 타임아웃
    dependencies: List[str] = field(default_factory=list)
    enabled: bool = True
    cron_expression: Optional[str] = None  # 향후 cron 지원용


class BatchAlertHook:
    """배치 작업 알림 훅 인터페이스"""
    
    async def send_alert(self, alert_type: str, job_execution: JobExecution, additional_data: Dict[str, Any] = None):
        """알림 전송 (서브클래스에서 구현)"""
        pass


class LoggerBatchAlertHook(BatchAlertHook):
    """로거 배치 알림 훅"""
    
    async def send_alert(self, alert_type: str, job_execution: JobExecution, additional_data: Dict[str, Any] = None):
        """로그로 알림 전송"""
        logger.warning(
            f"[BATCH_{alert_type.upper()}] {job_execution.job_name} ({job_execution.job_id}) - "
            f"상태: {job_execution.status.value}, 오류: {job_execution.error_message}, "
            f"추가정보: {additional_data or {}}"
        )


class BatchManager:
    """배치 작업 관리자 - 중복 실행 방지 및 강화된 오류 처리"""
    
    def __init__(self, lock_dir: str = "/tmp/stockpilot_locks"):
        self.jobs: Dict[str, BatchJob] = {}
        self.executions: Dict[str, JobExecution] = {}
        self.lock_dir = Path(lock_dir)
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        
        # 실행 통계
        self.daily_stats: Dict[str, Dict[str, int]] = {}
        
        # 동시 실행 제한
        self.max_concurrent_jobs = 5
        self.running_jobs = set()
        
        # 오류 임계치
        self.error_threshold = 0.3  # 30% 실패율 초과 시 알림
        
        # 모니터링 강화
        self.execution_history: List[JobExecution] = []  # 최근 실행 이력
        self.max_history_size = 1000  # 최대 이력 크기
        self.alert_hooks: List[BatchAlertHook] = [LoggerBatchAlertHook()]
        self.process_monitor = psutil.Process()
        
        logger.info(f"배치 관리자 초기화 완료, 잠금 디렉토리: {self.lock_dir}")
    
    def register_job(self, job: BatchJob):
        """배치 작업 등록"""
        self.jobs[job.job_id] = job
        logger.info(f"배치 작업 등록: {job.name} ({job.job_id})")
    
    async def execute_job(self, job_id: str, force: bool = False) -> JobExecution:
        """배치 작업 실행 - 중복 방지 및 강화된 오류 처리"""
        if job_id not in self.jobs:
            raise ValueError(f"등록되지 않은 작업: {job_id}")
        
        job = self.jobs[job_id]
        execution = JobExecution(
            job_id=job_id,
            job_name=job.name,
            max_retries=job.max_retries
        )
        
        # 작업이 비활성화된 경우
        if not job.enabled and not force:
            execution.status = JobStatus.SKIPPED
            execution.error_message = "작업이 비활성화됨"
            self.executions[job_id] = execution
            return execution
        
        # 중복 실행 방지 잠금 획득
        lock_acquired = await self._acquire_lock(job_id, execution)
        if not lock_acquired:
            execution.status = JobStatus.SKIPPED
            execution.error_message = "이미 실행 중인 작업"
            self.executions[job_id] = execution
            return execution
        
        try:
            # 의존성 체크
            if not await self._check_dependencies(job):
                execution.status = JobStatus.FAILED
                execution.error_message = "의존성 작업 실패"
                return execution
            
            # 동시 실행 제한 체크
            while len(self.running_jobs) >= self.max_concurrent_jobs:
                logger.info(f"동시 실행 제한 대기 중: {job.name}")
                await asyncio.sleep(5)
            
            self.running_jobs.add(job_id)
            execution.status = JobStatus.RUNNING
            execution.start_time = datetime.now()
            
            logger.info(f"배치 작업 시작: {job.name} ({job_id})")
            
            # 타임아웃과 함께 작업 실행
            try:
                result = await asyncio.wait_for(
                    self._execute_with_retries(job, execution),
                    timeout=job.timeout
                )
                
                execution.result = result
                execution.status = JobStatus.SUCCESS
                logger.info(f"배치 작업 성공: {job.name}, 결과: {result}")
                
            except asyncio.TimeoutError:
                execution.status = JobStatus.FAILED
                execution.error_message = f"작업 타임아웃 ({job.timeout}초)"
                logger.error(f"배치 작업 타임아웃: {job.name}")
                
            except Exception as e:
                execution.status = JobStatus.FAILED
                execution.error_message = str(e)
                logger.error(f"배치 작업 실패: {job.name}, 오류: {str(e)}")
        
        finally:
            execution.end_time = datetime.now()
            if execution.start_time:
                execution.duration = (execution.end_time - execution.start_time).total_seconds()
            
            self.running_jobs.discard(job_id)
            await self._release_lock(execution)
            self.executions[job_id] = execution
            
            # 통계 업데이트
            await self._update_stats(job_id, execution.status)
            
            # 실행 이력에 추가
            self.execution_history.append(execution)
            if len(self.execution_history) > self.max_history_size:
                self.execution_history = self.execution_history[-self.max_history_size:]
            
            # 실패시 알림 전송
            if execution.status == JobStatus.FAILED:
                await self._send_failure_alert(execution)
        
        return execution
    
    async def _acquire_lock(self, job_id: str, execution: JobExecution) -> bool:
        """작업 잠금 획득 - 중복 실행 방지"""
        today = datetime.now().strftime("%Y-%m-%d")
        lock_file = self.lock_dir / f"{job_id}_{today}.lock"
        execution.lock_file_path = str(lock_file)
        
        try:
            # 잠금 파일 생성 및 배타적 잠금 시도
            fd = open(lock_file, 'w')
            fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # 잠금 파일에 실행 정보 기록
            lock_info = {
                "job_id": job_id,
                "pid": "python-process",  # 실제 구현에서는 os.getpid() 사용
                "start_time": datetime.now().isoformat(),
                "hostname": "localhost"  # 실제 구현에서는 socket.gethostname() 사용
            }
            json.dump(lock_info, fd)
            fd.flush()
            
            # 잠금 유지를 위해 파일 디스크립터 저장
            execution._lock_fd = fd
            
            logger.info(f"작업 잠금 획득: {job_id}")
            return True
            
        except (IOError, OSError) as e:
            logger.warning(f"작업 잠금 실패: {job_id}, 오류: {str(e)}")
            return False
    
    async def _release_lock(self, execution: JobExecution):
        """작업 잠금 해제"""
        try:
            if hasattr(execution, '_lock_fd'):
                execution._lock_fd.close()
            
            if execution.lock_file_path:
                lock_file = Path(execution.lock_file_path)
                if lock_file.exists():
                    lock_file.unlink()
                    logger.debug(f"작업 잠금 해제: {execution.job_id}")
                    
        except Exception as e:
            logger.warning(f"잠금 해제 중 오류: {execution.job_id}, {str(e)}")
    
    async def _execute_with_retries(self, job: BatchJob, execution: JobExecution) -> Any:
        """재시도 로직을 포함한 작업 실행"""
        last_exception = None
        
        for attempt in range(job.max_retries + 1):
            try:
                if attempt > 0:
                    # 지수적 백오프
                    backoff_time = min(300, 2 ** attempt)  # 최대 5분
                    logger.info(f"재시도 대기: {job.name}, 시도 {attempt}, 대기시간: {backoff_time}초")
                    await asyncio.sleep(backoff_time)
                
                execution.retry_count = attempt
                result = await job.func()
                return result
                
            except Exception as e:
                last_exception = e
                logger.warning(f"작업 실행 실패: {job.name}, 시도 {attempt + 1}/{job.max_retries + 1}, 오류: {str(e)}")
                
                # 치명적 오류는 재시도하지 않음
                if self._is_fatal_error(e):
                    logger.error(f"치명적 오류로 재시도 중단: {job.name}, {str(e)}")
                    break
        
        # 모든 재시도 실패
        raise last_exception
    
    def _is_fatal_error(self, error: Exception) -> bool:
        """치명적 오류 판단 (재시도하지 않을 오류들)"""
        fatal_errors = [
            "Authentication failed",
            "Invalid API key", 
            "Permission denied",
            "Configuration error"
        ]
        
        error_msg = str(error).lower()
        return any(fatal in error_msg for fatal in fatal_errors)
    
    async def _check_dependencies(self, job: BatchJob) -> bool:
        """의존성 작업 완료 상태 체크"""
        if not job.dependencies:
            return True
        
        for dep_job_id in job.dependencies:
            dep_execution = self.executions.get(dep_job_id)
            
            if not dep_execution or dep_execution.status != JobStatus.SUCCESS:
                logger.warning(f"의존성 작업 미완료: {dep_job_id} -> {job.job_id}")
                return False
        
        return True
    
    async def _update_stats(self, job_id: str, status: JobStatus):
        """일일 통계 업데이트"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        if today not in self.daily_stats:
            self.daily_stats[today] = {
                "total": 0,
                "success": 0,
                "failed": 0,
                "skipped": 0
            }
        
        self.daily_stats[today]["total"] += 1
        self.daily_stats[today][status.value] = self.daily_stats[today].get(status.value, 0) + 1
    
    async def execute_daily_batch(self, date: Optional[str] = None) -> Dict[str, JobExecution]:
        """일일 배치 작업 실행"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"일일 배치 작업 시작: {date}")
        
        results = {}
        
        # 우선순위별로 정렬
        sorted_jobs = sorted(
            self.jobs.values(), 
            key=lambda job: (job.priority.value, job.job_id)
        )
        
        for job in sorted_jobs:
            if job.enabled:
                try:
                    execution = await self.execute_job(job.job_id)
                    results[job.job_id] = execution
                    
                    # 치명적 실패 시 후속 작업 중단 여부 결정
                    if execution.status == JobStatus.FAILED and job.priority in [JobPriority.CRITICAL, JobPriority.HIGH]:
                        logger.error(f"중요 작업 실패로 후속 작업 검토 필요: {job.name}")
                        
                except Exception as e:
                    logger.error(f"배치 작업 실행 중 예외: {job.job_id}, {str(e)}")
                    results[job.job_id] = JobExecution(
                        job_id=job.job_id,
                        job_name=job.name,
                        status=JobStatus.FAILED,
                        error_message=str(e)
                    )
        
        # 배치 완료 통계 로깅
        await self._log_batch_summary(date, results)
        
        return results
    
    async def _log_batch_summary(self, date: str, results: Dict[str, JobExecution]):
        """배치 실행 결과 요약 로깅"""
        total = len(results)
        success = sum(1 for r in results.values() if r.status == JobStatus.SUCCESS)
        failed = sum(1 for r in results.values() if r.status == JobStatus.FAILED)
        skipped = sum(1 for r in results.values() if r.status == JobStatus.SKIPPED)
        
        # 실패율 계산
        failure_rate = (failed / total) if total > 0 else 0
        
        logger.info(
            f"일일 배치 완료: {date}, "
            f"총 {total}개 작업, "
            f"성공: {success}, 실패: {failed}, 생략: {skipped}, "
            f"실패율: {failure_rate:.1%}"
        )
        
        # 실패율이 임계치를 초과하면 경고
        if failure_rate > self.error_threshold:
            logger.warning(f"배치 작업 실패율 임계치 초과: {failure_rate:.1%} > {self.error_threshold:.1%}")
    
    def get_job_status(self, job_id: str) -> Optional[JobExecution]:
        """작업 상태 조회"""
        return self.executions.get(job_id)
    
    def get_daily_stats(self, date: Optional[str] = None) -> Dict[str, int]:
        """일일 통계 조회"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        return self.daily_stats.get(date, {})
    
    def get_running_jobs(self) -> List[str]:
        """현재 실행 중인 작업 목록"""
        return list(self.running_jobs)
    
    async def cleanup_old_locks(self, days: int = 7):
        """오래된 잠금 파일 정리"""
        cutoff_date = datetime.now() - timedelta(days=days)
        cleaned = 0
        
        for lock_file in self.lock_dir.glob("*.lock"):
            try:
                if lock_file.stat().st_mtime < cutoff_date.timestamp():
                    lock_file.unlink()
                    cleaned += 1
            except Exception as e:
                logger.warning(f"잠금 파일 정리 실패: {lock_file}, {str(e)}")
        
        if cleaned > 0:
            logger.info(f"오래된 잠금 파일 {cleaned}개 정리 완료")
    
    async def _send_failure_alert(self, execution: JobExecution):
        """배치 작업 실패 알림 전송"""
        additional_data = {
            "execution_id": execution.execution_id,
            "duration": execution.duration,
            "retry_count": execution.retry_count,
            "max_retries": execution.max_retries,
            "memory_peak_mb": execution.memory_peak_mb,
            "cpu_usage_percent": execution.cpu_usage_percent,
            "items_processed": execution.items_processed,
            "warnings": execution.warnings
        }
        
        for hook in self.alert_hooks:
            try:
                await hook.send_alert("failure", execution, additional_data)
            except Exception as e:
                logger.error(f"배치 실패 알림 전송 실패: {str(e)}")
    
    def add_alert_hook(self, hook: BatchAlertHook):
        """알림 훅 추가"""
        self.alert_hooks.append(hook)
    
    def get_recent_executions(self, limit: int = 50) -> List[JobExecution]:
        """최근 N회 실행 이력 조회"""
        return sorted(
            self.execution_history[-limit:], 
            key=lambda x: x.end_time or x.start_time or datetime.min,
            reverse=True
        )
    
    def get_execution_stats(self, job_id: Optional[str] = None, days: int = 7) -> Dict[str, Any]:
        """실행 통계 조회"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # 필터링: 최근 N일, 특정 작업 ID (선택사항)
        filtered_executions = []
        for execution in self.execution_history:
            end_time = execution.end_time or execution.start_time
            if end_time and end_time >= cutoff_date:
                if job_id is None or execution.job_id == job_id:
                    filtered_executions.append(execution)
        
        if not filtered_executions:
            return {"total": 0, "stats": {}}
        
        # 통계 계산
        total_count = len(filtered_executions)
        success_count = sum(1 for e in filtered_executions if e.status == JobStatus.SUCCESS)
        failed_count = sum(1 for e in filtered_executions if e.status == JobStatus.FAILED)
        
        # 평균 실행 시간
        durations = [e.duration for e in filtered_executions if e.duration]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # 평균 처리량
        throughputs = [e.throughput_per_second for e in filtered_executions if e.throughput_per_second]
        avg_throughput = sum(throughputs) / len(throughputs) if throughputs else 0
        
        # 평균 메모리/CPU 사용량
        memories = [e.memory_peak_mb for e in filtered_executions if e.memory_peak_mb]
        avg_memory = sum(memories) / len(memories) if memories else 0
        
        cpus = [e.cpu_usage_percent for e in filtered_executions if e.cpu_usage_percent]
        avg_cpu = sum(cpus) / len(cpus) if cpus else 0
        
        return {
            "total": total_count,
            "success": success_count,
            "failed": failed_count,
            "success_rate": (success_count / total_count) * 100 if total_count > 0 else 0,
            "avg_duration_seconds": round(avg_duration, 2),
            "avg_throughput_per_second": round(avg_throughput, 2),
            "avg_memory_peak_mb": round(avg_memory, 2),
            "avg_cpu_usage_percent": round(avg_cpu, 2),
            "stats": {
                "by_status": {
                    status.value: sum(1 for e in filtered_executions if e.status == status)
                    for status in JobStatus
                },
                "by_job": {}
            }
        }
    
    async def force_release_lock(self, job_id: str, reason: str = "Manual release") -> bool:
        """강제 잠금 해제"""
        today = datetime.now().strftime("%Y-%m-%d")
        lock_file = self.lock_dir / f"{job_id}_{today}.lock"
        
        try:
            if lock_file.exists():
                lock_file.unlink()
                logger.warning(f"강제 잠금 해제: {job_id}, 이유: {reason}")
                
                # 알림 전송
                for hook in self.alert_hooks:
                    try:
                        await hook.send_alert(
                            "lock_released",
                            JobExecution(job_id=job_id, job_name=f"Lock for {job_id}"),
                            {"reason": reason, "timestamp": datetime.now().isoformat()}
                        )
                    except Exception as e:
                        logger.error(f"강제 잠금 해제 알림 실패: {str(e)}")
                
                return True
            else:
                logger.info(f"잠금 파일이 존재하지 않음: {job_id}")
                return False
                
        except Exception as e:
            logger.error(f"강제 잠금 해제 실패: {job_id}, 오류: {str(e)}")
            return False
    
    def check_lock_expiration(self, max_age_hours: int = 24) -> List[str]:
        """만료된 잠금 파일 확인"""
        expired_locks = []
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        for lock_file in self.lock_dir.glob("*.lock"):
            try:
                if lock_file.stat().st_mtime < cutoff_time.timestamp():
                    # 잠금 파일에서 작업 ID 추출
                    job_id = lock_file.stem.rsplit("_", 1)[0]
                    expired_locks.append(job_id)
                    logger.warning(f"만료된 잠금 파일 발견: {job_id}")
                    
            except Exception as e:
                logger.warning(f"잠금 파일 상태 확인 실패: {lock_file}, {str(e)}")
        
        return expired_locks


# 전역 인스턴스
batch_manager = BatchManager()


def get_batch_manager() -> BatchManager:
    """배치 관리자 인스턴스 반환"""
    return batch_manager