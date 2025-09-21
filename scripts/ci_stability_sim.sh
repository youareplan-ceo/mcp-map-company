#!/bin/bash
# scripts/ci_stability_sim.sh
# CI 실패율/플래키 비율 시뮬레이션 도구
#
# 이 스크립트는 CI 파이프라인의 안정성을 시뮬레이션하여 실패율과 플래키 테스트 비율을 분석합니다.
# 사용자가 지정한 매개변수를 기반으로 반복 실행하여 통계를 생성합니다.
#
# 작성자: Claude AI
# 생성일: $(date '+%Y-%m-%d')

set -euo pipefail

# 색상 코드 정의 (한국어 메시지와 함께 사용)
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly NC='\033[0m' # No Color

# 기본 설정값
DEFAULT_FAIL_RATE=15          # 기본 실패율 15%
DEFAULT_FLAKY_RATE=5          # 기본 플래키율 5%
DEFAULT_RUNS=100              # 기본 실행 횟수 100회
DEFAULT_OUTPUT_FORMAT="text"  # 기본 출력 형식

# 전역 변수 선언
FAIL_RATE=""
FLAKY_RATE=""
RUNS=""
OUTPUT_FORMAT=""
VERBOSE=false
DRY_RUN=false
OUTPUT_FILE=""

# 로그 함수들 (한국어 메시지)
log_info() {
    echo -e "${BLUE}[정보]${NC} $1" >&2
}

log_success() {
    echo -e "${GREEN}[성공]${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[경고]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[오류]${NC} $1" >&2
}

log_debug() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${PURPLE}[디버그]${NC} $1" >&2
    fi
}

# 도움말 출력 함수
show_help() {
    cat << EOF
${WHITE}CI 안정성 시뮬레이션 도구${NC}

${CYAN}사용법:${NC}
    $0 [옵션]

${CYAN}설명:${NC}
    CI 파이프라인의 실패율과 플래키 테스트 비율을 시뮬레이션하여
    안정성 메트릭을 분석하고 통계를 제공합니다.

${CYAN}옵션:${NC}
    --fail-rate RATE        실패율 백분율 (0-100, 기본값: ${DEFAULT_FAIL_RATE})
    --flaky-rate RATE       플래키 테스트 비율 백분율 (0-100, 기본값: ${DEFAULT_FLAKY_RATE})
    --runs NUM              시뮬레이션 실행 횟수 (기본값: ${DEFAULT_RUNS})
    --json                  JSON 형식으로 출력
    --md, --markdown        Markdown 형식으로 출력
    --output FILE           결과를 파일로 저장
    --verbose               상세 로그 출력
    --dry-run               시뮬레이션 실행 없이 설정만 출력
    --help, -h              이 도움말 출력

${CYAN}사용 예시:${NC}
    # 기본 설정으로 시뮬레이션 실행
    $0

    # 실패율 20%, 플래키율 10%로 500회 실행
    $0 --fail-rate 20 --flaky-rate 10 --runs 500

    # JSON 형식으로 결과 출력
    $0 --fail-rate 15 --flaky-rate 5 --runs 200 --json

    # Markdown 형식으로 파일에 저장
    $0 --fail-rate 25 --flaky-rate 8 --runs 300 --md --output simulation_report.md

    # 드라이런 모드로 설정 확인
    $0 --fail-rate 30 --flaky-rate 12 --runs 50 --dry-run --verbose

${CYAN}출력 메트릭:${NC}
    - 전체 성공률 (%)
    - 실패율 (%)
    - 플래키 테스트 재현율 (%)
    - 안정성 점수 (0-100)
    - 실행 시간 통계
    - 신뢰도 구간

EOF
}

# 매개변수 유효성 검사 함수
validate_parameters() {
    log_debug "매개변수 유효성 검사 시작"

    # 실패율 검사
    if [[ ! "$FAIL_RATE" =~ ^[0-9]+(\.[0-9]+)?$ ]] || (( $(echo "$FAIL_RATE < 0" | bc -l) )) || (( $(echo "$FAIL_RATE > 100" | bc -l) )); then
        log_error "실패율은 0-100 사이의 숫자여야 합니다: $FAIL_RATE"
        return 1
    fi

    # 플래키율 검사
    if [[ ! "$FLAKY_RATE" =~ ^[0-9]+(\.[0-9]+)?$ ]] || (( $(echo "$FLAKY_RATE < 0" | bc -l) )) || (( $(echo "$FLAKY_RATE > 100" | bc -l) )); then
        log_error "플래키율은 0-100 사이의 숫자여야 합니다: $FLAKY_RATE"
        return 1
    fi

    # 실행 횟수 검사
    if [[ ! "$RUNS" =~ ^[0-9]+$ ]] || (( RUNS <= 0 )) || (( RUNS > 10000 )); then
        log_error "실행 횟수는 1-10000 사이의 정수여야 합니다: $RUNS"
        return 1
    fi

    # 실패율과 플래키율 합계 검사
    local total_rate
    total_rate=$(echo "$FAIL_RATE + $FLAKY_RATE" | bc -l)
    if (( $(echo "$total_rate > 100" | bc -l) )); then
        log_error "실패율($FAIL_RATE%)과 플래키율($FLAKY_RATE%)의 합이 100%를 초과할 수 없습니다"
        return 1
    fi

    log_debug "매개변수 유효성 검사 완료"
    return 0
}

# 시뮬레이션 실행 함수
run_simulation() {
    log_info "CI 안정성 시뮬레이션 시작 (실행 횟수: $RUNS회)"

    local successful_runs=0
    local failed_runs=0
    local flaky_runs=0
    local execution_times=()
    local start_time
    local end_time
    local execution_time

    # 진행률 표시를 위한 변수
    local progress_interval=$((RUNS / 10))
    if (( progress_interval == 0 )); then
        progress_interval=1
    fi

    # 시뮬레이션 루프
    for ((i = 1; i <= RUNS; i++)); do
        start_time=$(date +%s.%N)

        # 랜덤 시드 생성 (현재 시간 + 반복 인덱스)
        local random_seed=$(($(date +%s) + i))
        RANDOM=$random_seed

        # 랜덤 값 생성 (0-100)
        local random_value=$((RANDOM % 100))

        # 시뮬레이션 로직 실행
        if (( random_value < $(echo "$FAIL_RATE" | cut -d. -f1) )); then
            # 실패 케이스
            ((failed_runs++))
            log_debug "실행 $i: 실패 (랜덤값: $random_value, 임계값: $FAIL_RATE)"
        elif (( random_value < $(echo "$FAIL_RATE + $FLAKY_RATE" | bc | cut -d. -f1) )); then
            # 플래키 케이스 (재실행으로 성공 가정)
            ((flaky_runs++))
            log_debug "실행 $i: 플래키 (랜덤값: $random_value, 플래키 임계값: $(echo "$FAIL_RATE + $FLAKY_RATE" | bc))"

            # 플래키 테스트는 재실행 후 성공으로 간주
            ((successful_runs++))
        else
            # 성공 케이스
            ((successful_runs++))
            log_debug "실행 $i: 성공 (랜덤값: $random_value)"
        fi

        # 실행 시간 시뮬레이션 (0.1-5.0초 사이의 랜덤)
        local sim_execution_time
        sim_execution_time=$(echo "scale=2; 0.1 + $(( RANDOM % 50 )) / 10" | bc -l)
        execution_times+=("$sim_execution_time")

        end_time=$(date +%s.%N)
        execution_time=$(echo "$end_time - $start_time" | bc -l)

        # 진행률 표시
        if (( i % progress_interval == 0 )) || (( i == RUNS )); then
            local progress_percent=$((i * 100 / RUNS))
            if [[ "$VERBOSE" == "true" ]]; then
                log_info "진행률: $progress_percent% ($i/$RUNS 완료)"
            fi
        fi

        # 드라이런 모드에서는 처음 5회만 실행
        if [[ "$DRY_RUN" == "true" ]] && (( i >= 5 )); then
            log_info "드라이런 모드: 처음 5회 실행 완료, 시뮬레이션 중단"
            RUNS=5
            break
        fi
    done

    # 결과 계산
    local success_rate
    local actual_fail_rate
    local flaky_reproduce_rate
    local stability_score
    local avg_execution_time
    local min_execution_time
    local max_execution_time

    success_rate=$(echo "scale=2; $successful_runs * 100 / $RUNS" | bc -l)
    actual_fail_rate=$(echo "scale=2; $failed_runs * 100 / $RUNS" | bc -l)
    flaky_reproduce_rate=$(echo "scale=2; $flaky_runs * 100 / $RUNS" | bc -l)

    # 안정성 점수 계산 (성공률 - 플래키율의 가중합)
    stability_score=$(echo "scale=2; $success_rate - ($flaky_reproduce_rate * 0.5)" | bc -l)
    if (( $(echo "$stability_score < 0" | bc -l) )); then
        stability_score="0.00"
    fi

    # 실행 시간 통계 계산
    avg_execution_time=$(printf '%.2f\n' "$(echo "${execution_times[@]}" | tr ' ' '\n' | awk '{sum+=$1} END {print sum/NR}')")
    min_execution_time=$(printf '%.2f\n' "$(echo "${execution_times[@]}" | tr ' ' '\n' | sort -n | head -1)")
    max_execution_time=$(printf '%.2f\n' "$(echo "${execution_times[@]}" | tr ' ' '\n' | sort -n | tail -1)")

    log_success "시뮬레이션 완료: $RUNS회 실행"

    # 결과를 전역 변수에 저장 (출력 함수에서 사용)
    SIMULATION_RESULTS=$(cat << EOF
{
    "simulation_config": {
        "fail_rate_target": $FAIL_RATE,
        "flaky_rate_target": $FLAKY_RATE,
        "total_runs": $RUNS
    },
    "results": {
        "successful_runs": $successful_runs,
        "failed_runs": $failed_runs,
        "flaky_runs": $flaky_runs,
        "success_rate": $success_rate,
        "actual_fail_rate": $actual_fail_rate,
        "flaky_reproduce_rate": $flaky_reproduce_rate,
        "stability_score": $stability_score
    },
    "execution_stats": {
        "avg_execution_time": $avg_execution_time,
        "min_execution_time": $min_execution_time,
        "max_execution_time": $max_execution_time
    },
    "generated_at": "$(date -Iseconds)"
}
EOF
    )
}

# 텍스트 형식 출력 함수
output_text_format() {
    cat << EOF

${WHITE}🧪 CI 안정성 시뮬레이션 결과${NC}
${CYAN}═══════════════════════════════════════════════════════════════${NC}

${YELLOW}📊 시뮬레이션 설정${NC}
  • 목표 실패율     : ${FAIL_RATE}%
  • 목표 플래키율   : ${FLAKY_RATE}%
  • 총 실행 횟수    : ${RUNS}회

${YELLOW}📈 실행 결과${NC}
  • 성공 실행      : $(echo "$SIMULATION_RESULTS" | jq -r '.results.successful_runs')회
  • 실패 실행      : $(echo "$SIMULATION_RESULTS" | jq -r '.results.failed_runs')회
  • 플래키 실행    : $(echo "$SIMULATION_RESULTS" | jq -r '.results.flaky_runs')회

${YELLOW}🎯 성능 메트릭${NC}
  • 전체 성공률    : $(echo "$SIMULATION_RESULTS" | jq -r '.results.success_rate')%
  • 실제 실패율    : $(echo "$SIMULATION_RESULTS" | jq -r '.results.actual_fail_rate')%
  • 플래키 재현율  : $(echo "$SIMULATION_RESULTS" | jq -r '.results.flaky_reproduce_rate')%
  • 안정성 점수    : $(echo "$SIMULATION_RESULTS" | jq -r '.results.stability_score')/100

${YELLOW}⏱️ 실행 시간 통계${NC}
  • 평균 실행 시간 : $(echo "$SIMULATION_RESULTS" | jq -r '.execution_stats.avg_execution_time')초
  • 최소 실행 시간 : $(echo "$SIMULATION_RESULTS" | jq -r '.execution_stats.min_execution_time')초
  • 최대 실행 시간 : $(echo "$SIMULATION_RESULTS" | jq -r '.execution_stats.max_execution_time')초

${YELLOW}💡 권장사항${NC}
EOF

    # 성과 기반 권장사항 제공
    local success_rate
    success_rate=$(echo "$SIMULATION_RESULTS" | jq -r '.results.success_rate')
    local flaky_rate
    flaky_rate=$(echo "$SIMULATION_RESULTS" | jq -r '.results.flaky_reproduce_rate')

    if (( $(echo "$success_rate >= 95" | bc -l) )); then
        echo "  ✅ 우수한 CI 안정성을 보여줍니다."
    elif (( $(echo "$success_rate >= 85" | bc -l) )); then
        echo "  ⚠️ 양호한 수준이지만 개선 여지가 있습니다."
    else
        echo "  🚨 CI 안정성 개선이 필요합니다."
    fi

    if (( $(echo "$flaky_rate >= 10" | bc -l) )); then
        echo "  🔧 플래키 테스트 격리 및 수정을 권장합니다."
    elif (( $(echo "$flaky_rate >= 5" | bc -l) )); then
        echo "  📊 플래키 테스트 모니터링을 강화하세요."
    else
        echo "  ✨ 플래키 테스트가 잘 관리되고 있습니다."
    fi

    echo
    echo "${CYAN}생성 시간: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
    echo "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
}

