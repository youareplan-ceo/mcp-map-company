#!/usr/bin/env python3
"""
StockPilot 환경 변수 검증 스크립트
환경 변수가 올바르게 설정되었는지 확인하고 보고서 생성
"""

import os
import re
import sys
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ValidationLevel(Enum):
    """검증 레벨"""
    REQUIRED = "required"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"


class ValidationResult(Enum):
    """검증 결과"""
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class ValidationRule:
    """환경 변수 검증 규칙"""
    name: str
    description: str
    level: ValidationLevel
    validator: callable
    default_value: Optional[str] = None
    example_value: Optional[str] = None


class EnvironmentValidator:
    """환경 변수 검증 클래스"""
    
    def __init__(self):
        self.rules: List[ValidationRule] = []
        self.results: List[Tuple[ValidationRule, ValidationResult, str]] = []
        
    def add_rule(self, rule: ValidationRule):
        """검증 규칙 추가"""
        self.rules.append(rule)
        
    def validate_all(self) -> bool:
        """모든 환경 변수 검증 실행"""
        self.results.clear()
        all_passed = True
        
        for rule in self.rules:
            try:
                result, message = self._validate_rule(rule)
                self.results.append((rule, result, message))
                
                if rule.level == ValidationLevel.REQUIRED and result == ValidationResult.FAIL:
                    all_passed = False
                    
            except Exception as e:
                self.results.append((rule, ValidationResult.FAIL, f"검증 중 오류 발생: {str(e)}"))
                if rule.level == ValidationLevel.REQUIRED:
                    all_passed = False
                    
        return all_passed
    
    def _validate_rule(self, rule: ValidationRule) -> Tuple[ValidationResult, str]:
        """개별 규칙 검증"""
        value = os.getenv(rule.name)
        
        if value is None:
            if rule.level == ValidationLevel.REQUIRED:
                return ValidationResult.FAIL, f"필수 환경 변수가 설정되지 않음"
            elif rule.level == ValidationLevel.RECOMMENDED:
                return ValidationResult.WARN, f"권장 환경 변수가 설정되지 않음"
            else:
                return ValidationResult.PASS, f"선택적 환경 변수 (미설정)"
                
        try:
            is_valid = rule.validator(value)
            if is_valid:
                return ValidationResult.PASS, "검증 성공"
            else:
                return ValidationResult.FAIL, "검증 실패: 값이 유효하지 않음"
        except Exception as e:
            return ValidationResult.FAIL, f"검증 실패: {str(e)}"
    
    def generate_report(self) -> str:
        """검증 결과 보고서 생성"""
        if not self.results:
            return "검증 결과가 없습니다. validate_all()을 먼저 실행하세요."
            
        report = []
        report.append("=" * 80)
        report.append("StockPilot 환경 변수 검증 보고서")
        report.append("=" * 80)
        report.append("")
        
        # 요약 정보
        total_count = len(self.results)
        pass_count = sum(1 for _, result, _ in self.results if result == ValidationResult.PASS)
        warn_count = sum(1 for _, result, _ in self.results if result == ValidationResult.WARN)
        fail_count = sum(1 for _, result, _ in self.results if result == ValidationResult.FAIL)
        
        report.append(f"총 검증 항목: {total_count}")
        report.append(f"성공: {pass_count}, 경고: {warn_count}, 실패: {fail_count}")
        report.append("")
        
        # 실패 항목
        if fail_count > 0:
            report.append("🔴 실패 항목:")
            report.append("-" * 40)
            for rule, result, message in self.results:
                if result == ValidationResult.FAIL:
                    report.append(f"• {rule.name} ({rule.level.value})")
                    report.append(f"  설명: {rule.description}")
                    report.append(f"  오류: {message}")
                    if rule.example_value:
                        report.append(f"  예시값: {rule.example_value}")
                    report.append("")
        
        # 경고 항목
        if warn_count > 0:
            report.append("🟡 경고 항목:")
            report.append("-" * 40)
            for rule, result, message in self.results:
                if result == ValidationResult.WARN:
                    report.append(f"• {rule.name} ({rule.level.value})")
                    report.append(f"  설명: {rule.description}")
                    report.append(f"  경고: {message}")
                    if rule.example_value:
                        report.append(f"  예시값: {rule.example_value}")
                    report.append("")
        
        # 성공 항목 (간략히)
        if pass_count > 0:
            report.append("✅ 성공 항목:")
            report.append("-" * 40)
            for rule, result, message in self.results:
                if result == ValidationResult.PASS:
                    report.append(f"• {rule.name}")
            report.append("")
        
        return "\n".join(report)


# 검증 함수들
def validate_database_url(value: str) -> bool:
    """데이터베이스 URL 형식 검증"""
    pattern = r'^postgresql://[\w-]+:[\w-]+@[\w.-]+:\d+/[\w-]+(\?.*)?$'
    return bool(re.match(pattern, value))


def validate_redis_url(value: str) -> bool:
    """Redis URL 형식 검증"""
    pattern = r'^redis://(:[^@]+@)?[\w.-]+:\d+(\/\d+)?$'
    return bool(re.match(pattern, value))


def validate_jwt_secret(value: str) -> bool:
    """JWT 시크릿 키 강도 검증"""
    return len(value) >= 32 and value != "your_super_secure_jwt_secret_key_here_at_least_32_chars"


def validate_api_key(value: str) -> bool:
    """API 키 형식 검증"""
    return len(value) > 10 and not value.startswith("your_")


def validate_port(value: str) -> bool:
    """포트 번호 검증"""
    try:
        port = int(value)
        return 1 <= port <= 65535
    except ValueError:
        return False


def validate_boolean(value: str) -> bool:
    """불린 값 검증"""
    return value.lower() in ['true', 'false']


def validate_environment(value: str) -> bool:
    """환경 타입 검증"""
    return value.lower() in ['development', 'staging', 'production']


def validate_log_level(value: str) -> bool:
    """로그 레벨 검증"""
    return value.upper() in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']


def validate_url(value: str) -> bool:
    """URL 형식 검증"""
    pattern = r'^https?://[\w.-]+(:\d+)?(/.*)?$'
    return bool(re.match(pattern, value))


def validate_email(value: str) -> bool:
    """이메일 형식 검증"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, value))


def setup_validation_rules() -> EnvironmentValidator:
    """검증 규칙 설정"""
    validator = EnvironmentValidator()
    
    # 필수 환경 변수들
    validator.add_rule(ValidationRule(
        "DATABASE_URL",
        "PostgreSQL 데이터베이스 연결 URL",
        ValidationLevel.REQUIRED,
        validate_database_url,
        example_value="postgresql://user:pass@localhost:5432/dbname"
    ))
    
    validator.add_rule(ValidationRule(
        "REDIS_URL",
        "Redis 캐시 서버 연결 URL",
        ValidationLevel.REQUIRED,
        validate_redis_url,
        example_value="redis://localhost:6379/0"
    ))
    
    validator.add_rule(ValidationRule(
        "JWT_SECRET_KEY",
        "JWT 토큰 서명에 사용할 비밀 키",
        ValidationLevel.REQUIRED,
        validate_jwt_secret,
        example_value="32자 이상의 강력한 랜덤 문자열"
    ))
    
    validator.add_rule(ValidationRule(
        "ENVIRONMENT",
        "애플리케이션 실행 환경",
        ValidationLevel.REQUIRED,
        validate_environment,
        default_value="development",
        example_value="development|staging|production"
    ))
    
    # 권장 환경 변수들
    validator.add_rule(ValidationRule(
        "OPENAI_API_KEY",
        "OpenAI API 키 (AI 기능 사용시 필요)",
        ValidationLevel.RECOMMENDED,
        validate_api_key,
        example_value="sk-..."
    ))
    
    validator.add_rule(ValidationRule(
        "KIS_APP_KEY",
        "한국투자증권 API 키",
        ValidationLevel.RECOMMENDED,
        validate_api_key,
        example_value="한국투자증권에서 발급받은 APP KEY"
    ))
    
    validator.add_rule(ValidationRule(
        "KIS_APP_SECRET",
        "한국투자증권 API 시크릿",
        ValidationLevel.RECOMMENDED,
        validate_api_key,
        example_value="한국투자증권에서 발급받은 APP SECRET"
    ))
    
    # 선택적 환경 변수들
    validator.add_rule(ValidationRule(
        "PORT",
        "웹 서버 포트 번호",
        ValidationLevel.OPTIONAL,
        validate_port,
        default_value="8000",
        example_value="8000"
    ))
    
    validator.add_rule(ValidationRule(
        "LOG_LEVEL",
        "로깅 레벨",
        ValidationLevel.OPTIONAL,
        validate_log_level,
        default_value="INFO",
        example_value="DEBUG|INFO|WARNING|ERROR|CRITICAL"
    ))
    
    validator.add_rule(ValidationRule(
        "DEBUG",
        "디버그 모드 활성화 여부",
        ValidationLevel.OPTIONAL,
        validate_boolean,
        default_value="false",
        example_value="true|false"
    ))
    
    validator.add_rule(ValidationRule(
        "CORS_ORIGINS",
        "CORS 허용 도메인 목록",
        ValidationLevel.OPTIONAL,
        lambda x: all(validate_url(url.strip()) for url in x.split(',')),
        default_value="http://localhost:3000",
        example_value="https://app.stockpilot.ai,https://www.stockpilot.ai"
    ))
    
    validator.add_rule(ValidationRule(
        "SMTP_USERNAME",
        "이메일 알림용 SMTP 사용자명",
        ValidationLevel.OPTIONAL,
        validate_email,
        example_value="noreply@stockpilot.ai"
    ))
    
    validator.add_rule(ValidationRule(
        "SENTRY_DSN",
        "Sentry 오류 추적 DSN",
        ValidationLevel.OPTIONAL,
        validate_url,
        example_value="https://xxx@sentry.io/xxx"
    ))
    
    return validator


def main():
    """메인 실행 함수"""
    print("StockPilot 환경 변수 검증을 시작합니다...")
    print("")
    
    # .env 파일 로드 시도
    env_file_paths = ['.env', '../.env', '../../.env']
    env_loaded = False
    
    for env_path in env_file_paths:
        if os.path.exists(env_path):
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            if key not in os.environ:  # 시스템 환경 변수 우선
                                os.environ[key] = value
                print(f"환경 변수 파일 로드됨: {env_path}")
                env_loaded = True
                break
            except Exception as e:
                print(f"환경 변수 파일 로드 실패 ({env_path}): {e}")
    
    if not env_loaded:
        print("⚠️  .env 파일을 찾을 수 없습니다. 시스템 환경 변수만 검증합니다.")
    
    print("")
    
    # 검증 실행
    validator = setup_validation_rules()
    all_passed = validator.validate_all()
    
    # 결과 출력
    print(validator.generate_report())
    
    # 권장사항 출력
    print("📋 설정 권장사항:")
    print("-" * 40)
    print("1. 프로덕션 환경에서는 반드시 강력한 JWT_SECRET_KEY 사용")
    print("2. 데이터베이스와 Redis에 인증 설정 적용")
    print("3. HTTPS 환경에서는 SECURE_COOKIES=true 설정")
    print("4. 로그 파일 로테이션 설정으로 디스크 공간 관리")
    print("5. 모니터링을 위한 Sentry 또는 로깅 시스템 연동")
    print("")
    
    # 환경별 추가 검사
    environment = os.getenv('ENVIRONMENT', 'development').lower()
    if environment == 'production':
        print("🔒 프로덕션 환경 추가 검사:")
        print("-" * 40)
        
        issues = []
        
        # 디버그 모드 체크
        if os.getenv('DEBUG', 'false').lower() == 'true':
            issues.append("DEBUG 모드가 활성화되어 있습니다 (보안 위험)")
            
        # 기본 시크릿 키 체크
        jwt_key = os.getenv('JWT_SECRET_KEY', '')
        if 'default' in jwt_key.lower() or len(jwt_key) < 64:
            issues.append("JWT_SECRET_KEY가 충분히 강력하지 않습니다")
            
        # HTTPS 체크
        cors_origins = os.getenv('CORS_ORIGINS', '')
        if cors_origins and 'http://' in cors_origins:
            issues.append("CORS_ORIGINS에 HTTP URL이 포함되어 있습니다 (HTTPS 권장)")
        
        if issues:
            for issue in issues:
                print(f"⚠️  {issue}")
        else:
            print("✅ 프로덕션 환경 설정이 적절합니다")
        print("")
    
    # 종료 코드 반환
    if all_passed:
        print("✅ 모든 필수 환경 변수가 올바르게 설정되었습니다!")
        return 0
    else:
        print("❌ 일부 필수 환경 변수 설정에 문제가 있습니다.")
        print("   위의 보고서를 참고하여 수정해주세요.")
        return 1


if __name__ == "__main__":
    sys.exit(main())