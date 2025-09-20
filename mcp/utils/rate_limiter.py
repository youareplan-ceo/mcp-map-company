#!/usr/bin/env python3
"""
Rate Limiting 미들웨어
IP별 분당 요청 수 제한 및 보안 로깅
"""

import os
import time
import logging
import asyncio
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, Set
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import json


class RateLimiter:
    """IP별 Rate Limiting 및 보안 로깅 클래스"""

    def __init__(
        self,
        requests_per_minute: int = 100,
        cleanup_interval: int = 300,  # 5분마다 정리
        log_file: str = "logs/security.log"
    ):
        self.requests_per_minute = requests_per_minute
        self.cleanup_interval = cleanup_interval
        self.log_file = log_file

        # IP별 요청 시간 기록 (deque로 효율적 관리)
        self.ip_requests: Dict[str, deque] = defaultdict(deque)

        # 차단된 IP 목록 (메모리 내 관리)
        self.blocked_ips: Set[str] = set()

        # 화이트리스트 (설정 파일에서 로드)
        self.whitelist_ips: Set[str] = self._load_whitelist()

        # 마지막 정리 시간
        self.last_cleanup = time.time()

        # 로거 설정
        self._setup_logger()

    def _setup_logger(self):
        """보안 로그 설정"""
        # logs 디렉토리 생성
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

        # 보안 로거 생성
        self.security_logger = logging.getLogger('security')
        self.security_logger.setLevel(logging.INFO)

        # 파일 핸들러 (중복 방지)
        if not self.security_logger.handlers:
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            self.security_logger.addHandler(file_handler)

    def _load_whitelist(self) -> Set[str]:
        """화이트리스트 IP 로드"""
        whitelist_file = "config/whitelist_ips.json"
        default_whitelist = {"127.0.0.1", "::1", "localhost"}

        try:
            if os.path.exists(whitelist_file):
                with open(whitelist_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return set(data.get('ips', [])) | default_whitelist
        except Exception as e:
            self.security_logger.warning(f"화이트리스트 로드 실패: {e}")

        return default_whitelist

    def _cleanup_old_requests(self):
        """오래된 요청 기록 정리"""
        current_time = time.time()

        # 정리 주기 확인
        if current_time - self.last_cleanup < self.cleanup_interval:
            return

        cutoff_time = current_time - 60  # 1분 전

        # 각 IP별로 오래된 요청 제거
        for ip in list(self.ip_requests.keys()):
            requests = self.ip_requests[ip]

            # 1분 이전 요청들 제거
            while requests and requests[0] < cutoff_time:
                requests.popleft()

            # 빈 큐는 삭제
            if not requests:
                del self.ip_requests[ip]

        self.last_cleanup = current_time

    def _get_client_ip(self, request: Request) -> str:
        """클라이언트 IP 추출"""
        # Proxy 환경 고려
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()

        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip

        # 기본 클라이언트 IP
        return request.client.host if request.client else "unknown"

    def is_rate_limited(self, request: Request) -> bool:
        """Rate Limit 확인"""
        client_ip = self._get_client_ip(request)
        current_time = time.time()

        # 화이트리스트 확인
        if client_ip in self.whitelist_ips:
            return False

        # 정리 작업 수행
        self._cleanup_old_requests()

        # 현재 IP의 요청 기록
        requests = self.ip_requests[client_ip]

        # 1분 이전 요청들 제거
        cutoff_time = current_time - 60
        while requests and requests[0] < cutoff_time:
            requests.popleft()

        # 현재 요청 추가
        requests.append(current_time)

        # Rate Limit 확인
        if len(requests) > self.requests_per_minute:
            # 차단된 IP에 추가
            self.blocked_ips.add(client_ip)

            # 보안 로그 기록
            self._log_rate_limit_violation(client_ip, len(requests), request)

            return True

        return False

    def _log_rate_limit_violation(self, client_ip: str, request_count: int, request: Request):
        """Rate Limit 위반 로깅 및 알림 전송"""
        user_agent = request.headers.get('User-Agent', 'Unknown')
        endpoint = f"{request.method} {request.url.path}"

        log_data = {
            'event': 'RATE_LIMIT_EXCEEDED',
            'client_ip': client_ip,
            'request_count': request_count,
            'limit': self.requests_per_minute,
            'endpoint': endpoint,
            'user_agent': user_agent,
            'timestamp': datetime.now().isoformat()
        }

        # 보안 로그 기록
        self.security_logger.warning(
            f"Rate limit exceeded - IP: {client_ip}, "
            f"Requests: {request_count}/{self.requests_per_minute}, "
            f"Endpoint: {endpoint}, "
            f"User-Agent: {user_agent}"
        )

        # 비동기 알림 전송 (백그라운드에서 실행)
        try:
            asyncio.create_task(self._send_security_notification(
                client_ip, request_count, endpoint, user_agent
            ))
        except Exception as e:
            self.security_logger.error(f"Failed to send security notification: {e}")

    async def _send_security_notification(self, client_ip: str, request_count: int, endpoint: str, user_agent: str):
        """보안 알림 전송 (비동기)"""
        try:
            # notifier 모듈을 지연 import (순환 import 방지)
            from .notifier import send_ip_blocked_alert

            await send_ip_blocked_alert(
                client_ip=client_ip,
                violation_count=request_count,
                endpoint=endpoint,
                user_agent=user_agent
            )
        except ImportError:
            self.security_logger.warning("Notifier module not available - skipping alert")
        except Exception as e:
            self.security_logger.error(f"Failed to send IP blocked alert: {e}")

    def get_blocked_ips_summary(self) -> Dict:
        """차단된 IP 요약 정보"""
        return {
            'blocked_count': len(self.blocked_ips),
            'blocked_ips': list(self.blocked_ips),
            'whitelist_count': len(self.whitelist_ips),
            'requests_per_minute_limit': self.requests_per_minute,
            'current_monitored_ips': len(self.ip_requests)
        }

    def add_to_whitelist(self, ip: str) -> bool:
        """IP를 화이트리스트에 추가"""
        try:
            self.whitelist_ips.add(ip)

            # 차단 목록에서 제거
            if ip in self.blocked_ips:
                self.blocked_ips.remove(ip)

            # 파일에 저장
            self._save_whitelist()

            self.security_logger.info(f"IP added to whitelist: {ip}")
            return True
        except Exception as e:
            self.security_logger.error(f"Failed to add IP to whitelist: {ip}, Error: {e}")
            return False

    def _save_whitelist(self):
        """화이트리스트를 파일에 저장"""
        whitelist_file = "config/whitelist_ips.json"
        os.makedirs(os.path.dirname(whitelist_file), exist_ok=True)

        try:
            # 기본 화이트리스트 제외하고 저장
            default_whitelist = {"127.0.0.1", "::1", "localhost"}
            custom_ips = list(self.whitelist_ips - default_whitelist)

            with open(whitelist_file, 'w', encoding='utf-8') as f:
                json.dump({'ips': custom_ips}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.security_logger.error(f"Failed to save whitelist: {e}")


# 전역 Rate Limiter 인스턴스
rate_limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next):
    """FastAPI Rate Limiting 미들웨어"""

    # Rate Limit 확인
    if rate_limiter.is_rate_limited(request):
        return JSONResponse(
            status_code=429,
            content={
                "error": "Too Many Requests",
                "message": "요청 횟수가 제한을 초과했습니다. 잠시 후 다시 시도해주세요.",
                "retry_after": 60
            },
            headers={
                "Retry-After": "60",
                "X-RateLimit-Limit": str(rate_limiter.requests_per_minute),
                "X-RateLimit-Remaining": "0"
            }
        )

    # 정상 요청 처리
    response = await call_next(request)

    # Rate Limit 헤더 추가
    client_ip = rate_limiter._get_client_ip(request)
    if client_ip not in rate_limiter.whitelist_ips:
        current_requests = len(rate_limiter.ip_requests.get(client_ip, []))
        remaining = max(0, rate_limiter.requests_per_minute - current_requests)

        response.headers["X-RateLimit-Limit"] = str(rate_limiter.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

    return response


def get_security_stats() -> Dict:
    """보안 통계 API용 함수"""
    return rate_limiter.get_blocked_ips_summary()


def add_ip_to_whitelist(ip: str) -> bool:
    """IP 화이트리스트 추가 API용 함수"""
    return rate_limiter.add_to_whitelist(ip)