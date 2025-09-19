#!/usr/bin/env python3
"""
StockPilot 운영 대시보드 API 서버
실시간 모니터링 지표 및 시각화 제공
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 유틸리티 임포트
from utils.websocket_auth import get_auth_manager
from utils.rate_limiter import get_rate_limiter
from utils.openai_optimizer import get_openai_optimizer

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class MetricDataPoint:
    """메트릭 데이터 포인트"""
    timestamp: float
    value: float
    metadata: Dict[str, Any] = None

    def to_dict(self):
        return asdict(self)

class DashboardMetrics:
    """대시보드 메트릭 수집 및 관리"""
    
    def __init__(self):
        # 메트릭 저장소 (시계열 데이터)
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # 실시간 카운터
        self.counters = defaultdict(int)
        
        # 인증 이벤트 추적
        self.auth_events = deque(maxlen=500)
        
        # 채널별 메시지 QPS
        self.channel_qps = defaultdict(lambda: deque(maxlen=60))  # 1분간 데이터
        
        # 시작 시간
        self.start_time = time.time()
        
    def add_auth_event(self, event_type: str, client_id: str, success: bool, details: Dict = None):
        """인증 이벤트 추가"""
        event = {
            "timestamp": time.time(),
            "event_type": event_type,  # login, token_generation, permission_check
            "client_id": client_id,
            "success": success,
            "details": details or {}
        }
        self.auth_events.append(event)
        
        # 카운터 업데이트
        self.counters[f"auth_{event_type}_total"] += 1
        if success:
            self.counters[f"auth_{event_type}_success"] += 1
        else:
            self.counters[f"auth_{event_type}_failure"] += 1
    
    def add_channel_message(self, channel: str, count: int = 1):
        """채널별 메시지 카운트 추가"""
        current_time = time.time()
        self.channel_qps[channel].append(MetricDataPoint(current_time, count))
        self.counters[f"channel_{channel}_messages"] += count
    
    def add_openai_call(self, cost: float, tokens_used: int, model: str):
        """OpenAI 호출 메트릭 추가"""
        current_time = time.time()
        self.metrics["openai_cost"].append(MetricDataPoint(current_time, cost, {"model": model}))
        self.metrics["openai_tokens"].append(MetricDataPoint(current_time, tokens_used, {"model": model}))
        
        self.counters["openai_calls_total"] += 1
        self.counters["openai_tokens_total"] += tokens_used
        self.counters["openai_cost_total"] += cost
    
    def get_channel_qps_stats(self, channel: str, window_seconds: int = 60) -> Dict[str, Any]:
        """채널별 QPS 통계"""
        current_time = time.time()
        window_start = current_time - window_seconds
        
        recent_messages = [
            dp for dp in self.channel_qps[channel] 
            if dp.timestamp >= window_start
        ]
        
        if not recent_messages:
            return {"qps": 0.0, "total_messages": 0, "window_seconds": window_seconds}
        
        total_messages = sum(dp.value for dp in recent_messages)
        qps = total_messages / window_seconds
        
        return {
            "qps": round(qps, 2),
            "total_messages": int(total_messages),
            "window_seconds": window_seconds,
            "peak_qps": max(dp.value for dp in recent_messages)
        }
    
    def get_auth_stats(self, window_minutes: int = 60) -> Dict[str, Any]:
        """인증 통계"""
        current_time = time.time()
        window_start = current_time - (window_minutes * 60)
        
        recent_events = [
            event for event in self.auth_events 
            if event["timestamp"] >= window_start
        ]
        
        stats = {
            "total_events": len(recent_events),
            "success_rate": 0.0,
            "events_by_type": defaultdict(int),
            "clients_active": set(),
            "window_minutes": window_minutes
        }
        
        success_count = 0
        for event in recent_events:
            if event["success"]:
                success_count += 1
            stats["events_by_type"][event["event_type"]] += 1
            stats["clients_active"].add(event["client_id"])
        
        if recent_events:
            stats["success_rate"] = round(success_count / len(recent_events) * 100, 1)
        
        stats["unique_clients"] = len(stats["clients_active"])
        stats["clients_active"] = list(stats["clients_active"])
        
        return stats
    
    def get_openai_stats(self, window_hours: int = 24) -> Dict[str, Any]:
        """OpenAI 사용 통계"""
        current_time = time.time()
        window_start = current_time - (window_hours * 3600)
        
        recent_cost_data = [
            dp for dp in self.metrics["openai_cost"] 
            if dp.timestamp >= window_start
        ]
        
        recent_token_data = [
            dp for dp in self.metrics["openai_tokens"] 
            if dp.timestamp >= window_start
        ]
        
        total_cost = sum(dp.value for dp in recent_cost_data)
        total_tokens = sum(dp.value for dp in recent_token_data)
        
        # 모델별 통계
        model_stats = defaultdict(lambda: {"cost": 0.0, "tokens": 0, "calls": 0})
        for dp in recent_cost_data:
            model = dp.metadata.get("model", "unknown") if dp.metadata else "unknown"
            model_stats[model]["cost"] += dp.value
            model_stats[model]["calls"] += 1
        
        for dp in recent_token_data:
            model = dp.metadata.get("model", "unknown") if dp.metadata else "unknown"
            model_stats[model]["tokens"] += dp.value
        
        return {
            "total_cost": round(total_cost, 4),
            "total_tokens": int(total_tokens),
            "total_calls": len(recent_cost_data),
            "window_hours": window_hours,
            "avg_cost_per_call": round(total_cost / len(recent_cost_data), 4) if recent_cost_data else 0,
            "models": dict(model_stats)
        }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """시스템 전반 통계"""
        current_time = time.time()
        uptime_seconds = current_time - self.start_time
        
        return {
            "uptime_seconds": int(uptime_seconds),
            "uptime_formatted": self._format_duration(uptime_seconds),
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "current_time": datetime.fromtimestamp(current_time).isoformat(),
            "counters": dict(self.counters),
            "active_metrics": len(self.metrics),
            "memory_usage_mb": self._get_memory_usage()
        }
    
    def _format_duration(self, seconds: float) -> str:
        """시간 포맷팅"""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}h {minutes}m {seconds}s"
    
    def _get_memory_usage(self) -> float:
        """메모리 사용량 (MB)"""
        try:
            import psutil
            process = psutil.Process()
            return round(process.memory_info().rss / 1024 / 1024, 2)
        except ImportError:
            return 0.0

# 전역 메트릭 인스턴스
dashboard_metrics = DashboardMetrics()

# FastAPI 앱 생성
app = FastAPI(
    title="StockPilot 운영 대시보드",
    version="1.0.0",
    description="실시간 모니터링 지표 및 시각화"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 의존성 주입
def get_auth_manager_instance():
    jwt_secret = os.getenv('JWT_SECRET_KEY', 'stockpilot-dev-secret-2024')
    return get_auth_manager(jwt_secret)

def get_rate_limiter_instance():
    return get_rate_limiter()

def get_openai_optimizer_instance():
    return get_openai_optimizer()

@app.get("/", response_class=HTMLResponse)
async def dashboard_home():
    """대시보드 홈페이지"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>StockPilot 운영 대시보드</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .card { background: white; border-radius: 8px; padding: 20px; margin: 10px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .header { text-align: center; color: #333; }
            .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
            .metric-value { font-size: 2em; font-weight: bold; color: #007bff; }
            .metric-label { color: #666; margin-bottom: 10px; }
            .status-good { color: #28a745; }
            .status-warning { color: #ffc107; }
            .status-error { color: #dc3545; }
            .api-list { list-style: none; padding: 0; }
            .api-list li { margin: 10px 0; }
            .api-list a { color: #007bff; text-decoration: none; }
            .api-list a:hover { text-decoration: underline; }
        </style>
        <script>
            async function loadMetrics() {
                try {
                    const [systemStats, authStats, rateLimitStats] = await Promise.all([
                        fetch('/api/metrics/system').then(r => r.json()),
                        fetch('/api/metrics/auth?window_minutes=60').then(r => r.json()),
                        fetch('/api/metrics/rate-limit').then(r => r.json())
                    ]);
                    
                    document.getElementById('uptime').textContent = systemStats.uptime_formatted;
                    document.getElementById('auth-success-rate').textContent = authStats.success_rate + '%';
                    document.getElementById('active-clients').textContent = rateLimitStats.active_clients;
                    document.getElementById('total-requests').textContent = rateLimitStats.total_requests.toLocaleString();
                } catch (error) {
                    console.error('메트릭 로드 실패:', error);
                }
            }
            
            setInterval(loadMetrics, 5000);
            window.onload = loadMetrics;
        </script>
    </head>
    <body>
        <div class="container">
            <div class="card">
                <h1 class="header">🚀 StockPilot 운영 대시보드</h1>
                <p class="header">실시간 모니터링 및 지표 시각화</p>
            </div>
            
            <div class="metrics">
                <div class="card">
                    <div class="metric-label">시스템 업타임</div>
                    <div class="metric-value status-good" id="uptime">로딩 중...</div>
                </div>
                
                <div class="card">
                    <div class="metric-label">인증 성공률</div>
                    <div class="metric-value status-good" id="auth-success-rate">로딩 중...</div>
                </div>
                
                <div class="card">
                    <div class="metric-label">활성 클라이언트</div>
                    <div class="metric-value status-good" id="active-clients">로딩 중...</div>
                </div>
                
                <div class="card">
                    <div class="metric-label">총 요청 수</div>
                    <div class="metric-value" id="total-requests">로딩 중...</div>
                </div>
            </div>
            
            <div class="card">
                <h2>📊 API 엔드포인트</h2>
                <ul class="api-list">
                    <li><a href="/api/metrics/system">📈 시스템 통계</a> - 전반적인 시스템 상태</li>
                    <li><a href="/api/metrics/auth?window_minutes=60">🔐 인증 통계</a> - 인증/권한 이벤트</li>
                    <li><a href="/api/metrics/openai?window_hours=24">🤖 OpenAI 통계</a> - API 호출량/비용</li>
                    <li><a href="/api/metrics/rate-limit">⚡ 레이트 리미팅</a> - 요청 제한 현황</li>
                    <li><a href="/api/metrics/channels">📡 채널별 QPS</a> - 메시지 처리량</li>
                    <li><a href="/api/health">💚 헬스체크</a> - 서비스 상태 확인</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/api/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "services": {
            "auth": "up",
            "rate_limiter": "up", 
            "metrics": "up"
        }
    }

@app.get("/api/metrics/system")
async def get_system_metrics():
    """시스템 메트릭"""
    return dashboard_metrics.get_system_stats()

@app.get("/api/metrics/auth")
async def get_auth_metrics(window_minutes: int = Query(60, ge=1, le=1440)):
    """인증 메트릭"""
    return dashboard_metrics.get_auth_stats(window_minutes)

@app.get("/api/metrics/openai")
async def get_openai_metrics(window_hours: int = Query(24, ge=1, le=168)):
    """OpenAI 메트릭"""
    return dashboard_metrics.get_openai_stats(window_hours)

@app.get("/api/metrics/rate-limit")
async def get_rate_limit_metrics(rate_limiter = Depends(get_rate_limiter_instance)):
    """레이트 리미팅 메트릭"""
    return rate_limiter.get_global_stats()

@app.get("/api/metrics/channels")
async def get_channel_metrics():
    """채널별 메트릭"""
    channels = ["us_stocks", "kr_stocks", "exchange_rates", "us_news", "kr_news", "ai_signals", "market_status", "connection"]
    
    channel_stats = {}
    for channel in channels:
        channel_stats[channel] = dashboard_metrics.get_channel_qps_stats(channel)
    
    return {
        "channels": channel_stats,
        "total_channels": len(channels),
        "timestamp": time.time()
    }

@app.get("/api/metrics/channels/{channel}")
async def get_specific_channel_metrics(channel: str, window_seconds: int = Query(60, ge=1, le=3600)):
    """특정 채널 메트릭"""
    return {
        "channel": channel,
        "stats": dashboard_metrics.get_channel_qps_stats(channel, window_seconds),
        "timestamp": time.time()
    }

@app.post("/api/events/auth")
async def record_auth_event(
    event_type: str,
    client_id: str, 
    success: bool,
    details: Optional[Dict] = None
):
    """인증 이벤트 기록"""
    dashboard_metrics.add_auth_event(event_type, client_id, success, details)
    return {"status": "recorded"}

@app.post("/api/events/channel/{channel}")
async def record_channel_event(channel: str, count: int = 1):
    """채널 이벤트 기록"""
    dashboard_metrics.add_channel_message(channel, count)
    return {"status": "recorded", "channel": channel, "count": count}

@app.post("/api/events/openai")
async def record_openai_event(cost: float, tokens_used: int, model: str):
    """OpenAI 이벤트 기록"""
    dashboard_metrics.add_openai_call(cost, tokens_used, model)
    return {"status": "recorded"}

# 서버 시작시 초기 메트릭 설정
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 운영 대시보드 API 서버 시작")
    
    # 초기 테스트 데이터 추가
    dashboard_metrics.add_auth_event("token_generation", "test_client", True, {"role": "admin"})
    dashboard_metrics.add_auth_event("permission_check", "test_client", True, {"channel": "ai_signals"})
    dashboard_metrics.add_channel_message("us_stocks", 10)
    dashboard_metrics.add_channel_message("kr_stocks", 5)
    dashboard_metrics.add_openai_call(0.001, 150, "gpt-4o-mini")

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 StockPilot 운영 대시보드 서버 시작...")
    uvicorn.run(app, host="0.0.0.0", port=8003)