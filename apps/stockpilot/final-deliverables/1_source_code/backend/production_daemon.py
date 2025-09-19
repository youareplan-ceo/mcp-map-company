#!/usr/bin/env python3
"""
StockPilot 프로덕션 관리 데몬
SSL 갱신, 백업, 성능 모니터링, 로드 밸런싱을 자동으로 관리하는 백그라운드 서비스
"""

import asyncio
import signal
import sys
import os
import logging
import schedule
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.production_manager import get_production_manager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/stockpilot/production_daemon.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ProductionDaemon:
    """프로덕션 관리 데몬"""
    
    def __init__(self):
        self.running = False
        self.production_manager = get_production_manager()
        self.daemon_stats = {
            'start_time': datetime.now(),
            'ssl_renewals': 0,
            'backups_created': 0,
            'benchmarks_run': 0,
            'health_checks': 0,
            'errors': 0
        }
        
        # 알림 설정
        self.alert_thresholds = {
            'cpu_percent': 85.0,
            'memory_percent': 90.0,
            'disk_percent': 95.0,
            'service_down_critical': True,
            'ssl_expiry_days': 30,
            'backup_age_hours': 48
        }

    async def setup(self):
        """데몬 초기화"""
        try:
            # 로그 디렉토리 생성
            log_dir = Path("/var/log/stockpilot")
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # 스케줄 설정
            self._setup_schedules()
            
            logger.info("프로덕션 관리 데몬 초기화 완료")
            return True
            
        except Exception as e:
            logger.error(f"데몬 초기화 실패: {e}")
            return False

    def _setup_schedules(self):
        """작업 스케줄 설정"""
        try:
            # SSL 인증서 체크 (매일 오전 6시)
            schedule.every().day.at("06:00").do(
                self._schedule_ssl_check,
                "SSL 인증서 체크 및 갱신"
            )
            
            # 서비스 헬스 체크 (매 5분)
            schedule.every(5).minutes.do(
                self._schedule_health_check,
                "서비스 헬스 체크"
            )
            
            # 전체 백업 (매일 새벽 2시)
            schedule.every().day.at("02:00").do(
                self._schedule_backup,
                "전체 시스템 백업"
            )
            
            # 증분 백업 (매 6시간)
            schedule.every(6).hours.do(
                self._schedule_incremental_backup,
                "증분 백업"
            )
            
            # 성능 벤치마크 (매일 오전 4시)
            schedule.every().day.at("04:00").do(
                self._schedule_benchmark,
                "성능 벤치마크 테스트"
            )
            
            # 시스템 리소스 모니터링 (매 1분)
            schedule.every(1).minutes.do(
                self._schedule_resource_monitor,
                "시스템 리소스 모니터링"
            )
            
            # 로그 로테이션 (매일 자정)
            schedule.every().day.at("00:00").do(
                self._schedule_log_rotation,
                "로그 파일 로테이션"
            )
            
            # 주간 종합 리포트 (매주 월요일 오전 9시)
            schedule.every().monday.at("09:00").do(
                self._schedule_weekly_report,
                "주간 종합 리포트"
            )
            
            logger.info(f"{len(schedule.jobs)}개 작업 스케줄 설정 완료")
            
        except Exception as e:
            logger.error(f"스케줄 설정 오류: {e}")

    def _schedule_ssl_check(self, task_name: str):
        """SSL 인증서 체크 스케줄"""
        try:
            asyncio.create_task(self._execute_ssl_check(task_name))
        except Exception as e:
            logger.error(f"{task_name} 스케줄링 오류: {e}")

    def _schedule_health_check(self, task_name: str):
        """헬스 체크 스케줄"""
        try:
            asyncio.create_task(self._execute_health_check(task_name))
        except Exception as e:
            logger.error(f"{task_name} 스케줄링 오류: {e}")

    def _schedule_backup(self, task_name: str):
        """백업 스케줄"""
        try:
            asyncio.create_task(self._execute_full_backup(task_name))
        except Exception as e:
            logger.error(f"{task_name} 스케줄링 오류: {e}")

    def _schedule_incremental_backup(self, task_name: str):
        """증분 백업 스케줄"""
        try:
            asyncio.create_task(self._execute_incremental_backup(task_name))
        except Exception as e:
            logger.error(f"{task_name} 스케줄링 오류: {e}")

    def _schedule_benchmark(self, task_name: str):
        """벤치마크 스케줄"""
        try:
            asyncio.create_task(self._execute_benchmark(task_name))
        except Exception as e:
            logger.error(f"{task_name} 스케줄링 오류: {e}")

    def _schedule_resource_monitor(self, task_name: str):
        """리소스 모니터링 스케줄"""
        try:
            asyncio.create_task(self._execute_resource_monitor(task_name))
        except Exception as e:
            logger.error(f"{task_name} 스케줄링 오류: {e}")

    def _schedule_log_rotation(self, task_name: str):
        """로그 로테이션 스케줄"""
        try:
            asyncio.create_task(self._execute_log_rotation(task_name))
        except Exception as e:
            logger.error(f"{task_name} 스케줄링 오류: {e}")

    def _schedule_weekly_report(self, task_name: str):
        """주간 리포트 스케줄"""
        try:
            asyncio.create_task(self._execute_weekly_report(task_name))
        except Exception as e:
            logger.error(f"{task_name} 스케줄링 오류: {e}")

    async def _execute_ssl_check(self, task_name: str):
        """SSL 인증서 체크 및 갱신 실행"""
        try:
            logger.info(f"🔒 {task_name} 시작")
            start_time = datetime.now()
            
            # SSL 인증서 상태 확인
            ssl_status = await self.production_manager.check_ssl_certificates()
            
            renewal_needed = ssl_status.get('renewal_needed', [])
            expiring_soon = ssl_status.get('expiring_soon', 0)
            expired = ssl_status.get('expired', 0)
            
            # 갱신 필요한 인증서 처리
            if renewal_needed:
                logger.info(f"갱신 필요한 인증서 {len(renewal_needed)}개 발견: {', '.join(renewal_needed)}")
                
                renewal_result = await self.production_manager.renew_ssl_certificates(renewal_needed)
                
                successful_renewals = renewal_result.get('successful_renewals', 0)
                failed_renewals = renewal_result.get('failed_renewals', 0)
                
                self.daemon_stats['ssl_renewals'] += successful_renewals
                
                if failed_renewals > 0:
                    await self._send_alert(
                        "SSL 인증서 갱신 실패",
                        f"{failed_renewals}개 인증서 갱신 실패. 즉시 확인 필요.",
                        "critical"
                    )
                
                logger.info(f"SSL 갱신 완료 - 성공: {successful_renewals}, 실패: {failed_renewals}")
            
            # 만료 임박 경고
            if expiring_soon > 0:
                await self._send_alert(
                    "SSL 인증서 만료 임박",
                    f"{expiring_soon}개 인증서가 {self.alert_thresholds['ssl_expiry_days']}일 내 만료 예정",
                    "warning"
                )
            
            # 만료된 인증서 경고
            if expired > 0:
                await self._send_alert(
                    "SSL 인증서 만료",
                    f"{expired}개 인증서가 이미 만료됨. 즉시 조치 필요.",
                    "critical"
                )
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ {task_name} 완료 - 소요시간: {duration:.1f}초")
            
        except Exception as e:
            logger.error(f"{task_name} 실행 오류: {e}")
            self.daemon_stats['errors'] += 1
            await self._send_alert(
                "SSL 체크 시스템 오류",
                f"SSL 인증서 체크 중 오류 발생: {str(e)}",
                "error"
            )

    async def _execute_health_check(self, task_name: str):
        """서비스 헬스 체크 실행"""
        try:
            logger.debug(f"💓 {task_name} 시작")
            
            # 서비스 상태 확인
            health_status = await self.production_manager.check_service_health()
            
            self.daemon_stats['health_checks'] += 1
            
            overall_status = health_status.get('overall_status')
            unhealthy_services = health_status.get('unhealthy_services', 0)
            
            # 서비스 상태 이상 시 알림
            if overall_status == 'unhealthy':
                critical_services = []
                for service_name, service_info in health_status.get('services', {}).items():
                    if service_info.get('status') != 'healthy' and service_info.get('critical'):
                        critical_services.append(service_name)
                
                if critical_services:
                    await self._send_alert(
                        "중요 서비스 장애",
                        f"중요 서비스 장애 발생: {', '.join(critical_services)}",
                        "critical"
                    )
            
            elif overall_status == 'degraded':
                await self._send_alert(
                    "서비스 성능 저하",
                    f"{unhealthy_services}개 서비스에서 문제 감지됨",
                    "warning"
                )
            
            logger.debug(f"✅ {task_name} 완료 - 상태: {overall_status}")
            
        except Exception as e:
            logger.error(f"{task_name} 실행 오류: {e}")
            self.daemon_stats['errors'] += 1

    async def _execute_full_backup(self, task_name: str):
        """전체 백업 실행"""
        try:
            logger.info(f"💾 {task_name} 시작")
            start_time = datetime.now()
            
            backup_results = []
            backup_configs = ["database_backup", "config_backup", "logs_backup"]
            
            for backup_name in backup_configs:
                try:
                    result = await self.production_manager.create_backup(backup_name)
                    backup_results.append(result)
                    
                    if result.get('status') == 'success':
                        logger.info(f"백업 생성 성공: {backup_name} - {result.get('file_size_mb')}MB")
                    else:
                        logger.error(f"백업 생성 실패: {backup_name} - {result.get('error')}")
                        
                except Exception as e:
                    logger.error(f"백업 {backup_name} 실행 오류: {e}")
                    backup_results.append({'status': 'error', 'error': str(e)})
            
            # 백업 결과 집계
            successful_backups = sum(1 for r in backup_results if r.get('status') == 'success')
            failed_backups = len(backup_results) - successful_backups
            
            self.daemon_stats['backups_created'] += successful_backups
            
            if failed_backups > 0:
                await self._send_alert(
                    "백업 실패",
                    f"{failed_backups}개 백업 실패. 데이터 보호에 문제가 있을 수 있음.",
                    "warning"
                )
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ {task_name} 완료 - 성공: {successful_backups}, 실패: {failed_backups}, 소요시간: {duration:.1f}초")
            
        except Exception as e:
            logger.error(f"{task_name} 실행 오류: {e}")
            self.daemon_stats['errors'] += 1
            await self._send_alert(
                "백업 시스템 오류",
                f"백업 프로세스 중 오류 발생: {str(e)}",
                "error"
            )

    async def _execute_incremental_backup(self, task_name: str):
        """증분 백업 실행"""
        try:
            logger.debug(f"📁 {task_name} 시작")
            
            # 데이터베이스만 증분 백업
            result = await self.production_manager.create_backup("database_backup")
            
            if result.get('status') == 'success':
                logger.debug(f"증분 백업 완료: {result.get('file_size_mb')}MB")
                self.daemon_stats['backups_created'] += 1
            else:
                logger.warning(f"증분 백업 실패: {result.get('error')}")
            
        except Exception as e:
            logger.error(f"{task_name} 실행 오류: {e}")
            self.daemon_stats['errors'] += 1

    async def _execute_benchmark(self, task_name: str):
        """성능 벤치마크 실행"""
        try:
            logger.info(f"📊 {task_name} 시작")
            start_time = datetime.now()
            
            # 성능 벤치마크 실행
            benchmark_results = await self.production_manager.run_performance_benchmark(duration=30)
            
            if benchmark_results:
                self.daemon_stats['benchmarks_run'] += len(benchmark_results)
                
                # 성능 지표 분석
                avg_rps = sum(r.requests_per_second for r in benchmark_results) / len(benchmark_results)
                avg_response_time = sum(r.average_response_time for r in benchmark_results) / len(benchmark_results)
                success_rate = sum(r.successful_requests / max(r.total_requests, 1) for r in benchmark_results) / len(benchmark_results)
                
                # 성능 저하 감지
                if success_rate < 0.95:  # 95% 미만
                    await self._send_alert(
                        "성능 저하 감지",
                        f"성공률 {success_rate*100:.1f}% (임계값: 95%)",
                        "warning"
                    )
                
                if avg_response_time > 2000:  # 2초 초과
                    await self._send_alert(
                        "응답 시간 지연",
                        f"평균 응답시간 {avg_response_time:.1f}ms (임계값: 2000ms)",
                        "warning"
                    )
                
                logger.info(f"벤치마크 완료 - RPS: {avg_rps:.1f}, 응답시간: {avg_response_time:.1f}ms, 성공률: {success_rate*100:.1f}%")
            else:
                logger.warning("벤치마크 결과가 없음")
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ {task_name} 완료 - 소요시간: {duration:.1f}초")
            
        except Exception as e:
            logger.error(f"{task_name} 실행 오류: {e}")
            self.daemon_stats['errors'] += 1

    async def _execute_resource_monitor(self, task_name: str):
        """시스템 리소스 모니터링 실행"""
        try:
            # 전체 프로덕션 상태 조회
            status = await self.production_manager.get_production_status()
            
            if 'error' in status:
                return
            
            # 시스템 리소스 확인
            system_resources = status.get('system_resources', {})
            disk_usage = status.get('disk_usage', {})
            
            # CPU 사용률 체크
            cpu_percent = system_resources.get('cpu_percent', 0)
            if cpu_percent > self.alert_thresholds['cpu_percent']:
                await self._send_alert(
                    "CPU 사용률 높음",
                    f"CPU 사용률 {cpu_percent:.1f}% (임계값: {self.alert_thresholds['cpu_percent']}%)",
                    "warning"
                )
            
            # 메모리 사용률 체크
            memory_percent = system_resources.get('memory_percent', 0)
            if memory_percent > self.alert_thresholds['memory_percent']:
                await self._send_alert(
                    "메모리 사용률 높음",
                    f"메모리 사용률 {memory_percent:.1f}% (임계값: {self.alert_thresholds['memory_percent']}%)",
                    "warning"
                )
            
            # 디스크 사용률 체크
            for disk_name, disk_info in disk_usage.items():
                disk_percent = disk_info.get('percent_used', 0)
                if disk_percent > self.alert_thresholds['disk_percent']:
                    await self._send_alert(
                        f"디스크 사용률 위험 - {disk_name}",
                        f"{disk_name} 디스크 사용률 {disk_percent:.1f}% (임계값: {self.alert_thresholds['disk_percent']}%)",
                        "critical"
                    )
            
            logger.debug(f"리소스 모니터링 완료 - CPU: {cpu_percent:.1f}%, 메모리: {memory_percent:.1f}%")
            
        except Exception as e:
            logger.debug(f"리소스 모니터링 오류: {e}")

    async def _execute_log_rotation(self, task_name: str):
        """로그 파일 로테이션 실행"""
        try:
            logger.info(f"📋 {task_name} 시작")
            
            # logrotate 실행
            import subprocess
            result = subprocess.run(['logrotate', '/etc/logrotate.d/stockpilot'], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("로그 파일 로테이션 완료")
            else:
                logger.warning(f"로그 로테이션 경고: {result.stderr}")
            
        except Exception as e:
            logger.error(f"{task_name} 실행 오류: {e}")

    async def _execute_weekly_report(self, task_name: str):
        """주간 종합 리포트 생성"""
        try:
            logger.info(f"📈 {task_name} 시작")
            
            # 전체 상태 조회
            status = await self.production_manager.get_production_status()
            uptime = self.daemon_stats['start_time']
            uptime_days = (datetime.now() - uptime).days
            
            # 주간 리포트 생성
            report = f"""
📊 StockPilot 프로덕션 주간 리포트 ({datetime.now().strftime('%Y-%m-%d')})

🎯 시스템 개요:
- 데몬 가동시간: {uptime_days}일
- SSL 갱신: {self.daemon_stats['ssl_renewals']}회
- 백업 생성: {self.daemon_stats['backups_created']}개
- 벤치마크 실행: {self.daemon_stats['benchmarks_run']}회
- 헬스 체크: {self.daemon_stats['health_checks']}회
- 오류 발생: {self.daemon_stats['errors']}회

🔒 SSL 인증서:
- 유효한 인증서: {status.get('ssl_certificates', {}).get('valid_certificates', 0)}개
- 만료 임박: {status.get('ssl_certificates', {}).get('expiring_soon', 0)}개
- 만료된 인증서: {status.get('ssl_certificates', {}).get('expired', 0)}개

💓 서비스 상태:
- 전체 상태: {status.get('service_health', {}).get('overall_status', 'unknown')}
- 정상 서비스: {status.get('service_health', {}).get('healthy_services', 0)}개
- 비정상 서비스: {status.get('service_health', {}).get('unhealthy_services', 0)}개

💾 백업 현황:
"""
            
            # 백업 정보 추가
            backup_info = status.get('recent_backups', {})
            for backup_name, info in backup_info.items():
                if 'latest_backup' in info:
                    report += f"- {backup_name}: {info['latest_backup']} ({info.get('file_size_mb', 0)}MB)\n"
                else:
                    report += f"- {backup_name}: {info.get('status', 'unknown')}\n"
            
            # 시스템 리소스 추가
            sys_res = status.get('system_resources', {})
            report += f"""
🖥️  시스템 리소스:
- CPU 사용률: {sys_res.get('cpu_percent', 0):.1f}%
- 메모리 사용률: {sys_res.get('memory_percent', 0):.1f}%
- 메모리 사용량: {sys_res.get('memory_used_gb', 0):.1f}GB / {sys_res.get('memory_total_gb', 0):.1f}GB
"""
            
            # 성능 벤치마크 추가
            benchmark_summary = status.get('benchmark_summary', {})
            if 'average_rps' in benchmark_summary:
                report += f"""
⚡ 성능 지표:
- 평균 RPS: {benchmark_summary.get('average_rps', 0):.1f}
- 평균 응답시간: {benchmark_summary.get('average_response_time_ms', 0):.1f}ms
- 성공률: {benchmark_summary.get('success_rate_percent', 0):.1f}%
"""
            
            logger.info(report)
            
            # 리포트 파일로 저장
            report_file = Path(f"/var/log/stockpilot/weekly_report_{datetime.now().strftime('%Y%m%d')}.txt")
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            # 중요한 이슈가 있으면 알림 전송
            if (status.get('ssl_certificates', {}).get('expired', 0) > 0 or 
                status.get('service_health', {}).get('overall_status') == 'unhealthy' or
                self.daemon_stats['errors'] > 10):
                
                await self._send_alert(
                    "주간 리포트 - 주의 필요",
                    "주간 리포트에서 중요한 이슈가 발견되었습니다. 리포트를 확인해주세요.",
                    "warning"
                )
            
            logger.info(f"✅ {task_name} 완료 - 리포트 저장: {report_file}")
            
        except Exception as e:
            logger.error(f"{task_name} 실행 오류: {e}")

    async def _send_alert(self, title: str, message: str, level: str = "info"):
        """알림 전송"""
        try:
            # 실제 환경에서는 Slack, 이메일, SMS 등으로 알림 전송
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            alert_message = f"[{level.upper()}] {title}\n{message}\n시간: {timestamp}"
            
            # 로그로 알림 기록
            if level == "critical":
                logger.critical(f"🚨 CRITICAL ALERT: {title} - {message}")
            elif level == "warning":
                logger.warning(f"⚠️ WARNING ALERT: {title} - {message}")
            elif level == "error":
                logger.error(f"❌ ERROR ALERT: {title} - {message}")
            else:
                logger.info(f"ℹ️ INFO ALERT: {title} - {message}")
            
            # 알림 파일로도 저장 (외부 모니터링 시스템에서 활용 가능)
            alert_file = Path(f"/var/log/stockpilot/alerts_{datetime.now().strftime('%Y%m')}.log")
            with open(alert_file, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp} [{level.upper()}] {title}: {message}\n")
            
        except Exception as e:
            logger.error(f"알림 전송 오류: {e}")

    async def start(self):
        """데몬 시작"""
        if not await self.setup():
            logger.error("데몬 초기화 실패")
            return False
        
        self.running = True
        
        # 시그널 핸들러 설정
        def signal_handler(signum, frame):
            logger.info(f"시그널 {signum} 수신 - 데몬 종료 중...")
            self.running = False
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        logger.info("🚀 StockPilot 프로덕션 관리 데몬 시작")
        
        try:
            # 시작 시 초기 상태 점검
            await self._execute_health_check("초기 헬스 체크")
            await self._execute_ssl_check("초기 SSL 체크")
            
            # 메인 스케줄링 루프
            while self.running:
                try:
                    # 스케줄된 작업 실행
                    schedule.run_pending()
                    
                    # 1초 대기
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"스케줄링 루프 오류: {e}")
                    self.daemon_stats['errors'] += 1
                    await asyncio.sleep(5)
                    
        except Exception as e:
            logger.error(f"데몬 실행 오류: {e}")
        finally:
            await self.cleanup()
        
        return True

    async def cleanup(self):
        """정리 작업"""
        logger.info("프로덕션 관리 데몬 종료 중...")
        
        # 최종 통계 출력
        uptime = datetime.now() - self.daemon_stats['start_time']
        logger.info(f"📊 최종 통계: SSL 갱신 {self.daemon_stats['ssl_renewals']}회, "
                   f"백업 {self.daemon_stats['backups_created']}개, "
                   f"벤치마크 {self.daemon_stats['benchmarks_run']}회, "
                   f"헬스체크 {self.daemon_stats['health_checks']}회, "
                   f"오류 {self.daemon_stats['errors']}회, "
                   f"가동시간 {uptime}")
        
        logger.info("프로덕션 관리 데몬 종료 완료")

    def get_status(self) -> Dict:
        """데몬 상태 조회"""
        uptime = datetime.now() - self.daemon_stats['start_time']
        
        return {
            'running': self.running,
            'uptime_seconds': uptime.total_seconds(),
            'daemon_stats': self.daemon_stats.copy(),
            'scheduled_jobs': len(schedule.jobs),
            'alert_thresholds': self.alert_thresholds.copy()
        }

async def main():
    """메인 함수"""
    # 로그 디렉토리 생성
    log_dir = Path("/var/log/stockpilot")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("🏭 StockPilot 프로덕션 관리 데몬 시작")
    
    daemon = ProductionDaemon()
    
    try:
        success = await daemon.start()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("사용자에 의한 중단")
    except Exception as e:
        logger.error(f"치명적 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())