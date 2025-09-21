#!/bin/bash
# 📡 MCP-MAP CI/CD 모니터링 자동화 스크립트 (한국어 주석 포함)
# 기능:
# 1. GitHub Actions CI 실행 상태 실시간 확인 (gh CLI 활용)
# 2. 최근 10개 워크플로우 실행 로그 요약
# 3. 실패 빌드 감지 시 logs/ci_failures.log 자동 기록
# 4. 옵션: --json, --verbose, --watch, --help
# 5. 실패 시 notifier.py를 통한 자동 알림 연동

set -e  # 에러 발생 시 스크립트 중단

# 🔧 기본 설정
LOGS_DIR="logs"
CI_FAILURES_LOG="$LOGS_DIR/ci_failures.log"
WATCH_INTERVAL=30  # 초 단위
MAX_WORKFLOWS=10
JSON_OUTPUT=false
VERBOSE=false
WATCH_MODE=false
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# 🎨 색상 코드 (터미널 출력용)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# 📊 CI 통계
TOTAL_RUNS=0
SUCCESS_COUNT=0
FAILURE_COUNT=0
IN_PROGRESS_COUNT=0

# 📝 사용법 출력
usage() {
    echo "📡 MCP-MAP CI/CD 모니터링 자동화 스크립트"
    echo "사용법: $0 [옵션]"
    echo ""
    echo "옵션:"
    echo "  --json              JSON 형식 출력"
    echo "  --verbose           상세 출력 모드"
    echo "  --watch             실시간 모니터링 모드 (30초 간격)"
    echo "  --interval SECONDS  watch 모드 간격 설정 (기본값: 30초)"
    echo "  --count NUMBER      모니터링할 워크플로우 수 (기본값: 10개)"
    echo "  --help              이 도움말 표시"
    echo ""
    echo "예시:"
    echo "  $0 --verbose"
    echo "  $0 --json"
    echo "  $0 --watch --interval 60"
    echo "  $0 --count 20 --verbose"
    echo ""
    echo "전제조건:"
    echo "  - GitHub CLI (gh) 설치 및 인증 필요"
    echo "  - 리포지토리에서 실행해야 함"
}

# 📊 인수 파싱
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --json) JSON_OUTPUT=true ;;
        --verbose) VERBOSE=true ;;
        --watch) WATCH_MODE=true ;;
        --interval) WATCH_INTERVAL="$2"; shift ;;
        --count) MAX_WORKFLOWS="$2"; shift ;;
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
    if [ "$VERBOSE" = true ] || [ "$JSON_OUTPUT" = false ]; then
        echo -e "${GREEN}✅ $1${NC}"
    fi
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_failure() {
    echo -e "${RED}🚨 $1${NC}"
}

# 🔍 GitHub CLI 설치 및 인증 확인
check_prerequisites() {
    log_info "전제조건 확인 중..."

    # gh CLI 설치 확인
    if ! command -v gh &> /dev/null; then
        log_error "GitHub CLI (gh)가 설치되지 않았습니다"
        echo "설치 방법: https://cli.github.com/manual/installation"
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

# 📋 워크플로우 실행 목록 가져오기
get_workflow_runs() {
    log_info "최근 $MAX_WORKFLOWS개 워크플로우 실행 목록 가져오는 중..."

    # GitHub API를 통해 워크플로우 실행 목록 가져오기
    local runs_json=$(gh api repos/:owner/:repo/actions/runs \
        --jq ".workflow_runs | sort_by(.created_at) | reverse | .[:$MAX_WORKFLOWS]" 2>/dev/null || echo "[]")

    echo "$runs_json"
}

# 🔍 워크플로우 상태 분석
analyze_workflow_status() {
    local runs_json="$1"
    local failed_runs=()

    # JSON 파싱하여 상태별 카운트
    TOTAL_RUNS=$(echo "$runs_json" | jq '. | length')
    SUCCESS_COUNT=$(echo "$runs_json" | jq '[.[] | select(.conclusion == "success")] | length')
    FAILURE_COUNT=$(echo "$runs_json" | jq '[.[] | select(.conclusion == "failure")] | length')
    IN_PROGRESS_COUNT=$(echo "$runs_json" | jq '[.[] | select(.status == "in_progress")] | length')

    log_info "워크플로우 상태 분석 완료"
    log_info "총 실행: $TOTAL_RUNS, 성공: $SUCCESS_COUNT, 실패: $FAILURE_COUNT, 진행중: $IN_PROGRESS_COUNT"

    # 실패한 워크플로우 정보 추출
    local failed_data=$(echo "$runs_json" | jq -r '
        [.[] | select(.conclusion == "failure")] |
        map({
            id: .id,
            name: .name,
            branch: .head_branch,
            created_at: .created_at,
            html_url: .html_url,
            run_number: .run_number
        })
    ')

    echo "$failed_data"
}

# 📝 실패 로그 기록
log_ci_failures() {
    local failed_runs="$1"

    if [ "$(echo "$failed_runs" | jq '. | length')" -eq 0 ]; then
        log_info "실패한 워크플로우가 없습니다"
        return
    fi

    # 로그 디렉토리 생성
    mkdir -p "$LOGS_DIR"

    # 실패 로그 기록
    echo "# CI 실패 로그 - $TIMESTAMP" >> "$CI_FAILURES_LOG"
    echo "$failed_runs" | jq -r '.[] |
        "- 워크플로우: \(.name) (#\(.run_number))\n" +
        "  브랜치: \(.branch)\n" +
        "  실행 시간: \(.created_at)\n" +
        "  링크: \(.html_url)\n"' >> "$CI_FAILURES_LOG"
    echo "" >> "$CI_FAILURES_LOG"

    log_warning "실패한 워크플로우가 $CI_FAILURES_LOG에 기록되었습니다"

    # notifier.py를 통한 알림 전송 (파일이 있는 경우)
    if [ -f "mcp/utils/notifier.py" ]; then
        log_info "CI 실패 알림 전송 중..."
        python3 -c "
import sys
sys.path.append('.')
try:
    from mcp.utils.notifier import send_ci_alerts
    import asyncio
    import json

    failed_data = json.loads('$failed_runs')
    asyncio.run(send_ci_alerts(failed_data))
    print('✅ CI 실패 알림 전송 완료')
except Exception as e:
    print(f'⚠️ 알림 전송 실패: {e}')
" 2>/dev/null || log_warning "알림 전송 중 오류 발생"
    fi
}

# 📊 JSON 출력 생성
generate_json_output() {
    local runs_json="$1"
    local failed_runs="$2"

    local json_output=$(jq -n \
        --argjson runs "$runs_json" \
        --argjson failed "$failed_runs" \
        --arg timestamp "$TIMESTAMP" \
        --argjson total "$TOTAL_RUNS" \
        --argjson success "$SUCCESS_COUNT" \
        --argjson failure "$FAILURE_COUNT" \
        --argjson in_progress "$IN_PROGRESS_COUNT" \
        '{
            timestamp: $timestamp,
            summary: {
                total_runs: $total,
                success_count: $success,
                failure_count: $failure,
                in_progress_count: $in_progress,
                success_rate: (if $total > 0 then (($success * 100) / $total) else 0 end)
            },
            failed_workflows: $failed,
            recent_runs: $runs | map({
                id: .id,
                name: .name,
                status: .status,
                conclusion: .conclusion,
                branch: .head_branch,
                created_at: .created_at,
                html_url: .html_url,
                run_number: .run_number
            })
        }')

    echo "$json_output"
}

# 📋 텍스트 요약 출력
generate_text_summary() {
    local runs_json="$1"
    local failed_runs="$2"

    echo "📡 CI/CD 모니터링 요약"
    echo "===================="
    echo ""
    echo "⏰ 검사 시간: $TIMESTAMP"
    echo "📊 워크플로우 통계:"
    echo "  📋 총 실행: $TOTAL_RUNS개"
    echo "  ✅ 성공: $SUCCESS_COUNT개"
    echo "  ❌ 실패: $FAILURE_COUNT개"
    echo "  🔄 진행중: $IN_PROGRESS_COUNT개"
    echo "  📈 성공률: $(( TOTAL_RUNS > 0 ? (SUCCESS_COUNT * 100) / TOTAL_RUNS : 0 ))%"
    echo ""

    # 실패한 워크플로우 상세 정보
    local failure_count=$(echo "$failed_runs" | jq '. | length')
    if [ "$failure_count" -gt 0 ]; then
        echo "🚨 실패한 워크플로우 ($failure_count개):"
        echo "$failed_runs" | jq -r '.[] |
            "  • \(.name) (#\(.run_number)) - \(.branch) 브랜치\n" +
            "    실행 시간: \(.created_at)\n" +
            "    링크: \(.html_url)"'
        echo ""
    fi

    # 최근 워크플로우 목록 (verbose 모드)
    if [ "$VERBOSE" = true ]; then
        echo "📋 최근 워크플로우 실행 목록:"
        echo "$runs_json" | jq -r '.[] |
            "  • \(.name) (#\(.run_number)) - " +
            (if .conclusion == "success" then "✅ 성공"
             elif .conclusion == "failure" then "❌ 실패"
             elif .status == "in_progress" then "🔄 진행중"
             else "⚪ \(.status // .conclusion // "알 수 없음")" end) +
            " (\(.head_branch))"'
        echo ""
    fi

    echo "📁 로그 파일: $CI_FAILURES_LOG"
    echo "🔗 GitHub Actions: https://github.com/$(gh repo view --json owner,name -q '.owner.login + "/" + .name')/actions"
}

# 🔄 실시간 모니터링 모드
run_watch_mode() {
    echo -e "${CYAN}📡 CI/CD 실시간 모니터링 시작 (${WATCH_INTERVAL}초 간격)${NC}"
    echo "종료하려면 Ctrl+C를 누르세요"
    echo ""

    local iteration=0
    while true; do
        iteration=$((iteration + 1))
        echo -e "${PURPLE}=== 모니터링 #$iteration - $(date '+%H:%M:%S') ===${NC}"

        # CI 모니터링 실행
        monitor_ci_status

        echo ""
        echo -e "${BLUE}다음 검사까지 ${WATCH_INTERVAL}초 대기 중...${NC}"
        sleep "$WATCH_INTERVAL"
        echo ""
    done
}

# 🎯 메인 CI 모니터링 로직
monitor_ci_status() {
    # 워크플로우 실행 목록 가져오기
    local runs_json=$(get_workflow_runs)

    if [ "$runs_json" = "[]" ] || [ -z "$runs_json" ]; then
        log_warning "워크플로우 실행 목록을 가져올 수 없습니다"
        return 1
    fi

    # 워크플로우 상태 분석
    local failed_runs=$(analyze_workflow_status "$runs_json")

    # 실패 로그 기록 및 알림
    if [ "$(echo "$failed_runs" | jq '. | length')" -gt 0 ]; then
        log_ci_failures "$failed_runs"
    fi

    # 결과 출력
    if [ "$JSON_OUTPUT" = true ]; then
        generate_json_output "$runs_json" "$failed_runs"
    else
        generate_text_summary "$runs_json" "$failed_runs"
    fi
}

# 🚀 메인 실행 함수
main() {
    if [ "$JSON_OUTPUT" = false ]; then
        echo -e "${CYAN}📡 MCP-MAP CI/CD 모니터링 시작${NC}"
        echo "⏰ 실행 시간: $TIMESTAMP"
        echo ""
    fi

    # 전제조건 확인
    check_prerequisites

    # 로그 디렉토리 생성
    mkdir -p "$LOGS_DIR"

    # 실시간 모니터링 또는 단일 실행
    if [ "$WATCH_MODE" = true ]; then
        run_watch_mode
    else
        monitor_ci_status
    fi

    if [ "$JSON_OUTPUT" = false ]; then
        echo ""
        echo -e "${GREEN}🎉 CI/CD 모니터링 완료!${NC}"
    fi
}

# 🔥 트랩 설정 (Ctrl+C 처리)
trap 'echo -e "\n${YELLOW}📡 CI/CD 모니터링이 중단되었습니다${NC}"; exit 0' INT

# 실행
main