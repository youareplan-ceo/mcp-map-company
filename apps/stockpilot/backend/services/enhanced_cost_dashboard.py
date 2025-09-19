#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
StockPilot 향상된 비용 대시보드 시스템
Chart.js 기반 실시간 그래프, 모델별/채널별 비용 분석
"""

import asyncio
import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/stockpilot/cost_dashboard.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class CostMetrics:
    """비용 메트릭 데이터 구조"""
    timestamp: datetime
    model: str
    channel: str
    country: str
    request_count: int
    token_usage: int
    cost_usd: float
    response_time_avg: float
    success_rate: float

@dataclass
class DashboardData:
    """대시보드 데이터 구조"""
    total_cost_today: float
    total_requests_today: int
    avg_cost_per_request: float
    budget_utilization: float
    cost_trend_7days: List[Dict]
    model_breakdown: List[Dict]
    channel_breakdown: List[Dict]
    country_breakdown: List[Dict]
    hourly_usage: List[Dict]
    cost_prediction: List[Dict]
    alerts: List[Dict]

class EnhancedCostDashboard:
    """향상된 비용 대시보드"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {
            'db_path': '/opt/stockpilot/data/cost_metrics.db',
            'budget_limits': {
                'daily': 100.0,
                'weekly': 500.0,
                'monthly': 2000.0
            },
            'alert_thresholds': {
                'budget_warning': 80,  # 80% 사용시 경고
                'budget_critical': 95,  # 95% 사용시 위험
                'cost_spike': 50,  # 50% 이상 급증시 알림
                'high_latency': 5000  # 5초 이상 지연시 알림
            },
            'websocket_port': 8004
        }
        self.db_path = self.config['db_path']
        self.connected_clients = set()
        self.app = FastAPI(title="StockPilot Cost Dashboard")
        
        self._init_database()
        self._setup_routes()
        
    def _init_database(self):
        """데이터베이스 초기화"""
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS cost_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME NOT NULL,
                        model TEXT NOT NULL,
                        channel TEXT NOT NULL,
                        country TEXT NOT NULL,
                        request_count INTEGER DEFAULT 1,
                        token_usage INTEGER NOT NULL,
                        cost_usd REAL NOT NULL,
                        response_time_ms REAL,
                        success BOOLEAN DEFAULT TRUE
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS budget_settings (
                        id INTEGER PRIMARY KEY,
                        period TEXT NOT NULL,
                        limit_usd REAL NOT NULL,
                        updated_at DATETIME NOT NULL
                    )
                ''')
                
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_timestamp_model 
                    ON cost_metrics(timestamp, model)
                ''')
                
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_timestamp_channel 
                    ON cost_metrics(timestamp, channel)
                ''')
                
        except Exception as e:
            logger.error(f"데이터베이스 초기화 오류: {str(e)}")
            raise
    
    def _setup_routes(self):
        """FastAPI 라우트 설정"""
        
        @self.app.get("/")
        async def dashboard():
            return HTMLResponse(self._get_dashboard_html())
        
        @self.app.get("/api/dashboard-data")
        async def get_dashboard_data():
            data = await self._get_dashboard_data()
            return JSONResponse(asdict(data))
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.connected_clients.add(websocket)
            
            try:
                while True:
                    # 실시간 데이터 전송
                    data = await self._get_dashboard_data()
                    await websocket.send_json(asdict(data))
                    await asyncio.sleep(10)  # 10초마다 업데이트
                    
            except WebSocketDisconnect:
                self.connected_clients.remove(websocket)
    
    def _get_dashboard_html(self) -> str:
        """대시보드 HTML 생성"""
        return '''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StockPilot 비용 대시보드</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .dashboard {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            background: #4CAF50;
            border-radius: 50%;
            margin-left: 10px;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .metric-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            backdrop-filter: blur(4px);
            border: 1px solid rgba(255,255,255,0.2);
        }
        
        .metric-value {
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .metric-label {
            color: #666;
            font-size: 0.9rem;
        }
        
        .metric-change {
            font-size: 0.8rem;
            margin-top: 5px;
        }
        
        .positive { color: #4CAF50; }
        .negative { color: #f44336; }
        
        .charts-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .chart-container {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        
        .chart-title {
            font-size: 1.2rem;
            font-weight: bold;
            margin-bottom: 20px;
            color: #333;
        }
        
        .breakdown-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .alerts-panel {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        
        .alert {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            border-left: 4px solid;
        }
        
        .alert-warning {
            background: #fff3cd;
            border-left-color: #ffc107;
            color: #856404;
        }
        
        .alert-danger {
            background: #f8d7da;
            border-left-color: #dc3545;
            color: #721c24;
        }
        
        .alert-info {
            background: #d1ecf1;
            border-left-color: #17a2b8;
            color: #0c5460;
        }
        
        .loading {
            text-align: center;
            padding: 50px;
            color: white;
        }
        
        .spinner {
            border: 4px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top: 4px solid #fff;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .progress-bar {
            background: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
            height: 20px;
            margin: 10px 0;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #4CAF50, #45a049);
            transition: width 0.5s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 0.8rem;
        }
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>📊 StockPilot 비용 대시보드</h1>
            <p>실시간 AI 모델 사용량 및 비용 모니터링<span class="status-indicator"></span></p>
        </div>
        
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <p>데이터를 로드하는 중...</p>
        </div>
        
        <div id="dashboard-content" style="display: none;">
            <!-- 주요 메트릭 -->
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value" id="total-cost">$0.00</div>
                    <div class="metric-label">오늘 총 비용</div>
                    <div class="metric-change" id="cost-change">-</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="total-requests">0</div>
                    <div class="metric-label">총 요청 수</div>
                    <div class="metric-change" id="requests-change">-</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="avg-cost">$0.000</div>
                    <div class="metric-label">요청당 평균 비용</div>
                    <div class="metric-change" id="avg-cost-change">-</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="budget-usage">0%</div>
                    <div class="metric-label">일일 예산 사용률</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="budget-progress" style="width: 0%;">0%</div>
                    </div>
                </div>
            </div>
            
            <!-- 주요 차트 -->
            <div class="charts-grid">
                <div class="chart-container">
                    <div class="chart-title">7일 비용 트렌드</div>
                    <canvas id="costTrendChart"></canvas>
                </div>
                <div class="chart-container">
                    <div class="chart-title">시간별 사용량</div>
                    <canvas id="hourlyUsageChart"></canvas>
                </div>
            </div>
            
            <!-- 세부 분석 차트 -->
            <div class="breakdown-grid">
                <div class="chart-container">
                    <div class="chart-title">모델별 비용 분석</div>
                    <canvas id="modelBreakdownChart"></canvas>
                </div>
                <div class="chart-container">
                    <div class="chart-title">채널별 사용량</div>
                    <canvas id="channelBreakdownChart"></canvas>
                </div>
                <div class="chart-container">
                    <div class="chart-title">국가별 분포</div>
                    <canvas id="countryBreakdownChart"></canvas>
                </div>
            </div>
            
            <!-- 알림 패널 -->
            <div class="alerts-panel">
                <div class="chart-title">🚨 실시간 알림</div>
                <div id="alerts-container">
                    <div class="alert alert-info">
                        시스템이 정상적으로 모니터링 중입니다.
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let charts = {};
        let websocket = null;
        
        // WebSocket 연결
        function connectWebSocket() {
            const wsUrl = `ws://${window.location.host}/ws`;
            websocket = new WebSocket(wsUrl);
            
            websocket.onopen = function() {
                console.log('WebSocket 연결됨');
            };
            
            websocket.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };
            
            websocket.onclose = function() {
                console.log('WebSocket 연결 끊어짐, 5초 후 재연결 시도...');
                setTimeout(connectWebSocket, 5000);
            };
        }
        
        // 대시보드 업데이트
        function updateDashboard(data) {
            document.getElementById('loading').style.display = 'none';
            document.getElementById('dashboard-content').style.display = 'block';
            
            // 메트릭 업데이트
            document.getElementById('total-cost').textContent = `$${data.total_cost_today.toFixed(2)}`;
            document.getElementById('total-requests').textContent = data.total_requests_today.toLocaleString();
            document.getElementById('avg-cost').textContent = `$${data.avg_cost_per_request.toFixed(4)}`;
            document.getElementById('budget-usage').textContent = `${data.budget_utilization.toFixed(1)}%`;
            
            // 예산 진행 바 업데이트
            const progressFill = document.getElementById('budget-progress');
            progressFill.style.width = `${Math.min(data.budget_utilization, 100)}%`;
            progressFill.textContent = `${data.budget_utilization.toFixed(1)}%`;
            
            // 예산 사용률에 따른 색상 변경
            if (data.budget_utilization >= 95) {
                progressFill.style.background = 'linear-gradient(90deg, #dc3545, #c82333)';
            } else if (data.budget_utilization >= 80) {
                progressFill.style.background = 'linear-gradient(90deg, #ffc107, #e0a800)';
            } else {
                progressFill.style.background = 'linear-gradient(90deg, #4CAF50, #45a049)';
            }
            
            // 차트 업데이트
            updateCostTrendChart(data.cost_trend_7days);
            updateHourlyUsageChart(data.hourly_usage);
            updateModelBreakdownChart(data.model_breakdown);
            updateChannelBreakdownChart(data.channel_breakdown);
            updateCountryBreakdownChart(data.country_breakdown);
            
            // 알림 업데이트
            updateAlerts(data.alerts);
        }
        
        // 비용 트렌드 차트
        function updateCostTrendChart(data) {
            const ctx = document.getElementById('costTrendChart').getContext('2d');
            
            if (charts.costTrend) {
                charts.costTrend.destroy();
            }
            
            charts.costTrend = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.map(d => new Date(d.date).toLocaleDateString('ko-KR', {month: 'short', day: 'numeric'})),
                    datasets: [{
                        label: '일일 비용',
                        data: data.map(d => d.cost),
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    return '$' + value.toFixed(2);
                                }
                            }
                        }
                    }
                }
            });
        }
        
        // 시간별 사용량 차트
        function updateHourlyUsageChart(data) {
            const ctx = document.getElementById('hourlyUsageChart').getContext('2d');
            
            if (charts.hourlyUsage) {
                charts.hourlyUsage.destroy();
            }
            
            charts.hourlyUsage = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.map(d => `${d.hour}시`),
                    datasets: [{
                        label: '요청 수',
                        data: data.map(d => d.requests),
                        backgroundColor: 'rgba(118, 75, 162, 0.8)',
                        borderColor: '#764ba2',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
        
        // 모델별 분석 차트
        function updateModelBreakdownChart(data) {
            const ctx = document.getElementById('modelBreakdownChart').getContext('2d');
            
            if (charts.modelBreakdown) {
                charts.modelBreakdown.destroy();
            }
            
            const colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF'];
            
            charts.modelBreakdown = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: data.map(d => d.model),
                    datasets: [{
                        data: data.map(d => d.cost),
                        backgroundColor: colors.slice(0, data.length),
                        borderWidth: 2,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = '$' + context.parsed.toFixed(2);
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((context.parsed / total) * 100).toFixed(1);
                                    return `${label}: ${value} (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            });
        }
        
        // 채널별 사용량 차트
        function updateChannelBreakdownChart(data) {
            const ctx = document.getElementById('channelBreakdownChart').getContext('2d');
            
            if (charts.channelBreakdown) {
                charts.channelBreakdown.destroy();
            }
            
            charts.channelBreakdown = new Chart(ctx, {
                type: 'polarArea',
                data: {
                    labels: data.map(d => d.channel),
                    datasets: [{
                        data: data.map(d => d.requests),
                        backgroundColor: [
                            'rgba(255, 99, 132, 0.7)',
                            'rgba(54, 162, 235, 0.7)',
                            'rgba(255, 205, 86, 0.7)',
                            'rgba(75, 192, 192, 0.7)',
                            'rgba(153, 102, 255, 0.7)'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
        }
        
        // 국가별 분포 차트
        function updateCountryBreakdownChart(data) {
            const ctx = document.getElementById('countryBreakdownChart').getContext('2d');
            
            if (charts.countryBreakdown) {
                charts.countryBreakdown.destroy();
            }
            
            charts.countryBreakdown = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: data.map(d => d.country),
                    datasets: [{
                        data: data.map(d => d.requests),
                        backgroundColor: [
                            '#FF6B6B',
                            '#4ECDC4',
                            '#45B7D1',
                            '#96CEB4',
                            '#FFEAA7',
                            '#DDA0DD',
                            '#98D8C8'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
        }
        
        // 알림 업데이트
        function updateAlerts(alerts) {
            const container = document.getElementById('alerts-container');
            
            if (alerts.length === 0) {
                container.innerHTML = '<div class="alert alert-info">현재 활성 알림이 없습니다.</div>';
                return;
            }
            
            container.innerHTML = alerts.map(alert => {
                const alertClass = alert.severity === 'critical' ? 'alert-danger' : 
                                 alert.severity === 'warning' ? 'alert-warning' : 'alert-info';
                return `<div class="alert ${alertClass}">${alert.message}</div>`;
            }).join('');
        }
        
        // 초기화
        document.addEventListener('DOMContentLoaded', function() {
            connectWebSocket();
            
            // 초기 데이터 로드
            fetch('/api/dashboard-data')
                .then(response => response.json())
                .then(data => updateDashboard(data))
                .catch(error => {
                    console.error('초기 데이터 로드 오류:', error);
                    document.getElementById('loading').innerHTML = '<p>데이터 로드 중 오류가 발생했습니다.</p>';
                });
        });
    </script>
</body>
</html>
        '''
    
    async def _get_dashboard_data(self) -> DashboardData:
        """대시보드 데이터 생성"""
        try:
            now = datetime.now(timezone.utc)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = now - timedelta(days=7)
            
            with sqlite3.connect(self.db_path) as conn:
                # 오늘 총 비용
                cursor = conn.execute('''
                    SELECT COALESCE(SUM(cost_usd), 0), COALESCE(SUM(request_count), 0)
                    FROM cost_metrics 
                    WHERE timestamp >= ?
                ''', (today_start,))
                total_cost_today, total_requests_today = cursor.fetchone()
                
                # 요청당 평균 비용
                avg_cost_per_request = total_cost_today / max(total_requests_today, 1)
                
                # 예산 사용률 계산
                daily_budget = self.config['budget_limits']['daily']
                budget_utilization = (total_cost_today / daily_budget) * 100
                
                # 7일 비용 트렌드
                cost_trend_7days = []
                for i in range(7):
                    day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
                    day_end = day_start + timedelta(days=1)
                    
                    cursor = conn.execute('''
                        SELECT COALESCE(SUM(cost_usd), 0)
                        FROM cost_metrics 
                        WHERE timestamp >= ? AND timestamp < ?
                    ''', (day_start, day_end))
                    
                    day_cost = cursor.fetchone()[0]
                    cost_trend_7days.append({
                        'date': day_start.isoformat(),
                        'cost': day_cost
                    })
                
                cost_trend_7days.reverse()
                
                # 모델별 분석
                cursor = conn.execute('''
                    SELECT model, SUM(cost_usd) as total_cost, SUM(request_count) as total_requests
                    FROM cost_metrics 
                    WHERE timestamp >= ?
                    GROUP BY model
                    ORDER BY total_cost DESC
                ''', (today_start,))
                
                model_breakdown = [
                    {'model': row[0], 'cost': row[1], 'requests': row[2]}
                    for row in cursor.fetchall()
                ]
                
                # 채널별 분석
                cursor = conn.execute('''
                    SELECT channel, SUM(request_count) as total_requests, SUM(cost_usd) as total_cost
                    FROM cost_metrics 
                    WHERE timestamp >= ?
                    GROUP BY channel
                    ORDER BY total_requests DESC
                ''', (today_start,))
                
                channel_breakdown = [
                    {'channel': row[0], 'requests': row[1], 'cost': row[2]}
                    for row in cursor.fetchall()
                ]
                
                # 국가별 분석
                cursor = conn.execute('''
                    SELECT country, SUM(request_count) as total_requests
                    FROM cost_metrics 
                    WHERE timestamp >= ?
                    GROUP BY country
                    ORDER BY total_requests DESC
                ''', (today_start,))
                
                country_breakdown = [
                    {'country': row[0], 'requests': row[1]}
                    for row in cursor.fetchall()
                ]
                
                # 시간별 사용량
                hourly_usage = []
                for hour in range(24):
                    hour_start = today_start.replace(hour=hour)
                    hour_end = hour_start + timedelta(hours=1)
                    
                    cursor = conn.execute('''
                        SELECT COALESCE(SUM(request_count), 0)
                        FROM cost_metrics 
                        WHERE timestamp >= ? AND timestamp < ?
                    ''', (hour_start, hour_end))
                    
                    requests = cursor.fetchone()[0]
                    hourly_usage.append({
                        'hour': hour,
                        'requests': requests
                    })
                
                # 비용 예측 (간단한 선형 예측)
                cost_prediction = []
                if len(cost_trend_7days) >= 3:
                    recent_costs = [day['cost'] for day in cost_trend_7days[-3:]]
                    trend = (recent_costs[-1] - recent_costs[0]) / 2
                    
                    for i in range(1, 4):  # 다음 3일 예측
                        predicted_date = now + timedelta(days=i)
                        predicted_cost = max(0, recent_costs[-1] + trend * i)
                        cost_prediction.append({
                            'date': predicted_date.isoformat(),
                            'cost': predicted_cost
                        })
                
                # 알림 생성
                alerts = self._generate_alerts(
                    total_cost_today, budget_utilization, model_breakdown
                )
                
                return DashboardData(
                    total_cost_today=total_cost_today,
                    total_requests_today=total_requests_today,
                    avg_cost_per_request=avg_cost_per_request,
                    budget_utilization=budget_utilization,
                    cost_trend_7days=cost_trend_7days,
                    model_breakdown=model_breakdown,
                    channel_breakdown=channel_breakdown,
                    country_breakdown=country_breakdown,
                    hourly_usage=hourly_usage,
                    cost_prediction=cost_prediction,
                    alerts=alerts
                )
                
        except Exception as e:
            logger.error(f"대시보드 데이터 생성 오류: {str(e)}")
            raise
    
    def _generate_alerts(self, total_cost: float, budget_utilization: float, 
                        model_breakdown: List[Dict]) -> List[Dict]:
        """알림 생성"""
        alerts = []
        thresholds = self.config['alert_thresholds']
        
        # 예산 사용률 알림
        if budget_utilization >= thresholds['budget_critical']:
            alerts.append({
                'severity': 'critical',
                'message': f'🚨 일일 예산의 {budget_utilization:.1f}% 사용! 즉시 확인이 필요합니다.'
            })
        elif budget_utilization >= thresholds['budget_warning']:
            alerts.append({
                'severity': 'warning',
                'message': f'⚠️ 일일 예산의 {budget_utilization:.1f}% 사용 중입니다.'
            })
        
        # 모델별 비용 급증 감지
        if model_breakdown:
            total_cost_today = sum(model['cost'] for model in model_breakdown)
            for model in model_breakdown:
                model_percentage = (model['cost'] / max(total_cost_today, 0.01)) * 100
                if model_percentage > 60:  # 특정 모델이 60% 이상 사용
                    alerts.append({
                        'severity': 'warning',
                        'message': f'📈 {model["model"]} 모델이 총 비용의 {model_percentage:.1f}%를 차지하고 있습니다.'
                    })
        
        # 일반 정보
        if not alerts:
            alerts.append({
                'severity': 'info',
                'message': '✅ 모든 시스템이 정상적으로 운영 중입니다.'
            })
        
        return alerts
    
    def record_cost_metric(self, model: str, channel: str, country: str,
                          token_usage: int, cost_usd: float, 
                          response_time_ms: float = None, success: bool = True):
        """비용 메트릭 기록"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO cost_metrics 
                    (timestamp, model, channel, country, token_usage, cost_usd, 
                     response_time_ms, success)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now(timezone.utc),
                    model,
                    channel,
                    country,
                    token_usage,
                    cost_usd,
                    response_time_ms,
                    success
                ))
                
        except Exception as e:
            logger.error(f"비용 메트릭 기록 오류: {str(e)}")
    
    async def broadcast_update(self):
        """연결된 모든 클라이언트에게 업데이트 전송"""
        if self.connected_clients:
            data = await self._get_dashboard_data()
            disconnected = set()
            
            for client in self.connected_clients:
                try:
                    await client.send_json(asdict(data))
                except:
                    disconnected.add(client)
            
            # 연결이 끊어진 클라이언트 제거
            self.connected_clients -= disconnected
    
    async def start_server(self):
        """대시보드 서버 시작"""
        logger.info(f"비용 대시보드 서버 시작: 포트 {self.config['websocket_port']}")
        
        # 샘플 데이터 생성 (테스트용)
        await self._generate_sample_data()
        
        config = uvicorn.Config(
            app=self.app,
            host="0.0.0.0",
            port=self.config['websocket_port'],
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    async def _generate_sample_data(self):
        """테스트용 샘플 데이터 생성"""
        logger.info("샘플 데이터 생성 중...")
        
        models = ['gpt-4', 'gpt-3.5-turbo', 'claude-3-sonnet', 'claude-3-haiku']
        channels = ['web', 'mobile', 'api', 'webhook']
        countries = ['KR', 'US', 'JP', 'CN']
        
        import random
        now = datetime.now(timezone.utc)
        
        # 최근 7일간 데이터 생성
        for days_ago in range(7):
            date = now - timedelta(days=days_ago)
            
            # 하루에 여러 번 호출
            for _ in range(random.randint(50, 200)):
                hour = random.randint(0, 23)
                call_time = date.replace(hour=hour, minute=random.randint(0, 59))
                
                model = random.choice(models)
                channel = random.choice(channels)
                country = random.choice(countries)
                
                # 모델별 다른 비용 구조
                if 'gpt-4' in model:
                    token_usage = random.randint(100, 1000)
                    cost_per_token = 0.03 / 1000
                elif 'claude-3-sonnet' in model:
                    token_usage = random.randint(150, 800)
                    cost_per_token = 0.015 / 1000
                else:
                    token_usage = random.randint(200, 1500)
                    cost_per_token = 0.001 / 1000
                
                cost_usd = token_usage * cost_per_token
                response_time = random.uniform(500, 3000)
                success = random.random() > 0.05  # 95% 성공률
                
                # 데이터베이스에 직접 삽입
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('''
                        INSERT INTO cost_metrics 
                        (timestamp, model, channel, country, token_usage, cost_usd, 
                         response_time_ms, success)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        call_time,
                        model,
                        channel,
                        country,
                        token_usage,
                        cost_usd,
                        response_time,
                        success
                    ))
        
        logger.info("샘플 데이터 생성 완료")

async def main():
    """메인 실행 함수"""
    try:
        dashboard = EnhancedCostDashboard()
        await dashboard.start_server()
    except KeyboardInterrupt:
        logger.info("대시보드 서버 종료")
    except Exception as e:
        logger.error(f"대시보드 서버 오류: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())