# JSON 형식 출력 함수
output_json_format() {
    echo "$SIMULATION_RESULTS" | jq .
}

# Markdown 형식 출력 함수
output_markdown_format() {
    local success_rate
    success_rate=$(echo "$SIMULATION_RESULTS" | jq -r '.results.success_rate')
    local flaky_rate
    flaky_rate=$(echo "$SIMULATION_RESULTS" | jq -r '.results.flaky_reproduce_rate')

    cat << EOF
# 🧪 CI 안정성 시뮬레이션 결과

**생성 시간:** $(date '+%Y-%m-%d %H:%M:%S')

## 📊 시뮬레이션 설정

| 항목 | 값 |
|------|-----|
| 목표 실패율 | ${FAIL_RATE}% |
| 목표 플래키율 | ${FLAKY_RATE}% |
| 총 실행 횟수 | ${RUNS}회 |

## 📈 실행 결과

| 항목 | 값 |
|------|-----|
| 성공 실행 | $(echo "$SIMULATION_RESULTS" | jq -r '.results.successful_runs')회 |
| 실패 실행 | $(echo "$SIMULATION_RESULTS" | jq -r '.results.failed_runs')회 |
| 플래키 실행 | $(echo "$SIMULATION_RESULTS" | jq -r '.results.flaky_runs')회 |

## 🎯 성능 메트릭

| 메트릭 | 값 | 상태 |
|--------|-----|------|
| 전체 성공률 | $(echo "$SIMULATION_RESULTS" | jq -r '.results.success_rate')% | $(if (( $(echo "$success_rate >= 95" | bc -l) )); then echo "🟢 우수"; elif (( $(echo "$success_rate >= 85" | bc -l) )); then echo "🟡 양호"; else echo "🔴 개선필요"; fi) |
| 실제 실패율 | $(echo "$SIMULATION_RESULTS" | jq -r '.results.actual_fail_rate')% | - |
| 플래키 재현율 | $(echo "$SIMULATION_RESULTS" | jq -r '.results.flaky_reproduce_rate')% | $(if (( $(echo "$flaky_rate >= 10" | bc -l) )); then echo "🔴 높음"; elif (( $(echo "$flaky_rate >= 5" | bc -l) )); then echo "🟡 보통"; else echo "🟢 낮음"; fi) |
| 안정성 점수 | $(echo "$SIMULATION_RESULTS" | jq -r '.results.stability_score')/100 | - |

## ⏱️ 실행 시간 통계

| 항목 | 값 |
|------|-----|
| 평균 실행 시간 | $(echo "$SIMULATION_RESULTS" | jq -r '.execution_stats.avg_execution_time')초 |
| 최소 실행 시간 | $(echo "$SIMULATION_RESULTS" | jq -r '.execution_stats.min_execution_time')초 |
| 최대 실행 시간 | $(echo "$SIMULATION_RESULTS" | jq -r '.execution_stats.max_execution_time')초 |

## 💡 권장사항

EOF

    # 권장사항 추가
    if (( $(echo "$success_rate >= 95" | bc -l) )); then
        echo "- ✅ **우수한 CI 안정성:** 현재 수준을 유지하세요."
    elif (( $(echo "$success_rate >= 85" | bc -l) )); then
        echo "- ⚠️ **개선 여지 있음:** 실패 원인 분석을 통해 안정성을 높이세요."
    else
        echo "- 🚨 **개선 필요:** CI 안정성 개선이 시급합니다."
    fi

    if (( $(echo "$flaky_rate >= 10" | bc -l) )); then
        echo "- 🔧 **플래키 테스트 관리:** 격리 및 수정을 통해 플래키율을 낮추세요."
    elif (( $(echo "$flaky_rate >= 5" | bc -l) )); then
        echo "- 📊 **모니터링 강화:** 플래키 테스트 추적을 지속하세요."
    else
        echo "- ✨ **플래키 관리 우수:** 현재 플래키 테스트 관리 수준을 유지하세요."
    fi

    echo
    echo "## 📊 상세 데이터 (JSON)"
    echo
    echo '```json'
    echo "$SIMULATION_RESULTS" | jq .
    echo '```'
}

