#!/usr/bin/env python3
"""
WebSocket 메시지 스키마 검증기
- JSON Schema 기반 메시지 검증
- 채널별 페이로드 검증
- 프로덕션용 고성능 검증
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from jsonschema import Draft202012Validator, ValidationError, SchemaError

# 로깅 설정
logger = logging.getLogger(__name__)

class WebSocketSchemaValidator:
    """WebSocket 메시지 스키마 검증기"""
    
    def __init__(self, schema_path: Optional[str] = None):
        """
        스키마 검증기 초기화
        
        Args:
            schema_path: 스키마 파일 경로 (None이면 기본 경로 사용)
        """
        if schema_path is None:
            schema_path = Path(__file__).parent.parent / "schemas" / "websocket-schemas.json"
        
        self.schema_path = Path(schema_path)
        self.schemas = {}
        self.validators = {}
        self._load_schemas()
    
    def _load_schemas(self):
        """스키마 파일 로드 및 검증기 초기화"""
        try:
            with open(self.schema_path, 'r', encoding='utf-8') as f:
                master_schema = json.load(f)
            
            # 메인 스키마 검증
            Draft202012Validator.check_schema(master_schema)
            
            # 채널별 스키마 추출 및 검증기 생성
            defs = master_schema.get("$defs", {})
            
            for schema_name, schema_def in defs.items():
                self.schemas[schema_name] = schema_def
                # 단순히 스키마 정의만으로 검증기 생성
                self.validators[schema_name] = Draft202012Validator(schema_def)
            
            # 메시지 타입별 매핑
            self.message_type_mapping = {
                "connection": "connection_message",
                "subscription": "subscription_message", 
                "us_stocks": "us_stocks_message",
                "exchange_rates": "exchange_rates_message",
                "market_status": "market_status_message",
                "ai_signals": "ai_signals_message",
                "error": "error_message"
            }
            
            logger.info(f"✅ 스키마 로드 완료: {len(self.schemas)}개 메시지 타입")
            
        except Exception as e:
            logger.error(f"❌ 스키마 로드 실패: {e}")
            raise
    
    def validate_message(self, message: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        메시지 검증
        
        Args:
            message: 검증할 메시지
            
        Returns:
            (검증 성공 여부, 에러 메시지)
        """
        try:
            message_type = message.get("type")
            if not message_type:
                return False, "메시지 타입이 없습니다"
            
            schema_name = self.message_type_mapping.get(message_type)
            if not schema_name:
                return False, f"지원하지 않는 메시지 타입: {message_type}"
            
            validator = self.validators.get(schema_name)
            if not validator:
                return False, f"스키마 검증기를 찾을 수 없음: {schema_name}"
            
            # 스키마 검증 실행
            validator.validate(message)
            return True, None
            
        except ValidationError as e:
            error_msg = f"스키마 검증 실패: {e.message}"
            if e.path:
                error_msg += f" (경로: {'.'.join(str(p) for p in e.path)})"
            logger.warning(f"⚠️ {error_msg}")
            return False, error_msg
            
        except Exception as e:
            logger.error(f"❌ 스키마 검증 중 오류: {e}")
            return False, f"검증 중 오류: {str(e)}"
    
    def validate_payload(self, message_type: str, payload: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        페이로드만 검증 (메시지 래퍼 없이)
        
        Args:
            message_type: 메시지 타입
            payload: 검증할 페이로드
            
        Returns:
            (검증 성공 여부, 에러 메시지)
        """
        # 임시 메시지 생성하여 검증
        temp_message = {
            "type": message_type,
            "payload": payload,
            "timestamp": "2024-01-01T00:00:00Z"  # 임시 타임스탬프
        }
        
        return self.validate_message(temp_message)
    
    def get_schema(self, message_type: str) -> Optional[Dict]:
        """
        특정 메시지 타입의 스키마 반환
        
        Args:
            message_type: 메시지 타입
            
        Returns:
            스키마 정의 또는 None
        """
        schema_name = self.message_type_mapping.get(message_type)
        return self.schemas.get(schema_name) if schema_name else None
    
    def get_supported_types(self) -> list[str]:
        """지원되는 메시지 타입 목록 반환"""
        return list(self.message_type_mapping.keys())
    
    def reload_schemas(self):
        """스키마 파일 재로드"""
        logger.info("🔄 스키마 재로드 중...")
        self.schemas.clear()
        self.validators.clear()
        self._load_schemas()

# 전역 검증기 인스턴스
_global_validator = None

def get_schema_validator() -> WebSocketSchemaValidator:
    """전역 스키마 검증기 인스턴스 반환"""
    global _global_validator
    if _global_validator is None:
        _global_validator = WebSocketSchemaValidator()
    return _global_validator

def validate_websocket_message(message: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """편의 함수: 메시지 검증"""
    validator = get_schema_validator()
    return validator.validate_message(message)

def validate_websocket_payload(message_type: str, payload: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """편의 함수: 페이로드 검증"""
    validator = get_schema_validator()
    return validator.validate_payload(message_type, payload)

# 테스트 함수
def test_schema_validator():
    """스키마 검증기 테스트"""
    print("=== WebSocket 메시지 스키마 검증기 테스트 ===")
    
    validator = WebSocketSchemaValidator()
    
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
    
    print(f"\n📊 총 {len(validator.schemas)}개 스키마 로드됨")

if __name__ == "__main__":
    test_schema_validator()