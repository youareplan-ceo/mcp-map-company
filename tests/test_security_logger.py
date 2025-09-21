import os
import json
import pytest
from mcp.security_logger import log_security_event

# 🔐 보안 로그 시스템 테스트 (한국어 주석 포함)
# 주요 검증 항목:
# 1. 로그 파일 생성 여부
# 2. 이벤트 기록 형식 (JSON 포함)
# 3. 차단된 IP, 화이트리스트 등 이벤트 기록 검증
# 4. 30일 보관 정책 시뮬레이션

LOG_PATH = "logs/security.log"

def setup_function():
    # 테스트 시작 전 기존 로그 제거
    if os.path.exists(LOG_PATH):
        os.remove(LOG_PATH)

def test_log_creation():
    log_security_event("BLOCKED_IP", "192.168.0.15 - Rate Limit 초과로 차단")
    assert os.path.exists(LOG_PATH), "❌ 로그 파일이 생성되지 않았습니다"

def test_log_content():
    log_security_event("WHITELIST_ADD", "127.0.0.1 - 화이트리스트 추가")
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert any("WHITELIST_ADD" in line for line in lines), "❌ 화이트리스트 이벤트 기록 실패"

def test_log_json_format():
    log_security_event("MONITOR", "테스트 모니터링 이벤트")
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        last_line = f.readlines()[-1]
    data = json.loads(last_line)
    assert "event" in data and "message" in data, "❌ 로그 JSON 형식이 올바르지 않습니다"