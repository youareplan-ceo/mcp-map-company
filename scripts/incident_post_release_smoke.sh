#!/bin/bash

# ===================================================================
# 🚨 인시던트 센터 v1.0.0 사후 검증 스모크 테스트
#
# 목적: 릴리스 후 API 엔드포인트 정상 동작 확인
# 사용법: ./scripts/incident_post_release_smoke.sh [--json] [--verbose] [--timeout=30]
#
# 검증 항목:
# - /api/v1/incidents/health 200 응답 확인
# - /api/v1/incidents/summary 필수 키 존재 확인
# - /api/v1/incidents/list CSV 내보내기 옵션 스모크
# - 실패 시 한국어 에러 메시지 출력
# ===================================================================

set -euo pipefail

# === 기본 설정 ===
API_BASE_URL="http://localhost:8000/api/v1/incidents"
DEFAULT_TIMEOUT=30
JSON_OUTPUT=false
VERBOSE=false
TIMEOUT=$DEFAULT_TIMEOUT

# 색깔 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# === 함수 정의 ===

show_help() {
    echo -e "${CYAN}🚨 인시던트 센터 v1.0.0 사후 검증 스모크 테스트${NC}"
    echo ""
    echo "사용법: $0 [옵션]"
    echo ""
    echo "옵션:"
    echo "  --json          JSON 형태로 결과 출력"
    echo "  --verbose       상세한 디버그 정보 출력"
    echo "  --timeout=N     HTTP 요청 타임아웃 (기본: 30초)"
    echo "  --help          이 도움말 표시"
    echo ""
    echo "예시:"
    echo "  $0                    # 기본 실행"
    echo "  $0 --json            # JSON 출력"
    echo "  $0 --verbose         # 상세 로그"
    echo "  $0 --timeout=60      # 60초 타임아웃"
}

log_info() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${CYAN}ℹ️  $1${NC}"
    fi
}

log_success() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${GREEN}✅ $1${NC}"
    fi
}

log_warning() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${YELLOW}⚠️  $1${NC}"
    fi
}

log_error() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${RED}❌ $1${NC}" >&2
    fi
}

log_verbose() {
    if [[ "$VERBOSE" == "true" && "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${PURPLE}🔍 $1${NC}"
    fi
}

# === 인수 파싱 ===
while [[ $# -gt 0 ]]; do
    case $1 in
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --timeout=*)
            TIMEOUT="${1#*=}"
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}❌ 알 수 없는 옵션: $1${NC}" >&2
            echo "도움말: $0 --help"
            exit 1
            ;;
    esac
done

# === JSON 결과 구조 초기화 ===
if [[ "$JSON_OUTPUT" == "true" ]]; then
    JSON_RESULT='{"timestamp":"'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'","smoke_test":"incident_center_v1.0.0","status":"running","tests":[]}'
fi

add_test_result() {
    local test_name="$1"
    local status="$2"
    local message="$3"
    local details="${4:-null}"

    if [[ "$JSON_OUTPUT" == "true" ]]; then
        local test_json="{\"name\":\"$test_name\",\"status\":\"$status\",\"message\":\"$message\",\"details\":$details}"
        JSON_RESULT=$(echo "$JSON_RESULT" | jq ".tests += [$test_json]")
    fi
}

finalize_json() {
    local overall_status="$1"
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        JSON_RESULT=$(echo "$JSON_RESULT" | jq ".status = \"$overall_status\"")
        echo "$JSON_RESULT" | jq .
    fi
}

# === 테스트 함수들 ===

test_health_endpoint() {
    log_info "🏥 헬스체크 엔드포인트 테스트 중..."
    log_verbose "URL: $API_BASE_URL/health"

    local response
    local http_code

    response=$(curl -s -w "HTTPSTATUS:%{http_code}" --max-time "$TIMEOUT" "$API_BASE_URL/health" 2>/dev/null || echo "HTTPSTATUS:000")
    http_code=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    local body=$(echo "$response" | sed -E 's/HTTPSTATUS:[0-9]*$//')

    log_verbose "HTTP 상태 코드: $http_code"
    log_verbose "응답 본문: $body"

    if [[ "$http_code" == "200" ]]; then
        log_success "헬스체크 엔드포인트 정상 (HTTP 200)"
        add_test_result "health_endpoint" "pass" "헬스체크 엔드포인트 정상 응답" "{\"http_code\":$http_code,\"response_body\":\"$body\"}"
        return 0
    else
        log_error "헬스체크 엔드포인트 실패 (HTTP $http_code)"
        add_test_result "health_endpoint" "fail" "헬스체크 엔드포인트 실패" "{\"http_code\":$http_code,\"response_body\":\"$body\"}"
        return 1
    fi
}

test_summary_endpoint() {
    log_info "📊 요약 통계 엔드포인트 테스트 중..."
    log_verbose "URL: $API_BASE_URL/summary"

    local response
    local http_code

    response=$(curl -s -w "HTTPSTATUS:%{http_code}" --max-time "$TIMEOUT" \
        -H "X-User-Role: VIEWER" \
        "$API_BASE_URL/summary" 2>/dev/null || echo "HTTPSTATUS:000")
    http_code=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    local body=$(echo "$response" | sed -E 's/HTTPSTATUS:[0-9]*$//')

    log_verbose "HTTP 상태 코드: $http_code"
    log_verbose "응답 본문: $body"

    if [[ "$http_code" != "200" ]]; then
        log_error "요약 엔드포인트 접근 실패 (HTTP $http_code)"
        add_test_result "summary_endpoint" "fail" "요약 엔드포인트 접근 실패" "{\"http_code\":$http_code,\"response_body\":\"$body\"}"
        return 1
    fi

    # 필수 키 확인
    local required_keys=("total_incidents" "sla_violation_rate" "by_severity" "by_status")
    local missing_keys=()

    for key in "${required_keys[@]}"; do
        if ! echo "$body" | jq -e ".$key" >/dev/null 2>&1; then
            missing_keys+=("$key")
        fi
    done

    if [[ ${#missing_keys[@]} -eq 0 ]]; then
        log_success "요약 엔드포인트 필수 키 모두 존재"
        add_test_result "summary_endpoint" "pass" "요약 엔드포인트 필수 키 검증 성공" "{\"required_keys\":$(printf '%s\n' "${required_keys[@]}" | jq -R . | jq -s .)}"
        return 0
    else
        log_error "요약 엔드포인트 누락 키: ${missing_keys[*]}"
        add_test_result "summary_endpoint" "fail" "요약 엔드포인트 누락 키 발견" "{\"missing_keys\":$(printf '%s\n' "${missing_keys[@]}" | jq -R . | jq -s .)}"
        return 1
    fi
}

test_csv_export() {
    log_info "📥 CSV 내보내기 스모크 테스트 중..."
    log_verbose "URL: $API_BASE_URL/list?export_format=csv"

    local response
    local http_code

    response=$(curl -s -w "HTTPSTATUS:%{http_code}" --max-time "$TIMEOUT" \
        -H "X-User-Role: VIEWER" \
        "$API_BASE_URL/list?export_format=csv" 2>/dev/null || echo "HTTPSTATUS:000")
    http_code=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    local body=$(echo "$response" | sed -E 's/HTTPSTATUS:[0-9]*$//')

    log_verbose "HTTP 상태 코드: $http_code"
    log_verbose "응답 본문 첫 100자: ${body:0:100}..."

    if [[ "$http_code" == "200" ]]; then
        # CSV 헤더 확인 (한국어)
        if echo "$body" | head -1 | grep -q "인시던트ID\|생성일시\|해결시간"; then
            log_success "CSV 내보내기 기능 정상 (한국어 헤더 확인)"
            add_test_result "csv_export" "pass" "CSV 내보내기 기능 정상" "{\"http_code\":$http_code,\"header_check\":true}"
            return 0
        else
            log_warning "CSV 응답은 받았으나 한국어 헤더 형식 불일치"
            add_test_result "csv_export" "warn" "CSV 헤더 형식 불일치" "{\"http_code\":$http_code,\"header_check\":false}"
            return 0
        fi
    else
        log_error "CSV 내보내기 실패 (HTTP $http_code)"
        add_test_result "csv_export" "fail" "CSV 내보내기 실패" "{\"http_code\":$http_code,\"response_body\":\"$body\"}"
        return 1
    fi
}

# === 메인 실행 ===

main() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${PURPLE}🚨 인시던트 센터 v1.0.0 사후 검증 스모크 테스트 시작${NC}"
        echo -e "${CYAN}📅 시작 시간: $(date)${NC}"
        echo -e "${CYAN}🌐 API 베이스 URL: $API_BASE_URL${NC}"
        echo -e "${CYAN}⏱️  타임아웃: ${TIMEOUT}초${NC}"
        echo ""
    fi

    local test_results=()
    local overall_success=true

    # 각 테스트 실행
    if test_health_endpoint; then
        test_results+=("✅ 헬스체크")
    else
        test_results+=("❌ 헬스체크")
        overall_success=false
    fi

    if test_summary_endpoint; then
        test_results+=("✅ 요약 통계")
    else
        test_results+=("❌ 요약 통계")
        overall_success=false
    fi

    if test_csv_export; then
        test_results+=("✅ CSV 내보내기")
    else
        test_results+=("❌ CSV 내보내기")
        overall_success=false
    fi

    # 결과 출력
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo ""
        echo -e "${PURPLE}📋 테스트 결과 요약:${NC}"
        for result in "${test_results[@]}"; do
            echo "  $result"
        done
        echo ""

        if [[ "$overall_success" == "true" ]]; then
            echo -e "${GREEN}🎉 모든 스모크 테스트 통과! 인시던트 센터 v1.0.0 정상 동작 확인${NC}"
            echo -e "${CYAN}📅 완료 시간: $(date)${NC}"
        else
            echo -e "${RED}💥 일부 스모크 테스트 실패. 시스템 점검 필요${NC}"
            echo -e "${YELLOW}💡 문제 해결 가이드:${NC}"
            echo "  1. API 서버 실행 상태 확인: make incident-health"
            echo "  2. 포트 8000 사용 여부 확인: lsof -i :8000"
            echo "  3. 로그 확인: tail -f logs/incident_api.log"
            echo "  4. 롤백 고려: make incident-rollback-dry"
        fi
    fi

    # JSON 결과 최종화
    if [[ "$overall_success" == "true" ]]; then
        finalize_json "pass"
        exit 0
    else
        finalize_json "fail"
        exit 1
    fi
}

# curl 및 jq 의존성 확인
if ! command -v curl &> /dev/null; then
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        echo '{"error":"curl 명령어가 설치되어 있지 않습니다. brew install curl 또는 apt install curl로 설치하세요."}'
    else
        log_error "curl 명령어가 설치되어 있지 않습니다. brew install curl 또는 apt install curl로 설치하세요."
    fi
    exit 1
fi

if [[ "$JSON_OUTPUT" == "true" ]] && ! command -v jq &> /dev/null; then
    echo '{"error":"jq 명령어가 설치되어 있지 않습니다. brew install jq 또는 apt install jq로 설치하세요."}'
    exit 1
fi

# 메인 함수 호출
main "$@"