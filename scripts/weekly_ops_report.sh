#!/bin/bash

# 📊 주간 운영 리포트 자동화 스크립트 (한국어 주석 포함)
# 목적: 보안 로그 및 백업 로그를 분석하여 주간 운영 현황 리포트 생성
# 실행 내용:
#   1. 지난 7일간 보안 이벤트 분석 (차단된 IP, Rate Limit 위반)
#   2. 백업 성공/실패 통계 집계
#   3. Markdown 형식 리포트 생성 (reports/weekly/YYYY-MM-DD.md)
#   4. JSON 형식 출력 지원
#   5. 알림 시스템 연동 데이터 준비

set -euo pipefail

# 🔧 설정 변수
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOGS_DIR="$PROJECT_ROOT/logs"
REPORTS_DIR="$PROJECT_ROOT/reports/weekly"
SECURITY_LOG="$LOGS_DIR/security.log"
DAILY_OPS_LOG="$LOGS_DIR/daily_ops.log"

# 📅 날짜 설정 (지난 7일)
END_DATE=$(date '+%Y-%m-%d')
START_DATE=$(date -d '7 days ago' '+%Y-%m-%d')
REPORT_FILE="$REPORTS_DIR/weekly-report-$END_DATE.md"
JSON_FILE="$REPORTS_DIR/weekly-report-$END_DATE.json"

# 🎛️ 옵션 플래그
DRY_RUN=false
JSON_OUTPUT=false
VERBOSE=false
HELP=false

# 📝 사용법 출력
show_usage() {
    cat << EOF
📊 주간 운영 리포트 자동화 스크립트

사용법: $0 [옵션]

옵션:
  --dry-run        시뮬레이션 모드 (파일 생성 없음)
  --json          JSON 형식으로 결과 출력
  --verbose       상세 출력 모드
  --help          이 도움말 출력

실행 내용:
  1. 지난 7일간 보안 이벤트 분석
  2. 백업 성공/실패 통계 집계
  3. Markdown 리포트 생성
  4. 주요 지표 요약

출력 파일:
  - $REPORT_FILE
  - $JSON_FILE (--json 사용 시)

예시:
  $0                    # 기본 실행
  $0 --verbose         # 상세 출력
  $0 --json --dry-run  # JSON + 시뮬레이션
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
}

# 🔍 보안 로그 분석 함수
analyze_security_logs() {
    log_message "INFO" "보안 로그 분석 시작 ($START_DATE ~ $END_DATE)"

    # 로그 파일 존재 확인
    if [[ ! -f "$SECURITY_LOG" ]]; then
        log_message "WARNING" "보안 로그 파일을 찾을 수 없음: $SECURITY_LOG"
        echo "0,0,0,0"  # blocked_ips, rate_violations, whitelist_adds, monitoring_events
        return 0
    fi

    # 지난 7일간 로그 필터링 및 분석
    local blocked_ips=0
    local rate_violations=0
    local whitelist_adds=0
    local monitoring_events=0

    # 압축된 로그 파일들도 포함하여 분석
    local log_files=("$SECURITY_LOG")
    for i in {1..7}; do
        local date_suffix=$(date -d "$i days ago" '+%Y%m%d')
        local archived_log="$SECURITY_LOG.$date_suffix.gz"
        if [[ -f "$archived_log" ]]; then
            log_files+=("$archived_log")
        fi
    done

    # 각 로그 파일 분석
    for log_file in "${log_files[@]}"; do
        if [[ ! -f "$log_file" ]]; then
            continue
        fi

        local content
        if [[ "$log_file" == *.gz ]]; then
            content=$(gunzip -c "$log_file" 2>/dev/null || echo "")
        else
            content=$(cat "$log_file" 2>/dev/null || echo "")
        fi

        # 이벤트 타입별 집계
        blocked_ips=$((blocked_ips + $(echo "$content" | grep -c "BLOCKED_IP" || true)))
        rate_violations=$((rate_violations + $(echo "$content" | grep -c "RATE_LIMIT" || true)))
        whitelist_adds=$((whitelist_adds + $(echo "$content" | grep -c "WHITELIST_ADD" || true)))
        monitoring_events=$((monitoring_events + $(echo "$content" | grep -c "MONITOR" || true)))
    done

    log_message "INFO" "보안 이벤트 집계 완료 - 차단IP: $blocked_ips, 위반: $rate_violations, 화이트리스트: $whitelist_adds, 모니터링: $monitoring_events"
    echo "$blocked_ips,$rate_violations,$whitelist_adds,$monitoring_events"
}

# 📦 백업 로그 분석 함수
analyze_backup_logs() {
    log_message "INFO" "백업 로그 분석 시작"

    # daily_ops.log 파일 확인
    if [[ ! -f "$DAILY_OPS_LOG" ]]; then
        log_message "WARNING" "일일 운영 로그 파일을 찾을 수 없음: $DAILY_OPS_LOG"
        echo "0,0,0"  # backup_success, backup_failures, cleanup_runs
        return 0
    fi

    # 지난 7일간 백업 관련 이벤트 분석
    local backup_success=0
    local backup_failures=0
    local cleanup_runs=0

    # 날짜 범위에 해당하는 로그 엔트리 필터링
    local filtered_logs
    filtered_logs=$(awk -v start="$START_DATE" -v end="$END_DATE" '
        $1 >= start && $1 <= end
    ' "$DAILY_OPS_LOG" 2>/dev/null || echo "")

    # 백업 관련 이벤트 집계
    backup_success=$(echo "$filtered_logs" | grep -c "백업 검증 완료" || true)
    backup_failures=$(echo "$filtered_logs" | grep -c "백업 검증 실패" || true)
    cleanup_runs=$(echo "$filtered_logs" | grep -c "백업 정리 완료" || true)

    log_message "INFO" "백업 이벤트 집계 완료 - 성공: $backup_success, 실패: $backup_failures, 정리: $cleanup_runs"
    echo "$backup_success,$backup_failures,$cleanup_runs"
}

# 📈 시스템 통계 수집 함수
collect_system_stats() {
    log_message "INFO" "시스템 통계 수집 시작"

    # 디스크 사용량
    local disk_usage
    disk_usage=$(df -h . | tail -1 | awk '{print $5}' | sed 's/%//')

    # 로그 파일 크기
    local security_log_size=0
    if [[ -f "$SECURITY_LOG" ]]; then
        security_log_size=$(stat -f%z "$SECURITY_LOG" 2>/dev/null || echo "0")
    fi

    # 백업 디렉토리 크기
    local backup_dir_size=0
    if [[ -d "$PROJECT_ROOT/backups" ]]; then
        backup_dir_size=$(du -sk "$PROJECT_ROOT/backups" 2>/dev/null | awk '{print $1}' || echo "0")
    fi

    log_message "INFO" "시스템 통계 수집 완료 - 디스크: ${disk_usage}%, 보안로그: ${security_log_size}B, 백업: ${backup_dir_size}KB"
    echo "$disk_usage,$security_log_size,$backup_dir_size"
}

# 📄 Markdown 리포트 생성 함수
generate_markdown_report() {
    local security_stats="$1"
    local backup_stats="$2"
    local system_stats="$3"

    # 통계 파싱
    IFS=',' read -r blocked_ips rate_violations whitelist_adds monitoring_events <<< "$security_stats"
    IFS=',' read -r backup_success backup_failures cleanup_runs <<< "$backup_stats"
    IFS=',' read -r disk_usage security_log_size backup_dir_size <<< "$system_stats"

    # 백업 성공률 계산
    local total_backups=$((backup_success + backup_failures))
    local success_rate=0
    if [[ $total_backups -gt 0 ]]; then
        success_rate=$((backup_success * 100 / total_backups))
    fi

    # Markdown 리포트 생성
    cat > "$REPORT_FILE" << EOF
# 📊 주간 운영 리포트

**보고 기간**: $START_DATE ~ $END_DATE
**생성 일시**: $(date '+%Y-%m-%d %H:%M:%S')

## 🛡️ 보안 현황

### 보안 이벤트 요약
- 🚫 **차단된 IP**: $blocked_ips 건
- ⚠️ **Rate Limit 위반**: $rate_violations 건
- ✅ **화이트리스트 추가**: $whitelist_adds 건
- 👀 **모니터링 이벤트**: $monitoring_events 건

### 보안 상태 평가
$(if [[ $blocked_ips -lt 10 ]]; then
    echo "✅ **양호**: 차단된 IP 수가 정상 범위입니다."
elif [[ $blocked_ips -lt 50 ]]; then
    echo "⚠️ **주의**: 차단된 IP 수가 증가했습니다. 모니터링을 강화하세요."
else
    echo "🚨 **위험**: 차단된 IP 수가 많습니다. 즉시 보안 점검이 필요합니다."
fi)

## 📦 백업 현황

### 백업 통계
- ✅ **성공한 백업**: $backup_success 회
- ❌ **실패한 백업**: $backup_failures 회
- 🧹 **정리 작업**: $cleanup_runs 회
- 📊 **성공률**: ${success_rate}%

### 백업 상태 평가
$(if [[ $success_rate -ge 95 ]]; then
    echo "✅ **우수**: 백업 성공률이 매우 높습니다."
elif [[ $success_rate -ge 80 ]]; then
    echo "⚠️ **양호**: 백업 성공률이 양호합니다."
else
    echo "🚨 **개선필요**: 백업 시스템 점검이 필요합니다."
fi)

## 💾 시스템 리소스

### 리소스 사용량
- 💽 **디스크 사용률**: ${disk_usage}%
- 📝 **보안 로그 크기**: $(numfmt --to=iec $security_log_size)
- 📦 **백업 디렉토리**: $(numfmt --to=iec $((backup_dir_size * 1024)))

### 권장 사항
$(if [[ $disk_usage -gt 90 ]]; then
    echo "🚨 **긴급**: 디스크 사용률이 90% 이상입니다. 즉시 정리가 필요합니다."
elif [[ $disk_usage -gt 80 ]]; then
    echo "⚠️ **주의**: 디스크 사용률이 높습니다. 정리 작업을 계획하세요."
else
    echo "✅ **정상**: 디스크 사용률이 안정적입니다."
fi)

## 📋 주간 활동 요약

### 주요 성과
- 📊 총 $((monitoring_events + backup_success + cleanup_runs))회의 자동화 작업 수행
- 🛡️ $blocked_ips개의 위험 IP 차단으로 보안 강화
- 📦 $backup_success회의 성공적인 백업으로 데이터 보호

### 다음 주 계획
- 🔍 보안 패턴 분석 및 화이트리스트 최적화
- 📦 백업 정책 검토 및 저장 공간 최적화
- 🔄 자동화 스크립트 성능 개선

---

*이 리포트는 자동 생성되었습니다. 문의사항은 시스템 관리팀에게 연락하세요.*
EOF

    log_message "INFO" "Markdown 리포트 생성 완료: $REPORT_FILE"
}

# 📊 JSON 리포트 생성 함수
generate_json_report() {
    local security_stats="$1"
    local backup_stats="$2"
    local system_stats="$3"

    # 통계 파싱
    IFS=',' read -r blocked_ips rate_violations whitelist_adds monitoring_events <<< "$security_stats"
    IFS=',' read -r backup_success backup_failures cleanup_runs <<< "$backup_stats"
    IFS=',' read -r disk_usage security_log_size backup_dir_size <<< "$system_stats"

    # 백업 성공률 계산
    local total_backups=$((backup_success + backup_failures))
    local success_rate=0
    if [[ $total_backups -gt 0 ]]; then
        success_rate=$((backup_success * 100 / total_backups))
    fi

    # JSON 리포트 생성
    cat > "$JSON_FILE" << EOF
{
  "report_metadata": {
    "period_start": "$START_DATE",
    "period_end": "$END_DATE",
    "generated_at": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')",
    "report_type": "weekly_operations"
  },
  "security_events": {
    "blocked_ips": $blocked_ips,
    "rate_limit_violations": $rate_violations,
    "whitelist_additions": $whitelist_adds,
    "monitoring_events": $monitoring_events,
    "total_security_events": $((blocked_ips + rate_violations + whitelist_adds + monitoring_events))
  },
  "backup_operations": {
    "successful_backups": $backup_success,
    "failed_backups": $backup_failures,
    "cleanup_operations": $cleanup_runs,
    "success_rate_percent": $success_rate,
    "total_backup_operations": $total_backups
  },
  "system_resources": {
    "disk_usage_percent": $disk_usage,
    "security_log_size_bytes": $security_log_size,
    "backup_directory_size_kb": $backup_dir_size
  },
  "status_summary": {
    "security_status": "$(if [[ $blocked_ips -lt 10 ]]; then echo "good"; elif [[ $blocked_ips -lt 50 ]]; then echo "warning"; else echo "critical"; fi)",
    "backup_status": "$(if [[ $success_rate -ge 95 ]]; then echo "excellent"; elif [[ $success_rate -ge 80 ]]; then echo "good"; else echo "needs_improvement"; fi)",
    "disk_status": "$(if [[ $disk_usage -gt 90 ]]; then echo "critical"; elif [[ $disk_usage -gt 80 ]]; then echo "warning"; else echo "normal"; fi)"
  }
}
EOF

    log_message "INFO" "JSON 리포트 생성 완료: $JSON_FILE"
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

    # 리포트 디렉토리 생성
    mkdir -p "$REPORTS_DIR"

    log_message "INFO" "주간 운영 리포트 생성 시작 ($START_DATE ~ $END_DATE)"

    # 데이터 수집
    local security_stats
    local backup_stats
    local system_stats

    security_stats=$(analyze_security_logs)
    backup_stats=$(analyze_backup_logs)
    system_stats=$(collect_system_stats)

    if [[ "$DRY_RUN" == "true" ]]; then
        log_message "INFO" "[시뮬레이션] 리포트 생성 건너뜀"
        if [[ "$VERBOSE" == "true" ]]; then
            echo "보안 통계: $security_stats"
            echo "백업 통계: $backup_stats"
            echo "시스템 통계: $system_stats"
        fi
    else
        # 리포트 생성
        generate_markdown_report "$security_stats" "$backup_stats" "$system_stats"

        if [[ "$JSON_OUTPUT" == "true" ]]; then
            generate_json_report "$security_stats" "$backup_stats" "$system_stats"
        fi
    fi

    # 완료 메시지
    local end_time=$(date '+%Y-%m-%d %H:%M:%S')
    local duration=$(($(date +%s) - start_timestamp))

    if [[ "$JSON_OUTPUT" == "true" && "$DRY_RUN" == "false" ]]; then
        cat "$JSON_FILE"
    else
        echo ""
        echo "📊 주간 운영 리포트 생성 완료"
        echo "   기간: $START_DATE ~ $END_DATE"
        echo "   완료: $end_time"
        echo "   소요: ${duration}초"
        if [[ "$DRY_RUN" == "false" ]]; then
            echo "   파일: $REPORT_FILE"
            if [[ "$JSON_OUTPUT" == "true" ]]; then
                echo "        $JSON_FILE"
            fi
        else
            echo "   모드: 시뮬레이션 (파일 생성 없음)"
        fi
        echo ""
    fi

    log_message "INFO" "주간 운영 리포트 생성 완료"
}

# 스크립트 실행
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi