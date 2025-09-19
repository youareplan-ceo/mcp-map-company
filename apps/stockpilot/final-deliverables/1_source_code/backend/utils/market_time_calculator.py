#!/usr/bin/env python3
"""
미국 주식 시장 시간 계산기
- zoneinfo 기반 정확한 타임존 처리
- DST(일광절약시간) 자동 전환
- 공식 휴장일/조기폐장 반영
- 프로덕션 준비된 시장 상태 계산
"""

from datetime import datetime, time, date
from zoneinfo import ZoneInfo
from typing import Dict, List, Tuple, Optional
import logging
from enum import Enum

# 로깅 설정
logger = logging.getLogger(__name__)

class MarketStatus(Enum):
    """시장 상태 열거형"""
    CLOSED = "CLOSED"           # 휴장
    PRE_MARKET = "PRE_MARKET"   # 시간외 거래 (오전)
    OPEN = "OPEN"               # 정규 거래
    AFTER_HOURS = "AFTER_HOURS" # 시간외 거래 (오후)
    HOLIDAY = "HOLIDAY"         # 공휴일 휴장

class USMarketTimeCalculator:
    """미국 주식 시장 시간 계산기"""
    
    # 뉴욕 증권거래소 타임존 (EST/EDT 자동 전환)
    NYSE_TZ = ZoneInfo("America/New_York")
    
    # 정규 거래 시간 (현지 시간 기준)
    MARKET_OPEN_TIME = time(9, 30)   # 9:30 AM
    MARKET_CLOSE_TIME = time(16, 0)  # 4:00 PM
    
    # 시간외 거래 시간
    PRE_MARKET_START = time(4, 0)    # 4:00 AM
    AFTER_HOURS_END = time(20, 0)    # 8:00 PM
    
    # 2024년 미국 주식 시장 휴장일 (NYSE/NASDAQ 공식 일정)
    MARKET_HOLIDAYS_2024 = {
        date(2024, 1, 1),    # 신정
        date(2024, 1, 15),   # 마틴 루터 킹 데이
        date(2024, 2, 19),   # 대통령의 날
        date(2024, 3, 29),   # 성금요일
        date(2024, 5, 27),   # 메모리얼 데이
        date(2024, 6, 19),   # 준틴스
        date(2024, 7, 4),    # 독립기념일
        date(2024, 9, 2),    # 노동절
        date(2024, 11, 28),  # 추수감사절
        date(2024, 12, 25),  # 성탄절
    }
    
    # 2025년 미국 주식 시장 휴장일
    MARKET_HOLIDAYS_2025 = {
        date(2025, 1, 1),    # 신정
        date(2025, 1, 20),   # 마틴 루터 킹 데이
        date(2025, 2, 17),   # 대통령의 날
        date(2025, 4, 18),   # 성금요일
        date(2025, 5, 26),   # 메모리얼 데이
        date(2025, 6, 19),   # 준틴스
        date(2025, 7, 4),    # 독립기념일
        date(2025, 9, 1),    # 노동절
        date(2025, 11, 27),  # 추수감사절
        date(2025, 12, 25),  # 성탄절
    }
    
    # 조기 폐장일 (1:00 PM 폐장)
    EARLY_CLOSE_DATES_2024 = {
        date(2024, 7, 3),    # 독립기념일 전날
        date(2024, 11, 29),  # 추수감사절 다음날 (블랙 프라이데이)
        date(2024, 12, 24),  # 성탄절 전날
    }
    
    EARLY_CLOSE_DATES_2025 = {
        date(2025, 7, 3),    # 독립기념일 전날
        date(2025, 11, 28),  # 추수감사절 다음날
        date(2025, 12, 24),  # 성탄절 전날
    }
    
    def __init__(self):
        """시장 시간 계산기 초기화"""
        self.all_holidays = (
            self.MARKET_HOLIDAYS_2024 | 
            self.MARKET_HOLIDAYS_2025
        )
        self.all_early_close = (
            self.EARLY_CLOSE_DATES_2024 | 
            self.EARLY_CLOSE_DATES_2025
        )
        
    def get_market_status(self, utc_time: Optional[datetime] = None) -> Dict:
        """
        현재 시장 상태 계산
        
        Args:
            utc_time: UTC 시간 (None이면 현재 시간 사용)
            
        Returns:
            시장 상태 정보 딕셔너리
        """
        if utc_time is None:
            utc_time = datetime.now(ZoneInfo("UTC"))
            
        # UTC를 뉴욕 시간으로 변환
        ny_time = utc_time.astimezone(self.NYSE_TZ)
        ny_date = ny_time.date()
        
        logger.debug(f"시장 상태 계산: UTC {utc_time.isoformat()} -> NY {ny_time.isoformat()}")
        
        # 주말 체크 (토요일=5, 일요일=6)
        if ny_time.weekday() >= 5:
            return self._create_status_response(
                MarketStatus.CLOSED,
                ny_time,
                "주말 휴장",
                next_open=self._get_next_market_open(ny_time)
            )
        
        # 공휴일 체크
        if ny_date in self.all_holidays:
            return self._create_status_response(
                MarketStatus.HOLIDAY,
                ny_time,
                "공휴일 휴장",
                next_open=self._get_next_market_open(ny_time)
            )
        
        # 조기 폐장일 체크
        is_early_close = ny_date in self.all_early_close
        market_close_time = time(13, 0) if is_early_close else self.MARKET_CLOSE_TIME
        
        # 현재 시간으로 시장 상태 판단
        current_time = ny_time.time()
        
        if current_time < self.PRE_MARKET_START:
            # 새벽 (4:00 AM 이전)
            return self._create_status_response(
                MarketStatus.CLOSED,
                ny_time,
                "새벽 휴장",
                next_open=self._get_next_market_open(ny_time)
            )
        elif current_time < self.MARKET_OPEN_TIME:
            # 시간외 거래 (오전 4:00 - 9:30)
            return self._create_status_response(
                MarketStatus.PRE_MARKET,
                ny_time,
                "시간외 거래 (오전)",
                closes_at=self._combine_date_time(ny_date, self.MARKET_OPEN_TIME)
            )
        elif current_time < market_close_time:
            # 정규 거래 시간
            close_reason = "조기 폐장" if is_early_close else "정규 거래 종료"
            return self._create_status_response(
                MarketStatus.OPEN,
                ny_time,
                f"정규 거래 중 ({close_reason} 예정)",
                closes_at=self._combine_date_time(ny_date, market_close_time)
            )
        elif current_time < self.AFTER_HOURS_END and not is_early_close:
            # 시간외 거래 (오후 4:00 - 8:00) - 조기폐장일엔 시간외거래 없음
            return self._create_status_response(
                MarketStatus.AFTER_HOURS,
                ny_time,
                "시간외 거래 (오후)",
                closes_at=self._combine_date_time(ny_date, self.AFTER_HOURS_END)
            )
        else:
            # 거래 종료
            return self._create_status_response(
                MarketStatus.CLOSED,
                ny_time,
                "거래 시간 종료",
                next_open=self._get_next_market_open(ny_time)
            )
    
    def _create_status_response(
        self, 
        status: MarketStatus, 
        ny_time: datetime,
        description: str,
        next_open: Optional[datetime] = None,
        closes_at: Optional[datetime] = None
    ) -> Dict:
        """시장 상태 응답 데이터 생성"""
        
        # DST 정보 확인
        is_dst = ny_time.dst().total_seconds() > 0
        timezone_name = "EDT" if is_dst else "EST"
        utc_offset = "-04:00" if is_dst else "-05:00"
        
        response = {
            "status": status.value,
            "description": description,
            "market_code": "US",
            "market_name": "미국 주식 시장 (NYSE/NASDAQ)",
            "timezone": "America/New_York",
            "timezone_name": timezone_name,
            "utc_offset": utc_offset,
            "is_dst": is_dst,
            "local_time": ny_time.isoformat(),
            "timestamp": datetime.now(ZoneInfo("UTC")).isoformat(),
            "regular_hours": {
                "open": "09:30:00",
                "close": "16:00:00"
            },
            "extended_hours": {
                "pre_market_start": "04:00:00",
                "after_hours_end": "20:00:00"
            }
        }
        
        # 다음 개장 시간
        if next_open:
            response["next_open"] = {
                "datetime": next_open.isoformat(),
                "timezone": timezone_name
            }
        
        # 폐장 예정 시간
        if closes_at:
            response["closes_at"] = {
                "datetime": closes_at.isoformat(),
                "timezone": timezone_name
            }
        
        return response
    
    def _combine_date_time(self, date_part: date, time_part: time) -> datetime:
        """날짜와 시간을 뉴욕 타임존 datetime으로 결합"""
        return datetime.combine(date_part, time_part, tzinfo=self.NYSE_TZ)
    
    def _get_next_market_open(self, from_time: datetime) -> datetime:
        """다음 시장 개장 시간 계산"""
        ny_time = from_time.astimezone(self.NYSE_TZ)
        check_date = ny_time.date()
        
        # 최대 10일 검색 (안전장치)
        for days_ahead in range(10):
            if days_ahead > 0:
                check_date = ny_time.date()
                check_date = check_date.replace(day=check_date.day + days_ahead)
            
            # 주말과 공휴일 건너뛰기
            check_datetime = datetime.combine(check_date, self.MARKET_OPEN_TIME, tzinfo=self.NYSE_TZ)
            
            if (check_datetime.weekday() < 5 and  # 평일
                check_date not in self.all_holidays and  # 공휴일 아님
                check_datetime > ny_time):  # 미래 시간
                return check_datetime
        
        # 찾지 못한 경우 (예외 상황)
        logger.error("다음 시장 개장 시간을 찾을 수 없음")
        return ny_time.replace(hour=9, minute=30, second=0, microsecond=0)
    
    def is_market_day(self, check_date: Optional[date] = None) -> bool:
        """지정된 날짜가 시장 개장일인지 확인"""
        if check_date is None:
            check_date = datetime.now(self.NYSE_TZ).date()
        
        # 주말과 공휴일이 아닌 경우 시장 개장일
        return (check_date.weekday() < 5 and 
                check_date not in self.all_holidays)
    
    def get_market_schedule_info(self) -> Dict:
        """시장 일정 정보 반환"""
        return {
            "regular_hours": {
                "open": self.MARKET_OPEN_TIME.strftime("%H:%M:%S"),
                "close": self.MARKET_CLOSE_TIME.strftime("%H:%M:%S")
            },
            "extended_hours": {
                "pre_market_start": self.PRE_MARKET_START.strftime("%H:%M:%S"),
                "after_hours_end": self.AFTER_HOURS_END.strftime("%H:%M:%S")
            },
            "timezone": "America/New_York",
            "holidays_2024": [d.isoformat() for d in sorted(self.MARKET_HOLIDAYS_2024)],
            "holidays_2025": [d.isoformat() for d in sorted(self.MARKET_HOLIDAYS_2025)],
            "early_close_2024": [d.isoformat() for d in sorted(self.EARLY_CLOSE_DATES_2024)],
            "early_close_2025": [d.isoformat() for d in sorted(self.EARLY_CLOSE_DATES_2025)]
        }

# 전역 인스턴스
market_calculator = USMarketTimeCalculator()

def get_current_market_status() -> Dict:
    """현재 시장 상태 반환 (편의 함수)"""
    return market_calculator.get_market_status()

def is_market_open() -> bool:
    """현재 정규 거래 시간인지 확인 (편의 함수)"""
    status = market_calculator.get_market_status()
    return status["status"] == MarketStatus.OPEN.value

# 테스트 함수
def test_market_calculator():
    """시장 시간 계산기 테스트"""
    print("=== 미국 주식 시장 시간 계산기 테스트 ===")
    
    calc = USMarketTimeCalculator()
    
    # 현재 상태
    current_status = calc.get_market_status()
    print(f"\n📊 현재 시장 상태:")
    print(f"   상태: {current_status['status']}")
    print(f"   설명: {current_status['description']}")
    print(f"   현지시간: {current_status['local_time']}")
    print(f"   타임존: {current_status['timezone_name']} ({current_status['utc_offset']})")
    print(f"   일광절약시간: {current_status['is_dst']}")
    
    if "next_open" in current_status:
        print(f"   다음 개장: {current_status['next_open']['datetime']}")
    
    if "closes_at" in current_status:
        print(f"   폐장 예정: {current_status['closes_at']['datetime']}")
    
    # 시장 일정 정보
    schedule = calc.get_market_schedule_info()
    print(f"\n📅 시장 일정:")
    print(f"   정규 거래: {schedule['regular_hours']['open']} - {schedule['regular_hours']['close']}")
    print(f"   시간외 거래: {schedule['extended_hours']['pre_market_start']} - {schedule['extended_hours']['after_hours_end']}")
    print(f"   2024년 휴장일: {len(schedule['holidays_2024'])}일")
    print(f"   2025년 휴장일: {len(schedule['holidays_2025'])}일")

if __name__ == "__main__":
    test_market_calculator()