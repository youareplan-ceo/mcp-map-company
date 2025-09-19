#!/usr/bin/env python3
"""
StockPilot AI 24시간 운영 모니터링 시스템
작성자: StockPilot Team
용도: 시스템 헬스 모니터링, 알림 발송, 성능 추적
"""

import asyncio
import json
import time
import psutil
import requests
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText, MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, List, Optional, Any
import logging
import aioredis
import psycopg2
import websockets
import os
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import schedule

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/monitoring.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    """알림 레벨 정의"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class SystemMetrics:
    """시스템 메트릭 데이터 클래스"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_io: Dict[str, int]
    process_count: int
    load_average: List[float]
    temperature: Optional[float] = None

@dataclass
class ServiceStatus:
    """서비스 상태 데이터 클래스"""
    service_name: str
    status: str  # 'healthy', 'unhealthy', 'degraded'
    response_time: float
    error_message: Optional[str] = None
    timestamp: datetime = None

@dataclass
class Alert:
    """알림 데이터 클래스"""
    level: AlertLevel
    title: str
    message: str
    service: str
    timestamp: datetime
    resolved: bool = False
    metadata: Dict[str, Any] = None

class NotificationChannel:
    """알림 채널 베이스 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('enabled', True)
    
    async def send_notification(self, alert: Alert) -> bool:
        """알림 발송 - 하위 클래스에서 구현"""
        raise NotImplementedError

class EmailNotifier(NotificationChannel):
    """이메일 알림 발송"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.smtp_host = config.get('smtp_host', 'smtp.gmail.com')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username')
        self.password = config.get('password')
        self.recipients = config.get('recipients', [])
    
    async def send_notification(self, alert: Alert) -> bool:
        """이메일 알림 발송"""
        try:
            # HTML 이메일 템플릿
            html_content = self._create_html_email(alert)
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[StockPilot AI] {alert.level.value.upper()}: {alert.title}"
            msg['From'] = self.username
            msg['To'] = ", ".join(self.recipients)
            
            # HTML 파트 추가
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # SMTP 서버 연결 및 발송
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"이메일 알림 발송 완료: {alert.title}")
            return True
            
        except Exception as e:
            logger.error(f"이메일 발송 실패: {e}")
            return False
    
    def _create_html_email(self, alert: Alert) -> str:
        """HTML 이메일 템플릿 생성"""
        colors = {
            AlertLevel.INFO: "#17a2b8",
            AlertLevel.WARNING: "#ffc107", 
            AlertLevel.ERROR: "#dc3545",
            AlertLevel.CRITICAL: "#dc3545"
        }
        
        color = colors.get(alert.level, "#6c757d")
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <div style="background: {color}; color: white; padding: 20px;">
                    <h1 style="margin: 0; font-size: 24px;">🚨 StockPilot AI 알림</h1>
                    <p style="margin: 10px 0 0 0; opacity: 0.9;">{alert.level.value.upper()} - {alert.service}</p>
                </div>
                <div style="padding: 30px;">
                    <h2 style="color: #333; margin-top: 0;">{alert.title}</h2>
                    <p style="color: #666; line-height: 1.6; font-size: 16px;">{alert.message}</p>
                    
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p style="margin: 5px 0;"><strong>서비스:</strong> {alert.service}</p>
                        <p style="margin: 5px 0;"><strong>시간:</strong> {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S KST')}</p>
                        <p style="margin: 5px 0;"><strong>상태:</strong> {'해결됨' if alert.resolved else '미해결'}</p>
                    </div>
                    
                    {self._format_metadata(alert.metadata) if alert.metadata else ''}
                    
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; text-align: center;">
                        <p style="color: #999; font-size: 12px;">
                            이 알림은 StockPilot AI 모니터링 시스템에서 자동으로 발송되었습니다.<br>
                            더 자세한 정보는 관리자 대시보드에서 확인하세요.
                        </p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        return html
    
    def _format_metadata(self, metadata: Dict[str, Any]) -> str:
        """메타데이터 HTML 포맷팅"""
        if not metadata:
            return ""
        
        items = []
        for key, value in metadata.items():
            items.append(f"<p style='margin: 5px 0;'><strong>{key}:</strong> {value}</p>")
        
        return f"""
        <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ffc107;">
            <h4 style="margin-top: 0; color: #856404;">추가 정보</h4>
            {''.join(items)}
        </div>
        """

class TelegramNotifier(NotificationChannel):
    """텔레그램 봇 알림 발송"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.bot_token = config.get('bot_token')
        self.chat_ids = config.get('chat_ids', [])
    
    async def send_notification(self, alert: Alert) -> bool:
        """텔레그램 알림 발송"""
        if not self.bot_token or not self.chat_ids:
            return False
        
        try:
            # 이모지 및 메시지 포맷팅
            emoji_map = {
                AlertLevel.INFO: "ℹ️",
                AlertLevel.WARNING: "⚠️",
                AlertLevel.ERROR: "❌",
                AlertLevel.CRITICAL: "🚨"
            }
            
            emoji = emoji_map.get(alert.level, "📢")
            message = self._format_telegram_message(alert, emoji)
            
            # 모든 채팅에 발송
            success_count = 0
            for chat_id in self.chat_ids:
                if await self._send_telegram_message(chat_id, message):
                    success_count += 1
            
            logger.info(f"텔레그램 알림 발송 완료: {success_count}/{len(self.chat_ids)}")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"텔레그램 발송 실패: {e}")
            return False
    
    async def _send_telegram_message(self, chat_id: str, message: str) -> bool:
        """개별 텔레그램 메시지 발송"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, data=data, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"텔레그램 메시지 발송 실패 (chat_id: {chat_id}): {e}")
            return False
    
    def _format_telegram_message(self, alert: Alert, emoji: str) -> str:
        """텔레그램 메시지 포맷팅"""
        status = "✅ 해결됨" if alert.resolved else "🔄 미해결"
        
        message = f"""
{emoji} *StockPilot AI 알림*

*레벨:* {alert.level.value.upper()}
*서비스:* {alert.service}
*제목:* {alert.title}

*내용:*
{alert.message}

*시간:* {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S KST')}
*상태:* {status}
        """.strip()
        
        if alert.metadata:
            message += "\n\n*추가 정보:*\n"
            for key, value in alert.metadata.items():
                message += f"• *{key}:* {value}\n"
        
        return message

class SlackNotifier(NotificationChannel):
    """Slack 웹훅 알림 발송"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.webhook_url = config.get('webhook_url')
        self.channel = config.get('channel', '#alerts')
    
    async def send_notification(self, alert: Alert) -> bool:
        """Slack 알림 발송"""
        if not self.webhook_url:
            return False
        
        try:
            payload = self._create_slack_payload(alert)
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Slack 알림 발송 완료: {alert.title}")
                return True
            else:
                logger.error(f"Slack 발송 실패: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Slack 발송 실패: {e}")
            return False
    
    def _create_slack_payload(self, alert: Alert) -> Dict[str, Any]:
        """Slack 페이로드 생성"""
        colors = {
            AlertLevel.INFO: "#36a64f",
            AlertLevel.WARNING: "#ff9500",
            AlertLevel.ERROR: "#ff0000",
            AlertLevel.CRITICAL: "#ff0000"
        }
        
        return {
            "channel": self.channel,
            "username": "StockPilot AI",
            "icon_emoji": ":robot_face:",
            "attachments": [{
                "color": colors.get(alert.level, "#cccccc"),
                "title": f"{alert.level.value.upper()}: {alert.title}",
                "text": alert.message,
                "fields": [
                    {
                        "title": "서비스",
                        "value": alert.service,
                        "short": True
                    },
                    {
                        "title": "시간",
                        "value": alert.timestamp.strftime('%Y-%m-%d %H:%M:%S KST'),
                        "short": True
                    },
                    {
                        "title": "상태",
                        "value": "해결됨" if alert.resolved else "미해결",
                        "short": True
                    }
                ],
                "footer": "StockPilot AI 모니터링 시스템",
                "ts": int(alert.timestamp.timestamp())
            }]
        }

class SystemMonitor:
    """시스템 모니터링 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.redis_client = None
        self.alerts_history: List[Alert] = []
        self.last_metrics: Optional[SystemMetrics] = None
        
        # 알림 채널 초기화
        self.notification_channels = []
        self._initialize_notification_channels()
        
        # 모니터링 임계값
        self.thresholds = config.get('thresholds', {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_percent': 90.0,
            'response_time': 5.0,  # 초
            'load_average': 4.0
        })
    
    def _initialize_notification_channels(self):
        """알림 채널 초기화"""
        notifications_config = self.config.get('notifications', {})
        
        # 이메일 알림
        if notifications_config.get('email', {}).get('enabled', False):
            email_notifier = EmailNotifier(notifications_config['email'])
            self.notification_channels.append(email_notifier)
        
        # 텔레그램 알림
        if notifications_config.get('telegram', {}).get('enabled', False):
            telegram_notifier = TelegramNotifier(notifications_config['telegram'])
            self.notification_channels.append(telegram_notifier)
        
        # Slack 알림
        if notifications_config.get('slack', {}).get('enabled', False):
            slack_notifier = SlackNotifier(notifications_config['slack'])
            self.notification_channels.append(slack_notifier)
        
        logger.info(f"알림 채널 {len(self.notification_channels)}개 초기화 완료")
    
    async def initialize(self):
        """모니터링 시스템 초기화"""
        try:
            # Redis 연결
            redis_config = self.config.get('redis', {})
            redis_url = f"redis://:{redis_config.get('password')}@{redis_config.get('host', 'localhost')}:{redis_config.get('port', 6379)}/0"
            self.redis_client = await aioredis.from_url(redis_url)
            
            logger.info("모니터링 시스템 초기화 완료")
            
        except Exception as e:
            logger.error(f"모니터링 시스템 초기화 실패: {e}")
            raise
    
    async def collect_system_metrics(self) -> SystemMetrics:
        """시스템 메트릭 수집"""
        try:
            # CPU 사용률
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 메모리 사용률
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 디스크 사용률
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # 네트워크 I/O
            net_io = psutil.net_io_counters()
            network_io = {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv
            }
            
            # 프로세스 수
            process_count = len(psutil.pids())
            
            # 로드 애버리지
            load_average = list(psutil.getloadavg())
            
            # 온도 (가능한 경우)
            temperature = None
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    # CPU 온도 찾기
                    for name, entries in temps.items():
                        if 'cpu' in name.lower() or 'core' in name.lower():
                            temperature = entries[0].current
                            break
            except:
                pass
            
            metrics = SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_percent=disk_percent,
                network_io=network_io,
                process_count=process_count,
                load_average=load_average,
                temperature=temperature
            )
            
            # Redis에 메트릭 저장
            if self.redis_client:
                await self.redis_client.lpush(
                    'system_metrics',
                    json.dumps(asdict(metrics), default=str)
                )
                # 최근 100개만 유지
                await self.redis_client.ltrim('system_metrics', 0, 99)
            
            self.last_metrics = metrics
            return metrics
            
        except Exception as e:
            logger.error(f"시스템 메트릭 수집 실패: {e}")
            raise
    
    async def check_service_health(self, service_config: Dict[str, Any]) -> ServiceStatus:
        """서비스 헬스체크"""
        service_name = service_config.get('name', 'Unknown')
        
        try:
            start_time = time.time()
            
            if service_config.get('type') == 'http':
                # HTTP 헬스체크
                url = service_config.get('url')
                response = requests.get(url, timeout=10)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    status = 'healthy'
                    error_message = None
                else:
                    status = 'unhealthy'
                    error_message = f"HTTP {response.status_code}: {response.text[:100]}"
            
            elif service_config.get('type') == 'websocket':
                # WebSocket 헬스체크
                uri = service_config.get('uri')
                async with websockets.connect(uri, timeout=10) as websocket:
                    await websocket.ping()
                    response_time = time.time() - start_time
                    status = 'healthy'
                    error_message = None
            
            elif service_config.get('type') == 'database':
                # 데이터베이스 헬스체크
                db_config = service_config.get('connection')
                conn = psycopg2.connect(**db_config)
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
                conn.close()
                
                response_time = time.time() - start_time
                status = 'healthy'
                error_message = None
            
            else:
                raise ValueError(f"지원하지 않는 서비스 타입: {service_config.get('type')}")
            
            return ServiceStatus(
                service_name=service_name,
                status=status,
                response_time=response_time,
                error_message=error_message,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            return ServiceStatus(
                service_name=service_name,
                status='unhealthy',
                response_time=time.time() - start_time,
                error_message=str(e),
                timestamp=datetime.now()
            )
    
    async def analyze_metrics_and_generate_alerts(self, metrics: SystemMetrics):
        """메트릭 분석 및 알림 생성"""
        alerts = []
        
        # CPU 사용률 체크
        if metrics.cpu_percent > self.thresholds['cpu_percent']:
            alerts.append(Alert(
                level=AlertLevel.WARNING if metrics.cpu_percent < 95 else AlertLevel.CRITICAL,
                title="높은 CPU 사용률 감지",
                message=f"CPU 사용률이 {metrics.cpu_percent:.1f}%에 도달했습니다.",
                service="시스템",
                timestamp=metrics.timestamp,
                metadata={'cpu_percent': f"{metrics.cpu_percent:.1f}%"}
            ))
        
        # 메모리 사용률 체크
        if metrics.memory_percent > self.thresholds['memory_percent']:
            alerts.append(Alert(
                level=AlertLevel.WARNING if metrics.memory_percent < 95 else AlertLevel.CRITICAL,
                title="높은 메모리 사용률 감지",
                message=f"메모리 사용률이 {metrics.memory_percent:.1f}%에 도달했습니다.",
                service="시스템",
                timestamp=metrics.timestamp,
                metadata={'memory_percent': f"{metrics.memory_percent:.1f}%"}
            ))
        
        # 디스크 사용률 체크
        if metrics.disk_percent > self.thresholds['disk_percent']:
            alerts.append(Alert(
                level=AlertLevel.ERROR if metrics.disk_percent < 98 else AlertLevel.CRITICAL,
                title="높은 디스크 사용률 감지",
                message=f"디스크 사용률이 {metrics.disk_percent:.1f}%에 도달했습니다.",
                service="시스템",
                timestamp=metrics.timestamp,
                metadata={'disk_percent': f"{metrics.disk_percent:.1f}%"}
            ))
        
        # 로드 애버리지 체크
        if metrics.load_average[0] > self.thresholds['load_average']:
            alerts.append(Alert(
                level=AlertLevel.WARNING,
                title="높은 시스템 로드 감지",
                message=f"1분 평균 로드가 {metrics.load_average[0]:.2f}에 도달했습니다.",
                service="시스템",
                timestamp=metrics.timestamp,
                metadata={'load_average': metrics.load_average}
            ))
        
        # 온도 체크 (가능한 경우)
        if metrics.temperature and metrics.temperature > 80:
            alerts.append(Alert(
                level=AlertLevel.WARNING if metrics.temperature < 90 else AlertLevel.CRITICAL,
                title="높은 시스템 온도 감지",
                message=f"시스템 온도가 {metrics.temperature:.1f}°C에 도달했습니다.",
                service="시스템",
                timestamp=metrics.timestamp,
                metadata={'temperature': f"{metrics.temperature:.1f}°C"}
            ))
        
        # 알림 발송
        for alert in alerts:
            await self.send_alert(alert)
    
    async def send_alert(self, alert: Alert):
        """알림 발송"""
        try:
            # 중복 알림 방지 (같은 서비스의 같은 제목 알림이 5분 내에 있으면 스킵)
            if self._is_duplicate_alert(alert):
                return
            
            # 알림 히스토리에 추가
            self.alerts_history.append(alert)
            
            # 모든 알림 채널에 발송
            for channel in self.notification_channels:
                if channel.enabled:
                    success = await channel.send_notification(alert)
                    if success:
                        logger.info(f"알림 발송 완료: {channel.__class__.__name__}")
                    else:
                        logger.warning(f"알림 발송 실패: {channel.__class__.__name__}")
            
            # Redis에 알림 저장
            if self.redis_client:
                await self.redis_client.lpush(
                    'alerts',
                    json.dumps(asdict(alert), default=str)
                )
                await self.redis_client.ltrim('alerts', 0, 499)  # 최근 500개만 유지
            
        except Exception as e:
            logger.error(f"알림 발송 실패: {e}")
    
    def _is_duplicate_alert(self, alert: Alert) -> bool:
        """중복 알림 체크"""
        cutoff_time = datetime.now() - timedelta(minutes=5)
        
        for existing_alert in self.alerts_history:
            if (existing_alert.timestamp > cutoff_time and
                existing_alert.service == alert.service and
                existing_alert.title == alert.title and
                not existing_alert.resolved):
                return True
        
        return False
    
    async def cleanup_old_data(self):
        """오래된 데이터 정리"""
        try:
            # 메모리에서 오래된 알림 제거 (24시간 이상)
            cutoff_time = datetime.now() - timedelta(hours=24)
            self.alerts_history = [
                alert for alert in self.alerts_history 
                if alert.timestamp > cutoff_time
            ]
            
            logger.info(f"오래된 알림 정리 완료. 현재 알림 수: {len(self.alerts_history)}")
            
        except Exception as e:
            logger.error(f"데이터 정리 실패: {e}")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 요약 반환"""
        try:
            current_metrics = await self.collect_system_metrics()
            
            # 최근 알림 수집 (1시간 이내)
            recent_cutoff = datetime.now() - timedelta(hours=1)
            recent_alerts = [
                alert for alert in self.alerts_history 
                if alert.timestamp > recent_cutoff and not alert.resolved
            ]
            
            return {
                'timestamp': datetime.now().isoformat(),
                'system_metrics': asdict(current_metrics),
                'recent_alerts_count': len(recent_alerts),
                'critical_alerts_count': len([a for a in recent_alerts if a.level == AlertLevel.CRITICAL]),
                'monitoring_status': 'healthy',
                'uptime': self._get_system_uptime(),
                'total_alerts_today': len([
                    a for a in self.alerts_history 
                    if a.timestamp.date() == datetime.now().date()
                ])
            }
            
        except Exception as e:
            logger.error(f"시스템 상태 조회 실패: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'monitoring_status': 'error',
                'error_message': str(e)
            }
    
    def _get_system_uptime(self) -> str:
        """시스템 업타임 조회"""
        try:
            uptime_seconds = time.time() - psutil.boot_time()
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            return f"{days}일 {hours}시간 {minutes}분"
        except:
            return "알 수 없음"

class MonitoringService:
    """모니터링 서비스 메인 클래스"""
    
    def __init__(self, config_file: str = "/app/config/monitoring.json"):
        self.config_file = config_file
        self.config = self._load_config()
        self.monitor = SystemMonitor(self.config)
        self.running = False
    
    def _load_config(self) -> Dict[str, Any]:
        """설정 파일 로드"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # 기본 설정 반환
            return self._get_default_config()
        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """기본 설정 반환"""
        return {
            "monitoring_interval": 60,  # 초
            "thresholds": {
                "cpu_percent": 80.0,
                "memory_percent": 85.0,
                "disk_percent": 90.0,
                "response_time": 5.0,
                "load_average": 4.0
            },
            "services": [
                {
                    "name": "StockPilot Backend API",
                    "type": "http",
                    "url": "http://localhost:8000/health"
                },
                {
                    "name": "StockPilot WebSocket",
                    "type": "websocket",
                    "uri": "ws://localhost:8765"
                }
            ],
            "redis": {
                "host": os.getenv('REDIS_HOST', 'localhost'),
                "port": int(os.getenv('REDIS_PORT', 6379)),
                "password": os.getenv('REDIS_PASSWORD', '')
            },
            "notifications": {
                "email": {
                    "enabled": True,
                    "smtp_host": os.getenv('SMTP_HOST', 'smtp.gmail.com'),
                    "smtp_port": int(os.getenv('SMTP_PORT', 587)),
                    "username": os.getenv('SMTP_USERNAME', ''),
                    "password": os.getenv('SMTP_PASSWORD', ''),
                    "recipients": os.getenv('ALERT_EMAIL_RECIPIENTS', '').split(',')
                },
                "telegram": {
                    "enabled": bool(os.getenv('TELEGRAM_BOT_TOKEN')),
                    "bot_token": os.getenv('TELEGRAM_BOT_TOKEN', ''),
                    "chat_ids": os.getenv('TELEGRAM_CHAT_IDS', '').split(',')
                },
                "slack": {
                    "enabled": bool(os.getenv('SLACK_WEBHOOK_URL')),
                    "webhook_url": os.getenv('SLACK_WEBHOOK_URL', ''),
                    "channel": os.getenv('SLACK_CHANNEL', '#alerts')
                }
            }
        }
    
    async def start_monitoring(self):
        """모니터링 시작"""
        try:
            logger.info("StockPilot AI 모니터링 시스템을 시작합니다...")
            
            # 모니터링 시스템 초기화
            await self.monitor.initialize()
            
            # 시작 알림 발송
            start_alert = Alert(
                level=AlertLevel.INFO,
                title="모니터링 시스템 시작",
                message="StockPilot AI 모니터링 시스템이 정상적으로 시작되었습니다.",
                service="모니터링",
                timestamp=datetime.now()
            )
            await self.monitor.send_alert(start_alert)
            
            self.running = True
            
            # 주기적 작업 스케줄링
            schedule.every(1).minutes.do(self._schedule_metric_collection)
            schedule.every(30).seconds.do(self._schedule_service_checks)
            schedule.every(1).hours.do(self._schedule_cleanup)
            
            # 메인 모니터링 루프
            while self.running:
                try:
                    # 스케줄된 작업 실행
                    schedule.run_pending()
                    
                    await asyncio.sleep(1)
                    
                except KeyboardInterrupt:
                    logger.info("모니터링 중단 요청 받음")
                    break
                except Exception as e:
                    logger.error(f"모니터링 루프 오류: {e}")
                    await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"모니터링 시스템 실행 실패: {e}")
            raise
        finally:
            await self.stop_monitoring()
    
    def _schedule_metric_collection(self):
        """메트릭 수집 스케줄링"""
        asyncio.create_task(self._collect_and_analyze())
    
    def _schedule_service_checks(self):
        """서비스 체크 스케줄링"""
        asyncio.create_task(self._check_all_services())
    
    def _schedule_cleanup(self):
        """정리 작업 스케줄링"""
        asyncio.create_task(self.monitor.cleanup_old_data())
    
    async def _collect_and_analyze(self):
        """메트릭 수집 및 분석"""
        try:
            metrics = await self.monitor.collect_system_metrics()
            await self.monitor.analyze_metrics_and_generate_alerts(metrics)
        except Exception as e:
            logger.error(f"메트릭 수집 실패: {e}")
    
    async def _check_all_services(self):
        """모든 서비스 상태 체크"""
        try:
            services = self.config.get('services', [])
            
            for service_config in services:
                status = await self.monitor.check_service_health(service_config)
                
                if status.status != 'healthy':
                    alert = Alert(
                        level=AlertLevel.ERROR,
                        title=f"서비스 상태 이상: {status.service_name}",
                        message=f"서비스가 비정상 상태입니다. 응답시간: {status.response_time:.2f}초",
                        service=status.service_name,
                        timestamp=status.timestamp,
                        metadata={
                            'response_time': f"{status.response_time:.2f}초",
                            'error_message': status.error_message or '알 수 없는 오류'
                        }
                    )
                    await self.monitor.send_alert(alert)
                
        except Exception as e:
            logger.error(f"서비스 체크 실패: {e}")
    
    async def stop_monitoring(self):
        """모니터링 중단"""
        try:
            logger.info("모니터링 시스템을 중단합니다...")
            self.running = False
            
            # 중단 알림 발송
            stop_alert = Alert(
                level=AlertLevel.INFO,
                title="모니터링 시스템 중단",
                message="StockPilot AI 모니터링 시스템이 중단되었습니다.",
                service="모니터링",
                timestamp=datetime.now()
            )
            await self.monitor.send_alert(stop_alert)
            
            # Redis 연결 해제
            if self.monitor.redis_client:
                await self.monitor.redis_client.close()
            
            logger.info("모니터링 시스템 중단 완료")
            
        except Exception as e:
            logger.error(f"모니터링 중단 실패: {e}")

async def main():
    """메인 실행 함수"""
    try:
        # 설정 디렉토리 생성
        os.makedirs('/app/config', exist_ok=True)
        os.makedirs('/app/logs', exist_ok=True)
        
        # 모니터링 서비스 시작
        monitoring_service = MonitoringService()
        await monitoring_service.start_monitoring()
        
    except Exception as e:
        logger.error(f"모니터링 시스템 실행 실패: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())