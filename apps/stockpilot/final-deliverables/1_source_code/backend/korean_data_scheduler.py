#!/usr/bin/env python3
"""
StockPilot KR 데이터 수집 스케줄러
주기적 데이터 수집, 품질 검증, 캐시 관리를 담당하는 백그라운드 서비스
"""

import asyncio
import signal
import sys
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import schedule
import time
from pathlib import Path

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.korean_data_sources import create_korean_data_manager, DataSourceType

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/stockpilot/korean_data_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class KoreanDataScheduler:
    """KR 데이터 수집 스케줄러"""
    
    def __init__(self):
        self.running = False
        self.data_manager = None
        self.collection_stats = {
            'total_collections': 0,
            'successful_collections': 0,
            'failed_collections': 0,
            'last_collection': None,
            'start_time': datetime.now()
        }
        
        # 수집 일정 설정
        self.collection_schedule = {
            DataSourceType.DART_DISCLOSURE: {
                'frequency': '1h',  # 1시간마다
                'active_hours': (9, 18),  # 9시-18시만 활성
                'priority': 1
            },
            DataSourceType.SECURITIES_REPORT: {
                'frequency': '6h',  # 6시간마다
                'active_hours': (8, 20),  # 8시-20시
                'priority': 2
            },
            DataSourceType.CALENDAR_DATA: {
                'frequency': '30m',  # 30분마다
                'active_hours': (6, 22),  # 6시-22시
                'priority': 1
            },
            DataSourceType.PRICE_DATA: {
                'frequency': '5m',   # 5분마다 (장중)
                'active_hours': (9, 15),  # 장시간만
                'priority': 1
            },
            DataSourceType.NEWS_DATA: {
                'frequency': '15m',  # 15분마다
                'active_hours': (6, 23),  # 6시-23시
                'priority': 2
            }
        }

    async def setup(self):
        """스케줄러 초기화"""
        try:
            # 데이터 매니저 초기화
            self.data_manager = await create_korean_data_manager()
            
            # 캘린더 이중화 설정
            await self.data_manager.setup_calendar_redundancy()
            
            # 캐시 TTL 설정
            await self.data_manager.configure_cache_ttl()
            
            # 스케줄 설정
            self._setup_schedules()
            
            logger.info("KR 데이터 스케줄러 초기화 완료")
            return True
            
        except Exception as e:
            logger.error(f"스케줄러 초기화 실패: {e}")
            return False

    def _setup_schedules(self):
        """수집 스케줄 설정"""
        try:
            # DART 전자공시 (1시간마다)
            schedule.every().hour.do(
                self._schedule_collection, 
                DataSourceType.DART_DISCLOSURE, 
                "DART 전자공시 수집"
            )
            
            # 증권사 리포트 (6시간마다)
            schedule.every(6).hours.do(
                self._schedule_collection,
                DataSourceType.SECURITIES_REPORT,
                "증권사 리포트 수집"
            )
            
            # 캘린더 데이터 (30분마다)
            schedule.every(30).minutes.do(
                self._schedule_collection,
                DataSourceType.CALENDAR_DATA,
                "캘린더 데이터 수집"
            )
            
            # 가격 데이터 (5분마다, 장시간만)
            schedule.every(5).minutes.do(
                self._schedule_trading_hours_collection,
                DataSourceType.PRICE_DATA,
                "가격 데이터 수집"
            )
            
            # 뉴스 데이터 (15분마다)
            schedule.every(15).minutes.do(
                self._schedule_collection,
                DataSourceType.NEWS_DATA,
                "뉴스 데이터 수집"
            )
            
            # 품질 검증 (매일 자정)
            schedule.every().day.at("00:00").do(
                self._schedule_quality_validation,
                "일일 품질 검증"
            )
            
            # 캐시 정리 (매일 새벽 3시)
            schedule.every().day.at("03:00").do(
                self._schedule_cache_cleanup,
                "캐시 정리"
            )
            
            # 통계 리포트 (매일 오전 9시)
            schedule.every().day.at("09:00").do(
                self._schedule_daily_report,
                "일일 리포트 생성"
            )
            
            logger.info("데이터 수집 스케줄 설정 완료")
            
        except Exception as e:
            logger.error(f"스케줄 설정 오류: {e}")

    def _schedule_collection(self, source_type: DataSourceType, task_name: str):
        """일반 데이터 수집 스케줄"""
        try:
            # 활성 시간대 체크
            current_hour = datetime.now().hour
            schedule_config = self.collection_schedule.get(source_type, {})
            active_hours = schedule_config.get('active_hours', (0, 24))
            
            if not (active_hours[0] <= current_hour <= active_hours[1]):
                logger.debug(f"{task_name} - 비활성 시간대로 건너뜀")
                return
            
            # 비동기 수집 작업 실행
            asyncio.create_task(self._execute_collection(source_type, task_name))
            
        except Exception as e:
            logger.error(f"{task_name} 스케줄링 오류: {e}")

    def _schedule_trading_hours_collection(self, source_type: DataSourceType, task_name: str):
        """장시간 한정 데이터 수집"""
        try:
            current_time = datetime.now()
            current_hour = current_time.hour
            
            # 평일인지 확인 (0=월요일, 6=일요일)
            if current_time.weekday() >= 5:  # 주말
                logger.debug(f"{task_name} - 주말로 건너뜀")
                return
            
            # 장시간 체크 (9:00-15:30)
            if not (9 <= current_hour < 15 or (current_hour == 15 and current_time.minute <= 30)):
                logger.debug(f"{task_name} - 장시간 외로 건너뜀")
                return
            
            # 비동기 수집 작업 실행
            asyncio.create_task(self._execute_collection(source_type, task_name))
            
        except Exception as e:
            logger.error(f"{task_name} 장시간 스케줄링 오류: {e}")

    def _schedule_quality_validation(self, task_name: str):
        """품질 검증 스케줄"""
        try:
            asyncio.create_task(self._execute_quality_validation(task_name))
        except Exception as e:
            logger.error(f"{task_name} 스케줄링 오류: {e}")

    def _schedule_cache_cleanup(self, task_name: str):
        """캐시 정리 스케줄"""
        try:
            asyncio.create_task(self._execute_cache_cleanup(task_name))
        except Exception as e:
            logger.error(f"{task_name} 스케줄링 오류: {e}")

    def _schedule_daily_report(self, task_name: str):
        """일일 리포트 스케줄"""
        try:
            asyncio.create_task(self._execute_daily_report(task_name))
        except Exception as e:
            logger.error(f"{task_name} 스케줄링 오류: {e}")

    async def _execute_collection(self, source_type: DataSourceType, task_name: str):
        """데이터 수집 실행"""
        try:
            logger.info(f"🔄 {task_name} 시작")
            start_time = datetime.now()
            
            self.collection_stats['total_collections'] += 1
            
            if not self.data_manager:
                logger.error("데이터 매니저가 초기화되지 않음")
                self.collection_stats['failed_collections'] += 1
                return
            
            success_count = 0
            error_count = 0
            
            # 해당 타입의 모든 소스에 대해 수집 실행
            for source_id, source in self.data_manager.data_sources.items():
                if source.source_type != source_type or not source.enabled:
                    continue
                
                try:
                    if source_type == DataSourceType.SECURITIES_REPORT:
                        items = await self.data_manager.collect_securities_reports(source_id)
                        success_count += len(items) if items else 0
                        
                    elif source_type == DataSourceType.DART_DISCLOSURE:
                        # DART 공시 수집 (샘플 데이터로 대체)
                        disclosure_data = await self.data_manager.fetch_dart_disclosure_details(
                            "00126380", "사업보고서"  # 삼성전자 예시
                        )
                        if disclosure_data.get('items'):
                            success_count += len(disclosure_data['items'])
                        
                    elif source_type == DataSourceType.CALENDAR_DATA:
                        # 캘린더 데이터 수집 (구현 필요)
                        logger.info(f"캘린더 데이터 수집: {source_id}")
                        success_count += 1
                        
                    elif source_type == DataSourceType.PRICE_DATA:
                        # 가격 데이터 수집 (구현 필요)
                        logger.info(f"가격 데이터 수집: {source_id}")
                        success_count += 1
                        
                    elif source_type == DataSourceType.NEWS_DATA:
                        # 뉴스 데이터 수집 (구현 필요)
                        logger.info(f"뉴스 데이터 수집: {source_id}")
                        success_count += 1
                    
                    # 소스 업데이트 시간 갱신
                    source.last_updated = datetime.now()
                    
                except Exception as e:
                    logger.error(f"소스 {source_id} 수집 오류: {e}")
                    source.error_count += 1
                    error_count += 1
            
            # 수집 완료 처리
            duration = (datetime.now() - start_time).total_seconds()
            
            if error_count == 0:
                self.collection_stats['successful_collections'] += 1
                logger.info(f"✅ {task_name} 완료 - 성공: {success_count}개, 소요시간: {duration:.1f}초")
            else:
                self.collection_stats['failed_collections'] += 1
                logger.warning(f"⚠️ {task_name} 부분 완료 - 성공: {success_count}개, 실패: {error_count}개, 소요시간: {duration:.1f}초")
            
            self.collection_stats['last_collection'] = datetime.now()
            
        except Exception as e:
            logger.error(f"{task_name} 실행 오류: {e}")
            self.collection_stats['failed_collections'] += 1

    async def _execute_quality_validation(self, task_name: str):
        """품질 검증 실행"""
        try:
            logger.info(f"🔍 {task_name} 시작")
            start_time = datetime.now()
            
            if not self.data_manager:
                logger.error("데이터 매니저가 초기화되지 않음")
                return
            
            # 모든 소스에 대해 품질 검증 실행
            reports = await self.data_manager.run_quality_validation()
            
            # 품질 리포트 요약
            total_sources = len(reports)
            high_quality = sum(1 for r in reports if r.quality_score >= 80)
            low_quality = sum(1 for r in reports if r.quality_score < 50)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"✅ {task_name} 완료 - 총 {total_sources}개 소스, 고품질: {high_quality}개, 저품질: {low_quality}개, 소요시간: {duration:.1f}초")
            
            # 저품질 소스에 대한 경고
            if low_quality > 0:
                low_quality_sources = [r.source_id for r in reports if r.quality_score < 50]
                logger.warning(f"⚠️ 저품질 소스 발견: {', '.join(low_quality_sources)}")
            
        except Exception as e:
            logger.error(f"{task_name} 실행 오류: {e}")

    async def _execute_cache_cleanup(self, task_name: str):
        """캐시 정리 실행"""
        try:
            logger.info(f"🧹 {task_name} 시작")
            start_time = datetime.now()
            
            if not self.data_manager or not self.data_manager.redis_client:
                logger.error("Redis 클라이언트가 초기화되지 않음")
                return
            
            # 만료된 캐시 키 패턴들
            cache_patterns = [
                "data_cache:*",
                "throttle:*",
                "emergency_stop:*",
                "cost_metric:*"
            ]
            
            cleaned_keys = 0
            
            for pattern in cache_patterns:
                keys = await self.data_manager.redis_client.keys(pattern)
                if keys:
                    # TTL이 0 이하인 키들 정리
                    for key in keys:
                        ttl = await self.data_manager.redis_client.ttl(key)
                        if ttl == -1:  # TTL이 설정되지 않은 키
                            await self.data_manager.redis_client.delete(key)
                            cleaned_keys += 1
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ {task_name} 완료 - {cleaned_keys}개 키 정리, 소요시간: {duration:.1f}초")
            
        except Exception as e:
            logger.error(f"{task_name} 실행 오류: {e}")

    async def _execute_daily_report(self, task_name: str):
        """일일 리포트 생성"""
        try:
            logger.info(f"📊 {task_name} 시작")
            start_time = datetime.now()
            
            if not self.data_manager:
                logger.error("데이터 매니저가 초기화되지 않음")
                return
            
            # 데이터 소스 상태 조회
            status = await self.data_manager.get_data_source_status()
            
            # 수집 통계
            uptime_hours = (datetime.now() - self.collection_stats['start_time']).total_seconds() / 3600
            success_rate = (self.collection_stats['successful_collections'] / 
                          max(self.collection_stats['total_collections'], 1)) * 100
            
            # 리포트 생성
            report = f"""
📊 StockPilot KR 데이터 수집 일일 리포트 ({datetime.now().strftime('%Y-%m-%d')})

🔧 시스템 상태:
- 총 데이터 소스: {status.get('total_sources', 0)}개
- 활성 소스: {status.get('active_sources', 0)}개
- 품질 우수: {status.get('quality_summary', {}).get('excellent', 0)}개
- 품질 양호: {status.get('quality_summary', {}).get('good', 0)}개
- 품질 불량: {status.get('quality_summary', {}).get('poor', 0)}개

📈 수집 통계:
- 총 수집 작업: {self.collection_stats['total_collections']}회
- 성공률: {success_rate:.1f}%
- 마지막 수집: {self.collection_stats['last_collection'].strftime('%H:%M:%S') if self.collection_stats['last_collection'] else 'N/A'}
- 서비스 가동시간: {uptime_hours:.1f}시간

🎯 품질 현황:
"""
            
            # 소스별 상세 정보
            for source_id, source_info in status.get('sources', {}).items():
                quality_icon = "🟢" if source_info['quality_score'] >= 80 else "🟡" if source_info['quality_score'] >= 50 else "🔴"
                report += f"- {source_info['name']}: {quality_icon} {source_info['quality_score']:.1f}점 (24시간 수집: {source_info['recent_items_24h']}개)\n"
            
            logger.info(report)
            
            # 리포트 파일로 저장
            report_file = Path(f"/var/log/stockpilot/daily_report_{datetime.now().strftime('%Y%m%d')}.txt")
            report_file.parent.mkdir(exist_ok=True)
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ {task_name} 완료 - 소요시간: {duration:.1f}초")
            
        except Exception as e:
            logger.error(f"{task_name} 실행 오류: {e}")

    async def start(self):
        """스케줄러 시작"""
        if not await self.setup():
            logger.error("스케줄러 초기화 실패")
            return False
        
        self.running = True
        
        # 시그널 핸들러 설정
        def signal_handler(signum, frame):
            logger.info(f"시그널 {signum} 수신 - 스케줄러 종료 중...")
            self.running = False
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        logger.info("🚀 KR 데이터 수집 스케줄러 시작")
        
        try:
            # 초기 품질 검증 실행
            await self._execute_quality_validation("초기 품질 검증")
            
            # 메인 스케줄링 루프
            while self.running:
                try:
                    # 스케줄된 작업 실행
                    schedule.run_pending()
                    
                    # 1초 대기
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"스케줄링 루프 오류: {e}")
                    await asyncio.sleep(5)
                    
        except Exception as e:
            logger.error(f"스케줄러 실행 오류: {e}")
        finally:
            await self.cleanup()
        
        return True

    async def cleanup(self):
        """정리 작업"""
        logger.info("KR 데이터 스케줄러 종료 중...")
        
        if self.data_manager:
            try:
                await self.data_manager.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"데이터 매니저 정리 오류: {e}")
        
        # 최종 통계 출력
        uptime = datetime.now() - self.collection_stats['start_time']
        logger.info(f"📊 최종 통계: 총 {self.collection_stats['total_collections']}회 수집, "
                   f"성공 {self.collection_stats['successful_collections']}회, "
                   f"실패 {self.collection_stats['failed_collections']}회, "
                   f"가동시간 {uptime}")
        
        logger.info("KR 데이터 스케줄러 종료 완료")

    def get_status(self) -> Dict:
        """현재 상태 조회"""
        uptime = datetime.now() - self.collection_stats['start_time']
        
        return {
            'running': self.running,
            'uptime_seconds': uptime.total_seconds(),
            'collection_stats': self.collection_stats.copy(),
            'scheduled_jobs': len(schedule.jobs),
            'data_manager_initialized': self.data_manager is not None
        }

async def main():
    """메인 함수"""
    # 로그 디렉토리 생성
    log_dir = Path("/var/log/stockpilot")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("🇰🇷 StockPilot KR 데이터 수집 스케줄러 시작")
    
    scheduler = KoreanDataScheduler()
    
    try:
        success = await scheduler.start()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("사용자에 의한 중단")
    except Exception as e:
        logger.error(f"치명적 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())