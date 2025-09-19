"""
작업 스케줄러
일정 기반 배치 작업 실행 관리
"""

import asyncio
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.jobs.batch_manager import BatchManager, get_batch_manager


@dataclass
class ScheduledJob:
    """예약된 작업"""
    name: str
    job_id: str
    cron_expression: str
    description: str
    enabled: bool = True
    next_run: Optional[datetime] = None


class JobScheduler:
    """배치 작업 스케줄러"""
    
    def __init__(self, batch_manager: BatchManager = None):
        self.batch_manager = batch_manager or get_batch_manager()
        self.scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
        self.scheduled_jobs: Dict[str, ScheduledJob] = {}
        self.is_running = False
        
        logger.info("작업 스케줄러 초기화 완료")
    
    def add_scheduled_job(
        self,
        job_id: str,
        name: str,
        cron_expression: str,
        description: str,
        enabled: bool = True
    ):
        """예약 작업 추가"""
        scheduled_job = ScheduledJob(
            name=name,
            job_id=job_id,
            cron_expression=cron_expression,
            description=description,
            enabled=enabled
        )
        
        self.scheduled_jobs[job_id] = scheduled_job
        
        if enabled:
            try:
                # 크론 트리거 생성 및 스케줄러에 추가
                trigger = CronTrigger.from_crontab(cron_expression, timezone="Asia/Seoul")
                
                self.scheduler.add_job(
                    func=self._execute_scheduled_job,
                    args=[job_id],
                    trigger=trigger,
                    id=f"scheduled_{job_id}",
                    name=name,
                    misfire_grace_time=300,  # 5분 지연 허용
                    coalesce=True,  # 중복 실행 방지
                    max_instances=1,  # 동시 실행 방지
                    replace_existing=True
                )
                
                # 다음 실행 시간 계산
                scheduled_job.next_run = self.scheduler.get_job(f"scheduled_{job_id}").next_run_time
                
                logger.info(f"예약 작업 추가: {name} ({cron_expression})")
                
            except Exception as e:
                logger.error(f"예약 작업 추가 실패: {name}, 오류: {str(e)}")
    
    async def _execute_scheduled_job(self, job_id: str):
        """예약된 작업 실행"""
        try:
            logger.info(f"예약 작업 실행: {job_id}")
            execution = await self.batch_manager.execute_job(job_id)
            
            # 다음 실행 시간 업데이트
            if job_id in self.scheduled_jobs:
                scheduler_job = self.scheduler.get_job(f"scheduled_{job_id}")
                if scheduler_job:
                    self.scheduled_jobs[job_id].next_run = scheduler_job.next_run_time
            
            logger.info(f"예약 작업 완료: {job_id}, 상태: {execution.status.value}")
            
        except Exception as e:
            logger.error(f"예약 작업 실행 실패: {job_id}, 오류: {str(e)}")
    
    def start(self):
        """스케줄러 시작"""
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            logger.info("작업 스케줄러 시작됨")
    
    def stop(self):
        """스케줄러 중단"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("작업 스케줄러 중단됨")
    
    def enable_job(self, job_id: str):
        """작업 활성화"""
        if job_id in self.scheduled_jobs:
            self.scheduled_jobs[job_id].enabled = True
            
            # 스케줄러에서 다시 활성화
            scheduled_job = self.scheduled_jobs[job_id]
            self.add_scheduled_job(
                job_id=job_id,
                name=scheduled_job.name,
                cron_expression=scheduled_job.cron_expression,
                description=scheduled_job.description,
                enabled=True
            )
            
            logger.info(f"작업 활성화: {job_id}")
    
    def disable_job(self, job_id: str):
        """작업 비활성화"""
        if job_id in self.scheduled_jobs:
            self.scheduled_jobs[job_id].enabled = False
            
            # 스케줄러에서 제거
            scheduler_job_id = f"scheduled_{job_id}"
            if self.scheduler.get_job(scheduler_job_id):
                self.scheduler.remove_job(scheduler_job_id)
            
            logger.info(f"작업 비활성화: {job_id}")
    
    def get_scheduled_jobs(self) -> Dict[str, ScheduledJob]:
        """예약된 작업 목록 조회"""
        return self.scheduled_jobs.copy()
    
    def get_next_run_time(self, job_id: str) -> Optional[datetime]:
        """다음 실행 시간 조회"""
        scheduler_job_id = f"scheduled_{job_id}"
        job = self.scheduler.get_job(scheduler_job_id)
        return job.next_run_time if job else None
    
    async def run_daily_batch(self):
        """일일 배치 작업 실행 (수동 실행)"""
        logger.info("수동 일일 배치 작업 실행")
        results = await self.batch_manager.execute_daily_batch()
        return results
    
    def setup_default_schedule(self):
        """기본 스케줄 설정"""
        # 일일 배치 작업들을 예약
        default_jobs = [
            {
                "job_id": "daily_data_collection",
                "name": "일일 데이터 수집",
                "cron": "0 1 * * *",  # 매일 새벽 1시
                "description": "일일 주식 데이터 및 뉴스 수집"
            },
            {
                "job_id": "daily_ai_analysis", 
                "name": "일일 AI 분석",
                "cron": "0 2 * * *",  # 매일 새벽 2시
                "description": "AI 기반 주식 분석 및 시그널 생성"
            },
            {
                "job_id": "daily_cleanup",
                "name": "일일 정리 작업",
                "cron": "0 3 * * *",  # 매일 새벽 3시
                "description": "로그 정리, 임시 파일 삭제 등"
            },
            {
                "job_id": "usage_report",
                "name": "사용량 리포트",
                "cron": "0 4 * * *",  # 매일 새벽 4시
                "description": "OpenAI API 사용량 및 비용 리포트"
            },
            {
                "job_id": "health_check_report",
                "name": "시스템 헬스체크",
                "cron": "*/30 * * * *",  # 30분마다
                "description": "시스템 상태 점검 및 알림"
            }
        ]
        
        for job_config in default_jobs:
            self.add_scheduled_job(
                job_id=job_config["job_id"],
                name=job_config["name"],
                cron_expression=job_config["cron"],
                description=job_config["description"]
            )
        
        logger.info(f"기본 스케줄 설정 완료: {len(default_jobs)}개 작업")


# 전역 인스턴스
job_scheduler = JobScheduler()


def get_job_scheduler() -> JobScheduler:
    """작업 스케줄러 인스턴스 반환"""
    return job_scheduler