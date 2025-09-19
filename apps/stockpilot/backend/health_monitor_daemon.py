#!/usr/bin/env python3
"""
StockPilot 헬스 모니터 데몬
상시 구동되며 모든 서비스의 상태를 모니터링하고 알림을 전송하는 백그라운드 서비스
"""

import asyncio
import signal
import sys
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.health_monitor import create_health_monitor

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/stockpilot/health_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HealthMonitorDaemon:
    """헬스 모니터 데몬 클래스"""
    
    def __init__(self):
        self.running = False
        self.monitor = None
        self.check_interval = 30  # 30초마다 체크
        self.alert_cooldown = 300  # 5분 알림 쿨다운
        self.last_alerts = {}
        
        # 품질 점수 임계치 조정
        self.quality_thresholds = {
            "healthy": 80,    # 80점 이상 정상
            "warning": 70,    # 70점 이상 경고
            "critical": 0     # 70점 미만 치명적
        }
        
        # 알림 규칙 튜닝
        self.alert_rules = {
            "cpu_threshold": 85.0,           # CPU 85% 이상
            "memory_threshold": 90.0,        # 메모리 90% 이상
            "disk_threshold": 95.0,          # 디스크 95% 이상
            "response_time_threshold": 3000,  # 응답시간 3초 이상
            "consecutive_failures": 3         # 연속 실패 3회 이상
        }
        
        self.consecutive_failures = {}

    async def setup_monitor(self):
        """모니터 설정"""
        try:
            self.monitor = await create_health_monitor()
            
            # 임계치 업데이트
            self.monitor.alert_thresholds.update(self.alert_rules)
            
            logger.info("헬스 모니터 데몬 초기화 완료")
            return True
            
        except Exception as e:
            logger.error(f"헬스 모니터 초기화 실패: {e}")
            return False

    def should_send_alert(self, alert_id: str) -> bool:
        """알림 쿨다운 체크"""
        now = datetime.now()
        
        if alert_id in self.last_alerts:
            time_diff = (now - self.last_alerts[alert_id]).total_seconds()
            if time_diff < self.alert_cooldown:
                return False
        
        self.last_alerts[alert_id] = now
        return True

    def check_consecutive_failures(self, service_key: str, is_healthy: bool) -> bool:
        """연속 실패 체크"""
        if service_key not in self.consecutive_failures:
            self.consecutive_failures[service_key] = 0
        
        if not is_healthy:
            self.consecutive_failures[service_key] += 1
        else:
            self.consecutive_failures[service_key] = 0
        
        return self.consecutive_failures[service_key] >= self.alert_rules["consecutive_failures"]

    async def monitor_loop(self):
        """메인 모니터링 루프"""
        logger.info("헬스 모니터 데몬 시작 - 상시 모니터링 모드")
        
        while self.running:
            try:
                # 종합 헬스 리포트 생성
                health_report = await self.monitor.get_comprehensive_health_report()
                
                # 전체 상태 로깅
                overall_status = health_report.get('overall_status', 'unknown')
                timestamp = health_report.get('timestamp', datetime.now().isoformat())
                
                logger.info(f"시스템 상태: {overall_status.upper()} - {timestamp}")
                
                # 서비스별 상태 체크 및 연속 실패 추적
                services = health_report.get('services', {})
                critical_alerts = []
                
                for service_key, service_info in services.items():
                    service_status = service_info.get('status', 'unknown')
                    is_healthy = service_status == 'healthy'
                    
                    # 연속 실패 체크
                    if self.check_consecutive_failures(service_key, is_healthy):
                        alert_id = f"consecutive_failure_{service_key}"
                        
                        if self.should_send_alert(alert_id):
                            critical_alerts.append({
                                "id": alert_id,
                                "severity": "critical",
                                "service": service_info.get('name', service_key),
                                "message": f"{service_info.get('name', service_key)}이 연속 {self.consecutive_failures[service_key]}회 실패했습니다.",
                                "response_time": service_info.get('response_time_ms', 0),
                                "error": service_info.get('error_message', ''),
                                "timestamp": datetime.now()
                            })
                
                # 시스템 메트릭 기반 알림
                system_metrics = health_report.get('system_metrics', {})
                
                # CPU 사용률 체크
                cpu_percent = system_metrics.get('cpu_percent', 0)
                if cpu_percent > self.alert_rules['cpu_threshold']:
                    alert_id = f"high_cpu_{int(cpu_percent)}"
                    if self.should_send_alert(alert_id):
                        critical_alerts.append({
                            "id": alert_id,
                            "severity": "warning",
                            "service": "System",
                            "message": f"⚠️ CPU 사용률 높음: {cpu_percent:.1f}% (임계치: {self.alert_rules['cpu_threshold']}%)",
                            "timestamp": datetime.now()
                        })
                
                # 메모리 사용률 체크
                memory_percent = system_metrics.get('memory_percent', 0)
                if memory_percent > self.alert_rules['memory_threshold']:
                    alert_id = f"high_memory_{int(memory_percent)}"
                    if self.should_send_alert(alert_id):
                        critical_alerts.append({
                            "id": alert_id,
                            "severity": "warning",
                            "service": "System",
                            "message": f"⚠️ 메모리 사용률 높음: {memory_percent:.1f}% (임계치: {self.alert_rules['memory_threshold']}%)",
                            "timestamp": datetime.now()
                        })
                
                # 디스크 사용률 체크
                disk_percent = system_metrics.get('disk_percent', 0)
                if disk_percent > self.alert_rules['disk_threshold']:
                    alert_id = f"high_disk_{int(disk_percent)}"
                    if self.should_send_alert(alert_id):
                        critical_alerts.append({
                            "id": alert_id,
                            "severity": "critical",
                            "service": "System",
                            "message": f"🚨 디스크 사용률 위험: {disk_percent:.1f}% (임계치: {self.alert_rules['disk_threshold']}%)",
                            "timestamp": datetime.now()
                        })
                
                # 서비스 품질 점수 계산
                summary = health_report.get('summary', {})
                total_services = summary.get('total_services', 1)
                healthy_services = summary.get('healthy_services', 0)
                
                quality_score = (healthy_services / total_services) * 100 if total_services > 0 else 0
                
                # 품질 점수 기반 알림
                if quality_score < self.quality_thresholds['warning']:
                    severity = "critical" if quality_score < self.quality_thresholds['critical'] + 70 else "warning"
                    alert_id = f"quality_score_{int(quality_score)}"
                    
                    if self.should_send_alert(alert_id):
                        critical_alerts.append({
                            "id": alert_id,
                            "severity": severity,
                            "service": "StockPilot System",
                            "message": f"📊 시스템 품질 점수 저하: {quality_score:.1f}점 (건강한 서비스: {healthy_services}/{total_services})",
                            "timestamp": datetime.now()
                        })
                
                # 알림 전송
                for alert in critical_alerts:
                    try:
                        # Slack 알림 전송 시뮬레이션 (실제로는 send_slack_alert 사용)
                        logger.warning(f"🚨 ALERT [{alert['severity'].upper()}] {alert['service']}: {alert['message']}")
                        
                        # 실제 Slack 알림 전송 (환경변수 설정시)
                        if hasattr(self.monitor, 'send_slack_alert'):
                            await self.monitor.send_slack_alert(alert)
                        
                    except Exception as e:
                        logger.error(f"알림 전송 실패: {e}")
                
                # 정상 상태일 때 간단 로깅
                if overall_status == 'healthy' and not critical_alerts:
                    healthy_count = summary.get('healthy_services', 0)
                    total_count = summary.get('total_services', 0)
                    avg_response = summary.get('average_response_time', 0)
                    
                    logger.info(f"✅ 모든 서비스 정상 ({healthy_count}/{total_count}) - 평균 응답시간: {avg_response:.0f}ms")
                
                # 헬스 리포트를 파일로 저장 (최근 상태 추적용)
                try:
                    health_file = Path("/tmp/stockpilot_health.json")
                    with open(health_file, 'w') as f:
                        import json
                        json.dump(health_report, f, indent=2, default=str)
                except Exception as e:
                    logger.warning(f"헬스 리포트 파일 저장 실패: {e}")
                
            except Exception as e:
                logger.error(f"모니터링 루프 오류: {e}")
            
            # 다음 체크까지 대기
            await asyncio.sleep(self.check_interval)

    async def start(self):
        """데몬 시작"""
        if not await self.setup_monitor():
            logger.error("헬스 모니터 설정 실패")
            return False
        
        self.running = True
        
        # 시그널 핸들러 설정
        def signal_handler(signum, frame):
            logger.info(f"시그널 {signum} 수신 - 데몬 종료 중...")
            self.running = False
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        try:
            await self.monitor_loop()
        except Exception as e:
            logger.error(f"데몬 실행 오류: {e}")
        finally:
            await self.cleanup()
        
        return True

    async def cleanup(self):
        """정리 작업"""
        logger.info("헬스 모니터 데몬 종료 중...")
        
        if self.monitor:
            try:
                await self.monitor.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"모니터 정리 오류: {e}")
        
        logger.info("헬스 모니터 데몬 종료 완료")

async def main():
    """메인 함수"""
    # 로그 디렉토리 생성
    log_dir = Path("/var/log/stockpilot")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("🔍 StockPilot 헬스 모니터 데몬 시작")
    
    daemon = HealthMonitorDaemon()
    
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