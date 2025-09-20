"""
MCP-MAP Company Notification System
심각도별 알림 시스템 - Slack, Discord, Email 채널 지원
"""

import os
import asyncio
import aiohttp
import smtplib
import logging
import json
import time
from datetime import datetime
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from typing import Optional, Dict, Any, List
from enum import Enum
from pathlib import Path
from jinja2 import Template, Environment, BaseLoader
from collections import defaultdict

logger = logging.getLogger(__name__)

# 알림 전송 속도 제한을 위한 글로벌 딕셔너리
_last_notification_times = defaultdict(lambda: defaultdict(float))

# 알림 레벨별 지연 시간 (초)
NOTIFICATION_DELAYS = {
    NotificationLevel.CRITICAL: 0,    # 즉시 전송
    NotificationLevel.ERROR: 1,       # 1초 지연
    NotificationLevel.WARNING: 3,     # 3초 지연
    NotificationLevel.INFO: 5         # 5초 지연
}

# Jinja2 템플릿 환경
template_env = Environment(loader=BaseLoader())

# 메시지 템플릿들
SLACK_TEMPLATES = {
    'basic': '''
{
    "username": "MCP-MAP Company Bot",
    "attachments": [{
        "color": "{{ color }}",
        "title": "{{ emoji }} {{ title }}",
        "text": "{{ message }}",
        "timestamp": {{ timestamp }},
        "footer": "MCP-MAP Company Monitoring",
        "fields": [
            {%- for key, value in fields.items() %}
            {
                "title": "{{ key }}",
                "value": "{{ value }}",
                "short": true
            }{% if not loop.last %},{% endif %}
            {%- endfor %}
        ]
    }]
}
''',
    'with_logs': '''
{
    "username": "MCP-MAP Company Bot",
    "attachments": [
        {
            "color": "{{ color }}",
            "title": "{{ emoji }} {{ title }}",
            "text": "{{ message }}",
            "timestamp": {{ timestamp }},
            "footer": "MCP-MAP Company Monitoring",
            "fields": [
                {%- for key, value in fields.items() %}
                {
                    "title": "{{ key }}",
                    "value": "{{ value }}",
                    "short": true
                }{% if not loop.last %},{% endif %}
                {%- endfor %}
            ]
        },
        {
            "color": "{{ log_color }}",
            "title": "{{ log_title }}",
            "text": "```\n{{ logs }}\n```",
            "footer": "{{ log_footer }}"
        }
    ]
}
'''
}

DISCORD_TEMPLATES = {
    'basic': '''
{
    "username": "MCP-MAP Company Bot",
    "avatar_url": "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f916.png",
    "embeds": [{
        "title": "{{ emoji }} {{ title }}",
        "description": "{{ message }}",
        "color": {{ color }},
        "fields": [
            {%- for key, value in fields.items() %}
            {
                "name": "{{ key }}",
                "value": "{{ value }}",
                "inline": true
            }{% if not loop.last %},{% endif %}
            {%- endfor %}
            {% if fields %},{% endif %}
            {
                "name": "시간",
                "value": "{{ formatted_time }}",
                "inline": true
            }
        ],
        "footer": {
            "text": "MCP-MAP Company Monitoring System"
        },
        "timestamp": "{{ iso_timestamp }}"
    }]
}
''',
    'with_logs': '''
{
    "username": "MCP-MAP Company Bot",
    "avatar_url": "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f916.png",
    "embeds": [
        {
            "title": "{{ emoji }} {{ title }}",
            "description": "{{ message }}",
            "color": {{ color }},
            "fields": [
                {%- for key, value in fields.items() %}
                {
                    "name": "{{ key }}",
                    "value": "{{ value }}",
                    "inline": true
                }{% if not loop.last %},{% endif %}
                {%- endfor %}
                {% if fields %},{% endif %}
                {
                    "name": "시간",
                    "value": "{{ formatted_time }}",
                    "inline": true
                }
            ],
            "footer": {
                "text": "MCP-MAP Company Monitoring System"
            },
            "timestamp": "{{ iso_timestamp }}"
        },
        {
            "title": "{{ log_title }}",
            "description": "```\n{{ logs }}\n```",
            "color": {{ log_color }},
            "footer": {
                "text": "{{ log_footer }}"
            }
        }
    ]
}
'''
}

EMAIL_HTML_TEMPLATE = '''
<html>
<body style="font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f9f9f9;">
    <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <div style="background: {{ bg_color }}; border-left: 4px solid {{ border_color }}; padding: 20px;">
            <h2 style="margin: 0; color: {{ border_color }};">{{ emoji }} MCP-MAP Company 알림</h2>
            <p style="margin: 5px 0 0 0; color: #666;">심각도: {{ level.upper() }}</p>
        </div>
        <div style="padding: 20px;">
            <p style="font-size: 16px; line-height: 1.5; color: #333;">{{ message }}</p>
            {% if fields %}
            <h3>추가 정보:</h3>
            <ul>
                {%- for key, value in fields.items() %}
                <li><strong>{{ key }}:</strong> {{ value }}</li>
                {%- endfor %}
            </ul>
            {% endif %}
            {% if logs %}
            <div style="margin: 20px 0; padding: 15px; background: {{ log_bg }}; border-left: 4px solid {{ log_border }}; border-radius: 4px;">
                <h3 style="margin-top: 0; color: {{ log_border }};">{{ log_title }}</h3>
                <pre style="background: #ffffff; padding: 10px; border-radius: 4px; overflow-x: auto; font-size: 12px; max-height: {{ log_height }}px; overflow-y: auto;">{{ logs }}</pre>
                <p style="font-size: 11px; color: #666; margin-bottom: 0;">{{ log_footer }}</p>
            </div>
            {% endif %}
            <hr style="margin: 20px 0; border: none; border-top: 1px solid #eee;">
            <p style="color: #999; font-size: 12px;">
                전송 시간: {{ formatted_time }}<br>
                발신: MCP-MAP Company 모니터링 시스템
            </p>
        </div>
    </div>
</body>
</html>
'''

EMAIL_TEXT_TEMPLATE = '''
MCP-MAP COMPANY 알림 - {{ level.upper() }}
{{ "=" * 50 }}

{{ message }}

{% if fields %}
추가 정보:
{%- for key, value in fields.items() %}
• {{ key }}: {{ value }}
{%- endfor %}

{% endif %}
{% if logs %}
{{ log_title }}:
{{ "-" * 60 }}
{{ logs }}
{{ "-" * 60 }}
{{ log_footer }}

{% endif %}
전송 시간: {{ formatted_time }}
발신: MCP-MAP Company 모니터링 시스템
'''

def setup_logging():
    """JSON과 텍스트 로그 동시 기록을 위한 로거 설정"""
    # logs 디렉토리 생성
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # JSON 로거 설정
    json_logger = logging.getLogger('notification_json')
    json_logger.setLevel(logging.INFO)
    json_handler = logging.FileHandler(log_dir / 'notifications.json')
    json_handler.setFormatter(logging.Formatter('%(message)s'))
    json_logger.addHandler(json_handler)

    # 텍스트 로거 설정
    text_logger = logging.getLogger('notification_text')
    text_logger.setLevel(logging.INFO)
    text_handler = logging.FileHandler(log_dir / 'notifications.log')
    text_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    text_logger.addHandler(text_handler)

    return json_logger, text_logger

# 로거 초기화
json_logger, text_logger = setup_logging()

def log_notification(level: str, message: str, channel: str, success: bool, **kwargs):
    """알림을 JSON과 텍스트 형식으로 동시 기록"""
    timestamp = datetime.now().isoformat()

    # JSON 로그 기록
    json_log = {
        "timestamp": timestamp,
        "level": level,
        "message": message,
        "channel": channel,
        "success": success,
        "metadata": kwargs
    }
    json_logger.info(json.dumps(json_log, ensure_ascii=False))

    # 텍스트 로그 기록
    status = "SUCCESS" if success else "FAILED"
    text_log = f"{level.upper()} notification via {channel.upper()}: {status} - {message}"
    if kwargs:
        text_log += f" | Metadata: {kwargs}"
    text_logger.info(text_log)

