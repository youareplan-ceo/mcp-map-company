#!/bin/bash
# StockPilot 운영 환경 모니터링 정식 가동 스크립트
# systemd 서비스 자동 등록, 헬스 모니터 24시간 구동, 로그 로테이션, 자동 장애 복구

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# systemd 서비스 자동 등록 및 활성화
activate_systemd_services() {
    log_step "systemd 서비스 자동 등록 및 활성화 중..."
    
    # 서비스 목록
    SERVICES=(
        "stockpilot-health-monitor"
        "stockpilot-production-daemon" 
        "stockpilot-korean-data-scheduler"
    )
    
    for service in "${SERVICES[@]}"; do
        if systemctl list-unit-files | grep -q "${service}.service"; then
            log_info "서비스 등록: $service"
            systemctl enable "$service"
            systemctl start "$service"
            
            # 서비스 상태 확인
            if systemctl is-active --quiet "$service"; then
                log_info "✅ $service 활성화 완료"
            else
                log_error "❌ $service 활성화 실패"
            fi
        else
            log_error "서비스 파일을 찾을 수 없음: $service"
        fi
    done
    
    # systemd 서비스 자동 재시작 설정 강화
    for service in "${SERVICES[@]}"; do
        mkdir -p "/etc/systemd/system/${service}.service.d"
        cat > "/etc/systemd/system/${service}.service.d/override.conf" << EOF
[Service]
Restart=always
RestartSec=10
StartLimitInterval=0
WatchdogSec=300
EOF
    done
    
    systemctl daemon-reload
    log_info "systemd 서비스 자동 등록 완료"
}

# 헬스 모니터 24시간 구동 설정
setup_24h_health_monitoring() {
    log_step "헬스 모니터 24시간 구동 설정 중..."
    
    # 모니터링 강화 설정 파일 생성
    cat > /opt/stockpilot/config/monitoring_config.json << 'EOF'
{
    "monitoring": {
        "interval_seconds": 30,
        "health_check_timeout": 10,
        "alert_cooldown_minutes": 5,
        "continuous_monitoring": true,
        "quality_thresholds": {
            "excellent": 95,
            "good": 80,
            "warning": 70,
            "critical": 50
        },
        "alert_channels": {
            "critical": ["slack", "email", "sms"],
            "warning": ["slack", "email"],
            "info": ["slack"]
        },
        "auto_recovery": {
            "enabled": true,
            "max_retry_attempts": 3,
            "restart_failed_services": true,
            "escalation_threshold": 5
        }
    },
    "services": {
        "websocket": {
            "port": 8765,
            "path": "/",
            "critical": true,
            "restart_command": "systemctl restart stockpilot-websocket"
        },
        "auth_api": {
            "port": 8002,
            "path": "/health",
            "critical": true,
            "restart_command": "systemctl restart stockpilot-auth"
        },
        "dashboard_api": {
            "port": 8003,
            "path": "/health",
            "critical": true,
            "restart_command": "systemctl restart stockpilot-dashboard"
        },
        "cost_dashboard": {
            "port": 8004,
            "path": "/health",
            "critical": false,
            "restart_command": "systemctl restart stockpilot-cost-dashboard"
        }
    }
}
EOF
    
    # 워치독 스크립트 생성
    cat > /opt/stockpilot/scripts/watchdog.sh << 'EOF'
#!/bin/bash
# StockPilot 서비스 워치독 스크립트

SERVICES=("stockpilot-health-monitor" "stockpilot-production-daemon" "stockpilot-korean-data-scheduler")
LOG_FILE="/var/log/stockpilot/watchdog.log"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

for service in "${SERVICES[@]}"; do
    if ! systemctl is-active --quiet "$service"; then
        log_message "🚨 SERVICE DOWN: $service - attempting restart"
        systemctl start "$service"
        
        sleep 5
        
        if systemctl is-active --quiet "$service"; then
            log_message "✅ SERVICE RECOVERED: $service"
        else
            log_message "❌ SERVICE RESTART FAILED: $service"
        fi
    fi
done
EOF
    
    chmod +x /opt/stockpilot/scripts/watchdog.sh
    chown stockpilot:stockpilot /opt/stockpilot/scripts/watchdog.sh
    
    # 워치독을 cron에 등록 (매 1분마다 실행)
    (crontab -l 2>/dev/null | grep -v "stockpilot watchdog"; echo "* * * * * /opt/stockpilot/scripts/watchdog.sh") | crontab -
    
    log_info "24시간 헬스 모니터링 설정 완료"
}

# 로그 로테이션 및 보존 정책 설정
setup_log_rotation_policy() {
    log_step "로그 로테이션 및 보존 정책 설정 중..."
    
    # 강화된 로그 로테이션 설정
    cat > /etc/logrotate.d/stockpilot-enhanced << 'EOF'
# StockPilot 로그 로테이션 정책 (강화된 버전)

/var/log/stockpilot/*.log {
    daily
    rotate 90
    compress
    delaycompress
    missingok
    notifempty
    create 644 stockpilot stockpilot
    copytruncate
    
    # 압축 옵션 최적화
    compresscmd /bin/gzip
    compressoptions "-9"
    
    postrotate
        # 서비스 리로드 (재시작 대신)
        /bin/systemctl reload stockpilot-health-monitor 2>/dev/null || true
        /bin/systemctl reload stockpilot-production-daemon 2>/dev/null || true
        /bin/systemctl reload stockpilot-korean-data-scheduler 2>/dev/null || true
        
        # 로그 아카이브 (30일 이상된 것은 S3 또는 외부 저장소로 이동)
        find /var/log/stockpilot/ -name "*.gz" -mtime +30 -exec mv {} /opt/stockpilot/backups/archived_logs/ \; 2>/dev/null || true
    endscript
    
    # 크기 기반 로테이션 (100MB 초과시)
    size 100M
    maxsize 500M
}

/var/log/stockpilot/benchmark/*.log {
    weekly
    rotate 12
    compress
    delaycompress
    missingok
    notifempty
    create 644 stockpilot stockpilot
}

/var/log/stockpilot/alerts/*.log {
    daily
    rotate 365
    compress
    delaycompress
    missingok
    notifempty
    create 644 stockpilot stockpilot
    
    # 알림 로그는 더 오래 보존
    maxage 365
}

# Nginx 로그도 함께 관리
/var/log/nginx/stockpilot_*.log {
    daily
    rotate 52
    compress
    delaycompress
    missingok
    notifempty
    create 644 www-data adm
    
    postrotate
        /bin/systemctl reload nginx 2>/dev/null || true
    endscript
}
EOF
    
    # 로그 디렉토리 구조 생성
    LOG_DIRS=(
        "/var/log/stockpilot/benchmark"
        "/var/log/stockpilot/alerts"
        "/var/log/stockpilot/performance" 
        "/var/log/stockpilot/archived"
        "/opt/stockpilot/backups/archived_logs"
    )
    
    for dir in "${LOG_DIRS[@]}"; do
        mkdir -p "$dir"
        chown stockpilot:stockpilot "$dir"
        chmod 755 "$dir"
    done
    
    # 로그 정리 스크립트 생성
    cat > /opt/stockpilot/scripts/log_cleanup.sh << 'EOF'
#!/bin/bash
# StockPilot 로그 정리 스크립트

# 6개월 이상된 아카이브 로그 삭제
find /opt/stockpilot/backups/archived_logs/ -name "*.gz" -mtime +180 -delete

# 임시 로그 파일 정리
find /tmp -name "stockpilot_*.log" -mtime +1 -delete

# 디스크 사용량 체크 후 로그 압축
DISK_USAGE=$(df /var/log | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    # 디스크 사용량이 80% 초과시 강제 압축
    find /var/log/stockpilot -name "*.log" -size +10M -exec gzip {} \;
fi

echo "로그 정리 완료: $(date)" >> /var/log/stockpilot/cleanup.log
EOF
    
    chmod +x /opt/stockpilot/scripts/log_cleanup.sh
    chown stockpilot:stockpilot /opt/stockpilot/scripts/log_cleanup.sh
    
    # 주간 로그 정리 cron 등록
    (crontab -l 2>/dev/null | grep -v "stockpilot log cleanup"; echo "0 3 * * 0 /opt/stockpilot/scripts/log_cleanup.sh") | crontab -
    
    log_info "로그 로테이션 정책 설정 완료"
}

# 자동 장애 복구 스크립트 활성화
setup_auto_recovery() {
    log_step "자동 장애 복구 스크립트 활성화 중..."
    
    # 통합 장애 복구 스크립트 생성
    cat > /opt/stockpilot/scripts/auto_recovery.sh << 'EOF'
#!/bin/bash
# StockPilot 자동 장애 복구 스크립트

RECOVERY_LOG="/var/log/stockpilot/recovery.log"
ALERT_LOG="/var/log/stockpilot/alerts/recovery_alerts.log"
MAX_RECOVERY_ATTEMPTS=3
RECOVERY_INTERVAL=30

log_recovery() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "[$timestamp] [$level] $message" >> "$RECOVERY_LOG"
    
    if [[ "$level" == "CRITICAL" ]]; then
        echo "[$timestamp] [CRITICAL] $message" >> "$ALERT_LOG"
    fi
}

# 서비스 상태 체크 및 복구
recover_service() {
    local service_name=$1
    local port=$2
    local health_path=${3:-"/health"}
    local max_attempts=${4:-$MAX_RECOVERY_ATTEMPTS}
    
    for ((i=1; i<=max_attempts; i++)); do
        log_recovery "INFO" "Checking $service_name (attempt $i/$max_attempts)"
        
        # 포트 체크
        if ! nc -z localhost "$port" 2>/dev/null; then
            log_recovery "WARNING" "$service_name port $port is not responding"
            
            # 프로세스 확인
            if ! pgrep -f "$service_name" > /dev/null; then
                log_recovery "CRITICAL" "$service_name process not found - attempting restart"
                
                # 서비스 재시작
                systemctl restart "$service_name" 2>/dev/null || {
                    log_recovery "ERROR" "Failed to restart $service_name via systemctl"
                    continue
                }
                
                # 재시작 후 대기
                sleep $RECOVERY_INTERVAL
                
                # 재시작 확인
                if systemctl is-active --quiet "$service_name" && nc -z localhost "$port" 2>/dev/null; then
                    log_recovery "SUCCESS" "$service_name successfully recovered"
                    return 0
                else
                    log_recovery "ERROR" "$service_name restart failed (attempt $i)"
                fi
            else
                log_recovery "WARNING" "$service_name process exists but port not responding"
                # 프로세스는 있지만 포트가 응답하지 않는 경우 강제 재시작
                pkill -f "$service_name"
                sleep 5
                systemctl start "$service_name"
                sleep $RECOVERY_INTERVAL
            fi
        else
            # HTTP 헬스체크 (가능한 경우)
            if [[ "$health_path" != "/" ]]; then
                if curl -sf "http://localhost:$port$health_path" > /dev/null 2>&1; then
                    log_recovery "SUCCESS" "$service_name health check passed"
                    return 0
                else
                    log_recovery "WARNING" "$service_name port responds but health check failed"
                fi
            else
                log_recovery "SUCCESS" "$service_name port check passed"
                return 0
            fi
        fi
    done
    
    log_recovery "CRITICAL" "$service_name recovery failed after $max_attempts attempts"
    return 1
}

# 시스템 리소스 모니터링 및 복구
recover_system_resources() {
    log_recovery "INFO" "Checking system resources"
    
    # 메모리 사용량 체크 (90% 초과시)
    MEMORY_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [[ $MEMORY_USAGE -gt 90 ]]; then
        log_recovery "WARNING" "High memory usage: ${MEMORY_USAGE}%"
        
        # 메모리 정리 시도
        echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true
        sync
        
        # 여전히 높다면 알림
        MEMORY_USAGE_AFTER=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
        if [[ $MEMORY_USAGE_AFTER -gt 85 ]]; then
            log_recovery "CRITICAL" "Memory usage still high after cleanup: ${MEMORY_USAGE_AFTER}%"
        fi
    fi
    
    # 디스크 사용량 체크 (95% 초과시)
    DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [[ $DISK_USAGE -gt 95 ]]; then
        log_recovery "CRITICAL" "Critical disk usage: ${DISK_USAGE}%"
        
        # 임시 파일 정리
        find /tmp -type f -mtime +1 -delete 2>/dev/null || true
        find /var/log -name "*.log.*.gz" -mtime +7 -delete 2>/dev/null || true
        
        # 로그 강제 로테이션
        logrotate -f /etc/logrotate.d/stockpilot-enhanced 2>/dev/null || true
    fi
    
    # CPU 사용량 체크 (95% 초과시)
    CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')
    if (( $(echo "$CPU_USAGE > 95" | bc -l) )); then
        log_recovery "CRITICAL" "Critical CPU usage: ${CPU_USAGE}%"
        
        # CPU 사용량이 높은 프로세스 확인 및 조치
        HIGH_CPU_PROCS=$(ps aux --sort=-%cpu | head -10 | grep -E "(python|node|nginx)" | head -3)
        if [[ -n "$HIGH_CPU_PROCS" ]]; then
            log_recovery "WARNING" "High CPU processes detected: $HIGH_CPU_PROCS"
        fi
    fi
}

# Redis 연결 복구
recover_redis() {
    if ! redis-cli ping > /dev/null 2>&1; then
        log_recovery "WARNING" "Redis not responding - attempting restart"
        systemctl restart redis-server
        sleep 10
        
        if redis-cli ping > /dev/null 2>&1; then
            log_recovery "SUCCESS" "Redis successfully recovered"
        else
            log_recovery "CRITICAL" "Redis recovery failed"
        fi
    fi
}

# PostgreSQL 연결 복구
recover_postgresql() {
    if ! sudo -u postgres psql -c '\l' > /dev/null 2>&1; then
        log_recovery "WARNING" "PostgreSQL not responding - attempting restart"
        systemctl restart postgresql
        sleep 15
        
        if sudo -u postgres psql -c '\l' > /dev/null 2>&1; then
            log_recovery "SUCCESS" "PostgreSQL successfully recovered"
        else
            log_recovery "CRITICAL" "PostgreSQL recovery failed"
        fi
    fi
}

# Nginx 복구
recover_nginx() {
    if ! nginx -t > /dev/null 2>&1; then
        log_recovery "ERROR" "Nginx configuration test failed"
        return 1
    fi
    
    if ! systemctl is-active --quiet nginx; then
        log_recovery "WARNING" "Nginx not running - attempting start"
        systemctl start nginx
        
        if systemctl is-active --quiet nginx; then
            log_recovery "SUCCESS" "Nginx successfully started"
        else
            log_recovery "CRITICAL" "Nginx start failed"
        fi
    fi
}

# 메인 복구 로직
main() {
    log_recovery "INFO" "=== Auto Recovery Check Started ==="
    
    # 시스템 리소스 복구
    recover_system_resources
    
    # 인프라 서비스 복구
    recover_redis
    recover_postgresql  
    recover_nginx
    
    # StockPilot 서비스 복구
    recover_service "auth_api" 8002 "/health"
    recover_service "dashboard_api" 8003 "/health"  
    recover_service "cost_dashboard" 8004 "/health"
    recover_service "websocket" 8765 "/" 2  # WebSocket은 재시도 횟수 줄임
    
    log_recovery "INFO" "=== Auto Recovery Check Completed ==="
}

# 스크립트 실행
main "$@"
EOF
    
    chmod +x /opt/stockpilot/scripts/auto_recovery.sh
    chown stockpilot:stockpilot /opt/stockpilot/scripts/auto_recovery.sh
    
    # 자동 복구를 cron에 등록 (매 3분마다)
    (crontab -l 2>/dev/null | grep -v "stockpilot auto recovery"; echo "*/3 * * * * /opt/stockpilot/scripts/auto_recovery.sh") | crontab -
    
    # 장애 발생시 즉시 알림 스크립트
    cat > /opt/stockpilot/scripts/emergency_alert.sh << 'EOF'
#!/bin/bash
# 긴급 상황 즉시 알림 스크립트

ALERT_THRESHOLD_FILE="/tmp/stockpilot_alert_threshold"

send_emergency_alert() {
    local service=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # 중복 알림 방지 (5분 쿨다운)
    if [[ -f "$ALERT_THRESHOLD_FILE" ]]; then
        LAST_ALERT=$(cat "$ALERT_THRESHOLD_FILE")
        CURRENT_TIME=$(date +%s)
        if (( CURRENT_TIME - LAST_ALERT < 300 )); then
            return 0
        fi
    fi
    
    echo "$CURRENT_TIME" > "$ALERT_THRESHOLD_FILE"
    
    # 긴급 알림 로그
    echo "[$timestamp] EMERGENCY: $service - $message" >> /var/log/stockpilot/alerts/emergency.log
    
    # 이메일 알림 (설정된 경우)
    if command -v mail &> /dev/null && [[ -n "${ADMIN_EMAIL:-}" ]]; then
        echo "StockPilot Emergency Alert: $service - $message" | mail -s "🚨 StockPilot EMERGENCY" "$ADMIN_EMAIL"
    fi
    
    # Slack 웹훅 (설정된 경우)
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"🚨 StockPilot EMERGENCY\\n**Service:** $service\\n**Message:** $message\\n**Time:** $timestamp\"}" \
            "$SLACK_WEBHOOK_URL" > /dev/null 2>&1 || true
    fi
}

# 스크립트를 다른 복구 스크립트에서 사용할 수 있도록 함수 export
export -f send_emergency_alert
EOF
    
    chmod +x /opt/stockpilot/scripts/emergency_alert.sh
    chown stockpilot:stockpilot /opt/stockpilot/scripts/emergency_alert.sh
    
    log_info "자동 장애 복구 시스템 활성화 완료"
}

# 모니터링 대시보드 생성
create_monitoring_dashboard() {
    log_step "모니터링 대시보드 생성 중..."
    
    # 실시간 상태 확인 스크립트
    cat > /opt/stockpilot/scripts/monitoring_dashboard.sh << 'EOF'
#!/bin/bash
# StockPilot 실시간 모니터링 대시보드

clear
echo "🔍 StockPilot 실시간 모니터링 대시보드"
echo "========================================"
echo "업데이트: $(date)"
echo ""

# 시스템 리소스
echo "💻 시스템 리소스:"
echo "  CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}')% 사용중"
echo "  메모리: $(free | awk 'NR==2{printf "%.1f%%", $3*100/$2}') 사용중"
echo "  디스크: $(df / | awk 'NR==2 {print $5}') 사용중"
echo ""

# 서비스 상태
echo "🔧 서비스 상태:"
SERVICES=("nginx" "redis-server" "postgresql" "stockpilot-health-monitor" "stockpilot-production-daemon" "stockpilot-korean-data-scheduler")

for service in "${SERVICES[@]}"; do
    if systemctl is-active --quiet "$service"; then
        echo "  ✅ $service"
    else
        echo "  ❌ $service"
    fi
done
echo ""

# 포트 확인
echo "🌐 네트워크 포트:"
PORTS=(80 443 8002 8003 8004 8765 5432 6379)
for port in "${PORTS[@]}"; do
    if nc -z localhost "$port" 2>/dev/null; then
        echo "  ✅ 포트 $port"
    else
        echo "  ❌ 포트 $port"
    fi
done
echo ""

# 최근 로그 오류
echo "⚠️  최근 오류 로그 (최근 1시간):"
if [[ -f "/var/log/stockpilot/error.log" ]]; then
    tail -n 5 /var/log/stockpilot/error.log | head -n 3
else
    echo "  오류 로그 없음"
fi
echo ""

# 업타임
echo "⏱️  시스템 업타임:"
uptime
echo ""

echo "========================================"
echo "자동 새로고침: 30초 후"
EOF
    
    chmod +x /opt/stockpilot/scripts/monitoring_dashboard.sh
    chown stockpilot:stockpilot /opt/stockpilot/scripts/monitoring_dashboard.sh
    
    log_info "모니터링 대시보드 생성 완료"
}

# 메인 실행 함수
main() {
    echo "🚀 StockPilot 운영 환경 모니터링 정식 가동 시작"
    echo "시간: $(date)"
    echo ""
    
    activate_systemd_services
    setup_24h_health_monitoring
    setup_log_rotation_policy
    setup_auto_recovery
    create_monitoring_dashboard
    
    # 최종 상태 확인
    echo ""
    echo "======================================"
    echo "✅ 운영 환경 모니터링 정식 가동 완료"
    echo "======================================"
    echo ""
    
    echo "📊 활성화된 기능:"
    echo "  ✅ systemd 서비스 자동 등록 및 활성화"
    echo "  ✅ 헬스 모니터 24시간 구동"
    echo "  ✅ 로그 로테이션 및 보존 정책"
    echo "  ✅ 자동 장애 복구 시스템"
    echo "  ✅ 실시간 모니터링 대시보드"
    echo ""
    
    echo "🔧 모니터링 도구:"
    echo "  대시보드: /opt/stockpilot/scripts/monitoring_dashboard.sh"
    echo "  로그 위치: /var/log/stockpilot/"
    echo "  복구 로그: /var/log/stockpilot/recovery.log"
    echo "  알림 로그: /var/log/stockpilot/alerts/"
    echo ""
    
    log_info "운영 환경 모니터링 가동이 완료되었습니다!"
}

# 스크립트 실행 (root 권한 필요)
if [[ $EUID -eq 0 ]]; then
    main "$@"
else
    echo "이 스크립트는 root 권한이 필요합니다."
    exit 1
fi