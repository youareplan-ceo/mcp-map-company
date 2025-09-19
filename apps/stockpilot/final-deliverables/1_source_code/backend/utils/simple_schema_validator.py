#!/usr/bin/env python3
"""
간단한 WebSocket 메시지 검증기
- 프로덕션 환경에서 안정적으로 작동
- 기본적인 타입 검증과 필수 필드 확인
- 높은 성능과 단순함
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

# 로깅 설정
logger = logging.getLogger(__name__)

class SimpleSchemaValidator:
    """간단한 스키마 검증기"""
    
    def __init__(self):
        """검증기 초기화"""
        self.supported_types = {
            "connection",
            "subscription", 
            "us_stocks",
            "exchange_rates",
            "market_status",
            "ai_signals",
            "error"
        }
    
    def validate_message(self, message: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        메시지 전체 구조 검증
        
        Args:
            message: 검증할 메시지
            
        Returns:
            (검증 성공 여부, 에러 메시지)
        """
        try:
            # 기본 구조 검증
            if not isinstance(message, dict):
                return False, "메시지가 딕셔너리가 아닙니다"
            
            # 필수 필드 확인
            required_fields = ["type", "payload", "timestamp"]
            for field in required_fields:
                if field not in message:
                    return False, f"필수 필드 '{field}'가 없습니다"
            
            message_type = message["type"]
            
            # 메시지 타입 검증
            if message_type not in self.supported_types:
                return False, f"지원하지 않는 메시지 타입: {message_type}"
            
            # 페이로드 검증
            payload = message["payload"]
            if not isinstance(payload, dict):
                return False, "payload가 딕셔너리가 아닙니다"
            
            # 타임스탬프 검증
            timestamp = message["timestamp"]
            if not isinstance(timestamp, str):
                return False, "timestamp가 문자열이 아닙니다"
            
            # 메시지 타입별 상세 검증
            return self._validate_payload_by_type(message_type, payload)
            
        except Exception as e:
            logger.error(f"메시지 검증 중 오류: {e}")
            return False, f"검증 중 오류: {str(e)}"
    
    def _validate_payload_by_type(self, message_type: str, payload: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """메시지 타입별 페이로드 검증"""
        
        if message_type == "connection":
            return self._validate_connection_payload(payload)
        elif message_type == "subscription":
            return self._validate_subscription_payload(payload)
        elif message_type == "us_stocks":
            return self._validate_us_stocks_payload(payload)
        elif message_type == "exchange_rates":
            return self._validate_exchange_rates_payload(payload)
        elif message_type == "market_status":
            return self._validate_market_status_payload(payload)
        elif message_type == "ai_signals":
            return self._validate_ai_signals_payload(payload)
        elif message_type == "error":
            return self._validate_error_payload(payload)
        else:
            return False, f"알 수 없는 메시지 타입: {message_type}"
    
    def _validate_connection_payload(self, payload: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """connection 페이로드 검증"""
        required_fields = ["client_id", "server_version", "services", "available_channels"]
        
        for field in required_fields:
            if field not in payload:
                return False, f"connection payload에 '{field}' 필드 누락"
        
        # services 검증
        services = payload["services"]
        if not isinstance(services, dict):
            return False, "services가 딕셔너리가 아닙니다"
        
        # available_channels 검증
        channels = payload["available_channels"]
        if not isinstance(channels, list):
            return False, "available_channels가 리스트가 아닙니다"
        
        return True, None
    
    def _validate_subscription_payload(self, payload: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """subscription 페이로드 검증"""
        required_fields = ["status", "events"]
        
        for field in required_fields:
            if field not in payload:
                return False, f"subscription payload에 '{field}' 필드 누락"
        
        # status 검증
        status = payload["status"]
        if status not in ["subscribed", "unsubscribed"]:
            return False, f"잘못된 subscription status: {status}"
        
        # events 검증
        events = payload["events"]
        if not isinstance(events, list):
            return False, "events가 리스트가 아닙니다"
        
        return True, None
    
    def _validate_us_stocks_payload(self, payload: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """us_stocks 페이로드 검증"""
        required_fields = ["stocks", "market_state", "count"]
        
        for field in required_fields:
            if field not in payload:
                return False, f"us_stocks payload에 '{field}' 필드 누락"
        
        # stocks 검증
        stocks = payload["stocks"]
        if not isinstance(stocks, list):
            return False, "stocks가 리스트가 아닙니다"
        
        # 각 주식 데이터 검증
        for i, stock in enumerate(stocks):
            if not isinstance(stock, dict):
                return False, f"stocks[{i}]가 딕셔너리가 아닙니다"
            
            stock_required = ["symbol", "company_name", "current_price", "change_percent", "volume"]
            for field in stock_required:
                if field not in stock:
                    return False, f"stocks[{i}]에 '{field}' 필드 누락"
        
        # market_state 검증
        market_state = payload["market_state"]
        valid_states = ["OPEN", "CLOSED", "PRE_MARKET", "AFTER_HOURS", "HOLIDAY"]
        if market_state not in valid_states:
            return False, f"잘못된 market_state: {market_state}"
        
        # count 검증
        count = payload["count"]
        if not isinstance(count, int) or count < 0:
            return False, "count가 음수가 아닌 정수가 아닙니다"
        
        return True, None
    
    def _validate_exchange_rates_payload(self, payload: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """exchange_rates 페이로드 검증"""
        required_fields = ["rates", "count"]
        
        for field in required_fields:
            if field not in payload:
                return False, f"exchange_rates payload에 '{field}' 필드 누락"
        
        # rates 검증
        rates = payload["rates"]
        if not isinstance(rates, list):
            return False, "rates가 리스트가 아닙니다"
        
        # 각 환율 데이터 검증
        for i, rate in enumerate(rates):
            if not isinstance(rate, dict):
                return False, f"rates[{i}]가 딕셔너리가 아닙니다"
            
            rate_required = ["pair", "rate", "timestamp"]
            for field in rate_required:
                if field not in rate:
                    return False, f"rates[{i}]에 '{field}' 필드 누락"
        
        return True, None
    
    def _validate_market_status_payload(self, payload: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """market_status 페이로드 검증"""
        if "markets" not in payload:
            return False, "market_status payload에 'markets' 필드 누락"
        
        markets = payload["markets"]
        if not isinstance(markets, list):
            return False, "markets가 리스트가 아닙니다"
        
        # 각 마켓 데이터 검증
        for i, market in enumerate(markets):
            if not isinstance(market, dict):
                return False, f"markets[{i}]가 딕셔너리가 아닙니다"
            
            market_required = ["market_code", "market_name", "status", "timezone"]
            for field in market_required:
                if field not in market:
                    return False, f"markets[{i}]에 '{field}' 필드 누락"
        
        return True, None
    
    def _validate_ai_signals_payload(self, payload: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """ai_signals 페이로드 검증"""
        required_fields = ["signals", "market", "count", "generated_at"]
        
        for field in required_fields:
            if field not in payload:
                return False, f"ai_signals payload에 '{field}' 필드 누락"
        
        # signals 검증
        signals = payload["signals"]
        if not isinstance(signals, list):
            return False, "signals가 리스트가 아닙니다"
        
        # 각 시그널 데이터 검증
        for i, signal in enumerate(signals):
            if not isinstance(signal, dict):
                return False, f"signals[{i}]가 딕셔너리가 아닙니다"
            
            signal_required = ["id", "symbol", "signal_type", "confidence", "strength", "current_price", "reasoning"]
            for field in signal_required:
                if field not in signal:
                    return False, f"signals[{i}]에 '{field}' 필드 누락"
            
            # signal_type 검증
            signal_type = signal["signal_type"]
            if signal_type not in ["BUY", "SELL", "HOLD"]:
                return False, f"잘못된 signal_type: {signal_type}"
            
            # confidence 검증
            confidence = signal["confidence"]
            if not isinstance(confidence, (int, float)) or not (0 <= confidence <= 1):
                return False, f"confidence가 0-1 범위의 숫자가 아닙니다: {confidence}"
        
        return True, None
    
    def _validate_error_payload(self, payload: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """error 페이로드 검증"""
        required_fields = ["code", "message"]
        
        for field in required_fields:
            if field not in payload:
                return False, f"error payload에 '{field}' 필드 누락"
        
        return True, None
    
    def get_supported_types(self) -> List[str]:
        """지원되는 메시지 타입 목록 반환"""
        return list(self.supported_types)

# 전역 검증기 인스턴스
_global_validator = None

def get_simple_validator() -> SimpleSchemaValidator:
    """전역 검증기 인스턴스 반환"""
    global _global_validator
    if _global_validator is None:
        _global_validator = SimpleSchemaValidator()
    return _global_validator

def validate_simple_message(message: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """편의 함수: 메시지 검증"""
    validator = get_simple_validator()
    return validator.validate_message(message)

# 테스트 함수
def test_simple_validator():
    """간단한 스키마 검증기 테스트"""
    print("=== 간단한 WebSocket 메시지 검증기 테스트 ===")
    
    validator = SimpleSchemaValidator()
    
    print(f"지원되는 메시지 타입: {validator.get_supported_types()}")
    
    # 테스트 메시지들
    test_messages = [
        {
            "name": "올바른 connection 메시지",
            "message": {
                "type": "connection",
                "payload": {
                    "client_id": "test_client_123",
                    "server_version": "1.0.0",
                    "services": {
                        "stock_data": True,
                        "currency_exchange": True,
                        "news_analysis": False,
                        "ai_signals": True
                    },
                    "available_channels": ["us_stocks", "exchange_rates", "ai_signals"]
                },
                "timestamp": "2024-01-01T12:00:00Z"
            }
        },
        {
            "name": "올바른 us_stocks 메시지",
            "message": {
                "type": "us_stocks",
                "payload": {
                    "stocks": [
                        {
                            "symbol": "AAPL",
                            "company_name": "Apple Inc.",
                            "current_price": 150.25,
                            "change_percent": 1.5,
                            "volume": 1000000
                        }
                    ],
                    "market_state": "OPEN",
                    "count": 1
                },
                "timestamp": "2024-01-01T12:00:00Z"
            }
        },
        {
            "name": "잘못된 메시지 (필수 필드 누락)",
            "message": {
                "type": "us_stocks",
                "payload": {
                    "stocks": [
                        {
                            "symbol": "AAPL"
                            # current_price, change_percent, volume 누락
                        }
                    ],
                    "market_state": "OPEN",
                    "count": 1
                },
                "timestamp": "2024-01-01T12:00:00Z"
            }
        },
        {
            "name": "올바른 ai_signals 메시지",
            "message": {
                "type": "ai_signals",
                "payload": {
                    "signals": [
                        {
                            "id": "signal_123",
                            "symbol": "AAPL",
                            "signal_type": "BUY",
                            "confidence": 0.85,
                            "strength": "HIGH",
                            "current_price": 150.0,
                            "reasoning": "강한 상승 추세"
                        }
                    ],
                    "market": "US",
                    "count": 1,
                    "generated_at": "2024-01-01T12:00:00Z"
                },
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }
    ]
    
    # 각 테스트 메시지 검증
    for test in test_messages:
        print(f"\n🧪 테스트: {test['name']}")
        is_valid, error = validator.validate_message(test['message'])
        
        if is_valid:
            print("   ✅ 검증 성공")
        else:
            print(f"   ❌ 검증 실패: {error}")
    
    print(f"\n📊 총 {len(validator.supported_types)}개 메시지 타입 지원")

if __name__ == "__main__":
    test_simple_validator()