async def apply_notification_delay(level: NotificationLevel, channel: str):
    """알림 레벨별 전송 속도 제한 적용"""
    delay = NOTIFICATION_DELAYS.get(level, 0)

    if delay > 0:
        current_time = time.time()
        last_time = _last_notification_times[channel][level.value]

        if current_time - last_time < delay:
            sleep_time = delay - (current_time - last_time)
            logger.info(f"{channel} {level.value} 알림 속도 제한: {sleep_time:.1f}초 대기")
            await asyncio.sleep(sleep_time)

        _last_notification_times[channel][level.value] = time.time()

class NotificationLevel(Enum):
    """알림 심각도 레벨"""
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

class NotificationChannel(Enum):
    """지원되는 알림 채널"""
    SLACK = "slack"
    DISCORD = "discord"
    EMAIL = "email"

def get_recent_logs(log_file_path: str = "logs/app.log", lines: int = 50) -> str:
    """
    최근 로그 라인을 가져옵니다.

    Args:
        log_file_path: 로그 파일 경로
        lines: 가져올 라인 수

    Returns:
        최근 로그 내용
    """
    try:
        # 여러 가능한 로그 파일 경로 시도
        possible_paths = [
            Path(log_file_path),
            Path("logs/app.log"),
            Path("logs/api.log"),
            Path("logs/scheduler.log"),
            Path("../logs/app.log")
        ]

        for path in possible_paths:
            if path.exists() and path.is_file():
                with open(path, 'r', encoding='utf-8') as f:
                    all_lines = f.readlines()
                    recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                    return ''.join(recent_lines).strip()

        return f"로그 파일을 찾을 수 없습니다. 확인된 경로: {[str(p) for p in possible_paths]}"

    except Exception as e:
        logger.error(f"로그 파일 읽기 오류: {e}")
        return f"로그 파일 읽기 오류: {str(e)}"

class SlackNotifier:
    """Slack 웹훅 알림 처리기"""

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv('SLACK_WEBHOOK_URL')
        self.enabled = bool(self.webhook_url)

    async def send_notification(
        self,
        message: str,
        level: NotificationLevel,
        title: Optional[str] = None,
        fields: Optional[Dict[str, Any]] = None,
        attach_logs: bool = False
    ) -> bool:
        """Slack 채널로 알림 전송 (템플릿 기반, 속도 제한 적용)"""
        if not self.enabled:
            logger.warning("Slack 알림이 비활성화됨 - 웹훅 URL 미설정")
            log_notification(level.value, message, "slack", False, reason="disabled")
            return False

        try:
            # 전송 속도 제한 적용
            await apply_notification_delay(level, "slack")

            # 심각도별 색상 및 이모지 설정
            level_config = {
                NotificationLevel.CRITICAL: {"color": "#d63031", "emoji": "🚨"},
                NotificationLevel.ERROR: {"color": "#ff6b6b", "emoji": "❌"},
                NotificationLevel.WARNING: {"color": "#fdcb6e", "emoji": "⚠️"},
                NotificationLevel.INFO: {"color": "#74b9ff", "emoji": "ℹ️"}
            }

            config = level_config.get(level, level_config[NotificationLevel.INFO])
            fields = fields or {}

            # 템플릿 데이터 준비
            template_data = {
                "color": config["color"],
                "emoji": config["emoji"],
                "title": title or f'MCP-MAP {level.value.upper()} 알림',
                "message": message,
                "timestamp": int(datetime.now().timestamp()),
                "fields": fields
            }

            # 로그 첨부 처리
            recent_logs = None
            if attach_logs:
                if level == NotificationLevel.CRITICAL:
                    recent_logs = get_recent_logs(lines=50)
                    if recent_logs and len(recent_logs) > 100:
                        max_log_length = 2000
                        if len(recent_logs) > max_log_length:
                            recent_logs = recent_logs[-max_log_length:] + "\n... (truncated)"
                        template_data.update({
                            "logs": recent_logs,
                            "log_color": "#ff0000",
                            "log_title": "📋 긴급 상황 로그 (최근 50줄)",
                            "log_footer": "Critical 알림에 자동 첨부됨"
                        })

                elif level == NotificationLevel.ERROR:
                    recent_logs = get_recent_logs(lines=20)
                    if recent_logs and len(recent_logs) > 50:
                        max_log_length = 1500
                        if len(recent_logs) > max_log_length:
                            recent_logs = recent_logs[-max_log_length:] + "\n... (truncated)"
                        template_data.update({
                            "logs": recent_logs,
                            "log_color": "#ff6b6b",
                            "log_title": "📋 오류 로그 (최근 20줄)",
                            "log_footer": "Error 알림에 자동 첨부됨"
                        })

                elif level == NotificationLevel.WARNING:
                    recent_logs = get_recent_logs(lines=10)
                    if recent_logs:
                        log_lines = recent_logs.split('\n')
                        summary = f"최근 로그 상태: {len(log_lines)}줄 확인됨 (최신 10줄 요약)"
                        template_data["fields"]["📝 로그 요약"] = summary

            # 템플릿 선택 및 렌더링
            template_name = 'with_logs' if recent_logs and level in [NotificationLevel.CRITICAL, NotificationLevel.ERROR] else 'basic'
            template = template_env.from_string(SLACK_TEMPLATES[template_name])
            payload_json = template.render(**template_data)
            payload = json.loads(payload_json)

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.info("Slack 알림 전송 성공")
                        log_notification(level.value, message, "slack", True, title=title, has_logs=bool(recent_logs))
                        return True
                    else:
                        logger.error(f"Slack 알림 전송 실패: {response.status}")
                        log_notification(level.value, message, "slack", False,
                                       reason=f"http_{response.status}", title=title)
                        return False

        except Exception as e:
            logger.error(f"Slack 알림 전송 오류: {e}")
            log_notification(level.value, message, "slack", False, reason=str(e), title=title)
            return False

class DiscordNotifier:
    """Discord 웹훅 알림 처리기"""

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv('DISCORD_WEBHOOK_URL')
        self.enabled = bool(self.webhook_url)

    async def send_notification(
        self,
        message: str,
        level: NotificationLevel,
        title: Optional[str] = None,
        fields: Optional[Dict[str, Any]] = None,
        attach_logs: bool = False
    ) -> bool:
        """Discord 채널로 알림 전송 (템플릿 기반, 속도 제한 적용)"""
        if not self.enabled:
            logger.warning("Discord 알림이 비활성화됨 - 웹훅 URL 미설정")
            log_notification(level.value, message, "discord", False, reason="disabled")
            return False

        try:
            # 전송 속도 제한 적용
            await apply_notification_delay(level, "discord")

            # 심각도별 색상 및 이모지 설정 (Discord용 정수 색상)
            level_config = {
                NotificationLevel.CRITICAL: {"color": 13382451, "emoji": "🚨"},
                NotificationLevel.ERROR: {"color": 16744272, "emoji": "❌"},
                NotificationLevel.WARNING: {"color": 16632814, "emoji": "⚠️"},
                NotificationLevel.INFO: {"color": 7649023, "emoji": "ℹ️"}
            }

            config = level_config.get(level, level_config[NotificationLevel.INFO])
            fields = fields or {}

            # 템플릿 데이터 준비
            template_data = {
                "color": config["color"],
                "emoji": config["emoji"],
                "title": title or f'MCP-MAP {level.value.upper()} 알림',
                "message": message,
                "formatted_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "iso_timestamp": datetime.now().isoformat(),
                "fields": fields
            }

            # 로그 첨부 처리
            recent_logs = None
            if attach_logs:
                if level == NotificationLevel.CRITICAL:
                    recent_logs = get_recent_logs(lines=50)
                    if recent_logs and len(recent_logs) > 100:
                        max_log_length = 1900
                        if len(recent_logs) > max_log_length:
                            recent_logs = recent_logs[-max_log_length:] + "\n... (truncated)"
                        template_data.update({
                            "logs": recent_logs,
                            "log_color": 13382451,
                            "log_title": "📋 긴급 상황 로그",
                            "log_footer": "최근 50줄 로그 - Critical 알림에 자동 첨부됨"
                        })

                elif level == NotificationLevel.ERROR:
                    recent_logs = get_recent_logs(lines=20)
                    if recent_logs and len(recent_logs) > 50:
                        max_log_length = 1400
                        if len(recent_logs) > max_log_length:
                            recent_logs = recent_logs[-max_log_length:] + "\n... (truncated)"
                        template_data.update({
                            "logs": recent_logs,
                            "log_color": 16744272,
                            "log_title": "📋 오류 로그",
                            "log_footer": "최근 20줄 로그 - Error 알림에 자동 첨부됨"
                        })

                elif level in [NotificationLevel.WARNING, NotificationLevel.INFO]:
                    recent_logs = get_recent_logs(lines=10)
                    if recent_logs:
                        log_lines = recent_logs.split('\n')
                        summary = f"최근 로그 상태: {len(log_lines)}줄 확인됨"
                        template_data["fields"]["📝 로그 요약"] = summary

            # 템플릿 선택 및 렌더링
            template_name = 'with_logs' if recent_logs and level in [NotificationLevel.CRITICAL, NotificationLevel.ERROR] else 'basic'
            template = template_env.from_string(DISCORD_TEMPLATES[template_name])
            payload_json = template.render(**template_data)
            payload = json.loads(payload_json)

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 204:  # Discord는 성공 시 204 반환
                        logger.info("Discord 알림 전송 성공")
                        log_notification(level.value, message, "discord", True, title=title, has_logs=bool(recent_logs))
                        return True
                    else:
                        logger.error(f"Discord 알림 전송 실패: {response.status}")
                        log_notification(level.value, message, "discord", False,
                                       reason=f"http_{response.status}", title=title)
                        return False

        except Exception as e:
            logger.error(f"Discord 알림 전송 오류: {e}")
            log_notification(level.value, message, "discord", False, reason=str(e), title=title)
            return False

