#!/usr/bin/env python3
"""
StockPilot AI 다중 알림 채널 통합 서비스
작성자: StockPilot Team
용도: 텔레그램, 이메일, Slack, Discord, SMS 등 다중 채널 알림 발송
"""

import asyncio
import json
import time
import aiohttp
import smtplib
import ssl
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, List, Optional, Any, Union
import logging
import aioredis
import os
from dataclasses import dataclass, asdict, field
from enum import Enum
import hashlib
import base64
from jinja2 import Template
import requests
from urllib.parse import urlencode

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/notifications.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NotificationType(Enum):
    """알림 유형 정의"""
    TRADE_SIGNAL = "trade_signal"
    PORTFOLIO_UPDATE = "portfolio_update"
    MARKET_ALERT = "market_alert"
    SYSTEM_STATUS = "system_status"
    PRICE_ALERT = "price_alert"
    NEWS_UPDATE = "news_update"
    ERROR_ALERT = "error_alert"
    MAINTENANCE = "maintenance"
    WELCOME = "welcome"
    CUSTOM = "custom"

class NotificationPriority(Enum):
    """알림 우선순위"""
    LOW = "low"
    NORMAL = "normal"  
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"

@dataclass
class NotificationTemplate:
    """알림 템플릿 데이터 클래스"""
    title_template: str
    message_template: str
    html_template: Optional[str] = None
    emoji: str = "📢"
    color: str = "#007bff"

@dataclass 
class NotificationUser:
    """알림 수신자 정보"""
    user_id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    slack_user_id: Optional[str] = None
    discord_user_id: Optional[str] = None
    preferences: Dict[str, Any] = field(default_factory=dict)
    enabled_channels: List[str] = field(default_factory=list)

@dataclass
class NotificationMessage:
    """알림 메시지 데이터 클래스"""
    id: str
    type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    recipients: List[str] = field(default_factory=list)  # user_ids
    channels: List[str] = field(default_factory=list)   # channel names
    scheduled_time: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    delivery_status: Dict[str, str] = field(default_factory=dict)  # channel -> status

