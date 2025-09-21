#!/bin/bash

# 📅 월간 운영 리포트 자동화 스크립트 (한국어 주석 포함)
# 목적: 지난 30일간 보안/백업/시스템 메트릭을 종합 분석하여 월간 운영 현황 리포트 생성
# 실행 내용:
#   1. 지난 30일간 보안 이벤트 종합 분석 (차단된 IP, Rate Limit 위반, 화이트리스트)
#   2. 백업 성공/실패 통계 및 성능 추이 분석
#   3. 시스템 리소스 사용량 및 성능 메트릭 수집
#   4. 월간 성능 등급 판정 (우수/보통/개선 필요)
#   5. Markdown 형식 리포트 생성 (reports/monthly/YYYY-MM.md)
#   6. JSON 형식 출력 지원
#   7. 권장사항 및 다음 달 목표 자동 생성

set -euo pipefail

# 🔧 설정 변수
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOGS_DIR="$PROJECT_ROOT/logs"
REPORTS_DIR="$PROJECT_ROOT/reports/monthly"
SECURITY_LOG="$LOGS_DIR/security.log"
DAILY_OPS_LOG="$LOGS_DIR/daily_ops.log"

# 📅 날짜 설정 (지난 30일)
END_DATE=$(date '+%Y-%m-%d')
START_DATE=$(date -d '30 days ago' '+%Y-%m-%d')
MONTH_YEAR=$(date '+%Y-%m')
REPORT_FILE="$REPORTS_DIR/monthly-report-$MONTH_YEAR.md"
JSON_FILE="$REPORTS_DIR/monthly-report-$MONTH_YEAR.json"

# 🎛️ 옵션 플래그
DRY_RUN=false
JSON_OUTPUT=false
VERBOSE=false
HELP=false

# 📝 사용법 출력
show_usage() {
    cat << EOF
📅 월간 운영 리포트 자동화 스크립트

사용법: $0 [옵션]

옵션:
  --dry-run        시뮬레이션 모드 (파일 생성 없음)
  --json          JSON 형식으로 결과 출력
  --verbose       상세 출력 모드
  --help          이 도움말 출력

실행 내용:
  1. 지난 30일간 보안 이벤트 종합 분석
  2. 백업 성공/실패 통계 및 성능 추이
  3. 시스템 리소스 사용량 분석
  4. 월간 성능 등급 판정
  5. Markdown 리포트 생성
  6. 권장사항 및 다음 달 목표 제시

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

# 🔍 월간 보안 로그 분석 함수
analyze_monthly_security_logs() {
    log_message "INFO" "월간 보안 로그 분석 시작 ($START_DATE ~ $END_DATE)"

    # 로그 파일 존재 확인
    if [[ ! -f "$SECURITY_LOG" ]]; then
        log_message "WARNING" "보안 로그 파일을 찾을 수 없음: $SECURITY_LOG"
        echo "0,0,0,0,0,0"  # blocked_ips, rate_violations, whitelist_adds, monitoring_events, unique_ips, avg_per_day
        return 0
    fi

    # 지난 30일간 로그 필터링 및 분석
    local blocked_ips=0
    local rate_violations=0
    local whitelist_adds=0
    local monitoring_events=0
    local unique_blocked_ips=()

    # 압축된 로그 파일들도 포함하여 분석 (30일)
    local log_files=("$SECURITY_LOG")
    for i in {1..30}; do
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

        # 날짜 필터링 적용
        local filtered_content
        filtered_content=$(echo "$content" | awk -v start="$START_DATE" -v end="$END_DATE" '
            $1 >= start && $1 <= end
        ' 2>/dev/null || echo "")

        # 이벤트 타입별 집계
        blocked_ips=$((blocked_ips + $(echo "$filtered_content" | grep -c "BLOCKED_IP" || true)))
        rate_violations=$((rate_violations + $(echo "$filtered_content" | grep -c "RATE_LIMIT" || true)))
        whitelist_adds=$((whitelist_adds + $(echo "$filtered_content" | grep -c "WHITELIST_ADD" || true)))
        monitoring_events=$((monitoring_events + $(echo "$filtered_content" | grep -c "MONITOR" || true)))

        # 고유 차단 IP 수집
        while IFS= read -r line; do
            if [[ "$line" =~ BLOCKED_IP.*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+) ]]; then
                unique_blocked_ips+=("${BASH_REMATCH[1]}")
            fi
        done <<< "$filtered_content"
    done

    # 고유 IP 수 계산
    local unique_ip_count
    if [[ ${#unique_blocked_ips[@]} -gt 0 ]]; then
        unique_ip_count=$(printf '%s\n' "${unique_blocked_ips[@]}" | sort -u | wc -l)
    else
        unique_ip_count=0
    fi

    # 일일 평균 계산
    local avg_blocked_per_day
    avg_blocked_per_day=$((blocked_ips / 30))

    log_message "INFO" "월간 보안 이벤트 집계 완료 - 차단IP: $blocked_ips (고유: $unique_ip_count), 위반: $rate_violations, 화이트리스트: $whitelist_adds, 모니터링: $monitoring_events"
    echo "$blocked_ips,$rate_violations,$whitelist_adds,$monitoring_events,$unique_ip_count,$avg_blocked_per_day"
}

# 📦 월간 백업 로그 분석 함수
analyze_monthly_backup_logs() {
    log_message "INFO" "월간 백업 로그 분석 시작"

    # daily_ops.log 파일 확인
    if [[ ! -f "$DAILY_OPS_LOG" ]]; then
        log_message "WARNING" "일일 운영 로그 파일을 찾을 수 없음: $DAILY_OPS_LOG"
        echo "0,0,0,0,0"  # backup_success, backup_failures, cleanup_runs, avg_success_rate, total_operations
        return 0
    fi

    # 지난 30일간 백업 관련 이벤트 분석
    local backup_success=0
    local backup_failures=0
    local cleanup_runs=0

    # 날짜 범위에 해당하는 로그 엔트리 필터링
    local filtered_logs
    filtered_logs=$(awk -v start="$START_DATE" -v end="$END_DATE" '
        $1 >= start && $1 <= end
    ' "$DAILY_OPS_LOG" 2>/dev/null || echo "")

    # 백업 관련 이벤트 집계
    backup_success=$(echo "$filtered_logs" | grep -c "백업 검증 완료\|백업.*성공" || true)
    backup_failures=$(echo "$filtered_logs" | grep -c "백업 검증 실패\|백업.*실패" || true)
    cleanup_runs=$(echo "$filtered_logs" | grep -c "백업 정리 완료\|정리.*완료" || true)

    # 성공률 및 총 작업 수 계산
    local total_operations=$((backup_success + backup_failures))
    local avg_success_rate=0
    if [[ $total_operations -gt 0 ]]; then
        avg_success_rate=$((backup_success * 100 / total_operations))
    fi

    log_message "INFO" "월간 백업 이벤트 집계 완료 - 성공: $backup_success, 실패: $backup_failures, 정리: $cleanup_runs, 성공률: ${avg_success_rate}%"
    echo "$backup_success,$backup_failures,$cleanup_runs,$avg_success_rate,$total_operations"
}

# 📈 월간 시스템 메트릭 분석 함수
analyze_monthly_system_metrics() {
    log_message "INFO" "월간 시스템 메트릭 분석 시작"

    # 현재 시스템 상태
    local current_disk_usage
    current_disk_usage=$(df -h . | tail -1 | awk '{print $5}' | sed 's/%//')

    # 로그 파일 크기 추이
    local security_log_size=0
    if [[ -f "$SECURITY_LOG" ]]; then
        security_log_size=$(stat -f%z "$SECURITY_LOG" 2>/dev/null || echo "0")
    fi

    # 백업 디렉토리 총 크기
    local backup_dir_size=0
    if [[ -d "$PROJECT_ROOT/backups" ]]; then
        backup_dir_size=$(du -sk "$PROJECT_ROOT/backups" 2>/dev/null | awk '{print $1}' || echo "0")
    fi

    # 리포트 디렉토리 크기
    local reports_dir_size=0
    if [[ -d "$PROJECT_ROOT/reports" ]]; then
        reports_dir_size=$(du -sk "$PROJECT_ROOT/reports" 2>/dev/null | awk '{print $1}' || echo "0")
    fi

    # 압축된 로그 파일 수 (보관 효율성 지표)
    local compressed_logs=0
    if [[ -d "$LOGS_DIR" ]]; then
        compressed_logs=$(find "$LOGS_DIR" -name "*.gz" -type f | wc -l)
    fi

    # 전체 프로젝트 크기
    local total_project_size
    total_project_size=$(du -sk "$PROJECT_ROOT" 2>/dev/null | awk '{print $1}' || echo "0")

    log_message "INFO" "월간 시스템 메트릭 수집 완료 - 디스크: ${current_disk_usage}%, 보안로그: ${security_log_size}B, 백업: ${backup_dir_size}KB, 압축로그: ${compressed_logs}개"
    echo "$current_disk_usage,$security_log_size,$backup_dir_size,$reports_dir_size,$compressed_logs,$total_project_size"
}

# 🏆 월간 성능 등급 판정 함수
calculate_monthly_performance_grade() {
    local security_stats="$1"
    local backup_stats="$2"
    local system_stats="$3"

    # 통계 파싱
    IFS=',' read -r blocked_ips rate_violations whitelist_adds monitoring_events unique_ips avg_per_day <<< "$security_stats"
    IFS=',' read -r backup_success backup_failures cleanup_runs avg_success_rate total_operations <<< "$backup_stats"
    IFS=',' read -r disk_usage security_log_size backup_dir_size reports_dir_size compressed_logs total_project_size <<< "$system_stats"

    # 성능 점수 계산 (100점 만점)
    local security_score=0
    local backup_score=0
    local system_score=0

    # 보안 점수 (40점 만점)
    if [[ $blocked_ips -le 10 ]]; then
        security_score=$((security_score + 15))  # 매우 좋음
    elif [[ $blocked_ips -le 50 ]]; then
        security_score=$((security_score + 10))  # 좋음
    elif [[ $blocked_ips -le 100 ]]; then
        security_score=$((security_score + 5))   # 보통
    fi

    if [[ $rate_violations -le 20 ]]; then
        security_score=$((security_score + 15))  # 매우 좋음
    elif [[ $rate_violations -le 100 ]]; then
        security_score=$((security_score + 10))  # 좋음
    elif [[ $rate_violations -le 200 ]]; then
        security_score=$((security_score + 5))   # 보통
    fi

    if [[ $monitoring_events -ge 100 ]]; then
        security_score=$((security_score + 10))  # 활발한 모니터링
    elif [[ $monitoring_events -ge 50 ]]; then
        security_score=$((security_score + 5))   # 적절한 모니터링
    fi

    # 백업 점수 (40점 만점)
    if [[ $avg_success_rate -ge 95 ]]; then
        backup_score=$((backup_score + 25))      # 매우 우수
    elif [[ $avg_success_rate -ge 90 ]]; then
        backup_score=$((backup_score + 20))      # 우수
    elif [[ $avg_success_rate -ge 80 ]]; then
        backup_score=$((backup_score + 15))      # 양호
    elif [[ $avg_success_rate -ge 70 ]]; then
        backup_score=$((backup_score + 10))      # 보통
    else
        backup_score=$((backup_score + 5))       # 개선 필요
    fi

    if [[ $cleanup_runs -ge 20 ]]; then
        backup_score=$((backup_score + 15))      # 정기적 정리
    elif [[ $cleanup_runs -ge 10 ]]; then
        backup_score=$((backup_score + 10))      # 적절한 정리
    elif [[ $cleanup_runs -ge 5 ]]; then
        backup_score=$((backup_score + 5))       # 최소 정리
    fi

    # 시스템 점수 (20점 만점)
    if [[ $disk_usage -le 70 ]]; then
        system_score=$((system_score + 10))      # 여유로움
    elif [[ $disk_usage -le 85 ]]; then
        system_score=$((system_score + 7))       # 적절함
    elif [[ $disk_usage -le 95 ]]; then
        system_score=$((system_score + 3))       # 주의 필요
    fi

    if [[ $compressed_logs -ge 10 ]]; then
        system_score=$((system_score + 10))      # 효율적 관리
    elif [[ $compressed_logs -ge 5 ]]; then
        system_score=$((system_score + 7))       # 적절한 관리
    elif [[ $compressed_logs -ge 1 ]]; then
        system_score=$((system_score + 3))       # 최소 관리
    fi

    # 총 점수 및 등급 계산
    local total_score=$((security_score + backup_score + system_score))
    local grade=""
    local grade_status=""

    if [[ $total_score -ge 85 ]]; then
        grade="우수"
        grade_status="excellent"
    elif [[ $total_score -ge 70 ]]; then
        grade="보통"
        grade_status="good"
    else
        grade="개선 필요"
        grade_status="needs_improvement"
    fi

    log_message "INFO" "월간 성능 등급 판정 완료 - 총점: ${total_score}/100, 등급: ${grade}"
    echo "$total_score,$grade,$grade_status,$security_score,$backup_score,$system_score"
}

# 📄 Markdown 리포트 생성 함수
generate_monthly_markdown_report() {
    local security_stats="$1"
    local backup_stats="$2"
    local system_stats="$3"
    local performance_grade="$4"

    # 통계 파싱
    IFS=',' read -r blocked_ips rate_violations whitelist_adds monitoring_events unique_ips avg_per_day <<< "$security_stats"
    IFS=',' read -r backup_success backup_failures cleanup_runs avg_success_rate total_operations <<< "$backup_stats"
    IFS=',' read -r disk_usage security_log_size backup_dir_size reports_dir_size compressed_logs total_project_size <<< "$system_stats"
    IFS=',' read -r total_score grade grade_status security_score backup_score system_score <<< "$performance_grade"

    # Markdown 리포트 생성
    cat > "$REPORT_FILE" << EOF
# 📅 월간 운영 리포트

**보고 기간**: $START_DATE ~ $END_DATE
**보고 월**: $(date -d "$END_DATE" '+%Y년 %m월')
**생성 일시**: $(date '+%Y-%m-%d %H:%M:%S')

## 🏆 월간 성능 등급

### 종합 평가
- 📊 **총 점수**: $total_score/100점
- 🏅 **성능 등급**: $grade
- 📈 **세부 점수**: 보안 $security_score/40, 백업 $backup_score/40, 시스템 $system_score/20

$(if [[ "$grade_status" == "excellent" ]]; then
    echo "✅ **우수**: 모든 영역에서 뛰어난 성과를 보이고 있습니다. 현재 수준을 유지하세요."
elif [[ "$grade_status" == "good" ]]; then
    echo "👍 **보통**: 전반적으로 양호한 상태입니다. 일부 영역에서 개선 여지가 있습니다."
else
    echo "⚠️ **개선 필요**: 여러 영역에서 주의가 필요합니다. 개선 계획을 수립하세요."
fi)

## 🛡️ 보안 현황 (30일간)

### 보안 이벤트 요약
- 🚫 **차단된 IP**: $blocked_ips건 (고유 IP: $unique_ips개)
- ⚠️ **Rate Limit 위반**: $rate_violations건
- ✅ **화이트리스트 추가**: $whitelist_adds건
- 👀 **모니터링 이벤트**: $monitoring_events건
- 📊 **일일 평균 차단**: ${avg_per_day}건

### 보안 상태 평가
$(if [[ $blocked_ips -lt 20 ]]; then
    echo "✅ **매우 양호**: 차단된 IP 수가 매우 적어 보안 상태가 우수합니다."
elif [[ $blocked_ips -lt 100 ]]; then
    echo "👍 **양호**: 차단된 IP 수가 적절한 수준입니다."
elif [[ $blocked_ips -lt 200 ]]; then
    echo "⚠️ **주의**: 차단된 IP 수가 증가 추세입니다. 보안 정책을 검토하세요."
else
    echo "🚨 **위험**: 차단된 IP 수가 많습니다. 즉시 보안 강화 조치가 필요합니다."
fi)

### 보안 추세 분석
- **일일 평균**: ${avg_per_day}개 IP 차단
- **고유 IP 비율**: $((unique_ips * 100 / (blocked_ips == 0 ? 1 : blocked_ips)))% (재차단 비율: $((100 - unique_ips * 100 / (blocked_ips == 0 ? 1 : blocked_ips)))%)
- **모니터링 활성도**: $(if [[ $monitoring_events -gt 200 ]]; then echo "높음"; elif [[ $monitoring_events -gt 100 ]]; then echo "보통"; else echo "낮음"; fi)

## 📦 백업 현황 (30일간)

### 백업 통계
- ✅ **성공한 백업**: $backup_success회
- ❌ **실패한 백업**: $backup_failures회
- 🧹 **정리 작업**: $cleanup_runs회
- 📊 **평균 성공률**: ${avg_success_rate}%
- 🔧 **총 백업 작업**: $total_operations회

### 백업 상태 평가
$(if [[ $avg_success_rate -ge 95 ]]; then
    echo "✅ **매우 우수**: 백업 성공률이 95% 이상으로 매우 안정적입니다."
elif [[ $avg_success_rate -ge 90 ]]; then
    echo "👍 **우수**: 백업 성공률이 90% 이상으로 안정적입니다."
elif [[ $avg_success_rate -ge 80 ]]; then
    echo "⚠️ **양호**: 백업 성공률이 80% 이상이지만 개선 여지가 있습니다."
else
    echo "🚨 **개선 필요**: 백업 성공률이 80% 미만입니다. 백업 시스템을 점검하세요."
fi)

### 백업 효율성 분석
- **정리 작업 빈도**: $(if [[ $cleanup_runs -gt 20 ]]; then echo "높음 (효율적)"; elif [[ $cleanup_runs -gt 10 ]]; then echo "보통"; else echo "낮음 (개선 필요)"; fi)
- **실패율**: $((backup_failures * 100 / (total_operations == 0 ? 1 : total_operations)))%
- **월간 백업 신뢰도**: $(if [[ $avg_success_rate -ge 95 ]]; then echo "높음"; elif [[ $avg_success_rate -ge 85 ]]; then echo "보통"; else echo "낮음"; fi)

## 💾 시스템 리소스 (현재 상태)

### 리소스 사용량
- 💽 **디스크 사용률**: ${disk_usage}%
- 📝 **보안 로그 크기**: $(numfmt --to=iec $security_log_size)
- 📦 **백업 디렉토리**: $(numfmt --to=iec $((backup_dir_size * 1024)))
- 📋 **리포트 디렉토리**: $(numfmt --to=iec $((reports_dir_size * 1024)))
- 🗜️ **압축된 로그**: ${compressed_logs}개
- 📁 **전체 프로젝트**: $(numfmt --to=iec $((total_project_size * 1024)))

### 시스템 상태 평가
$(if [[ $disk_usage -lt 70 ]]; then
    echo "✅ **여유로움**: 디스크 사용률이 70% 미만으로 충분한 여유 공간이 있습니다."
elif [[ $disk_usage -lt 85 ]]; then
    echo "👍 **적절함**: 디스크 사용률이 적절한 수준입니다."
elif [[ $disk_usage -lt 95 ]]; then
    echo "⚠️ **주의 필요**: 디스크 사용률이 높습니다. 정리 작업을 계획하세요."
else
    echo "🚨 **긴급**: 디스크 사용률이 95% 이상입니다. 즉시 공간 확보가 필요합니다."
fi)

### 저장 공간 효율성
- **로그 압축 효율**: $(if [[ $compressed_logs -gt 10 ]]; then echo "높음"; elif [[ $compressed_logs -gt 5 ]]; then echo "보통"; else echo "낮음"; fi)
- **백업 용량 추세**: $(if [[ $backup_dir_size -gt 1048576 ]]; then echo "증가 (1GB+)"; elif [[ $backup_dir_size -gt 524288 ]]; then echo "보통 (500MB+)"; else echo "적음"; fi)

## 📋 월간 성과 요약

### 주요 성과
- 📊 총 $(($monitoring_events + $backup_success + $cleanup_runs))회의 자동화 작업 수행
- 🛡️ $blocked_ips개의 위험 IP 차단으로 보안 강화 (고유 IP: $unique_ips개)
- 📦 $backup_success회의 성공적인 백업으로 데이터 보호 (성공률: ${avg_success_rate}%)
- 🧹 $cleanup_runs회의 정리 작업으로 저장 공간 최적화

### 이번 달 하이라이트
$(if [[ $grade_status == "excellent" ]]; then
    echo "🏆 **우수한 성과**: 모든 영역에서 목표를 달성했습니다."
elif [[ $grade_status == "good" ]]; then
    echo "👍 **안정적 운영**: 대부분의 영역에서 양호한 성과를 보였습니다."
else
    echo "🔧 **개선 기회**: 여러 영역에서 개선 여지를 확인했습니다."
fi)

## 💡 권장 사항

### 즉시 조치 사항
$(if [[ $blocked_ips -gt 100 ]]; then
    echo "🚨 **긴급**: 차단 IP 수가 많습니다. 보안 정책을 즉시 검토하세요."
fi)
$(if [[ $avg_success_rate -lt 90 ]]; then
    echo "📦 **우선**: 백업 성공률이 낮습니다. 백업 시스템을 점검하세요."
fi)
$(if [[ $disk_usage -gt 90 ]]; then
    echo "💾 **긴급**: 디스크 사용률이 높습니다. 즉시 정리 작업을 수행하세요."
fi)

### 개선 방안
$(if [[ $security_score -lt 30 ]]; then
    echo "- 🔍 보안 모니터링 시스템 강화 및 Rate Limit 정책 최적화"
fi)
$(if [[ $backup_score -lt 30 ]]; then
    echo "- 📦 백업 자동화 개선 및 정기 백업 검증 프로세스 도입"
fi)
$(if [[ $system_score -lt 15 ]]; then
    echo "- 💾 시스템 리소스 모니터링 강화 및 자동 정리 정책 수립"
fi)
- 🔄 자동화 스크립트 성능 최적화 및 알림 시스템 개선
- 📊 월간 리포트 기반 데이터 분석 및 예측 모델 구축

## 📅 다음 달 목표

### 성능 목표
- 🎯 **보안**: 차단 IP $(($blocked_ips > 50 ? blocked_ips - 20 : blocked_ips))개 이하 유지, Rate Limit 위반 $(($rate_violations > 50 ? rate_violations - 20 : rate_violations))건 이하
- 🎯 **백업**: 성공률 $((avg_success_rate > 95 ? 98 : avg_success_rate + 5))% 이상 달성, 정리 작업 $(($cleanup_runs < 20 ? cleanup_runs + 5 : cleanup_runs))회 이상
- 🎯 **시스템**: 디스크 사용률 $(($disk_usage > 80 ? disk_usage - 10 : disk_usage))% 이하 유지

### 전략적 계획
1. **보안 강화**: 화이트리스트 정책 최적화 및 자동 차단 로직 개선
2. **백업 고도화**: 다중 백업 전략 도입 및 복구 테스트 정기화
3. **자동화 확장**: CI/CD 파이프라인 통합 및 실시간 모니터링 강화
4. **성능 최적화**: 로그 압축 자동화 및 리소스 사용량 예측 시스템 구축

### 핵심 성과 지표 (KPI)
- 📈 **보안 점수**: 현재 $security_score/40 → 목표 $(($security_score > 35 ? 38 : security_score + 3))/40
- 📈 **백업 점수**: 현재 $backup_score/40 → 목표 $(($backup_score > 35 ? 38 : backup_score + 3))/40
- 📈 **시스템 점수**: 현재 $system_score/20 → 목표 $(($system_score > 17 ? 19 : system_score + 2))/20
- 📈 **종합 등급**: 현재 $grade → 목표 $(if [[ "$grade_status" == "excellent" ]]; then echo "우수 유지"; elif [[ "$grade_status" == "good" ]]; then echo "우수"; else echo "보통"; fi)

---

*이 월간 리포트는 자동 생성되었습니다. 상세한 분석이나 문의사항은 시스템 관리팀에게 연락하세요.*

**다음 월간 리포트 예정일**: $(date -d "next month" '+%Y년 %m월 1일')
EOF

    log_message "INFO" "월간 Markdown 리포트 생성 완료: $REPORT_FILE"
}

# 📊 JSON 리포트 생성 함수
generate_monthly_json_report() {
    local security_stats="$1"
    local backup_stats="$2"
    local system_stats="$3"
    local performance_grade="$4"

    # 통계 파싱
    IFS=',' read -r blocked_ips rate_violations whitelist_adds monitoring_events unique_ips avg_per_day <<< "$security_stats"
    IFS=',' read -r backup_success backup_failures cleanup_runs avg_success_rate total_operations <<< "$backup_stats"
    IFS=',' read -r disk_usage security_log_size backup_dir_size reports_dir_size compressed_logs total_project_size <<< "$system_stats"
    IFS=',' read -r total_score grade grade_status security_score backup_score system_score <<< "$performance_grade"

    # JSON 리포트 생성
    cat > "$JSON_FILE" << EOF
{
  "report_metadata": {
    "period_start": "$START_DATE",
    "period_end": "$END_DATE",
    "report_month": "$(date -d "$END_DATE" '+%Y-%m')",
    "generated_at": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')",
    "report_type": "monthly_operations",
    "analysis_period_days": 30
  },
  "performance_grade": {
    "total_score": $total_score,
    "grade": "$grade",
    "grade_status": "$grade_status",
    "security_score": $security_score,
    "backup_score": $backup_score,
    "system_score": $system_score,
    "max_scores": {
      "security": 40,
      "backup": 40,
      "system": 20,
      "total": 100
    }
  },
  "security_events": {
    "blocked_ips": $blocked_ips,
    "unique_blocked_ips": $unique_ips,
    "rate_limit_violations": $rate_violations,
    "whitelist_additions": $whitelist_adds,
    "monitoring_events": $monitoring_events,
    "daily_average_blocks": $avg_per_day,
    "repeat_offender_rate": $((100 - unique_ips * 100 / (blocked_ips == 0 ? 1 : blocked_ips))),
    "total_security_events": $((blocked_ips + rate_violations + whitelist_adds + monitoring_events))
  },
  "backup_operations": {
    "successful_backups": $backup_success,
    "failed_backups": $backup_failures,
    "cleanup_operations": $cleanup_runs,
    "average_success_rate_percent": $avg_success_rate,
    "total_backup_operations": $total_operations,
    "failure_rate_percent": $((backup_failures * 100 / (total_operations == 0 ? 1 : total_operations))),
    "cleanup_frequency": "$(if [[ $cleanup_runs -gt 20 ]]; then echo "high"; elif [[ $cleanup_runs -gt 10 ]]; then echo "medium"; else echo "low"; fi)"
  },
  "system_resources": {
    "disk_usage_percent": $disk_usage,
    "security_log_size_bytes": $security_log_size,
    "backup_directory_size_kb": $backup_dir_size,
    "reports_directory_size_kb": $reports_dir_size,
    "compressed_logs_count": $compressed_logs,
    "total_project_size_kb": $total_project_size,
    "storage_efficiency": "$(if [[ $compressed_logs -gt 10 ]]; then echo "high"; elif [[ $compressed_logs -gt 5 ]]; then echo "medium"; else echo "low"; fi)"
  },
  "monthly_trends": {
    "security_status": "$(if [[ $blocked_ips -lt 50 ]]; then echo "stable"; elif [[ $blocked_ips -lt 150 ]]; then echo "increasing"; else echo "high_activity"; fi)",
    "backup_reliability": "$(if [[ $avg_success_rate -ge 95 ]]; then echo "excellent"; elif [[ $avg_success_rate -ge 85 ]]; then echo "good"; else echo "needs_improvement"; fi)",
    "system_health": "$(if [[ $disk_usage -lt 80 ]]; then echo "healthy"; elif [[ $disk_usage -lt 95 ]]; then echo "caution"; else echo "critical"; fi)"
  },
  "recommendations": {
    "immediate_actions": [
      $(if [[ $blocked_ips -gt 100 ]]; then echo '"Review security policies due to high IP blocks",'fi)
      $(if [[ $avg_success_rate -lt 90 ]]; then echo '"Investigate backup system issues",'fi)
      $(if [[ $disk_usage -gt 90 ]]; then echo '"Immediate disk cleanup required",'fi)
      "Monitor system performance trends"
    ],
    "strategic_improvements": [
      $(if [[ $security_score -lt 30 ]]; then echo '"Enhance security monitoring and rate limiting",'fi)
      $(if [[ $backup_score -lt 30 ]]; then echo '"Improve backup automation and verification",'fi)
      $(if [[ $system_score -lt 15 ]]; then echo '"Optimize system resource management",'fi)
      "Implement predictive analytics for capacity planning"
    ]
  },
  "next_month_targets": {
    "security_targets": {
      "max_blocked_ips": $(($blocked_ips > 50 ? blocked_ips - 20 : blocked_ips)),
      "max_rate_violations": $(($rate_violations > 50 ? rate_violations - 20 : rate_violations)),
      "target_security_score": $(($security_score > 35 ? 38 : security_score + 3))
    },
    "backup_targets": {
      "min_success_rate": $((avg_success_rate > 95 ? 98 : avg_success_rate + 5)),
      "min_cleanup_operations": $(($cleanup_runs < 20 ? cleanup_runs + 5 : cleanup_runs)),
      "target_backup_score": $(($backup_score > 35 ? 38 : backup_score + 3))
    },
    "system_targets": {
      "max_disk_usage": $(($disk_usage > 80 ? disk_usage - 10 : disk_usage)),
      "target_system_score": $(($system_score > 17 ? 19 : system_score + 2)),
      "target_overall_grade": "$(if [[ "$grade_status" == "excellent" ]]; then echo "excellent"; elif [[ "$grade_status" == "good" ]]; then echo "excellent"; else echo "good"; fi)"
    }
  }
}
EOF

    log_message "INFO" "월간 JSON 리포트 생성 완료: $JSON_FILE"
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

    log_message "INFO" "월간 운영 리포트 생성 시작 ($START_DATE ~ $END_DATE)"

    # 데이터 수집 및 분석
    local security_stats
    local backup_stats
    local system_stats
    local performance_grade

    security_stats=$(analyze_monthly_security_logs)
    backup_stats=$(analyze_monthly_backup_logs)
    system_stats=$(analyze_monthly_system_metrics)
    performance_grade=$(calculate_monthly_performance_grade "$security_stats" "$backup_stats" "$system_stats")

    if [[ "$DRY_RUN" == "true" ]]; then
        log_message "INFO" "[시뮬레이션] 리포트 생성 건너뜀"
        if [[ "$VERBOSE" == "true" ]]; then
            echo "보안 통계: $security_stats"
            echo "백업 통계: $backup_stats"
            echo "시스템 통계: $system_stats"
            echo "성능 등급: $performance_grade"
        fi
    else
        # 리포트 생성
        generate_monthly_markdown_report "$security_stats" "$backup_stats" "$system_stats" "$performance_grade"

        if [[ "$JSON_OUTPUT" == "true" ]]; then
            generate_monthly_json_report "$security_stats" "$backup_stats" "$system_stats" "$performance_grade"
        fi
    fi

    # 완료 메시지
    local end_time=$(date '+%Y-%m-%d %H:%M:%S')
    local duration=$(($(date +%s) - start_timestamp))

    if [[ "$JSON_OUTPUT" == "true" && "$DRY_RUN" == "false" ]]; then
        cat "$JSON_FILE"
    else
        echo ""
        echo "📅 월간 운영 리포트 생성 완료"
        echo "   기간: $START_DATE ~ $END_DATE (30일)"
        echo "   보고월: $(date -d "$END_DATE" '+%Y년 %m월')"
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

    log_message "INFO" "월간 운영 리포트 생성 완료"
}

# 스크립트 실행
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi