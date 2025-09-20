#!/usr/bin/env python3
"""
시스템 자원 모니터링 API
psutil을 사용하여 CPU, 메모리, 디스크, 네트워크 사용률 정보 제공
"""

import psutil
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

# 로거 설정
logger = logging.getLogger(__name__)

# FastAPI 라우터 생성
router = APIRouter(
    prefix="/api/v1/metrics",
    tags=["system-metrics"],
    responses={404: {"description": "Not found"}}
)


class SystemMetricsCollector:
    """시스템 메트릭 수집 클래스"""

    def __init__(self):
        # 네트워크 I/O 측정을 위한 이전 값 저장
        self._last_network_io = None
        self._last_disk_io = None
        self._last_measurement_time = None

        # 시스템 정보 캐시
        self._system_info_cache = None
        self._cache_expiry = 0

    def _get_cpu_usage(self) -> float:
        """CPU 사용률 반환 (퍼센트)"""
        try:
            # 1초 간격으로 CPU 사용률 측정 (더 정확한 값)
            return psutil.cpu_percent(interval=1.0)
        except Exception as e:
            logger.error(f"CPU 사용률 측정 오류: {e}")
            return 0.0

    def _get_memory_usage(self) -> Dict[str, float]:
        """메모리 사용률 정보 반환"""
        try:
            memory = psutil.virtual_memory()
            return {
                'percent': memory.percent,
                'total_gb': round(memory.total / (1024**3), 2),
                'used_gb': round(memory.used / (1024**3), 2),
                'available_gb': round(memory.available / (1024**3), 2)
            }
        except Exception as e:
            logger.error(f"메모리 사용률 측정 오류: {e}")
            return {'percent': 0.0, 'total_gb': 0.0, 'used_gb': 0.0, 'available_gb': 0.0}

    def _get_disk_usage(self) -> Dict[str, Any]:
        """디스크 사용률 정보 반환"""
        try:
            # 루트 파티션 정보 가져오기
            disk_usage = psutil.disk_usage('/')

            # 디스크 I/O 통계
            disk_io = psutil.disk_io_counters()

            # I/O 속도 계산 (이전 측정값과 비교)
            io_speed = {'read_mb_s': 0.0, 'write_mb_s': 0.0}
            current_time = time.time()

            if self._last_disk_io and self._last_measurement_time:
                time_diff = current_time - self._last_measurement_time
                if time_diff > 0:
                    read_diff = disk_io.read_bytes - self._last_disk_io.read_bytes
                    write_diff = disk_io.write_bytes - self._last_disk_io.write_bytes

                    io_speed['read_mb_s'] = round((read_diff / time_diff) / (1024**2), 2)
                    io_speed['write_mb_s'] = round((write_diff / time_diff) / (1024**2), 2)

            # 이전 값 저장
            self._last_disk_io = disk_io

            return {
                'percent': round((disk_usage.used / disk_usage.total) * 100, 1),
                'total_gb': round(disk_usage.total / (1024**3), 2),
                'used_gb': round(disk_usage.used / (1024**3), 2),
                'free_gb': round(disk_usage.free / (1024**3), 2),
                'io_speed': io_speed
            }
        except Exception as e:
            logger.error(f"디스크 사용률 측정 오류: {e}")
            return {
                'percent': 0.0,
                'total_gb': 0.0,
                'used_gb': 0.0,
                'free_gb': 0.0,
                'io_speed': {'read_mb_s': 0.0, 'write_mb_s': 0.0}
            }

    def _get_network_io(self) -> Dict[str, float]:
        """네트워크 I/O 속도 반환 (MB/s)"""
        try:
            network_io = psutil.net_io_counters()
            current_time = time.time()

            network_speed = {'in': 0.0, 'out': 0.0}

            if self._last_network_io and self._last_measurement_time:
                time_diff = current_time - self._last_measurement_time
                if time_diff > 0:
                    bytes_recv_diff = network_io.bytes_recv - self._last_network_io.bytes_recv
                    bytes_sent_diff = network_io.bytes_sent - self._last_network_io.bytes_sent

                    # MB/s로 변환
                    network_speed['in'] = round((bytes_recv_diff / time_diff) / (1024**2), 2)
                    network_speed['out'] = round((bytes_sent_diff / time_diff) / (1024**2), 2)

            # 이전 값 저장
            self._last_network_io = network_io
            self._last_measurement_time = current_time

            return network_speed
        except Exception as e:
            logger.error(f"네트워크 I/O 측정 오류: {e}")
            return {'in': 0.0, 'out': 0.0}

    def _get_system_info(self) -> Dict[str, Any]:
        """시스템 정보 반환 (캐시 사용)"""
        try:
            current_time = time.time()

            # 캐시 만료 확인 (60초)
            if self._system_info_cache and current_time < self._cache_expiry:
                return self._system_info_cache

            # 시스템 부팅 시간
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time

            # 프로세스 개수
            process_count = len(psutil.pids())

            # 시스템 부하 (Unix 시스템에서만 사용 가능)
            try:
                load_avg = psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0.0
            except (AttributeError, OSError):
                load_avg = 0.0

            # 시스템 건강도 계산 (간단한 점수 시스템)
            cpu_score = max(0, 100 - psutil.cpu_percent(interval=0.1))
            memory_score = max(0, 100 - psutil.virtual_memory().percent)
            disk_score = max(0, 100 - (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100)
            health_score = round((cpu_score + memory_score + disk_score) / 3, 1)

            system_info = {
                'uptime_seconds': int(uptime.total_seconds()),
                'uptime_string': str(uptime).split('.')[0],  # 소수점 제거
                'boot_time': boot_time.isoformat(),
                'process_count': process_count,
                'load_average': round(load_avg, 2),
                'health_score': health_score,
                'cpu_count': psutil.cpu_count(),
                'cpu_count_logical': psutil.cpu_count(logical=True)
            }

            # 캐시 업데이트
            self._system_info_cache = system_info
            self._cache_expiry = current_time + 60  # 60초 후 만료

            return system_info
        except Exception as e:
            logger.error(f"시스템 정보 수집 오류: {e}")
            return {
                'uptime_seconds': 0,
                'uptime_string': '알 수 없음',
                'boot_time': datetime.now().isoformat(),
                'process_count': 0,
                'load_average': 0.0,
                'health_score': 50.0,
                'cpu_count': 1,
                'cpu_count_logical': 1
            }

    def get_all_metrics(self) -> Dict[str, Any]:
        """모든 시스템 메트릭을 수집하여 반환"""
        try:
            logger.info("시스템 메트릭 수집 시작")

            # 각 메트릭 수집
            cpu_usage = self._get_cpu_usage()
            memory_info = self._get_memory_usage()
            disk_info = self._get_disk_usage()
            network_info = self._get_network_io()
            system_info = self._get_system_info()

            # 통합된 응답 데이터 구성
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'cpu': cpu_usage,
                'memory': memory_info['percent'],
                'disk': disk_info['percent'],
                'network': network_info,
                'detailed': {
                    'memory': memory_info,
                    'disk': disk_info,
                    'system': system_info
                }
            }

            logger.info(f"시스템 메트릭 수집 완료 - CPU: {cpu_usage}%, 메모리: {memory_info['percent']}%, 디스크: {disk_info['percent']}%")
            return metrics

        except Exception as e:
            logger.error(f"시스템 메트릭 수집 중 오류 발생: {e}")
            raise HTTPException(status_code=500, detail=f"시스템 메트릭 수집 오류: {str(e)}")


# 시스템 메트릭 수집기 인스턴스
metrics_collector = SystemMetricsCollector()


@router.get("/system")
async def get_system_metrics() -> Dict[str, Any]:
    """
    시스템 자원 사용률 정보를 반환하는 API 엔드포인트

    Returns:
        Dict: CPU, 메모리, 디스크, 네트워크 사용률 정보
    """
    try:
        metrics = metrics_collector.get_all_metrics()
        return metrics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"시스템 메트릭 API 오류: {e}")
        raise HTTPException(status_code=500, detail="시스템 메트릭 조회 실패")


@router.get("/system/cpu")
async def get_cpu_metrics() -> Dict[str, Any]:
    """CPU 사용률 정보만 반환"""
    try:
        cpu_usage = metrics_collector._get_cpu_usage()
        return {
            'timestamp': datetime.now().isoformat(),
            'cpu_percent': cpu_usage,
            'cpu_count': psutil.cpu_count(),
            'cpu_count_logical': psutil.cpu_count(logical=True)
        }
    except Exception as e:
        logger.error(f"CPU 메트릭 API 오류: {e}")
        raise HTTPException(status_code=500, detail="CPU 메트릭 조회 실패")


@router.get("/system/memory")
async def get_memory_metrics() -> Dict[str, Any]:
    """메모리 사용률 정보만 반환"""
    try:
        memory_info = metrics_collector._get_memory_usage()
        return {
            'timestamp': datetime.now().isoformat(),
            **memory_info
        }
    except Exception as e:
        logger.error(f"메모리 메트릭 API 오류: {e}")
        raise HTTPException(status_code=500, detail="메모리 메트릭 조회 실패")


@router.get("/system/disk")
async def get_disk_metrics() -> Dict[str, Any]:
    """디스크 사용률 정보만 반환"""
    try:
        disk_info = metrics_collector._get_disk_usage()
        return {
            'timestamp': datetime.now().isoformat(),
            **disk_info
        }
    except Exception as e:
        logger.error(f"디스크 메트릭 API 오류: {e}")
        raise HTTPException(status_code=500, detail="디스크 메트릭 조회 실패")


@router.get("/system/network")
async def get_network_metrics() -> Dict[str, Any]:
    """네트워크 I/O 정보만 반환"""
    try:
        network_info = metrics_collector._get_network_io()
        return {
            'timestamp': datetime.now().isoformat(),
            **network_info
        }
    except Exception as e:
        logger.error(f"네트워크 메트릭 API 오류: {e}")
        raise HTTPException(status_code=500, detail="네트워크 메트릭 조회 실패")


@router.get("/health")
async def get_metrics_health() -> Dict[str, Any]:
    """메트릭 API 상태 확인"""
    try:
        # 간단한 메트릭 수집 테스트
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory_usage = psutil.virtual_memory().percent

        return {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'message': '시스템 메트릭 API가 정상 작동 중입니다',
            'quick_check': {
                'cpu_percent': cpu_usage,
                'memory_percent': memory_usage,
                'psutil_version': psutil.__version__
            }
        }
    except Exception as e:
        logger.error(f"메트릭 헬스체크 오류: {e}")
        raise HTTPException(status_code=503, detail=f"시스템 메트릭 서비스 이용 불가: {str(e)}")


def get_metrics_router() -> APIRouter:
    """시스템 메트릭 라우터 반환"""
    return router