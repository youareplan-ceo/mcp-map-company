#!/usr/bin/env python3
"""
StockPilot 비용 모니터링 활성화 및 알림 테스트
작성자: StockPilot Team
용도: OpenAI API 비용 모니터링, 알림 테스트, 임계값 확인
"""

import asyncio
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import aioredis
import os
from services.openai_service import GPTService
from services.notification_service import NotificationService, NotificationMessage, NotificationType, NotificationPriority

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cost_monitoring_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CostMonitoringTester:
    """비용 모니터링 테스터 클래스"""
    
    def __init__(self):
        self.gpt_service = None
        self.notification_service = None
        self.redis_client = None
        self.test_results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'cost_tests': [],
            'alert_tests': [],
            'errors': []
        }
    
    async def initialize(self):
        """서비스 초기화"""
        try:
            # GPT 서비스 초기화
            self.gpt_service = GPTService()
            await self.gpt_service.initialize()
            
            # 알림 서비스 초기화
            self.notification_service = NotificationService()
            await self.notification_service.initialize()
            
            # Redis 연결
            redis_url = f"redis://localhost:6379/2"  # 테스트용 DB
            self.redis_client = await aioredis.from_url(redis_url)
            
            logger.info("✅ 비용 모니터링 테스터 초기화 완료")
            
        except Exception as e:
            logger.error(f"❌ 초기화 실패: {e}")
            raise
    
    async def run_cost_monitoring_tests(self) -> Dict[str, Any]:
        """모든 비용 모니터링 테스트 실행"""
        logger.info("💰 비용 모니터링 테스트 시작")
        
        await self.initialize()
        
        # 1. 기본 비용 추적 테스트
        await self._test_basic_cost_tracking()
        
        # 2. 비용 임계값 테스트
        await self._test_cost_thresholds()
        
        # 3. 일일 한도 테스트
        await self._test_daily_limits()
        
        # 4. API 키 로테이션 테스트
        await self._test_api_key_rotation()
        
        # 5. 비용 알림 테스트
        await self._test_cost_alerts()
        
        # 6. 비용 리포팅 테스트
        await self._test_cost_reporting()
        
        # 7. 사용량 통계 테스트
        await self._test_usage_statistics()
        
        # 8. 비용 예측 테스트
        await self._test_cost_prediction()
        
        # 결과 리포트 생성
        report = self._generate_report()
        
        logger.info(f"✅ 비용 모니터링 테스트 완료: {self.test_results['passed_tests']}/{self.test_results['total_tests']} 통과")
        
        return report
    
    async def _test_basic_cost_tracking(self):
        """기본 비용 추적 테스트"""
        logger.info("📊 기본 비용 추적 테스트")
        
        try:
            # 테스트 GPT 요청 생성
            test_request = {
                'messages': [
                    {'role': 'user', 'content': '간단한 테스트 메시지입니다.'}
                ],
                'model': 'gpt-3.5-turbo',
                'max_tokens': 100
            }
            
            # 비용 추적 전 상태 확인
            initial_usage = await self.gpt_service.get_usage_stats()
            
            # GPT 요청 실행
            response = await self.gpt_service.create_chat_completion(test_request)
            
            # 비용 추적 후 상태 확인
            final_usage = await self.gpt_service.get_usage_stats()
            
            # 비용 증가 확인
            cost_increased = final_usage['total_cost'] > initial_usage['total_cost']
            requests_increased = final_usage['total_requests'] > initial_usage['total_requests']
            
            success = response['success'] and cost_increased and requests_increased
            
            self._record_test_result(
                category='cost_tracking',
                test_name='기본 비용 추적',
                success=success,
                details={
                    'initial_cost': initial_usage['total_cost'],
                    'final_cost': final_usage['total_cost'],
                    'cost_increase': final_usage['total_cost'] - initial_usage['total_cost'],
                    'requests_tracked': requests_increased
                }
            )
            
            if success:
                logger.info(f"✅ 비용 추적 성공: ${final_usage['total_cost'] - initial_usage['total_cost']:.4f} 증가")
            else:
                logger.error("❌ 비용 추적 실패")
                
        except Exception as e:
            self._record_test_result(
                category='cost_tracking',
                test_name='기본 비용 추적',
                success=False,
                error=str(e)
            )
            logger.error(f"❌ 비용 추적 테스트 실패: {e}")
    
    async def _test_cost_thresholds(self):
        """비용 임계값 테스트"""
        logger.info("🚨 비용 임계값 테스트")
        
        try:
            # 테스트용 임계값 설정 (매우 낮은 값)
            test_threshold = 0.01  # $0.01
            await self.gpt_service.set_cost_threshold(test_threshold)
            
            # 현재 비용 확인
            current_usage = await self.gpt_service.get_usage_stats()
            current_cost = current_usage['today_cost']
            
            # 임계값 초과하도록 요청 생성
            if current_cost < test_threshold:
                # 여러 요청으로 임계값 초과 시도
                for i in range(5):
                    test_request = {
                        'messages': [
                            {'role': 'user', 'content': f'임계값 테스트 메시지 {i+1}'}
                        ],
                        'model': 'gpt-3.5-turbo',
                        'max_tokens': 50
                    }
                    
                    await self.gpt_service.create_chat_completion(test_request)
                    await asyncio.sleep(0.1)
            
            # 임계값 상태 확인
            final_usage = await self.gpt_service.get_usage_stats()
            threshold_exceeded = final_usage['today_cost'] >= test_threshold
            
            # 알림이 발생했는지 확인 (Redis에서)
            alerts = await self.redis_client.lrange('cost_alerts', 0, -1)
            alert_triggered = len(alerts) > 0
            
            success = threshold_exceeded or alert_triggered
            
            self._record_test_result(
                category='cost_tracking',
                test_name='비용 임계값',
                success=success,
                details={
                    'threshold': test_threshold,
                    'final_cost': final_usage['today_cost'],
                    'threshold_exceeded': threshold_exceeded,
                    'alert_triggered': alert_triggered,
                    'alerts_count': len(alerts)
                }
            )
            
            if success:
                logger.info(f"✅ 임계값 테스트 성공: ${final_usage['today_cost']:.4f} (임계값: ${test_threshold})")
            else:
                logger.warning(f"⚠️ 임계값 테스트: 비용이 임계값에 도달하지 않음")
                
        except Exception as e:
            self._record_test_result(
                category='cost_tracking',
                test_name='비용 임계값',
                success=False,
                error=str(e)
            )
            logger.error(f"❌ 임계값 테스트 실패: {e}")
    
    async def _test_daily_limits(self):
        """일일 한도 테스트"""
        logger.info("📅 일일 한도 테스트")
        
        try:
            # 현재 일일 사용량 확인
            daily_usage = await self.gpt_service.get_daily_usage()
            daily_limit = self.gpt_service.daily_cost_limit
            
            # 한도까지 남은 금액 확인
            remaining_budget = daily_limit - daily_usage['cost']
            
            success = daily_usage['cost'] <= daily_limit
            limit_enforced = remaining_budget >= 0
            
            self._record_test_result(
                category='cost_tracking',
                test_name='일일 한도',
                success=success,
                details={
                    'daily_limit': daily_limit,
                    'daily_usage': daily_usage['cost'],
                    'remaining_budget': remaining_budget,
                    'limit_enforced': limit_enforced,
                    'requests_today': daily_usage['requests']
                }
            )
            
            if success:
                logger.info(f"✅ 일일 한도 확인: ${daily_usage['cost']:.4f}/${daily_limit} 사용")
            else:
                logger.warning(f"⚠️ 일일 한도 초과: ${daily_usage['cost']:.4f}/${daily_limit}")
                
        except Exception as e:
            self._record_test_result(
                category='cost_tracking',
                test_name='일일 한도',
                success=False,
                error=str(e)
            )
            logger.error(f"❌ 일일 한도 테스트 실패: {e}")
    
    async def _test_api_key_rotation(self):
        """API 키 로테이션 테스트"""
        logger.info("🔄 API 키 로테이션 테스트")
        
        try:
            # 현재 활성 키 확인
            current_key = self.gpt_service.get_current_api_key()
            
            # 키 로테이션 실행
            rotated = await self.gpt_service.rotate_api_key()
            
            # 로테이션 후 키 확인
            new_key = self.gpt_service.get_current_api_key()
            
            # 키가 변경되었는지 확인
            key_changed = current_key != new_key if rotated else True
            
            # 키 사용량 추적 확인
            key_stats = await self.gpt_service.get_key_usage_stats()
            
            success = rotated and key_changed
            
            self._record_test_result(
                category='cost_tracking',
                test_name='API 키 로테이션',
                success=success,
                details={
                    'rotation_successful': rotated,
                    'key_changed': key_changed,
                    'active_keys': len(key_stats),
                    'current_key_masked': f"...{new_key[-8:]}" if new_key else None
                }
            )
            
            if success:
                logger.info(f"✅ API 키 로테이션 성공: {len(key_stats)}개 키 활성화")
            else:
                logger.warning("⚠️ API 키 로테이션 실패 또는 불필요")
                
        except Exception as e:
            self._record_test_result(
                category='cost_tracking',
                test_name='API 키 로테이션',
                success=False,
                error=str(e)
            )
            logger.error(f"❌ API 키 로테이션 테스트 실패: {e}")
    
    async def _test_cost_alerts(self):
        """비용 알림 테스트"""
        logger.info("🔔 비용 알림 테스트")
        
        try:
            # 테스트용 사용자 등록
            from services.notification_service import NotificationUser
            
            test_user = NotificationUser(
                user_id="cost_test_user",
                name="비용 테스트 사용자",
                email="cost-test@stockpilot.ai",
                enabled_channels=['email'],
                preferences={'cost_alerts': True}
            )
            
            await self.notification_service.register_user(test_user)
            
            # 비용 알림 메시지 생성
            alert_message = NotificationMessage(
                id="cost_alert_test",
                type=NotificationType.SYSTEM_STATUS,
                priority=NotificationPriority.HIGH,
                title="비용 알림 테스트",
                message="OpenAI API 비용이 일일 한도의 80%에 도달했습니다.",
                data={
                    "current_cost": "$15.60",
                    "daily_limit": "$20.00",
                    "usage_percentage": "78%",
                    "remaining_budget": "$4.40"
                }
            )
            
            # 알림 발송 테스트
            results = await self.notification_service.send_notification(alert_message)
            alert_sent = any(results.get(user_id, {}).get('email', False) for user_id in results)
            
            # 알림 로그 확인
            if self.redis_client:
                logs = await self.redis_client.lrange('notification_logs', 0, 0)
                log_recorded = len(logs) > 0
            else:
                log_recorded = False
            
            success = alert_sent or log_recorded
            
            self._record_test_result(
                category='alerts',
                test_name='비용 알림',
                success=success,
                details={
                    'alert_sent': alert_sent,
                    'log_recorded': log_recorded,
                    'delivery_results': results
                }
            )
            
            if success:
                logger.info("✅ 비용 알림 테스트 성공")
            else:
                logger.error("❌ 비용 알림 테스트 실패")
                
        except Exception as e:
            self._record_test_result(
                category='alerts',
                test_name='비용 알림',
                success=False,
                error=str(e)
            )
            logger.error(f"❌ 비용 알림 테스트 실패: {e}")
    
    async def _test_cost_reporting(self):
        """비용 리포팅 테스트"""
        logger.info("📈 비용 리포팅 테스트")
        
        try:
            # 다양한 기간의 리포트 생성
            reports = {}
            
            # 일일 리포트
            reports['daily'] = await self.gpt_service.get_daily_report()
            
            # 주간 리포트 (7일)
            reports['weekly'] = await self.gpt_service.get_usage_report(days=7)
            
            # 월간 리포트 (30일)
            reports['monthly'] = await self.gpt_service.get_usage_report(days=30)
            
            # 모델별 사용량 리포트
            reports['by_model'] = await self.gpt_service.get_model_usage_report()
            
            # 리포트 유효성 검증
            valid_reports = 0
            for period, report in reports.items():
                if report and isinstance(report, dict) and 'total_cost' in report:
                    valid_reports += 1
            
            success = valid_reports >= 3  # 최소 3개 리포트가 유효해야 함
            
            self._record_test_result(
                category='cost_tracking',
                test_name='비용 리포팅',
                success=success,
                details={
                    'valid_reports': valid_reports,
                    'total_reports': len(reports),
                    'daily_cost': reports.get('daily', {}).get('total_cost', 0),
                    'weekly_cost': reports.get('weekly', {}).get('total_cost', 0),
                    'monthly_cost': reports.get('monthly', {}).get('total_cost', 0)
                }
            )
            
            if success:
                logger.info(f"✅ 비용 리포팅 테스트 성공: {valid_reports}개 리포트 생성")
            else:
                logger.error("❌ 비용 리포팅 테스트 실패")
                
        except Exception as e:
            self._record_test_result(
                category='cost_tracking',
                test_name='비용 리포팅',
                success=False,
                error=str(e)
            )
            logger.error(f"❌ 비용 리포팅 테스트 실패: {e}")
    
    async def _test_usage_statistics(self):
        """사용량 통계 테스트"""
        logger.info("📊 사용량 통계 테스트")
        
        try:
            # 다양한 통계 수집
            stats = {}
            
            # 전체 사용량 통계
            stats['overall'] = await self.gpt_service.get_usage_stats()
            
            # 시간별 사용량 (지난 24시간)
            stats['hourly'] = await self.gpt_service.get_hourly_usage()
            
            # 토큰 사용량 상세
            stats['tokens'] = await self.gpt_service.get_token_usage_stats()
            
            # 에러율 통계
            stats['errors'] = await self.gpt_service.get_error_stats()
            
            # 통계 유효성 검증
            valid_stats = 0
            for category, stat in stats.items():
                if stat and isinstance(stat, dict):
                    valid_stats += 1
            
            success = valid_stats >= 3
            
            self._record_test_result(
                category='cost_tracking',
                test_name='사용량 통계',
                success=success,
                details={
                    'valid_stats': valid_stats,
                    'total_categories': len(stats),
                    'total_requests': stats.get('overall', {}).get('total_requests', 0),
                    'total_tokens': stats.get('tokens', {}).get('total_tokens', 0),
                    'error_rate': stats.get('errors', {}).get('error_rate', 0)
                }
            )
            
            if success:
                logger.info(f"✅ 사용량 통계 테스트 성공: {valid_stats}개 카테고리 수집")
            else:
                logger.error("❌ 사용량 통계 테스트 실패")
                
        except Exception as e:
            self._record_test_result(
                category='cost_tracking',
                test_name='사용량 통계',
                success=False,
                error=str(e)
            )
            logger.error(f"❌ 사용량 통계 테스트 실패: {e}")
    
    async def _test_cost_prediction(self):
        """비용 예측 테스트"""
        logger.info("🔮 비용 예측 테스트")
        
        try:
            # 현재 사용 패턴을 기반으로 예측
            current_usage = await self.gpt_service.get_usage_stats()
            
            # 일일 예측
            daily_prediction = await self.gpt_service.predict_daily_cost()
            
            # 주간 예측
            weekly_prediction = await self.gpt_service.predict_weekly_cost()
            
            # 월간 예측
            monthly_prediction = await self.gpt_service.predict_monthly_cost()
            
            # 예측값 유효성 검증
            predictions = [daily_prediction, weekly_prediction, monthly_prediction]
            valid_predictions = sum(1 for p in predictions if p and p > 0)
            
            success = valid_predictions >= 2  # 최소 2개 예측이 유효해야 함
            
            self._record_test_result(
                category='cost_tracking',
                test_name='비용 예측',
                success=success,
                details={
                    'valid_predictions': valid_predictions,
                    'daily_prediction': daily_prediction,
                    'weekly_prediction': weekly_prediction,
                    'monthly_prediction': monthly_prediction,
                    'current_daily_cost': current_usage.get('today_cost', 0)
                }
            )
            
            if success:
                logger.info(f"✅ 비용 예측 테스트 성공: 일일 ${daily_prediction:.2f}, 주간 ${weekly_prediction:.2f}")
            else:
                logger.error("❌ 비용 예측 테스트 실패")
                
        except Exception as e:
            self._record_test_result(
                category='cost_tracking',
                test_name='비용 예측',
                success=False,
                error=str(e)
            )
            logger.error(f"❌ 비용 예측 테스트 실패: {e}")
    
    def _record_test_result(self, category: str, test_name: str, success: bool, details: Dict = None, error: str = None):
        """테스트 결과 기록"""
        self.test_results['total_tests'] += 1
        
        if success:
            self.test_results['passed_tests'] += 1
        else:
            self.test_results['failed_tests'] += 1
            if error:
                self.test_results['errors'].append({
                    'test': test_name,
                    'error': error,
                    'timestamp': datetime.now().isoformat()
                })
        
        test_result = {
            'category': category,
            'test_name': test_name,
            'success': success,
            'timestamp': datetime.now().isoformat(),
            'details': details or {},
        }
        
        if error:
            test_result['error'] = error
        
        if category == 'alerts':
            self.test_results['alert_tests'].append(test_result)
        else:
            self.test_results['cost_tests'].append(test_result)
    
    def _generate_report(self) -> Dict[str, Any]:
        """최종 리포트 생성"""
        success_rate = (self.test_results['passed_tests'] / self.test_results['total_tests'] * 100) if self.test_results['total_tests'] > 0 else 0
        
        # 카테고리별 통계
        category_stats = {}
        all_tests = self.test_results['cost_tests'] + self.test_results['alert_tests']
        
        for test in all_tests:
            category = test['category']
            if category not in category_stats:
                category_stats[category] = {'total': 0, 'passed': 0, 'failed': 0}
            
            category_stats[category]['total'] += 1
            if test['success']:
                category_stats[category]['passed'] += 1
            else:
                category_stats[category]['failed'] += 1
        
        report = {
            'summary': {
                'total_tests': self.test_results['total_tests'],
                'passed_tests': self.test_results['passed_tests'],
                'failed_tests': self.test_results['failed_tests'],
                'success_rate': round(success_rate, 2),
                'timestamp': datetime.now().isoformat()
            },
            'category_stats': category_stats,
            'cost_tests': self.test_results['cost_tests'],
            'alert_tests': self.test_results['alert_tests'],
            'errors': self.test_results['errors']
        }
        
        return report
    
    async def cleanup(self):
        """리소스 정리"""
        try:
            if self.redis_client:
                await self.redis_client.close()
            
            logger.info("✅ 리소스 정리 완료")
        except Exception as e:
            logger.error(f"⚠️ 리소스 정리 중 오류: {e}")

async def main():
    """메인 실행 함수"""
    logger.info("🚀 StockPilot 비용 모니터링 테스트 시작")
    
    tester = None
    try:
        tester = CostMonitoringTester()
        report = await tester.run_cost_monitoring_tests()
        
        # 리포트를 JSON 파일로 저장
        with open('cost_monitoring_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # 콘솔에 요약 출력
        print("\\n" + "="*80)
        print("💰 비용 모니터링 테스트 리포트")
        print("="*80)
        print(f"총 테스트: {report['summary']['total_tests']}")
        print(f"성공: {report['summary']['passed_tests']}")
        print(f"실패: {report['summary']['failed_tests']}")
        print(f"성공률: {report['summary']['success_rate']}%")
        print("="*80)
        
        # 카테고리별 통계 출력
        print("\\n📈 카테고리별 통계:")
        for category, stats in report['category_stats'].items():
            success_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"  {category}: {stats['passed']}/{stats['total']} 성공 ({success_rate:.1f}%)")
        
        # 주요 결과 출력
        print("\\n💡 주요 결과:")
        for test in report['cost_tests'] + report['alert_tests']:
            status = "✅" if test['success'] else "❌"
            print(f"  {status} {test['test_name']}")
        
        # 에러 요약 출력
        if report['errors']:
            print(f"\\n❌ 에러 ({len(report['errors'])}개):")
            for error in report['errors'][:3]:
                print(f"  - {error['test']}: {error['error']}")
        
        print(f"\\n📄 상세 리포트: cost_monitoring_report.json")
        
        return report
        
    except Exception as e:
        logger.error(f"❌ 비용 모니터링 테스트 실행 실패: {e}")
        raise
    
    finally:
        if tester:
            await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())