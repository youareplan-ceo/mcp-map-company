#!/bin/bash

# ===================================================================
# 🌐 인시던트 센터 대시보드 스모크 테스트 (무브라우저)
#
# 목적: 웹 대시보드 파일 접근성 및 핵심 DOM 구조 검증
# 사용법: ./scripts/dashboard_smoke_incidents.sh [--json] [--verbose]
#
# 검증 항목:
# - web/admin_dashboard.html 파일 존재 및 크기 확인
# - "인시던트" 패널 핵심 DOM 토큰 정규식 검사
# - 5개 통계 카드 ID 확인 (totalIncidents, highSeverityIncidents 등)
# - 2개 차트 ID 확인 (incidentTrendChart, incidentSeverityChart)
# - 필수 섹션 앵커 키워드 검사
# ===================================================================

set -euo pipefail

# === 기본 설정 ===
DASHBOARD_FILE="web/admin_dashboard.html"
JSON_OUTPUT=false
VERBOSE=false

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
    echo -e "${CYAN}🌐 인시던트 센터 대시보드 스모크 테스트${NC}"
    echo ""
    echo "사용법: $0 [옵션]"
    echo ""
    echo "옵션:"
    echo "  --json          JSON 형태로 결과 출력"
    echo "  --verbose       상세한 디버그 정보 출력"
    echo "  --help          이 도움말 표시"
    echo ""
    echo "예시:"
    echo "  $0                    # 기본 실행"
    echo "  $0 --json            # JSON 출력"
    echo "  $0 --verbose         # 상세 로그"
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
    JSON_RESULT='{"timestamp":"'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'","smoke_test":"dashboard_incidents","status":"running","tests":[]}'
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

test_file_accessibility() {
    log_info "📄 대시보드 파일 접근성 테스트 중..."
    log_verbose "파일 경로: $DASHBOARD_FILE"

    if [[ ! -f "$DASHBOARD_FILE" ]]; then
        log_error "대시보드 파일이 존재하지 않음: $DASHBOARD_FILE"
        add_test_result "file_accessibility" "fail" "대시보드 파일이 존재하지 않음" "{\"file_path\":\"$DASHBOARD_FILE\"}"
        return 1
    fi

    local file_size=$(stat -f%z "$DASHBOARD_FILE" 2>/dev/null || stat -c%s "$DASHBOARD_FILE" 2>/dev/null || echo "0")
    log_verbose "파일 크기: $file_size bytes"

    if [[ "$file_size" -lt 10000 ]]; then
        log_warning "대시보드 파일 크기가 너무 작음 (${file_size} bytes < 10KB)"
        add_test_result "file_accessibility" "warn" "파일 크기가 예상보다 작음" "{\"file_size\":$file_size,\"min_expected\":10000}"
        return 0
    fi

    log_success "대시보드 파일 접근성 정상 (${file_size} bytes)"
    add_test_result "file_accessibility" "pass" "대시보드 파일 접근성 정상" "{\"file_size\":$file_size}"
    return 0
}

test_incident_cards() {
    log_info "📊 인시던트 통계 카드 DOM 구조 테스트 중..."

    local required_card_ids=(
        "totalIncidents"
        "highSeverityIncidents"
        "avgResolutionTime"
        "slaViolationRate"
        "activeIncidents"
    )

    local found_cards=()
    local missing_cards=()

    for card_id in "${required_card_ids[@]}"; do
        if grep -q "id=\"$card_id\"" "$DASHBOARD_FILE"; then
            found_cards+=("$card_id")
            log_verbose "✓ 카드 ID 발견: $card_id"
        else
            missing_cards+=("$card_id")
            log_verbose "✗ 카드 ID 누락: $card_id"
        fi
    done

    if [[ ${#missing_cards[@]} -eq 0 ]]; then
        log_success "모든 인시던트 통계 카드 ID 확인 (${#found_cards[@]}개)"
        add_test_result "incident_cards" "pass" "모든 인시던트 통계 카드 확인" "{\"found_cards\":$(printf '%s\n' "${found_cards[@]}" | jq -R . | jq -s .),\"count\":${#found_cards[@]}}"
        return 0
    else
        log_error "누락된 인시던트 카드 ID: ${missing_cards[*]}"
        add_test_result "incident_cards" "fail" "인시던트 카드 ID 누락" "{\"missing_cards\":$(printf '%s\n' "${missing_cards[@]}" | jq -R . | jq -s .),\"found_cards\":$(printf '%s\n' "${found_cards[@]}" | jq -R . | jq -s .)}"
        return 1
    fi
}

test_incident_charts() {
    log_info "📈 인시던트 차트 DOM 구조 테스트 중..."

    local required_chart_ids=(
        "incidentTrendChart"
        "incidentSeverityChart"
    )

    local found_charts=()
    local missing_charts=()

    for chart_id in "${required_chart_ids[@]}"; do
        if grep -q "id=\"$chart_id\"" "$DASHBOARD_FILE"; then
            found_charts+=("$chart_id")
            log_verbose "✓ 차트 ID 발견: $chart_id"
        else
            missing_charts+=("$chart_id")
            log_verbose "✗ 차트 ID 누락: $chart_id"
        fi
    done

    if [[ ${#missing_charts[@]} -eq 0 ]]; then
        log_success "모든 인시던트 차트 ID 확인 (${#found_charts[@]}개)"
        add_test_result "incident_charts" "pass" "모든 인시던트 차트 확인" "{\"found_charts\":$(printf '%s\n' "${found_charts[@]}" | jq -R . | jq -s .),\"count\":${#found_charts[@]}}"
        return 0
    else
        log_error "누락된 인시던트 차트 ID: ${missing_charts[*]}"
        add_test_result "incident_charts" "fail" "인시던트 차트 ID 누락" "{\"missing_charts\":$(printf '%s\n' "${missing_charts[@]}" | jq -R . | jq -s .),\"found_charts\":$(printf '%s\n' "${found_charts[@]}" | jq -R . | jq -s .)}"
        return 1
    fi
}

test_korean_localization() {
    log_info "🇰🇷 한국어 로컬라이제이션 테스트 중..."

    local korean_keywords=(
        "인시던트"
        "통계"
        "심각도"
        "해결시간"
        "위반율"
        "다크모드"
    )

    local found_keywords=()
    local missing_keywords=()

    for keyword in "${korean_keywords[@]}"; do
        if grep -q "$keyword" "$DASHBOARD_FILE"; then
            found_keywords+=("$keyword")
            log_verbose "✓ 한국어 키워드 발견: $keyword"
        else
            missing_keywords+=("$keyword")
            log_verbose "✗ 한국어 키워드 누락: $keyword"
        fi
    done

    local localization_score=$((${#found_keywords[@]} * 100 / ${#korean_keywords[@]}))

    if [[ $localization_score -ge 80 ]]; then
        log_success "한국어 로컬라이제이션 우수 (${localization_score}% 커버리지)"
        add_test_result "korean_localization" "pass" "한국어 로컬라이제이션 검증 성공" "{\"found_keywords\":$(printf '%s\n' "${found_keywords[@]}" | jq -R . | jq -s .),\"coverage_percent\":$localization_score}"
        return 0
    elif [[ $localization_score -ge 60 ]]; then
        log_warning "한국어 로컬라이제이션 부족 (${localization_score}% 커버리지)"
        add_test_result "korean_localization" "warn" "한국어 로컬라이제이션 부족" "{\"found_keywords\":$(printf '%s\n' "${found_keywords[@]}" | jq -R . | jq -s .),\"missing_keywords\":$(printf '%s\n' "${missing_keywords[@]}" | jq -R . | jq -s .),\"coverage_percent\":$localization_score}"
        return 0
    else
        log_error "한국어 로컬라이제이션 심각한 부족 (${localization_score}% 커버리지)"
        add_test_result "korean_localization" "fail" "한국어 로컬라이제이션 심각한 부족" "{\"found_keywords\":$(printf '%s\n' "${found_keywords[@]}" | jq -R . | jq -s .),\"missing_keywords\":$(printf '%s\n' "${missing_keywords[@]}" | jq -R . | jq -s .),\"coverage_percent\":$localization_score}"
        return 1
    fi
}

test_dark_mode_support() {
    log_info "🌙 다크모드 지원 테스트 중..."

    # 다크모드 관련 CSS 클래스 및 미디어 쿼리 확인
    local dark_mode_indicators=(
        "prefers-color-scheme.*dark"
        "다크모드"
        "dark.*mode"
        "@media.*dark"
    )

    local found_indicators=()

    for indicator in "${dark_mode_indicators[@]}"; do
        if grep -E -q "$indicator" "$DASHBOARD_FILE"; then
            found_indicators+=("$indicator")
            log_verbose "✓ 다크모드 지시자 발견: $indicator"
        fi
    done

    if [[ ${#found_indicators[@]} -gt 0 ]]; then
        log_success "다크모드 지원 확인됨 (${#found_indicators[@]}개 지시자)"
        add_test_result "dark_mode_support" "pass" "다크모드 지원 확인" "{\"found_indicators\":$(printf '%s\n' "${found_indicators[@]}" | jq -R . | jq -s .),\"count\":${#found_indicators[@]}}"
        return 0
    else
        log_warning "다크모드 지원 지시자를 찾을 수 없음"
        add_test_result "dark_mode_support" "warn" "다크모드 지원 지시자 없음" "{\"found_indicators\":[]}"
        return 0
    fi
}

test_responsive_design() {
    log_info "📱 반응형 디자인 테스트 중..."

    # 반응형 디자인 관련 CSS 확인
    local responsive_indicators=(
        "@media.*max-width"
        "@media.*min-width"
        "viewport"
        "responsive"
        "grid"
        "flex"
    )

    local found_indicators=()

    for indicator in "${responsive_indicators[@]}"; do
        if grep -E -i -q "$indicator" "$DASHBOARD_FILE"; then
            found_indicators+=("$indicator")
            log_verbose "✓ 반응형 지시자 발견: $indicator"
        fi
    done

    if [[ ${#found_indicators[@]} -ge 2 ]]; then
        log_success "반응형 디자인 지원 확인됨 (${#found_indicators[@]}개 지시자)"
        add_test_result "responsive_design" "pass" "반응형 디자인 지원 확인" "{\"found_indicators\":$(printf '%s\n' "${found_indicators[@]}" | jq -R . | jq -s .),\"count\":${#found_indicators[@]}}"
        return 0
    else
        log_warning "반응형 디자인 지시자가 부족함 (${#found_indicators[@]}개)"
        add_test_result "responsive_design" "warn" "반응형 디자인 지시자 부족" "{\"found_indicators\":$(printf '%s\n' "${found_indicators[@]}" | jq -R . | jq -s .),\"count\":${#found_indicators[@]}}"
        return 0
    fi
}

# === 메인 실행 ===

main() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${PURPLE}🌐 인시던트 센터 대시보드 스모크 테스트 시작${NC}"
        echo -e "${CYAN}📅 시작 시간: $(date)${NC}"
        echo -e "${CYAN}📄 대시보드 파일: $DASHBOARD_FILE${NC}"
        echo ""
    fi

    local test_results=()
    local overall_success=true

    # 각 테스트 실행
    if test_file_accessibility; then
        test_results+=("✅ 파일 접근성")
    else
        test_results+=("❌ 파일 접근성")
        overall_success=false
    fi

    if test_incident_cards; then
        test_results+=("✅ 인시던트 카드")
    else
        test_results+=("❌ 인시던트 카드")
        overall_success=false
    fi

    if test_incident_charts; then
        test_results+=("✅ 인시던트 차트")
    else
        test_results+=("❌ 인시던트 차트")
        overall_success=false
    fi

    if test_korean_localization; then
        test_results+=("✅ 한국어 지원")
    else
        test_results+=("❌ 한국어 지원")
        overall_success=false
    fi

    if test_dark_mode_support; then
        test_results+=("✅ 다크모드")
    else
        test_results+=("⚠️ 다크모드")
        # 다크모드는 warning일 수 있으므로 전체 실패로 간주하지 않음
    fi

    if test_responsive_design; then
        test_results+=("✅ 반응형")
    else
        test_results+=("⚠️ 반응형")
        # 반응형도 warning일 수 있으므로 전체 실패로 간주하지 않음
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
            echo -e "${GREEN}🎉 모든 대시보드 스모크 테스트 통과! UI 구조 정상 확인${NC}"
            echo -e "${CYAN}💡 다음 단계: 브라우저에서 실제 동작 확인${NC}"
            echo "  1. 로컬 서버 실행: python3 -m http.server 8080 --directory web/"
            echo "  2. 브라우저 접속: http://localhost:8080/admin_dashboard.html"
            echo "  3. 모든 카드와 차트 정상 로딩 확인"
        else
            echo -e "${RED}💥 일부 대시보드 스모크 테스트 실패. UI 구조 점검 필요${NC}"
            echo -e "${YELLOW}💡 문제 해결 가이드:${NC}"
            echo "  1. 파일 백업 확인: git status"
            echo "  2. 원본 복원: git checkout web/admin_dashboard.html"
            echo "  3. 롤백 고려: make incident-rollback-dry"
        fi
        echo -e "${CYAN}📅 완료 시간: $(date)${NC}"
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

# jq 의존성 확인 (JSON 출력시에만)
if [[ "$JSON_OUTPUT" == "true" ]] && ! command -v jq &> /dev/null; then
    echo '{"error":"jq 명령어가 설치되어 있지 않습니다. brew install jq 또는 apt install jq로 설치하세요."}'
    exit 1
fi

# 메인 함수 호출
main "$@"