#!/bin/bash
# scripts/runbook_validator.sh
# 런북 시스템 검증 도구
#
# 이 스크립트는 mcp/utils/runbook.py에 정의된 에러 유형과 실제 훅/스크립트 매핑을 확인합니다.
# 누락된 매핑, 중복된 매핑, 잘못된 참조 등을 자동으로 검출하여 런북 시스템의 무결성을 보장합니다.
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
readonly RUNBOOK_MODULE="mcp/utils/runbook.py"
readonly AUTOREMEDIATE_SCRIPT="scripts/ci_autoremediate.sh"
readonly HOOKS_DIR="scripts/hooks"
readonly DEFAULT_OUTPUT_FORMAT="text"

# 전역 변수 선언
OUTPUT_FORMAT="$DEFAULT_OUTPUT_FORMAT"
VERBOSE=false
OUTPUT_FILE=""
VALIDATION_RESULTS=""

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
${WHITE}런북 시스템 검증 도구${NC}

${CYAN}사용법:${NC}
    $0 [옵션]

${CYAN}설명:${NC}
    mcp/utils/runbook.py에 정의된 에러 유형과 실제 훅/스크립트 매핑을 확인하여
    런북 시스템의 무결성을 검증하고 누락/중복 사항을 리포트합니다.

${CYAN}옵션:${NC}
    --json                  JSON 형식으로 출력
    --output FILE           결과를 파일로 저장
    --verbose               상세 로그 출력
    --help, -h              이 도움말 출력

${CYAN}검증 항목:${NC}
    1. 런북 템플릿 정의 확인
    2. 에러 타입별 훅 매핑 검증
    3. 훅 스크립트 존재성 확인
    4. 중복/누락 매핑 탐지
    5. 스크립트 실행 권한 확인
    6. 런북 카테고리 일관성 검사

${CYAN}사용 예시:${NC}
    # 기본 검증 실행
    $0

    # JSON 형식으로 결과 출력
    $0 --json

    # 상세 로그와 함께 파일에 저장
    $0 --verbose --output validation_report.txt

${CYAN}출력 형식:${NC}
    - 검증 통과/실패 상태
    - 누락된 매핑 목록
    - 중복된 매핑 목록
    - 권한 문제 항목
    - 권장 수정 사항

EOF
}

# 필수 파일 존재성 확인 함수
check_required_files() {
    log_debug "필수 파일 존재성 확인 시작"

    local required_files=(
        "$RUNBOOK_MODULE"
        "$AUTOREMEDIATE_SCRIPT"
    )

    local missing_files=()

    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            missing_files+=("$file")
            log_error "필수 파일이 없습니다: $file"
        else
            log_debug "파일 확인 완료: $file"
        fi
    done

    if [[ ! -d "$HOOKS_DIR" ]]; then
        missing_files+=("$HOOKS_DIR (디렉토리)")
        log_error "훅 디렉토리가 없습니다: $HOOKS_DIR"
    else
        log_debug "훅 디렉토리 확인 완료: $HOOKS_DIR"
    fi

    if [[ ${#missing_files[@]} -gt 0 ]]; then
        log_error "필수 파일/디렉토리가 누락되었습니다: ${missing_files[*]}"
        return 1
    fi

    log_debug "모든 필수 파일 존재성 확인 완료"
    return 0
}

# 런북 템플릿 추출 함수
extract_runbook_templates() {
    log_debug "런북 템플릿 추출 시작"

    if [[ ! -f "$RUNBOOK_MODULE" ]]; then
        log_error "런북 모듈을 찾을 수 없습니다: $RUNBOOK_MODULE"
        return 1
    fi

    # Python을 사용하여 RUNBOOK_TEMPLATES 딕셔너리에서 키 추출
    local templates
    templates=$(python3 -c "
import sys
import os
sys.path.insert(0, os.path.dirname('$RUNBOOK_MODULE'))
try:
    from mcp.utils.runbook import RUNBOOK_TEMPLATES
    import json
    print(json.dumps(list(RUNBOOK_TEMPLATES.keys())))
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null)

    if [[ $? -ne 0 ]] || [[ -z "$templates" ]]; then
        log_error "런북 템플릿 추출에 실패했습니다"
        return 1
    fi

    echo "$templates"
    log_debug "런북 템플릿 추출 완료: $(echo "$templates" | jq length) 개"
    return 0
}

# 에러 타입 매핑 추출 함수
extract_error_mappings() {
    log_debug "에러 타입 매핑 추출 시작"

    if [[ ! -f "$AUTOREMEDIATE_SCRIPT" ]]; then
        log_error "자동 완화 스크립트를 찾을 수 없습니다: $AUTOREMEDIATE_SCRIPT"
        return 1
    fi

    # bash 스크립트에서 ERROR_TO_HOOK_MAP 배열 추출
    local mappings
    mappings=$(grep -A 20 "declare -A ERROR_TO_HOOK_MAP" "$AUTOREMEDIATE_SCRIPT" | \
               grep -E '^\s*\["[^"]+"\]=' | \
               sed 's/.*\["\([^"]*\)"\]="/\1/' | \
               sed 's/"$//' | \
               jq -R . | jq -s .)

    if [[ $? -ne 0 ]] || [[ -z "$mappings" ]]; then
        log_warning "에러 타입 매핑 추출에 실패했습니다 (빈 매핑일 수 있음)"
        echo "[]"
        return 0
    fi

    echo "$mappings"
    log_debug "에러 타입 매핑 추출 완료: $(echo "$mappings" | jq length) 개"
    return 0
}

# 훅 파일 목록 추출 함수
extract_hook_files() {
    log_debug "훅 파일 목록 추출 시작"

    if [[ ! -d "$HOOKS_DIR" ]]; then
        log_error "훅 디렉토리를 찾을 수 없습니다: $HOOKS_DIR"
        return 1
    fi

    # .sh 확장자를 가진 파일들만 추출
    local hook_files
    hook_files=$(find "$HOOKS_DIR" -name "*.sh" -type f | sort | jq -R . | jq -s .)

    if [[ $? -ne 0 ]]; then
        log_error "훅 파일 목록 추출에 실패했습니다"
        return 1
    fi

    echo "$hook_files"
    log_debug "훅 파일 목록 추출 완료: $(echo "$hook_files" | jq length) 개"
    return 0
}

# 훅-에러 매핑 추출 함수
extract_hook_error_mappings() {
    log_debug "훅-에러 매핑 추출 시작"

    if [[ ! -f "$AUTOREMEDIATE_SCRIPT" ]]; then
        log_error "자동 완화 스크립트를 찾을 수 없습니다: $AUTOREMEDIATE_SCRIPT"
        return 1
    fi

    # ERROR_TO_HOOK_MAP에서 에러타입:훅파일 매핑 추출
    local mappings
    mappings=$(grep -A 20 "declare -A ERROR_TO_HOOK_MAP" "$AUTOREMEDIATE_SCRIPT" | \
               grep -E '^\s*\["[^"]+"\]=' | \
               sed 's/.*\["\([^"]*\)"\]="\([^"]*\)".*/{"error_type": "\1", "hook_file": "\2"}/' | \
               jq -s .)

    if [[ $? -ne 0 ]] || [[ -z "$mappings" ]]; then
        log_warning "훅-에러 매핑 추출에 실패했습니다 (빈 매핑일 수 있음)"
        echo "[]"
        return 0
    fi

    echo "$mappings"
    log_debug "훅-에러 매핑 추출 완료: $(echo "$mappings" | jq length) 개"
    return 0
}

# 런북 카테고리 정보 추출 함수
extract_runbook_categories() {
    log_debug "런북 카테고리 정보 추출 시작"

    if [[ ! -f "$RUNBOOK_MODULE" ]]; then
        log_error "런북 모듈을 찾을 수 없습니다: $RUNBOOK_MODULE"
        return 1
    fi

    # Python을 사용하여 각 템플릿의 카테고리 정보 추출
    local categories
    categories=$(python3 -c "
import sys
import os
sys.path.insert(0, os.path.dirname('$RUNBOOK_MODULE'))
try:
    from mcp.utils.runbook import RUNBOOK_TEMPLATES
    import json
    result = []
    for error_type, template in RUNBOOK_TEMPLATES.items():
        result.append({
            'error_type': error_type,
            'category': template.get('category', 'UNKNOWN'),
            'severity': template.get('severity', 'UNKNOWN')
        })
    print(json.dumps(result))
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null)

    if [[ $? -ne 0 ]] || [[ -z "$categories" ]]; then
        log_error "런북 카테고리 정보 추출에 실패했습니다"
        return 1
    fi

    echo "$categories"
    log_debug "런북 카테고리 정보 추출 완료: $(echo "$categories" | jq length) 개"
    return 0
}

# 실행 권한 확인 함수
check_executable_permissions() {
    log_debug "실행 권한 확인 시작"

    local scripts_to_check=(
        "$AUTOREMEDIATE_SCRIPT"
    )

    # 훅 파일들 추가
    while IFS= read -r hook_file; do
        scripts_to_check+=("$hook_file")
    done < <(find "$HOOKS_DIR" -name "*.sh" -type f 2>/dev/null || true)

    local permission_issues=()

    for script in "${scripts_to_check[@]}"; do
        if [[ -f "$script" ]] && [[ ! -x "$script" ]]; then
            permission_issues+=("$script")
            log_warning "실행 권한이 없습니다: $script"
        elif [[ -f "$script" ]]; then
            log_debug "실행 권한 확인 완료: $script"
        fi
    done

    echo "${permission_issues[@]}" | jq -R 'split(" ") | map(select(length > 0))'
}

# 종합 검증 실행 함수
run_validation() {
    log_info "런북 시스템 종합 검증 시작"

    # 필수 파일 존재성 확인
    if ! check_required_files; then
        log_error "필수 파일 검사 실패"
        return 1
    fi

    # 데이터 추출
    local runbook_templates
    local error_mappings
    local hook_files
    local hook_error_mappings
    local runbook_categories
    local permission_issues

    log_info "런북 데이터 추출 중..."

    runbook_templates=$(extract_runbook_templates)
    if [[ $? -ne 0 ]]; then
        log_error "런북 템플릿 추출 실패"
        return 1
    fi

    error_mappings=$(extract_error_mappings)
    hook_files=$(extract_hook_files)
    hook_error_mappings=$(extract_hook_error_mappings)
    runbook_categories=$(extract_runbook_categories)
    permission_issues=$(check_executable_permissions)

    log_info "데이터 추출 완료, 검증 분석 시작..."

    # 검증 결과 계산
    local total_runbook_templates
    local total_error_mappings
    local total_hook_files
    local mapped_error_types
    local unmapped_error_types
    local missing_hooks
    local orphaned_hooks
    local duplicate_mappings
    local category_issues

    total_runbook_templates=$(echo "$runbook_templates" | jq length)
    total_error_mappings=$(echo "$error_mappings" | jq length)
    total_hook_files=$(echo "$hook_files" | jq length)

    # 매핑된 에러 타입 찾기
    mapped_error_types=$(echo "$hook_error_mappings" | jq '[.[].error_type] | unique')

    # 매핑되지 않은 런북 템플릿 찾기
    unmapped_error_types=$(echo "$runbook_templates $mapped_error_types" | jq -s '.[0] - .[1]')

    # 존재하지 않는 훅 파일 참조 찾기
    missing_hooks=$(echo "$hook_error_mappings" | jq --argjson hookfiles "$(echo "$hook_files" | jq 'map(split("/")[-1])')" '
        [.[] | select(.hook_file as $h | $hookfiles | index($h) | not) | .hook_file] | unique
    ')

    # 사용되지 않는 훅 파일 찾기 (고아 훅)
    orphaned_hooks=$(echo "$hook_files $hook_error_mappings" | jq -s '
        .[0] | map(split("/")[-1]) as $all_hooks |
        .[1] | map(.hook_file) | unique as $used_hooks |
        $all_hooks - $used_hooks
    ')

    # 중복 매핑 찾기
    duplicate_mappings=$(echo "$hook_error_mappings" | jq '
        group_by(.error_type) | map(select(length > 1)) | map(.[0].error_type)
    ')

    # 카테고리 일관성 확인
    local category_count
    category_count=$(echo "$runbook_categories" | jq '[.[] | .category] | group_by(.) | map({category: .[0], count: length})')

    # 심각도 분포 확인
    local severity_count
    severity_count=$(echo "$runbook_categories" | jq '[.[] | .severity] | group_by(.) | map({severity: .[0], count: length})')

    # 전체 검증 결과 생성
    local validation_status
    local issues_count
    issues_count=$(($(echo "$unmapped_error_types" | jq length) + $(echo "$missing_hooks" | jq length) + $(echo "$duplicate_mappings" | jq length)))

    if [[ $issues_count -eq 0 ]]; then
        validation_status="PASSED"
        log_success "런북 시스템 검증 통과"
    else
        validation_status="FAILED"
        log_warning "런북 시스템 검증에서 $issues_count 개의 문제를 발견했습니다"
    fi

    # 결과를 전역 변수에 저장
    VALIDATION_RESULTS=$(cat << EOF
{
    "validation_status": "$validation_status",
    "timestamp": "$(date -Iseconds)",
    "summary": {
        "total_runbook_templates": $total_runbook_templates,
        "total_error_mappings": $total_error_mappings,
        "total_hook_files": $total_hook_files,
        "issues_found": $issues_count
    },
    "runbook_templates": $runbook_templates,
    "error_mappings": $error_mappings,
    "hook_files": $hook_files,
    "hook_error_mappings": $hook_error_mappings,
    "runbook_categories": $runbook_categories,
    "validation_results": {
        "mapped_error_types": $mapped_error_types,
        "unmapped_error_types": $unmapped_error_types,
        "missing_hooks": $missing_hooks,
        "orphaned_hooks": $orphaned_hooks,
        "duplicate_mappings": $duplicate_mappings,
        "permission_issues": $permission_issues
    },
    "statistics": {
        "category_distribution": $category_count,
        "severity_distribution": $severity_count
    }
}
EOF
    )

    return 0
}

# 텍스트 형식 출력 함수
output_text_format() {
    local validation_status
    validation_status=$(echo "$VALIDATION_RESULTS" | jq -r '.validation_status')

    cat << EOF

${WHITE}📚 런북 시스템 검증 결과${NC}
${CYAN}═══════════════════════════════════════════════════════════════${NC}

EOF

    # 검증 상태에 따른 헤더 색상
    if [[ "$validation_status" == "PASSED" ]]; then
        echo -e "${GREEN}🟢 검증 상태: 통과${NC}"
    else
        echo -e "${RED}🔴 검증 상태: 실패${NC}"
    fi

    cat << EOF

${YELLOW}📊 검증 요약${NC}
  • 런북 템플릿 수    : $(echo "$VALIDATION_RESULTS" | jq -r '.summary.total_runbook_templates')개
  • 에러 매핑 수      : $(echo "$VALIDATION_RESULTS" | jq -r '.summary.total_error_mappings')개
  • 훅 파일 수        : $(echo "$VALIDATION_RESULTS" | jq -r '.summary.total_hook_files')개
  • 발견된 문제 수    : $(echo "$VALIDATION_RESULTS" | jq -r '.summary.issues_found')개

EOF

    # 문제 상세 내용 출력
    local unmapped_count
    local missing_hooks_count
    local duplicate_count
    local permission_count

    unmapped_count=$(echo "$VALIDATION_RESULTS" | jq '.validation_results.unmapped_error_types | length')
    missing_hooks_count=$(echo "$VALIDATION_RESULTS" | jq '.validation_results.missing_hooks | length')
    duplicate_count=$(echo "$VALIDATION_RESULTS" | jq '.validation_results.duplicate_mappings | length')
    permission_count=$(echo "$VALIDATION_RESULTS" | jq '.validation_results.permission_issues | length')

    if [[ $unmapped_count -gt 0 ]]; then
        echo -e "${RED}❌ 매핑되지 않은 에러 타입 ($unmapped_count 개):${NC}"
        echo "$VALIDATION_RESULTS" | jq -r '.validation_results.unmapped_error_types[]' | sed 's/^/  • /'
        echo
    fi

    if [[ $missing_hooks_count -gt 0 ]]; then
        echo -e "${RED}❌ 존재하지 않는 훅 파일 ($missing_hooks_count 개):${NC}"
        echo "$VALIDATION_RESULTS" | jq -r '.validation_results.missing_hooks[]' | sed 's/^/  • /'
        echo
    fi

    if [[ $duplicate_count -gt 0 ]]; then
        echo -e "${YELLOW}⚠️ 중복 매핑된 에러 타입 ($duplicate_count 개):${NC}"
        echo "$VALIDATION_RESULTS" | jq -r '.validation_results.duplicate_mappings[]' | sed 's/^/  • /'
        echo
    fi

    if [[ $permission_count -gt 0 ]]; then
        echo -e "${YELLOW}⚠️ 실행 권한 문제 ($permission_count 개):${NC}"
        echo "$VALIDATION_RESULTS" | jq -r '.validation_results.permission_issues[]' | sed 's/^/  • /'
        echo
    fi

    # 고아 훅 파일 (경고 수준)
    local orphaned_count
    orphaned_count=$(echo "$VALIDATION_RESULTS" | jq '.validation_results.orphaned_hooks | length')
    if [[ $orphaned_count -gt 0 ]]; then
        echo -e "${CYAN}ℹ️ 사용되지 않는 훅 파일 ($orphaned_count 개):${NC}"
        echo "$VALIDATION_RESULTS" | jq -r '.validation_results.orphaned_hooks[]' | sed 's/^/  • /'
        echo
    fi

    # 통계 정보
    echo -e "${YELLOW}📈 카테고리 분포${NC}"
    echo "$VALIDATION_RESULTS" | jq -r '.statistics.category_distribution[] | "  • \(.category): \(.count)개"'
    echo

    echo -e "${YELLOW}📈 심각도 분포${NC}"
    echo "$VALIDATION_RESULTS" | jq -r '.statistics.severity_distribution[] | "  • \(.severity): \(.count)개"'
    echo

    # 권장사항
    echo -e "${YELLOW}💡 권장사항${NC}"
    if [[ $unmapped_count -gt 0 ]]; then
        echo "  🔧 매핑되지 않은 에러 타입에 대한 훅을 추가하거나 기존 훅에 매핑을 추가하세요."
    fi
    if [[ $missing_hooks_count -gt 0 ]]; then
        echo "  📝 참조된 훅 파일을 생성하거나 올바른 파일명으로 수정하세요."
    fi
    if [[ $duplicate_count -gt 0 ]]; then
        echo "  🔍 중복 매핑을 정리하여 일관성을 확보하세요."
    fi
    if [[ $permission_count -gt 0 ]]; then
        echo "  🔐 스크립트 파일에 실행 권한을 추가하세요: chmod +x [파일명]"
    fi
    if [[ $orphaned_count -gt 0 ]]; then
        echo "  🧹 사용되지 않는 훅 파일을 정리하거나 매핑에 추가하는 것을 고려하세요."
    fi
    if [[ "$validation_status" == "PASSED" ]]; then
        echo "  ✅ 런북 시스템이 올바르게 구성되어 있습니다."
    fi

    echo
    echo "${CYAN}생성 시간: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
    echo "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
}

# JSON 형식 출력 함수
output_json_format() {
    echo "$VALIDATION_RESULTS" | jq .
}

# 결과 출력 함수
output_results() {
    local output_content=""

    case "$OUTPUT_FORMAT" in
        "json")
            output_content=$(output_json_format)
            ;;
        *)
            output_content=$(output_text_format)
            ;;
    esac

    # 파일 출력 또는 콘솔 출력
    if [[ -n "$OUTPUT_FILE" ]]; then
        echo "$output_content" > "$OUTPUT_FILE"
        log_success "검증 결과가 파일에 저장되었습니다: $OUTPUT_FILE"
    else
        echo "$output_content"
    fi
}

# 메인 함수
main() {
    log_debug "런북 시스템 검증 도구 시작"

    # 매개변수 파싱
    while [[ $# -gt 0 ]]; do
        case $1 in
            --json)
                OUTPUT_FORMAT="json"
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
    if ! command -v python3 &> /dev/null; then
        log_error "Python3이 필요합니다. 설치 후 다시 시도하세요."
        exit 1
    fi

    if ! command -v jq &> /dev/null; then
        log_error "jq 명령어가 필요합니다. 설치 후 다시 시도하세요."
        exit 1
    fi

    # 작업 디렉토리 확인 (프로젝트 루트인지 확인)
    if [[ ! -f "mcp/run.py" ]] || [[ ! -d "scripts" ]]; then
        log_error "프로젝트 루트 디렉토리에서 실행해주세요."
        exit 1
    fi

    # 검증 실행
    if ! run_validation; then
        log_error "런북 시스템 검증이 실패했습니다."
        exit 1
    fi

    # 결과 출력
    output_results

    # 검증 상태에 따른 종료 코드
    local validation_status
    validation_status=$(echo "$VALIDATION_RESULTS" | jq -r '.validation_status')

    if [[ "$validation_status" == "PASSED" ]]; then
        log_success "런북 시스템 검증이 성공적으로 완료되었습니다."
        exit 0
    else
        log_error "런북 시스템 검증에서 문제가 발견되었습니다."
        exit 1
    fi
}

# 스크립트 실행
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi