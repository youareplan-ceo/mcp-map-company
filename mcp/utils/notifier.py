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
import random
from datetime import datetime, timedelta
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

# 재시도 설정
MAX_RETRY_ATTEMPTS = 3  # 최대 재시도 횟수
RETRY_BASE_DELAY = 1    # 기본 지연 시간 (초)

# NotificationLevel enum 정의를 위해 이동
class NotificationLevel(Enum):
    """알림 심각도 레벨"""
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

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

    # 알림 전용 로거 설정 (성공/실패 내역 기록)
    notifier_logger = logging.getLogger('notifier_status')
    notifier_logger.setLevel(logging.INFO)
    notifier_handler = logging.FileHandler(log_dir / 'notifier.log')
    notifier_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    notifier_logger.addHandler(notifier_handler)

    return json_logger, text_logger, notifier_logger

# 로거 초기화
json_logger, text_logger, notifier_logger = setup_logging()

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

async def retry_with_backoff(func, *args, **kwargs):
    """
    지수 백오프를 사용한 재시도 함수

    Args:
        func: 실행할 비동기 함수
        *args: 함수에 전달할 인수
        **kwargs: 함수에 전달할 키워드 인수

    Returns:
        함수 실행 결과 또는 False (모든 재시도 실패 시)
    """
    last_exception = None

    for attempt in range(MAX_RETRY_ATTEMPTS):
        try:
            result = await func(*args, **kwargs)
            if result:  # 성공한 경우
                if attempt > 0:  # 재시도를 통해 성공한 경우
                    notifier_logger.info(f"재시도 성공: {attempt + 1}회 시도 후 성공")
                return result
            else:
                # 함수가 False를 반환한 경우 (실패)
                raise Exception("Function returned False")

        except Exception as e:
            last_exception = e

            if attempt < MAX_RETRY_ATTEMPTS - 1:  # 마지막 시도가 아닌 경우
                delay = RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(0, 1)  # 지수 백오프 + 지터
                notifier_logger.warning(f"알림 전송 실패 (시도 {attempt + 1}/{MAX_RETRY_ATTEMPTS}): {str(e)}, {delay:.2f}초 후 재시도")
                await asyncio.sleep(delay)
            else:
                # 모든 재시도 실패
                notifier_logger.error(f"모든 재시도 실패 ({MAX_RETRY_ATTEMPTS}회): 최종 오류 - {str(e)}")

    return False

