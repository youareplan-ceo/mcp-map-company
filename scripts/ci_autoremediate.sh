#!/bin/bash
# =============================================================================
# CI 자동 완화 스크립트 (CI Auto-Remediation Script)
# =============================================================================
# 목적: 실패 유형별 자동 완화 액션 실행 (안전한 드라이런 기본)
# Purpose: Execute automated remediation actions for different failure types
#
# 기능:
# - CI 에러 분석 리포트를 기반으로 자동 완화 액션 실행
# - 에러 유형별 매핑된 훅 스크립트 호출
# - 동일 유형 중복 방지 (15분 내)
# - 보호 워크플로 필터링
# - JSON/Markdown 결과 출력
#
# 작성자: CI/CD 자동화 팀
# 버전: 1.0.0
# 최종 수정: 2025-09-21
# =============================================================================

set -euo pipefail

# 전역 변수 설정
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
readonly HOOKS_DIR="$SCRIPT_DIR/hooks"
readonly DATA_DIR="$PROJECT_ROOT/data"
readonly LOGS_DIR="$PROJECT_ROOT/logs"
readonly REMEDIATION_LOG="$LOGS_DIR/autoremediate.log"
readonly DUPLICATE_PREVENTION_FILE="$DATA_DIR/remediation_locks.json"

# 기본 설정값
DEFAULT_MAX_ACTIONS=10
DEFAULT_DUPLICATE_TIMEOUT=900  # 15분 (초)
DEFAULT_OUTPUT_FORMAT="json"

# 명령줄 옵션 초기화
DRY_RUN_MODE=true  # 기본값: 드라이런 모드
APPLY_MODE=false
JSON_OUTPUT=false
VERBOSE_MODE=false
MAX_ACTIONS="$DEFAULT_MAX_ACTIONS"
INPUT_REPORT=""
OUTPUT_FORMAT="$DEFAULT_OUTPUT_FORMAT"

# 색상 코드 (터미널 출력용)
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly NC='\033[0m' # No Color

# 보호 워크플로 리스트 (건드리면 안 되는 워크플로)
readonly PROTECTED_WORKFLOWS=(
    "security-scan"
    "production-deploy"
    "master-build"
    "release-pipeline"
    "hotfix-deploy"
)

# 에러 유형별 훅 매핑
declare -A ERROR_TO_HOOK_MAP=(
    ["dependency_install_failed"]="clear_ci_cache.sh"
    ["test_timeout"]="retry_failed_tests.sh"
    ["build_timeout"]="restart_worker.sh"
    ["network_error"]="clear_ci_cache.sh"
    ["cache_corruption"]="clear_ci_cache.sh"
    ["worker_unavailable"]="restart_worker.sh"
    ["flaky_test"]="retry_failed_tests.sh"
    ["disk_space_full"]="clear_ci_cache.sh"
    ["memory_limit"]="restart_worker.sh"
    ["permission_denied"]="clear_ci_cache.sh"
)

# 로깅 함수
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    # 로그 디렉토리 생성
    mkdir -p "$LOGS_DIR"

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
        "DEBUG")
            if [[ "$VERBOSE_MODE" == true ]]; then
                echo -e "${BLUE}[DEBUG]${NC} ${timestamp} - $message" >&2
            fi
            ;;
        *)
            echo -e "${CYAN}[${level}]${NC} ${timestamp} - $message" >&2
            ;;
    esac

    # 파일에도 로그 기록
    echo "[$level] $timestamp - $message" >> "$REMEDIATION_LOG"
}

# 진행 상황 표시 함수
show_progress() {
    local current="$1"
    local total="$2"
    local description="$3"

    if [[ "$VERBOSE_MODE" == true ]]; then
        local percentage=$((current * 100 / total))
        printf "\r${BLUE}진행률:${NC} [%-20s] %d%% - %s" \
               "$(printf '#%.0s' $(seq 1 $((percentage / 5))))" \
               "$percentage" "$description" >&2

        if [[ "$current" -eq "$total" ]]; then
            echo "" >&2  # 새 줄 추가
        fi
    fi
}

# 도움말 표시 함수
show_help() {
    cat << 'EOF'
🛠️ CI 자동 완화 스크립트

사용법:
    ./scripts/ci_autoremediate.sh [옵션]

설명:
    CI 에러 분석 리포트를 기반으로 실패 유형별 자동 완화 액션을 실행합니다.
    안전한 드라이런 모드가 기본값이며, 동일 유형 중복 방지 및 보호 워크플로
    필터링 기능을 제공합니다.

주요 기능:
    • 에러 유형별 자동 매핑된 훅 스크립트 실행
    • 15분 내 동일 유형 중복 액션 방지
    • 보호 워크플로 필터링 (프로덕션 파이프라인 등)
    • JSON/Markdown 결과 출력 지원
    • 상세한 조치 내역 로깅

옵션:
    --dry-run       드라이런 모드 (기본값, 실제 액션 실행 안함)
    --apply         실제 완화 액션 실행 (보호 가드 유지)
    --json          JSON 형식으로 결과 출력
    --verbose       상세한 진행 상황 및 디버그 정보 표시
    --max-actions N 최대 실행할 액션 수 제한 (기본값: 10)
    --input REPORT  특정 CI 에러 리포트 파일 지정
    --help          이 도움말 메시지 표시

사용 예시:
    # 기본 드라이런 모드로 실행
    ./scripts/ci_autoremediate.sh

    # 최근 CI 에러 리포트를 자동 탐색하여 실제 적용
    ./scripts/ci_autoremediate.sh --apply --verbose

    # 특정 리포트 파일을 사용하여 JSON 출력
    ./scripts/ci_autoremediate.sh --input reports/ci-errors-latest.json --json

    # 최대 5개 액션만 실행 (드라이런)
    ./scripts/ci_autoremediate.sh --max-actions 5 --verbose

    # 실제 적용 모드 (신중히 사용)
    ./scripts/ci_autoremediate.sh --apply

에러 유형별 매핑:
    • dependency_install_failed → clear_ci_cache.sh
    • test_timeout → retry_failed_tests.sh
    • build_timeout → restart_worker.sh
    • network_error → clear_ci_cache.sh
    • flaky_test → retry_failed_tests.sh

보호 워크플로:
    • security-scan, production-deploy, master-build
    • release-pipeline, hotfix-deploy

안전 가드:
    • 15분 내 동일 에러 유형 중복 액션 방지
    • 보호 워크플로 자동 제외
    • 드라이런 모드 기본값
    • 상세한 실행 로그 및 감사 추적

출력 파일:
    • 조치 내역: logs/autoremediate.log
    • 중복 방지: data/remediation_locks.json
    • JSON 결과: stdout 또는 지정된 파일

종료 코드:
    • 0: 성공 또는 부분 성공
    • 1: 실패 (에러 발생)
    • 2: 입력 오류 (잘못된 옵션 또는 파일)

문의:
    운영팀 또는 CI/CD 관리자에게 연락하세요.

EOF
}

# 최근 CI 에러 리포트 자동 탐색 함수
find_latest_report() {
    log_message "DEBUG" "최근 CI 에러 리포트 자동 탐색 시작"

    local reports_dir="$PROJECT_ROOT/reports"
    local latest_report=""

    if [[ -d "$reports_dir" ]]; then
        # 가장 최근의 ci-errors 리포트 찾기
        latest_report=$(find "$reports_dir" -name "ci-errors-*.json" -type f -exec ls -t {} + | head -n 1)

        if [[ -n "$latest_report" && -f "$latest_report" ]]; then
            log_message "INFO" "최근 CI 에러 리포트 발견: $latest_report"
            echo "$latest_report"
            return 0
        fi
    fi

    # 대안: scripts/ci_error_analyzer.sh 실행하여 새 리포트 생성
    local analyzer_script="$SCRIPT_DIR/ci_error_analyzer.sh"
    if [[ -x "$analyzer_script" ]]; then
        log_message "INFO" "ci_error_analyzer.sh를 실행하여 새 리포트 생성 중..."

        if [[ "$DRY_RUN_MODE" == true ]]; then
            log_message "INFO" "드라이런 모드: 에러 분석기 실행 시뮬레이션"
            echo ""  # 빈 문자열 반환 (시뮬레이션)
        else
            # 실제 에러 분석기 실행
            if "$analyzer_script" --json --output-dir "$reports_dir" >/dev/null 2>&1; then
                # 새로 생성된 리포트 찾기
                latest_report=$(find "$reports_dir" -name "ci-errors-*.json" -type f -exec ls -t {} + | head -n 1)
                if [[ -n "$latest_report" ]]; then
                    log_message "INFO" "새 CI 에러 리포트 생성됨: $latest_report"
                    echo "$latest_report"
                    return 0
                fi
            fi
        fi
    fi

    log_message "WARN" "사용 가능한 CI 에러 리포트를 찾을 수 없습니다"
    echo ""
}

