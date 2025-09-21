#!/bin/bash
# =============================================================================
# 실패 테스트 재시도 훅 스크립트 (Failed Tests Retry Hook Script)
# =============================================================================
# 목적: 실패한 테스트 타깃 재실행 (플래그만 출력)
# Purpose: Retry failed test targets (output flags only for guidance)
#
# 주의사항:
# - 이 스크립트는 실제 테스트 재실행을 수행하지 않습니다
# - 테스트 프레임워크별 재시도 플래그와 가이드를 제공합니다
# - 실제 재시도는 CI 파이프라인에서 적절한 설정으로 수행해야 합니다
#
# 작성자: CI/CD 자동화 팀
# 버전: 1.0.0
# 최종 수정: 2025-09-21
# =============================================================================

set -euo pipefail

# 색상 코드 (터미널 출력용)
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly PURPLE='\033[0;35m'
readonly NC='\033[0m' # No Color

# 로깅 함수
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    case "$level" in
        "INFO")
            echo -e "${GREEN}[INFO]${NC} ${timestamp} - $message" >&2
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} ${timestamp} - $message" >&2
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} ${timestamp} - $message" >&2
            ;;
        "GUIDE")
            echo -e "${CYAN}[가이드]${NC} ${timestamp} - $message" >&2
            ;;
        "FLAG")
            echo -e "${PURPLE}[플래그]${NC} ${timestamp} - $message" >&2
            ;;
        *)
            echo -e "${BLUE}[${level}]${NC} ${timestamp} - $message" >&2
            ;;
    esac
}

# 테스트 프레임워크 감지 함수
detect_test_framework() {
    local error_data="$1"
    local framework=""

    # 에러 데이터에서 테스트 프레임워크 추론
    if echo "$error_data" | grep -qi "pytest\|python.*test"; then
        framework="pytest"
    elif echo "$error_data" | grep -qi "jest\|npm.*test\|yarn.*test"; then
        framework="jest"
    elif echo "$error_data" | grep -qi "junit\|maven.*test\|gradle.*test"; then
        framework="junit"
    elif echo "$error_data" | grep -qi "rspec\|ruby.*test"; then
        framework="rspec"
    elif echo "$error_data" | grep -qi "go.*test"; then
        framework="go_test"
    elif echo "$error_data" | grep -qi "cargo.*test\|rust.*test"; then
        framework="cargo_test"
    else
        framework="unknown"
    fi

    echo "$framework"
}

# 실패한 테스트 추출 함수
extract_failed_tests() {
    local error_data="$1"
    local framework="$2"

    log_message "INFO" "실패한 테스트 추출 중... (프레임워크: $framework)"

    # JSON 형태의 에러 데이터에서 테스트 이름 추출 시도
    if command -v jq &> /dev/null && echo "$error_data" | jq empty 2>/dev/null; then
        # JSON 데이터에서 테스트 이름 추출
        local test_names
        test_names=$(echo "$error_data" | jq -r '.test_name // .name // .failed_test // empty' 2>/dev/null || echo "")

        if [[ -n "$test_names" ]]; then
            echo "$test_names"
            return 0
        fi
    fi

    # 텍스트 기반 추출 (패턴 매칭)
    case "$framework" in
        "pytest")
            echo "$error_data" | grep -o "FAILED.*::" | sed 's/FAILED //' | head -10
            ;;
        "jest")
            echo "$error_data" | grep -o "● .*" | sed 's/● //' | head -10
            ;;
        "junit")
            echo "$error_data" | grep -o "Test.*failed\|.*Test.*FAILED" | head -10
            ;;
        "go_test")
            echo "$error_data" | grep -o "--- FAIL: Test.*" | sed 's/--- FAIL: //' | head -10
            ;;
        *)
            echo "알 수 없는 테스트 (프레임워크 감지 실패)"
            ;;
    esac
}

# 메인 실행 함수
main() {
    local error_data=""
    local failed_tests=""
    local framework=""

    # stdin에서 에러 데이터 읽기
    if [[ -t 0 ]]; then
        # 터미널에서 직접 실행된 경우
        log_message "INFO" "실패 테스트 재시도 훅 스크립트 단독 실행"
        error_data='{"type":"test_timeout","message":"Test execution timeout","test_name":"test_example"}'
    else
        # 파이프를 통해 에러 데이터가 전달된 경우
        error_data=$(cat)
        log_message "INFO" "실패 테스트 재시도 훅 스크립트 실행 - 에러 데이터 수신됨"
    fi

    log_message "WARN" "🚨 안전 모드: 실제 테스트 재실행은 수행되지 않습니다"

    echo "🔄 실패 테스트 재시도 훅 실행 결과"
    echo "===================================="
    echo

    # 테스트 프레임워크 감지
    framework=$(detect_test_framework "$error_data")
    log_message "INFO" "감지된 테스트 프레임워크: $framework"

    # 실패한 테스트 추출
    failed_tests=$(extract_failed_tests "$error_data" "$framework")

    if [[ -n "$failed_tests" ]]; then
        echo "📋 감지된 실패 테스트:"
        echo "$failed_tests" | while read -r test_name; do
            [[ -n "$test_name" ]] && echo "  ❌ $test_name"
        done
        echo
    else
        echo "📋 구체적인 실패 테스트를 감지하지 못했습니다"
        echo
    fi

    # 프레임워크별 재시도 플래그 및 가이드 제공
    log_message "GUIDE" "테스트 프레임워크별 재시도 가이드:"
    echo

    case "$framework" in
        "pytest")
            log_message "FLAG" "pytest 재시도 플래그:"
            echo "  🔧 마지막 실패 테스트만: pytest --lf"
            echo "  🔧 실패 후 첫 번째 실패까지: pytest -x"
            echo "  🔧 특정 테스트 재실행: pytest path/to/test.py::test_function"
            echo "  🔧 재시도 플러그인: pytest --reruns 3 --reruns-delay 2"
            ;;
        "jest")
            log_message "FLAG" "Jest 재시도 플래그:"
            echo "  🔧 마지막 실패 테스트만: jest --onlyFailures"
            echo "  🔧 변경된 파일 테스트: jest --changedSince=main"
            echo "  🔧 특정 테스트 재실행: jest --testNamePattern='test_name'"
            echo "  🔧 watch 모드: jest --watch"
            ;;
        "junit")
            log_message "FLAG" "JUnit (Maven/Gradle) 재시도 플래그:"
            echo "  🔧 Maven 재시도: mvn test -Dsurefire.rerunFailingTestsCount=3"
            echo "  🔧 Gradle 재시도: ./gradlew test --rerun-tasks"
            echo "  🔧 특정 테스트: mvn test -Dtest=TestClassName"
            echo "  🔧 Surefire 플러그인: surefire-rerunFailingTestsCount"
            ;;
        "go_test")
            log_message "FLAG" "Go 테스트 재시도 플래그:"
            echo "  🔧 특정 테스트: go test -run TestName"
            echo "  🔧 패키지 테스트: go test ./..."
            echo "  🔧 반복 실행: go test -count=3"
            echo "  🔧 자세한 출력: go test -v"
            ;;
        "cargo_test")
            log_message "FLAG" "Rust Cargo 테스트 재시도 플래그:"
            echo "  🔧 특정 테스트: cargo test test_name"
            echo "  🔧 모든 테스트: cargo test"
            echo "  🔧 릴리스 모드: cargo test --release"
            echo "  🔧 자세한 출력: cargo test -- --nocapture"
            ;;
        *)
            log_message "FLAG" "일반적인 테스트 재시도 가이드:"
            echo "  🔧 CI/CD 파이프라인에서 재시도 설정"
            echo "  🔧 테스트 격리 및 독립성 확인"
            echo "  🔧 플래키 테스트 마킹 및 별도 실행"
            echo "  🔧 타임아웃 설정 증가"
            ;;
    esac

    echo
    log_message "GUIDE" "CI/CD 플랫폼별 재시도 설정:"
    echo
    echo "📖 GitHub Actions:"
    echo "   uses: nick-fields/retry@v2"
    echo "   with:"
    echo "     timeout_minutes: 10"
    echo "     max_attempts: 3"
    echo "     command: npm test"
    echo
    echo "📖 GitLab CI:"
    echo "   test:"
    echo "     script: npm test"
    echo "     retry: 2"
    echo
    echo "📖 Jenkins:"
    echo "   retry(3) {"
    echo "     sh 'npm test'"
    echo "   }"
    echo

    # 플래키 테스트 감지 및 권장사항
    if echo "$error_data" | grep -qi "timeout\|flaky\|intermittent"; then
        log_message "WARN" "🎯 플래키 테스트 의심 케이스 감지!"
        echo
        echo "📖 플래키 테스트 대응 방안:"
        echo "  1. 🏷️  플래키 테스트 태그 추가"
        echo "  2. 🔄 자동 재시도 설정"
        echo "  3. 📊 실패 패턴 분석"
        echo "  4. 🚫 임시 격리 (quarantine)"
        echo "  5. 🔧 테스트 안정화 작업"
    fi

    echo
    log_message "INFO" "테스트 재시도 훅 실행 완료 (드라이런 모드)"
    log_message "WARN" "실제 재시도를 원한다면 위의 플래그를 CI 설정에 적용하세요"

    # 성공 상태로 종료
    echo "✅ 실패 테스트 재시도 훅 성공적으로 완료"
    exit 0
}

# 스크립트 실행
main "$@"