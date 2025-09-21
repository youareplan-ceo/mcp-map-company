#!/bin/bash
# 📊 MCP-MAP CI/CD 성능 리포트 자동화 스크립트 (한국어 주석 포함)
# 기능:
# 1. GitHub Actions 로그 수집 및 요약 분석
# 2. 실패 테스트만 필터링하여 상세 분석
# 3. 성능 지표(실행 시간, 실패율) 자동 계산
# 4. JSON/Markdown 출력 형식 지원
# 5. Slack/Discord/Email 알림 연동
# 6. 일간/주간/월간 리포트 생성 기능

set -e  # 에러 발생 시 스크립트 중단

# 🔧 기본 설정
LOGS_DIR="logs"
REPORTS_DIR="reports"
CI_REPORT_LOG="$LOGS_DIR/ci_reports.log"
MAX_RUNS=20
JSON_OUTPUT=false
MARKDOWN_OUTPUT=false
VERBOSE=false
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
REPORT_DATE=$(date '+%Y%m%d')

# 🎨 색상 코드 (터미널 출력용)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# 📊 성능 지표 변수
TOTAL_RUNS=0
SUCCESS_COUNT=0
FAILURE_COUNT=0
CANCELLED_COUNT=0
TOTAL_DURATION=0
AVG_DURATION=0
FAILURE_RATE=0
SUCCESS_RATE=0

# 📋 실패 테스트 상세 정보
declare -a FAILED_TESTS=()
declare -a PERFORMANCE_ISSUES=()

# 📝 사용법 출력
usage() {
    echo "📊 MCP-MAP CI/CD 성능 리포트 자동화 스크립트"
    echo "사용법: $0 [옵션]"
    echo ""
    echo "옵션:"
    echo "  --json              JSON 형식 출력"
    echo "  --md, --markdown    Markdown 형식 출력"
    echo "  --verbose           상세 출력 모드"
    echo "  --runs NUMBER       분석할 워크플로우 수 (기본값: 20개)"
    echo "  --days NUMBER       분석 기간 (기본값: 7일)"
    echo "  --notify            알림 전송 활성화"
    echo "  --help              이 도움말 표시"
    echo ""
    echo "출력 형식:"
    echo "  - 기본: 터미널 친화적 컬러 출력"
    echo "  - JSON: 자동화 파이프라인용"
    echo "  - Markdown: 문서화 및 공유용"
    echo ""
    echo "예시:"
    echo "  $0 --verbose"
    echo "  $0 --json --runs 50"
    echo "  $0 --md --days 30 --notify"
    echo "  $0 --json > reports/ci_report_\$(date +%Y%m%d).json"
    echo ""
    echo "전제조건:"
    echo "  - GitHub CLI (gh) 설치 및 인증 필요"
    echo "  - 리포지토리에서 실행해야 함"
    echo "  - jq 설치 필요 (JSON 처리용)"
}

# 📊 인수 파싱
DAYS=7
NOTIFY=false

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --json) JSON_OUTPUT=true ;;
        --md|--markdown) MARKDOWN_OUTPUT=true ;;
        --verbose) VERBOSE=true ;;
        --runs) MAX_RUNS="$2"; shift ;;
        --days) DAYS="$2"; shift ;;
        --notify) NOTIFY=true ;;
        --help) usage; exit 0 ;;
        *) echo "❌ 알 수 없는 옵션: $1"; usage; exit 1 ;;
    esac
    shift
done

# 🎭 출력 함수
log_info() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}ℹ️  $1${NC}"
    fi
}

