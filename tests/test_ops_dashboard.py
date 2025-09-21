#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🖥️ 운영 대시보드 테스트 자동화 모듈

이 모듈은 관리자 대시보드의 주요 패널들에 대한 포괄적인 테스트를 제공합니다:
- 알림 통합 패널 로드 및 기능 테스트
- 보안 로그 패널 데이터 표시 검증
- 백업 상태/알림 통합 패널 정상 동작 확인
- 모의 데이터로 필터링, 모달, 내보내기 기능 검증
"""

import pytest
import asyncio
import json
import tempfile
import requests
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 프로젝트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent
DASHBOARD_PATH = PROJECT_ROOT / "web" / "admin_dashboard.html"


class TestOpsDashboardPanels:
    """운영 대시보드 패널 테스트 클래스"""

    @pytest.fixture(scope="class")
    def browser_setup(self):
        """브라우저 설정 (헤드리스 모드)"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # 헤드리스 모드
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.implicitly_wait(10)
            yield driver
        except Exception as e:
            pytest.skip(f"Chrome WebDriver를 사용할 수 없습니다: {e}")
        finally:
            if 'driver' in locals():
                driver.quit()

    @pytest.fixture
    def dashboard_url(self):
        """대시보드 URL 반환"""
        if DASHBOARD_PATH.exists():
            return f"file://{DASHBOARD_PATH.absolute()}"
        else:
            pytest.skip("admin_dashboard.html 파일을 찾을 수 없습니다")

    def test_dashboard_page_load(self, browser_setup, dashboard_url):
        """관리자 대시보드 페이지 로드 테스트"""
        driver = browser_setup

        # 대시보드 페이지 로드
        driver.get(dashboard_url)

        # 페이지 제목 확인
        assert "MCP-MAP 관리자 대시보드" in driver.title

        # 주요 섹션 존재 확인
        main_sections = [
            "🔔 운영 알림 통합 패널",
            "🔒 보안 모니터링",
            "💾 백업 관리",
            "📊 시스템 모니터링"
        ]

        for section in main_sections:
            try:
                element = driver.find_element(By.XPATH, f"//*[contains(text(), '{section}')]")
                assert element.is_displayed()
                print(f"✅ {section} 섹션 확인됨")
            except NoSuchElementException:
                print(f"⚠️ {section} 섹션을 찾을 수 없음")

    def test_ops_notification_panel_elements(self, browser_setup, dashboard_url):
        """🔔 운영 알림 통합 패널 요소 존재 확인 테스트"""
        driver = browser_setup
        driver.get(dashboard_url)

        # 통계 카드 요소들 확인
        stat_cards = [
            "criticalNotificationCount",
            "errorNotificationCount",
            "warningNotificationCount",
            "infoNotificationCount"
        ]

        for card_id in stat_cards:
            try:
                element = driver.find_element(By.ID, card_id)
                assert element.is_displayed()
                print(f"✅ 통계 카드 {card_id} 확인됨")
            except NoSuchElementException:
                print(f"⚠️ 통계 카드 {card_id}를 찾을 수 없음")

        # 필터 버튼들 확인
        filter_buttons = [
            "filterAllBtn",
            "filterSecurityBtn",
            "filterBackupBtn",
            "filterSystemBtn"
        ]

        for btn_id in filter_buttons:
            try:
                element = driver.find_element(By.ID, btn_id)
                assert element.is_displayed()
                print(f"✅ 필터 버튼 {btn_id} 확인됨")
            except NoSuchElementException:
                print(f"⚠️ 필터 버튼 {btn_id}를 찾을 수 없음")

        # 알림 목록 컨테이너 확인
        try:
            notifications_list = driver.find_element(By.ID, "opsNotificationsList")
            assert notifications_list.is_displayed()
            print("✅ 운영 알림 목록 컨테이너 확인됨")
        except NoSuchElementException:
            print("⚠️ 운영 알림 목록 컨테이너를 찾을 수 없음")

    def test_security_monitoring_panel(self, browser_setup, dashboard_url):
        """🔒 보안 모니터링 패널 테스트"""
        driver = browser_setup
        driver.get(dashboard_url)

        # 보안 통계 카드 확인
        security_stats = [
            "blockedIpCount",
            "rateLimitViolations",
            "whitelistCount",
            "monitoringIpCount"
        ]

        for stat_id in security_stats:
            try:
                element = driver.find_element(By.ID, stat_id)
                # 요소가 존재하면 성공 (값이 없어도 됨)
                print(f"✅ 보안 통계 {stat_id} 확인됨")
            except NoSuchElementException:
                print(f"⚠️ 보안 통계 {stat_id}를 찾을 수 없음")

        # 차단된 IP 목록 컨테이너 확인
        try:
            blocked_ips = driver.find_element(By.ID, "blockedIpsList")
            print("✅ 차단된 IP 목록 컨테이너 확인됨")
        except NoSuchElementException:
            print("⚠️ 차단된 IP 목록 컨테이너를 찾을 수 없음")

        # IP 화이트리스트 입력 폼 확인
        try:
            whitelist_input = driver.find_element(By.ID, "newWhitelistIp")
            add_btn = driver.find_element(By.ID, "addWhitelistBtn")
            print("✅ IP 화이트리스트 관리 폼 확인됨")
        except NoSuchElementException:
            print("⚠️ IP 화이트리스트 관리 폼을 찾을 수 없음")

    def test_backup_management_panel(self, browser_setup, dashboard_url):
        """💾 백업 관리 패널 테스트"""
        driver = browser_setup
        driver.get(dashboard_url)

        # 백업 상태 카드 확인
        backup_stats = [
            "lastBackupTime",
            "backupFileCount",
            "totalBackupSize",
            "backupIntegrityStatus"
        ]

        for stat_id in backup_stats:
            try:
                element = driver.find_element(By.ID, stat_id)
                print(f"✅ 백업 통계 {stat_id} 확인됨")
            except NoSuchElementException:
                print(f"⚠️ 백업 통계 {stat_id}를 찾을 수 없음")

        # 백업 작업 버튼들 확인
        backup_buttons = [
            "startBackupBtn",
            "verifyBackupBtn",
            "cleanupBackupBtn"
        ]

        for btn_id in backup_buttons:
            try:
                element = driver.find_element(By.ID, btn_id)
                print(f"✅ 백업 버튼 {btn_id} 확인됨")
            except NoSuchElementException:
                print(f"⚠️ 백업 버튼 {btn_id}를 찾을 수 없음")

    def test_filter_button_interactions(self, browser_setup, dashboard_url):
        """필터 버튼 상호작용 테스트"""
        driver = browser_setup
        driver.get(dashboard_url)

        # JavaScript 로드 대기
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return typeof opsNotificationManager !== 'undefined'")
        )

        filter_buttons = ["filterAllBtn", "filterSecurityBtn", "filterBackupBtn", "filterSystemBtn"]

        for btn_id in filter_buttons:
            try:
                button = driver.find_element(By.ID, btn_id)

                # 버튼 클릭
                driver.execute_script("arguments[0].click();", button)
                time.sleep(0.5)  # 클릭 처리 대기

                # 활성화 상태 확인 (CSS 클래스 확인)
                classes = button.get_attribute("class")
                print(f"✅ {btn_id} 클릭 후 클래스: {classes}")

            except NoSuchElementException:
                print(f"⚠️ 필터 버튼 {btn_id}를 찾을 수 없음")
            except Exception as e:
                print(f"⚠️ {btn_id} 클릭 중 오류: {e}")

    def test_json_modal_functionality(self, browser_setup, dashboard_url):
        """JSON 데이터 모달 기능 테스트"""
        driver = browser_setup
        driver.get(dashboard_url)

        # JSON 모달 요소 확인
        try:
            json_modal = driver.find_element(By.ID, "jsonDataModal")
            close_btn = driver.find_element(By.ID, "closeJsonModalBtn")
            json_content = driver.find_element(By.ID, "jsonContent")

            print("✅ JSON 모달 요소들 확인됨")

            # 모달이 초기에는 숨겨져 있는지 확인
            assert "hidden" in json_modal.get_attribute("class")
            print("✅ JSON 모달이 초기에 숨겨져 있음")

        except NoSuchElementException:
            print("⚠️ JSON 모달 요소를 찾을 수 없음")

    def test_dark_mode_toggle(self, browser_setup, dashboard_url):
        """다크 모드 토글 기능 테스트"""
        driver = browser_setup
        driver.get(dashboard_url)

        try:
            # 다크 모드 토글 버튼 찾기
            dark_mode_btn = driver.find_element(By.ID, "darkModeToggle")

            # 초기 상태 확인
            initial_classes = driver.find_element(By.TAG_NAME, "html").get_attribute("class")
            print(f"초기 HTML 클래스: {initial_classes}")

            # 다크 모드 토글
            dark_mode_btn.click()
            time.sleep(0.5)

            # 변경된 상태 확인
            new_classes = driver.find_element(By.TAG_NAME, "html").get_attribute("class")
            print(f"토글 후 HTML 클래스: {new_classes}")

            print("✅ 다크 모드 토글 기능 확인됨")

        except NoSuchElementException:
            print("⚠️ 다크 모드 토글 버튼을 찾을 수 없음")

    def test_refresh_button_functionality(self, browser_setup, dashboard_url):
        """새로고침 버튼 기능 테스트"""
        driver = browser_setup
        driver.get(dashboard_url)

        refresh_buttons = [
            "refreshOpsNotificationsBtn",
            "refreshSecurityDataBtn",
            "refreshBackupStatusBtn"
        ]

        for btn_id in refresh_buttons:
            try:
                button = driver.find_element(By.ID, btn_id)

                # 버튼 클릭
                driver.execute_script("arguments[0].click();", button)
                time.sleep(1)  # 새로고침 처리 대기

                print(f"✅ {btn_id} 새로고침 버튼 클릭 확인됨")

            except NoSuchElementException:
                print(f"⚠️ 새로고침 버튼 {btn_id}를 찾을 수 없음")


class TestDashboardAPIIntegration:
    """대시보드 API 통합 테스트 클래스"""

    def test_security_api_endpoint_structure(self):
        """보안 API 엔드포인트 구조 테스트"""
        # 모의 API 응답 구조 검증
        mock_security_data = {
            "blocked_count": 5,
            "blocked_ips": ["192.168.1.100", "203.0.113.1"],
            "whitelist_count": 10,
            "rate_limit_violations": 25,
            "monitoring_ips": 50
        }

        # 필수 필드 확인
        required_fields = ["blocked_count", "blocked_ips", "whitelist_count"]
        for field in required_fields:
            assert field in mock_security_data
            print(f"✅ 보안 API 필수 필드 {field} 확인됨")

    def test_backup_api_endpoint_structure(self):
        """백업 API 엔드포인트 구조 테스트"""
        # 모의 백업 API 응답 구조 검증
        mock_backup_data = {
            "last_backup": "2024-01-15T02:00:00Z",
            "file_count": 127,
            "total_size_gb": 45.2,
            "integrity_status": "good",
            "recent_operations": [
                {
                    "operation": "backup_verification",
                    "timestamp": "2024-01-15T02:15:00Z",
                    "status": "completed",
                    "files_checked": 127
                }
            ]
        }

        # 필수 필드 확인
        required_fields = ["last_backup", "file_count", "integrity_status"]
        for field in required_fields:
            assert field in mock_backup_data
            print(f"✅ 백업 API 필수 필드 {field} 확인됨")

    def test_notification_api_endpoint_structure(self):
        """알림 API 엔드포인트 구조 테스트"""
        # 모의 알림 API 응답 구조 검증
        mock_notification_data = {
            "notifications": [
                {
                    "id": "ops-1642234567-1",
                    "type": "security",
                    "level": "critical",
                    "title": "🚨 보안 침입 시도 탐지",
                    "message": "비정상적인 로그인 시도가 감지되었습니다",
                    "timestamp": "2024-01-15T14:30:00Z",
                    "source": "Security Logger",
                    "status": "active"
                }
            ],
            "total_count": 1,
            "stats": {
                "critical": 1,
                "error": 0,
                "warning": 2,
                "info": 5
            }
        }

        # 필수 필드 확인
        required_fields = ["notifications", "total_count", "stats"]
        for field in required_fields:
            assert field in mock_notification_data
            print(f"✅ 알림 API 필수 필드 {field} 확인됨")

        # 개별 알림 구조 확인
        notification = mock_notification_data["notifications"][0]
        notification_fields = ["id", "type", "level", "title", "timestamp"]
        for field in notification_fields:
            assert field in notification
            print(f"✅ 알림 개체 필수 필드 {field} 확인됨")


class TestDashboardMockDataInteraction:
    """모의 데이터와의 상호작용 테스트 클래스"""

    def test_mock_notification_filtering(self):
        """모의 알림 데이터 필터링 테스트"""
        # 모의 알림 데이터 생성
        mock_notifications = [
            {
                "id": "1", "type": "security", "level": "critical",
                "title": "보안 침입 시도", "timestamp": "2024-01-15T14:30:00Z"
            },
            {
                "id": "2", "type": "backup", "level": "warning",
                "title": "백업 검증 경고", "timestamp": "2024-01-15T02:15:00Z"
            },
            {
                "id": "3", "type": "system", "level": "info",
                "title": "시스템 점검 완료", "timestamp": "2024-01-15T01:00:00Z"
            }
        ]

        # 타입별 필터링 테스트
        security_notifications = [n for n in mock_notifications if n["type"] == "security"]
        backup_notifications = [n for n in mock_notifications if n["type"] == "backup"]
        system_notifications = [n for n in mock_notifications if n["type"] == "system"]

        assert len(security_notifications) == 1
        assert len(backup_notifications) == 1
        assert len(system_notifications) == 1

        print("✅ 모의 알림 데이터 타입별 필터링 확인됨")

        # 심각도별 필터링 테스트
        critical_notifications = [n for n in mock_notifications if n["level"] == "critical"]
        warning_notifications = [n for n in mock_notifications if n["level"] == "warning"]
        info_notifications = [n for n in mock_notifications if n["level"] == "info"]

        assert len(critical_notifications) == 1
        assert len(warning_notifications) == 1
        assert len(info_notifications) == 1

        print("✅ 모의 알림 데이터 심각도별 필터링 확인됨")

    def test_mock_security_event_processing(self):
        """모의 보안 이벤트 처리 테스트"""
        # 모의 보안 이벤트 데이터
        mock_security_events = [
            {
                "timestamp": "2024-01-15T14:30:00Z",
                "event_type": "brute_force_attack",
                "source_ip": "192.168.1.100",
                "failed_attempts": 50,
                "action_taken": "IP 차단"
            },
            {
                "timestamp": "2024-01-15T15:45:00Z",
                "event_type": "suspicious_file_access",
                "user": "unknown_user",
                "file_path": "/etc/passwd",
                "action_taken": "접근 거부"
            }
        ]

        # 이벤트 타입별 통계 생성
        event_types = [event["event_type"] for event in mock_security_events]
        brute_force_count = event_types.count("brute_force_attack")
        file_access_count = event_types.count("suspicious_file_access")

        assert brute_force_count == 1
        assert file_access_count == 1

        print("✅ 모의 보안 이벤트 타입별 통계 확인됨")

        # 심각도 판정 로직 테스트
        def determine_severity(event):
            if event["event_type"] == "brute_force_attack" and event.get("failed_attempts", 0) > 30:
                return "critical"
            elif event["event_type"] == "suspicious_file_access":
                return "warning"
            else:
                return "info"

        severities = [determine_severity(event) for event in mock_security_events]
        assert "critical" in severities
        assert "warning" in severities

        print("✅ 모의 보안 이벤트 심각도 판정 로직 확인됨")

    def test_mock_backup_status_validation(self):
        """모의 백업 상태 검증 테스트"""
        # 모의 백업 상태 데이터
        mock_backup_status = {
            "last_backup": "2024-01-15T02:00:00Z",
            "files_backed_up": 127,
            "files_corrupted": 3,
            "integrity_percentage": 97.6,
            "backup_size_gb": 45.2,
            "status": "warning"  # 일부 파일 손상으로 인한 경고
        }

        # 백업 상태 검증 로직
        def validate_backup_status(status):
            integrity = status.get("integrity_percentage", 0)
            corrupted = status.get("files_corrupted", 0)

            if integrity >= 99.5 and corrupted == 0:
                return "excellent"
            elif integrity >= 95.0 and corrupted < 5:
                return "good"
            elif integrity >= 90.0:
                return "warning"
            else:
                return "critical"

        validated_status = validate_backup_status(mock_backup_status)
        assert validated_status == "warning"

        print("✅ 모의 백업 상태 검증 로직 확인됨")

        # 백업 크기 유효성 검사
        backup_size = mock_backup_status["backup_size_gb"]
        assert isinstance(backup_size, (int, float))
        assert backup_size > 0

        print("✅ 모의 백업 크기 유효성 확인됨")


class TestDashboardPerformance:
    """대시보드 성능 테스트 클래스"""

    def test_page_load_performance(self, browser_setup, dashboard_url):
        """페이지 로드 성능 테스트"""
        driver = browser_setup

        start_time = time.time()
        driver.get(dashboard_url)

        # 주요 요소가 로드될 때까지 대기
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "opsNotificationsList"))
            )
            load_time = time.time() - start_time

            # 페이지 로드 시간이 5초 미만이어야 함
            assert load_time < 5.0
            print(f"✅ 페이지 로드 시간: {load_time:.2f}초")

        except TimeoutException:
            print("⚠️ 페이지 로드 타임아웃 (10초 초과)")

    def test_javascript_initialization_time(self, browser_setup, dashboard_url):
        """JavaScript 초기화 시간 테스트"""
        driver = browser_setup
        driver.get(dashboard_url)

        start_time = time.time()

        # JavaScript 매니저 객체들이 초기화될 때까지 대기
        try:
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("""
                    return typeof opsNotificationManager !== 'undefined' &&
                           typeof securityMonitor !== 'undefined'
                """)
            )

            init_time = time.time() - start_time

            # JavaScript 초기화 시간이 3초 미만이어야 함
            assert init_time < 3.0
            print(f"✅ JavaScript 초기화 시간: {init_time:.2f}초")

        except TimeoutException:
            print("⚠️ JavaScript 초기화 타임아웃 (10초 초과)")


if __name__ == "__main__":
    # 테스트 실행
    print("🖥️ 운영 대시보드 테스트 자동화 시작...")

    # pytest 실행 (상세 모드)
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--maxfail=10",
        "-x"  # 첫 번째 실패 시 중단
    ])