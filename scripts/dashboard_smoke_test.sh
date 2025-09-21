#!/bin/bash

# =============================================================================
# 🖥️ 대시보드 스모크 테스트 스크립트
# =============================================================================
#
# 기능:
# - curl을 이용한 대시보드 및 API 엔드포인트 헬스체크
# - HTTP 응답 코드 및 JSON 구조 검증
# - 에러 발생 시 보안 로그에 자동 기록
# - 다양한 출력 형식 지원 (JSON, 상세, 요약)
#
# 사용법:
#   ./scripts/dashboard_smoke_test.sh [옵션]
#
# 옵션:
#   --json      : JSON 형식으로 결과 출력
#   --verbose   : 상세 로그 출력
#   --help      : 도움말 출력
#   --timeout N : HTTP 요청 타임아웃 설정 (기본값: 10초)
#   --host URL  : 테스트할 호스트 URL 설정 (기본값: http://localhost:8088)
#
# =============================================================================

set -euo pipefail

# ── 🎯 전역 변수 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
SECURITY_LOG="$LOG_DIR/security.log"

# 기본 설정값
DEFAULT_HOST="http://localhost:8088"
DEFAULT_TIMEOUT=10
VERBOSE=false
JSON_OUTPUT=false
HOST="$DEFAULT_HOST"
TIMEOUT="$DEFAULT_TIMEOUT"

# 결과 저장용 변수
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
TEST_RESULTS=()

# ── 🎨 색상 정의 (터미널 출력용)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# ── 📋 도움말 출력 함수
show_help() {
    cat << EOF
🖥️ 대시보드 스모크 테스트 스크립트

사용법:
    $0 [옵션]

옵션:
    --json              JSON 형식으로 결과 출력
    --verbose           상세 로그 출력 활성화
    --help              이 도움말 출력
    --timeout N         HTTP 요청 타임아웃 설정 (기본값: ${DEFAULT_TIMEOUT}초)
    --host URL          테스트할 호스트 URL (기본값: ${DEFAULT_HOST})

예시:
    # 기본 실행
    $0

    # 상세 로그와 함께 실행
    $0 --verbose

    # JSON 출력으로 실행
    $0 --json

    # 다른 호스트 테스트
    $0 --host http://production.example.com --timeout 30

    # 상세 로그 + JSON 출력
    $0 --verbose --json

테스트 대상:
    - 관리자 대시보드 페이지 (/admin_dashboard.html)
    - 보안 API 엔드포인트 (/api/v1/security/stats)
    - 시스템 메트릭 API (/api/v1/metrics)
    - 헬스체크 엔드포인트 (/health)

출력:
    - 성공 시: 종료 코드 0
    - 실패 시: 종료 코드 1
    - 로그: logs/security.log 에 결과 기록

EOF
}

# ── 📝 로그 기록 함수
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    # 보안 로그 디렉토리 생성
    mkdir -p "$LOG_DIR"

    # 보안 로그 파일에 기록
    echo "$timestamp - $level - [DASHBOARD_SMOKE_TEST] $message" >> "$SECURITY_LOG"

    # Verbose 모드일 때만 콘솔 출력
    if [[ "$VERBOSE" == "true" ]]; then
        case "$level" in
            "INFO")  echo -e "${BLUE}[INFO]${NC} $message" ;;
            "WARN")  echo -e "${YELLOW}[WARN]${NC} $message" ;;
            "ERROR") echo -e "${RED}[ERROR]${NC} $message" ;;
            "SUCCESS") echo -e "${GREEN}[SUCCESS]${NC} $message" ;;
            *) echo -e "${WHITE}[$level]${NC} $message" ;;
        esac
    fi
}

# ── 🔍 HTTP 엔드포인트 테스트 함수
test_endpoint() {
    local name="$1"
    local url="$2"
    local expected_status="$3"
    local check_json="${4:-false}"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    log_message "INFO" "테스트 시작: $name ($url)"

    # curl을 이용한 HTTP 요청
    local response
    local http_status
    local curl_exit_code

    response=$(curl -s -w "HTTPSTATUS:%{http_code}" \
                   --max-time "$TIMEOUT" \
                   --connect-timeout 5 \
                   --user-agent "MCP-Dashboard-SmokeTest/1.0" \
                   "$url" 2>/dev/null) || curl_exit_code=$?

    # curl 실행 실패 처리
    if [[ -n "${curl_exit_code:-}" ]]; then
        log_message "ERROR" "$name 테스트 실패: curl 오류 (exit code: $curl_exit_code)"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        TEST_RESULTS+=("{\"name\":\"$name\",\"url\":\"$url\",\"status\":\"FAILED\",\"error\":\"curl_error\",\"exit_code\":$curl_exit_code}")
        return 1
    fi

    # HTTP 상태 코드 추출
    http_status=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    local body=$(echo "$response" | sed 's/HTTPSTATUS:[0-9]*$//')

    # HTTP 상태 코드 검증
    if [[ "$http_status" == "$expected_status" ]]; then
        log_message "SUCCESS" "$name HTTP 상태 코드 검증 성공: $http_status"

        # JSON 응답 검증 (선택적)
        if [[ "$check_json" == "true" ]]; then
            if echo "$body" | jq . >/dev/null 2>&1; then
                log_message "SUCCESS" "$name JSON 구조 검증 성공"
                local json_valid=true
            else
                log_message "WARN" "$name JSON 구조 검증 실패 - 유효하지 않은 JSON"
                local json_valid=false
            fi
        else
            local json_valid="not_checked"
        fi

        PASSED_TESTS=$((PASSED_TESTS + 1))
        TEST_RESULTS+=("{\"name\":\"$name\",\"url\":\"$url\",\"status\":\"PASSED\",\"http_status\":$http_status,\"json_valid\":\"$json_valid\"}")
        return 0

    else
        log_message "ERROR" "$name HTTP 상태 코드 불일치: 예상 $expected_status, 실제 $http_status"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        TEST_RESULTS+=("{\"name\":\"$name\",\"url\":\"$url\",\"status\":\"FAILED\",\"expected_status\":$expected_status,\"actual_status\":$http_status}")
        return 1
    fi
}

# ── ⚡ 고급 JSON API 테스트 함수
test_json_api() {
    local name="$1"
    local url="$2"
    local required_fields="$3"  # 쉼표로 구분된 필수 필드 목록

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    log_message "INFO" "JSON API 테스트 시작: $name ($url)"

    local response
    local http_status
    local curl_exit_code

    response=$(curl -s -w "HTTPSTATUS:%{http_code}" \
                   --max-time "$TIMEOUT" \
                   --connect-timeout 5 \
                   -H "Accept: application/json" \
                   -H "Content-Type: application/json" \
                   "$url" 2>/dev/null) || curl_exit_code=$?

    # curl 실행 실패 처리
    if [[ -n "${curl_exit_code:-}" ]]; then
        log_message "ERROR" "$name JSON API 테스트 실패: curl 오류"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        TEST_RESULTS+=("{\"name\":\"$name\",\"url\":\"$url\",\"status\":\"FAILED\",\"error\":\"curl_error\"}")
        return 1
    fi

    # HTTP 상태 코드 추출
    http_status=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    local body=$(echo "$response" | sed 's/HTTPSTATUS:[0-9]*$//')

    # 200번대 응답이 아닌 경우 - 서버가 실행 중이 아닐 수 있음
    if [[ ! "$http_status" =~ ^2[0-9][0-9]$ ]]; then
        log_message "WARN" "$name API 사용 불가 (HTTP $http_status) - 서버가 실행 중이 아닐 수 있음"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        TEST_RESULTS+=("{\"name\":\"$name\",\"url\":\"$url\",\"status\":\"FAILED\",\"http_status\":$http_status,\"note\":\"서버 미실행 가능성\"}")
        return 1
    fi

    # JSON 구조 검증
    if ! echo "$body" | jq . >/dev/null 2>&1; then
        log_message "ERROR" "$name JSON 구조 검증 실패"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        TEST_RESULTS+=("{\"name\":\"$name\",\"url\":\"$url\",\"status\":\"FAILED\",\"error\":\"invalid_json\"}")
        return 1
    fi

    # 필수 필드 검증
    local missing_fields=()
    IFS=',' read -ra FIELDS <<< "$required_fields"
    for field in "${FIELDS[@]}"; do
        field=$(echo "$field" | xargs)  # 공백 제거
        if ! echo "$body" | jq -e ".$field" >/dev/null 2>&1; then
            missing_fields+=("$field")
        fi
    done

    if [[ ${#missing_fields[@]} -gt 0 ]]; then
        local missing_str=$(IFS=','; echo "${missing_fields[*]}")
        log_message "ERROR" "$name 필수 필드 누락: $missing_str"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        TEST_RESULTS+=("{\"name\":\"$name\",\"url\":\"$url\",\"status\":\"FAILED\",\"missing_fields\":\"$missing_str\"}")
        return 1
    fi

    log_message "SUCCESS" "$name JSON API 테스트 성공 (모든 필수 필드 확인됨)"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    TEST_RESULTS+=("{\"name\":\"$name\",\"url\":\"$url\",\"status\":\"PASSED\",\"http_status\":$http_status,\"fields_verified\":\"$required_fields\"}")
    return 0
}

# ── 🏃‍♂️ 모든 테스트 실행 함수
run_all_tests() {
    log_message "INFO" "대시보드 스모크 테스트 시작 (호스트: $HOST, 타임아웃: ${TIMEOUT}초)"

    echo -e "${PURPLE}🖥️ 대시보드 스모크 테스트 시작${NC}"
    echo -e "${CYAN}호스트: $HOST${NC}"
    echo -e "${CYAN}타임아웃: ${TIMEOUT}초${NC}"
    echo ""

    # 1. 관리자 대시보드 페이지 테스트
    echo -e "${WHITE}📄 관리자 대시보드 페이지 테스트${NC}"
    test_endpoint "관리자 대시보드" "$HOST/admin_dashboard.html" "200"

    # 2. 헬스체크 엔드포인트 테스트
    echo -e "${WHITE}🔍 헬스체크 엔드포인트 테스트${NC}"
    test_endpoint "헬스체크" "$HOST/health" "200" "true"

    # 3. 보안 API 엔드포인트 테스트 (선택적 - 서버가 실행 중일 때만)
    echo -e "${WHITE}🔒 보안 API 엔드포인트 테스트${NC}"
    test_json_api "보안 통계 API" "$HOST/api/v1/security/stats" "blocked_count,whitelist_count"

    # 4. 시스템 메트릭 API 테스트 (선택적)
    echo -e "${WHITE}📊 시스템 메트릭 API 테스트${NC}"
    test_json_api "시스템 메트릭 API" "$HOST/api/v1/metrics" "cpu_usage,memory_usage"

    # 5. 운영 알림 API 테스트 (선택적)
    echo -e "${WHITE}🔔 운영 알림 API 테스트${NC}"
    test_json_api "운영 알림 API" "$HOST/api/v1/notifications" "notifications,total_count"

    log_message "INFO" "대시보드 스모크 테스트 완료 - 총 $TOTAL_TESTS개 테스트, 성공 $PASSED_TESTS개, 실패 $FAILED_TESTS개"
}

# ── 📊 결과 출력 함수
output_results() {
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        # JSON 형식 출력
        local results_json="["
        for (( i=0; i<${#TEST_RESULTS[@]}; i++ )); do
            results_json+="${TEST_RESULTS[i]}"
            if [[ $i -lt $((${#TEST_RESULTS[@]} - 1)) ]]; then
                results_json+=","
            fi
        done
        results_json+="]"

        cat << EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "host": "$HOST",
    "timeout": $TIMEOUT,
    "summary": {
        "total_tests": $TOTAL_TESTS,
        "passed": $PASSED_TESTS,
        "failed": $FAILED_TESTS,
        "success_rate": $(echo "scale=2; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc)
    },
    "test_results": $results_json
}
EOF
    else
        # 일반 텍스트 형식 출력
        echo ""
        echo -e "${WHITE}📋 테스트 결과 요약${NC}"
        echo -e "${CYAN}════════════════════════════════════════${NC}"
        echo -e "총 테스트: ${WHITE}$TOTAL_TESTS${NC}개"
        echo -e "성공: ${GREEN}$PASSED_TESTS${NC}개"
        echo -e "실패: ${RED}$FAILED_TESTS${NC}개"

        local success_rate
        if [[ $TOTAL_TESTS -gt 0 ]]; then
            success_rate=$(echo "scale=1; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc)
            echo -e "성공률: ${WHITE}$success_rate%${NC}"
        fi

        echo ""

        if [[ $FAILED_TESTS -gt 0 ]]; then
            echo -e "${RED}❌ 실패한 테스트가 있습니다.${NC}"
            echo -e "${YELLOW}💡 자세한 내용은 logs/security.log를 확인하세요.${NC}"
        else
            echo -e "${GREEN}✅ 모든 테스트가 성공적으로 완료되었습니다!${NC}"
        fi
    fi
}

# ── 🚀 메인 실행 함수
main() {
    # 명령행 인수 파싱
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help)
                show_help
                exit 0
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --json)
                JSON_OUTPUT=true
                shift
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            --host)
                HOST="$2"
                shift 2
                ;;
            *)
                echo -e "${RED}❌ 알 수 없는 옵션: $1${NC}"
                echo "도움말을 보려면 --help 옵션을 사용하세요."
                exit 1
                ;;
        esac
    done

    # bc 명령어 설치 확인 (성공률 계산용)
    if ! command -v bc &> /dev/null; then
        log_message "WARN" "bc 명령어를 찾을 수 없습니다. 성공률 계산을 건너뜁니다."
    fi

    # jq 명령어 설치 확인 (JSON 검증용)
    if ! command -v jq &> /dev/null; then
        log_message "WARN" "jq 명령어를 찾을 수 없습니다. JSON 검증을 건너뜁니다."
    fi

    # 타임아웃 값 검증
    if ! [[ "$TIMEOUT" =~ ^[0-9]+$ ]] || [[ $TIMEOUT -lt 1 ]] || [[ $TIMEOUT -gt 300 ]]; then
        echo -e "${RED}❌ 타임아웃 값이 유효하지 않습니다: $TIMEOUT${NC}"
        echo "1~300초 사이의 값을 입력하세요."
        exit 1
    fi

    # 모든 테스트 실행
    run_all_tests

    # 결과 출력
    output_results

    # 종료 코드 설정
    if [[ $FAILED_TESTS -gt 0 ]]; then
        exit 1
    else
        exit 0
    fi
}

# ── 🎬 스크립트 진입점
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi