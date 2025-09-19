#!/bin/bash
# StockPilot 프로덕션 환경 자동 설정 스크립트
# SSL 인증서, 로드 밸런서, 백업, 모니터링 시스템을 모두 설정

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로깅 함수
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 루트 권한 확인
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "이 스크립트는 root 권한으로 실행되어야 합니다."
        exit 1
    fi
}

# 시스템 요구사항 확인
check_requirements() {
    log_step "시스템 요구사항 확인 중..."
    
    # Ubuntu/Debian 확인
    if ! command -v apt-get &> /dev/null; then
        log_error "Ubuntu/Debian 시스템이 필요합니다."
        exit 1
    fi
    
    # 메모리 확인 (최소 4GB)
    MEM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    MEM_GB=$((MEM_KB / 1024 / 1024))
    
    if [[ $MEM_GB -lt 4 ]]; then
        log_warn "메모리가 4GB 미만입니다. 성능 문제가 발생할 수 있습니다."
    fi
    
    # 디스크 용량 확인 (최소 20GB)
    DISK_AVAIL=$(df / | awk 'NR==2 {print $4}')
    DISK_AVAIL_GB=$((DISK_AVAIL / 1024 / 1024))
    
    if [[ $DISK_AVAIL_GB -lt 20 ]]; then
        log_error "루트 파티션에 최소 20GB의 여유 공간이 필요합니다."
        exit 1
    fi
    
    log_info "시스템 요구사항 확인 완료 (메모리: ${MEM_GB}GB, 디스크: ${DISK_AVAIL_GB}GB)"
}

# 필수 패키지 설치
install_dependencies() {
    log_step "필수 패키지 설치 중..."
    
    # 패키지 목록 업데이트
    apt-get update -qq
    
    # 필수 패키지 설치
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        nginx \
        redis-server \
        postgresql \
        postgresql-contrib \
        certbot \
        python3-certbot-nginx \
        supervisor \
        logrotate \
        fail2ban \
        ufw \
        htop \
        curl \
        wget \
        git \
        unzip \
        cron \
        rsync \
        sqlite3
    
    log_info "필수 패키지 설치 완료"
}

# 사용자 및 그룹 생성
create_user() {
    log_step "stockpilot 사용자 및 그룹 생성 중..."
    
    # 그룹 생성
    if ! getent group stockpilot > /dev/null; then
        groupadd --system stockpilot
        log_info "stockpilot 그룹 생성됨"
    fi
    
    # 사용자 생성
    if ! getent passwd stockpilot > /dev/null; then
        useradd --system --gid stockpilot --home-dir /opt/stockpilot \
                --shell /bin/bash --create-home stockpilot
        log_info "stockpilot 사용자 생성됨"
    fi
    
    # 권한 설정
    usermod -a -G www-data stockpilot
}

# 디렉토리 구조 생성
create_directories() {
    log_step "디렉토리 구조 생성 중..."
    
    # 주요 디렉토리들
    DIRECTORIES=(
        "/opt/stockpilot"
        "/opt/stockpilot/backend"
        "/opt/stockpilot/frontend"
        "/opt/stockpilot/data"
        "/opt/stockpilot/backups"
        "/opt/stockpilot/ssl"
        "/opt/stockpilot/config"
        "/opt/stockpilot/logs"
        "/var/log/stockpilot"
        "/var/lib/stockpilot"
        "/etc/stockpilot"
    )
    
    for dir in "${DIRECTORIES[@]}"; do
        mkdir -p "$dir"
        chown stockpilot:stockpilot "$dir"
        chmod 755 "$dir"
    done
    
    # 특별한 권한이 필요한 디렉토리들
    chmod 700 /opt/stockpilot/ssl
    chmod 700 /opt/stockpilot/backups
    
    log_info "디렉토리 구조 생성 완료"
}

# 애플리케이션 코드 배포
deploy_application() {
    log_step "애플리케이션 코드 배포 중..."
    
    # 현재 스크립트의 위치에서 프로젝트 루트 찾기
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
    
    # 백엔드 코드 복사
    if [[ -d "$PROJECT_ROOT/backend" ]]; then
        rsync -av --exclude='__pycache__' --exclude='*.pyc' \
              "$PROJECT_ROOT/backend/" "/opt/stockpilot/backend/"
        chown -R stockpilot:stockpilot /opt/stockpilot/backend/
        log_info "백엔드 코드 배포 완료"
    else
        log_warn "백엔드 코드 디렉토리를 찾을 수 없음"
    fi
    
    # 프론트엔드 코드 복사 (빌드된 것이 있다면)
    if [[ -d "$PROJECT_ROOT/frontend/build" ]]; then
        rsync -av "$PROJECT_ROOT/frontend/build/" "/opt/stockpilot/frontend/"
        chown -R stockpilot:stockpilot /opt/stockpilot/frontend/
        log_info "프론트엔드 코드 배포 완료"
    else
        log_warn "빌드된 프론트엔드 코드를 찾을 수 없음"
    fi
}

# Python 가상환경 설정
setup_python_env() {
    log_step "Python 가상환경 설정 중..."
    
    # 가상환경 생성
    sudo -u stockpilot python3 -m venv /opt/stockpilot/backend/venv
    
    # pip 업그레이드
    sudo -u stockpilot /opt/stockpilot/backend/venv/bin/pip install --upgrade pip
    
    # requirements.txt가 있으면 설치
    if [[ -f "/opt/stockpilot/backend/requirements.txt" ]]; then
        sudo -u stockpilot /opt/stockpilot/backend/venv/bin/pip install \
            -r /opt/stockpilot/backend/requirements.txt
        log_info "Python 패키지 설치 완료"
    else
        log_warn "requirements.txt를 찾을 수 없음. 수동으로 패키지를 설치해야 합니다."
    fi
}

# 데이터베이스 설정
setup_database() {
    log_step "데이터베이스 설정 중..."
    
    # PostgreSQL 서비스 시작
    systemctl enable postgresql
    systemctl start postgresql
    
    # stockpilot 데이터베이스 사용자 생성
    sudo -u postgres psql -tc "SELECT 1 FROM pg_user WHERE usename = 'stockpilot'" | grep -q 1 || \
        sudo -u postgres createuser --createdb stockpilot
    
    # 데이터베이스 생성
    sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = 'stockpilot'" | grep -q 1 || \
        sudo -u postgres createdb -O stockpilot stockpilot
    
    # 패스워드 설정
    DB_PASSWORD=$(openssl rand -base64 32)
    sudo -u postgres psql -c "ALTER USER stockpilot PASSWORD '$DB_PASSWORD';"
    
    # 패스워드를 환경 파일에 저장
    echo "DB_PASSWORD=$DB_PASSWORD" >> /opt/stockpilot/.env.production
    chown stockpilot:stockpilot /opt/stockpilot/.env.production
    chmod 600 /opt/stockpilot/.env.production
    
    log_info "PostgreSQL 데이터베이스 설정 완료"
}

# Redis 설정
setup_redis() {
    log_step "Redis 설정 중..."
    
    # Redis 설정 파일 수정
    REDIS_CONF="/etc/redis/redis.conf"
    
    # Redis 패스워드 생성
    REDIS_PASSWORD=$(openssl rand -base64 32)
    
    # Redis 설정 백업
    cp $REDIS_CONF $REDIS_CONF.backup
    
    # 보안 설정 적용
    sed -i "s/^# requirepass .*/requirepass $REDIS_PASSWORD/" $REDIS_CONF
    sed -i 's/^bind 127.0.0.1.*/bind 127.0.0.1/' $REDIS_CONF
    sed -i 's/^# maxmemory .*/maxmemory 256mb/' $REDIS_CONF
    sed -i 's/^# maxmemory-policy .*/maxmemory-policy allkeys-lru/' $REDIS_CONF
    
    # 패스워드를 환경 파일에 저장
    echo "REDIS_PASSWORD=$REDIS_PASSWORD" >> /opt/stockpilot/.env.production
    
    # Redis 서비스 재시작
    systemctl enable redis-server
    systemctl restart redis-server
    
    log_info "Redis 설정 완료"
}

# Nginx 설정
setup_nginx() {
    log_step "Nginx 설정 중..."
    
    # 기본 사이트 비활성화
    rm -f /etc/nginx/sites-enabled/default
    
    # StockPilot Nginx 설정 생성
    cat > /etc/nginx/sites-available/stockpilot << 'EOF'
upstream stockpilot_websocket {
    server 127.0.0.1:8765;
    keepalive 32;
}

upstream stockpilot_api {
    server 127.0.0.1:8002 weight=3;
    server 127.0.0.1:8003 weight=3;
    server 127.0.0.1:8004 weight=2;
    keepalive 32;
}

server {
    listen 80;
    listen [::]:80;
    server_name _;
    
    # HTTP에서 HTTPS로 리다이렉트
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name _;
    
    # SSL 설정 (Let's Encrypt 사용 시 자동으로 설정됨)
    ssl_certificate /opt/stockpilot/ssl/stockpilot.crt;
    ssl_certificate_key /opt/stockpilot/ssl/stockpilot.key;
    
    # 보안 헤더
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # 로깅
    access_log /var/log/nginx/stockpilot_access.log;
    error_log /var/log/nginx/stockpilot_error.log;
    
    # 프론트엔드 (React)
    location / {
        root /opt/stockpilot/frontend;
        index index.html;
        try_files $uri $uri/ /index.html;
    }
    
    # WebSocket
    location /ws/ {
        proxy_pass http://stockpilot_websocket;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # API 엔드포인트
    location /api/ {
        proxy_pass http://stockpilot_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 타임아웃 설정
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
    
    # 정적 파일 캐싱
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        root /opt/stockpilot/frontend;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # 헬스 체크
    location /nginx-health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF
    
    # 사이트 활성화
    ln -sf /etc/nginx/sites-available/stockpilot /etc/nginx/sites-enabled/
    
    # Nginx 설정 테스트
    if nginx -t; then
        systemctl enable nginx
        systemctl restart nginx
        log_info "Nginx 설정 완료"
    else
        log_error "Nginx 설정 테스트 실패"
        return 1
    fi
}

# 방화벽 설정
setup_firewall() {
    log_step "방화벽 설정 중..."
    
    # UFW 초기화
    ufw --force reset
    
    # 기본 정책 설정
    ufw default deny incoming
    ufw default allow outgoing
    
    # 필수 포트 허용
    ufw allow ssh
    ufw allow http
    ufw allow https
    
    # 방화벽 활성화
    ufw --force enable
    
    log_info "방화벽 설정 완료"
}

# Systemd 서비스 설정
setup_systemd_services() {
    log_step "Systemd 서비스 설정 중..."
    
    # 현재 스크립트 위치에서 systemd 파일들을 찾기
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
    SYSTEMD_DIR="$PROJECT_ROOT/systemd"
    
    if [[ -d "$SYSTEMD_DIR" ]]; then
        # 모든 .service 파일을 복사
        for service_file in "$SYSTEMD_DIR"/*.service; do
            if [[ -f "$service_file" ]]; then
                service_name=$(basename "$service_file")
                cp "$service_file" "/etc/systemd/system/"
                log_info "서비스 파일 설치: $service_name"
            fi
        done
        
        # Systemd 데몬 리로드
        systemctl daemon-reload
        
        # 서비스들 활성화
        systemctl enable stockpilot-health-monitor.service
        systemctl enable stockpilot-production-daemon.service
        systemctl enable stockpilot-korean-data-scheduler.service
        
        log_info "Systemd 서비스 설정 완료"
    else
        log_warn "Systemd 서비스 파일 디렉토리를 찾을 수 없음"
    fi
}

# 로그 로테이션 설정
setup_log_rotation() {
    log_step "로그 로테이션 설정 중..."
    
    cat > /etc/logrotate.d/stockpilot << 'EOF'
/var/log/stockpilot/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 stockpilot stockpilot
    postrotate
        /bin/systemctl reload stockpilot-* 2>/dev/null || true
    endscript
}

/var/log/nginx/stockpilot_*.log {
    daily
    rotate 30
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
    
    log_info "로그 로테이션 설정 완료"
}

# SSL 인증서 설정 (Let's Encrypt)
setup_ssl() {
    log_step "SSL 인증서 설정 중..."
    
    # 도메인 입력 받기 (대화형이 아닌 경우 기본값 사용)
    if [[ -t 0 ]]; then
        read -p "도메인 이름을 입력하세요 (예: stockpilot.ai): " DOMAIN
        read -p "이메일 주소를 입력하세요: " EMAIL
    else
        DOMAIN="localhost"
        EMAIL="admin@localhost"
        log_warn "대화형 모드가 아니므로 기본값 사용: $DOMAIN"
    fi
    
    if [[ "$DOMAIN" != "localhost" ]] && [[ -n "$EMAIL" ]]; then
        # Let's Encrypt 인증서 발급
        certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email "$EMAIL"
        
        # 자동 갱신 설정
        crontab -l 2>/dev/null | grep -v "certbot renew" | crontab -
        (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -
        
        log_info "SSL 인증서 설정 완료: $DOMAIN"
    else
        # 자체 서명된 인증서 생성 (개발용)
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout /opt/stockpilot/ssl/stockpilot.key \
            -out /opt/stockpilot/ssl/stockpilot.crt \
            -subj "/C=KR/ST=Seoul/L=Seoul/O=StockPilot/OU=IT Department/CN=localhost"
        
        chown stockpilot:stockpilot /opt/stockpilot/ssl/*
        chmod 600 /opt/stockpilot/ssl/*
        
        log_warn "자체 서명된 SSL 인증서 생성됨 (개발용)"
    fi
}

# 환경 변수 파일 생성
create_env_file() {
    log_step "환경 변수 파일 생성 중..."
    
    # JWT 시크릿 키 생성
    JWT_SECRET=$(openssl rand -base64 64)
    OPENAI_API_KEY_PLACEHOLDER="your-openai-api-key-here"
    
    cat > /opt/stockpilot/.env.production << EOF
# StockPilot Production Environment Variables

# 데이터베이스 설정
DB_HOST=localhost
DB_PORT=5432
DB_NAME=stockpilot
DB_USER=stockpilot
# DB_PASSWORD는 위에서 자동 생성됨

# Redis 설정
REDIS_HOST=localhost
REDIS_PORT=6379
# REDIS_PASSWORD는 위에서 자동 생성됨

# JWT 설정
JWT_SECRET_KEY=$JWT_SECRET
JWT_ALGORITHM=HS256

# OpenAI API (수동 설정 필요)
OPENAI_API_KEY=$OPENAI_API_KEY_PLACEHOLDER

# 외부 API 키들 (선택사항)
POLYGON_API_KEY=
ALPHA_VANTAGE_API_KEY=

# 알림 설정 (선택사항)
SLACK_WEBHOOK_URL=
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=$(openssl rand -base64 16)

# 환경 설정
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG=false
EOF
    
    chown stockpilot:stockpilot /opt/stockpilot/.env.production
    chmod 600 /opt/stockpilot/.env.production
    
    log_info "환경 변수 파일 생성 완료"
}

# 백업 스크립트 생성
create_backup_script() {
    log_step "백업 스크립트 생성 중..."
    
    cat > /opt/stockpilot/scripts/backup.sh << 'EOF'
#!/bin/bash
# StockPilot 자동 백업 스크립트

BACKUP_DIR="/opt/stockpilot/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# 데이터베이스 백업
sudo -u postgres pg_dump stockpilot | gzip > "$BACKUP_DIR/database_$TIMESTAMP.sql.gz"

# 애플리케이션 데이터 백업
tar -czf "$BACKUP_DIR/data_$TIMESTAMP.tar.gz" /opt/stockpilot/data/

# 설정 파일 백업
tar -czf "$BACKUP_DIR/config_$TIMESTAMP.tar.gz" /opt/stockpilot/config/ /etc/stockpilot/

# 7일 이상된 백업 파일 삭제
find "$BACKUP_DIR" -name "*.gz" -mtime +7 -delete

echo "백업 완료: $TIMESTAMP"
EOF
    
    chmod +x /opt/stockpilot/scripts/backup.sh
    chown stockpilot:stockpilot /opt/stockpilot/scripts/backup.sh
    
    # Cron 작업 추가 (매일 새벽 2시)
    (crontab -l 2>/dev/null | grep -v "stockpilot backup"; echo "0 2 * * * /opt/stockpilot/scripts/backup.sh") | crontab -
    
    log_info "백업 스크립트 생성 완료"
}

# 헬스 체크 스크립트 생성
create_health_check_script() {
    log_step "헬스 체크 스크립트 생성 중..."
    
    cat > /opt/stockpilot/scripts/health_check.sh << 'EOF'
#!/bin/bash
# StockPilot 헬스 체크 스크립트

check_service() {
    local service_name=$1
    local url=$2
    local expected_status=${3:-200}
    
    if curl -sf -o /dev/null -w "%{http_code}" "$url" | grep -q "$expected_status"; then
        echo "✅ $service_name: OK"
        return 0
    else
        echo "❌ $service_name: FAILED"
        return 1
    fi
}

echo "🔍 StockPilot 헬스 체크 시작 ($(date))"

# 시스템 서비스 확인
systemctl is-active --quiet nginx && echo "✅ Nginx: OK" || echo "❌ Nginx: FAILED"
systemctl is-active --quiet redis-server && echo "✅ Redis: OK" || echo "❌ Redis: FAILED"
systemctl is-active --quiet postgresql && echo "✅ PostgreSQL: OK" || echo "❌ PostgreSQL: FAILED"

# 애플리케이션 서비스 확인
check_service "Auth API" "http://localhost:8002/health"
check_service "Dashboard API" "http://localhost:8003/health"
check_service "Cost Dashboard API" "http://localhost:8004/health"
check_service "Nginx Frontend" "http://localhost/nginx-health"

# 디스크 사용량 체크
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    echo "⚠️ 디스크 사용량 높음: ${DISK_USAGE}%"
else
    echo "✅ 디스크 사용량: ${DISK_USAGE}%"
fi

# 메모리 사용량 체크
MEM_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
if [ "$MEM_USAGE" -gt 90 ]; then
    echo "⚠️ 메모리 사용량 높음: ${MEM_USAGE}%"
else
    echo "✅ 메모리 사용량: ${MEM_USAGE}%"
fi

echo "🔍 헬스 체크 완료"
EOF
    
    chmod +x /opt/stockpilot/scripts/health_check.sh
    chown stockpilot:stockpilot /opt/stockpilot/scripts/health_check.sh
    
    log_info "헬스 체크 스크립트 생성 완료"
}

# 서비스 시작
start_services() {
    log_step "StockPilot 서비스 시작 중..."
    
    # 핵심 인프라 서비스 시작
    systemctl start postgresql
    systemctl start redis-server
    systemctl start nginx
    
    # StockPilot 서비스들 시작
    if systemctl list-unit-files | grep -q stockpilot-health-monitor.service; then
        systemctl start stockpilot-health-monitor
    fi
    
    if systemctl list-unit-files | grep -q stockpilot-production-daemon.service; then
        systemctl start stockpilot-production-daemon
    fi
    
    if systemctl list-unit-files | grep -q stockpilot-korean-data-scheduler.service; then
        systemctl start stockpilot-korean-data-scheduler
    fi
    
    log_info "서비스 시작 완료"
}

# 최종 상태 확인 및 보고
final_status_check() {
    log_step "최종 상태 확인 중..."
    
    sleep 5  # 서비스 시작 대기
    
    echo ""
    echo "======================================"
    echo "🚀 StockPilot 프로덕션 환경 설정 완료"
    echo "======================================"
    echo ""
    
    # 서비스 상태 확인
    echo "📊 서비스 상태:"
    systemctl is-active postgresql && echo "  ✅ PostgreSQL" || echo "  ❌ PostgreSQL"
    systemctl is-active redis-server && echo "  ✅ Redis" || echo "  ❌ Redis"
    systemctl is-active nginx && echo "  ✅ Nginx" || echo "  ❌ Nginx"
    
    # 포트 확인
    echo ""
    echo "🌐 포트 상태:"
    ss -tlnp | grep :80 > /dev/null && echo "  ✅ HTTP (80)" || echo "  ❌ HTTP (80)"
    ss -tlnp | grep :443 > /dev/null && echo "  ✅ HTTPS (443)" || echo "  ❌ HTTPS (443)"
    ss -tlnp | grep :5432 > /dev/null && echo "  ✅ PostgreSQL (5432)" || echo "  ❌ PostgreSQL (5432)"
    ss -tlnp | grep :6379 > /dev/null && echo "  ✅ Redis (6379)" || echo "  ❌ Redis (6379)"
    
    echo ""
    echo "📁 중요 경로:"
    echo "  애플리케이션: /opt/stockpilot/"
    echo "  설정 파일: /opt/stockpilot/.env.production"
    echo "  로그 파일: /var/log/stockpilot/"
    echo "  백업: /opt/stockpilot/backups/"
    echo "  SSL 인증서: /opt/stockpilot/ssl/"
    echo ""
    
    echo "🔧 다음 단계:"
    echo "  1. OpenAI API 키 설정: vi /opt/stockpilot/.env.production"
    echo "  2. 헬스 체크 실행: /opt/stockpilot/scripts/health_check.sh"
    echo "  3. 서비스 로그 확인: journalctl -u stockpilot-*"
    echo "  4. 웹사이트 접속 테스트: https://$(hostname -f)"
    echo ""
    
    log_info "설정이 완료되었습니다!"
}

# 메인 함수
main() {
    echo "🚀 StockPilot 프로덕션 환경 자동 설정 시작"
    echo "시간: $(date)"
    echo ""
    
    check_root
    check_requirements
    install_dependencies
    create_user
    create_directories
    deploy_application
    setup_python_env
    setup_database
    setup_redis
    setup_nginx
    setup_firewall
    setup_systemd_services
    setup_log_rotation
    setup_ssl
    create_env_file
    create_backup_script
    create_health_check_script
    start_services
    final_status_check
    
    echo "🎉 StockPilot 프로덕션 환경 설정 완료!"
}

# 스크립트 실행
main "$@"