class BaseNotificationChannel:
    """알림 채널 베이스 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('enabled', True)
        self.name = config.get('name', self.__class__.__name__)
        self.rate_limit = config.get('rate_limit', {})
        self.retry_config = config.get('retry', {
            'max_attempts': 3,
            'delay': 1,
            'backoff_multiplier': 2
        })
    
    async def send_notification(self, message: NotificationMessage, user: NotificationUser) -> bool:
        """알림 발송 - 하위 클래스에서 구현"""
        raise NotImplementedError
    
    def format_message(self, message: NotificationMessage, template: NotificationTemplate) -> Dict[str, str]:
        """메시지 포맷팅"""
        template_vars = {
            'title': message.title,
            'message': message.message,
            'type': message.type.value,
            'priority': message.priority.value,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            **message.data
        }
        
        title = Template(template.title_template).render(**template_vars)
        content = Template(template.message_template).render(**template_vars)
        html_content = None
        
        if template.html_template:
            html_content = Template(template.html_template).render(**template_vars)
        
        return {
            'title': title,
            'content': content,
            'html_content': html_content,
            'emoji': template.emoji,
            'color': template.color
        }

class EmailNotificationChannel(BaseNotificationChannel):
    """이메일 알림 채널"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.smtp_host = config.get('smtp_host', 'smtp.gmail.com')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username', '')
        self.password = config.get('password', '')
        self.from_name = config.get('from_name', 'StockPilot AI')
    
    async def send_notification(self, message: NotificationMessage, user: NotificationUser) -> bool:
        """이메일 알림 발송"""
        if not user.email:
            return False
        
        try:
            template = self._get_template_for_type(message.type)
            formatted = self.format_message(message, template)
            
            # HTML 이메일 생성
            msg = MIMEMultipart('alternative')
            msg['Subject'] = formatted['title']
            msg['From'] = f"{self.from_name} <{self.username}>"
            msg['To'] = user.email
            
            # 텍스트 버전
            text_part = MIMEText(formatted['content'], 'plain', 'utf-8')
            msg.attach(text_part)
            
            # HTML 버전 (있는 경우)
            if formatted['html_content']:
                html_part = MIMEText(formatted['html_content'], 'html', 'utf-8')
                msg.attach(html_part)
            
            # SMTP 발송
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"이메일 알림 발송 성공: {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"이메일 발송 실패 ({user.email}): {e}")
            return False
    
    def _get_template_for_type(self, notification_type: NotificationType) -> NotificationTemplate:
        """알림 유형별 템플릿 반환"""
        templates = {
            NotificationType.TRADE_SIGNAL: NotificationTemplate(
                title_template="📈 [StockPilot] {{type.upper()}} - {{title}}",
                message_template="""
안녕하세요 {{user_name}}님,

새로운 투자 신호가 감지되었습니다.

제목: {{title}}
내용: {{message}}

상세 정보:
{% for key, value in data.items() %}
- {{key}}: {{value}}
{% endfor %}

시간: {{timestamp}}

더 자세한 정보는 대시보드에서 확인하세요.
https://stockpilot.ai/dashboard

StockPilot AI 팀 드림
                """,
                html_template=self._get_html_template(),
                emoji="📈",
                color="#28a745"
            ),
            NotificationType.PRICE_ALERT: NotificationTemplate(
                title_template="🚨 [StockPilot] 가격 알림 - {{title}}",
                message_template="{{message}}\n\n시간: {{timestamp}}",
                emoji="🚨",
                color="#dc3545"
            ),
            NotificationType.SYSTEM_STATUS: NotificationTemplate(
                title_template="⚙️ [StockPilot] 시스템 알림 - {{title}}",
                message_template="{{message}}\n\n시간: {{timestamp}}",
                emoji="⚙️",
                color="#6c757d"
            )
        }
        
        return templates.get(notification_type, NotificationTemplate(
            title_template="📢 [StockPilot] {{title}}",
            message_template="{{message}}\n\n시간: {{timestamp}}"
        ))
    
    def _get_html_template(self) -> str:
        """HTML 이메일 템플릿"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>{{title}}</title>
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 0; background-color: #f8f9fa; }
                .container { max-width: 600px; margin: 0 auto; background: white; }
                .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px 20px; text-align: center; }
                .content { padding: 30px 20px; }
                .footer { background: #f8f9fa; padding: 20px; text-align: center; color: #6c757d; font-size: 14px; }
                .badge { display: inline-block; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; }
                .badge-high { background: #dc3545; color: white; }
                .badge-normal { background: #007bff; color: white; }
                .data-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                .data-table td { padding: 10px; border-bottom: 1px solid #eee; }
                .data-table td:first-child { font-weight: bold; width: 30%; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{{emoji}} StockPilot AI</h1>
                    <p>{{title}}</p>
                    <span class="badge badge-{{priority}}">{{priority.upper()}}</span>
                </div>
                
                <div class="content">
                    <p>{{message}}</p>
                    
                    {% if data %}
                    <table class="data-table">
                        {% for key, value in data.items() %}
                        <tr>
                            <td>{{key}}</td>
                            <td>{{value}}</td>
                        </tr>
                        {% endfor %}
                    </table>
                    {% endif %}
                    
                    <p><strong>시간:</strong> {{timestamp}}</p>
                </div>
                
                <div class="footer">
                    <p>이 알림은 StockPilot AI에서 자동으로 발송되었습니다.</p>
                    <p><a href="https://stockpilot.ai">StockPilot AI 방문하기</a> | <a href="#">구독 해제</a></p>
                </div>
            </div>
        </body>
        </html>
        """

class TelegramNotificationChannel(BaseNotificationChannel):
    """텔레그램 봇 알림 채널"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.bot_token = config.get('bot_token', '')
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    async def send_notification(self, message: NotificationMessage, user: NotificationUser) -> bool:
        """텔레그램 알림 발송"""
        if not user.telegram_chat_id or not self.bot_token:
            return False
        
        try:
            template = self._get_template_for_type(message.type)
            formatted = self.format_message(message, template)
            
            # 텔레그램 메시지 포맷팅
            telegram_message = self._format_telegram_message(formatted, message)
            
            # API 호출
            async with aiohttp.ClientSession() as session:
                url = f"{self.api_url}/sendMessage"
                data = {
                    'chat_id': user.telegram_chat_id,
                    'text': telegram_message,
                    'parse_mode': 'Markdown',
                    'disable_web_page_preview': True
                }
                
                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        logger.info(f"텔레그램 알림 발송 성공: {user.telegram_chat_id}")
                        return True
                    else:
                        logger.error(f"텔레그램 발송 실패: HTTP {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"텔레그램 발송 실패 ({user.telegram_chat_id}): {e}")
            return False
    
    def _get_template_for_type(self, notification_type: NotificationType) -> NotificationTemplate:
        """알림 유형별 템플릿"""
        templates = {
            NotificationType.TRADE_SIGNAL: NotificationTemplate(
                title_template="{{title}}",
                message_template="{{message}}",
                emoji="📈"
            ),
            NotificationType.PRICE_ALERT: NotificationTemplate(
                title_template="{{title}}",
                message_template="{{message}}",
                emoji="🚨"
            ),
            NotificationType.MARKET_ALERT: NotificationTemplate(
                title_template="{{title}}",
                message_template="{{message}}",
                emoji="📊"
            )
        }
        
        return templates.get(notification_type, NotificationTemplate(
            title_template="{{title}}",
            message_template="{{message}}"
        ))
    
    def _format_telegram_message(self, formatted: Dict[str, str], message: NotificationMessage) -> str:
        """텔레그램용 메시지 포맷팅"""
        priority_emoji = {
            NotificationPriority.LOW: "🔵",
            NotificationPriority.NORMAL: "🟢", 
            NotificationPriority.HIGH: "🟡",
            NotificationPriority.URGENT: "🟠",
            NotificationPriority.CRITICAL: "🔴"
        }
        
        emoji = priority_emoji.get(message.priority, "📢")
        
        text = f"{formatted['emoji']} *{formatted['title']}*\n\n"
        text += f"{formatted['content']}\n\n"
        
        if message.data:
            text += "*추가 정보:*\n"
            for key, value in message.data.items():
                text += f"• *{key}:* {value}\n"
            text += "\n"
        
        text += f"{emoji} *우선순위:* {message.priority.value.upper()}\n"
        text += f"🕐 *시간:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return text

class SlackNotificationChannel(BaseNotificationChannel):
    """Slack 웹훅 알림 채널"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.webhook_url = config.get('webhook_url', '')
        self.channel = config.get('channel', '#general')
        self.username = config.get('username', 'StockPilot AI')
        self.icon_emoji = config.get('icon_emoji', ':robot_face:')
    
    async def send_notification(self, message: NotificationMessage, user: NotificationUser) -> bool:
        """Slack 알림 발송"""
        if not self.webhook_url:
            return False
        
        try:
            template = self._get_template_for_type(message.type)
            formatted = self.format_message(message, template)
            
            payload = self._create_slack_payload(formatted, message, user)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info(f"Slack 알림 발송 성공: {user.name}")
                        return True
                    else:
                        logger.error(f"Slack 발송 실패: HTTP {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Slack 발송 실패: {e}")
            return False
    
    def _get_template_for_type(self, notification_type: NotificationType) -> NotificationTemplate:
        """알림 유형별 템플릿"""
        return NotificationTemplate(
            title_template="{{title}}",
            message_template="{{message}}",
            emoji="📢",
            color="#007bff"
        )
    
    def _create_slack_payload(self, formatted: Dict[str, str], message: NotificationMessage, user: NotificationUser) -> Dict[str, Any]:
        """Slack 페이로드 생성"""
        color_map = {
            NotificationPriority.LOW: "#28a745",
            NotificationPriority.NORMAL: "#007bff",
            NotificationPriority.HIGH: "#ffc107", 
            NotificationPriority.URGENT: "#fd7e14",
            NotificationPriority.CRITICAL: "#dc3545"
        }
        
        attachment = {
            "color": color_map.get(message.priority, "#007bff"),
            "title": formatted['title'],
            "text": formatted['content'],
            "fields": [
                {
                    "title": "우선순위",
                    "value": message.priority.value.upper(),
                    "short": True
                },
                {
                    "title": "유형", 
                    "value": message.type.value,
                    "short": True
                },
                {
                    "title": "시간",
                    "value": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "short": True
                }
            ],
            "footer": "StockPilot AI",
            "ts": int(time.time())
        }
        
        # 추가 데이터가 있으면 필드에 추가
        for key, value in message.data.items():
            attachment["fields"].append({
                "title": key,
                "value": str(value),
                "short": True
            })
        
        return {
            "channel": self.channel,
            "username": self.username,
            "icon_emoji": self.icon_emoji,
            "attachments": [attachment]
        }

class DiscordNotificationChannel(BaseNotificationChannel):
    """Discord 웹훅 알림 채널"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.webhook_url = config.get('webhook_url', '')
        self.username = config.get('username', 'StockPilot AI')
        self.avatar_url = config.get('avatar_url', '')
    
    async def send_notification(self, message: NotificationMessage, user: NotificationUser) -> bool:
        """Discord 알림 발송"""
        if not self.webhook_url:
            return False
        
        try:
            template = self._get_template_for_type(message.type)
            formatted = self.format_message(message, template)
            
            payload = self._create_discord_payload(formatted, message)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 204:  # Discord returns 204 for success
                        logger.info(f"Discord 알림 발송 성공: {user.name}")
                        return True
                    else:
                        logger.error(f"Discord 발송 실패: HTTP {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Discord 발송 실패: {e}")
            return False
    
    def _get_template_for_type(self, notification_type: NotificationType) -> NotificationTemplate:
        """알림 유형별 템플릿"""
        return NotificationTemplate(
            title_template="{{title}}",
            message_template="{{message}}",
            emoji="📢"
        )
    
    def _create_discord_payload(self, formatted: Dict[str, str], message: NotificationMessage) -> Dict[str, Any]:
        """Discord 페이로드 생성"""
        color_map = {
            NotificationPriority.LOW: 0x28a745,
            NotificationPriority.NORMAL: 0x007bff,
            NotificationPriority.HIGH: 0xffc107,
            NotificationPriority.URGENT: 0xfd7e14,
            NotificationPriority.CRITICAL: 0xdc3545
        }
        
        embed = {
            "title": f"{formatted['emoji']} {formatted['title']}",
            "description": formatted['content'],
            "color": color_map.get(message.priority, 0x007bff),
            "timestamp": datetime.now().isoformat(),
            "footer": {
                "text": "StockPilot AI"
            },
            "fields": [
                {
                    "name": "우선순위",
                    "value": message.priority.value.upper(),
                    "inline": True
                },
                {
                    "name": "유형",
                    "value": message.type.value,
                    "inline": True
                }
            ]
        }
        
        # 추가 데이터 필드 추가
        for key, value in message.data.items():
            embed["fields"].append({
                "name": key,
                "value": str(value),
                "inline": True
            })
        
        payload = {
            "username": self.username,
            "embeds": [embed]
        }
        
        if self.avatar_url:
            payload["avatar_url"] = self.avatar_url
        
        return payload

class SMSNotificationChannel(BaseNotificationChannel):
    """SMS 알림 채널 (Twilio 사용)"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.account_sid = config.get('twilio_account_sid', '')
        self.auth_token = config.get('twilio_auth_token', '')
        self.from_number = config.get('from_number', '')
        self.api_url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
    
    async def send_notification(self, message: NotificationMessage, user: NotificationUser) -> bool:
        """SMS 알림 발송"""
        if not user.phone or not self.account_sid:
            return False
        
        try:
            template = self._get_template_for_type(message.type)
            formatted = self.format_message(message, template)
            
            # SMS용 짧은 메시지 생성
            sms_text = f"{formatted['emoji']} {formatted['title'][:50]}\n{formatted['content'][:100]}..."
            
            # Twilio API 호출
            auth = base64.b64encode(f"{self.account_sid}:{self.auth_token}".encode()).decode()
            headers = {
                'Authorization': f'Basic {auth}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'From': self.from_number,
                'To': user.phone,
                'Body': sms_text
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, headers=headers, data=urlencode(data)) as response:
                    if response.status == 201:
                        logger.info(f"SMS 알림 발송 성공: {user.phone}")
                        return True
                    else:
                        logger.error(f"SMS 발송 실패: HTTP {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"SMS 발송 실패 ({user.phone}): {e}")
            return False
    
    def _get_template_for_type(self, notification_type: NotificationType) -> NotificationTemplate:
        """SMS용 간단한 템플릿"""
        return NotificationTemplate(
            title_template="{{title}}",
            message_template="{{message}}",
            emoji="📱"
        )

class NotificationService:
    """통합 알림 서비스"""
    
    def __init__(self, config_file: str = "/app/config/notifications.json"):
        self.config_file = config_file
        self.config = self._load_config()
        self.redis_client = None
        self.channels: Dict[str, BaseNotificationChannel] = {}
        self.users: Dict[str, NotificationUser] = {}
        self._initialize_channels()
    
    def _load_config(self) -> Dict[str, Any]:
        """설정 파일 로드"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return self._get_default_config()
        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """기본 설정 반환"""
        return {
            "channels": {
                "email": {
                    "enabled": True,
                    "smtp_host": os.getenv('SMTP_HOST', 'smtp.gmail.com'),
                    "smtp_port": int(os.getenv('SMTP_PORT', 587)),
                    "username": os.getenv('SMTP_USERNAME', ''),
                    "password": os.getenv('SMTP_PASSWORD', ''),
                    "from_name": "StockPilot AI"
                },
                "telegram": {
                    "enabled": bool(os.getenv('TELEGRAM_BOT_TOKEN')),
                    "bot_token": os.getenv('TELEGRAM_BOT_TOKEN', '')
                },
                "slack": {
                    "enabled": bool(os.getenv('SLACK_WEBHOOK_URL')),
                    "webhook_url": os.getenv('SLACK_WEBHOOK_URL', ''),
                    "channel": "#alerts"
                }
            },
            "redis": {
                "host": os.getenv('REDIS_HOST', 'localhost'),
                "port": int(os.getenv('REDIS_PORT', 6379)),
                "password": os.getenv('REDIS_PASSWORD', '')
            }
        }
    
    def _initialize_channels(self):
        """알림 채널 초기화"""
        channel_classes = {
            'email': EmailNotificationChannel,
            'telegram': TelegramNotificationChannel,
            'slack': SlackNotificationChannel,
            'discord': DiscordNotificationChannel,
            'sms': SMSNotificationChannel
        }
        
        for channel_name, channel_config in self.config.get('channels', {}).items():
            if channel_config.get('enabled', False):
                channel_class = channel_classes.get(channel_name)
                if channel_class:
                    self.channels[channel_name] = channel_class(channel_config)
                    logger.info(f"알림 채널 초기화: {channel_name}")
        
        logger.info(f"총 {len(self.channels)}개 알림 채널 활성화됨")
    
    async def initialize(self):
        """서비스 초기화"""
        try:
            # Redis 연결
            redis_config = self.config.get('redis', {})
            redis_url = f"redis://:{redis_config.get('password')}@{redis_config.get('host', 'localhost')}:{redis_config.get('port', 6379)}/1"
            self.redis_client = await aioredis.from_url(redis_url)
            
            # 사용자 데이터 로드
            await self._load_users()
            
            logger.info("알림 서비스 초기화 완료")
            
        except Exception as e:
            logger.error(f"알림 서비스 초기화 실패: {e}")
            raise
    
    async def _load_users(self):
        """사용자 데이터 로드"""
        try:
            if self.redis_client:
                users_data = await self.redis_client.hgetall('notification_users')
                for user_id, user_json in users_data.items():
                    user_data = json.loads(user_json)
                    self.users[user_id.decode()] = NotificationUser(**user_data)
                
                logger.info(f"{len(self.users)}명의 사용자 데이터 로드됨")
        except Exception as e:
            logger.error(f"사용자 데이터 로드 실패: {e}")
    
    async def register_user(self, user: NotificationUser):
        """사용자 등록"""
        try:
            self.users[user.user_id] = user
            
            if self.redis_client:
                await self.redis_client.hset(
                    'notification_users',
                    user.user_id,
                    json.dumps(asdict(user), default=str)
                )
            
            logger.info(f"사용자 등록 완료: {user.name} ({user.user_id})")
            
        except Exception as e:
            logger.error(f"사용자 등록 실패: {e}")
            raise
    
    async def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]):
        """사용자 알림 설정 업데이트"""
        try:
            if user_id in self.users:
                self.users[user_id].preferences.update(preferences)
                
                if self.redis_client:
                    await self.redis_client.hset(
                        'notification_users',
                        user_id,
                        json.dumps(asdict(self.users[user_id]), default=str)
                    )
                
                logger.info(f"사용자 설정 업데이트: {user_id}")
                return True
            else:
                logger.warning(f"사용자를 찾을 수 없음: {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"사용자 설정 업데이트 실패: {e}")
            return False
    
    async def send_notification(self, message: NotificationMessage) -> Dict[str, bool]:
        """알림 발송"""
        results = {}
        
        try:
            # 메시지 ID 생성 (없는 경우)
            if not message.id:
                message.id = self._generate_message_id(message)
            
            # 발송 대상 사용자 결정
            target_users = []
            if message.recipients:
                # 특정 사용자들
                for user_id in message.recipients:
                    if user_id in self.users:
                        target_users.append(self.users[user_id])
            else:
                # 모든 사용자 (유형별 필터링 적용)
                target_users = list(self.users.values())
            
            # 각 사용자별로 각 채널에 발송
            for user in target_users:
                user_results = {}
                
                # 사용자 설정에 따른 채널 결정
                channels_to_use = self._get_channels_for_user(user, message)
                
                for channel_name in channels_to_use:
                    if channel_name in self.channels:
                        channel = self.channels[channel_name]
                        
                        # 발송 시도
                        try:
                            success = await channel.send_notification(message, user)
                            user_results[channel_name] = success
                            
                            if success:
                                logger.info(f"알림 발송 성공: {user.name} via {channel_name}")
                            else:
                                logger.warning(f"알림 발송 실패: {user.name} via {channel_name}")
                                
                        except Exception as e:
                            logger.error(f"알림 발송 오류: {user.name} via {channel_name}: {e}")
                            user_results[channel_name] = False
                
                results[user.user_id] = user_results
            
            # 발송 결과 저장
            message.sent_at = datetime.now()
            message.delivery_status = results
            await self._save_message_log(message)
            
            return results
            
        except Exception as e:
            logger.error(f"알림 발송 처리 실패: {e}")
            return {}
    
    def _generate_message_id(self, message: NotificationMessage) -> str:
        """메시지 ID 생성"""
        content = f"{message.type.value}_{message.title}_{message.created_at.isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _get_channels_for_user(self, user: NotificationUser, message: NotificationMessage) -> List[str]:
        """사용자별 사용할 채널 결정"""
        # 메시지에 명시된 채널이 있으면 사용
        if message.channels:
            return [ch for ch in message.channels if ch in user.enabled_channels]
        
        # 사용자 설정에 따른 채널 결정
        user_channels = user.enabled_channels or list(self.channels.keys())
        
        # 우선순위별 필터링
        if message.priority == NotificationPriority.CRITICAL:
            # 중요 알림은 모든 채널 사용
            return user_channels
        elif message.priority in [NotificationPriority.HIGH, NotificationPriority.URGENT]:
            # 높은 우선순위는 즉시 알림 채널 우선 (텔레그램, SMS)
            priority_channels = ['telegram', 'sms', 'email']
            return [ch for ch in priority_channels if ch in user_channels]
        else:
            # 일반 알림은 사용자 설정대로
            return user_channels
    
    async def _save_message_log(self, message: NotificationMessage):
        """메시지 로그 저장"""
        try:
            if self.redis_client:
                log_data = asdict(message)
                await self.redis_client.lpush(
                    'notification_logs',
                    json.dumps(log_data, default=str)
                )
                # 최근 1000개만 유지
                await self.redis_client.ltrim('notification_logs', 0, 999)
        except Exception as e:
            logger.error(f"메시지 로그 저장 실패: {e}")
    
    async def send_bulk_notification(self, messages: List[NotificationMessage]) -> Dict[str, Dict[str, bool]]:
        """대량 알림 발송"""
        results = {}
        
        for message in messages:
            message_results = await self.send_notification(message)
            results[message.id] = message_results
        
        return results
    
    async def schedule_notification(self, message: NotificationMessage, scheduled_time: datetime):
        """알림 예약"""
        try:
            message.scheduled_time = scheduled_time
            
            if self.redis_client:
                # 예약 알림을 Redis에 저장
                schedule_data = asdict(message)
                await self.redis_client.zadd(
                    'scheduled_notifications',
                    {json.dumps(schedule_data, default=str): scheduled_time.timestamp()}
                )
            
            logger.info(f"알림 예약 완료: {message.id} at {scheduled_time}")
            
        except Exception as e:
            logger.error(f"알림 예약 실패: {e}")
            raise
    
    async def process_scheduled_notifications(self):
        """예약된 알림 처리"""
        try:
            if not self.redis_client:
                return
            
            now = time.time()
            
            # 현재 시간보다 과거의 예약 알림 조회
            scheduled = await self.redis_client.zrangebyscore(
                'scheduled_notifications', 0, now, withscores=True
            )
            
            for notification_json, score in scheduled:
                try:
                    notification_data = json.loads(notification_json)
                    message = NotificationMessage(**notification_data)
                    
                    # 알림 발송
                    await self.send_notification(message)
                    
                    # 처리된 알림 제거
                    await self.redis_client.zrem('scheduled_notifications', notification_json)
                    
                    logger.info(f"예약 알림 발송 완료: {message.id}")
                    
                except Exception as e:
                    logger.error(f"예약 알림 처리 실패: {e}")
        
        except Exception as e:
            logger.error(f"예약 알림 처리 실패: {e}")
    
    async def get_notification_stats(self) -> Dict[str, Any]:
        """알림 통계 조회"""
        try:
            stats = {
                'total_users': len(self.users),
                'active_channels': len(self.channels),
                'channel_stats': {},
                'recent_notifications': 0
            }
            
            # 채널별 통계
            for channel_name in self.channels.keys():
                enabled_users = len([
                    user for user in self.users.values() 
                    if channel_name in user.enabled_channels
                ])
                stats['channel_stats'][channel_name] = {
                    'enabled_users': enabled_users,
                    'total_users': len(self.users)
                }
            
            # 최근 24시간 알림 수
            if self.redis_client:
                logs = await self.redis_client.lrange('notification_logs', 0, 99)
                recent_count = 0
                cutoff = datetime.now() - timedelta(days=1)
                
                for log_json in logs:
                    try:
                        log_data = json.loads(log_json)
                        sent_at = datetime.fromisoformat(log_data.get('sent_at', ''))
                        if sent_at > cutoff:
                            recent_count += 1
                    except:
                        continue
                
                stats['recent_notifications'] = recent_count
            
            return stats
            
        except Exception as e:
            logger.error(f"통계 조회 실패: {e}")
            return {}

async def main():
    """메인 실행 함수"""
    try:
        # 설정 디렉토리 생성
        os.makedirs('/app/config', exist_ok=True)
        os.makedirs('/app/logs', exist_ok=True)
        
        # 알림 서비스 초기화
        notification_service = NotificationService()
        await notification_service.initialize()
        
        # 테스트 사용자 등록
        test_user = NotificationUser(
            user_id="test_user_1",
            name="테스트 사용자",
            email="test@stockpilot.ai",
            telegram_chat_id="123456789",
            enabled_channels=['email', 'telegram'],
            preferences={
                'trade_signals': True,
                'price_alerts': True,
                'system_alerts': False
            }
        )
        await notification_service.register_user(test_user)
        
        # 테스트 알림 발송
        test_message = NotificationMessage(
            id="test_001",
            type=NotificationType.TRADE_SIGNAL,
            priority=NotificationPriority.HIGH,
            title="테스트 투자 신호",
            message="삼성전자 매수 신호가 감지되었습니다.",
            data={
                "종목": "삼성전자",
                "현재가": "75,000원",
                "신호": "매수",
                "신뢰도": "85%"
            }
        )
        
        results = await notification_service.send_notification(test_message)
        logger.info(f"테스트 알림 발송 결과: {results}")
        
        # 예약된 알림 처리 루프 (실제 환경에서는 별도 스케줄러 사용)
        while True:
            await notification_service.process_scheduled_notifications()
            await asyncio.sleep(60)  # 1분마다 체크
        
    except Exception as e:
        logger.error(f"알림 서비스 실행 실패: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())