#!/usr/bin/env python3
"""
StockPilot 프로덕션 환경 관리자
SSL 인증서 자동 갱신, 로드 밸런싱, 백업 및 복구, 성능 벤치마크를 담당
"""

import asyncio
import aiohttp
import json
import logging
import subprocess
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import ssl
import socket
import psutil
import time
import os
import sqlite3
import tarfile
import gzip

# 로깅 설정
logger = logging.getLogger(__name__)

class ServiceHealth(Enum):
    """서비스 상태"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DOWN = "down"

class BackupType(Enum):
    """백업 타입"""
    FULL = "full"
    INCREMENTAL = "incremental"
    CONFIG = "config"
    DATABASE = "database"
    LOGS = "logs"

@dataclass
class SSLCertificateInfo:
    """SSL 인증서 정보"""
    domain: str
    cert_path: str
    key_path: str
    ca_path: Optional[str] = None
    expiry_date: Optional[datetime] = None
    days_until_expiry: int = 0
    auto_renew: bool = True
    renewal_threshold_days: int = 30

@dataclass
class ServiceEndpoint:
    """서비스 엔드포인트"""
    name: str
    url: str
    health_path: str = "/health"
    expected_status: int = 200
    timeout_seconds: int = 10
    critical: bool = True

@dataclass
class LoadBalancerConfig:
    """로드 밸런서 설정"""
    name: str
    frontend_port: int
    backend_servers: List[Dict[str, Any]]
    health_check_interval: int = 30
    max_retries: int = 3
    algorithm: str = "round_robin"  # round_robin, least_conn, ip_hash

@dataclass
class BackupConfig:
    """백업 설정"""
    name: str
    backup_type: BackupType
    source_path: str
    destination_path: str
    retention_days: int = 7
    compression: bool = True
    encryption: bool = False
    schedule_cron: str = "0 2 * * *"  # 매일 새벽 2시

@dataclass
class BenchmarkResult:
    """벤치마크 결과"""
    test_name: str
    endpoint: str
    timestamp: datetime
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    memory_usage_mb: float
    cpu_usage_percent: float

class ProductionManager:
    """프로덕션 환경 관리자"""
    
    def __init__(self, config_path: str = "config/production.json"):
        self.config_path = Path(config_path)
        self.ssl_certificates: Dict[str, SSLCertificateInfo] = {}
        self.service_endpoints: List[ServiceEndpoint] = []
        self.load_balancers: Dict[str, LoadBalancerConfig] = {}
        self.backup_configs: Dict[str, BackupConfig] = {}
        self.benchmark_history: List[BenchmarkResult] = []
        
        # 기본 경로 설정
        self.base_dir = Path("/opt/stockpilot")
        self.ssl_dir = self.base_dir / "ssl"
        self.backup_dir = self.base_dir / "backups"
        self.logs_dir = Path("/var/log/stockpilot")
        self.data_dir = self.base_dir / "data"
        
        # 디렉토리 생성
        for dir_path in [self.ssl_dir, self.backup_dir, self.logs_dir, self.data_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # 기본 설정 로드
        self._load_default_configurations()

    def _load_default_configurations(self):
        """기본 설정 로드"""
        try:
            # 기본 SSL 인증서 설정
            default_domains = ["stockpilot.ai", "api.stockpilot.ai", "dashboard.stockpilot.ai"]
            for domain in default_domains:
                self.ssl_certificates[domain] = SSLCertificateInfo(
                    domain=domain,
                    cert_path=str(self.ssl_dir / f"{domain}.crt"),
                    key_path=str(self.ssl_dir / f"{domain}.key"),
                    ca_path=str(self.ssl_dir / "ca-bundle.crt"),
                    auto_renew=True,
                    renewal_threshold_days=30
                )
            
            # 기본 서비스 엔드포인트
            self.service_endpoints = [
                ServiceEndpoint("WebSocket Server", "ws://localhost:8765", "/", 101, 5, True),
                ServiceEndpoint("Auth API", "http://localhost:8002", "/health", 200, 10, True),
                ServiceEndpoint("Dashboard API", "http://localhost:8003", "/health", 200, 10, True),
                ServiceEndpoint("Cost Dashboard API", "http://localhost:8004", "/health", 200, 10, False),
            ]
            
            # 기본 로드 밸런서 설정
            self.load_balancers["api_lb"] = LoadBalancerConfig(
                name="API Load Balancer",
                frontend_port=80,
                backend_servers=[
                    {"host": "localhost", "port": 8002, "weight": 1},
                    {"host": "localhost", "port": 8003, "weight": 1},
                    {"host": "localhost", "port": 8004, "weight": 1}
                ],
                health_check_interval=30,
                max_retries=3,
                algorithm="round_robin"
            )
            
            # 기본 백업 설정
            self.backup_configs = {
                "database_backup": BackupConfig(
                    name="Database Backup",
                    backup_type=BackupType.DATABASE,
                    source_path=str(self.data_dir),
                    destination_path=str(self.backup_dir / "database"),
                    retention_days=30,
                    compression=True,
                    schedule_cron="0 2 * * *"
                ),
                "config_backup": BackupConfig(
                    name="Configuration Backup",
                    backup_type=BackupType.CONFIG,
                    source_path="/opt/stockpilot/config",
                    destination_path=str(self.backup_dir / "config"),
                    retention_days=14,
                    compression=True,
                    schedule_cron="0 3 * * 0"  # 매주 일요일
                ),
                "logs_backup": BackupConfig(
                    name="Logs Backup",
                    backup_type=BackupType.LOGS,
                    source_path=str(self.logs_dir),
                    destination_path=str(self.backup_dir / "logs"),
                    retention_days=7,
                    compression=True,
                    schedule_cron="0 1 * * *"
                )
            }
            
            logger.info("기본 프로덕션 설정 로드 완료")
            
        except Exception as e:
            logger.error(f"기본 설정 로드 오류: {e}")

    async def check_ssl_certificates(self) -> Dict[str, Any]:
        """SSL 인증서 상태 확인"""
        try:
            certificate_status = {
                'total_certificates': len(self.ssl_certificates),
                'valid_certificates': 0,
                'expiring_soon': 0,
                'expired': 0,
                'certificates': {},
                'renewal_needed': [],
                'checked_at': datetime.now().isoformat()
            }
            
            for domain, cert_info in self.ssl_certificates.items():
                try:
                    cert_status = await self._check_single_certificate(cert_info)
                    certificate_status['certificates'][domain] = cert_status
                    
                    if cert_status['valid']:
                        certificate_status['valid_certificates'] += 1
                    
                    if cert_status['days_until_expiry'] <= 0:
                        certificate_status['expired'] += 1
                        certificate_status['renewal_needed'].append(domain)
                    elif cert_status['days_until_expiry'] <= cert_info.renewal_threshold_days:
                        certificate_status['expiring_soon'] += 1
                        if cert_info.auto_renew:
                            certificate_status['renewal_needed'].append(domain)
                    
                except Exception as e:
                    logger.error(f"인증서 {domain} 확인 오류: {e}")
                    certificate_status['certificates'][domain] = {
                        'valid': False,
                        'error': str(e),
                        'days_until_expiry': -1
                    }
            
            return certificate_status
            
        except Exception as e:
            logger.error(f"SSL 인증서 상태 확인 오류: {e}")
            return {'error': str(e)}

    async def _check_single_certificate(self, cert_info: SSLCertificateInfo) -> Dict[str, Any]:
        """단일 인증서 확인"""
        try:
            cert_path = Path(cert_info.cert_path)
            
            if not cert_path.exists():
                return {
                    'valid': False,
                    'error': 'Certificate file not found',
                    'days_until_expiry': -1
                }
            
            # OpenSSL을 사용한 인증서 정보 추출
            result = subprocess.run([
                'openssl', 'x509', '-in', str(cert_path), 
                '-noout', '-dates', '-subject'
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                return {
                    'valid': False,
                    'error': f'OpenSSL error: {result.stderr}',
                    'days_until_expiry': -1
                }
            
            # 만료일 파싱
            output_lines = result.stdout.strip().split('\n')
            expiry_line = next((line for line in output_lines if line.startswith('notAfter=')), None)
            
            if not expiry_line:
                return {
                    'valid': False,
                    'error': 'Cannot parse expiry date',
                    'days_until_expiry': -1
                }
            
            # 만료일 계산
            expiry_str = expiry_line.replace('notAfter=', '')
            try:
                expiry_date = datetime.strptime(expiry_str, '%b %d %H:%M:%S %Y %Z')
            except ValueError:
                # 다른 형식 시도
                try:
                    expiry_date = datetime.strptime(expiry_str, '%b %d %H:%M:%S %Y GMT')
                except ValueError:
                    return {
                        'valid': False,
                        'error': f'Cannot parse expiry date format: {expiry_str}',
                        'days_until_expiry': -1
                    }
            
            # 인증서 정보 업데이트
            cert_info.expiry_date = expiry_date
            cert_info.days_until_expiry = (expiry_date - datetime.now()).days
            
            return {
                'valid': cert_info.days_until_expiry > 0,
                'expiry_date': expiry_date.isoformat(),
                'days_until_expiry': cert_info.days_until_expiry,
                'auto_renew': cert_info.auto_renew
            }
            
        except Exception as e:
            logger.error(f"인증서 확인 상세 오류: {e}")
            return {
                'valid': False,
                'error': str(e),
                'days_until_expiry': -1
            }

    async def renew_ssl_certificates(self, domains: Optional[List[str]] = None) -> Dict[str, Any]:
        """SSL 인증서 갱신"""
        try:
            renewal_results = {
                'total_renewals_attempted': 0,
                'successful_renewals': 0,
                'failed_renewals': 0,
                'results': {},
                'renewed_at': datetime.now().isoformat()
            }
            
            domains_to_renew = domains if domains else list(self.ssl_certificates.keys())
            
            for domain in domains_to_renew:
                if domain not in self.ssl_certificates:
                    continue
                
                cert_info = self.ssl_certificates[domain]
                renewal_results['total_renewals_attempted'] += 1
                
                try:
                    # Let's Encrypt Certbot을 사용한 갱신
                    success = await self._renew_certificate_with_certbot(cert_info)
                    
                    if success:
                        renewal_results['successful_renewals'] += 1
                        renewal_results['results'][domain] = {
                            'status': 'success',
                            'message': '인증서 갱신 완료'
                        }
                        logger.info(f"도메인 {domain} 인증서 갱신 성공")
                    else:
                        renewal_results['failed_renewals'] += 1
                        renewal_results['results'][domain] = {
                            'status': 'failed',
                            'message': '인증서 갱신 실패'
                        }
                        logger.error(f"도메인 {domain} 인증서 갱신 실패")
                    
                except Exception as e:
                    renewal_results['failed_renewals'] += 1
                    renewal_results['results'][domain] = {
                        'status': 'error',
                        'message': str(e)
                    }
                    logger.error(f"도메인 {domain} 갱신 중 오류: {e}")
            
            return renewal_results
            
        except Exception as e:
            logger.error(f"SSL 인증서 갱신 오류: {e}")
            return {'error': str(e)}

    async def _renew_certificate_with_certbot(self, cert_info: SSLCertificateInfo) -> bool:
        """Certbot을 사용한 인증서 갱신"""
        try:
            # Certbot 갱신 명령
            cmd = [
                'certbot', 'renew',
                '--cert-name', cert_info.domain,
                '--quiet',
                '--no-self-upgrade'
            ]
            
            # 프로덕션에서는 웹서버 중단 없는 갱신 방식 사용
            if os.path.exists('/etc/nginx/nginx.conf'):
                cmd.extend(['--nginx'])
            elif os.path.exists('/etc/apache2/apache2.conf'):
                cmd.extend(['--apache'])
            else:
                # 독립 실행형 갱신
                cmd.extend(['--standalone', '--preferred-challenges', 'http'])
            
            # 갱신 실행
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Certbot 갱신 성공: {cert_info.domain}")
                return True
            else:
                logger.error(f"Certbot 갱신 실패 ({cert_info.domain}): {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Certbot 실행 오류: {e}")
            return False

    async def check_service_health(self) -> Dict[str, Any]:
        """서비스 상태 확인"""
        try:
            health_status = {
                'overall_status': ServiceHealth.HEALTHY.value,
                'total_services': len(self.service_endpoints),
                'healthy_services': 0,
                'unhealthy_services': 0,
                'services': {},
                'checked_at': datetime.now().isoformat()
            }
            
            unhealthy_critical_services = 0
            
            for endpoint in self.service_endpoints:
                try:
                    service_health = await self._check_service_endpoint(endpoint)
                    health_status['services'][endpoint.name] = service_health
                    
                    if service_health['status'] == ServiceHealth.HEALTHY.value:
                        health_status['healthy_services'] += 1
                    else:
                        health_status['unhealthy_services'] += 1
                        if endpoint.critical:
                            unhealthy_critical_services += 1
                    
                except Exception as e:
                    logger.error(f"서비스 {endpoint.name} 상태 확인 오류: {e}")
                    health_status['services'][endpoint.name] = {
                        'status': ServiceHealth.DOWN.value,
                        'error': str(e),
                        'critical': endpoint.critical
                    }
                    health_status['unhealthy_services'] += 1
                    if endpoint.critical:
                        unhealthy_critical_services += 1
            
            # 전체 상태 결정
            if unhealthy_critical_services > 0:
                health_status['overall_status'] = ServiceHealth.UNHEALTHY.value
            elif health_status['unhealthy_services'] > 0:
                health_status['overall_status'] = ServiceHealth.DEGRADED.value
            
            return health_status
            
        except Exception as e:
            logger.error(f"서비스 상태 확인 오류: {e}")
            return {'error': str(e)}

    async def _check_service_endpoint(self, endpoint: ServiceEndpoint) -> Dict[str, Any]:
        """개별 서비스 엔드포인트 확인"""
        try:
            start_time = time.time()
            
            timeout = aiohttp.ClientTimeout(total=endpoint.timeout_seconds)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                if endpoint.url.startswith('ws://') or endpoint.url.startswith('wss://'):
                    # WebSocket 연결 테스트
                    import aiohttp.client_ws
                    try:
                        async with session.ws_connect(endpoint.url) as ws:
                            await ws.ping()
                            status = ServiceHealth.HEALTHY.value
                            status_code = 101  # WebSocket 업그레이드
                    except Exception as e:
                        status = ServiceHealth.UNHEALTHY.value
                        status_code = 0
                        response_text = str(e)
                else:
                    # HTTP 요청 테스트
                    async with session.get(f"{endpoint.url}{endpoint.health_path}") as response:
                        status_code = response.status
                        response_text = await response.text()
                        
                        if status_code == endpoint.expected_status:
                            status = ServiceHealth.HEALTHY.value
                        else:
                            status = ServiceHealth.UNHEALTHY.value
            
            response_time = (time.time() - start_time) * 1000  # ms
            
            return {
                'status': status,
                'status_code': status_code,
                'response_time_ms': round(response_time, 2),
                'critical': endpoint.critical,
                'url': endpoint.url,
                'last_checked': datetime.now().isoformat()
            }
            
        except asyncio.TimeoutError:
            return {
                'status': ServiceHealth.DOWN.value,
                'error': 'Connection timeout',
                'critical': endpoint.critical,
                'url': endpoint.url,
                'last_checked': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': ServiceHealth.DOWN.value,
                'error': str(e),
                'critical': endpoint.critical,
                'url': endpoint.url,
                'last_checked': datetime.now().isoformat()
            }

    async def create_backup(self, backup_name: str) -> Dict[str, Any]:
        """백업 생성"""
        try:
            if backup_name not in self.backup_configs:
                return {'error': f'백업 설정 {backup_name}을 찾을 수 없음'}
            
            config = self.backup_configs[backup_name]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 백업 파일명 생성
            backup_filename = f"{backup_name}_{timestamp}"
            if config.compression:
                backup_filename += ".tar.gz"
            else:
                backup_filename += ".tar"
            
            destination_dir = Path(config.destination_path)
            destination_dir.mkdir(parents=True, exist_ok=True)
            backup_file_path = destination_dir / backup_filename
            
            # 백업 실행
            success = await self._execute_backup(config, backup_file_path)
            
            if success:
                # 백업 파일 검증
                if backup_file_path.exists():
                    file_size = backup_file_path.stat().st_size
                    
                    # 오래된 백업 파일 정리
                    await self._cleanup_old_backups(config)
                    
                    return {
                        'status': 'success',
                        'backup_file': str(backup_file_path),
                        'file_size_bytes': file_size,
                        'file_size_mb': round(file_size / (1024 * 1024), 2),
                        'created_at': datetime.now().isoformat(),
                        'retention_days': config.retention_days
                    }
                else:
                    return {'status': 'failed', 'error': '백업 파일이 생성되지 않음'}
            else:
                return {'status': 'failed', 'error': '백업 실행 실패'}
            
        except Exception as e:
            logger.error(f"백업 생성 오류 ({backup_name}): {e}")
            return {'status': 'error', 'error': str(e)}

    async def _execute_backup(self, config: BackupConfig, backup_file_path: Path) -> bool:
        """백업 실행"""
        try:
            source_path = Path(config.source_path)
            
            if not source_path.exists():
                logger.error(f"백업 소스 경로가 존재하지 않음: {source_path}")
                return False
            
            # tar 명령 구성
            tar_cmd = ['tar']
            
            if config.compression:
                tar_cmd.append('-czf')
            else:
                tar_cmd.append('-cf')
            
            tar_cmd.extend([str(backup_file_path), '-C', str(source_path.parent), source_path.name])
            
            # 특정 백업 타입별 추가 처리
            if config.backup_type == BackupType.DATABASE:
                # 데이터베이스 백업 전 특별 처리
                await self._prepare_database_backup(source_path)
            
            # 백업 실행
            result = subprocess.run(tar_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"백업 생성 완료: {backup_file_path}")
                return True
            else:
                logger.error(f"tar 백업 실패: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"백업 실행 오류: {e}")
            return False

    async def _prepare_database_backup(self, db_path: Path):
        """데이터베이스 백업 전 준비"""
        try:
            # SQLite 데이터베이스들에 대해 VACUUM 실행
            for db_file in db_path.glob("*.db"):
                try:
                    conn = sqlite3.connect(db_file)
                    conn.execute("VACUUM")
                    conn.close()
                    logger.info(f"데이터베이스 {db_file.name} VACUUM 완료")
                except Exception as e:
                    logger.warning(f"데이터베이스 {db_file.name} VACUUM 실패: {e}")
        except Exception as e:
            logger.error(f"데이터베이스 백업 준비 오류: {e}")

    async def _cleanup_old_backups(self, config: BackupConfig):
        """오래된 백업 파일 정리"""
        try:
            destination_dir = Path(config.destination_path)
            if not destination_dir.exists():
                return
            
            cutoff_date = datetime.now() - timedelta(days=config.retention_days)
            
            # 백업 파일 패턴 매칭
            pattern = f"{config.name.lower().replace(' ', '_')}_*"
            backup_files = list(destination_dir.glob(pattern))
            
            cleaned_files = 0
            for backup_file in backup_files:
                try:
                    file_mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    if file_mtime < cutoff_date:
                        backup_file.unlink()
                        cleaned_files += 1
                        logger.info(f"오래된 백업 파일 삭제: {backup_file.name}")
                except Exception as e:
                    logger.error(f"백업 파일 삭제 오류 ({backup_file}): {e}")
            
            if cleaned_files > 0:
                logger.info(f"{cleaned_files}개 오래된 백업 파일 정리 완료")
                
        except Exception as e:
            logger.error(f"백업 파일 정리 오류: {e}")

    async def restore_backup(self, backup_file_path: str, restore_path: Optional[str] = None) -> Dict[str, Any]:
        """백업 복원"""
        try:
            backup_file = Path(backup_file_path)
            
            if not backup_file.exists():
                return {'status': 'error', 'error': '백업 파일을 찾을 수 없음'}
            
            # 복원 경로 결정
            if restore_path:
                target_path = Path(restore_path)
            else:
                # 원본 경로로 복원 (위험하므로 확인 필요)
                target_path = self.base_dir / "restore" / datetime.now().strftime('%Y%m%d_%H%M%S')
            
            target_path.mkdir(parents=True, exist_ok=True)
            
            # tar 압축 해제
            if backup_file.suffix == '.gz':
                tar_cmd = ['tar', '-xzf', str(backup_file), '-C', str(target_path)]
            else:
                tar_cmd = ['tar', '-xf', str(backup_file), '-C', str(target_path)]
            
            result = subprocess.run(tar_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # 복원된 파일들 확인
                restored_files = list(target_path.rglob('*'))
                file_count = len([f for f in restored_files if f.is_file()])
                
                return {
                    'status': 'success',
                    'restored_to': str(target_path),
                    'restored_files': file_count,
                    'restored_at': datetime.now().isoformat()
                }
            else:
                return {
                    'status': 'failed',
                    'error': f'복원 실패: {result.stderr}'
                }
                
        except Exception as e:
            logger.error(f"백업 복원 오류: {e}")
            return {'status': 'error', 'error': str(e)}

    async def run_performance_benchmark(self, test_duration: int = 60) -> List[BenchmarkResult]:
        """성능 벤치마크 테스트 실행"""
        try:
            benchmark_results = []
            test_scenarios = [
                {
                    'name': 'API Health Check Load Test',
                    'endpoint': 'http://localhost:8002/health',
                    'concurrent_users': 10,
                    'requests_per_user': 100
                },
                {
                    'name': 'Dashboard API Load Test',
                    'endpoint': 'http://localhost:8003/health',
                    'concurrent_users': 20,
                    'requests_per_user': 50
                },
                {
                    'name': 'Cost Dashboard Stress Test',
                    'endpoint': 'http://localhost:8004/health',
                    'concurrent_users': 5,
                    'requests_per_user': 200
                }
            ]
            
            for scenario in test_scenarios:
                logger.info(f"벤치마크 테스트 시작: {scenario['name']}")
                
                try:
                    result = await self._run_single_benchmark(scenario, test_duration)
                    if result:
                        benchmark_results.append(result)
                        logger.info(f"벤치마크 테스트 완료: {scenario['name']} - "
                                  f"RPS: {result.requests_per_second:.2f}")
                except Exception as e:
                    logger.error(f"벤치마크 테스트 실패 ({scenario['name']}): {e}")
            
            # 결과를 히스토리에 저장
            self.benchmark_history.extend(benchmark_results)
            
            return benchmark_results
            
        except Exception as e:
            logger.error(f"성능 벤치마크 실행 오류: {e}")
            return []

    async def _run_single_benchmark(self, scenario: Dict[str, Any], duration: int) -> Optional[BenchmarkResult]:
        """단일 벤치마크 테스트 실행"""
        try:
            endpoint = scenario['endpoint']
            concurrent_users = scenario['concurrent_users']
            requests_per_user = scenario['requests_per_user']
            
            # 시스템 리소스 측정 시작
            process = psutil.Process()
            start_memory = process.memory_info().rss / 1024 / 1024  # MB
            start_cpu = psutil.cpu_percent(interval=1)
            start_time = time.time()
            
            # 동시 요청 실행
            response_times = []
            successful_requests = 0
            failed_requests = 0
            
            async def make_requests(session: aiohttp.ClientSession, user_id: int) -> List[float]:
                user_response_times = []
                for _ in range(requests_per_user):
                    try:
                        request_start = time.time()
                        async with session.get(endpoint, timeout=aiohttp.ClientTimeout(total=10)) as response:
                            await response.text()  # 응답 내용 읽기
                            request_time = (time.time() - request_start) * 1000  # ms
                            user_response_times.append(request_time)
                            
                            if response.status == 200:
                                nonlocal successful_requests
                                successful_requests += 1
                            else:
                                nonlocal failed_requests
                                failed_requests += 1
                    except Exception as e:
                        failed_requests += 1
                        logger.debug(f"요청 실패 (User {user_id}): {e}")
                
                return user_response_times
            
            # 동시 사용자 시뮬레이션
            async with aiohttp.ClientSession() as session:
                tasks = []
                for user_id in range(concurrent_users):
                    task = make_requests(session, user_id)
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 응답 시간 집계
                for user_times in results:
                    if isinstance(user_times, list):
                        response_times.extend(user_times)
            
            # 시스템 리소스 측정 종료
            end_time = time.time()
            end_memory = process.memory_info().rss / 1024 / 1024  # MB
            end_cpu = psutil.cpu_percent(interval=1)
            
            # 통계 계산
            if response_times:
                response_times.sort()
                total_requests = successful_requests + failed_requests
                test_duration_actual = end_time - start_time
                
                # 백분위수 계산
                p95_index = int(len(response_times) * 0.95)
                p99_index = int(len(response_times) * 0.99)
                
                result = BenchmarkResult(
                    test_name=scenario['name'],
                    endpoint=endpoint,
                    timestamp=datetime.now(),
                    total_requests=total_requests,
                    successful_requests=successful_requests,
                    failed_requests=failed_requests,
                    average_response_time=sum(response_times) / len(response_times),
                    p95_response_time=response_times[p95_index] if p95_index < len(response_times) else response_times[-1],
                    p99_response_time=response_times[p99_index] if p99_index < len(response_times) else response_times[-1],
                    requests_per_second=total_requests / test_duration_actual,
                    memory_usage_mb=max(start_memory, end_memory),
                    cpu_usage_percent=max(start_cpu, end_cpu)
                )
                
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"단일 벤치마크 실행 오류: {e}")
            return None

    async def setup_load_balancer(self, lb_name: str) -> Dict[str, Any]:
        """로드 밸런서 설정"""
        try:
            if lb_name not in self.load_balancers:
                return {'error': f'로드 밸런서 설정 {lb_name}을 찾을 수 없음'}
            
            config = self.load_balancers[lb_name]
            
            # Nginx 설정 파일 생성
            nginx_config = self._generate_nginx_config(config)
            
            # 설정 파일 저장
            nginx_conf_path = Path(f"/etc/nginx/sites-available/stockpilot_{lb_name}")
            nginx_conf_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(nginx_conf_path, 'w') as f:
                f.write(nginx_config)
            
            # 심볼릭 링크 생성
            nginx_enabled_path = Path(f"/etc/nginx/sites-enabled/stockpilot_{lb_name}")
            if not nginx_enabled_path.exists():
                nginx_enabled_path.symlink_to(nginx_conf_path)
            
            # Nginx 설정 테스트
            test_result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
            
            if test_result.returncode == 0:
                # Nginx 재로드
                reload_result = subprocess.run(['systemctl', 'reload', 'nginx'], capture_output=True, text=True)
                
                if reload_result.returncode == 0:
                    return {
                        'status': 'success',
                        'message': f'로드 밸런서 {lb_name} 설정 완료',
                        'config_file': str(nginx_conf_path),
                        'frontend_port': config.frontend_port,
                        'backend_servers': len(config.backend_servers)
                    }
                else:
                    return {
                        'status': 'failed',
                        'error': f'Nginx 재로드 실패: {reload_result.stderr}'
                    }
            else:
                return {
                    'status': 'failed',
                    'error': f'Nginx 설정 테스트 실패: {test_result.stderr}'
                }
                
        except Exception as e:
            logger.error(f"로드 밸런서 설정 오류 ({lb_name}): {e}")
            return {'status': 'error', 'error': str(e)}

    def _generate_nginx_config(self, config: LoadBalancerConfig) -> str:
        """Nginx 설정 파일 생성"""
        upstream_servers = []
        for server in config.backend_servers:
            weight = server.get('weight', 1)
            upstream_servers.append(f"    server {server['host']}:{server['port']} weight={weight};")
        
        upstream_block = '\n'.join(upstream_servers)
        
        nginx_config = f"""
