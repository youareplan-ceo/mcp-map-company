#!/bin/bash
# scripts/ci_error_analyzer.sh
#
# CI/CD 에러 로그 분석 및 알림 자동화 스크립트
#
# 주요 기능:
# - 최근 7일간 CI/CD 로그 분석
# - 실패 빌드/테스트 Top10 원인 추출
# - 로그 크기 > 1MB 파일 자동 압축
# - 에러 유형별 빈도 집계 (빌드, 테스트, 배포)
# - Markdown/JSON 리포트 생성
# - 알림 시스템 연동

set -euo pipefail

# ─────────────────────────────────────────
# 글로벌 변수
# ─────────────────────────────────────────
readonly SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 기본 설정
DAYS="${CI_ERROR_ANALYZER_DAYS:-7}"
OUTPUT_FORMAT="${CI_ERROR_ANALYZER_FORMAT:-text}"
DRY_RUN="${CI_ERROR_ANALYZER_DRY_RUN:-false}"
VERBOSE="${CI_ERROR_ANALYZER_VERBOSE:-false}"
OUTPUT_DIR="${CI_ERROR_ANALYZER_OUTPUT_DIR:-${PROJECT_ROOT}/logs/ci_errors}"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"
COMPRESS_THRESHOLD="${CI_ERROR_ANALYZER_COMPRESS_MB:-1}"
ALERT_ENABLED="${CI_ERROR_ANALYZER_ALERT_ENABLED:-true}"

# 색상 정의
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly NC='\033[0m' # No Color

# ─────────────────────────────────────────
# 로깅 및 유틸리티 함수
# ─────────────────────────────────────────
log() {
    echo -e "${WHITE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*" >&2
}

log_info() {
    echo -e "${BLUE}ℹ️  [INFO]${NC} $*" >&2
}

log_warn() {
    echo -e "${YELLOW}⚠️  [WARN]${NC} $*" >&2
}

log_error() {
    echo -e "${RED}❌ [ERROR]${NC} $*" >&2
}

log_success() {
    echo -e "${GREEN}✅ [SUCCESS]${NC} $*" >&2
}

log_debug() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${PURPLE}🔍 [DEBUG]${NC} $*" >&2
    fi
}

die() {
    log_error "$*"
    exit 1
}

# ─────────────────────────────────────────
# 도움말 함수
# ─────────────────────────────────────────
show_help() {
    cat << 'EOF'
🚨 MCP-MAP CI/CD 에러 로그 분석기

사용법:
    ./scripts/ci_error_analyzer.sh [옵션]

옵션:
    --days N                분석할 일수 (기본값: 7)
    --format FORMAT         출력 형식: text|json|markdown (기본값: text)
    --output-dir DIR        출력 디렉토리 (기본값: logs/ci_errors)
    --dry-run              실제 변경 없이 시뮬레이션만 실행
    --verbose              상세 로그 출력
    --no-alert             알림 전송 비활성화
    --compress-mb SIZE     압축 임계치 MB (기본값: 1)
    --help                 이 도움말 표시

환경 변수:
    GITHUB_TOKEN                    GitHub API 토큰
    CI_ERROR_ANALYZER_DAYS          분석 일수
    CI_ERROR_ANALYZER_FORMAT        출력 형식
    CI_ERROR_ANALYZER_DRY_RUN       드라이런 모드 (true/false)
    CI_ERROR_ANALYZER_VERBOSE       상세 로그 (true/false)
    CI_ERROR_ANALYZER_OUTPUT_DIR    출력 디렉토리
    CI_ERROR_ANALYZER_COMPRESS_MB   압축 임계치 (MB)
    CI_ERROR_ANALYZER_ALERT_ENABLED 알림 활성화 (true/false)

예시:
    # 기본 분석 (최근 7일)
    ./scripts/ci_error_analyzer.sh

    # JSON 형식으로 최근 14일 분석
    ./scripts/ci_error_analyzer.sh --days 14 --format json

    # 드라이런 모드로 상세 로그 포함
    ./scripts/ci_error_analyzer.sh --dry-run --verbose

    # 알림 없이 마크다운 리포트 생성
    ./scripts/ci_error_analyzer.sh --format markdown --no-alert

출력:
    - CI/CD 에러 통계 요약
    - 실패 빌드/테스트 Top 10 원인
    - 에러 유형별 빈도 집계
    - 대용량 로그 파일 압축 결과
    - 생성된 리포트 파일 경로
EOF
}

# ─────────────────────────────────────────
# 인수 파싱
# ─────────────────────────────────────────
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --days)
                DAYS="$2"
                shift 2
                ;;
            --format)
                OUTPUT_FORMAT="$2"
                shift 2
                ;;
            --output-dir)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN="true"
                shift
                ;;
            --verbose)
                VERBOSE="true"
                shift
                ;;
            --no-alert)
                ALERT_ENABLED="false"
                shift
                ;;
            --compress-mb)
                COMPRESS_THRESHOLD="$2"
                shift 2
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                die "알 수 없는 옵션: $1. --help를 사용하여 도움말을 확인하세요."
                ;;
        esac
    done
}

# ─────────────────────────────────────────
# 의존성 확인
# ─────────────────────────────────────────
check_dependencies() {
    local deps=("jq" "curl" "gzip" "python3")

    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            die "필수 의존성이 설치되지 않음: $dep"
        fi
    done

    if [[ -z "$GITHUB_TOKEN" ]]; then
        log_warn "GITHUB_TOKEN이 설정되지 않음. 공개 리포지토리 제한 적용."
    fi

    log_debug "의존성 확인 완료"
}

# ─────────────────────────────────────────
# 디렉토리 설정
# ─────────────────────────────────────────
setup_directories() {
    local dirs=(
        "$OUTPUT_DIR"
        "$OUTPUT_DIR/logs"
        "$OUTPUT_DIR/reports"
        "$OUTPUT_DIR/compressed"
    )

    for dir in "${dirs[@]}"; do
        if [[ "$DRY_RUN" == "false" ]]; then
            mkdir -p "$dir"
            log_debug "디렉토리 생성: $dir"
        else
            log_debug "[DRY-RUN] 디렉토리 생성 시뮬레이션: $dir"
        fi
    done
}

# ─────────────────────────────────────────
# GitHub Actions 워크플로우 실행 정보 수집
# ─────────────────────────────────────────
fetch_workflow_runs() {
    local days="$1"
    local since_date
    since_date=$(date -d "${days} days ago" -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -v-${days}d +"%Y-%m-%dT%H:%M:%SZ")

    log_info "GitHub Actions 워크플로우 실행 정보 수집 중... (최근 ${days}일)"

    local api_url="https://api.github.com/repos/youareplan/mcp-map-company/actions/runs"
    local auth_header=""

    if [[ -n "$GITHUB_TOKEN" ]]; then
        auth_header="-H \"Authorization: token $GITHUB_TOKEN\""
    fi

    local runs_data
    if runs_data=$(eval curl -s $auth_header \
        "\"$api_url?created=>\${since_date}&per_page=100\""); then
        echo "$runs_data" > "$OUTPUT_DIR/workflow_runs.json"
        log_success "워크플로우 실행 정보 수집 완료"

        # 실행 상태별 통계
        local total_runs failed_runs success_runs
        total_runs=$(echo "$runs_data" | jq '.total_count // 0')
        failed_runs=$(echo "$runs_data" | jq '[.workflow_runs[] | select(.conclusion == "failure")] | length')
        success_runs=$(echo "$runs_data" | jq '[.workflow_runs[] | select(.conclusion == "success")] | length')

        log_debug "총 실행: $total_runs, 성공: $success_runs, 실패: $failed_runs"

        return 0
    else
        log_error "GitHub API 호출 실패"
        return 1
    fi
}

# ─────────────────────────────────────────
# 실패한 워크플로우 로그 다운로드
# ─────────────────────────────────────────
download_failed_logs() {
    if [[ ! -f "$OUTPUT_DIR/workflow_runs.json" ]]; then
        log_error "워크플로우 실행 정보 파일이 없습니다."
        return 1
    fi

    log_info "실패한 워크플로우 로그 다운로드 중..."

    local failed_runs
    failed_runs=$(jq -r '.workflow_runs[] | select(.conclusion == "failure") | "\(.id)|\(.name)|\(.head_branch)"' "$OUTPUT_DIR/workflow_runs.json")

    local download_count=0
    while IFS='|' read -r run_id run_name branch; do
        if [[ -z "$run_id" ]]; then continue; fi

        log_debug "다운로드 중: $run_name (ID: $run_id, 브랜치: $branch)"

        local log_file="$OUTPUT_DIR/logs/run_${run_id}_${run_name//[^a-zA-Z0-9]/_}.log"

        if [[ "$DRY_RUN" == "false" ]]; then
            local auth_header=""
            if [[ -n "$GITHUB_TOKEN" ]]; then
                auth_header="-H \"Authorization: token $GITHUB_TOKEN\""
            fi

            # GitHub Actions 로그 URL (실제 구현에서는 적절한 API 엔드포인트 사용)
            local log_url="https://api.github.com/repos/youareplan/mcp-map-company/actions/runs/$run_id/logs"

            if eval curl -s $auth_header -L "\"$log_url\"" > "$log_file" 2>/dev/null; then
                ((download_count++))
                log_debug "로그 다운로드 완료: $log_file"
            else
                log_warn "로그 다운로드 실패: $run_id"
            fi
        else
            log_debug "[DRY-RUN] 로그 다운로드 시뮬레이션: $log_file"
            ((download_count++))
        fi
    done <<< "$failed_runs"

    log_success "총 ${download_count}개 실패 로그 다운로드 완료"
}

