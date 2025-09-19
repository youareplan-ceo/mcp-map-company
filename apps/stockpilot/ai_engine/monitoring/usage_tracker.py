"""
사용량 추적 모듈 - AI 엔진의 모든 사용량을 추적하고 분석
"""

import logging
import asyncio
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
import sqlite3
import aiosqlite
from collections import defaultdict, deque
import numpy as np

from ..config.model_policy import ModelTier
from ..routing.model_router import ModelRequest, ModelResponse

logger = logging.getLogger(__name__)

class MetricType(Enum):
    """메트릭 타입"""
    REQUEST_COUNT = "request_count"
    TOKEN_USAGE = "token_usage"
    COST = "cost"
    RESPONSE_TIME = "response_time"
    ERROR_RATE = "error_rate"
    CACHE_HIT_RATE = "cache_hit_rate"

@dataclass
class UsageMetric:
    """사용량 메트릭"""
    metric_type: MetricType
    value: float
    unit: str
    timestamp: datetime
    dimensions: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ModelUsageRecord:
    """모델 사용 기록"""
    request_id: str
    model_name: str
    model_tier: ModelTier
    task_type: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float
    response_time_ms: float
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None
    cache_hit: bool = False
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DailyUsageSummary:
    """일일 사용량 요약"""
    date: date
    total_requests: int
    total_tokens: int
    total_cost: float
    avg_response_time_ms: float
    success_rate: float
    cache_hit_rate: float
    model_breakdown: Dict[str, Dict[str, Any]]
    task_type_breakdown: Dict[str, int]
    error_summary: Dict[str, int]

class UsageDatabase:
    """사용량 데이터베이스"""
    
    def __init__(self, db_path: str = "usage_tracking.db"):
        self.db_path = db_path
    
    async def initialize(self):
        """데이터베이스 초기화"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS usage_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    model_tier TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    cost REAL NOT NULL,
                    response_time_ms REAL NOT NULL,
                    timestamp DATETIME NOT NULL,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    cache_hit BOOLEAN DEFAULT FALSE,
                    user_id TEXT,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS daily_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL UNIQUE,
                    total_requests INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    total_cost REAL NOT NULL,
                    avg_response_time_ms REAL NOT NULL,
                    success_rate REAL NOT NULL,
                    cache_hit_rate REAL NOT NULL,
                    model_breakdown TEXT NOT NULL,
                    task_type_breakdown TEXT NOT NULL,
                    error_summary TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_type TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    dimensions TEXT,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 인덱스 생성
            await db.execute('CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage_records(timestamp)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_usage_model ON usage_records(model_name)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_usage_task_type ON usage_records(task_type)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp)')
            
            await db.commit()
            logger.info("Usage database initialized")
    
    async def save_usage_record(self, record: ModelUsageRecord):
        """사용량 기록 저장"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO usage_records 
                (request_id, model_name, model_tier, task_type, input_tokens, 
                 output_tokens, total_tokens, cost, response_time_ms, timestamp, 
                 success, error_message, cache_hit, user_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.request_id,
                record.model_name,
                record.model_tier.value,
                record.task_type,
                record.input_tokens,
                record.output_tokens,
                record.total_tokens,
                record.cost,
                record.response_time_ms,
                record.timestamp,
                record.success,
                record.error_message,
                record.cache_hit,
                record.user_id,
                json.dumps(record.metadata)
            ))
            await db.commit()
    
    async def save_metric(self, metric: UsageMetric):
        """메트릭 저장"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO metrics (metric_type, value, unit, timestamp, dimensions, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                metric.metric_type.value,
                metric.value,
                metric.unit,
                metric.timestamp,
                json.dumps(metric.dimensions),
                json.dumps(metric.metadata)
            ))
            await db.commit()
    
    async def get_usage_records(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        model_name: Optional[str] = None,
        limit: int = 1000
    ) -> List[ModelUsageRecord]:
        """사용량 기록 조회"""
        query = "SELECT * FROM usage_records WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
        
        if model_name:
            query += " AND model_name = ?"
            params.append(model_name)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        records = []
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(query, params) as cursor:
                async for row in cursor:
                    records.append(ModelUsageRecord(
                        request_id=row[1],
                        model_name=row[2],
                        model_tier=ModelTier(row[3]),
                        task_type=row[4],
                        input_tokens=row[5],
                        output_tokens=row[6],
                        total_tokens=row[7],
                        cost=row[8],
                        response_time_ms=row[9],
                        timestamp=datetime.fromisoformat(row[10]),
                        success=bool(row[11]),
                        error_message=row[12],
                        cache_hit=bool(row[13]),
                        user_id=row[14],
                        metadata=json.loads(row[15]) if row[15] else {}
                    ))
        
        return records
    
    async def save_daily_summary(self, summary: DailyUsageSummary):
        """일일 요약 저장"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO daily_summaries 
                (date, total_requests, total_tokens, total_cost, avg_response_time_ms,
                 success_rate, cache_hit_rate, model_breakdown, task_type_breakdown, error_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                summary.date,
                summary.total_requests,
                summary.total_tokens,
                summary.total_cost,
                summary.avg_response_time_ms,
                summary.success_rate,
                summary.cache_hit_rate,
                json.dumps(summary.model_breakdown),
                json.dumps(summary.task_type_breakdown),
                json.dumps(summary.error_summary)
            ))
            await db.commit()

class UsageTracker:
    """사용량 추적기"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db = UsageDatabase(db_path or "usage_tracking.db")
        self.real_time_metrics = defaultdict(deque)
        self.metric_windows = {
            MetricType.REQUEST_COUNT: deque(maxlen=1000),
            MetricType.TOKEN_USAGE: deque(maxlen=1000),
            MetricType.COST: deque(maxlen=1000),
            MetricType.RESPONSE_TIME: deque(maxlen=1000),
            MetricType.ERROR_RATE: deque(maxlen=1000)
        }
        
        # 일일 집계용 임시 저장소
        self.daily_aggregator = defaultdict(list)
        self.last_summary_date = None
    
    async def initialize(self):
        """추적기 초기화"""
        await self.db.initialize()
        self.last_summary_date = date.today() - timedelta(days=1)
        
        # 백그라운드 태스크 시작
        asyncio.create_task(self._periodic_summary_task())
    
    async def track_model_usage(
        self,
        request: ModelRequest,
        response: ModelResponse,
        cache_hit: bool = False,
        user_id: Optional[str] = None
    ):
        """모델 사용량 추적"""
        try:
            record = ModelUsageRecord(
                request_id=request.task_id,
                model_name=response.model_name,
                model_tier=response.model_tier,
                task_type=request.task_type,
                input_tokens=response.usage.get("prompt_tokens", 0),
                output_tokens=response.usage.get("completion_tokens", 0),
                total_tokens=response.usage.get("total_tokens", 0),
                cost=response.cost,
                response_time_ms=response.processing_time_ms,
                timestamp=datetime.now(),
                success=True,
                cache_hit=cache_hit,
                user_id=user_id,
                metadata={
                    "content_type": request.content_type.value,
                    "priority": request.priority,
                    "confidence_score": response.confidence_score
                }
            )
            
            # 데이터베이스에 저장
            await self.db.save_usage_record(record)
            
            # 실시간 메트릭 업데이트
            await self._update_real_time_metrics(record)
            
            # 일일 집계에 추가
            today = date.today()
            self.daily_aggregator[today].append(record)
            
            logger.debug(f"Tracked usage for request {request.task_id}")
            
        except Exception as e:
            logger.error(f"Failed to track model usage: {e}")
    
    async def track_error(
        self,
        request: ModelRequest,
        error_message: str,
        user_id: Optional[str] = None
    ):
        """오류 발생 추적"""
        try:
            record = ModelUsageRecord(
                request_id=request.task_id,
                model_name="unknown",
                model_tier=ModelTier.MINI,  # 기본값
                task_type=request.task_type,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                cost=0.0,
                response_time_ms=0.0,
                timestamp=datetime.now(),
                success=False,
                error_message=error_message,
                user_id=user_id,
                metadata={"content_type": request.content_type.value, "priority": request.priority}
            )
            
            await self.db.save_usage_record(record)
            
            # 오류율 메트릭 업데이트
            await self._update_error_metrics(record)
            
            logger.debug(f"Tracked error for request {request.task_id}")
            
        except Exception as e:
            logger.error(f"Failed to track error: {e}")
    
    async def track_custom_metric(
        self,
        metric_type: MetricType,
        value: float,
        unit: str,
        dimensions: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """커스텀 메트릭 추적"""
        metric = UsageMetric(
            metric_type=metric_type,
            value=value,
            unit=unit,
            timestamp=datetime.now(),
            dimensions=dimensions or {},
            metadata=metadata or {}
        )
        
        await self.db.save_metric(metric)
        
        # 실시간 메트릭에 추가
        self.metric_windows[metric_type].append((datetime.now(), value))
    
    async def get_real_time_stats(self) -> Dict[str, Any]:
        """실시간 통계 조회"""
        stats = {}
        
        for metric_type, values in self.metric_windows.items():
            if values:
                recent_values = [v for t, v in values if (datetime.now() - t).total_seconds() < 3600]
                
                if recent_values:
                    stats[metric_type.value] = {
                        "current": recent_values[-1] if recent_values else 0,
                        "avg_1h": np.mean(recent_values),
                        "min_1h": np.min(recent_values),
                        "max_1h": np.max(recent_values),
                        "count_1h": len(recent_values)
                    }
        
        return stats
    
    async def get_usage_summary(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """사용량 요약 조회"""
        if start_date is None:
            start_date = date.today() - timedelta(days=7)
        if end_date is None:
            end_date = date.today()
        
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        records = await self.db.get_usage_records(
            start_date=start_datetime,
            end_date=end_datetime,
            limit=10000
        )
        
        if not records:
            return {
                "period": f"{start_date} to {end_date}",
                "total_requests": 0,
                "total_cost": 0.0,
                "total_tokens": 0
            }
        
        # 집계 계산
        total_requests = len(records)
        total_cost = sum(r.cost for r in records)
        total_tokens = sum(r.total_tokens for r in records)
        successful_requests = sum(1 for r in records if r.success)
        cached_requests = sum(1 for r in records if r.cache_hit)
        
        # 모델별 집계
        model_stats = defaultdict(lambda: {"requests": 0, "cost": 0.0, "tokens": 0})
        for record in records:
            model_stats[record.model_name]["requests"] += 1
            model_stats[record.model_name]["cost"] += record.cost
            model_stats[record.model_name]["tokens"] += record.total_tokens
        
        # 태스크 타입별 집계
        task_stats = defaultdict(int)
        for record in records:
            task_stats[record.task_type] += 1
        
        # 시간대별 집계
        hourly_stats = defaultdict(int)
        for record in records:
            hour = record.timestamp.hour
            hourly_stats[hour] += 1
        
        return {
            "period": f"{start_date} to {end_date}",
            "total_requests": total_requests,
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "success_rate": successful_requests / total_requests if total_requests > 0 else 0,
            "cache_hit_rate": cached_requests / total_requests if total_requests > 0 else 0,
            "avg_cost_per_request": total_cost / total_requests if total_requests > 0 else 0,
            "avg_tokens_per_request": total_tokens / total_requests if total_requests > 0 else 0,
            "model_breakdown": dict(model_stats),
            "task_type_breakdown": dict(task_stats),
            "hourly_distribution": dict(hourly_stats)
        }
    
    async def get_cost_analysis(self, days: int = 30) -> Dict[str, Any]:
        """비용 분석 조회"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        records = await self.db.get_usage_records(
            start_date=datetime.combine(start_date, datetime.min.time()),
            end_date=datetime.combine(end_date, datetime.max.time()),
            limit=50000
        )
        
        if not records:
            return {"period": f"Last {days} days", "total_cost": 0.0}
        
        # 일별 비용 추이
        daily_costs = defaultdict(float)
        for record in records:
            record_date = record.timestamp.date()
            daily_costs[record_date] += record.cost
        
        # 모델 티어별 비용
        tier_costs = defaultdict(float)
        for record in records:
            tier_costs[record.model_tier.value] += record.cost
        
        # 가장 비싼 요청들
        expensive_requests = sorted(records, key=lambda r: r.cost, reverse=True)[:10]
        
        total_cost = sum(r.cost for r in records)
        
        return {
            "period": f"Last {days} days",
            "total_cost": total_cost,
            "daily_average": total_cost / days,
            "daily_costs": dict(daily_costs),
            "tier_breakdown": dict(tier_costs),
            "expensive_requests": [
                {
                    "request_id": r.request_id,
                    "model_name": r.model_name,
                    "cost": r.cost,
                    "tokens": r.total_tokens,
                    "timestamp": r.timestamp.isoformat()
                }
                for r in expensive_requests
            ],
            "cost_trends": self._calculate_cost_trends(daily_costs, days)
        }
    
    async def _update_real_time_metrics(self, record: ModelUsageRecord):
        """실시간 메트릭 업데이트"""
        now = datetime.now()
        
        # 요청 수 메트릭
        self.metric_windows[MetricType.REQUEST_COUNT].append((now, 1))
        
        # 토큰 사용량 메트릭
        self.metric_windows[MetricType.TOKEN_USAGE].append((now, record.total_tokens))
        
        # 비용 메트릭
        self.metric_windows[MetricType.COST].append((now, record.cost))
        
        # 응답 시간 메트릭
        self.metric_windows[MetricType.RESPONSE_TIME].append((now, record.response_time_ms))
    
    async def _update_error_metrics(self, record: ModelUsageRecord):
        """오류 메트릭 업데이트"""
        now = datetime.now()
        self.metric_windows[MetricType.ERROR_RATE].append((now, 1))
    
    def _calculate_cost_trends(self, daily_costs: Dict[date, float], days: int) -> Dict[str, Any]:
        """비용 트렌드 계산"""
        if len(daily_costs) < 2:
            return {"trend": "insufficient_data"}
        
        sorted_dates = sorted(daily_costs.keys())
        costs = [daily_costs[d] for d in sorted_dates]
        
        # 단순 선형 트렌드
        if len(costs) >= 7:
            recent_avg = np.mean(costs[-7:])
            previous_avg = np.mean(costs[-14:-7]) if len(costs) >= 14 else np.mean(costs[:-7])
            
            if previous_avg > 0:
                trend_percentage = ((recent_avg - previous_avg) / previous_avg) * 100
            else:
                trend_percentage = 0
            
            return {
                "trend": "increasing" if trend_percentage > 5 else "decreasing" if trend_percentage < -5 else "stable",
                "trend_percentage": trend_percentage,
                "recent_avg": recent_avg,
                "previous_avg": previous_avg
            }
        
        return {"trend": "insufficient_data"}
    
    async def _periodic_summary_task(self):
        """주기적 요약 태스크"""
        while True:
            try:
                await asyncio.sleep(3600)  # 1시간마다 실행
                
                today = date.today()
                yesterday = today - timedelta(days=1)
                
                # 어제 데이터가 있고 아직 요약하지 않았으면 요약 생성
                if (yesterday not in self.daily_aggregator and 
                    self.last_summary_date < yesterday):
                    
                    await self._generate_daily_summary(yesterday)
                    self.last_summary_date = yesterday
                
            except Exception as e:
                logger.error(f"Periodic summary task failed: {e}")
    
    async def _generate_daily_summary(self, target_date: date):
        """일일 요약 생성"""
        try:
            start_datetime = datetime.combine(target_date, datetime.min.time())
            end_datetime = datetime.combine(target_date, datetime.max.time())
            
            records = await self.db.get_usage_records(
                start_date=start_datetime,
                end_date=end_datetime,
                limit=50000
            )
            
            if not records:
                logger.info(f"No records found for {target_date}")
                return
            
            # 집계 계산
            total_requests = len(records)
            total_tokens = sum(r.total_tokens for r in records)
            total_cost = sum(r.cost for r in records)
            successful_requests = sum(1 for r in records if r.success)
            cached_requests = sum(1 for r in records if r.cache_hit)
            
            response_times = [r.response_time_ms for r in records if r.success]
            avg_response_time = np.mean(response_times) if response_times else 0
            
            # 모델별 집계
            model_breakdown = defaultdict(lambda: {"requests": 0, "cost": 0.0, "tokens": 0})
            for record in records:
                model_breakdown[record.model_name]["requests"] += 1
                model_breakdown[record.model_name]["cost"] += record.cost
                model_breakdown[record.model_name]["tokens"] += record.total_tokens
            
            # 태스크 타입별 집계
            task_type_breakdown = defaultdict(int)
            for record in records:
                task_type_breakdown[record.task_type] += 1
            
            # 오류 요약
            error_summary = defaultdict(int)
            for record in records:
                if not record.success and record.error_message:
                    error_summary[record.error_message] += 1
            
            # 요약 객체 생성
            summary = DailyUsageSummary(
                date=target_date,
                total_requests=total_requests,
                total_tokens=total_tokens,
                total_cost=total_cost,
                avg_response_time_ms=avg_response_time,
                success_rate=successful_requests / total_requests if total_requests > 0 else 0,
                cache_hit_rate=cached_requests / total_requests if total_requests > 0 else 0,
                model_breakdown=dict(model_breakdown),
                task_type_breakdown=dict(task_type_breakdown),
                error_summary=dict(error_summary)
            )
            
            # 데이터베이스에 저장
            await self.db.save_daily_summary(summary)
            
            logger.info(f"Generated daily summary for {target_date}")
            
        except Exception as e:
            logger.error(f"Failed to generate daily summary for {target_date}: {e}")

# 글로벌 사용량 추적기
usage_tracker = UsageTracker()

async def initialize_usage_tracking(db_path: Optional[str] = None):
    """사용량 추적 시스템 초기화"""
    global usage_tracker
    usage_tracker = UsageTracker(db_path)
    await usage_tracker.initialize()
    logger.info("Usage tracking system initialized")

async def track_model_request(
    request: ModelRequest,
    response: ModelResponse,
    cache_hit: bool = False,
    user_id: Optional[str] = None
):
    """모델 요청 추적"""
    await usage_tracker.track_model_usage(request, response, cache_hit, user_id)

async def track_request_error(
    request: ModelRequest,
    error_message: str,
    user_id: Optional[str] = None
):
    """요청 오류 추적"""
    await usage_tracker.track_error(request, error_message, user_id)

async def get_usage_statistics(days: int = 7) -> Dict[str, Any]:
    """사용량 통계 조회"""
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    return await usage_tracker.get_usage_summary(start_date, end_date)

async def get_real_time_metrics() -> Dict[str, Any]:
    """실시간 메트릭 조회"""
    return await usage_tracker.get_real_time_stats()

async def get_cost_analysis_report(days: int = 30) -> Dict[str, Any]:
    """비용 분석 리포트 조회"""
    return await usage_tracker.get_cost_analysis(days)