# 중복 액션 방지 체크 함수
is_duplicate_action() {
    local error_type="$1"
    local current_time=$(date +%s)

    # 데이터 디렉토리 생성
    mkdir -p "$DATA_DIR"

    # 중복 방지 파일이 없으면 빈 객체로 생성
    if [[ ! -f "$DUPLICATE_PREVENTION_FILE" ]]; then
        echo '{}' > "$DUPLICATE_PREVENTION_FILE"
    fi

    # jq가 설치되어 있는지 확인
    if ! command -v jq &> /dev/null; then
        log_message "WARN" "jq가 설치되지 않아 중복 방지 기능을 사용할 수 없습니다"
        return 1  # 중복이 아닌 것으로 처리
    fi

    # 이전 실행 시간 조회
    local last_action_time
    last_action_time=$(jq -r --arg error_type "$error_type" '.[$error_type] // 0' "$DUPLICATE_PREVENTION_FILE" 2>/dev/null || echo "0")

    # 시간 차이 계산
    local time_diff=$((current_time - last_action_time))

    if [[ "$time_diff" -lt "$DEFAULT_DUPLICATE_TIMEOUT" && "$last_action_time" -ne 0 ]]; then
        local remaining_time=$((DEFAULT_DUPLICATE_TIMEOUT - time_diff))
        log_message "WARN" "중복 액션 방지: $error_type 유형은 ${remaining_time}초 후 재시도 가능"
        return 0  # 중복임
    fi

    return 1  # 중복이 아님
}

# 중복 방지 파일 업데이트 함수
update_duplicate_prevention() {
    local error_type="$1"
    local current_time=$(date +%s)

    if command -v jq &> /dev/null; then
        # 기존 파일 읽고 업데이트
        local temp_file=$(mktemp)
        jq --arg error_type "$error_type" --arg timestamp "$current_time" \
           '.[$error_type] = ($timestamp | tonumber)' \
           "$DUPLICATE_PREVENTION_FILE" > "$temp_file" && \
           mv "$temp_file" "$DUPLICATE_PREVENTION_FILE"

        log_message "DEBUG" "중복 방지 파일 업데이트: $error_type = $current_time"
    fi
}

# 보호 워크플로 체크 함수
is_protected_workflow() {
    local workflow_name="$1"

    for protected in "${PROTECTED_WORKFLOWS[@]}"; do
        if [[ "$workflow_name" == *"$protected"* ]]; then
            log_message "WARN" "보호 워크플로 감지: $workflow_name (액션 건너뜀)"
            return 0  # 보호됨
        fi
    done

    return 1  # 보호되지 않음
}

# 훅 스크립트 실행 함수
execute_hook() {
    local hook_script="$1"
    local error_data="$2"
    local error_type="$3"

    local hook_path="$HOOKS_DIR/$hook_script"

    # 훅 스크립트 존재 및 실행 권한 확인
    if [[ ! -f "$hook_path" ]]; then
        log_message "ERROR" "훅 스크립트를 찾을 수 없음: $hook_path"
        return 1
    fi

    if [[ ! -x "$hook_path" ]]; then
        log_message "ERROR" "훅 스크립트 실행 권한 없음: $hook_path"
        return 1
    fi

    log_message "INFO" "훅 스크립트 실행: $hook_script (에러 유형: $error_type)"

    # 훅 스크립트 실행
    local hook_result=""
    local exit_code=0

    if [[ "$DRY_RUN_MODE" == true ]]; then
        log_message "INFO" "드라이런 모드: $hook_script 실행 시뮬레이션"
        hook_result="드라이런 모드 - 실제 실행되지 않음"
        exit_code=0
    else
        # 실제 훅 스크립트 실행 (에러 데이터를 stdin으로 전달)
        if hook_result=$(echo "$error_data" | "$hook_path" 2>&1); then
            exit_code=0
            log_message "INFO" "훅 스크립트 성공적으로 실행됨: $hook_script"
        else
            exit_code=$?
            log_message "ERROR" "훅 스크립트 실행 실패: $hook_script (종료 코드: $exit_code)"
        fi
    fi

    # 실행 결과 반환
    echo "$hook_result"
    return $exit_code
}

# CI 에러 리포트 파싱 함수
parse_error_report() {
    local report_file="$1"

    log_message "DEBUG" "CI 에러 리포트 파싱 시작: $report_file"

    if [[ ! -f "$report_file" ]]; then
        log_message "ERROR" "리포트 파일을 찾을 수 없음: $report_file"
        return 1
    fi

    # jq가 설치되어 있는지 확인
    if ! command -v jq &> /dev/null; then
        log_message "ERROR" "jq가 설치되지 않아 JSON 파싱을 할 수 없습니다"
        return 1
    fi

    # JSON 유효성 검사
    if ! jq empty "$report_file" 2>/dev/null; then
        log_message "ERROR" "잘못된 JSON 형식: $report_file"
        return 1
    fi

    # 에러 목록 추출 및 출력
    jq -c '.errors[]? // .error_summary[]? // []' "$report_file" 2>/dev/null || {
        log_message "WARN" "에러 데이터를 찾을 수 없음: $report_file"
        return 1
    }
}

# 완화 액션 실행 함수
execute_remediation() {
    local report_file="$1"
    local actions_executed=0
    local actions_succeeded=0
    local actions_failed=0
    local actions_skipped=0

    declare -a execution_results=()

    log_message "INFO" "CI 자동 완화 액션 실행 시작"

    # 에러 리포트 파싱
    local error_data
    if ! error_data=$(parse_error_report "$report_file"); then
        log_message "ERROR" "에러 리포트 파싱 실패"
        return 1
    fi

    # 에러가 없는 경우
    if [[ -z "$error_data" ]]; then
        log_message "INFO" "처리할 에러가 없습니다"
        return 0
    fi

    # 각 에러에 대해 액션 실행
    while IFS= read -r error_json; do
        if [[ $actions_executed -ge $MAX_ACTIONS ]]; then
            log_message "WARN" "최대 액션 수 도달 ($MAX_ACTIONS), 나머지 건너뜀"
            break
        fi

        # 에러 정보 추출
        local error_type
        local workflow_name
        local error_message

        error_type=$(echo "$error_json" | jq -r '.type // .error_type // "unknown"')
        workflow_name=$(echo "$error_json" | jq -r '.workflow // .workflow_name // "unknown"')
        error_message=$(echo "$error_json" | jq -r '.message // .error_message // "No message"')

        show_progress $((actions_executed + 1)) $MAX_ACTIONS "처리 중: $error_type"

        # 보호 워크플로 체크
        if is_protected_workflow "$workflow_name"; then
            actions_skipped=$((actions_skipped + 1))
            execution_results+=("{\"error_type\":\"$error_type\",\"workflow\":\"$workflow_name\",\"action\":\"skipped\",\"reason\":\"protected_workflow\"}")
            continue
        fi

        # 중복 액션 방지 체크
        if is_duplicate_action "$error_type"; then
            actions_skipped=$((actions_skipped + 1))
            execution_results+=("{\"error_type\":\"$error_type\",\"workflow\":\"$workflow_name\",\"action\":\"skipped\",\"reason\":\"duplicate_prevention\"}")
            continue
        fi

        # 에러 유형에 매핑된 훅 스크립트 찾기
        local hook_script="${ERROR_TO_HOOK_MAP[$error_type]:-}"

        if [[ -z "$hook_script" ]]; then
            log_message "WARN" "알 수 없는 에러 유형: $error_type (매핑된 훅 없음)"
            actions_skipped=$((actions_skipped + 1))
            execution_results+=("{\"error_type\":\"$error_type\",\"workflow\":\"$workflow_name\",\"action\":\"skipped\",\"reason\":\"no_mapping\"}")
            continue
        fi

        # 훅 스크립트 실행
        local hook_output
        if hook_output=$(execute_hook "$hook_script" "$error_json" "$error_type"); then
            actions_succeeded=$((actions_succeeded + 1))
            execution_results+=("{\"error_type\":\"$error_type\",\"workflow\":\"$workflow_name\",\"action\":\"$hook_script\",\"status\":\"success\",\"output\":\"$hook_output\"}")

            # 중복 방지 파일 업데이트 (성공한 경우만)
            update_duplicate_prevention "$error_type"
        else
            actions_failed=$((actions_failed + 1))
            execution_results+=("{\"error_type\":\"$error_type\",\"workflow\":\"$workflow_name\",\"action\":\"$hook_script\",\"status\":\"failed\",\"output\":\"$hook_output\"}")
        fi

        actions_executed=$((actions_executed + 1))

    done <<< "$error_data"

    # 실행 결과 요약
    log_message "INFO" "완화 액션 실행 완료"
    log_message "INFO" "총 실행: $actions_executed, 성공: $actions_succeeded, 실패: $actions_failed, 건너뜀: $actions_skipped"

    # 결과를 전역 변수에 저장 (출력 함수에서 사용)
    EXECUTION_SUMMARY="{\"total_executed\":$actions_executed,\"succeeded\":$actions_succeeded,\"failed\":$actions_failed,\"skipped\":$actions_skipped,\"results\":[$(IFS=,; echo "${execution_results[*]}")]}"

    # 종료 코드 결정
    if [[ $actions_failed -gt 0 ]]; then
        return 1  # 실패가 있음
    else
        return 0  # 성공 또는 부분 성공
    fi
}