# ─────────────────────────────────────────
# 에러 패턴 분석
# ─────────────────────────────────────────
analyze_error_patterns() {
    log_info "에러 패턴 분석 중..."

    local log_dir="$OUTPUT_DIR/logs"
    local analysis_file="$OUTPUT_DIR/error_analysis.json"

    # Python 스크립트를 사용한 고급 로그 분석
    cat > "$OUTPUT_DIR/analyze_errors.py" << 'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CI/CD 에러 로그 분석 스크립트
"""

import json
import re
import os
import sys
from collections import defaultdict, Counter
from pathlib import Path
import gzip

def analyze_log_file(log_path):
    """개별 로그 파일 분석"""
    errors = []
    error_types = defaultdict(int)

    try:
        # gzip 파일 처리
        if log_path.suffix == '.gz':
            with gzip.open(log_path, 'rt', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        else:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

        lines = content.split('\n')

        for i, line in enumerate(lines):
            line = line.strip()

            # 에러 패턴 매칭
            error_patterns = [
                (r'(?i)error\s*:\s*(.+)', 'BUILD_ERROR'),
                (r'(?i)test\s+failed\s*:\s*(.+)', 'TEST_FAILURE'),
                (r'(?i)assertion\s+failed\s*:\s*(.+)', 'ASSERTION_ERROR'),
                (r'(?i)timeout\s*:\s*(.+)', 'TIMEOUT_ERROR'),
                (r'(?i)out\s+of\s+memory\s*:\s*(.+)', 'MEMORY_ERROR'),
                (r'(?i)permission\s+denied\s*:\s*(.+)', 'PERMISSION_ERROR'),
                (r'(?i)module\s+not\s+found\s*:\s*(.+)', 'MODULE_ERROR'),
                (r'(?i)syntax\s+error\s*:\s*(.+)', 'SYNTAX_ERROR'),
                (r'(?i)deployment\s+failed\s*:\s*(.+)', 'DEPLOY_ERROR'),
                (r'(?i)connection\s+refused\s*:\s*(.+)', 'CONNECTION_ERROR'),
            ]

            for pattern, error_type in error_patterns:
                match = re.search(pattern, line)
                if match:
                    error_msg = match.group(1) if len(match.groups()) > 0 else line
                    errors.append({
                        'type': error_type,
                        'message': error_msg[:200],  # 메시지 길이 제한
                        'line_number': i + 1,
                        'context': lines[max(0, i-1):i+2] if i > 0 else [line]
                    })
                    error_types[error_type] += 1
                    break

    except Exception as e:
        print(f"로그 파일 분석 오류 {log_path}: {e}", file=sys.stderr)

    return errors, dict(error_types)

def main():
    import argparse

    parser = argparse.ArgumentParser(description='CI/CD 로그 에러 분석')
    parser.add_argument('--log-dir', required=True, help='로그 디렉토리')
    parser.add_argument('--output', required=True, help='출력 JSON 파일')
    parser.add_argument('--verbose', action='store_true', help='상세 출력')

    args = parser.parse_args()

    log_dir = Path(args.log_dir)
    if not log_dir.exists():
        print(f"로그 디렉토리가 존재하지 않음: {log_dir}", file=sys.stderr)
        sys.exit(1)

    all_errors = []
    all_error_types = defaultdict(int)
    processed_files = 0

    # 로그 파일 처리
    for log_file in log_dir.glob('*.log*'):
        if args.verbose:
            print(f"분석 중: {log_file}", file=sys.stderr)

        errors, error_types = analyze_log_file(log_file)

        all_errors.extend([{
            **error,
            'source_file': str(log_file.name)
        } for error in errors])

        for error_type, count in error_types.items():
            all_error_types[error_type] += count

        processed_files += 1

    # 에러 빈도순 정렬 (Top 10)
    top_errors = Counter()
    for error in all_errors:
        top_errors[error['message']] += 1

    # 결과 생성
    result = {
        'analysis_summary': {
            'processed_files': processed_files,
            'total_errors': len(all_errors),
            'unique_error_types': len(all_error_types),
            'top_error_types': dict(sorted(all_error_types.items(), key=lambda x: x[1], reverse=True)[:10])
        },
        'top_10_errors': [
            {'message': msg, 'count': count}
            for msg, count in top_errors.most_common(10)
        ],
        'error_distribution': dict(all_error_types),
        'detailed_errors': all_errors[:50]  # 상위 50개만 저장
    }

    # JSON 출력
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    if args.verbose:
        print(f"분석 완료: 총 {len(all_errors)}개 에러 발견 ({processed_files}개 파일)", file=sys.stderr)

if __name__ == '__main__':
    main()
EOF

    # Python 분석 스크립트 실행
    if [[ "$DRY_RUN" == "false" ]]; then
        python3 "$OUTPUT_DIR/analyze_errors.py" \
            --log-dir "$log_dir" \
            --output "$analysis_file" \
            $([ "$VERBOSE" == "true" ] && echo "--verbose")

        if [[ -f "$analysis_file" ]]; then
            log_success "에러 분석 완료: $analysis_file"
        else
            log_error "에러 분석 실패"
            return 1
        fi
    else
        log_debug "[DRY-RUN] 에러 분석 시뮬레이션"
        # 드라이런 모드에서 샘플 데이터 생성
        cat > "$analysis_file" << 'EOF'
{
  "analysis_summary": {
    "processed_files": 5,
    "total_errors": 23,
    "unique_error_types": 4,
    "top_error_types": {
      "TEST_FAILURE": 12,
      "BUILD_ERROR": 7,
      "TIMEOUT_ERROR": 3,
      "MODULE_ERROR": 1
    }
  },
  "top_10_errors": [
    {"message": "test_user_authentication failed", "count": 5},
    {"message": "build timeout after 30 minutes", "count": 3},
    {"message": "module 'requests' not found", "count": 2}
  ],
  "error_distribution": {
    "TEST_FAILURE": 12,
    "BUILD_ERROR": 7,
    "TIMEOUT_ERROR": 3,
    "MODULE_ERROR": 1
  }
}
EOF
    fi
}

# ─────────────────────────────────────────
# 대용량 로그 파일 압축
# ─────────────────────────────────────────
compress_large_logs() {
    log_info "대용량 로그 파일 압축 중... (임계치: ${COMPRESS_THRESHOLD}MB)"

    local log_dir="$OUTPUT_DIR/logs"
    local compressed_dir="$OUTPUT_DIR/compressed"
    local compressed_count=0
    local total_saved=0

    if [[ ! -d "$log_dir" ]]; then
        log_warn "로그 디렉토리가 존재하지 않음: $log_dir"
        return 0
    fi

    # MB를 바이트로 변환
    local threshold_bytes=$((COMPRESS_THRESHOLD * 1024 * 1024))

    while IFS= read -r -d '' log_file; do
        local file_size
        file_size=$(stat -f%z "$log_file" 2>/dev/null || stat -c%s "$log_file" 2>/dev/null || echo "0")

        if [[ "$file_size" -gt "$threshold_bytes" ]]; then
            local basename
            basename=$(basename "$log_file")
            local compressed_file="$compressed_dir/${basename}.gz"

            log_debug "압축 중: $log_file ($(echo "scale=2; $file_size/1024/1024" | bc 2>/dev/null || echo "N/A")MB)"

            if [[ "$DRY_RUN" == "false" ]]; then
                if gzip -c "$log_file" > "$compressed_file"; then
                    local compressed_size
                    compressed_size=$(stat -f%z "$compressed_file" 2>/dev/null || stat -c%s "$compressed_file" 2>/dev/null || echo "0")
                    local saved=$((file_size - compressed_size))

                    rm -f "$log_file"
                    ((compressed_count++))
                    total_saved=$((total_saved + saved))

                    log_debug "압축 완료: $compressed_file (절약: $(echo "scale=2; $saved/1024/1024" | bc 2>/dev/null || echo "N/A")MB)"
                else
                    log_warn "압축 실패: $log_file"
                fi
            else
                log_debug "[DRY-RUN] 압축 시뮬레이션: $log_file"
                ((compressed_count++))
                total_saved=$((total_saved + file_size / 2))  # 추정 압축률 50%
            fi
        fi
    done < <(find "$log_dir" -name "*.log" -type f -print0 2>/dev/null)

    if [[ "$compressed_count" -gt 0 ]]; then
        log_success "총 ${compressed_count}개 파일 압축 완료 (절약: $(echo "scale=2; $total_saved/1024/1024" | bc 2>/dev/null || echo "N/A")MB)"
    else
        log_info "압축 대상 파일 없음"
    fi
}

# ─────────────────────────────────────────
# 리포트 생성
# ─────────────────────────────────────────
generate_report() {
    local format="$1"
    local timestamp
    timestamp=$(date '+%Y%m%d_%H%M%S')

    log_info "리포트 생성 중... (형식: $format)"

    local analysis_file="$OUTPUT_DIR/error_analysis.json"
    if [[ ! -f "$analysis_file" ]]; then
        log_error "에러 분석 파일이 없습니다: $analysis_file"
        return 1
    fi

    case "$format" in
        "json")
            generate_json_report "$timestamp"
            ;;
        "markdown")
            generate_markdown_report "$timestamp"
            ;;
        "text")
            generate_text_report "$timestamp"
            ;;
        *)
            log_error "지원하지 않는 형식: $format"
            return 1
            ;;
    esac
}

generate_json_report() {
    local timestamp="$1"
    local output_file="$OUTPUT_DIR/reports/ci_error_report_${timestamp}.json"

    local analysis_data
    analysis_data=$(cat "$OUTPUT_DIR/error_analysis.json")

    # 추가 메타데이터와 함께 JSON 리포트 생성
    jq -n \
        --arg timestamp "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
        --arg days "$DAYS" \
        --arg format "$OUTPUT_FORMAT" \
        --argjson analysis "$analysis_data" \
        '{
            generated_at: $timestamp,
            analysis_period_days: ($days | tonumber),
            format: $format,
            summary: $analysis.analysis_summary,
            top_errors: $analysis.top_10_errors,
            error_distribution: $analysis.error_distribution,
            detailed_errors: $analysis.detailed_errors
        }' > "$output_file"

    log_success "JSON 리포트 생성: $output_file"
}

generate_markdown_report() {
    local timestamp="$1"
    local output_file="$OUTPUT_DIR/reports/ci_error_report_${timestamp}.md"

    local analysis_data
    analysis_data=$(cat "$OUTPUT_DIR/error_analysis.json")

    cat > "$output_file" << EOF
# 🚨 CI/CD 에러 로그 분석 리포트

**생성 일시:** $(date '+%Y-%m-%d %H:%M:%S %Z')
**분석 기간:** 최근 ${DAYS}일
**리포트 형식:** Markdown

## 📊 분석 요약

$(echo "$analysis_data" | jq -r '
"- **처리된 파일 수:** \(.analysis_summary.processed_files)개",
"- **총 에러 수:** \(.analysis_summary.total_errors)개",
"- **고유 에러 유형:** \(.analysis_summary.unique_error_types)개"
')

## 🔥 상위 에러 유형 분포

$(echo "$analysis_data" | jq -r '.analysis_summary.top_error_types | to_entries[] | "- **\(.key):** \(.value)회"')

## 📋 Top 10 에러 메시지

$(echo "$analysis_data" | jq -r '.top_10_errors[] | "### \(.count)회: \(.message)\n"')

## 📈 에러 유형별 상세 분포

$(echo "$analysis_data" | jq -r '.error_distribution | to_entries[] | "- \(.key): \(.value)회"')

## 🔍 상세 에러 정보

$(echo "$analysis_data" | jq -r '.detailed_errors[0:5][] | "### \(.type): \(.message)\n**소스 파일:** \(.source_file)  \n**라인:** \(.line_number)\n"')

---

**리포트 생성:** MCP-MAP CI 에러 분석기 v1.0
**문의:** CI/CD 팀
EOF

    log_success "Markdown 리포트 생성: $output_file"
}

generate_text_report() {
    local timestamp="$1"
    local output_file="$OUTPUT_DIR/reports/ci_error_report_${timestamp}.txt"

    local analysis_data
    analysis_data=$(cat "$OUTPUT_DIR/error_analysis.json")

    cat > "$output_file" << EOF
==========================================
🚨 MCP-MAP CI/CD 에러 로그 분석 리포트
==========================================

생성 일시: $(date '+%Y-%m-%d %H:%M:%S %Z')
분석 기간: 최근 ${DAYS}일
리포트 형식: 텍스트

📊 분석 요약
----------------------------------------
$(echo "$analysis_data" | jq -r '
"처리된 파일 수: \(.analysis_summary.processed_files)개",
"총 에러 수: \(.analysis_summary.total_errors)개",
"고유 에러 유형: \(.analysis_summary.unique_error_types)개"
')

🔥 상위 에러 유형 분포
----------------------------------------
$(echo "$analysis_data" | jq -r '.analysis_summary.top_error_types | to_entries[] | "\(.key): \(.value)회"')

📋 Top 10 에러 메시지
----------------------------------------
$(echo "$analysis_data" | jq -r '.top_10_errors[] | "\(.count)회: \(.message)"')

==========================================
리포트 생성: MCP-MAP CI 에러 분석기 v1.0
EOF

    log_success "텍스트 리포트 생성: $output_file"
}

# ─────────────────────────────────────────
# 알림 전송
# ─────────────────────────────────────────
send_alerts() {
    if [[ "$ALERT_ENABLED" != "true" ]]; then
        log_info "알림 전송이 비활성화되어 있습니다."
        return 0
    fi

    log_info "에러 분석 결과 알림 전송 중..."

    local analysis_file="$OUTPUT_DIR/error_analysis.json"
    if [[ ! -f "$analysis_file" ]]; then
        log_warn "분석 파일이 없어 알림을 전송할 수 없습니다."
        return 0
    fi

    # 실패율 계산 (워크플로우 실행 정보가 있는 경우)
    local failure_rate=0
    if [[ -f "$OUTPUT_DIR/workflow_runs.json" ]]; then
        local total_runs failed_runs
        total_runs=$(jq '.total_count // 0' "$OUTPUT_DIR/workflow_runs.json")
        failed_runs=$(jq '[.workflow_runs[] | select(.conclusion == "failure")] | length' "$OUTPUT_DIR/workflow_runs.json")

        if [[ "$total_runs" -gt 0 ]]; then
            failure_rate=$(echo "scale=2; $failed_runs * 100 / $total_runs" | bc 2>/dev/null || echo "0")
        fi
    fi

    # notifier.py의 send_ci_error_alert 함수 호출
    if [[ "$DRY_RUN" == "false" ]]; then
        if python3 -c "
import sys
import os
sys.path.append('$PROJECT_ROOT')
from mcp.utils.notifier import send_ci_error_alert_sync
import json

with open('$analysis_file', 'r') as f:
    analysis = json.load(f)

send_ci_error_alert_sync(
    failure_rate=$failure_rate,
    total_errors=analysis['analysis_summary']['total_errors'],
    top_errors=analysis['top_10_errors'][:3],
    period_days=$DAYS
)
"; then
            log_success "알림 전송 완료"
        else
            log_warn "알림 전송 실패"
        fi
    else
        log_debug "[DRY-RUN] 알림 전송 시뮬레이션 (실패율: ${failure_rate}%)"
    fi
}

# ─────────────────────────────────────────
# 정리 작업
# ─────────────────────────────────────────
cleanup() {
    log_debug "정리 작업 수행 중..."

    # 임시 Python 스크립트 제거
    if [[ -f "$OUTPUT_DIR/analyze_errors.py" ]]; then
        rm -f "$OUTPUT_DIR/analyze_errors.py"
    fi

    # 7일 이상 된 리포트 파일 정리
    if [[ "$DRY_RUN" == "false" ]]; then
        find "$OUTPUT_DIR/reports" -name "ci_error_report_*.{json,md,txt}" -type f -mtime +7 -delete 2>/dev/null || true
        find "$OUTPUT_DIR/logs" -name "*.log" -type f -mtime +7 -delete 2>/dev/null || true
    fi

    log_debug "정리 작업 완료"
}

# ─────────────────────────────────────────
# 메인 함수
# ─────────────────────────────────────────
main() {
    local start_time
    start_time=$(date +%s)

    echo -e "${CYAN}"
    cat << 'EOF'
🚨 MCP-MAP CI/CD 에러 로그 분석기 시작
========================================
EOF
    echo -e "${NC}"

    log_info "분석 설정:"
    log_info "  - 분석 기간: ${DAYS}일"
    log_info "  - 출력 형식: ${OUTPUT_FORMAT}"
    log_info "  - 출력 디렉토리: ${OUTPUT_DIR}"
    log_info "  - 드라이런 모드: ${DRY_RUN}"
    log_info "  - 압축 임계치: ${COMPRESS_THRESHOLD}MB"
    log_info "  - 알림 전송: ${ALERT_ENABLED}"

    # 실행 단계
    check_dependencies
    setup_directories

    if fetch_workflow_runs "$DAYS"; then
        download_failed_logs
    else
        log_warn "GitHub API 접근 실패. 로컬 로그 파일만 분석합니다."
    fi

    analyze_error_patterns
    compress_large_logs
    generate_report "$OUTPUT_FORMAT"
    send_alerts
    cleanup

    local end_time duration
    end_time=$(date +%s)
    duration=$((end_time - start_time))

    echo -e "${GREEN}"
    cat << EOF
🎉 CI/CD 에러 분석 완료!
========================================
실행 시간: ${duration}초
출력 디렉토리: ${OUTPUT_DIR}
생성된 리포트: ${OUTPUT_DIR}/reports/
EOF
    echo -e "${NC}"
}

# ─────────────────────────────────────────
# 스크립트 실행
# ─────────────────────────────────────────
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # 인수 파싱
    parse_args "$@"

    # 메인 함수 실행
    main
fi