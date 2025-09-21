#!/bin/bash
# 🧹 MCP-MAP CI 클린업 자동화 스크립트 (한국어 주석 포함)
# 기능:
# 1. logs/ 하위 로그 파일 압축 (security.log, api.log, scheduler.log)
# 2. 30일 이상 된 reports/ 파일 자동 삭제
# 3. backups/ 디렉토리 무결성 검증 후 요약 출력
# 4. --dry-run, --verbose 모드 지원
# 5. JSON 출력 옵션으로 자동화 파이프라인 연동

set -e  # 에러 발생 시 스크립트 중단

# 🔧 기본 설정
LOGS_DIR="logs"
REPORTS_DIR="reports"
BACKUPS_DIR="backups"
CLEANUP_DAYS=30
DRY_RUN=false
VERBOSE=false
JSON_OUTPUT=false
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
DATE_SUFFIX=$(date '+%Y%m%d_%H%M%S')

# 🎨 색상 코드 (터미널 출력용)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 📊 클린업 통계
COMPRESSED_COUNT=0
DELETED_COUNT=0
TOTAL_SAVED_BYTES=0
BACKUP_FILES_COUNT=0

# 📝 사용법 출력
usage() {
    echo "🧹 MCP-MAP CI 클린업 자동화 스크립트"
    echo "사용법: $0 [옵션]"
    echo ""
    echo "옵션:"
    echo "  --dry-run           시뮬레이션 모드 (실제 변경 없음)"
    echo "  --verbose           상세 출력 모드"
    echo "  --json              JSON 형식 출력"
    echo "  --days DAYS         보관 기간 설정 (기본값: 30일)"
    echo "  --help              이 도움말 표시"
    echo ""
    echo "예시:"
    echo "  $0 --dry-run --verbose"
    echo "  $0 --json --days 7"
    echo "  $0 --verbose"
}

# 📊 인수 파싱
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN=true ;;
        --verbose) VERBOSE=true ;;
        --json) JSON_OUTPUT=true ;;
        --days) CLEANUP_DAYS="$2"; shift ;;
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
    if [ "$VERBOSE" = true ] || [ "$DRY_RUN" = true ]; then
        echo -e "${GREEN}✅ $1${NC}"
    fi
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 📦 로그 파일 압축 함수
compress_log_files() {
    log_info "로그 파일 압축 작업 시작..."

    # 디렉토리 존재 확인
    if [ ! -d "$LOGS_DIR" ]; then
        log_warning "로그 디렉토리를 찾을 수 없음: $LOGS_DIR"
        return
    fi

    # 압축할 로그 파일 목록
    local log_files=("security.log" "api.log" "scheduler.log" "app.log" "error.log")

    for log_file in "${log_files[@]}"; do
        local log_path="$LOGS_DIR/$log_file"

        if [ -f "$log_path" ]; then
            # 파일 크기 확인 (1MB 이상인 경우만 압축)
            local file_size=$(stat -f%z "$log_path" 2>/dev/null || echo 0)

            if [ "$file_size" -gt 1048576 ]; then  # 1MB = 1048576 bytes
                local compressed_file="$LOGS_DIR/${log_file}_${DATE_SUFFIX}.gz"

                if [ "$DRY_RUN" = true ]; then
                    log_success "시뮬레이션: $log_file 압축 → ${log_file}_${DATE_SUFFIX}.gz"
                else
                    # 로그 파일 압축
                    gzip -c "$log_path" > "$compressed_file"
                    # 원본 파일을 비움 (실행 중인 프로세스를 위해)
                    > "$log_path"
                    log_success "$log_file 압축 완료 → ${log_file}_${DATE_SUFFIX}.gz"
                fi

                COMPRESSED_COUNT=$((COMPRESSED_COUNT + 1))
                TOTAL_SAVED_BYTES=$((TOTAL_SAVED_BYTES + file_size - file_size/4))  # 압축률 75% 가정
            else
                log_info "$log_file: 크기가 작아 압축 생략 (${file_size} bytes)"
            fi
        else
            log_info "$log_file: 파일이 존재하지 않아 생략"
        fi
    done
}

# 🗑️ 오래된 리포트 파일 삭제 함수
cleanup_old_reports() {
    log_info "오래된 리포트 파일 정리 작업 시작..."

    # 디렉토리 존재 확인
    if [ ! -d "$REPORTS_DIR" ]; then
        log_warning "리포트 디렉토리를 찾을 수 없음: $REPORTS_DIR"
        return
    fi

    # 30일 이상 된 파일 찾기
    local old_files=$(find "$REPORTS_DIR" -type f -mtime +$CLEANUP_DAYS 2>/dev/null || true)

    if [ -n "$old_files" ]; then
        while IFS= read -r file; do
            if [ -f "$file" ]; then
                local file_size=$(stat -f%z "$file" 2>/dev/null || echo 0)

                if [ "$DRY_RUN" = true ]; then
                    log_success "시뮬레이션: $file 삭제 예정 (${file_size} bytes)"
                else
                    rm -f "$file"
                    log_success "$file 삭제 완료 (${file_size} bytes)"
                fi

                DELETED_COUNT=$((DELETED_COUNT + 1))
                TOTAL_SAVED_BYTES=$((TOTAL_SAVED_BYTES + file_size))
            fi
        done <<< "$old_files"
    else
        log_info "삭제할 오래된 리포트 파일이 없습니다"
    fi
}

# 🔍 백업 디렉토리 무결성 검증 함수
verify_backup_integrity() {
    log_info "백업 디렉토리 무결성 검증 시작..."

    # 디렉토리 존재 확인
    if [ ! -d "$BACKUPS_DIR" ]; then
        log_warning "백업 디렉토리를 찾을 수 없음: $BACKUPS_DIR"
        return
    fi

    # 백업 파일 수 계산
    BACKUP_FILES_COUNT=$(find "$BACKUPS_DIR" -type f 2>/dev/null | wc -l)

    if [ "$BACKUP_FILES_COUNT" -eq 0 ]; then
        log_warning "백업 디렉토리에 파일이 없습니다"
        return
    fi

    # 최신 백업 파일 확인
    local latest_backup=$(ls -t "$BACKUPS_DIR" 2>/dev/null | head -n 1)

    if [ -n "$latest_backup" ]; then
        local latest_path="$BACKUPS_DIR/$latest_backup"
        local latest_size=$(stat -f%z "$latest_path" 2>/dev/null || echo 0)
        local latest_date=$(stat -f"%Sm" -t "%Y-%m-%d %H:%M:%S" "$latest_path" 2>/dev/null || echo "알 수 없음")

        log_success "최신 백업: $latest_backup (${latest_size} bytes, $latest_date)"

        # 백업 파일 크기 검증 (최소 크기 확인)
        if [ "$latest_size" -lt 1024 ]; then  # 1KB 미만
            log_warning "최신 백업 파일이 너무 작습니다 (${latest_size} bytes)"
        fi

        # 24시간 이내 백업 확인
        local current_time=$(date +%s)
        local file_time=$(stat -f%m "$latest_path" 2>/dev/null || echo 0)
        local time_diff=$((current_time - file_time))

        if [ "$time_diff" -gt 86400 ]; then  # 24시간 = 86400초
            log_warning "최신 백업이 24시간 이전입니다"
        fi
    fi
}

# 📊 JSON 출력 생성 함수
generate_json_output() {
    local json_output="{
        \"timestamp\": \"$TIMESTAMP\",
        \"dry_run\": $DRY_RUN,
        \"cleanup_results\": {
            \"compressed_logs\": $COMPRESSED_COUNT,
            \"deleted_reports\": $DELETED_COUNT,
            \"total_saved_bytes\": $TOTAL_SAVED_BYTES,
            \"backup_files_count\": $BACKUP_FILES_COUNT
        },
        \"directories\": {
            \"logs_dir\": \"$LOGS_DIR\",
            \"reports_dir\": \"$REPORTS_DIR\",
            \"backups_dir\": \"$BACKUPS_DIR\"
        },
        \"settings\": {
            \"cleanup_days\": $CLEANUP_DAYS,
            \"verbose\": $VERBOSE
        }
    }"

    echo "$json_output"
}

# 📋 텍스트 요약 출력 함수
generate_text_summary() {
    echo "🧹 CI 클린업 실행 요약"
    echo "======================"
    echo ""
    echo "⏰ 실행 시간: $TIMESTAMP"
    echo "🔧 실행 모드: $([ "$DRY_RUN" = true ] && echo "시뮬레이션" || echo "실제 실행")"
    echo ""
    echo "📊 클린업 결과:"
    echo "  📦 압축된 로그: ${COMPRESSED_COUNT}개"
    echo "  🗑️ 삭제된 리포트: ${DELETED_COUNT}개"
    echo "  💾 절약된 용량: $((TOTAL_SAVED_BYTES / 1024)) KB"
    echo "  📁 백업 파일: ${BACKUP_FILES_COUNT}개"
    echo ""
    echo "📁 대상 디렉토리:"
    echo "  • 로그: $LOGS_DIR"
    echo "  • 리포트: $REPORTS_DIR"
    echo "  • 백업: $BACKUPS_DIR"
    echo ""
    echo "⚙️ 설정:"
    echo "  • 보관 기간: ${CLEANUP_DAYS}일"
    echo "  • 상세 출력: $([ "$VERBOSE" = true ] && echo "활성화" || echo "비활성화")"
}

# 🚀 메인 실행 함수
main() {
    if [ "$JSON_OUTPUT" = false ]; then
        echo -e "${CYAN}🧹 MCP-MAP CI 클린업 자동화 시작${NC}"
        echo "⏰ 실행 시간: $TIMESTAMP"
        echo "🔧 모드: $([ "$DRY_RUN" = true ] && echo "시뮬레이션" || echo "실제 실행")"
        echo ""
    fi

    # 디렉토리 생성 (존재하지 않는 경우)
    mkdir -p "$LOGS_DIR" "$REPORTS_DIR" "$BACKUPS_DIR"

    # 1. 로그 파일 압축
    compress_log_files

    # 2. 오래된 리포트 파일 삭제
    cleanup_old_reports

    # 3. 백업 무결성 검증
    verify_backup_integrity

    # 결과 출력
    if [ "$JSON_OUTPUT" = true ]; then
        generate_json_output
    else
        echo ""
        generate_text_summary
        echo ""
        echo -e "${GREEN}🎉 CI 클린업 완료!${NC}"
    fi
}

# 🔥 트랩 설정 (에러 발생 시 정리)
trap 'echo -e "${RED}❌ 스크립트 실행 중 오류 발생${NC}"; exit 1' ERR

# 실행
main