#!/bin/sh
#
# 프론트엔드 헬스체크 스크립트
# Docker 컨테이너의 상태를 확인합니다.
#

set -e

# 설정
HEALTH_CHECK_URL="http://localhost/health"
TIMEOUT=10
MAX_RETRIES=3

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo "${RED}[ERROR]${NC} $1"
}

# 메인 헬스체크 함수
health_check() {
    local retries=0
    
    while [ $retries -lt $MAX_RETRIES ]; do
        log_info "헬스체크 시도 $(($retries + 1))/$MAX_RETRIES"
        
        # HTTP 상태 코드 확인
        if command -v curl >/dev/null 2>&1; then
            response=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT "$HEALTH_CHECK_URL" 2>/dev/null)
            
            if [ "$response" = "200" ]; then
                log_info "✅ 헬스체크 성공 (HTTP $response)"
                return 0
            else
                log_warn "❌ 헬스체크 실패 (HTTP $response)"
            fi
        else
            # curl이 없는 경우 wget 사용
            if command -v wget >/dev/null 2>&1; then
                if wget --quiet --timeout=$TIMEOUT --tries=1 --spider "$HEALTH_CHECK_URL" 2>/dev/null; then
                    log_info "✅ 헬스체크 성공 (wget)"
                    return 0
                else
                    log_warn "❌ 헬스체크 실패 (wget)"
                fi
            else
                log_error "curl 또는 wget이 설치되어 있지 않습니다"
                return 1
            fi
        fi
        
        retries=$(($retries + 1))
        
        if [ $retries -lt $MAX_RETRIES ]; then
            log_info "$(($MAX_RETRIES - $retries))초 후 재시도..."
            sleep 2
        fi
    done
    
    log_error "헬스체크 실패: 최대 재시도 횟수 초과"
    return 1
}

# Nginx 프로세스 확인
check_nginx_process() {
    if pgrep nginx >/dev/null 2>&1; then
        log_info "✅ Nginx 프로세스 실행 중"
        return 0
    else
        log_error "❌ Nginx 프로세스를 찾을 수 없습니다"
        return 1
    fi
}

# 정적 파일 존재 확인
check_static_files() {
    local html_dir="/usr/share/nginx/html"
    
    if [ -f "$html_dir/index.html" ]; then
        log_info "✅ index.html 파일 존재"
        
        # 파일 크기 확인 (최소 1KB)
        file_size=$(wc -c < "$html_dir/index.html")
        if [ $file_size -gt 1024 ]; then
            log_info "✅ index.html 파일 크기 정상 (${file_size} bytes)"
            return 0
        else
            log_warn "⚠️ index.html 파일이 너무 작습니다 (${file_size} bytes)"
            return 1
        fi
    else
        log_error "❌ index.html 파일을 찾을 수 없습니다"
        return 1
    fi
}

# 메모리 사용량 확인
check_memory_usage() {
    if command -v free >/dev/null 2>&1; then
        memory_usage=$(free | grep Mem | awk '{printf "%.1f", ($3/$2) * 100.0}')
        log_info "메모리 사용률: ${memory_usage}%"
        
        # 90% 이상이면 경고
        if awk "BEGIN {exit !($memory_usage > 90)}"; then
            log_warn "⚠️ 메모리 사용률이 높습니다 (${memory_usage}%)"
        fi
    else
        log_info "메모리 정보를 확인할 수 없습니다"
    fi
}

# 디스크 사용량 확인
check_disk_usage() {
    if command -v df >/dev/null 2>&1; then
        disk_usage=$(df /usr/share/nginx/html | tail -1 | awk '{print $5}' | sed 's/%//')
        log_info "디스크 사용률: ${disk_usage}%"
        
        # 90% 이상이면 경고
        if [ "$disk_usage" -gt 90 ]; then
            log_warn "⚠️ 디스크 사용률이 높습니다 (${disk_usage}%)"
        fi
    else
        log_info "디스크 정보를 확인할 수 없습니다"
    fi
}

# 메인 실행
main() {
    log_info "🏥 StockPilot 프론트엔드 헬스체크 시작"
    
    # 기본 검사들
    check_nginx_process || exit 1
    check_static_files || exit 1
    
    # HTTP 헬스체크
    health_check || exit 1
    
    # 추가 시스템 정보
    check_memory_usage
    check_disk_usage
    
    log_info "🎉 모든 헬스체크 통과!"
    exit 0
}

# 스크립트 실행
main "$@"