class EmailNotifier:
    """SMTP 이메일 알림 처리기"""

    def __init__(
        self,
        smtp_server: Optional[str] = None,
        smtp_port: Optional[int] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
        recipients: Optional[List[str]] = None
    ):
        self.smtp_server = smtp_server or os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = smtp_port or int(os.getenv('SMTP_PORT', '587'))
        self.email = email or os.getenv('NOTIFY_EMAIL')
        self.password = password or os.getenv('NOTIFY_PASSWORD')

        # 수신자 목록 처리
        if recipients:
            self.recipients = recipients
        else:
            recipients_str = os.getenv('NOTIFY_RECIPIENTS', self.email)
            self.recipients = [email.strip() for email in recipients_str.split(',')] if recipients_str else []

        self.enabled = bool(self.email and self.password and self.recipients)

    async def send_notification(
        self,
        message: str,
        level: NotificationLevel,
        title: Optional[str] = None,
        fields: Optional[Dict[str, Any]] = None,
        attach_logs: bool = False
    ) -> bool:
        """이메일 알림 전송 (템플릿 기반, 속도 제한 적용)"""
        if not self.enabled:
            logger.warning("이메일 알림이 비활성화됨 - 설정 누락")
            log_notification(level.value, message, "email", False, reason="disabled")
            return False

        try:
            # 전송 속도 제한 적용
            await apply_notification_delay(level, "email")

            # 메시지 생성
            msg = MimeMultipart('alternative')
            msg['Subject'] = title or f'MCP-MAP {level.value.upper()} 알림'
            msg['From'] = self.email
            msg['To'] = ', '.join(self.recipients)

            # 로그 내용 가져오기 (심각도별)
            recent_logs = None
            if attach_logs:
                if level == NotificationLevel.CRITICAL:
                    recent_logs = get_recent_logs(lines=50)
                elif level == NotificationLevel.ERROR:
                    recent_logs = get_recent_logs(lines=20)
                elif level in [NotificationLevel.WARNING, NotificationLevel.INFO]:
                    recent_logs = get_recent_logs(lines=10)

            # 템플릿 데이터 준비
            template_data = self._prepare_template_data(message, level, title, fields, recent_logs)

            # HTML 및 텍스트 컨텐츠 생성 (템플릿 기반)
            html_template = template_env.from_string(EMAIL_HTML_TEMPLATE)
            text_template = template_env.from_string(EMAIL_TEXT_TEMPLATE)

            html_content = html_template.render(**template_data)
            text_content = text_template.render(**template_data)

            html_part = MimeText(html_content, 'html')
            text_part = MimeText(text_content, 'plain')

            msg.attach(text_part)
            msg.attach(html_part)

            # 이메일 전송 (동기 함수를 비동기로 실행)
            await asyncio.get_event_loop().run_in_executor(
                None, self._send_email_sync, msg
            )

            logger.info(f"이메일 알림 전송 성공 ({len(self.recipients)}명)")
            log_notification(level.value, message, "email", True,
                           recipients=len(self.recipients), title=title, has_logs=bool(recent_logs))
            return True

        except Exception as e:
            logger.error(f"이메일 알림 전송 오류: {e}")
            log_notification(level.value, message, "email", False, reason=str(e), title=title)
            return False

    def _send_email_sync(self, msg: MimeMultipart):
        """동기식 이메일 전송"""
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.email, self.password)
            server.send_message(msg)

    def _prepare_template_data(self, message: str, level: NotificationLevel, title: Optional[str] = None,
                              fields: Optional[Dict] = None, recent_logs: Optional[str] = None) -> Dict:
        """이메일 템플릿 데이터 준비"""
        level_config = {
            NotificationLevel.CRITICAL: {
                "bg_color": "#ffebee", "border_color": "#d32f2f", "emoji": "🚨",
                "log_bg": "#ffebee", "log_border": "#d32f2f", "log_title": "📋 긴급 상황 로그 (최근 50줄)",
                "log_footer": "Critical 알림에 자동 첨부됨", "log_height": 400
            },
            NotificationLevel.ERROR: {
                "bg_color": "#fff3e0", "border_color": "#f57c00", "emoji": "❌",
                "log_bg": "#fff3e0", "log_border": "#f57c00", "log_title": "📋 오류 로그 (최근 20줄)",
                "log_footer": "Error 알림에 자동 첨부됨", "log_height": 300
            },
            NotificationLevel.WARNING: {
                "bg_color": "#fffde7", "border_color": "#fbc02d", "emoji": "⚠️",
                "log_bg": "#f1f8ff", "log_border": "#1976d2", "log_title": "📝 로그 상태 요약",
                "log_footer": "Warning 로그 요약", "log_height": 200
            },
            NotificationLevel.INFO: {
                "bg_color": "#e3f2fd", "border_color": "#1976d2", "emoji": "ℹ️",
                "log_bg": "#f1f8ff", "log_border": "#1976d2", "log_title": "📝 로그 상태 요약",
                "log_footer": "Info 로그 요약", "log_height": 200
            }
        }

        config = level_config.get(level, level_config[NotificationLevel.INFO])

        template_data = {
            "message": message,
            "level": level.value,
            "title": title or f'MCP-MAP {level.value.upper()} 알림',
            "fields": fields or {},
            "formatted_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "logs": None,
            **config
        }

        # 로그 처리
        if recent_logs:
            if level == NotificationLevel.CRITICAL and len(recent_logs) > 100:
                template_data["logs"] = recent_logs
            elif level == NotificationLevel.ERROR and len(recent_logs) > 50:
                template_data["logs"] = recent_logs
            elif level in [NotificationLevel.WARNING, NotificationLevel.INFO]:
                log_lines = recent_logs.split('\n')
                template_data["logs"] = f"최근 로그 상태: {len(log_lines)}줄 확인됨 (최신 10줄 요약)"
                template_data["log_title"] = "📝 로그 상태 요약"

        return template_data


class NotificationManager:
    """통합 알림 관리자"""

    def __init__(self):
        self.slack = SlackNotifier()
        self.discord = DiscordNotifier()
        self.email = EmailNotifier()

        self.enabled_channels = []
        if self.slack.enabled:
            self.enabled_channels.append(NotificationChannel.SLACK)
        if self.discord.enabled:
            self.enabled_channels.append(NotificationChannel.DISCORD)
        if self.email.enabled:
            self.enabled_channels.append(NotificationChannel.EMAIL)

        logger.info(f"알림 관리자 초기화 완료. 활성 채널: {[ch.value for ch in self.enabled_channels]}")

    async def send_notification(
        self,
        message: str,
        level: NotificationLevel,
        title: Optional[str] = None,
        fields: Optional[Dict[str, Any]] = None,
        channels: Optional[List[NotificationChannel]] = None,
        attach_logs: bool = True
    ) -> Dict[str, bool]:
        """지정된 채널로 알림 전송"""

        if not self.enabled_channels:
            logger.warning("활성화된 알림 채널이 없습니다")
            return {}

        # 대상 채널 결정
        target_channels = channels or self.enabled_channels
        results = {}

        # 동시 전송을 위한 태스크 생성
        tasks = []

        for channel in target_channels:
            if channel == NotificationChannel.SLACK and self.slack.enabled:
                tasks.append(
                    (channel.value, self.slack.send_notification(message, level, title, fields, attach_logs))
                )
            elif channel == NotificationChannel.DISCORD and self.discord.enabled:
                tasks.append(
                    (channel.value, self.discord.send_notification(message, level, title, fields, attach_logs))
                )
            elif channel == NotificationChannel.EMAIL and self.email.enabled:
                tasks.append(
                    (channel.value, self.email.send_notification(message, level, title, fields, attach_logs))
                )

        # 모든 알림 전송 대기
        if tasks:
            for channel_name, task in tasks:
                try:
                    results[channel_name] = await task
                except Exception as e:
                    logger.error(f"{channel_name} 알림 전송 오류: {e}")
                    results[channel_name] = False

        return results

    async def send_critical(self, message: str, **kwargs):
        """긴급 알림 전송 (로그 50줄 자동 첨부)"""
        return await self.send_notification(
            message=message,
            level=NotificationLevel.CRITICAL,
            title="🚨 긴급 상황 발생",
            **kwargs
        )

    async def send_error(self, message: str, **kwargs):
        """오류 알림 전송 (로그 20줄 자동 첨부)"""
        return await self.send_notification(
            message=message,
            level=NotificationLevel.ERROR,
            title="❌ 시스템 오류 발생",
            **kwargs
        )

    async def send_warning(self, message: str, **kwargs):
        """경고 알림 전송 (로그 요약)"""
        return await self.send_notification(
            message=message,
            level=NotificationLevel.WARNING,
            title="⚠️ 주의 사항",
            **kwargs
        )

    async def send_info(self, message: str, **kwargs):
        """정보 알림 전송 (단순 메시지)"""
        return await self.send_notification(
            message=message,
            level=NotificationLevel.INFO,
            **kwargs
        )

# 전역 알림 관리자 인스턴스
notification_manager = NotificationManager()

# 편의 함수들
async def send_critical(message: str, **kwargs):
    """긴급 알림 전송"""
    return await notification_manager.send_critical(message, **kwargs)

async def send_error(message: str, **kwargs):
    """오류 알림 전송"""
    return await notification_manager.send_error(message, **kwargs)

async def send_warning(message: str, **kwargs):
    """경고 알림 전송"""
    return await notification_manager.send_warning(message, **kwargs)

async def send_info(message: str, **kwargs):
    """정보 알림 전송"""
    return await notification_manager.send_info(message, **kwargs)

async def test_notifications():
    """알림 시스템 테스트"""
    print("MCP-MAP Company 알림 시스템 테스트 시작...")
    print(f"활성 채널: {[ch.value for ch in notification_manager.enabled_channels]}")

    # 각 심각도별 테스트
    test_results = {}

    # Info 테스트
    test_results['info'] = await send_info(
        "알림 시스템 테스트 - Info 레벨",
        title="📢 시스템 테스트",
        fields={
            "테스트 유형": "Info Level",
            "시스템": "MCP-MAP Company",
            "상태": "정상"
        }
    )

    # Warning 테스트
    test_results['warning'] = await send_warning(
        "알림 시스템 테스트 - Warning 레벨",
        fields={
            "테스트 유형": "Warning Level",
            "디스크 사용률": "85%",
            "권장 조치": "로그 파일 정리"
        }
    )

    # Error 테스트
    test_results['error'] = await send_error(
        "알림 시스템 테스트 - Error 레벨",
        fields={
            "테스트 유형": "Error Level",
            "오류 코드": "TEST_ERROR_001",
            "영향 범위": "테스트 환경"
        }
    )

    # Critical 테스트
    test_results['critical'] = await send_critical(
        "알림 시스템 테스트 - Critical 레벨",
        fields={
            "테스트 유형": "Critical Level",
            "긴급도": "최고",
            "대응 필요": "즉시"
        }
    )

    print(f"알림 테스트 결과: {test_results}")
    return test_results

if __name__ == "__main__":
    # 테스트 실행
    asyncio.run(test_notifications())