upstream stockpilot_backend_{config.name.lower().replace(' ', '_')} {{
    {config.algorithm};
{upstream_block}
    
    # 헬스 체크 설정
    keepalive 32;
}}

server {{
    listen {config.frontend_port};
    server_name stockpilot.ai *.stockpilot.ai;
    
    # 보안 헤더
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
    
    # 로깅
    access_log /var/log/nginx/stockpilot_access.log;
    error_log /var/log/nginx/stockpilot_error.log;
    
    # 프록시 설정
    location / {{
        proxy_pass http://stockpilot_backend_{config.name.lower().replace(' ', '_')};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 타임아웃 설정
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        
        # 버퍼링 설정
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        
        # HTTP/1.1 지원
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }}
    
    # 헬스 체크 엔드포인트
    location /nginx-health {{
        access_log off;
        return 200 "healthy\\n";
        add_header Content-Type text/plain;
    }}
    
    # 정적 파일 캐싱
    location ~* \\.(js|css|png|jpg|jpeg|gif|ico|svg)$ {{
        expires 1y;
        add_header Cache-Control "public, immutable";
    }}
}}
"""
        
        return nginx_config

    async def get_production_status(self) -> Dict[str, Any]:
        """프로덕션 환경 전체 상태 조회"""
        try:
            status = {
                'timestamp': datetime.now().isoformat(),
                'ssl_certificates': await self.check_ssl_certificates(),
                'service_health': await self.check_service_health(),
                'system_resources': self._get_system_resources(),
                'disk_usage': self._get_disk_usage(),
                'recent_backups': await self._get_recent_backup_info(),
                'benchmark_summary': self._get_benchmark_summary(),
                'uptime': self._get_system_uptime()
            }
            
            return status
            
        except Exception as e:
            logger.error(f"프로덕션 상태 조회 오류: {e}")
            return {'error': str(e)}

    def _get_system_resources(self) -> Dict[str, Any]:
        """시스템 리소스 정보"""
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            
            return {
                'cpu_percent': cpu_percent,
                'memory_total_gb': round(memory.total / (1024**3), 2),
                'memory_used_gb': round(memory.used / (1024**3), 2),
                'memory_percent': memory.percent,
                'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else None
            }
        except Exception as e:
            logger.error(f"시스템 리소스 조회 오류: {e}")
            return {'error': str(e)}

    def _get_disk_usage(self) -> Dict[str, Any]:
        """디스크 사용량 정보"""
        try:
            disk_info = {}
            
            # 주요 경로들의 디스크 사용량 확인
            important_paths = [
                ('/', 'Root'),
                ('/opt/stockpilot', 'Application'),
                ('/var/log', 'Logs'),
                ('/tmp', 'Temporary')
            ]
            
            for path, name in important_paths:
                if os.path.exists(path):
                    usage = shutil.disk_usage(path)
                    disk_info[name.lower()] = {
                        'total_gb': round(usage.total / (1024**3), 2),
                        'used_gb': round(usage.used / (1024**3), 2),
                        'free_gb': round(usage.free / (1024**3), 2),
                        'percent_used': round((usage.used / usage.total) * 100, 1)
                    }
            
            return disk_info
            
        except Exception as e:
            logger.error(f"디스크 사용량 조회 오류: {e}")
            return {'error': str(e)}

    async def _get_recent_backup_info(self) -> Dict[str, Any]:
        """최근 백업 정보"""
        try:
            backup_info = {}
            
            for backup_name, config in self.backup_configs.items():
                destination_dir = Path(config.destination_path)
                if destination_dir.exists():
                    backup_files = list(destination_dir.glob(f"{backup_name.lower().replace(' ', '_')}_*"))
                    backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    
                    if backup_files:
                        latest_backup = backup_files[0]
                        backup_info[backup_name] = {
                            'latest_backup': latest_backup.name,
                            'backup_date': datetime.fromtimestamp(latest_backup.stat().st_mtime).isoformat(),
                            'file_size_mb': round(latest_backup.stat().st_size / (1024*1024), 2),
                            'total_backups': len(backup_files)
                        }
                    else:
                        backup_info[backup_name] = {
                            'status': 'no_backups_found'
                        }
                else:
                    backup_info[backup_name] = {
                        'status': 'backup_directory_not_found'
                    }
            
            return backup_info
            
        except Exception as e:
            logger.error(f"백업 정보 조회 오류: {e}")
            return {'error': str(e)}

    def _get_benchmark_summary(self) -> Dict[str, Any]:
        """벤치마크 요약 정보"""
        try:
            if not self.benchmark_history:
                return {'status': 'no_benchmarks_run'}
            
            recent_benchmarks = sorted(self.benchmark_history, key=lambda x: x.timestamp, reverse=True)[:10]
            
            summary = {
                'total_benchmarks_run': len(self.benchmark_history),
                'latest_benchmark_date': recent_benchmarks[0].timestamp.isoformat(),
                'average_rps': round(sum(b.requests_per_second for b in recent_benchmarks) / len(recent_benchmarks), 2),
                'average_response_time_ms': round(sum(b.average_response_time for b in recent_benchmarks) / len(recent_benchmarks), 2),
                'success_rate_percent': round(sum(b.successful_requests / max(b.total_requests, 1) for b in recent_benchmarks) / len(recent_benchmarks) * 100, 1)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"벤치마크 요약 조회 오류: {e}")
            return {'error': str(e)}

    def _get_system_uptime(self) -> Dict[str, Any]:
        """시스템 가동시간"""
        try:
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            uptime_days = int(uptime_seconds // 86400)
            uptime_hours = int((uptime_seconds % 86400) // 3600)
            uptime_minutes = int((uptime_seconds % 3600) // 60)
            
            return {
                'uptime_seconds': int(uptime_seconds),
                'uptime_formatted': f"{uptime_days}일 {uptime_hours}시간 {uptime_minutes}분",
                'boot_time': datetime.fromtimestamp(boot_time).isoformat()
            }
            
        except Exception as e:
            logger.error(f"시스템 가동시간 조회 오류: {e}")
            return {'error': str(e)}

# 전역 프로덕션 매니저 인스턴스
production_manager = None

def get_production_manager() -> ProductionManager:
    """프로덕션 매니저 인스턴스 가져오기"""
    global production_manager
    if production_manager is None:
        production_manager = ProductionManager()
    return production_manager

async def run_production_health_check():
    """프로덕션 환경 상태 점검 실행"""
    try:
        manager = get_production_manager()
        
        logger.info("🔍 프로덕션 환경 상태 점검 시작")
        
        # SSL 인증서 확인
        ssl_status = await manager.check_ssl_certificates()
        if ssl_status.get('renewal_needed'):
            logger.warning(f"갱신 필요한 SSL 인증서: {ssl_status['renewal_needed']}")
            await manager.renew_ssl_certificates(ssl_status['renewal_needed'])
        
        # 서비스 상태 확인
        service_status = await manager.check_service_health()
        if service_status.get('overall_status') != 'healthy':
            logger.warning(f"서비스 상태 이상: {service_status['overall_status']}")
        
        # 전체 상태 리포트
        full_status = await manager.get_production_status()
        logger.info(f"✅ 프로덕션 환경 점검 완료 - SSL: {ssl_status.get('valid_certificates', 0)}개, 서비스: {service_status.get('healthy_services', 0)}개")
        
        return full_status
        
    except Exception as e:
        logger.error(f"프로덕션 상태 점검 오류: {e}")
        return {'error': str(e)}

if __name__ == "__main__":
    asyncio.run(run_production_health_check())