# 결과 출력 함수
output_results() {
    local exit_code="$1"

    if [[ "$JSON_OUTPUT" == true ]]; then
        # JSON 형식 출력
        local final_result
        final_result=$(echo "$EXECUTION_SUMMARY" | jq --arg exit_code "$exit_code" \
                      --arg timestamp "$(date -Iseconds)" \
                      --arg mode "$([ "$DRY_RUN_MODE" == true ] && echo "dry_run" || echo "apply")" \
                      '. + {exit_code: ($exit_code | tonumber), timestamp: $timestamp, mode: $mode}')
        echo "$final_result"
    else
        # Markdown 형식 출력
        echo "# 🛠️ CI 자동 완화 실행 결과"
        echo
        echo "**실행 시간**: $(date)"
        echo "**모드**: $([ "$DRY_RUN_MODE" == true ] && echo "드라이런" || echo "실제 적용")"
        echo "**종료 코드**: $exit_code"
        echo

        if [[ -n "$EXECUTION_SUMMARY" ]]; then
            local total_executed succeeded failed skipped
            total_executed=$(echo "$EXECUTION_SUMMARY" | jq -r '.total_executed')
            succeeded=$(echo "$EXECUTION_SUMMARY" | jq -r '.succeeded')
            failed=$(echo "$EXECUTION_SUMMARY" | jq -r '.failed')
            skipped=$(echo "$EXECUTION_SUMMARY" | jq -r '.skipped')

            echo "## 📊 실행 요약"
            echo "- **총 실행**: $total_executed"
            echo "- **성공**: $succeeded"
            echo "- **실패**: $failed"
            echo "- **건너뜀**: $skipped"
            echo

            echo "## 📋 상세 결과"
            echo "$EXECUTION_SUMMARY" | jq -r '.results[] | "- **\(.error_type)** (\(.workflow)): \(.action // "N/A") - \(.status // .reason)"'
        fi
    fi
}

# 메인 함수
main() {
    local input_report="$INPUT_REPORT"
    local exit_code=0

    log_message "INFO" "CI 자동 완화 스크립트 시작 (버전: 1.0.0)"
    log_message "INFO" "모드: $([ "$DRY_RUN_MODE" == true ] && echo "드라이런" || echo "실제 적용")"

    # 필요한 디렉토리 생성
    mkdir -p "$DATA_DIR" "$LOGS_DIR"

    # 입력 리포트가 지정되지 않은 경우 자동 탐색
    if [[ -z "$input_report" ]]; then
        input_report=$(find_latest_report)
        if [[ -z "$input_report" ]]; then
            log_message "ERROR" "사용 가능한 CI 에러 리포트를 찾을 수 없습니다"
            exit_code=2
            output_results "$exit_code"
            exit $exit_code
        fi
    fi

    # 입력 리포트 유효성 검사
    if [[ ! -f "$input_report" ]]; then
        log_message "ERROR" "지정된 리포트 파일을 찾을 수 없음: $input_report"
        exit_code=2
        output_results "$exit_code"
        exit $exit_code
    fi

    log_message "INFO" "사용할 CI 에러 리포트: $input_report"

    # 완화 액션 실행
    if execute_remediation "$input_report"; then
        exit_code=0
        log_message "INFO" "CI 자동 완화 스크립트 성공적으로 완료"
    else
        exit_code=1
        log_message "ERROR" "CI 자동 완화 스크립트 실행 중 오류 발생"
    fi

    # 결과 출력
    output_results "$exit_code"

    exit $exit_code
}

# 명령줄 인수 파싱
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN_MODE=true
            APPLY_MODE=false
            shift
            ;;
        --apply)
            DRY_RUN_MODE=false
            APPLY_MODE=true
            shift
            ;;
        --json)
            JSON_OUTPUT=true
            OUTPUT_FORMAT="json"
            shift
            ;;
        --verbose)
            VERBOSE_MODE=true
            shift
            ;;
        --max-actions)
            MAX_ACTIONS="$2"
            # 숫자 유효성 검사
            if ! [[ "$MAX_ACTIONS" =~ ^[0-9]+$ ]] || [[ "$MAX_ACTIONS" -le 0 ]]; then
                echo "오류: --max-actions 값은 양의 정수여야 합니다" >&2
                exit 2
            fi
            shift 2
            ;;
        --input)
            INPUT_REPORT="$2"
            shift 2
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo "오류: 알 수 없는 옵션: $1" >&2
            echo "사용법은 --help를 참조하세요" >&2
            exit 2
            ;;
    esac
done

# 메인 함수 실행
main