log_success() {
    if [ "$VERBOSE" = true ] || [ "$JSON_OUTPUT" = false ] && [ "$MARKDOWN_OUTPUT" = false ]; then
        echo -e "${GREEN}✅ $1${NC}"
    fi
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_stat() {
    if [ "$VERBOSE" = true ] || [ "$JSON_OUTPUT" = false ] && [ "$MARKDOWN_OUTPUT" = false ]; then
        echo -e "${CYAN}📊 $1${NC}"
    fi
}

# 🔍 전제조건 확인
check_prerequisites() {
    log_info "전제조건 확인 중..."

    # gh CLI 설치 확인
    if ! command -v gh &> /dev/null; then
        log_error "GitHub CLI (gh)가 설치되지 않았습니다"
        echo "설치 방법: https://cli.github.com/manual/installation"
        exit 1
    fi

    # jq 설치 확인
    if ! command -v jq &> /dev/null; then
        log_error "jq가 설치되지 않았습니다"
        echo "설치 방법: brew install jq (macOS) 또는 apt-get install jq (Ubuntu)"
        exit 1
    fi

    # gh CLI 인증 확인
    if ! gh auth status &> /dev/null; then
        log_error "GitHub CLI 인증이 필요합니다"
        echo "인증 방법: gh auth login"
        exit 1
    fi

    # Git 리포지토리 확인
    if ! git rev-parse --git-dir &> /dev/null; then
        log_error "Git 리포지토리에서 실행해야 합니다"
        exit 1
    fi

    log_info "전제조건 확인 완료"
}

# 📋 워크플로우 실행 데이터 수집
collect_workflow_data() {
    log_info "최근 $MAX_RUNS개 워크플로우 데이터 수집 중..."

    # 지정된 기간 내 워크플로우 실행 목록 가져오기
    local since_date=$(date -d "$DAYS days ago" '+%Y-%m-%d' 2>/dev/null || date -v-${DAYS}d '+%Y-%m-%d')

    local runs_json=$(gh api repos/:owner/:repo/actions/runs \
        --jq ".workflow_runs | map(select(.created_at >= \"$since_date\")) | sort_by(.created_at) | reverse | .[:$MAX_RUNS]" \
        2>/dev/null || echo "[]")

    if [ "$runs_json" = "[]" ] || [ -z "$runs_json" ]; then
        log_warning "워크플로우 실행 데이터를 가져올 수 없습니다"
        return 1
    fi

    echo "$runs_json"
}

# 🧮 성능 지표 계산
calculate_performance_metrics() {
    local runs_json="$1"

    log_info "성능 지표 계산 중..."

    # 기본 통계 계산
    TOTAL_RUNS=$(echo "$runs_json" | jq '. | length')
    SUCCESS_COUNT=$(echo "$runs_json" | jq '[.[] | select(.conclusion == "success")] | length')
    FAILURE_COUNT=$(echo "$runs_json" | jq '[.[] | select(.conclusion == "failure")] | length')
    CANCELLED_COUNT=$(echo "$runs_json" | jq '[.[] | select(.conclusion == "cancelled")] | length')

    # 실행 시간 통계 계산 (완료된 워크플로우만)
    local completed_runs=$(echo "$runs_json" | jq '[.[] | select(.conclusion != null and .conclusion != "in_progress")]')
    local duration_sum=$(echo "$completed_runs" | jq 'map(
        ((.updated_at | strptime("%Y-%m-%dT%H:%M:%SZ") | mktime) -
         (.created_at | strptime("%Y-%m-%dT%H:%M:%SZ") | mktime))
    ) | add // 0')

    local completed_count=$(echo "$completed_runs" | jq '. | length')

    if [ "$completed_count" -gt 0 ]; then
        TOTAL_DURATION=$duration_sum
        AVG_DURATION=$(echo "scale=2; $TOTAL_DURATION / $completed_count" | bc -l 2>/dev/null || echo "0")
    fi

    # 성공률 및 실패율 계산
    if [ "$TOTAL_RUNS" -gt 0 ]; then
        SUCCESS_RATE=$(echo "scale=2; $SUCCESS_COUNT * 100 / $TOTAL_RUNS" | bc -l 2>/dev/null || echo "0")
        FAILURE_RATE=$(echo "scale=2; $FAILURE_COUNT * 100 / $TOTAL_RUNS" | bc -l 2>/dev/null || echo "0")
    fi

    log_info "성능 지표 계산 완료"
}

# 🔍 실패 테스트 상세 분석
analyze_failed_tests() {
    local runs_json="$1"

    log_info "실패 테스트 상세 분석 중..."

    # 실패한 워크플로우 목록 추출
    local failed_runs=$(echo "$runs_json" | jq '[.[] | select(.conclusion == "failure")]')
    local failed_count=$(echo "$failed_runs" | jq '. | length')

    if [ "$failed_count" -eq 0 ]; then
        log_info "실패한 테스트가 없습니다"
        return 0
    fi

    # 각 실패한 워크플로우의 상세 정보 수집
    echo "$failed_runs" | jq -r '.[] | .id' | while read -r run_id; do
        if [ -n "$run_id" ]; then
            # 워크플로우 실행 로그 요약 가져오기
            local run_details=$(gh api repos/:owner/:repo/actions/runs/$run_id 2>/dev/null || echo "{}")
            local jobs_data=$(gh api repos/:owner/:repo/actions/runs/$run_id/jobs 2>/dev/null || echo '{"jobs":[]}')

            # 실패한 스텝 정보 추출
            local failed_jobs=$(echo "$jobs_data" | jq -r '.jobs[] | select(.conclusion == "failure") |
                {
                    name: .name,
                    conclusion: .conclusion,
                    started_at: .started_at,
                    completed_at: .completed_at,
                    steps: [.steps[] | select(.conclusion == "failure") | {name: .name, conclusion: .conclusion}]
                }')

            if [ -n "$failed_jobs" ] && [ "$failed_jobs" != "null" ]; then
                FAILED_TESTS+=("$failed_jobs")
            fi
        fi
    done

    log_info "실패 테스트 분석 완료 (총 $failed_count개 실패)"
}

# 🚀 성능 이슈 감지
detect_performance_issues() {
    local runs_json="$1"

    log_info "성능 이슈 감지 중..."

    # 장시간 실행 워크플로우 감지 (30분 이상)
    local long_running=$(echo "$runs_json" | jq --arg threshold "1800" '[
        .[] | select(
            .conclusion != null and
            ((.updated_at | strptime("%Y-%m-%dT%H:%M:%SZ") | mktime) -
             (.created_at | strptime("%Y-%m-%dT%H:%M:%SZ") | mktime)) > ($threshold | tonumber)
        ) | {
            id: .id,
            name: .name,
            duration: ((.updated_at | strptime("%Y-%m-%dT%H:%M:%SZ") | mktime) -
                      (.created_at | strptime("%Y-%m-%dT%H:%M:%SZ") | mktime)),
            branch: .head_branch,
            created_at: .created_at
        }
    ]')

    # 반복적 실패 패턴 감지
    local frequent_failures=$(echo "$runs_json" | jq '[
        .[] | select(.conclusion == "failure") | .head_branch
    ] | group_by(.) | map({
        branch: .[0],
        count: length
    }) | map(select(.count > 2))')

    # 성능 이슈 목록에 추가
    if [ "$(echo "$long_running" | jq '. | length')" -gt 0 ]; then
        PERFORMANCE_ISSUES+=("장시간 실행: $(echo "$long_running" | jq '. | length')개 워크플로우가 30분 이상 실행")
    fi

    if [ "$(echo "$frequent_failures" | jq '. | length')" -gt 0 ]; then
        PERFORMANCE_ISSUES+=("반복 실패: $(echo "$frequent_failures" | jq -r '.[] | "\(.branch) 브랜치 \(.count)회 실패"')")
    fi

    log_info "성능 이슈 감지 완료"
}

# 📄 JSON 리포트 생성
generate_json_report() {
    local runs_json="$1"

    # 실패 테스트 정보를 JSON 배열로 변환
    local failed_tests_json="[]"
    if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
        failed_tests_json=$(printf '%s\n' "${FAILED_TESTS[@]}" | jq -s '.')
    fi

    # 성능 이슈를 JSON 배열로 변환
    local performance_issues_json="[]"
    if [ ${#PERFORMANCE_ISSUES[@]} -gt 0 ]; then
        performance_issues_json=$(printf '%s\n' "${PERFORMANCE_ISSUES[@]}" | jq -R '.' | jq -s '.')
    fi

    local json_report=$(jq -n \
        --argjson runs "$runs_json" \
        --argjson failed_tests "$failed_tests_json" \
        --argjson performance_issues "$performance_issues_json" \
        --arg timestamp "$TIMESTAMP" \
        --arg report_date "$REPORT_DATE" \
        --argjson total "$TOTAL_RUNS" \
        --argjson success "$SUCCESS_COUNT" \
        --argjson failure "$FAILURE_COUNT" \
        --argjson cancelled "$CANCELLED_COUNT" \
        --argjson total_duration "$TOTAL_DURATION" \
        --argjson avg_duration "$AVG_DURATION" \
        --argjson success_rate "$SUCCESS_RATE" \
        --argjson failure_rate "$FAILURE_RATE" \
        --argjson analysis_days "$DAYS" \
        '{
            report_metadata: {
                generated_at: $timestamp,
                report_date: $report_date,
                analysis_period_days: $analysis_days,
                workflow_count: $total
            },
            performance_summary: {
                total_runs: $total,
                success_count: $success,
                failure_count: $failure,
                cancelled_count: $cancelled,
                success_rate: $success_rate,
                failure_rate: $failure_rate,
                avg_duration_seconds: $avg_duration,
                total_duration_seconds: $total_duration
            },
            failed_tests: $failed_tests,
            performance_issues: $performance_issues,
            recent_workflows: $runs | map({
                id: .id,
                name: .name,
                status: .status,
                conclusion: .conclusion,
                branch: .head_branch,
                created_at: .created_at,
                updated_at: .updated_at,
                duration_seconds: (
                    if .updated_at and .created_at then
                        (.updated_at | strptime("%Y-%m-%dT%H:%M:%SZ") | mktime) -
                        (.created_at | strptime("%Y-%m-%dT%H:%M:%SZ") | mktime)
                    else null end
                ),
                html_url: .html_url,
                run_number: .run_number
            })
        }')

    echo "$json_report"
}

# 📄 Markdown 리포트 생성
generate_markdown_report() {
    local runs_json="$1"

    cat << EOF
# 📊 CI/CD 성능 리포트

**생성 일시:** $TIMESTAMP
**분석 기간:** 최근 $DAYS일
**분석 워크플로우:** $TOTAL_RUNS개

## 📈 성능 요약

| 지표 | 값 | 비율 |
|------|-----|------|
| 총 실행 | $TOTAL_RUNS개 | 100% |
| ✅ 성공 | $SUCCESS_COUNT개 | ${SUCCESS_RATE}% |
| ❌ 실패 | $FAILURE_COUNT개 | ${FAILURE_RATE}% |
| ⏹️ 취소 | $CANCELLED_COUNT개 | $(echo "scale=2; $CANCELLED_COUNT * 100 / $TOTAL_RUNS" | bc -l 2>/dev/null || echo "0")% |
| ⏱️ 평균 실행 시간 | $(echo "scale=0; $AVG_DURATION / 60" | bc -l 2>/dev/null || echo "0")분 | - |

## 🚨 실패 분석

EOF

    if [ "$FAILURE_COUNT" -gt 0 ]; then
        echo "### 실패한 워크플로우 목록"
        echo ""
        echo "$runs_json" | jq -r '.[] | select(.conclusion == "failure") |
            "- **\(.name)** (#\(.run_number)) - `\(.head_branch)` 브랜치  " +
            "  실행 시간: \(.created_at)  " +
            "  링크: [\(.html_url)](\(.html_url))  "
        '
        echo ""
    else
        echo "✅ 분석 기간 동안 실패한 워크플로우가 없습니다."
        echo ""
    fi

    if [ ${#PERFORMANCE_ISSUES[@]} -gt 0 ]; then
        echo "### ⚠️ 성능 이슈"
        echo ""
        for issue in "${PERFORMANCE_ISSUES[@]}"; do
            echo "- $issue"
        done
        echo ""
    fi

    echo "## 📋 최근 워크플로우 실행 이력"
    echo ""
    echo "| 워크플로우 | 상태 | 브랜치 | 실행 시간 | 소요 시간 |"
    echo "|------------|------|---------|-----------|----------|"

    echo "$runs_json" | jq -r '.[] |
        "| \(.name) (#\(.run_number)) | " +
        (if .conclusion == "success" then "✅ 성공"
         elif .conclusion == "failure" then "❌ 실패"
         elif .conclusion == "cancelled" then "⏹️ 취소"
         elif .status == "in_progress" then "🔄 진행중"
         else "⚪ \(.status // .conclusion // "알 수 없음")" end) +
        " | `\(.head_branch)` | \(.created_at | split("T")[0]) | " +
        (if .updated_at and .created_at then
            (((.updated_at | strptime("%Y-%m-%dT%H:%M:%SZ") | mktime) -
              (.created_at | strptime("%Y-%m-%dT%H:%M:%SZ") | mktime)) / 60 | floor | tostring) + "분"
        else "진행중" end) + " |"
    '

    echo ""
    echo "---"
    echo ""
    echo "📁 **로그 파일:** $CI_REPORT_LOG  "
    echo "🔗 **GitHub Actions:** https://github.com/$(gh repo view --json owner,name -q '.owner.login + "/" + .name')/actions  "
    echo ""
    echo "*리포트 생성 시간: $TIMESTAMP*"
}

# 📋 터미널 요약 출력
generate_terminal_summary() {
    local runs_json="$1"

    echo -e "${WHITE}📊 CI/CD 성능 리포트${NC}"
    echo "=========================="
    echo ""
    echo -e "⏰ 생성 시간: ${CYAN}$TIMESTAMP${NC}"
    echo -e "📅 분석 기간: ${CYAN}최근 $DAYS일${NC}"
    echo -e "📋 분석 대상: ${CYAN}$TOTAL_RUNS개 워크플로우${NC}"
    echo ""

    log_stat "성능 요약:"
    echo -e "  📋 총 실행: ${WHITE}$TOTAL_RUNS${NC}개"
    echo -e "  ✅ 성공: ${GREEN}$SUCCESS_COUNT${NC}개 (${GREEN}${SUCCESS_RATE}%${NC})"
    echo -e "  ❌ 실패: ${RED}$FAILURE_COUNT${NC}개 (${RED}${FAILURE_RATE}%${NC})"
    echo -e "  ⏹️ 취소: ${YELLOW}$CANCELLED_COUNT${NC}개"
    echo -e "  ⏱️ 평균 실행 시간: ${CYAN}$(echo "scale=1; $AVG_DURATION / 60" | bc -l 2>/dev/null || echo "0")${NC}분"
    echo ""

    # 실패 워크플로우 상세 정보
    if [ "$FAILURE_COUNT" -gt 0 ]; then
        echo -e "${RED}🚨 실패한 워크플로우 ($FAILURE_COUNT개):${NC}"
        echo "$runs_json" | jq -r '.[] | select(.conclusion == "failure") |
            "  • \(.name) (#\(.run_number)) - \(.head_branch) 브랜치\n" +
            "    실행 시간: \(.created_at)\n" +
            "    링크: \(.html_url)"'
        echo ""
    fi

    # 성능 이슈 표시
    if [ ${#PERFORMANCE_ISSUES[@]} -gt 0 ]; then
        echo -e "${YELLOW}⚠️ 감지된 성능 이슈:${NC}"
        for issue in "${PERFORMANCE_ISSUES[@]}"; do
            echo -e "  • ${YELLOW}$issue${NC}"
        done
        echo ""
    fi

    # 최근 워크플로우 목록 (verbose 모드)
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}📋 최근 워크플로우 실행 목록:${NC}"
        echo "$runs_json" | jq -r '.[] |
            "  • \(.name) (#\(.run_number)) - " +
            (if .conclusion == "success" then "✅ 성공"
             elif .conclusion == "failure" then "❌ 실패"
             elif .conclusion == "cancelled" then "⏹️ 취소"
             elif .status == "in_progress" then "🔄 진행중"
             else "⚪ \(.status // .conclusion // "알 수 없음")" end) +
            " (\(.head_branch))"'
        echo ""
    fi

    echo -e "📁 리포트 로그: ${CYAN}$CI_REPORT_LOG${NC}"
    echo -e "🔗 GitHub Actions: ${CYAN}https://github.com/$(gh repo view --json owner,name -q '.owner.login + "/" + .name')/actions${NC}"
}

# 📝 리포트 로그 저장
save_report_log() {
    local report_data="$1"
    local format="$2"

    # 로그 및 리포트 디렉토리 생성
    mkdir -p "$LOGS_DIR" "$REPORTS_DIR"

    # 요약 로그 저장
    echo "# CI/CD 성능 리포트 - $TIMESTAMP" >> "$CI_REPORT_LOG"
    echo "분석 기간: $DAYS일, 워크플로우: $TOTAL_RUNS개" >> "$CI_REPORT_LOG"
    echo "성공: $SUCCESS_COUNT개 (${SUCCESS_RATE}%), 실패: $FAILURE_COUNT개 (${FAILURE_RATE}%)" >> "$CI_REPORT_LOG"
    echo "평균 실행 시간: $(echo "scale=1; $AVG_DURATION / 60" | bc -l 2>/dev/null || echo "0")분" >> "$CI_REPORT_LOG"
    echo "" >> "$CI_REPORT_LOG"

    # 상세 리포트 파일 저장
    case $format in
        "json")
            echo "$report_data" > "$REPORTS_DIR/ci_report_${REPORT_DATE}.json"
            log_success "JSON 리포트가 $REPORTS_DIR/ci_report_${REPORT_DATE}.json에 저장되었습니다"
            ;;
        "markdown")
            echo "$report_data" > "$REPORTS_DIR/ci_report_${REPORT_DATE}.md"
            log_success "Markdown 리포트가 $REPORTS_DIR/ci_report_${REPORT_DATE}.md에 저장되었습니다"
            ;;
    esac
}

# 📧 알림 전송
send_notifications() {
    local report_data="$1"
    local format="$2"

    if [ "$NOTIFY" = true ] && [ -f "mcp/utils/notifier.py" ]; then
        log_info "CI/CD 성능 리포트 알림 전송 중..."

        # Python 스크립트를 통한 알림 전송
        python3 -c "
import sys
import json
sys.path.append('.')
try:
    from mcp.utils.notifier import send_ci_report_alert
    import asyncio

    report_summary = {
        'timestamp': '$TIMESTAMP',
        'total_runs': $TOTAL_RUNS,
        'success_count': $SUCCESS_COUNT,
        'failure_count': $FAILURE_COUNT,
        'success_rate': $SUCCESS_RATE,
        'failure_rate': $FAILURE_RATE,
        'avg_duration_minutes': $(echo "scale=1; $AVG_DURATION / 60" | bc -l 2>/dev/null || echo "0"),
        'analysis_days': $DAYS
    }

    asyncio.run(send_ci_report_alert(report_summary))
    print('✅ CI/CD 성능 리포트 알림 전송 완료')
except Exception as e:
    print(f'⚠️ 알림 전송 실패: {e}')
" 2>/dev/null || log_warning "알림 전송 중 오류 발생"
    fi
}

# 🎯 메인 리포팅 로직
generate_ci_report() {
    # 워크플로우 데이터 수집
    local runs_json=$(collect_workflow_data)

    if [ $? -ne 0 ] || [ "$runs_json" = "[]" ]; then
        log_error "워크플로우 데이터 수집 실패"
        return 1
    fi

    # 성능 지표 계산
    calculate_performance_metrics "$runs_json"

    # 실패 테스트 분석
    analyze_failed_tests "$runs_json"

    # 성능 이슈 감지
    detect_performance_issues "$runs_json"

    # 리포트 생성 및 출력
    local report_data=""
    local format=""

    if [ "$JSON_OUTPUT" = true ]; then
        format="json"
        report_data=$(generate_json_report "$runs_json")
        echo "$report_data"
        save_report_log "$report_data" "$format"
    elif [ "$MARKDOWN_OUTPUT" = true ]; then
        format="markdown"
        report_data=$(generate_markdown_report "$runs_json")
        echo "$report_data"
        save_report_log "$report_data" "$format"
    else
        format="terminal"
        generate_terminal_summary "$runs_json"
        save_report_log "terminal_summary" "$format"
    fi

    # 알림 전송
    send_notifications "$report_data" "$format"
}

# 🚀 메인 실행 함수
main() {
    if [ "$JSON_OUTPUT" = false ] && [ "$MARKDOWN_OUTPUT" = false ]; then
        echo -e "${CYAN}📊 MCP-MAP CI/CD 성능 리포트 생성 시작${NC}"
        echo "⏰ 실행 시간: $TIMESTAMP"
        echo ""
    fi

    # 전제조건 확인
    check_prerequisites

    # 디렉토리 생성
    mkdir -p "$LOGS_DIR" "$REPORTS_DIR"

    # CI/CD 성능 리포트 생성
    generate_ci_report

    if [ "$JSON_OUTPUT" = false ] && [ "$MARKDOWN_OUTPUT" = false ]; then
        echo ""
        echo -e "${GREEN}🎉 CI/CD 성능 리포트 생성 완료!${NC}"
    fi
}

# 🔥 트랩 설정 (Ctrl+C 처리)
trap 'echo -e "\n${YELLOW}📊 CI/CD 성능 리포트 생성이 중단되었습니다${NC}"; exit 0' INT

# 실행
main