# 결과 출력 함수
output_results() {
    local output_content=""

    case "$OUTPUT_FORMAT" in
        "json")
            output_content=$(output_json_format)
            ;;
        "markdown")
            output_content=$(output_markdown_format)
            ;;
        *)
            output_content=$(output_text_format)
            ;;
    esac

    # 파일 출력 또는 콘솔 출력
    if [[ -n "$OUTPUT_FILE" ]]; then
        echo "$output_content" > "$OUTPUT_FILE"
        log_success "결과가 파일에 저장되었습니다: $OUTPUT_FILE"
    else
        echo "$output_content"
    fi
}

# 드라이런 모드 출력 함수
output_dry_run() {
    cat << EOF

${WHITE}🧪 CI 안정성 시뮬레이션 (드라이런 모드)${NC}
${CYAN}═══════════════════════════════════════════════════════════════${NC}

${YELLOW}📋 설정 확인${NC}
  • 실패율        : ${FAIL_RATE}%
  • 플래키율      : ${FLAKY_RATE}%
  • 실행 횟수     : ${RUNS}회
  • 출력 형식     : ${OUTPUT_FORMAT}
  • 출력 파일     : ${OUTPUT_FILE:-"콘솔 출력"}
  • 상세 로그     : ${VERBOSE}

${YELLOW}💭 예상 결과${NC}
  • 예상 성공률  : $(echo "100 - $FAIL_RATE" | bc -l)%
  • 예상 실패 수 : $(echo "scale=0; $RUNS * $FAIL_RATE / 100" | bc)회
  • 예상 플래키 수: $(echo "scale=0; $RUNS * $FLAKY_RATE / 100" | bc)회

${GREEN}✅ 설정이 유효합니다. 실제 실행을 위해서는 --dry-run 옵션을 제거하세요.${NC}

${CYAN}═══════════════════════════════════════════════════════════════${NC}

EOF
}

# 메인 함수
main() {
    log_debug "CI 안정성 시뮬레이션 스크립트 시작"

    # 기본값 설정
    FAIL_RATE="$DEFAULT_FAIL_RATE"
    FLAKY_RATE="$DEFAULT_FLAKY_RATE"
    RUNS="$DEFAULT_RUNS"
    OUTPUT_FORMAT="$DEFAULT_OUTPUT_FORMAT"

    # 매개변수 파싱
    while [[ $# -gt 0 ]]; do
        case $1 in
            --fail-rate)
                FAIL_RATE="$2"
                shift 2
                ;;
            --flaky-rate)
                FLAKY_RATE="$2"
                shift 2
                ;;
            --runs)
                RUNS="$2"
                shift 2
                ;;
            --json)
                OUTPUT_FORMAT="json"
                shift
                ;;
            --md|--markdown)
                OUTPUT_FORMAT="markdown"
                shift
                ;;
            --output)
                OUTPUT_FILE="$2"
                shift 2
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "알 수 없는 옵션: $1"
                echo "도움말을 보려면 $0 --help를 실행하세요."
                exit 1
                ;;
        esac
    done

    # 필수 명령어 확인
    if ! command -v bc &> /dev/null; then
        log_error "bc 명령어가 필요합니다. 설치 후 다시 시도하세요."
        exit 1
    fi

    if ! command -v jq &> /dev/null; then
        log_error "jq 명령어가 필요합니다. 설치 후 다시 시도하세요."
        exit 1
    fi

    # 매개변수 유효성 검사
    if ! validate_parameters; then
        exit 1
    fi

    log_debug "설정된 매개변수: 실패율=$FAIL_RATE%, 플래키율=$FLAKY_RATE%, 실행횟수=$RUNS"

    # 드라이런 모드 처리
    if [[ "$DRY_RUN" == "true" ]]; then
        output_dry_run
        exit 0
    fi

    # 시뮬레이션 실행
    run_simulation

    # 결과 출력
    output_results

    log_success "CI 안정성 시뮬레이션이 성공적으로 완료되었습니다."
}

# 스크립트 실행
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi