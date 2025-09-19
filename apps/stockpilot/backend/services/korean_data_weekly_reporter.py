#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
StockPilot KR 데이터 소스 주간 리포트 자동화 시스템
품질 점수 트렌드 분석, 수집 성공률 모니터링, 자동 리포트 생성
"""

import asyncio
import json
import logging
import sqlite3
import statistics
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import smtplib
import jinja2

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/stockpilot/korean_data_reporter.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class DataSourceMetrics:
    """데이터 소스 품질 메트릭"""
    source_name: str
    collection_attempts: int
    successful_collections: int
    failed_collections: int
    success_rate: float
    avg_quality_score: float
    min_quality_score: float
    max_quality_score: float
    quality_trend: List[float]
    last_update: datetime
    error_types: Dict[str, int]
    data_completeness: float
    latency_avg: float

@dataclass
class WeeklyReport:
    """주간 리포트 데이터 구조"""
    week_start: datetime
    week_end: datetime
    total_sources: int
    active_sources: int
    inactive_sources: int
    overall_success_rate: float
    overall_quality_score: float
    quality_trend: List[float]
    source_metrics: List[DataSourceMetrics]
    anomalies: List[Dict[str, Any]]
    recommendations: List[str]
    generated_at: datetime

class KoreanDataWeeklyReporter:
    """KR 데이터 소스 주간 리포트 생성기"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {
            'db_path': '/opt/stockpilot/data/korean_data_metrics.db',
            'report_output_dir': '/var/log/stockpilot/reports',
            'email_config': {
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'sender_email': 'stockpilot@yourdomain.com',
                'sender_password': 'your_app_password',
                'recipients': ['admin@yourdomain.com']
            },
            'quality_thresholds': {
                'excellent': 95.0,
                'good': 85.0,
                'warning': 70.0,
                'critical': 50.0
            },
            'success_rate_threshold': 90.0
        }
        self.db_path = self.config['db_path']
        self.report_dir = Path(self.config['report_output_dir'])
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        # 템플릿 환경 설정
        template_dir = Path(__file__).parent / 'templates'
        template_dir.mkdir(exist_ok=True)
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(template_dir))
        )
        
        self._init_database()
        self._create_report_template()
    
    def _init_database(self):
        """데이터베이스 초기화"""
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS data_source_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source_name TEXT NOT NULL,
                        timestamp DATETIME NOT NULL,
                        collection_result TEXT NOT NULL,
                        quality_score REAL,
                        error_message TEXT,
                        data_size INTEGER,
                        latency_ms REAL,
                        completeness_ratio REAL
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS weekly_reports (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        week_start DATE NOT NULL,
                        week_end DATE NOT NULL,
                        report_data TEXT NOT NULL,
                        generated_at DATETIME NOT NULL
                    )
                ''')
                
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_source_timestamp 
                    ON data_source_metrics(source_name, timestamp)
                ''')
                
        except Exception as e:
            logger.error(f"데이터베이스 초기화 오류: {str(e)}")
            raise
    
    def _create_report_template(self):
        """HTML 리포트 템플릿 생성"""
        template_path = Path(__file__).parent / 'templates' / 'weekly_report.html'
        template_content = '''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StockPilot KR 데이터 소스 주간 리포트</title>
    <style>
        body {
            font-family: 'Malgun Gothic', '맑은 고딕', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            border-bottom: 3px solid #007bff;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        .header h1 {
            color: #007bff;
            margin: 0;
            font-size: 2.2em;
        }
        .meta-info {
            color: #666;
            margin-top: 10px;
        }
        .summary-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .card {
            padding: 20px;
            border-radius: 8px;
            border-left: 5px solid;
        }
        .card.success { border-left-color: #28a745; background: #f8fff9; }
        .card.warning { border-left-color: #ffc107; background: #fffef5; }
        .card.danger { border-left-color: #dc3545; background: #fff5f5; }
        .card.info { border-left-color: #17a2b8; background: #f5fcff; }
        .card-title {
            font-weight: bold;
            font-size: 1.1em;
            margin-bottom: 10px;
        }
        .card-value {
            font-size: 2em;
            font-weight: bold;
            margin: 5px 0;
        }
        .section {
            margin-bottom: 40px;
        }
        .section h2 {
            color: #333;
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
        }
        .table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        .table th, .table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        .table th {
            background-color: #f8f9fa;
            font-weight: bold;
        }
        .status-excellent { color: #28a745; font-weight: bold; }
        .status-good { color: #17a2b8; font-weight: bold; }
        .status-warning { color: #ffc107; font-weight: bold; }
        .status-critical { color: #dc3545; font-weight: bold; }
        .chart-container {
            margin: 20px 0;
            text-align: center;
        }
        .anomalies {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 5px;
            padding: 15px;
            margin: 20px 0;
        }
        .recommendations {
            background: #d1ecf1;
            border: 1px solid #bee5eb;
            border-radius: 5px;
            padding: 15px;
            margin: 20px 0;
        }
        .recommendations ul {
            margin: 10px 0;
            padding-left: 20px;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            text-align: center;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 StockPilot KR 데이터 소스 주간 리포트</h1>
            <div class="meta-info">
                <strong>보고 기간:</strong> {{ report.week_start.strftime('%Y년 %m월 %d일') }} ~ {{ report.week_end.strftime('%Y년 %m월 %d일') }}<br>
                <strong>생성 시간:</strong> {{ report.generated_at.strftime('%Y년 %m월 %d일 %H:%M:%S') }}
            </div>
        </div>

        <div class="summary-cards">
            <div class="card info">
                <div class="card-title">총 데이터 소스</div>
                <div class="card-value">{{ report.total_sources }}</div>
            </div>
            <div class="card {{ 'success' if report.overall_success_rate >= 90 else 'warning' if report.overall_success_rate >= 70 else 'danger' }}">
                <div class="card-title">전체 성공률</div>
                <div class="card-value">{{ "%.1f"|format(report.overall_success_rate) }}%</div>
            </div>
            <div class="card {{ 'success' if report.overall_quality_score >= 85 else 'warning' if report.overall_quality_score >= 70 else 'danger' }}">
                <div class="card-title">평균 품질 점수</div>
                <div class="card-value">{{ "%.1f"|format(report.overall_quality_score) }}</div>
            </div>
            <div class="card {{ 'success' if report.active_sources == report.total_sources else 'warning' }}">
                <div class="card-title">활성 소스</div>
                <div class="card-value">{{ report.active_sources }}/{{ report.total_sources }}</div>
            </div>
        </div>

        <div class="section">
            <h2>📈 데이터 소스별 상세 현황</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>데이터 소스</th>
                        <th>수집 시도</th>
                        <th>성공률</th>
                        <th>평균 품질점수</th>
                        <th>평균 지연시간</th>
                        <th>상태</th>
                    </tr>
                </thead>
                <tbody>
                    {% for source in report.source_metrics %}
                    <tr>
                        <td><strong>{{ source.source_name }}</strong></td>
                        <td>{{ source.collection_attempts }}</td>
                        <td>{{ "%.1f"|format(source.success_rate) }}%</td>
                        <td>{{ "%.1f"|format(source.avg_quality_score) }}</td>
                        <td>{{ "%.0f"|format(source.latency_avg) }}ms</td>
                        <td>
                            {% if source.avg_quality_score >= 95 %}
                                <span class="status-excellent">우수</span>
                            {% elif source.avg_quality_score >= 85 %}
                                <span class="status-good">양호</span>
                            {% elif source.avg_quality_score >= 70 %}
                                <span class="status-warning">주의</span>
                            {% else %}
                                <span class="status-critical">위험</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        {% if report.anomalies %}
        <div class="section">
            <h2>⚠️ 이상 패턴 및 경고</h2>
            <div class="anomalies">
                {% for anomaly in report.anomalies %}
                <div style="margin-bottom: 15px;">
                    <strong>{{ anomaly.type }}:</strong> {{ anomaly.description }}
                    {% if anomaly.source %}<br><em>대상: {{ anomaly.source }}</em>{% endif %}
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        <div class="section">
            <h2>💡 개선 권장사항</h2>
            <div class="recommendations">
                <ul>
                    {% for recommendation in report.recommendations %}
                    <li>{{ recommendation }}</li>
                    {% endfor %}
                </ul>
            </div>
        </div>

        <div class="footer">
            <p>이 리포트는 StockPilot 자동 모니터링 시스템에 의해 생성되었습니다.</p>
            <p>문의사항이 있으시면 기술팀에 연락해주세요.</p>
        </div>
    </div>
</body>
</html>
        '''
        
        template_path.parent.mkdir(parents=True, exist_ok=True)
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(template_content)
    
    def record_data_collection(self, source_name: str, success: bool, 
                             quality_score: float = None, error: str = None,
                             data_size: int = None, latency_ms: float = None,
                             completeness: float = None):
        """데이터 수집 결과 기록"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO data_source_metrics 
                    (source_name, timestamp, collection_result, quality_score, 
                     error_message, data_size, latency_ms, completeness_ratio)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    source_name,
                    datetime.now(timezone.utc),
                    'success' if success else 'failed',
                    quality_score,
                    error,
                    data_size,
                    latency_ms,
                    completeness
                ))
                
        except Exception as e:
            logger.error(f"데이터 수집 결과 기록 오류: {str(e)}")
    
    def get_source_metrics(self, source_name: str, 
                          start_date: datetime, end_date: datetime) -> DataSourceMetrics:
        """특정 데이터 소스의 주간 메트릭 계산"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT collection_result, quality_score, error_message, 
                           latency_ms, completeness_ratio, timestamp
                    FROM data_source_metrics
                    WHERE source_name = ? AND timestamp BETWEEN ? AND ?
                    ORDER BY timestamp ASC
                ''', (source_name, start_date, end_date))
                
                rows = cursor.fetchall()
                
                if not rows:
                    return DataSourceMetrics(
                        source_name=source_name,
                        collection_attempts=0,
                        successful_collections=0,
                        failed_collections=0,
                        success_rate=0.0,
                        avg_quality_score=0.0,
                        min_quality_score=0.0,
                        max_quality_score=0.0,
                        quality_trend=[],
                        last_update=None,
                        error_types={},
                        data_completeness=0.0,
                        latency_avg=0.0
                    )
                
                total_attempts = len(rows)
                successful = sum(1 for row in rows if row[0] == 'success')
                failed = total_attempts - successful
                
                quality_scores = [row[1] for row in rows if row[1] is not None]
                latencies = [row[3] for row in rows if row[3] is not None]
                completeness_values = [row[4] for row in rows if row[4] is not None]
                
                # 에러 유형 분석
                error_types = {}
                for row in rows:
                    if row[0] == 'failed' and row[2]:
                        error_type = row[2].split(':')[0] if ':' in row[2] else row[2]
                        error_types[error_type] = error_types.get(error_type, 0) + 1
                
                # 품질 점수 트렌드 (일별 평균)
                quality_trend = []
                if quality_scores:
                    # 간단한 트렌드 계산 (7일간의 평균)
                    days = (end_date - start_date).days
                    for i in range(min(days, 7)):
                        day_start = start_date + timedelta(days=i)
                        day_end = day_start + timedelta(days=1)
                        day_scores = []
                        
                        for row in rows:
                            row_time = datetime.fromisoformat(row[5].replace('Z', '+00:00'))
                            if day_start <= row_time < day_end and row[1] is not None:
                                day_scores.append(row[1])
                        
                        if day_scores:
                            quality_trend.append(statistics.mean(day_scores))
                
                return DataSourceMetrics(
                    source_name=source_name,
                    collection_attempts=total_attempts,
                    successful_collections=successful,
                    failed_collections=failed,
                    success_rate=(successful / total_attempts * 100) if total_attempts > 0 else 0,
                    avg_quality_score=statistics.mean(quality_scores) if quality_scores else 0,
                    min_quality_score=min(quality_scores) if quality_scores else 0,
                    max_quality_score=max(quality_scores) if quality_scores else 0,
                    quality_trend=quality_trend,
                    last_update=datetime.fromisoformat(rows[-1][5].replace('Z', '+00:00')) if rows else None,
                    error_types=error_types,
                    data_completeness=statistics.mean(completeness_values) if completeness_values else 0,
                    latency_avg=statistics.mean(latencies) if latencies else 0
                )
                
        except Exception as e:
            logger.error(f"소스 메트릭 계산 오류 ({source_name}): {str(e)}")
            raise
    
    def detect_anomalies(self, source_metrics: List[DataSourceMetrics]) -> List[Dict[str, Any]]:
        """이상 패턴 감지"""
        anomalies = []
        
        for source in source_metrics:
            # 성공률 급락
            if source.success_rate < self.config['success_rate_threshold']:
                anomalies.append({
                    'type': '성공률 저하',
                    'description': f'성공률이 {source.success_rate:.1f}%로 임계값({self.config["success_rate_threshold"]}%) 미달',
                    'source': source.source_name,
                    'severity': 'high' if source.success_rate < 70 else 'medium'
                })
            
            # 품질 점수 저하
            if source.avg_quality_score < self.config['quality_thresholds']['warning']:
                severity = 'critical' if source.avg_quality_score < self.config['quality_thresholds']['critical'] else 'high'
                anomalies.append({
                    'type': '품질 점수 저하',
                    'description': f'평균 품질 점수가 {source.avg_quality_score:.1f}점으로 낮음',
                    'source': source.source_name,
                    'severity': severity
                })
            
            # 품질 트렌드 하락
            if len(source.quality_trend) >= 3:
                recent_trend = source.quality_trend[-3:]
                if all(recent_trend[i] > recent_trend[i+1] for i in range(len(recent_trend)-1)):
                    anomalies.append({
                        'type': '품질 트렌드 하락',
                        'description': f'최근 3일간 지속적인 품질 점수 하락 추세',
                        'source': source.source_name,
                        'severity': 'medium'
                    })
            
            # 높은 지연시간
            if source.latency_avg > 5000:  # 5초 이상
                anomalies.append({
                    'type': '높은 응답 지연',
                    'description': f'평균 응답시간이 {source.latency_avg:.0f}ms로 과도함',
                    'source': source.source_name,
                    'severity': 'medium'
                })
            
            # 데이터 불완전성
            if source.data_completeness < 0.8:  # 80% 미만
                anomalies.append({
                    'type': '데이터 불완전',
                    'description': f'데이터 완전성이 {source.data_completeness*100:.1f}%로 낮음',
                    'source': source.source_name,
                    'severity': 'high'
                })
            
            # 반복적인 에러 패턴
            if source.error_types:
                max_error_type = max(source.error_types, key=source.error_types.get)
                max_error_count = source.error_types[max_error_type]
                if max_error_count >= 5:  # 같은 에러가 5회 이상
                    anomalies.append({
                        'type': '반복적 에러',
                        'description': f'"{max_error_type}" 에러가 {max_error_count}회 반복 발생',
                        'source': source.source_name,
                        'severity': 'high'
                    })
        
        return sorted(anomalies, key=lambda x: {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}[x['severity']], reverse=True)
    
    def generate_recommendations(self, source_metrics: List[DataSourceMetrics], 
                               anomalies: List[Dict[str, Any]]) -> List[str]:
        """개선 권장사항 생성"""
        recommendations = []
        
        # 전체 성공률 기반 권장사항
        total_attempts = sum(s.collection_attempts for s in source_metrics)
        total_success = sum(s.successful_collections for s in source_metrics)
        overall_success_rate = (total_success / total_attempts * 100) if total_attempts > 0 else 0
        
        if overall_success_rate < 85:
            recommendations.append("전체 성공률이 85% 미만입니다. 네트워크 연결 및 API 엔드포인트 상태를 점검하세요.")
        
        # 품질 점수 기반 권장사항
        avg_quality = statistics.mean([s.avg_quality_score for s in source_metrics if s.avg_quality_score > 0])
        if avg_quality < 80:
            recommendations.append("평균 품질 점수가 낮습니다. 데이터 검증 로직을 강화하고 소스별 품질 기준을 재검토하세요.")
        
        # 이상 패턴별 권장사항
        anomaly_types = [a['type'] for a in anomalies]
        
        if '성공률 저하' in anomaly_types:
            recommendations.append("일부 데이터 소스의 성공률이 저하되었습니다. 해당 소스의 API 상태와 인증 정보를 확인하세요.")
        
        if '높은 응답 지연' in anomaly_types:
            recommendations.append("응답 시간이 긴 소스가 있습니다. 타임아웃 설정을 조정하거나 캐싱 전략을 도입하세요.")
        
        if '데이터 불완전' in anomaly_types:
            recommendations.append("데이터 완전성이 떨어지는 소스가 있습니다. 백업 데이터 소스 활용을 고려하세요.")
        
        if '반복적 에러' in anomaly_types:
            recommendations.append("동일한 에러가 반복 발생하는 소스가 있습니다. 에러 처리 로직과 재시도 메커니즘을 개선하세요.")
        
        # 기본 권장사항
        if not recommendations:
            recommendations.append("모든 데이터 소스가 정상적으로 운영되고 있습니다. 현재 품질 수준을 유지하세요.")
        
        recommendations.append("정기적인 모니터링을 통해 데이터 품질을 지속적으로 관리하세요.")
        recommendations.append("새로운 데이터 소스 추가 시 충분한 테스트와 검증을 수행하세요.")
        
        return recommendations
    
    async def generate_weekly_report(self, week_start: datetime = None) -> WeeklyReport:
        """주간 리포트 생성"""
        if week_start is None:
            # 지난 주 월요일부터 일요일까지
            today = datetime.now(timezone.utc)
            days_since_monday = today.weekday()
            week_start = (today - timedelta(days=days_since_monday + 7)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        week_end = week_start + timedelta(days=7)
        
        logger.info(f"주간 리포트 생성 중: {week_start.date()} ~ {week_end.date()}")
        
        try:
            # 데이터 소스 목록 조회
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT DISTINCT source_name FROM data_source_metrics 
                    WHERE timestamp BETWEEN ? AND ?
                ''', (week_start, week_end))
                source_names = [row[0] for row in cursor.fetchall()]
            
            if not source_names:
                logger.warning(f"지정된 기간에 데이터가 없습니다: {week_start.date()} ~ {week_end.date()}")
                source_names = ['DART_API', 'KRX_API', 'NAVER_FINANCE', 'SAMSUNG_API']  # 기본 소스들
            
            # 각 데이터 소스별 메트릭 수집
            source_metrics = []
            for source_name in source_names:
                metrics = self.get_source_metrics(source_name, week_start, week_end)
                source_metrics.append(metrics)
            
            # 전체 통계 계산
            total_sources = len(source_metrics)
            active_sources = sum(1 for s in source_metrics if s.collection_attempts > 0)
            inactive_sources = total_sources - active_sources
            
            # 전체 성공률 계산
            total_attempts = sum(s.collection_attempts for s in source_metrics)
            total_success = sum(s.successful_collections for s in source_metrics)
            overall_success_rate = (total_success / total_attempts * 100) if total_attempts > 0 else 0
            
            # 전체 품질 점수 계산
            quality_scores = [s.avg_quality_score for s in source_metrics if s.avg_quality_score > 0]
            overall_quality_score = statistics.mean(quality_scores) if quality_scores else 0
            
            # 전체 품질 트렌드 (모든 소스의 평균)
            max_trend_length = max(len(s.quality_trend) for s in source_metrics if s.quality_trend)
            quality_trend = []
            if max_trend_length > 0:
                for i in range(max_trend_length):
                    day_scores = []
                    for source in source_metrics:
                        if i < len(source.quality_trend):
                            day_scores.append(source.quality_trend[i])
                    if day_scores:
                        quality_trend.append(statistics.mean(day_scores))
            
            # 이상 패턴 감지
            anomalies = self.detect_anomalies(source_metrics)
            
            # 권장사항 생성
            recommendations = self.generate_recommendations(source_metrics, anomalies)
            
            report = WeeklyReport(
                week_start=week_start,
                week_end=week_end,
                total_sources=total_sources,
                active_sources=active_sources,
                inactive_sources=inactive_sources,
                overall_success_rate=overall_success_rate,
                overall_quality_score=overall_quality_score,
                quality_trend=quality_trend,
                source_metrics=source_metrics,
                anomalies=anomalies,
                recommendations=recommendations,
                generated_at=datetime.now(timezone.utc)
            )
            
            # 데이터베이스에 리포트 저장
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO weekly_reports (week_start, week_end, report_data, generated_at)
                    VALUES (?, ?, ?, ?)
                ''', (
                    week_start.date(),
                    week_end.date(),
                    json.dumps(asdict(report), default=str, ensure_ascii=False),
                    report.generated_at
                ))
            
            return report
            
        except Exception as e:
            logger.error(f"주간 리포트 생성 오류: {str(e)}")
            raise
    
    def save_report_as_html(self, report: WeeklyReport) -> str:
        """HTML 형식으로 리포트 저장"""
        try:
            template = self.jinja_env.get_template('weekly_report.html')
            html_content = template.render(report=report)
            
            filename = f"korean_data_weekly_report_{report.week_start.strftime('%Y%m%d')}.html"
            filepath = self.report_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"HTML 리포트 저장 완료: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"HTML 리포트 저장 오류: {str(e)}")
            raise
    
    def generate_charts(self, report: WeeklyReport) -> str:
        """차트 이미지 생성"""
        try:
            plt.style.use('seaborn-v0_8')
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('StockPilot KR 데이터 소스 주간 분석', fontsize=16, fontweight='bold')
            
            # 1. 데이터 소스별 성공률
            sources = [s.source_name for s in report.source_metrics]
            success_rates = [s.success_rate for s in report.source_metrics]
            
            colors = ['#28a745' if sr >= 90 else '#ffc107' if sr >= 70 else '#dc3545' for sr in success_rates]
            axes[0, 0].bar(sources, success_rates, color=colors)
            axes[0, 0].set_title('데이터 소스별 성공률', fontsize=12)
            axes[0, 0].set_ylabel('성공률 (%)')
            axes[0, 0].tick_params(axis='x', rotation=45)
            
            # 2. 품질 점수 분포
            quality_scores = [s.avg_quality_score for s in report.source_metrics if s.avg_quality_score > 0]
            if quality_scores:
                axes[0, 1].hist(quality_scores, bins=10, color='skyblue', alpha=0.7, edgecolor='black')
                axes[0, 1].set_title('품질 점수 분포', fontsize=12)
                axes[0, 1].set_xlabel('품질 점수')
                axes[0, 1].set_ylabel('빈도')
            
            # 3. 품질 트렌드
            if report.quality_trend:
                days = [f'Day {i+1}' for i in range(len(report.quality_trend))]
                axes[1, 0].plot(days, report.quality_trend, marker='o', linewidth=2, markersize=6)
                axes[1, 0].set_title('주간 품질 트렌드', fontsize=12)
                axes[1, 0].set_ylabel('평균 품질 점수')
                axes[1, 0].tick_params(axis='x', rotation=45)
            
            # 4. 응답 시간 비교
            latencies = [s.latency_avg for s in report.source_metrics if s.latency_avg > 0]
            if latencies:
                axes[1, 1].bar(sources[:len(latencies)], latencies, color='lightcoral')
                axes[1, 1].set_title('데이터 소스별 평균 응답시간', fontsize=12)
                axes[1, 1].set_ylabel('응답시간 (ms)')
                axes[1, 1].tick_params(axis='x', rotation=45)
            
            plt.tight_layout()
            
            chart_filename = f"korean_data_charts_{report.week_start.strftime('%Y%m%d')}.png"
            chart_filepath = self.report_dir / chart_filename
            
            plt.savefig(chart_filepath, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"차트 이미지 생성 완료: {chart_filepath}")
            return str(chart_filepath)
            
        except Exception as e:
            logger.error(f"차트 생성 오류: {str(e)}")
            raise
    
    async def send_email_report(self, report: WeeklyReport, html_file: str, chart_file: str):
        """이메일로 리포트 전송"""
        try:
            email_config = self.config['email_config']
            
            # 이메일 메시지 구성
            msg = MIMEMultipart('related')
            msg['Subject'] = f"StockPilot KR 데이터 소스 주간 리포트 ({report.week_start.strftime('%Y-%m-%d')})"
            msg['From'] = email_config['sender_email']
            msg['To'] = ', '.join(email_config['recipients'])
            
            # HTML 본문
            with open(html_file, 'r', encoding='utf-8') as f:
                html_body = f.read()
            
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))
            
            # 차트 이미지 첨부
            if Path(chart_file).exists():
                with open(chart_file, 'rb') as f:
                    img_data = f.read()
                    img = MIMEImage(img_data)
                    img.add_header('Content-ID', '<chart>')
                    msg.attach(img)
            
            # SMTP 서버로 전송
            with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
                server.starttls()
                server.login(email_config['sender_email'], email_config['sender_password'])
                server.send_message(msg)
            
            logger.info(f"이메일 리포트 전송 완료: {email_config['recipients']}")
            
        except Exception as e:
            logger.error(f"이메일 전송 오류: {str(e)}")
            # 이메일 전송 실패해도 리포트 생성은 계속 진행

async def main():
    """메인 실행 함수"""
    try:
        logger.info("KR 데이터 소스 주간 리포트 생성 시작")
        
        # 샘플 데이터 생성 (실제 환경에서는 제거)
        reporter = KoreanDataWeeklyReporter()
        
        # 최근 일주일간의 샘플 데이터 생성
        now = datetime.now(timezone.utc)
        for i in range(7):
            date = now - timedelta(days=i)
            
            # 각 데이터 소스별 샘플 데이터
            sources = ['DART_API', 'KRX_API', 'NAVER_FINANCE', 'SAMSUNG_API']
            for source in sources:
                # 하루에 여러번 수집
                for j in range(24):  # 매시간 수집
                    collection_time = date.replace(hour=j, minute=0, second=0, microsecond=0)
                    
                    # 성공/실패 랜덤 생성 (대부분 성공)
                    import random
                    success = random.random() > 0.1  # 90% 성공률
                    quality_score = random.uniform(70, 100) if success else None
                    latency = random.uniform(100, 2000) if success else None
                    completeness = random.uniform(0.8, 1.0) if success else None
                    
                    reporter.record_data_collection(
                        source_name=source,
                        success=success,
                        quality_score=quality_score,
                        error="Connection timeout" if not success else None,
                        latency_ms=latency,
                        completeness=completeness
                    )
        
        # 주간 리포트 생성
        report = await reporter.generate_weekly_report()
        
        # HTML 리포트 저장
        html_file = reporter.save_report_as_html(report)
        
        # 차트 생성
        chart_file = reporter.generate_charts(report)
        
        # 이메일 전송 (설정이 있을 경우)
        # await reporter.send_email_report(report, html_file, chart_file)
        
        logger.info("주간 리포트 생성 완료")
        
        # 요약 출력
        print("\n" + "="*60)
        print("StockPilot KR 데이터 소스 주간 리포트 요약")
        print("="*60)
        print(f"보고 기간: {report.week_start.date()} ~ {report.week_end.date()}")
        print(f"총 데이터 소스: {report.total_sources}")
        print(f"활성 소스: {report.active_sources}")
        print(f"전체 성공률: {report.overall_success_rate:.1f}%")
        print(f"평균 품질 점수: {report.overall_quality_score:.1f}")
        
        if report.anomalies:
            print(f"\n감지된 이상 패턴: {len(report.anomalies)}개")
            for anomaly in report.anomalies[:3]:  # 상위 3개만 표시
                print(f"  - {anomaly['type']}: {anomaly['description']}")
        
        print(f"\n파일 저장 위치:")
        print(f"  HTML 리포트: {html_file}")
        print(f"  차트 이미지: {chart_file}")
        
    except Exception as e:
        logger.error(f"리포트 생성 중 오류 발생: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())