def get_log_links(level: NotificationLevel) -> Dict[str, str]:
    """
    심각도에 따른 관련 로그 파일 링크 생성

    Args:
        level: 알림 심각도 레벨

    Returns:
        로그 파일명과 링크가 포함된 딕셔너리
    """
    base_url = os.getenv('LOG_BASE_URL', 'http://localhost:8088/logs')  # 환경변수에서 로그 베이스 URL 가져오기
    log_links = {}

    # 심각도별로 우선 확인할 로그 파일들 정의
    if level in [NotificationLevel.CRITICAL, NotificationLevel.ERROR]:
        # 심각한 오류의 경우 보안 로그와 API 로그 모두 제공
        log_links["보안 로그"] = f"{base_url}/security.log"
        log_links["API 로그"] = f"{base_url}/api.log"
        log_links["시스템 로그"] = f"{base_url}/app.log"
    elif level == NotificationLevel.WARNING:
        # 경고의 경우 API 로그와 시스템 로그
        log_links["API 로그"] = f"{base_url}/api.log"
        log_links["시스템 로그"] = f"{base_url}/app.log"
    else:  # INFO
        # 정보성 알림의 경우 시스템 로그만
        log_links["시스템 로그"] = f"{base_url}/app.log"

    return log_links

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
        """Slack 채널로 알림 전송 (재시도 기능, 로그 링크 포함)"""
        # 재시도 기능을 위한 내부 함수 정의
        async def _send_slack_notification():
            if not self.enabled:
                logger.warning("Slack 알림이 비활성화됨 - 웹훅 URL 미설정")
                notifier_logger.warning("Slack 알림 실패: 웹훅 URL 미설정")
                log_notification(level.value, message, "slack", False, reason="disabled")
                return False

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

            # 로그 링크 추가
            log_links = get_log_links(level)
            for log_name, log_url in log_links.items():
                fields[f"🔗 {log_name}"] = f"<{log_url}|로그 확인>"

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
                        notifier_logger.info(f"Slack 알림 전송 성공: {title or '제목없음'} - {level.value}")
                        log_notification(level.value, message, "slack", True, title=title, has_logs=bool(recent_logs))
                        return True
                    else:
                        error_msg = f"HTTP {response.status}"
                        logger.error(f"Slack 알림 전송 실패: {error_msg}")
                        notifier_logger.error(f"Slack 알림 전송 실패: {error_msg} - {title or '제목없음'}")
                        log_notification(level.value, message, "slack", False,
                                       reason=f"http_{response.status}", title=title)
                        return False

        # 재시도 기능을 사용하여 실제 알림 전송
        notifier_logger.info(f"Slack 알림 전송 시작: {title or '제목없음'} - {level.value}")
        result = await retry_with_backoff(_send_slack_notification)

        if result:
            notifier_logger.info(f"Slack 알림 최종 성공: {title or '제목없음'}")
        else:
            notifier_logger.error(f"Slack 알림 최종 실패: {title or '제목없음'}")

        return result

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
        """Discord 채널로 알림 전송 (재시도 기능, 로그 링크 포함)"""
        # 재시도 기능을 위한 내부 함수 정의
        async def _send_discord_notification():
            if not self.enabled:
                logger.warning("Discord 알림이 비활성화됨 - 웹훅 URL 미설정")
                notifier_logger.warning("Discord 알림 실패: 웹훅 URL 미설정")
                log_notification(level.value, message, "discord", False, reason="disabled")
                return False

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

            # 로그 링크 추가
            log_links = get_log_links(level)
            for log_name, log_url in log_links.items():
                fields[f"🔗 {log_name}"] = f"[로그 확인]({log_url})"

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
                        notifier_logger.info(f"Discord 알림 전송 성공: {title or '제목없음'} - {level.value}")
                        log_notification(level.value, message, "discord", True, title=title, has_logs=bool(recent_logs))
                        return True
                    else:
                        error_msg = f"HTTP {response.status}"
                        logger.error(f"Discord 알림 전송 실패: {error_msg}")
                        notifier_logger.error(f"Discord 알림 전송 실패: {error_msg} - {title or '제목없음'}")
                        log_notification(level.value, message, "discord", False,
                                       reason=f"http_{response.status}", title=title)
                        return False

        # 재시도 기능을 사용하여 실제 알림 전송
        notifier_logger.info(f"Discord 알림 전송 시작: {title or '제목없음'} - {level.value}")
        result = await retry_with_backoff(_send_discord_notification)

        if result:
            notifier_logger.info(f"Discord 알림 최종 성공: {title or '제목없음'}")
        else:
            notifier_logger.error(f"Discord 알림 최종 실패: {title or '제목없음'}")

        return result

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
        """이메일 알림 전송 (재시도 기능, 로그 링크 포함)"""
        # 재시도 기능을 위한 내부 함수 정의
        async def _send_email_notification():
            if not self.enabled:
                logger.warning("이메일 알림이 비활성화됨 - 설정 누락")
                notifier_logger.warning("이메일 알림 실패: 설정 누락")
                log_notification(level.value, message, "email", False, reason="disabled")
                return False

            # 전송 속도 제한 적용
            await apply_notification_delay(level, "email")

            # 메시지 생성
            msg = MimeMultipart('alternative')
            msg['Subject'] = title or f'MCP-MAP {level.value.upper()} 알림'
            msg['From'] = self.email
            msg['To'] = ', '.join(self.recipients)

            # 필드에 로그 링크 추가
            fields = fields or {}
            log_links = get_log_links(level)
            for log_name, log_url in log_links.items():
                fields[f"🔗 {log_name}"] = log_url

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
            notifier_logger.info(f"이메일 알림 전송 성공: {title or '제목없음'} - {level.value} ({len(self.recipients)}명)")
            log_notification(level.value, message, "email", True,
                           recipients=len(self.recipients), title=title, has_logs=bool(recent_logs))
            return True

        # 재시도 기능을 사용하여 실제 알림 전송
        notifier_logger.info(f"이메일 알림 전송 시작: {title or '제목없음'} - {level.value}")
        result = await retry_with_backoff(_send_email_notification)

        if result:
            notifier_logger.info(f"이메일 알림 최종 성공: {title or '제목없음'}")
        else:
            notifier_logger.error(f"이메일 알림 최종 실패: {title or '제목없음'}")

        return result

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

# ================================================
# Security-Specific Notification Functions
# ================================================

def get_security_logs(log_file_path: str = "logs/security.log", lines: int = 50) -> str:
    """
    보안 로그 파일에서 최근 로그를 가져옵니다.

    Args:
        log_file_path: 보안 로그 파일 경로
        lines: 가져올 라인 수

    Returns:
        최근 보안 로그 내용
    """
    try:
        # 여러 가능한 보안 로그 파일 경로 시도
        possible_paths = [
            Path(log_file_path),
            Path("logs/security.log"),
            Path("logs/rate_limit.log"),
            Path("../logs/security.log")
        ]

        for path in possible_paths:
            if path.exists() and path.is_file():
                with open(path, 'r', encoding='utf-8') as f:
                    all_lines = f.readlines()
                    recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                    return ''.join(recent_lines).strip()

        return f"보안 로그 파일을 찾을 수 없습니다. 확인된 경로: {[str(p) for p in possible_paths]}"

    except Exception as e:
        logger.error(f"보안 로그 파일 읽기 오류: {e}")
        return f"보안 로그 파일 읽기 오류: {str(e)}"

async def send_security_alert(
    event_type: str,
    client_ip: str,
    details: Dict[str, Any],
    level: NotificationLevel = NotificationLevel.CRITICAL
) -> Dict[str, bool]:
    """
    보안 이벤트 알림 전송

    Args:
        event_type: 보안 이벤트 유형 (예: 'IP_BLOCKED', 'RATE_LIMIT_EXCEEDED')
        client_ip: 관련 클라이언트 IP
        details: 추가 세부 정보
        level: 알림 심각도

    Returns:
        채널별 전송 결과
    """
    # 이벤트 유형별 메시지 템플릿
    event_messages = {
        'IP_BLOCKED': f"🚫 IP 주소 {client_ip}가 Rate Limit 초과로 차단되었습니다.",
        'RATE_LIMIT_EXCEEDED': f"⚠️ IP 주소 {client_ip}에서 요청 한도를 초과했습니다.",
        'WHITELIST_ADDED': f"✅ IP 주소 {client_ip}가 화이트리스트에 추가되었습니다.",
        'SECURITY_BREACH_ATTEMPT': f"🚨 IP 주소 {client_ip}에서 보안 침해 시도가 감지되었습니다.",
        'SUSPICIOUS_ACTIVITY': f"🔍 IP 주소 {client_ip}에서 의심스러운 활동이 감지되었습니다."
    }

    message = event_messages.get(event_type, f"🔒 보안 이벤트 감지: {event_type} (IP: {client_ip})")

    # 알림 제목 생성
    title = f"🔒 보안 알림: {event_type}"

    # 세부 정보 필드 준비
    security_fields = {
        "🌐 IP 주소": client_ip,
        "📅 발생 시간": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "🚨 이벤트 유형": event_type
    }

    # details의 내용을 필드에 추가
    for key, value in details.items():
        if isinstance(value, (str, int, float)):
            security_fields[f"📋 {key}"] = str(value)

    # 보안 로그 첨부 (Critical 및 Error 레벨의 경우)
    attach_security_logs = level in [NotificationLevel.CRITICAL, NotificationLevel.ERROR]

    return await notification_manager.send_notification(
        message=message,
        level=level,
        title=title,
        fields=security_fields,
        attach_logs=attach_security_logs
    )

async def send_ip_blocked_alert(client_ip: str, violation_count: int, endpoint: str, user_agent: str = "Unknown") -> Dict[str, bool]:
    """
    IP 차단 알림 전송

    Args:
        client_ip: 차단된 IP 주소
        violation_count: 위반 횟수
        endpoint: 요청된 엔드포인트
        user_agent: User-Agent 정보

    Returns:
        채널별 전송 결과
    """
    details = {
        "위반 횟수": violation_count,
        "요청 엔드포인트": endpoint,
        "User-Agent": user_agent[:100] + "..." if len(user_agent) > 100 else user_agent,
        "조치 사항": "자동 차단 적용됨"
    }

    return await send_security_alert(
        event_type="IP_BLOCKED",
        client_ip=client_ip,
        details=details,
        level=NotificationLevel.CRITICAL
    )

async def send_rate_limit_alert(client_ip: str, request_count: int, limit: int, endpoint: str) -> Dict[str, bool]:
    """
    Rate Limit 초과 알림 전송

    Args:
        client_ip: 요청 IP 주소
        request_count: 현재 요청 수
        limit: 허용된 요청 한도
        endpoint: 요청된 엔드포인트

    Returns:
        채널별 전송 결과
    """
    details = {
        "현재 요청 수": request_count,
        "허용 한도": limit,
        "초과율": f"{((request_count - limit) / limit * 100):.1f}%",
        "요청 엔드포인트": endpoint
    }

    return await send_security_alert(
        event_type="RATE_LIMIT_EXCEEDED",
        client_ip=client_ip,
        details=details,
        level=NotificationLevel.ERROR
    )

async def send_whitelist_update_alert(client_ip: str, action: str = "added") -> Dict[str, bool]:
    """
    화이트리스트 업데이트 알림 전송

    Args:
        client_ip: 화이트리스트에 추가/제거된 IP
        action: 수행된 작업 ("added" 또는 "removed")

    Returns:
        채널별 전송 결과
    """
    details = {
        "수행 작업": action,
        "관리자 조치": "수동 화이트리스트 관리",
        "영향": "해당 IP는 Rate Limit 제한에서 제외됨" if action == "added" else "해당 IP에 Rate Limit 적용됨"
    }

    event_type = "WHITELIST_ADDED" if action == "added" else "WHITELIST_REMOVED"

    return await send_security_alert(
        event_type=event_type,
        client_ip=client_ip,
        details=details,
        level=NotificationLevel.INFO
    )

async def send_security_summary_alert(blocked_count: int, violations_24h: int, new_ips: List[str]) -> Dict[str, bool]:
    """
    보안 요약 정보 알림 전송 (일일 리포트용)

    Args:
        blocked_count: 현재 차단된 IP 수
        violations_24h: 최근 24시간 위반 횟수
        new_ips: 새로 차단된 IP 목록

    Returns:
        채널별 전송 결과
    """
    message = f"📊 일일 보안 현황 요약이 도착했습니다."

    fields = {
        "🚫 현재 차단된 IP": f"{blocked_count}개",
        "⚠️ 24시간 위반 횟수": f"{violations_24h}회",
        "🆕 신규 차단 IP": f"{len(new_ips)}개",
        "🔍 신규 차단 목록": ", ".join(new_ips[:5]) + ("..." if len(new_ips) > 5 else "")
    }

    return await notification_manager.send_notification(
        message=message,
        level=NotificationLevel.INFO,
        title="📊 일일 보안 현황 요약",
        fields=fields,
        attach_logs=False
    )

