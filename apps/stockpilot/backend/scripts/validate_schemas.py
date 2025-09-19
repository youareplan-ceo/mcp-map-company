#!/usr/bin/env python3
"""
스키마 검증 스크립트
CI/CD 파이프라인에서 WebSocket 메시지 스키마 유효성 검사
"""

import sys
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple

def load_schema_file(schema_path: Path) -> Dict[str, Any]:
    """스키마 파일 로드"""
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        print(f"✅ 스키마 파일 로드 성공: {schema_path}")
        return schema
    except FileNotFoundError:
        print(f"❌ 스키마 파일을 찾을 수 없습니다: {schema_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ 스키마 파일 JSON 파싱 오류: {schema_path}")
        print(f"   오류 내용: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 스키마 파일 로드 중 예상치 못한 오류: {e}")
        sys.exit(1)

def validate_schema_structure(schema: Dict[str, Any]) -> List[str]:
    """스키마 구조 유효성 검사"""
    errors = []
    
    # 필수 필드 검사
    required_fields = ["$schema", "title", "description", "version", "definitions", "oneOf", "$defs"]
    for field in required_fields:
        if field not in schema:
            errors.append(f"필수 필드 누락: {field}")
    
    # definitions 구조 검사
    if "definitions" in schema:
        definitions = schema["definitions"]
        if "timestamp" not in definitions:
            errors.append("definitions.timestamp 필드 누락")
        if "base_message" not in definitions:
            errors.append("definitions.base_message 필드 누락")
    
    # $defs 구조 검사
    if "$defs" in schema:
        defs = schema["$defs"]
        expected_message_types = [
            "connection_message",
            "subscription_message", 
            "us_stocks_message",
            "kr_stocks_message",
            "exchange_rates_message",
            "market_status_message",
            "ai_signals_message",
            "kr_news_message",
            "error_message"
        ]
        
        for msg_type in expected_message_types:
            if msg_type not in defs:
                errors.append(f"$defs.{msg_type} 정의 누락")
            else:
                # 각 메시지 타입의 구조 검사
                msg_def = defs[msg_type]
                if "allOf" not in msg_def:
                    errors.append(f"$defs.{msg_type}.allOf 구조 누락")
    
    return errors

def validate_message_types(schema: Dict[str, Any]) -> List[str]:
    """메시지 타입별 상세 검증"""
    errors = []
    
    if "$defs" not in schema:
        return ["$defs 필드가 없어서 메시지 타입 검증을 수행할 수 없습니다"]
    
    defs = schema["$defs"]
    
    # 각 메시지 타입별 검증
    message_validations = {
        "us_stocks_message": ["stocks", "market", "count"],
        "kr_stocks_message": ["stocks", "market", "count"],
        "exchange_rates_message": ["rates", "count"],
        "market_status_message": ["market", "state", "local_time"],
        "ai_signals_message": ["signals", "market", "count", "generated_at"],
        "kr_news_message": ["news", "count"],
        "error_message": ["code", "message"]
    }
    
    for msg_type, required_payload_fields in message_validations.items():
        if msg_type in defs:
            msg_def = defs[msg_type]
            try:
                # allOf 구조에서 payload 검사
                if "allOf" in msg_def and len(msg_def["allOf"]) > 1:
                    payload_def = msg_def["allOf"][1]
                    if "properties" in payload_def and "payload" in payload_def["properties"]:
                        payload_props = payload_def["properties"]["payload"]
                        if "properties" in payload_props:
                            payload_fields = payload_props["properties"]
                            for field in required_payload_fields:
                                if field not in payload_fields:
                                    errors.append(f"{msg_type} payload에 필수 필드 누락: {field}")
            except (KeyError, IndexError) as e:
                errors.append(f"{msg_type} 구조 분석 중 오류: {e}")
    
    return errors

def validate_enum_values(schema: Dict[str, Any]) -> List[str]:
    """열거형 값들 검증"""
    errors = []
    
    if "$defs" not in schema:
        return errors
    
    defs = schema["$defs"]
    
    # 예상되는 열거형 값들 검사
    expected_enums = {
        "ai_signals_message": {
            "signal_type": ["BUY", "SELL", "HOLD"],
            "strength": ["HIGH", "MEDIUM", "LOW"],
            "risk_level": ["HIGH", "MEDIUM", "LOW"]
        },
        "kr_stocks_message": {
            "market": ["KOSPI", "KOSDAQ"]
        },
        "kr_news_message": {
            "sentiment": ["POSITIVE", "NEGATIVE", "NEUTRAL"]
        }
    }
    
    for msg_type, expected_fields in expected_enums.items():
        if msg_type in defs:
            for field_name, expected_values in expected_fields.items():
                # 깊은 구조에서 enum 값 찾기는 복잡하므로, 문자열 검색으로 대체
                msg_str = json.dumps(defs[msg_type])
                if f'"{field_name}"' in msg_str:
                    for expected_val in expected_values:
                        if f'"{expected_val}"' not in msg_str:
                            errors.append(f"{msg_type}.{field_name}에 예상 값 누락: {expected_val}")
    
    return errors

def validate_schema_references(schema: Dict[str, Any]) -> List[str]:
    """스키마 참조 유효성 검사"""
    errors = []
    
    # $ref 참조 검사
    schema_str = json.dumps(schema)
    refs = []
    
    # $ref 패턴 찾기
    import re
    ref_pattern = r'"#/definitions/(\w+)"'
    definition_refs = re.findall(ref_pattern, schema_str)
    
    ref_pattern = r'"#/\$defs/(\w+)"'
    defs_refs = re.findall(ref_pattern, schema_str)
    
    # definitions 참조 검사
    if "definitions" in schema:
        definitions = schema["definitions"]
        for ref in definition_refs:
            if ref not in definitions:
                errors.append(f"정의되지 않은 definitions 참조: {ref}")
    
    # $defs 참조 검사
    if "$defs" in schema:
        defs = schema["$defs"]
        for ref in defs_refs:
            if ref not in defs:
                errors.append(f"정의되지 않은 $defs 참조: {ref}")
    
    return errors

def main():
    """메인 검증 함수"""
    print("🔍 StockPilot WebSocket 스키마 검증 시작")
    print("=" * 50)
    
    # 스키마 파일 경로
    backend_dir = Path(__file__).parent.parent
    schema_path = backend_dir / "schemas" / "websocket-schemas.json"
    
    # 스키마 파일 로드
    schema = load_schema_file(schema_path)
    
    all_errors = []
    
    # 1. 기본 구조 검증
    print("\n1. 기본 구조 검증 중...")
    structure_errors = validate_schema_structure(schema)
    if structure_errors:
        print(f"   ❌ 구조 오류 {len(structure_errors)}개 발견")
        for error in structure_errors:
            print(f"      - {error}")
        all_errors.extend(structure_errors)
    else:
        print("   ✅ 기본 구조 검증 통과")
    
    # 2. 메시지 타입 검증
    print("\n2. 메시지 타입 검증 중...")
    message_errors = validate_message_types(schema)
    if message_errors:
        print(f"   ❌ 메시지 타입 오류 {len(message_errors)}개 발견")
        for error in message_errors:
            print(f"      - {error}")
        all_errors.extend(message_errors)
    else:
        print("   ✅ 메시지 타입 검증 통과")
    
    # 3. 열거형 값 검증
    print("\n3. 열거형 값 검증 중...")
    enum_errors = validate_enum_values(schema)
    if enum_errors:
        print(f"   ❌ 열거형 오류 {len(enum_errors)}개 발견")
        for error in enum_errors:
            print(f"      - {error}")
        all_errors.extend(enum_errors)
    else:
        print("   ✅ 열거형 값 검증 통과")
    
    # 4. 스키마 참조 검증
    print("\n4. 스키마 참조 검증 중...")
    ref_errors = validate_schema_references(schema)
    if ref_errors:
        print(f"   ❌ 참조 오류 {len(ref_errors)}개 발견")
        for error in ref_errors:
            print(f"      - {error}")
        all_errors.extend(ref_errors)
    else:
        print("   ✅ 스키마 참조 검증 통과")
    
    # 검증 결과 출력
    print("\n" + "=" * 50)
    if all_errors:
        print(f"❌ 스키마 검증 실패: 총 {len(all_errors)}개 오류 발견")
        print("\n전체 오류 목록:")
        for i, error in enumerate(all_errors, 1):
            print(f"{i}. {error}")
        sys.exit(1)
    else:
        print("✅ 스키마 검증 완료: 모든 검사 통과")
        print(f"   - 스키마 버전: {schema.get('version', 'Unknown')}")
        print(f"   - 메시지 타입 수: {len(schema.get('$defs', {}))}")
        print(f"   - 파일 크기: {os.path.getsize(schema_path)} bytes")
    
    print("\n🎉 스키마 검증이 성공적으로 완료되었습니다!")

if __name__ == "__main__":
    main()