"""
MCP-MAP Company Notification System
심각도별 알림 시스템 - Slack, Discord, Email 채널 지원
"""

import os
import asyncio
import aiohttp
import smtplib
import logging
from datetime import datetime
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from typing import Optional, Dict, Any, List
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

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
        """Slack 채널로 알림 전송"""
        if not self.enabled:
            logger.warning("Slack 알림이 비활성화됨 - 웹훅 URL 미설정")
            return False

        try:
            # 심각도별 색상 및 이모지 설정
            level_config = {
                NotificationLevel.CRITICAL: {"color": "#d63031", "emoji": "🚨"},
                NotificationLevel.ERROR: {"color": "#ff6b6b", "emoji": "❌"},
                NotificationLevel.WARNING: {"color": "#fdcb6e", "emoji": "⚠️"},
                NotificationLevel.INFO: {"color": "#74b9ff", "emoji": "ℹ️"}
            }

            config = level_config.get(level, level_config[NotificationLevel.INFO])

            payload = {
                "username": "MCP-MAP Company Bot",
                "attachments": [{
                    "color": config["color"],
                    "title": f"{config['emoji']} {title or f'MCP-MAP {level.value.upper()} 알림'}",
                    "text": message,
                    "timestamp": int(datetime.now().timestamp()),
                    "footer": "MCP-MAP Company Monitoring",
                    "fields": []
                }]
            }

            # 추가 필드 정보 첨부
            if fields:
                for key, value in fields.items():
                    payload["attachments"][0]["fields"].append({
                        "title": key,
                        "value": str(value),
                        "short": True
                    })

            # 로그 첨부 (심각도별 차별화)
            if attach_logs:
                if level == NotificationLevel.CRITICAL:
                    recent_logs = get_recent_logs(lines=50)
                    if recent_logs and len(recent_logs) > 100:
                        # Slack 메시지 길이 제한 고려
                        max_log_length = 2000
                        if len(recent_logs) > max_log_length:
                            recent_logs = recent_logs[-max_log_length:] + "\n... (truncated)"

                        payload["attachments"].append({
                            "color": "#ff0000",
                            "title": "📋 긴급 상황 로그 (최근 50줄)",
                            "text": f"```\n{recent_logs}\n```",
                            "footer": "Critical 알림에 자동 첨부됨"
                        })

                elif level == NotificationLevel.ERROR:
                    recent_logs = get_recent_logs(lines=20)
                    if recent_logs and len(recent_logs) > 50:
                        max_log_length = 1500
                        if len(recent_logs) > max_log_length:
                            recent_logs = recent_logs[-max_log_length:] + "\n... (truncated)"

                        payload["attachments"].append({
                            "color": "#ff6b6b",
                            "title": "📋 오류 로그 (최근 20줄)",
                            "text": f"```\n{recent_logs}\n```",
                            "footer": "Error 알림에 자동 첨부됨"
                        })

                elif level == NotificationLevel.WARNING:
                    # Warning은 로그 요약만 제공
                    recent_logs = get_recent_logs(lines=10)
                    if recent_logs:
                        log_lines = recent_logs.split('\n')
                        summary = f"최근 로그 상태: {len(log_lines)}줄 확인됨 (최신 10줄 요약)"
                        payload["attachments"][0]["fields"].append({
                            "title": "📝 로그 요약",
                            "value": summary,
                            "short": True
                        })

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.info("Slack 알림 전송 성공")
                        return True
                    else:
                        logger.error(f"Slack 알림 전송 실패: {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Slack 알림 전송 오류: {e}")
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
        """Discord 채널로 알림 전송"""
        if not self.enabled:
            logger.warning("Discord 알림이 비활성화됨 - 웹훅 URL 미설정")
            return False

        try:
            # 심각도별 색상 및 이모지 설정 (Discord용 정수 색상)
            level_config = {
                NotificationLevel.CRITICAL: {"color": 13382451, "emoji": "🚨"},
                NotificationLevel.ERROR: {"color": 16744272, "emoji": "❌"},
                NotificationLevel.WARNING: {"color": 16632814, "emoji": "⚠️"},
                NotificationLevel.INFO: {"color": 7649023, "emoji": "ℹ️"}
            }

            config = level_config.get(level, level_config[NotificationLevel.INFO])

            # 기본 embed 필드 생성
            embed_fields = []
            if fields:
                for key, value in fields.items():
                    embed_fields.append({
                        "name": key,
                        "value": str(value),
                        "inline": True
                    })

            # 로그 요약 (Warning/Info용)
            if attach_logs and level in [NotificationLevel.WARNING, NotificationLevel.INFO]:
                recent_logs = get_recent_logs(lines=10)
                if recent_logs:
                    log_lines = recent_logs.split('\n')
                    summary = f"최근 로그 상태: {len(log_lines)}줄 확인됨"
                    embed_fields.append({
                        "name": "📝 로그 요약",
                        "value": summary,
                        "inline": True
                    })

            # 타임스탬프 필드 추가
            embed_fields.append({
                "name": "시간",
                "value": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "inline": True
            })

            embeds = [{
                "title": f"{config['emoji']} {title or f'MCP-MAP {level.value.upper()} 알림'}",
                "description": message,
                "color": config["color"],
                "fields": embed_fields,
                "footer": {
                    "text": "MCP-MAP Company Monitoring System"
                },
                "timestamp": datetime.now().isoformat()
            }]

            # 로그 첨부 (Critical/Error용)
            if attach_logs:
                if level == NotificationLevel.CRITICAL:
                    recent_logs = get_recent_logs(lines=50)
                    if recent_logs and len(recent_logs) > 100:
                        # Discord 필드 값 제한 고려
                        max_log_length = 1900
                        if len(recent_logs) > max_log_length:
                            recent_logs = recent_logs[-max_log_length:] + "\n... (truncated)"

                        embeds.append({
                            "title": "📋 긴급 상황 로그",
                            "description": f"```\n{recent_logs}\n```",
                            "color": 13382451,
                            "footer": {
                                "text": "최근 50줄 로그 - Critical 알림에 자동 첨부됨"
                            }
                        })

                elif level == NotificationLevel.ERROR:
                    recent_logs = get_recent_logs(lines=20)
                    if recent_logs and len(recent_logs) > 50:
                        max_log_length = 1400
                        if len(recent_logs) > max_log_length:
                            recent_logs = recent_logs[-max_log_length:] + "\n... (truncated)"

                        embeds.append({
                            "title": "📋 오류 로그",
                            "description": f"```\n{recent_logs}\n```",
                            "color": 16744272,
                            "footer": {
                                "text": "최근 20줄 로그 - Error 알림에 자동 첨부됨"
                            }
                        })

            payload = {
                "username": "MCP-MAP Company Bot",
                "avatar_url": "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f916.png",
                "embeds": embeds
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 204:  # Discord는 성공 시 204 반환
                        logger.info("Discord 알림 전송 성공")
                        return True
                    else:
                        logger.error(f"Discord 알림 전송 실패: {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Discord 알림 전송 오류: {e}")
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
        """이메일 알림 전송"""
        if not self.enabled:
            logger.warning("이메일 알림이 비활성화됨 - 설정 누락")
            return False

        try:
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

            # HTML 및 텍스트 컨텐츠 생성
            html_content = self._create_html_content(message, level, fields, recent_logs)
            text_content = self._create_text_content(message, level, fields, recent_logs)

            html_part = MimeText(html_content, 'html')
            text_part = MimeText(text_content, 'plain')

            msg.attach(text_part)
            msg.attach(html_part)

            # 이메일 전송 (동기 함수를 비동기로 실행)
            await asyncio.get_event_loop().run_in_executor(
                None, self._send_email_sync, msg
            )

            logger.info(f"이메일 알림 전송 성공 ({len(self.recipients)}명)")
            return True

        except Exception as e:
            logger.error(f"이메일 알림 전송 오류: {e}")
            return False

    def _send_email_sync(self, msg: MimeMultipart):
        """동기식 이메일 전송"""
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.email, self.password)
            server.send_message(msg)

    def _create_html_content(self, message: str, level: NotificationLevel, fields: Optional[Dict] = None, recent_logs: Optional[str] = None) -> str:
        """HTML 이메일 컨텐츠 생성"""
        level_config = {
            NotificationLevel.CRITICAL: {"bg": "#ffebee", "border": "#d32f2f", "emoji": "🚨"},
            NotificationLevel.ERROR: {"bg": "#fff3e0", "border": "#f57c00", "emoji": "❌"},
            NotificationLevel.WARNING: {"bg": "#fffde7", "border": "#fbc02d", "emoji": "⚠️"},
            NotificationLevel.INFO: {"bg": "#e3f2fd", "border": "#1976d2", "emoji": "ℹ️"}
        }

        config = level_config.get(level, level_config[NotificationLevel.INFO])

        fields_html = ""
        if fields:
            fields_html = "<h3>추가 정보:</h3><ul>"
            for key, value in fields.items():
                fields_html += f"<li><strong>{key}:</strong> {value}</li>"
            fields_html += "</ul>"

        logs_html = ""
        if recent_logs:
            if level == NotificationLevel.CRITICAL and len(recent_logs) > 100:
                logs_html = f"""
                <div style="margin: 20px 0; padding: 15px; background: #ffebee; border-left: 4px solid #d32f2f; border-radius: 4px;">
                    <h3 style="margin-top: 0; color: #d32f2f;">📋 긴급 상황 로그 (최근 50줄)</h3>
                    <pre style="background: #ffffff; padding: 10px; border-radius: 4px; overflow-x: auto; font-size: 12px; max-height: 400px; overflow-y: auto;">{recent_logs}</pre>
                    <p style="font-size: 11px; color: #666; margin-bottom: 0;">Critical 알림에 자동 첨부됨</p>
                </div>
                """
            elif level == NotificationLevel.ERROR and len(recent_logs) > 50:
                logs_html = f"""
                <div style="margin: 20px 0; padding: 15px; background: #fff3e0; border-left: 4px solid #f57c00; border-radius: 4px;">
                    <h3 style="margin-top: 0; color: #f57c00;">📋 오류 로그 (최근 20줄)</h3>
                    <pre style="background: #ffffff; padding: 10px; border-radius: 4px; overflow-x: auto; font-size: 12px; max-height: 300px; overflow-y: auto;">{recent_logs}</pre>
                    <p style="font-size: 11px; color: #666; margin-bottom: 0;">Error 알림에 자동 첨부됨</p>
                </div>
                """
            elif level in [NotificationLevel.WARNING, NotificationLevel.INFO] and recent_logs:
                log_lines = recent_logs.split('\n')
                logs_html = f"""
                <div style="margin: 20px 0; padding: 15px; background: #f1f8ff; border-left: 4px solid #1976d2; border-radius: 4px;">
                    <h3 style="margin-top: 0; color: #1976d2;">📝 로그 상태 요약</h3>
                    <p style="margin: 5px 0;">최근 로그 상태: {len(log_lines)}줄 확인됨 (최신 10줄 요약)</p>
                </div>
                """

        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f9f9f9;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="background: {config['bg']}; border-left: 4px solid {config['border']}; padding: 20px;">
                    <h2 style="margin: 0; color: {config['border']};">{config['emoji']} MCP-MAP Company 알림</h2>
                    <p style="margin: 5px 0 0 0; color: #666;">심각도: {level.value.upper()}</p>
                </div>
                <div style="padding: 20px;">
                    <p style="font-size: 16px; line-height: 1.5; color: #333;">{message}</p>
                    {fields_html}
                    {logs_html}
                    <hr style="margin: 20px 0; border: none; border-top: 1px solid #eee;">
                    <p style="color: #999; font-size: 12px;">
                        전송 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                        발신: MCP-MAP Company 모니터링 시스템
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

    def _create_text_content(self, message: str, level: NotificationLevel, fields: Optional[Dict] = None, recent_logs: Optional[str] = None) -> str:
        """텍스트 이메일 컨텐츠 생성"""
        content = f"""
MCP-MAP COMPANY 알림 - {level.value.upper()}
{'=' * 50}

{message}

"""
        if fields:
            content += "추가 정보:\n"
            for key, value in fields.items():
                content += f"• {key}: {value}\n"
            content += "\n"

        if recent_logs:
            if level == NotificationLevel.CRITICAL and len(recent_logs) > 100:
                content += f"""
긴급 상황 로그 (최근 50줄):
{'-' * 60}
{recent_logs}
{'-' * 60}
Critical 알림에 자동 첨부됨

"""
            elif level == NotificationLevel.ERROR and len(recent_logs) > 50:
                content += f"""
오류 로그 (최근 20줄):
{'-' * 60}
{recent_logs}
{'-' * 60}
Error 알림에 자동 첨부됨

"""
            elif level in [NotificationLevel.WARNING, NotificationLevel.INFO]:
                log_lines = recent_logs.split('\n')
                content += f"""
로그 상태 요약:
최근 로그 상태: {len(log_lines)}줄 확인됨 (최신 10줄 요약)

"""

        content += f"""
전송 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
발신: MCP-MAP Company 모니터링 시스템
        """

        return content

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