# Override get_recent_logs to include security logs when appropriate
def get_recent_logs_with_security(log_file_path: str = "logs/app.log", lines: int = 50, include_security: bool = False) -> str:
    """
    일반 로그와 보안 로그를 함께 가져오는 확장 함수

    Args:
        log_file_path: 기본 로그 파일 경로
        lines: 가져올 라인 수
        include_security: 보안 로그 포함 여부

    Returns:
        통합된 로그 내용
    """
    # 기본 로그 가져오기
    main_logs = get_recent_logs(log_file_path, lines)

    if not include_security:
        return main_logs

    # 보안 로그 가져오기
    security_logs = get_security_logs(lines=lines//2)  # 보안 로그는 절반만

    if security_logs and "오류" not in security_logs:
        combined_logs = f"""=== 주요 시스템 로그 (최근 {lines}줄) ===
{main_logs}

=== 보안 로그 (최근 {lines//2}줄) ===
{security_logs}"""
        return combined_logs

    return main_logs

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

# ================================================
# 보안+백업 통합 알림 시스템 (Operations Integration)
# ================================================

import subprocess
import tempfile

async def send_backup_alert(
    script_name: str,
    execution_result: Dict[str, Any],
    level: NotificationLevel = NotificationLevel.INFO
) -> Dict[str, bool]:
    """
    백업 스크립트 실행 결과 알림 전송

    Args:
        script_name: 실행된 스크립트 이름 (backup_verifier.sh, cleanup_old_backups.sh 등)
        execution_result: 스크립트 실행 결과 (JSON 형태)
        level: 알림 심각도

    Returns:
        채널별 전송 결과
    """
    # 스크립트별 메시지 템플릿
    script_messages = {
        'backup_verifier.sh': "🔍 백업 검증이 완료되었습니다.",
        'cleanup_old_backups.sh': "🧹 백업 정리가 완료되었습니다.",
        'daily_ops.sh': "🔄 일일 운영 작업이 완료되었습니다."
    }

    message = script_messages.get(script_name, f"🔧 운영 스크립트 실행 완료: {script_name}")

    # 실행 결과에 따른 레벨 조정
    if execution_result.get('returncode', 0) != 0:
        level = NotificationLevel.ERROR
        message = f"❌ 운영 스크립트 실행 실패: {script_name}"
    elif execution_result.get('warnings', 0) > 0:
        level = NotificationLevel.WARNING
        message = f"⚠️ 운영 스크립트 경고 발생: {script_name}"

    # 알림 제목 생성
    title = f"🔧 운영 알림: {script_name}"

    # 세부 정보 필드 준비
    ops_fields = {
        "🛠️ 스크립트": script_name,
        "📅 실행 시간": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "📊 실행 결과": "성공" if execution_result.get('returncode', 0) == 0 else "실패"
    }

    # execution_result의 주요 정보를 필드에 추가
    if 'file' in execution_result:
        ops_fields["📦 백업 파일"] = execution_result['file']
    if 'size' in execution_result:
        ops_fields["📏 파일 크기"] = f"{execution_result['size']:,} bytes"
    if 'deleted_count' in execution_result:
        ops_fields["🗑️ 정리된 파일"] = f"{execution_result['deleted_count']}개"
    if 'total_size_bytes' in execution_result:
        ops_fields["💾 절약된 공간"] = f"{execution_result['total_size_bytes']:,} bytes"

    # JSON 원본 데이터 첨부 (Info 레벨 이상)
    if level in [NotificationLevel.WARNING, NotificationLevel.ERROR]:
        json_data = json.dumps(execution_result, ensure_ascii=False, indent=2)
        ops_fields["📄 JSON 원본"] = f"```json\n{json_data}\n```"

    return await notification_manager.send_notification(
        message=message,
        level=level,
        title=title,
        fields=ops_fields,
        attach_logs=level in [NotificationLevel.ERROR, NotificationLevel.CRITICAL]
    )

async def execute_and_notify_backup_script(
    script_path: str,
    script_args: List[str] = None,
    notify_on_success: bool = True,
    notify_on_error: bool = True
) -> Dict[str, Any]:
    """
    백업 스크립트 실행 후 결과에 따라 자동 알림 전송

    Args:
        script_path: 실행할 스크립트 경로
        script_args: 스크립트 인수 목록
        notify_on_success: 성공 시 알림 여부
        notify_on_error: 실패 시 알림 여부

    Returns:
        실행 결과와 알림 전송 결과를 포함한 딕셔너리
    """
    script_args = script_args or []
    script_name = Path(script_path).name

    try:
        # 스크립트 실행
        result = subprocess.run(
            [script_path] + script_args,
            capture_output=True,
            text=True,
            timeout=300  # 5분 타임아웃
        )

        # 결과 파싱
        execution_result = {
            'script': script_name,
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'timestamp': datetime.now().isoformat()
        }

        # JSON 출력 파싱 시도
        if result.stdout.strip():
            try:
                # JSON 출력인 경우 파싱
                json_output = json.loads(result.stdout.strip())
                execution_result.update(json_output)
            except json.JSONDecodeError:
                # 일반 텍스트 출력인 경우 그대로 저장
                execution_result['output'] = result.stdout.strip()

        # 알림 전송 조건 확인
        send_notification = False
        notification_level = NotificationLevel.INFO

        if result.returncode != 0 and notify_on_error:
            send_notification = True
            notification_level = NotificationLevel.ERROR
        elif result.returncode == 0 and notify_on_success:
            send_notification = True
            notification_level = NotificationLevel.INFO

        # 알림 전송
        notification_result = {}
        if send_notification:
            notification_result = await send_backup_alert(
                script_name=script_name,
                execution_result=execution_result,
                level=notification_level
            )

        return {
            'execution': execution_result,
            'notification': notification_result,
            'success': result.returncode == 0
        }

    except subprocess.TimeoutExpired:
        error_result = {
            'script': script_name,
            'returncode': -1,
            'error': 'Script execution timeout (5 minutes)',
            'timestamp': datetime.now().isoformat()
        }

        if notify_on_error:
            notification_result = await send_backup_alert(
                script_name=script_name,
                execution_result=error_result,
                level=NotificationLevel.ERROR
            )
        else:
            notification_result = {}

        return {
            'execution': error_result,
            'notification': notification_result,
            'success': False
        }

    except Exception as e:
        error_result = {
            'script': script_name,
            'returncode': -2,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

        if notify_on_error:
            notification_result = await send_backup_alert(
                script_name=script_name,
                execution_result=error_result,
                level=NotificationLevel.ERROR
            )
        else:
            notification_result = {}

        return {
            'execution': error_result,
            'notification': notification_result,
            'success': False
        }

async def send_ops_integration_alert(
    event_type: str,
    security_events: List[Dict],
    backup_results: List[Dict],
    level: NotificationLevel = NotificationLevel.INFO
) -> Dict[str, bool]:
    """
    보안 이벤트와 백업 결과를 통합한 운영 알림 전송

    Args:
        event_type: 통합 이벤트 유형 ('daily_summary', 'security_backup_sync' 등)
        security_events: 보안 이벤트 목록
        backup_results: 백업 결과 목록
        level: 알림 심각도

    Returns:
        채널별 전송 결과
    """
    # 이벤트 유형별 메시지 템플릿
    event_messages = {
        'daily_summary': "📊 일일 운영 현황 요약",
        'security_backup_sync': "🔒 보안+백업 통합 현황",
        'ops_health_check': "🏥 운영 시스템 헬스체크",
        'weekly_report': "📋 주간 운영 리포트"
    }

    message = event_messages.get(event_type, f"🔧 운영 통합 알림: {event_type}")
    title = f"🔧 운영 통합 알림: {event_type}"

    # 통합 통계 계산
    total_security_events = len(security_events)
    blocked_ips = len([e for e in security_events if e.get('event') == 'BLOCKED_IP'])
    backup_successes = len([b for b in backup_results if b.get('success', False)])
    backup_failures = len([b for b in backup_results if not b.get('success', True)])

    # 통합 필드 준비
    integration_fields = {
        "📅 리포트 시간": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "🔒 보안 이벤트": f"{total_security_events}건",
        "🚫 차단된 IP": f"{blocked_ips}개",
        "✅ 백업 성공": f"{backup_successes}건",
        "❌ 백업 실패": f"{backup_failures}건"
    }

    # 세부 보안 이벤트 (최근 5개)
    if security_events:
        recent_security = security_events[-5:]
        security_summary = []
        for event in recent_security:
            event_info = f"• {event.get('event', 'UNKNOWN')} - {event.get('ip', 'N/A')}"
            security_summary.append(event_info)
        integration_fields["🔍 최근 보안 이벤트"] = "\n".join(security_summary)

    # 세부 백업 결과 (최근 5개)
    if backup_results:
        recent_backups = backup_results[-5:]
        backup_summary = []
        for backup in recent_backups:
            status = "✅" if backup.get('success', False) else "❌"
            backup_info = f"{status} {backup.get('script', 'Unknown')} - {backup.get('timestamp', 'N/A')}"
            backup_summary.append(backup_info)
        integration_fields["🔧 최근 백업 작업"] = "\n".join(backup_summary)

    # 레벨 조정 (실패가 있는 경우)
    if backup_failures > 0 or blocked_ips > 10:
        level = NotificationLevel.WARNING
        message = f"⚠️ {message} (주의 필요)"
    elif backup_failures > 2 or blocked_ips > 50:
        level = NotificationLevel.ERROR
        message = f"❌ {message} (즉시 확인 필요)"

    return await notification_manager.send_notification(
        message=message,
        level=level,
        title=title,
        fields=integration_fields,
        attach_logs=level in [NotificationLevel.ERROR, NotificationLevel.CRITICAL]
    )

async def send_dashboard_notification(
    notification_data: Dict[str, Any],
    target_dashboard: str = "admin"
) -> bool:
    """
    관리자 대시보드로 실시간 알림 전송

    Args:
        notification_data: 대시보드에 표시할 알림 데이터
        target_dashboard: 대상 대시보드 ('admin', 'security' 등)

    Returns:
        전송 성공 여부
    """
    try:
        # 대시보드 알림 파일 경로
        dashboard_notification_file = f"logs/dashboard_notifications_{target_dashboard}.json"

        # 기존 알림 로드
        notifications = []
        if Path(dashboard_notification_file).exists():
            try:
                with open(dashboard_notification_file, 'r', encoding='utf-8') as f:
                    notifications = json.load(f)
            except json.JSONDecodeError:
                notifications = []

        # 새 알림 추가
        new_notification = {
            'id': f"notif_{int(datetime.now().timestamp())}_{random.randint(1000, 9999)}",
            'timestamp': datetime.now().isoformat(),
            'title': notification_data.get('title', '알림'),
            'message': notification_data.get('message', ''),
            'level': notification_data.get('level', 'info'),
            'source': notification_data.get('source', 'system'),
            'fields': notification_data.get('fields', {}),
            'read': False
        }

        notifications.append(new_notification)

        # 최대 100개까지만 보관
        if len(notifications) > 100:
            notifications = notifications[-100:]

        # 알림 파일 저장
        with open(dashboard_notification_file, 'w', encoding='utf-8') as f:
            json.dump(notifications, f, ensure_ascii=False, indent=2)

        logger.info(f"대시보드 알림 전송 완료: {target_dashboard} - {notification_data.get('title', '제목없음')}")
        return True

    except Exception as e:
        logger.error(f"대시보드 알림 전송 실패: {e}")
        return False

class OpsIntegrationNotifier:
    """운영 통합 알림 관리자 (보안+백업)"""

    def __init__(self):
        self.security_events = []
        self.backup_results = []
        self.last_summary_time = datetime.now()

    async def log_security_event(self, event_data: Dict[str, Any]):
        """보안 이벤트 로깅"""
        event_data['timestamp'] = datetime.now().isoformat()
        self.security_events.append(event_data)

        # 최대 500개까지만 보관
        if len(self.security_events) > 500:
            self.security_events = self.security_events[-500:]

        # 심각한 보안 이벤트의 경우 즉시 알림
        if event_data.get('level') in ['critical', 'error']:
            await send_security_alert(
                event_type=event_data.get('event', 'SECURITY_EVENT'),
                client_ip=event_data.get('ip', 'Unknown'),
                details=event_data,
                level=NotificationLevel.CRITICAL if event_data.get('level') == 'critical' else NotificationLevel.ERROR
            )

        # 대시보드 알림 전송
        await send_dashboard_notification({
            'title': f"보안 이벤트: {event_data.get('event', 'Unknown')}",
            'message': f"IP {event_data.get('ip', 'Unknown')}에서 {event_data.get('event', '보안 이벤트')} 발생",
            'level': event_data.get('level', 'info'),
            'source': 'security',
            'fields': event_data
        })

    async def log_backup_result(self, backup_data: Dict[str, Any]):
        """백업 결과 로깅"""
        backup_data['timestamp'] = datetime.now().isoformat()
        self.backup_results.append(backup_data)

        # 최대 100개까지만 보관
        if len(self.backup_results) > 100:
            self.backup_results = self.backup_results[-100:]

        # 백업 실패의 경우 즉시 알림
        if not backup_data.get('success', True):
            await send_backup_alert(
                script_name=backup_data.get('script', 'unknown'),
                execution_result=backup_data,
                level=NotificationLevel.ERROR
            )

        # 대시보드 알림 전송
        await send_dashboard_notification({
            'title': f"백업 작업: {backup_data.get('script', 'Unknown')}",
            'message': f"백업 작업이 {'성공' if backup_data.get('success', True) else '실패'}했습니다",
            'level': 'info' if backup_data.get('success', True) else 'error',
            'source': 'backup',
            'fields': backup_data
        })

    async def send_daily_summary(self):
        """일일 요약 알림 전송"""
        # 24시간 내 이벤트 필터링
        now = datetime.now()
        yesterday = now - timedelta(days=1)

        recent_security = [
            event for event in self.security_events
            if datetime.fromisoformat(event['timestamp']) > yesterday
        ]

        recent_backups = [
            backup for backup in self.backup_results
            if datetime.fromisoformat(backup['timestamp']) > yesterday
        ]

        await send_ops_integration_alert(
            event_type='daily_summary',
            security_events=recent_security,
            backup_results=recent_backups,
            level=NotificationLevel.INFO
        )

        self.last_summary_time = now

# 전역 운영 통합 알림 관리자 인스턴스
ops_notifier = OpsIntegrationNotifier()

# 편의 함수들
async def log_security_event(event_data: Dict[str, Any]):
    """보안 이벤트 로깅 편의 함수"""
    return await ops_notifier.log_security_event(event_data)

async def log_backup_result(backup_data: Dict[str, Any]):
    """백업 결과 로깅 편의 함수"""
    return await ops_notifier.log_backup_result(backup_data)

async def send_daily_ops_summary():
    """일일 운영 요약 전송 편의 함수"""
    return await ops_notifier.send_daily_summary()

async def test_ops_integration():
    """운영 통합 알림 시스템 테스트"""
    print("🔧 운영 통합 알림 시스템 테스트 시작...")

    # 테스트 보안 이벤트 로깅
    await log_security_event({
        'event': 'BLOCKED_IP',
        'ip': '192.168.1.100',
        'level': 'critical',
        'details': '테스트용 차단 이벤트'
    })

    # 테스트 백업 결과 로깅
    await log_backup_result({
        'script': 'backup_verifier.sh',
        'success': True,
        'file': 'backup_20240921.tar.gz',
        'size': 1337,
        'details': '테스트용 백업 검증'
    })

    # 백업 스크립트 실행 및 알림 테스트
    test_result = await execute_and_notify_backup_script(
        script_path="scripts/backup_verifier.sh",
        script_args=["--dry-run", "--json"],
        notify_on_success=True,
        notify_on_error=True
    )

    print(f"백업 스크립트 실행 테스트 결과: {test_result['success']}")

    # 일일 요약 테스트
    await send_daily_ops_summary()

    print("✅ 운영 통합 알림 시스템 테스트 완료")

# ================================================
# 주간 운영 리포트 알림 시스템 (Weekly Operations Report)
# ================================================

async def send_weekly_ops_report(
    report_data: Dict[str, Any],
    report_file_path: Optional[str] = None,
    level: NotificationLevel = NotificationLevel.INFO
) -> Dict[str, bool]:
    """
    주간 운영 리포트 결과 알림 전송 (한국어 메시지 지원)

    Args:
        report_data: weekly_ops_report.sh 실행 결과 데이터
        report_file_path: 생성된 Markdown 리포트 파일 경로
        level: 알림 심각도

    Returns:
        채널별 전송 결과
    """
    # 리포트 기간 정보
    period_start = report_data.get('report_metadata', {}).get('period_start', 'Unknown')
    period_end = report_data.get('report_metadata', {}).get('period_end', 'Unknown')

    # 주요 통계 추출
    security_events = report_data.get('security_events', {})
    backup_ops = report_data.get('backup_operations', {})
    system_resources = report_data.get('system_resources', {})
    status_summary = report_data.get('status_summary', {})

    # 통계 요약
    blocked_ips = security_events.get('blocked_ips', 0)
    backup_success_rate = backup_ops.get('success_rate_percent', 0)
    disk_usage = system_resources.get('disk_usage_percent', 0)

    # 상태에 따른 레벨 조정
    if status_summary.get('security_status') == 'critical' or status_summary.get('backup_status') == 'needs_improvement':
        level = NotificationLevel.ERROR
    elif status_summary.get('security_status') == 'warning' or backup_success_rate < 90:
        level = NotificationLevel.WARNING

    # 메시지 생성
    message = f"📊 주간 운영 리포트가 생성되었습니다.\n"
    message += f"📅 기간: {period_start} ~ {period_end}\n\n"

    # 상태 요약
    if blocked_ips > 50:
        message += "🚨 보안: 다수의 IP 차단이 발생했습니다. 즉시 검토가 필요합니다.\n"
    elif blocked_ips > 10:
        message += "⚠️ 보안: 평소보다 많은 IP 차단이 발생했습니다.\n"
    else:
        message += "✅ 보안: 정상적인 보안 상태를 유지하고 있습니다.\n"

    if backup_success_rate < 80:
        message += "🚨 백업: 백업 성공률이 낮습니다. 백업 시스템 점검이 필요합니다.\n"
    elif backup_success_rate < 95:
        message += "⚠️ 백업: 백업 성공률이 평균 이하입니다.\n"
    else:
        message += "✅ 백업: 백업이 안정적으로 수행되고 있습니다.\n"

    # 알림 제목 생성
    title = f"📊 주간 운영 리포트 ({period_start} ~ {period_end})"

    # 세부 정보 필드 준비
    report_fields = {
        "📅 리포트 기간": f"{period_start} ~ {period_end}",
        "📊 생성 시간": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "🛡️ 보안 현황": f"차단 IP {blocked_ips}개 | 상태: {status_summary.get('security_status', 'unknown')}",
        "📦 백업 현황": f"성공률 {backup_success_rate}% | 상태: {status_summary.get('backup_status', 'unknown')}",
        "💾 시스템 리소스": f"디스크 사용률 {disk_usage}% | 상태: {status_summary.get('disk_status', 'unknown')}"
    }

    # 상세 통계 추가
    if security_events:
        report_fields["🔒 보안 세부사항"] = (
            f"Rate Limit 위반: {security_events.get('rate_limit_violations', 0)}회\n"
            f"화이트리스트 추가: {security_events.get('whitelist_additions', 0)}회\n"
            f"모니터링 이벤트: {security_events.get('monitoring_events', 0)}회"
        )

    if backup_ops:
        report_fields["📦 백업 세부사항"] = (
            f"성공한 백업: {backup_ops.get('successful_backups', 0)}회\n"
            f"실패한 백업: {backup_ops.get('failed_backups', 0)}회\n"
            f"정리 작업: {backup_ops.get('cleanup_operations', 0)}회"
        )

    # 리포트 파일 링크 추가
    if report_file_path:
        # 상대 경로를 웹 URL로 변환
        report_url = report_file_path.replace('reports/', '/reports/')
        report_fields["📄 상세 리포트"] = f"[Markdown 리포트 보기]({report_url})"

    # 권장 사항 추가
    recommendations = []
    if blocked_ips > 20:
        recommendations.append("🔍 보안 정책 검토 및 화이트리스트 최적화")
    if backup_success_rate < 95:
        recommendations.append("📦 백업 시스템 점검 및 저장소 확인")
    if disk_usage > 85:
        recommendations.append("💾 디스크 정리 및 용량 확장 검토")

    if recommendations:
        report_fields["💡 권장 사항"] = "\n".join(recommendations)

    # 다음 주 계획 추가
    next_week_plans = [
        "🔍 보안 패턴 분석 및 화이트리스트 최적화",
        "📦 백업 정책 검토 및 저장 공간 최적화",
        "🔄 자동화 스크립트 성능 개선"
    ]
    report_fields["📋 다음 주 계획"] = "\n".join(next_week_plans)

    return await notification_manager.send_notification(
        message=message,
        level=level,
        title=title,
        fields=report_fields,
        attach_logs=level in [NotificationLevel.ERROR, NotificationLevel.CRITICAL]
    )

async def execute_and_notify_weekly_report(
    script_path: str = "scripts/weekly_ops_report.sh",
    script_args: List[str] = None,
    auto_notify: bool = True
) -> Dict[str, Any]:
    """
    주간 운영 리포트 스크립트 실행 후 결과 알림 전송

    Args:
        script_path: weekly_ops_report.sh 스크립트 경로
        script_args: 스크립트 실행 인수
        auto_notify: 자동 알림 전송 여부

    Returns:
        실행 결과와 알림 전송 결과
    """
    script_args = script_args or ["--json"]

    try:
        # 스크립트 실행
        result = subprocess.run(
            [script_path] + script_args,
            capture_output=True,
            text=True,
            timeout=300,  # 5분 타임아웃
            cwd=Path(script_path).parent.parent  # 프로젝트 루트에서 실행
        )

        execution_result = {
            'script': 'weekly_ops_report.sh',
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'timestamp': datetime.now().isoformat()
        }

        # JSON 출력 파싱
        report_data = {}
        report_file_path = None

        if result.returncode == 0 and result.stdout.strip():
            try:
                # JSON 출력 파싱
                json_output = json.loads(result.stdout.strip())
                report_data = json_output

                # 리포트 파일 경로 추정
                period_end = report_data.get('report_metadata', {}).get('period_end', datetime.now().strftime('%Y-%m-%d'))
                report_file_path = f"reports/weekly/weekly-report-{period_end}.md"

            except json.JSONDecodeError:
                # JSON 파싱 실패 시 기본 데이터 사용
                report_data = {
                    'report_metadata': {
                        'period_start': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
                        'period_end': datetime.now().strftime('%Y-%m-%d'),
                        'generated_at': datetime.now().isoformat()
                    },
                    'execution_output': result.stdout.strip()
                }

        # 알림 전송
        notification_result = {}
        if auto_notify and result.returncode == 0:
            notification_result = await send_weekly_ops_report(
                report_data=report_data,
                report_file_path=report_file_path,
                level=NotificationLevel.INFO
            )
        elif auto_notify and result.returncode != 0:
            # 실행 실패 시 에러 알림
            error_data = {
                'report_metadata': {
                    'period_start': 'Unknown',
                    'period_end': 'Unknown',
                    'generated_at': datetime.now().isoformat()
                },
                'error': result.stderr or "스크립트 실행 실패",
                'returncode': result.returncode
            }
            notification_result = await send_weekly_ops_report(
                report_data=error_data,
                level=NotificationLevel.ERROR
            )

        return {
            'execution': execution_result,
            'report_data': report_data,
            'report_file': report_file_path,
            'notification': notification_result,
            'success': result.returncode == 0
        }

    except subprocess.TimeoutExpired:
        error_result = {
            'script': 'weekly_ops_report.sh',
            'returncode': -1,
            'error': 'Weekly report generation timeout (5 minutes)',
            'timestamp': datetime.now().isoformat()
        }

        if auto_notify:
            notification_result = await send_weekly_ops_report(
                report_data={
                    'error': 'Script timeout',
                    'report_metadata': {'generated_at': datetime.now().isoformat()}
                },
                level=NotificationLevel.ERROR
            )
        else:
            notification_result = {}

        return {
            'execution': error_result,
            'report_data': {},
            'report_file': None,
            'notification': notification_result,
            'success': False
        }

    except Exception as e:
        error_result = {
            'script': 'weekly_ops_report.sh',
            'returncode': -2,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

        if auto_notify:
            notification_result = await send_weekly_ops_report(
                report_data={
                    'error': str(e),
                    'report_metadata': {'generated_at': datetime.now().isoformat()}
                },
                level=NotificationLevel.ERROR
            )
        else:
            notification_result = {}

        return {
            'execution': error_result,
            'report_data': {},
            'report_file': None,
            'notification': notification_result,
            'success': False
        }

# 편의 함수
async def send_weekly_report_notification(report_period: str = None):
    """
    주간 리포트 생성 및 알림 전송 편의 함수

    Args:
        report_period: 리포트 기간 (None일 경우 최근 7일)
    """
    script_args = ["--json"]
    if report_period:
        script_args.extend(["--period", report_period])

    return await execute_and_notify_weekly_report(
        script_args=script_args,
        auto_notify=True
    )

async def test_weekly_report_notification():
    """주간 리포트 알림 시스템 테스트"""
    print("📊 주간 리포트 알림 시스템 테스트 시작...")

    # 테스트용 리포트 데이터
    test_report_data = {
        'report_metadata': {
            'period_start': '2024-09-14',
            'period_end': '2024-09-21',
            'generated_at': datetime.now().isoformat(),
            'report_type': 'weekly_operations'
        },
        'security_events': {
            'blocked_ips': 15,
            'rate_limit_violations': 45,
            'whitelist_additions': 3,
            'monitoring_events': 120,
            'total_security_events': 183
        },
        'backup_operations': {
            'successful_backups': 6,
            'failed_backups': 1,
            'cleanup_operations': 2,
            'success_rate_percent': 86,
            'total_backup_operations': 7
        },
        'system_resources': {
            'disk_usage_percent': 78,
            'security_log_size_bytes': 2048576,
            'backup_directory_size_kb': 1048576
        },
        'status_summary': {
            'security_status': 'warning',
            'backup_status': 'good',
            'disk_status': 'normal'
        }
    }

    # 테스트 알림 전송
    result = await send_weekly_ops_report(
        report_data=test_report_data,
        report_file_path="reports/weekly/weekly-report-2024-09-21.md",
        level=NotificationLevel.INFO
    )

    print(f"✅ 주간 리포트 알림 테스트 완료: {result}")
    return result

if __name__ == "__main__":
    # 테스트 실행
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "ops":
            asyncio.run(test_ops_integration())
        elif sys.argv[1] == "weekly":
            asyncio.run(test_weekly_report_notification())
        else:
            asyncio.run(test_notifications())
    else:
        asyncio.run(test_notifications())