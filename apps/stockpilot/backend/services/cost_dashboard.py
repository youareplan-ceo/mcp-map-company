#!/usr/bin/env python3
"""
StockPilot 비용 대시보드 고도화 시스템
모델/채널/국가별 호출량·비용 집계, 실시간 그래프 시각화, 예산 알림 및 자동 제어
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import aioredis
import psutil
from collections import defaultdict, deque
import sqlite3
import os
from pathlib import Path

# 로깅 설정
logger = logging.getLogger(__name__)

class CostCategory(Enum):
    """비용 카테고리"""
    OPENAI_API = "openai_api"
    DATA_SOURCE = "data_source"
    INFRASTRUCTURE = "infrastructure"
    STORAGE = "storage"
    BANDWIDTH = "bandwidth"

class AlertLevel(Enum):
    """알림 레벨"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class CostMetric:
    """비용 메트릭 데이터 클래스"""
    timestamp: datetime
    category: CostCategory
    model: str
    channel: str
    country: str
    call_count: int
    token_count: int
    cost_usd: float
    response_time_ms: int
    user_id: Optional[str] = None
    session_id: Optional[str] = None

@dataclass
class BudgetRule:
    """예산 규칙 데이터 클래스"""
    name: str
    category: CostCategory
    model_filter: Optional[str] = None
    channel_filter: Optional[str] = None
    country_filter: Optional[str] = None
    daily_limit_usd: float = 100.0
    monthly_limit_usd: float = 3000.0
    alert_threshold_percent: float = 80.0
    auto_throttle_enabled: bool = True
    emergency_stop_enabled: bool = True

@dataclass
class CostAlert:
    """비용 알림 데이터 클래스"""
    alert_id: str
    level: AlertLevel
    category: CostCategory
    message: str
    current_cost: float
    limit_cost: float
    threshold_percent: float
    timestamp: datetime
    auto_action_taken: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

class CostTracker:
    """실시간 비용 추적기"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client = None
        self.cost_buffer = deque(maxlen=1000)  # 최근 1000개 메트릭 버퍼
        self.budget_rules: Dict[str, BudgetRule] = {}
        self.active_throttles: Dict[str, datetime] = {}
        
        # SQLite 데이터베이스 초기화
        self.db_path = Path("data/cost_metrics.db")
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()
        
        # 기본 예산 규칙 설정
        self._setup_default_budget_rules()

    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        self.redis_client = await aioredis.from_url(self.redis_url, decode_responses=True)
        logger.info("비용 추적기 초기화 완료")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self.redis_client:
            await self.redis_client.close()
        logger.info("비용 추적기 종료")

    def _init_database(self):
        """SQLite 데이터베이스 초기화"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 비용 메트릭 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cost_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    category TEXT NOT NULL,
                    model TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    country TEXT NOT NULL,
                    call_count INTEGER NOT NULL,
                    token_count INTEGER NOT NULL,
                    cost_usd REAL NOT NULL,
                    response_time_ms INTEGER NOT NULL,
                    user_id TEXT,
                    session_id TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 비용 알림 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cost_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT UNIQUE NOT NULL,
                    level TEXT NOT NULL,
                    category TEXT NOT NULL,
                    message TEXT NOT NULL,
                    current_cost REAL NOT NULL,
                    limit_cost REAL NOT NULL,
                    threshold_percent REAL NOT NULL,
                    timestamp DATETIME NOT NULL,
                    auto_action_taken BOOLEAN DEFAULT FALSE,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 인덱스 생성
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON cost_metrics(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON cost_metrics(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_model ON cost_metrics(model)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_channel ON cost_metrics(channel)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_country ON cost_metrics(country)")
            
            conn.commit()
            conn.close()
            logger.info("SQLite 데이터베이스 초기화 완료")
            
        except Exception as e:
            logger.error(f"데이터베이스 초기화 오류: {e}")

    def _setup_default_budget_rules(self):
        """기본 예산 규칙 설정"""
        default_rules = [
            BudgetRule(
                name="OpenAI GPT-4 일일 한도",
                category=CostCategory.OPENAI_API,
                model_filter="gpt-4",
                daily_limit_usd=50.0,
                monthly_limit_usd=1500.0,
                alert_threshold_percent=75.0,
                auto_throttle_enabled=True
            ),
            BudgetRule(
                name="OpenAI GPT-3.5 일일 한도",
                category=CostCategory.OPENAI_API,
                model_filter="gpt-3.5",
                daily_limit_usd=20.0,
                monthly_limit_usd=600.0,
                alert_threshold_percent=80.0,
                auto_throttle_enabled=True
            ),
            BudgetRule(
                name="한국 채널 일일 한도",
                category=CostCategory.OPENAI_API,
                channel_filter="korean",
                country_filter="KR",
                daily_limit_usd=100.0,
                monthly_limit_usd=3000.0,
                alert_threshold_percent=85.0,
                auto_throttle_enabled=True
            ),
            BudgetRule(
                name="데이터 소스 비용 한도",
                category=CostCategory.DATA_SOURCE,
                daily_limit_usd=30.0,
                monthly_limit_usd=900.0,
                alert_threshold_percent=70.0,
                auto_throttle_enabled=False
            )
        ]
        
        for rule in default_rules:
            self.budget_rules[rule.name] = rule
        
        logger.info(f"{len(default_rules)}개 기본 예산 규칙 설정 완료")

    async def track_cost(self, metric: CostMetric) -> List[CostAlert]:
        """비용 메트릭 추적 및 알림 생성"""
        alerts = []
        
        try:
            # 메모리 버퍼에 추가
            self.cost_buffer.append(metric)
            
            # Redis에 실시간 데이터 저장 (1시간 TTL)
            redis_key = f"cost_metric:{metric.timestamp.strftime('%Y%m%d_%H%M%S')}_{id(metric)}"
            metric_data = {
                "timestamp": metric.timestamp.isoformat(),
                "category": metric.category.value,
                "model": metric.model,
                "channel": metric.channel,
                "country": metric.country,
                "call_count": metric.call_count,
                "token_count": metric.token_count,
                "cost_usd": metric.cost_usd,
                "response_time_ms": metric.response_time_ms,
                "user_id": metric.user_id,
                "session_id": metric.session_id
            }
            
            await self.redis_client.hset(redis_key, mapping=metric_data)
            await self.redis_client.expire(redis_key, 3600)  # 1시간 TTL
            
            # SQLite에 영구 저장
            self._save_metric_to_db(metric)
            
            # 예산 규칙 체크 및 알림 생성
            alerts = await self._check_budget_rules(metric)
            
            # 알림 저장
            for alert in alerts:
                await self._save_alert_to_db(alert)
                await self._send_alert_notification(alert)
            
            # 실시간 집계 업데이트
            await self._update_realtime_aggregates(metric)
            
        except Exception as e:
            logger.error(f"비용 추적 오류: {e}")
        
        return alerts

    def _save_metric_to_db(self, metric: CostMetric):
        """SQLite에 메트릭 저장"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO cost_metrics 
                (timestamp, category, model, channel, country, call_count, token_count, 
                 cost_usd, response_time_ms, user_id, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metric.timestamp,
                metric.category.value,
                metric.model,
                metric.channel,
                metric.country,
                metric.call_count,
                metric.token_count,
                metric.cost_usd,
                metric.response_time_ms,
                metric.user_id,
                metric.session_id
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"메트릭 데이터베이스 저장 오류: {e}")

    async def _check_budget_rules(self, metric: CostMetric) -> List[CostAlert]:
        """예산 규칙 체크 및 알림 생성"""
        alerts = []
        
        for rule_name, rule in self.budget_rules.items():
            try:
                # 규칙 필터 매칭 체크
                if not self._rule_matches_metric(rule, metric):
                    continue
                
                # 일일/월별 비용 집계
                daily_cost = await self._get_aggregated_cost(rule, "daily")
                monthly_cost = await self._get_aggregated_cost(rule, "monthly")
                
                # 일일 한도 체크
                daily_usage_percent = (daily_cost / rule.daily_limit_usd) * 100
                if daily_usage_percent >= rule.alert_threshold_percent:
                    alert = CostAlert(
                        alert_id=f"{rule_name}_daily_{datetime.now().strftime('%Y%m%d_%H')}",
                        level=AlertLevel.WARNING if daily_usage_percent < 95 else AlertLevel.CRITICAL,
                        category=rule.category,
                        message=f"일일 예산 임계치 초과: {rule_name} ({daily_usage_percent:.1f}%)",
                        current_cost=daily_cost,
                        limit_cost=rule.daily_limit_usd,
                        threshold_percent=daily_usage_percent,
                        timestamp=datetime.now(),
                        metadata={
                            "rule_name": rule_name,
                            "period": "daily",
                            "auto_throttle_enabled": rule.auto_throttle_enabled
                        }
                    )
                    
                    # 자동 스로틀링 적용
                    if rule.auto_throttle_enabled and daily_usage_percent >= 90:
                        await self._apply_throttling(rule, alert)
                        alert.auto_action_taken = True
                    
                    alerts.append(alert)
                
                # 월별 한도 체크
                monthly_usage_percent = (monthly_cost / rule.monthly_limit_usd) * 100
                if monthly_usage_percent >= rule.alert_threshold_percent:
                    alert = CostAlert(
                        alert_id=f"{rule_name}_monthly_{datetime.now().strftime('%Y%m')}",
                        level=AlertLevel.CRITICAL if monthly_usage_percent >= 95 else AlertLevel.WARNING,
                        category=rule.category,
                        message=f"월별 예산 임계치 초과: {rule_name} ({monthly_usage_percent:.1f}%)",
                        current_cost=monthly_cost,
                        limit_cost=rule.monthly_limit_usd,
                        threshold_percent=monthly_usage_percent,
                        timestamp=datetime.now(),
                        metadata={
                            "rule_name": rule_name,
                            "period": "monthly",
                            "emergency_stop_enabled": rule.emergency_stop_enabled
                        }
                    )
                    
                    # 긴급 정지 적용
                    if rule.emergency_stop_enabled and monthly_usage_percent >= 98:
                        await self._apply_emergency_stop(rule, alert)
                        alert.auto_action_taken = True
                        alert.level = AlertLevel.EMERGENCY
                    
                    alerts.append(alert)
                
            except Exception as e:
                logger.error(f"예산 규칙 체크 오류 ({rule_name}): {e}")
        
        return alerts

    def _rule_matches_metric(self, rule: BudgetRule, metric: CostMetric) -> bool:
        """예산 규칙이 메트릭에 매칭되는지 확인"""
        if rule.category != metric.category:
            return False
        
        if rule.model_filter and rule.model_filter not in metric.model:
            return False
        
        if rule.channel_filter and rule.channel_filter != metric.channel:
            return False
        
        if rule.country_filter and rule.country_filter != metric.country:
            return False
        
        return True

    async def _get_aggregated_cost(self, rule: BudgetRule, period: str) -> float:
        """지정된 기간의 집계된 비용 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 기간 설정
            if period == "daily":
                start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "monthly":
                start_time = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                start_time = datetime.now() - timedelta(hours=1)
            
            # 필터 조건 구성
            where_conditions = ["timestamp >= ?"]
            params = [start_time]
            
            where_conditions.append("category = ?")
            params.append(rule.category.value)
            
            if rule.model_filter:
                where_conditions.append("model LIKE ?")
                params.append(f"%{rule.model_filter}%")
            
            if rule.channel_filter:
                where_conditions.append("channel = ?")
                params.append(rule.channel_filter)
            
            if rule.country_filter:
                where_conditions.append("country = ?")
                params.append(rule.country_filter)
            
            query = f"""
                SELECT COALESCE(SUM(cost_usd), 0) as total_cost
                FROM cost_metrics
                WHERE {' AND '.join(where_conditions)}
            """
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result else 0.0
            
        except Exception as e:
            logger.error(f"비용 집계 조회 오류: {e}")
            return 0.0

    async def _apply_throttling(self, rule: BudgetRule, alert: CostAlert):
        """자동 스로틀링 적용"""
        try:
            throttle_key = f"throttle:{rule.name}"
            throttle_data = {
                "rule_name": rule.name,
                "applied_at": datetime.now().isoformat(),
                "reason": f"예산 초과 ({alert.threshold_percent:.1f}%)",
                "duration_minutes": 60  # 1시간 스로틀링
            }
            
            # Redis에 스로틀링 정보 저장
            await self.redis_client.hset(throttle_key, mapping=throttle_data)
            await self.redis_client.expire(throttle_key, 3600)  # 1시간 TTL
            
            # 메모리에도 저장
            self.active_throttles[rule.name] = datetime.now() + timedelta(hours=1)
            
            logger.warning(f"자동 스로틀링 적용: {rule.name}")
            
        except Exception as e:
            logger.error(f"스로틀링 적용 오류: {e}")

    async def _apply_emergency_stop(self, rule: BudgetRule, alert: CostAlert):
        """긴급 정지 적용"""
        try:
            stop_key = f"emergency_stop:{rule.name}"
            stop_data = {
                "rule_name": rule.name,
                "stopped_at": datetime.now().isoformat(),
                "reason": f"월별 예산 위험 초과 ({alert.threshold_percent:.1f}%)",
                "manual_override_required": True
            }
            
            # Redis에 긴급 정지 정보 저장
            await self.redis_client.hset(stop_key, mapping=stop_data)
            await self.redis_client.expire(stop_key, 86400)  # 24시간 TTL
            
            logger.critical(f"긴급 정지 적용: {rule.name}")
            
        except Exception as e:
            logger.error(f"긴급 정지 적용 오류: {e}")

    async def _save_alert_to_db(self, alert: CostAlert):
        """알림을 데이터베이스에 저장"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO cost_alerts 
                (alert_id, level, category, message, current_cost, limit_cost, 
                 threshold_percent, timestamp, auto_action_taken, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.alert_id,
                alert.level.value,
                alert.category.value,
                alert.message,
                alert.current_cost,
                alert.limit_cost,
                alert.threshold_percent,
                alert.timestamp,
                alert.auto_action_taken,
                json.dumps(alert.metadata)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"알림 데이터베이스 저장 오류: {e}")

    async def _send_alert_notification(self, alert: CostAlert):
        """알림 전송 (Slack, 이메일 등)"""
        try:
            # Redis 채널로 실시간 알림 발송
            notification_data = {
                "type": "cost_alert",
                "alert_id": alert.alert_id,
                "level": alert.level.value,
                "category": alert.category.value,
                "message": alert.message,
                "current_cost": alert.current_cost,
                "limit_cost": alert.limit_cost,
                "threshold_percent": alert.threshold_percent,
                "timestamp": alert.timestamp.isoformat(),
                "auto_action_taken": alert.auto_action_taken
            }
            
            await self.redis_client.publish("cost_alerts", json.dumps(notification_data))
            
            logger.info(f"비용 알림 전송: {alert.level.value.upper()} - {alert.message}")
            
        except Exception as e:
            logger.error(f"알림 전송 오류: {e}")

    async def _update_realtime_aggregates(self, metric: CostMetric):
        """실시간 집계 데이터 업데이트"""
        try:
            now = datetime.now()
            hour_key = now.strftime("%Y%m%d_%H")
            
            # 시간별 집계 키들
            aggregate_keys = [
                f"hourly_cost:{hour_key}:total",
                f"hourly_cost:{hour_key}:model:{metric.model}",
                f"hourly_cost:{hour_key}:channel:{metric.channel}",
                f"hourly_cost:{hour_key}:country:{metric.country}",
                f"hourly_calls:{hour_key}:total",
                f"hourly_tokens:{hour_key}:total"
            ]
            
            # Redis 파이프라인으로 일괄 업데이트
            pipe = self.redis_client.pipeline()
            
            for key in aggregate_keys:
                if "cost" in key:
                    pipe.incrbyfloat(key, metric.cost_usd)
                elif "calls" in key:
                    pipe.incr(key, metric.call_count)
                elif "tokens" in key:
                    pipe.incr(key, metric.token_count)
                
                pipe.expire(key, 86400)  # 24시간 TTL
            
            await pipe.execute()
            
        except Exception as e:
            logger.error(f"실시간 집계 업데이트 오류: {e}")

    async def get_cost_dashboard_data(self, period: str = "hourly", limit: int = 24) -> Dict[str, Any]:
        """비용 대시보드 데이터 조회"""
        try:
            dashboard_data = {
                "period": period,
                "generated_at": datetime.now().isoformat(),
                "summary": {},
                "trends": {},
                "breakdown": {},
                "alerts": [],
                "throttle_status": {}
            }
            
            # 요약 정보
            dashboard_data["summary"] = await self._get_cost_summary()
            
            # 트렌드 데이터
            dashboard_data["trends"] = await self._get_cost_trends(period, limit)
            
            # 세부 분석
            dashboard_data["breakdown"] = await self._get_cost_breakdown()
            
            # 활성 알림
            dashboard_data["alerts"] = await self._get_active_alerts()
            
            # 스로틀링 상태
            dashboard_data["throttle_status"] = await self._get_throttle_status()
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"대시보드 데이터 조회 오류: {e}")
            return {"error": str(e)}

    async def _get_cost_summary(self) -> Dict[str, Any]:
        """비용 요약 정보"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 오늘 총 비용
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cursor.execute("""
                SELECT COALESCE(SUM(cost_usd), 0), COALESCE(SUM(call_count), 0), COALESCE(SUM(token_count), 0)
                FROM cost_metrics 
                WHERE timestamp >= ?
            """, (today,))
            
            today_cost, today_calls, today_tokens = cursor.fetchone()
            
            # 어제와 비교
            yesterday = today - timedelta(days=1)
            cursor.execute("""
                SELECT COALESCE(SUM(cost_usd), 0)
                FROM cost_metrics 
                WHERE timestamp >= ? AND timestamp < ?
            """, (yesterday, today))
            
            yesterday_cost = cursor.fetchone()[0]
            
            # 이번 달 총 비용
            this_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            cursor.execute("""
                SELECT COALESCE(SUM(cost_usd), 0)
                FROM cost_metrics 
                WHERE timestamp >= ?
            """, (this_month,))
            
            month_cost = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "today": {
                    "cost_usd": round(today_cost, 4),
                    "calls": today_calls,
                    "tokens": today_tokens,
                    "change_percent": round(((today_cost - yesterday_cost) / yesterday_cost * 100) if yesterday_cost > 0 else 0, 2)
                },
                "month": {
                    "cost_usd": round(month_cost, 4)
                },
                "average_cost_per_call": round(today_cost / today_calls if today_calls > 0 else 0, 6),
                "average_cost_per_token": round(today_cost / today_tokens if today_tokens > 0 else 0, 8)
            }
            
        except Exception as e:
            logger.error(f"비용 요약 조회 오류: {e}")
            return {}

    async def _get_cost_trends(self, period: str, limit: int) -> Dict[str, List]:
        """비용 트렌드 데이터"""
        try:
            if period == "hourly":
                time_format = "%Y-%m-%d %H:00:00"
                time_delta = timedelta(hours=1)
            elif period == "daily":
                time_format = "%Y-%m-%d"
                time_delta = timedelta(days=1)
            else:
                time_format = "%Y-%m-%d %H:00:00"
                time_delta = timedelta(hours=1)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 시간별/일별 비용 트렌드
            cursor.execute(f"""
                SELECT 
                    strftime('{time_format}', timestamp) as period,
                    COALESCE(SUM(cost_usd), 0) as total_cost,
                    COALESCE(SUM(call_count), 0) as total_calls,
                    COALESCE(SUM(token_count), 0) as total_tokens
                FROM cost_metrics 
                WHERE timestamp >= datetime('now', '-{limit} {period.replace("ly", "")}')
                GROUP BY strftime('{time_format}', timestamp)
                ORDER BY period DESC
                LIMIT {limit}
            """)
            
            trend_data = cursor.fetchall()
            conn.close()
            
            periods = []
            costs = []
            calls = []
            tokens = []
            
            for row in trend_data:
                periods.append(row[0])
                costs.append(round(row[1], 4))
                calls.append(row[2])
                tokens.append(row[3])
            
            return {
                "periods": list(reversed(periods)),
                "costs": list(reversed(costs)),
                "calls": list(reversed(calls)),
                "tokens": list(reversed(tokens))
            }
            
        except Exception as e:
            logger.error(f"비용 트렌드 조회 오류: {e}")
            return {"periods": [], "costs": [], "calls": [], "tokens": []}

    async def _get_cost_breakdown(self) -> Dict[str, Any]:
        """비용 세부 분석"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # 모델별 분석
            cursor.execute("""
                SELECT model, COALESCE(SUM(cost_usd), 0) as cost, COALESCE(SUM(call_count), 0) as calls
                FROM cost_metrics 
                WHERE timestamp >= ?
                GROUP BY model 
                ORDER BY cost DESC
            """, (today,))
            
            model_breakdown = [{"model": row[0], "cost": round(row[1], 4), "calls": row[2]} for row in cursor.fetchall()]
            
            # 채널별 분석
            cursor.execute("""
                SELECT channel, COALESCE(SUM(cost_usd), 0) as cost, COALESCE(SUM(call_count), 0) as calls
                FROM cost_metrics 
                WHERE timestamp >= ?
                GROUP BY channel 
                ORDER BY cost DESC
            """, (today,))
            
            channel_breakdown = [{"channel": row[0], "cost": round(row[1], 4), "calls": row[2]} for row in cursor.fetchall()]
            
            # 국가별 분석
            cursor.execute("""
                SELECT country, COALESCE(SUM(cost_usd), 0) as cost, COALESCE(SUM(call_count), 0) as calls
                FROM cost_metrics 
                WHERE timestamp >= ?
                GROUP BY country 
                ORDER BY cost DESC
            """, (today,))
            
            country_breakdown = [{"country": row[0], "cost": round(row[1], 4), "calls": row[2]} for row in cursor.fetchall()]
            
            conn.close()
            
            return {
                "by_model": model_breakdown,
                "by_channel": channel_breakdown,
                "by_country": country_breakdown
            }
            
        except Exception as e:
            logger.error(f"비용 분석 조회 오류: {e}")
            return {"by_model": [], "by_channel": [], "by_country": []}

    async def _get_active_alerts(self) -> List[Dict]:
        """활성 알림 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 최근 24시간 알림
            yesterday = datetime.now() - timedelta(days=1)
            cursor.execute("""
                SELECT alert_id, level, category, message, current_cost, 
                       limit_cost, threshold_percent, timestamp, auto_action_taken
                FROM cost_alerts 
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT 20
            """, (yesterday,))
            
            alerts = []
            for row in cursor.fetchall():
                alerts.append({
                    "alert_id": row[0],
                    "level": row[1],
                    "category": row[2],
                    "message": row[3],
                    "current_cost": round(row[4], 4),
                    "limit_cost": round(row[5], 4),
                    "threshold_percent": round(row[6], 2),
                    "timestamp": row[7],
                    "auto_action_taken": row[8]
                })
            
            conn.close()
            return alerts
            
        except Exception as e:
            logger.error(f"활성 알림 조회 오류: {e}")
            return []

    async def _get_throttle_status(self) -> Dict[str, Any]:
        """스로틀링 상태 조회"""
        try:
            throttle_keys = await self.redis_client.keys("throttle:*")
            stop_keys = await self.redis_client.keys("emergency_stop:*")
            
            throttles = []
            emergency_stops = []
            
            for key in throttle_keys:
                data = await self.redis_client.hgetall(key)
                if data:
                    throttles.append({
                        "rule_name": data.get("rule_name"),
                        "applied_at": data.get("applied_at"),
                        "reason": data.get("reason"),
                        "duration_minutes": int(data.get("duration_minutes", 60))
                    })
            
            for key in stop_keys:
                data = await self.redis_client.hgetall(key)
                if data:
                    emergency_stops.append({
                        "rule_name": data.get("rule_name"),
                        "stopped_at": data.get("stopped_at"),
                        "reason": data.get("reason"),
                        "manual_override_required": data.get("manual_override_required") == "True"
                    })
            
            return {
                "active_throttles": throttles,
                "emergency_stops": emergency_stops,
                "total_throttled": len(throttles),
                "total_stopped": len(emergency_stops)
            }
            
        except Exception as e:
            logger.error(f"스로틀링 상태 조회 오류: {e}")
            return {"active_throttles": [], "emergency_stops": [], "total_throttled": 0, "total_stopped": 0}

    async def is_throttled(self, model: str = None, channel: str = None, country: str = None) -> Tuple[bool, Optional[str]]:
        """요청이 스로틀링되었는지 확인"""
        try:
            for rule_name, rule in self.budget_rules.items():
                # 규칙 매칭 체크
                if rule.model_filter and model and rule.model_filter not in model:
                    continue
                if rule.channel_filter and channel and rule.channel_filter != channel:
                    continue
                if rule.country_filter and country and rule.country_filter != country:
                    continue
                
                # 스로틀링 상태 체크
                if rule_name in self.active_throttles:
                    if self.active_throttles[rule_name] > datetime.now():
                        return True, f"스로틀링 적용 중: {rule_name}"
                    else:
                        del self.active_throttles[rule_name]
                
                # Redis에서 긴급 정지 상태 체크
                stop_key = f"emergency_stop:{rule_name}"
                stop_data = await self.redis_client.hgetall(stop_key)
                if stop_data and stop_data.get("manual_override_required") == "True":
                    return True, f"긴급 정지 상태: {rule_name}"
            
            return False, None
            
        except Exception as e:
            logger.error(f"스로틀링 상태 확인 오류: {e}")
            return False, None

# 전역 비용 추적기 인스턴스
cost_tracker = None

async def create_cost_tracker(redis_url: str = "redis://localhost:6379") -> CostTracker:
    """비용 추적기 생성"""
    global cost_tracker
    if cost_tracker is None:
        cost_tracker = CostTracker(redis_url)
        await cost_tracker.__aenter__()
    return cost_tracker

async def track_openai_cost(model: str, channel: str, country: str, 
                           call_count: int, token_count: int, cost_usd: float, 
                           response_time_ms: int, user_id: str = None, session_id: str = None) -> List[CostAlert]:
    """OpenAI API 비용 추적 헬퍼 함수"""
    global cost_tracker
    if cost_tracker is None:
        cost_tracker = await create_cost_tracker()
    
    metric = CostMetric(
        timestamp=datetime.now(),
        category=CostCategory.OPENAI_API,
        model=model,
        channel=channel,
        country=country,
        call_count=call_count,
        token_count=token_count,
        cost_usd=cost_usd,
        response_time_ms=response_time_ms,
        user_id=user_id,
        session_id=session_id
    )
    
    return await cost_tracker.track_cost(metric)