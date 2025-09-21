#!/usr/bin/env python3
"""
보안 이벤트 로거
- Rate Limiting 위반, 차단된 IP, 화이트리스트 이벤트를 기록
- logs/security.log 파일에 일별 회전식 로그 저장
"""
import logging
from logging.handlers import TimedRotatingFileHandler

logger = logging.getLogger("security")
logger.setLevel(logging.INFO)

handler = TimedRotatingFileHandler("logs/security.log", when="midnight", interval=1, backupCount=30, encoding="utf-8")
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

logger.addHandler(handler)

def log_security_event(event_type: str, detail: str):
    """보안 이벤트 기록 함수"""
    logger.info(f"[{event_type}] {detail}")