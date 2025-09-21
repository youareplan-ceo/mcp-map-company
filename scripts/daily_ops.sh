#!/bin/bash

# 🔄 일일 운영 자동화 스크립트 (한국어 주석 포함)
# 목적: 매일 실행되는 보안 로그 회전, 백업 검증, 정리 작업 자동화
# 실행 순서:
#   1. 보안 로그 회전 및 압축 (logs/security.log)
#   2. backup_verifier.sh 실행 → 백업 무결성 검증
#   3. cleanup_old_backups.sh 실행 → 오래된 백업 정리
#   4. 결과 요약을 logs/daily_ops.log에 저장

set -euo pipefail

# 🔧 설정 변수
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOGS_DIR="$PROJECT_ROOT/logs"
DAILY_LOG="$LOGS_DIR/daily_ops.log"
SECURITY_LOG="$LOGS_DIR/security.log"

# 🎛️ 옵션 플래그
DRY_RUN=false
JSON_OUTPUT=false
VERBOSE=false
HELP=false

# 📝 사용법 출력
show_usage() {
    cat << EOF
🔄 일일 운영 자동화 스크립트

사용법: $0 [옵션]

옵션:
  --dry-run        시뮬레이션 모드 (실제 변경 없음)
  --json          JSON 형식으로 결과 출력
  --verbose       상세 출력 모드
  --help          이 도움말 출력

예시:
  $0                    # 일반 실행
  $0 --dry-run         # 시뮬레이션 모드
  $0 --json --verbose  # JSON 출력 + 상세 모드

실행 내용:
  1. 보안 로그 회전 및 압축
  2. 백업 무결성 검증
  3. 오래된 백업 정리
  4. 결과 로그 저장
EOF
}

# 🎯 명령행 인수 파싱
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --json)
                JSON_OUTPUT=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help)
                HELP=true
                shift
                ;;
            *)
                echo "❌ 알 수 없는 옵션: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# 📊 로그 출력 함수
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    if [[ "$VERBOSE" == "true" ]]; then
        echo "[$timestamp] $level: $message"
    fi

    # daily_ops.log에 기록
    echo "[$timestamp] $level: $message" >> "$DAILY_LOG"
}

# 🔄 보안 로그 회전 함수
rotate_security_logs() {
    log_message "INFO" "보안 로그 회전 시작"

    if [[ ! -f "$SECURITY_LOG" ]]; then
        log_message "WARNING" "보안 로그 파일이 존재하지 않음: $SECURITY_LOG"
        return 0
    fi

    local file_size=$(stat -f%z "$SECURITY_LOG" 2>/dev/null || echo "0")
    local date_suffix=$(date '+%Y%m%d')
    local archived_log="$SECURITY_LOG.$date_suffix.gz"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_message "INFO" "[시뮬레이션] 보안 로그 압축: $SECURITY_LOG → $archived_log (크기: ${file_size}B)"
        return 0
    fi

    # 로그 압축 및 회전
    if gzip -c "$SECURITY_LOG" > "$archived_log"; then
        > "$SECURITY_LOG"  # 원본 파일 비우기
        log_message "INFO" "보안 로그 회전 완료: $archived_log (크기: ${file_size}B)"
    else
        log_message "ERROR" "보안 로그 회전 실패"
        return 1
    fi
}

# 🔍 백업 검증 함수
verify_backups() {
    log_message "INFO" "백업 무결성 검증 시작"

    local backup_script="$SCRIPT_DIR/backup_verifier.sh"

    if [[ ! -f "$backup_script" ]]; then
        log_message "WARNING" "백업 검증 스크립트를 찾을 수 없음: $backup_script"
        return 0
    fi

    local cmd_args=""
    if [[ "$DRY_RUN" == "true" ]]; then
        cmd_args="--dry-run"
    fi

    if [[ "$JSON_OUTPUT" == "true" ]]; then
        cmd_args="$cmd_args --json"
    fi

    if chmod +x "$backup_script" && "$backup_script" $cmd_args > /tmp/backup_verify.log 2>&1; then
        log_message "INFO" "백업 검증 완료"
        if [[ "$VERBOSE" == "true" ]]; then
            cat /tmp/backup_verify.log
        fi
    else
        log_message "ERROR" "백업 검증 실패"
        cat /tmp/backup_verify.log >> "$DAILY_LOG"
        return 1
    fi
}

# 🧹 백업 정리 함수
cleanup_old_backups() {
    log_message "INFO" "오래된 백업 정리 시작"

    local cleanup_script="$SCRIPT_DIR/cleanup_old_backups.sh"

    if [[ ! -f "$cleanup_script" ]]; then
        log_message "WARNING" "백업 정리 스크립트를 찾을 수 없음: $cleanup_script"
        return 0
    fi

    local cmd_args=""
    if [[ "$DRY_RUN" == "true" ]]; then
        cmd_args="--dry-run"
    fi

    if chmod +x "$cleanup_script" && "$cleanup_script" $cmd_args > /tmp/backup_cleanup.log 2>&1; then
        log_message "INFO" "백업 정리 완료"
        if [[ "$VERBOSE" == "true" ]]; then
            cat /tmp/backup_cleanup.log
        fi
    else
        log_message "ERROR" "백업 정리 실패"
        cat /tmp/backup_cleanup.log >> "$DAILY_LOG"
        return 1
    fi
}

# 📊 결과 요약 출력
output_summary() {
    local end_time=$(date '+%Y-%m-%d %H:%M:%S')
    local duration=$(($(date +%s) - start_timestamp))

    if [[ "$JSON_OUTPUT" == "true" ]]; then
        cat << EOF
{
  "timestamp": "$end_time",
  "duration_seconds": $duration,
  "dry_run": $DRY_RUN,
  "tasks_completed": [
    "security_log_rotation",
    "backup_verification",
    "backup_cleanup"
  ],
  "log_file": "$DAILY_LOG",
  "status": "completed"
}
EOF
    else
        echo ""
        echo "🎉 일일 운영 작업 완료"
        echo "   완료 시간: $end_time"
        echo "   소요 시간: ${duration}초"
        echo "   로그 파일: $DAILY_LOG"
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "   모드: 시뮬레이션 (실제 변경 없음)"
        fi
        echo ""
    fi
}

# 🚀 메인 실행 함수
main() {
    local start_timestamp=$(date +%s)

    # 명령행 인수 파싱
    parse_args "$@"

    if [[ "$HELP" == "true" ]]; then
        show_usage
        exit 0
    fi

    # 로그 디렉토리 생성
    mkdir -p "$LOGS_DIR"

    # 일일 작업 시작 로그
    log_message "INFO" "일일 운영 작업 시작 (모드: $([ "$DRY_RUN" == "true" ] && echo "시뮬레이션" || echo "실제"))"

    # 작업 실행
    rotate_security_logs
    verify_backups
    cleanup_old_backups

    # 결과 요약 출력
    output_summary

    log_message "INFO" "일일 운영 작업 완료"
}

# 스크립트 실행
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi