"""
배치 작업 관리 API 엔드포인트 - 강화된 모니터링
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field

from app.jobs.batch_manager import get_batch_manager, JobStatus
from app.jobs.job_scheduler import get_job_scheduler
from app.jobs.jobs import register_all_jobs

router = APIRouter()


class JobExecutionResponse(BaseModel):
    """작업 실행 응답 모델 - 확장된 메트릭스"""
    job_id: str
    job_name: str
    status: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration: Optional[float] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    result: Optional[Dict[str, Any]] = None
    # 확장 메트릭스
    execution_id: Optional[str] = None
    items_processed: Optional[int] = None
    throughput_per_second: Optional[float] = None
    memory_peak_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    warnings: List[str] = Field(default_factory=list)
    progress_percentage: Optional[float] = None


class BatchStatsResponse(BaseModel):
    """배치 통계 응답 모델"""
    date: str
    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    failure_rate: float = 0.0


class ExecutionStatsResponse(BaseModel):
    """실행 통계 응답 모델"""
    total: int
    success: int
    failed: int
    success_rate: float
    avg_duration_seconds: float
    avg_throughput_per_second: float
    avg_memory_peak_mb: float
    avg_cpu_usage_percent: float
    stats: Dict[str, Any]


class LockStatusResponse(BaseModel):
    """잠금 상태 응답 모델"""
    job_id: str
    lock_exists: bool
    lock_age_hours: Optional[float] = None
    is_expired: bool = False


class ForceReleaseRequest(BaseModel):
    """강제 잠금 해제 요청 모델"""
    reason: str = Field(default="Manual release", description="해제 사유")


@router.post("/jobs/{job_id}/execute")
async def execute_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    force: bool = False
):
    """개별 배치 작업 실행"""
    try:
        batch_manager = get_batch_manager()
        
        # 백그라운드에서 실행
        background_tasks.add_task(batch_manager.execute_job, job_id, force)
        
        return {
            "message": f"배치 작업 실행 시작: {job_id}",
            "job_id": job_id,
            "force": force
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"작업 실행 실패: {str(e)}")


@router.get("/jobs/{job_id}/status", response_model=JobExecutionResponse)
async def get_job_status(job_id: str):
    """작업 상태 조회"""
    try:
        batch_manager = get_batch_manager()
        execution = batch_manager.get_job_status(job_id)
        
        if not execution:
            raise HTTPException(status_code=404, detail="작업 실행 기록을 찾을 수 없습니다")
        
        return JobExecutionResponse(
            job_id=execution.job_id,
            job_name=execution.job_name,
            status=execution.status.value,
            start_time=execution.start_time.isoformat() if execution.start_time else None,
            end_time=execution.end_time.isoformat() if execution.end_time else None,
            duration=execution.duration,
            error_message=execution.error_message,
            retry_count=execution.retry_count,
            result=execution.result,
            # 확장 메트릭스
            execution_id=execution.execution_id,
            items_processed=execution.items_processed,
            throughput_per_second=execution.throughput_per_second,
            memory_peak_mb=execution.memory_peak_mb,
            cpu_usage_percent=execution.cpu_usage_percent,
            warnings=execution.warnings,
            progress_percentage=execution.progress_percentage
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"상태 조회 실패: {str(e)}")


@router.get("/jobs")
async def list_jobs():
    """등록된 배치 작업 목록"""
    try:
        batch_manager = get_batch_manager()
        jobs = []
        
        for job_id, job in batch_manager.jobs.items():
            execution = batch_manager.get_job_status(job_id)
            
            jobs.append({
                "job_id": job_id,
                "name": job.name,
                "description": job.description,
                "priority": job.priority.name,
                "enabled": job.enabled,
                "max_retries": job.max_retries,
                "timeout": job.timeout,
                "dependencies": job.dependencies,
                "last_status": execution.status.value if execution else "never_run",
                "last_run": execution.end_time.isoformat() if execution and execution.end_time else None
            })
        
        return {"jobs": jobs}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"작업 목록 조회 실패: {str(e)}")


@router.post("/daily-batch/run")
async def run_daily_batch(background_tasks: BackgroundTasks, date: Optional[str] = None):
    """일일 배치 작업 실행"""
    try:
        job_scheduler = get_job_scheduler()
        
        # 백그라운드에서 실행
        background_tasks.add_task(job_scheduler.run_daily_batch)
        
        return {
            "message": "일일 배치 작업 실행 시작",
            "date": date or "today"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"일일 배치 실행 실패: {str(e)}")


@router.get("/daily-batch/stats", response_model=BatchStatsResponse)
async def get_daily_stats(date: Optional[str] = None):
    """일일 배치 통계 조회"""
    try:
        batch_manager = get_batch_manager()
        stats = batch_manager.get_daily_stats(date)
        
        total = stats.get("total", 0)
        success = stats.get("success", 0)
        failed = stats.get("failed", 0)
        skipped = stats.get("skipped", 0)
        
        failure_rate = (failed / total * 100) if total > 0 else 0.0
        
        return BatchStatsResponse(
            date=date or "today",
            total=total,
            success=success,
            failed=failed,
            skipped=skipped,
            failure_rate=failure_rate
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")


@router.get("/running")
async def get_running_jobs():
    """현재 실행 중인 작업 목록"""
    try:
        batch_manager = get_batch_manager()
        running_jobs = batch_manager.get_running_jobs()
        
        return {
            "running_jobs": running_jobs,
            "count": len(running_jobs)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"실행 중 작업 조회 실패: {str(e)}")


@router.get("/schedule")
async def get_schedule():
    """예약된 작업 스케줄 조회"""
    try:
        job_scheduler = get_job_scheduler()
        scheduled_jobs = job_scheduler.get_scheduled_jobs()
        
        schedule = []
        for job_id, scheduled_job in scheduled_jobs.items():
            schedule.append({
                "job_id": job_id,
                "name": scheduled_job.name,
                "cron_expression": scheduled_job.cron_expression,
                "description": scheduled_job.description,
                "enabled": scheduled_job.enabled,
                "next_run": scheduled_job.next_run.isoformat() if scheduled_job.next_run else None
            })
        
        return {"scheduled_jobs": schedule}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"스케줄 조회 실패: {str(e)}")


@router.post("/schedule/{job_id}/enable")
async def enable_scheduled_job(job_id: str):
    """예약 작업 활성화"""
    try:
        job_scheduler = get_job_scheduler()
        job_scheduler.enable_job(job_id)
        
        return {
            "message": f"작업 활성화: {job_id}",
            "job_id": job_id,
            "enabled": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"작업 활성화 실패: {str(e)}")


@router.post("/schedule/{job_id}/disable")
async def disable_scheduled_job(job_id: str):
    """예약 작업 비활성화"""
    try:
        job_scheduler = get_job_scheduler()
        job_scheduler.disable_job(job_id)
        
        return {
            "message": f"작업 비활성화: {job_id}",
            "job_id": job_id,
            "enabled": False
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"작업 비활성화 실패: {str(e)}")


@router.post("/initialize")
async def initialize_batch_system():
    """배치 시스템 초기화 (작업 등록 및 스케줄 설정)"""
    try:
        # 배치 작업들 등록
        register_all_jobs()
        
        # 스케줄러 설정
        job_scheduler = get_job_scheduler()
        job_scheduler.setup_default_schedule()
        
        # 스케줄러 시작
        if not job_scheduler.is_running:
            job_scheduler.start()
        
        return {
            "message": "배치 시스템 초기화 완료",
            "jobs_registered": len(get_batch_manager().jobs),
            "scheduler_running": job_scheduler.is_running
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"배치 시스템 초기화 실패: {str(e)}")


@router.get("/health")
async def batch_system_health():
    """배치 시스템 상태 확인"""
    try:
        batch_manager = get_batch_manager()
        job_scheduler = get_job_scheduler()
        
        # 최근 실행 상태 확인
        recent_failures = 0
        total_executions = len(batch_manager.executions)
        
        for execution in batch_manager.executions.values():
            if execution.status == JobStatus.FAILED:
                recent_failures += 1
        
        failure_rate = (recent_failures / total_executions) if total_executions > 0 else 0
        
        return {
            "status": "healthy" if failure_rate < 0.3 else "degraded",
            "scheduler_running": job_scheduler.is_running,
            "total_jobs": len(batch_manager.jobs),
            "running_jobs": len(batch_manager.running_jobs),
            "total_executions": total_executions,
            "recent_failures": recent_failures,
            "failure_rate": f"{failure_rate:.1%}",
            "scheduled_jobs": len(job_scheduler.scheduled_jobs)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"상태 확인 실패: {str(e)}")


# 강화된 모니터링 엔드포인트들

@router.get("/executions/recent")
async def get_recent_executions(
    limit: int = Query(default=50, ge=1, le=500, description="조회할 실행 이력 수")
):
    """최근 N회 실행 이력 조회"""
    try:
        batch_manager = get_batch_manager()
        recent_executions = batch_manager.get_recent_executions(limit)
        
        executions = []
        for execution in recent_executions:
            executions.append({
                "execution_id": execution.execution_id,
                "job_id": execution.job_id,
                "job_name": execution.job_name,
                "status": execution.status.value,
                "start_time": execution.start_time.isoformat() if execution.start_time else None,
                "end_time": execution.end_time.isoformat() if execution.end_time else None,
                "duration": execution.duration,
                "error_message": execution.error_message,
                "retry_count": execution.retry_count,
                "items_processed": execution.items_processed,
                "throughput_per_second": execution.throughput_per_second,
                "memory_peak_mb": execution.memory_peak_mb,
                "cpu_usage_percent": execution.cpu_usage_percent,
                "warnings": execution.warnings,
                "progress_percentage": execution.progress_percentage
            })
        
        return {
            "executions": executions,
            "total_count": len(executions),
            "limit": limit
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"실행 이력 조회 실패: {str(e)}")


@router.get("/executions/stats", response_model=ExecutionStatsResponse)
async def get_execution_stats(
    job_id: Optional[str] = Query(default=None, description="특정 작업 ID (선택)"),
    days: int = Query(default=7, ge=1, le=90, description="조회 기간 (일)")
):
    """실행 통계 조회"""
    try:
        batch_manager = get_batch_manager()
        stats = batch_manager.get_execution_stats(job_id, days)
        
        return ExecutionStatsResponse(**stats)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"실행 통계 조회 실패: {str(e)}")


@router.get("/jobs/{job_id}/lock/status", response_model=LockStatusResponse)
async def get_lock_status(job_id: str):
    """작업 잠금 상태 조회"""
    try:
        batch_manager = get_batch_manager()
        
        # 오늘 날짜의 잠금 파일 확인
        today = datetime.now().strftime("%Y-%m-%d")
        lock_file = batch_manager.lock_dir / f"{job_id}_{today}.lock"
        
        lock_exists = lock_file.exists()
        lock_age_hours = None
        is_expired = False
        
        if lock_exists:
            lock_age_hours = (datetime.now().timestamp() - lock_file.stat().st_mtime) / 3600
            is_expired = lock_age_hours > 24  # 24시간 초과시 만료
        
        return LockStatusResponse(
            job_id=job_id,
            lock_exists=lock_exists,
            lock_age_hours=lock_age_hours,
            is_expired=is_expired
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"잠금 상태 조회 실패: {str(e)}")


@router.post("/jobs/{job_id}/lock/release")
async def force_release_lock(job_id: str, request: ForceReleaseRequest):
    """강제 잠금 해제"""
    try:
        batch_manager = get_batch_manager()
        success = await batch_manager.force_release_lock(job_id, request.reason)
        
        if success:
            return {
                "message": f"잠금 해제 성공: {job_id}",
                "job_id": job_id,
                "reason": request.reason,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "message": f"잠금 파일이 존재하지 않음: {job_id}",
                "job_id": job_id,
                "reason": request.reason,
                "timestamp": datetime.now().isoformat()
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"잠금 해제 실패: {str(e)}")


@router.get("/locks/expired")
async def get_expired_locks(
    max_age_hours: int = Query(default=24, ge=1, le=168, description="최대 잠금 유지 시간 (시간)")
):
    """만료된 잠금 파일 조회"""
    try:
        batch_manager = get_batch_manager()
        expired_locks = batch_manager.check_lock_expiration(max_age_hours)
        
        return {
            "expired_locks": expired_locks,
            "count": len(expired_locks),
            "max_age_hours": max_age_hours
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"만료된 잠금 조회 실패: {str(e)}")


@router.post("/locks/cleanup")
async def cleanup_expired_locks(
    max_age_hours: int = Query(default=24, ge=1, le=168, description="최대 잠금 유지 시간 (시간)"),
    force: bool = Query(default=False, description="강제 정리 여부")
):
    """만료된 잠금 파일 정리"""
    try:
        batch_manager = get_batch_manager()
        
        # 먼저 만료된 잠금들 확인
        expired_locks = batch_manager.check_lock_expiration(max_age_hours)
        
        if not expired_locks:
            return {
                "message": "만료된 잠금 파일이 없습니다",
                "cleaned_count": 0,
                "max_age_hours": max_age_hours
            }
        
        if not force and len(expired_locks) > 5:
            return {
                "message": f"만료된 잠금 파일이 {len(expired_locks)}개 있습니다. force=true로 강제 정리하세요",
                "expired_locks": expired_locks,
                "force_required": True
            }
        
        # 만료된 잠금들 정리
        cleaned_count = 0
        for job_id in expired_locks:
            success = await batch_manager.force_release_lock(job_id, "Expired lock cleanup")
            if success:
                cleaned_count += 1
        
        return {
            "message": f"만료된 잠금 파일 {cleaned_count}개 정리 완료",
            "cleaned_count": cleaned_count,
            "total_expired": len(expired_locks),
            "max_age_hours": max_age_hours
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"만료된 잠금 정리 실패: {str(e)}")