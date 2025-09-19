#!/bin/bash
# StockPilot AI 클라우드 서버 자동 설정 스크립트
# 작성자: StockPilot Team
# 용도: AWS/GCP/Digital Ocean 서버 자동 설정 및 배포

set -euo pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수들
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 설정 변수들
DOMAIN=""
EMAIL=""
CLOUD_PROVIDER=""
SERVER_TYPE=""
DB_PASSWORD=""
REDIS_PASSWORD=""
JWT_SECRET=""
API_KEYS=""

# 클라우드 제공자 선택 함수
select_cloud_provider() {
    log_info "클라우드 서비스 제공자를 선택합니다..."
    
    echo "1) AWS (Amazon Web Services)"
    echo "2) GCP (Google Cloud Platform)"  
    echo "3) Digital Ocean"
    echo "4) Vultr"
    echo "5) Linode"
    
    read -p "선택 (1-5): " choice
    
    case $choice in
        1) CLOUD_PROVIDER="aws" ;;
        2) CLOUD_PROVIDER="gcp" ;;
        3) CLOUD_PROVIDER="digitalocean" ;;
        4) CLOUD_PROVIDER="vultr" ;;
        5) CLOUD_PROVIDER="linode" ;;
        *) log_error "잘못된 선택입니다."; exit 1 ;;
    esac
    
    log_success "클라우드 제공자: $CLOUD_PROVIDER"
}

# 서버 스펙 선택 함수
select_server_type() {
    log_info "서버 스펙을 선택합니다..."
    
    echo "1) 소형 (2 vCPU, 4GB RAM) - 개발/테스트 환경"
    echo "2) 중형 (4 vCPU, 8GB RAM) - 베타 서비스"
    echo "3) 대형 (8 vCPU, 16GB RAM) - 프로덕션 환경"
    echo "4) 고성능 (16 vCPU, 32GB RAM) - 대용량 처리"
    
    read -p "선택 (1-4): " choice
    
    case $choice in
        1) SERVER_TYPE="small" ;;
        2) SERVER_TYPE="medium" ;;
        3) SERVER_TYPE="large" ;;
        4) SERVER_TYPE="xlarge" ;;
        *) log_error "잘못된 선택입니다."; exit 1 ;;
    esac
    
    log_success "서버 스펙: $SERVER_TYPE"
}

# 도메인 및 이메일 입력 함수
input_domain_email() {
    log_info "도메인 및 이메일 정보를 입력합니다..."
    
    read -p "도메인명 (예: stockpilot.ai): " DOMAIN
    read -p "관리자 이메일: " EMAIL
    
    if [[ -z "$DOMAIN" || -z "$EMAIL" ]]; then
        log_error "도메인과 이메일은 필수입니다."
        exit 1
    fi
    
    log_success "도메인: $DOMAIN, 이메일: $EMAIL"
}

# 보안 설정 함수
generate_secrets() {
    log_info "보안 키들을 생성합니다..."
    
    DB_PASSWORD=$(openssl rand -base64 32)
    REDIS_PASSWORD=$(openssl rand -base64 32)
    JWT_SECRET=$(openssl rand -base64 64)
    
    log_success "보안 키 생성 완료"
}

# Ubuntu 서버 초기 설정
setup_ubuntu_server() {
    log_info "Ubuntu 서버 초기 설정을 시작합니다..."
    
    # 시스템 업데이트
    sudo apt update && sudo apt upgrade -y
    
    # 필수 패키지 설치
    sudo apt install -y \
        curl \
        wget \
        git \
        vim \
        htop \
        ufw \
        fail2ban \
        certbot \
        python3-certbot-nginx \
        nginx \
        postgresql \
        postgresql-contrib \
        redis-server \
        nodejs \
        npm \
        python3 \
        python3-pip \
        python3-venv \
        docker.io \
        docker-compose
    
    # Docker 서비스 시작
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -aG docker $USER
    
    log_success "기본 패키지 설치 완료"
}

# PostgreSQL 설정
setup_postgresql() {
    log_info "PostgreSQL 데이터베이스를 설정합니다..."
    
    sudo -u postgres psql -c "CREATE USER stockpilot WITH ENCRYPTED PASSWORD '$DB_PASSWORD';"
    sudo -u postgres psql -c "CREATE DATABASE stockpilot_db OWNER stockpilot;"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE stockpilot_db TO stockpilot;"
    
    # PostgreSQL 설정 파일 백업 및 수정
    sudo cp /etc/postgresql/*/main/postgresql.conf /etc/postgresql/*/main/postgresql.conf.bak
    sudo cp /etc/postgresql/*/main/pg_hba.conf /etc/postgresql/*/main/pg_hba.conf.bak
    
    # 원격 접속 허용 (보안 설정)
    sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = 'localhost'/" /etc/postgresql/*/main/postgresql.conf
    
    sudo systemctl restart postgresql
    
    log_success "PostgreSQL 설정 완료"
}

# Redis 설정
setup_redis() {
    log_info "Redis 캐시 서버를 설정합니다..."
    
    # Redis 설정 파일 백업
    sudo cp /etc/redis/redis.conf /etc/redis/redis.conf.bak
    
    # 패스워드 설정
    sudo sed -i "s/# requirepass foobared/requirepass $REDIS_PASSWORD/" /etc/redis/redis.conf
    
    # 보안 설정
    sudo sed -i "s/bind 127.0.0.1/bind 127.0.0.1/" /etc/redis/redis.conf
    
    sudo systemctl restart redis-server
    sudo systemctl enable redis-server
    
    log_success "Redis 설정 완료"
}

# Nginx 설정
setup_nginx() {
    log_info "Nginx 웹서버를 설정합니다..."
    
    # 기본 사이트 비활성화
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # StockPilot 전용 Nginx 설정 생성
    cat << EOF | sudo tee /etc/nginx/sites-available/stockpilot
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    
    # ACME Challenge for Let's Encrypt
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    # Redirect to HTTPS
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;
    
    # SSL 설정 (Let's Encrypt로 자동 생성됨)
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    
    # SSL 보안 설정
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # 보안 헤더
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
    add_header Referrer-Policy strict-origin-when-cross-origin;
    
    # Gzip 압축
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    
    # 프론트엔드 (React)
    location / {
        root /var/www/stockpilot/frontend/build;
        try_files \$uri \$uri/ /index.html;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # API 백엔드 프록시
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket 지원
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 타임아웃 설정
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # WebSocket 전용 엔드포인트
    location /ws/ {
        proxy_pass http://127.0.0.1:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # 로그 파일
    access_log /var/log/nginx/stockpilot.access.log;
    error_log /var/log/nginx/stockpilot.error.log;
}
EOF
    
    # 사이트 활성화
    sudo ln -s /etc/nginx/sites-available/stockpilot /etc/nginx/sites-enabled/
    
    # Nginx 설정 테스트
    sudo nginx -t
    
    sudo systemctl restart nginx
    sudo systemctl enable nginx
    
    log_success "Nginx 설정 완료"
}

# SSL 인증서 설정 (Let's Encrypt)
setup_ssl() {
    log_info "SSL 인증서를 설정합니다..."
    
    # certbot 디렉토리 생성
    sudo mkdir -p /var/www/certbot
    
    # SSL 인증서 발급
    sudo certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email $EMAIL \
        --agree-tos \
        --no-eff-email \
        -d $DOMAIN \
        -d www.$DOMAIN
    
    # 자동 갱신 설정
    echo "0 12 * * * /usr/bin/certbot renew --quiet && systemctl reload nginx" | sudo crontab -
    
    log_success "SSL 인증서 설정 완료"
}

# 방화벽 설정
setup_firewall() {
    log_info "방화벽을 설정합니다..."
    
    # UFW 초기화
    sudo ufw --force reset
    
    # 기본 정책 설정
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    
    # 필요한 포트 허용
    sudo ufw allow ssh
    sudo ufw allow 'Nginx Full'
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    
    # 관리 포트 (필요시)
    # sudo ufw allow from YOUR_IP to any port 5432  # PostgreSQL
    # sudo ufw allow from YOUR_IP to any port 6379  # Redis
    
    # 방화벽 활성화
    sudo ufw --force enable
    
    # Fail2ban 설정
    sudo systemctl enable fail2ban
    sudo systemctl start fail2ban
    
    log_success "방화벽 설정 완료"
}

# 애플리케이션 배포
deploy_application() {
    log_info "StockPilot 애플리케이션을 배포합니다..."
    
    # 애플리케이션 디렉토리 생성
    sudo mkdir -p /var/www/stockpilot
    sudo chown $USER:$USER /var/www/stockpilot
    
    # Git 저장소 클론 (실제 저장소 URL로 변경 필요)
    cd /var/www/stockpilot
    # git clone https://github.com/your-username/stockpilot-ai.git .
    
    # 임시로 현재 디렉토리 복사 (개발 환경)
    cp -r /Users/youareplan/stockpilot-ai/* /var/www/stockpilot/ 2>/dev/null || true
    
    # 프로덕션 환경 변수 생성
    cat << EOF > /var/www/stockpilot/backend/.env.production
# StockPilot AI 프로덕션 환경 변수
DATABASE_URL=postgresql://stockpilot:$DB_PASSWORD@localhost/stockpilot_db
REDIS_URL=redis://:$REDIS_PASSWORD@localhost:6379/0
JWT_SECRET_KEY=$JWT_SECRET
SECRET_KEY=$JWT_SECRET

# 서버 설정
DEBUG=False
ENVIRONMENT=production
HOST=0.0.0.0
PORT=8000

# 도메인 설정
FRONTEND_URL=https://$DOMAIN
BACKEND_URL=https://$DOMAIN/api

# 외부 API 키들 (실제 키로 교체 필요)
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
FINNHUB_API_KEY=your_finnhub_key
NEWS_API_KEY=your_news_api_key

# 알림 설정
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# 보안 설정
CORS_ORIGINS=["https://$DOMAIN", "https://www.$DOMAIN"]
TRUSTED_HOSTS=["$DOMAIN", "www.$DOMAIN"]

# 로깅 설정
LOG_LEVEL=INFO
LOG_FILE=/var/log/stockpilot/app.log

# 세션 설정
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=lax
EOF
    
    # 로그 디렉토리 생성
    sudo mkdir -p /var/log/stockpilot
    sudo chown $USER:$USER /var/log/stockpilot
    
    log_success "애플리케이션 배포 완료"
}

# Python 백엔드 설정
setup_backend() {
    log_info "Python 백엔드를 설정합니다..."
    
    cd /var/www/stockpilot/backend
    
    # 가상 환경 생성
    python3 -m venv venv
    source venv/bin/activate
    
    # 의존성 설치
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # 데이터베이스 마이그레이션
    python manage.py migrate || echo "마이그레이션 스크립트가 없습니다."
    
    # systemd 서비스 파일 생성
    cat << EOF | sudo tee /etc/systemd/system/stockpilot-backend.service
[Unit]
Description=StockPilot AI Backend
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=$USER
WorkingDirectory=/var/www/stockpilot/backend
Environment=PATH=/var/www/stockpilot/backend/venv/bin
ExecStart=/var/www/stockpilot/backend/venv/bin/python main.py
EnvironmentFile=/var/www/stockpilot/backend/.env.production
Restart=always
RestartSec=10

# 보안 설정
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/www/stockpilot /var/log/stockpilot

[Install]
WantedBy=multi-user.target
EOF
    
    # 서비스 활성화
    sudo systemctl daemon-reload
    sudo systemctl enable stockpilot-backend
    sudo systemctl start stockpilot-backend
    
    log_success "Python 백엔드 설정 완료"
}

# React 프론트엔드 빌드
build_frontend() {
    log_info "React 프론트엔드를 빌드합니다..."
    
    cd /var/www/stockpilot/frontend
    
    # Node.js 의존성 설치
    npm install
    
    # 프로덕션 빌드
    REACT_APP_API_URL=https://$DOMAIN/api npm run build
    
    # 빌드 파일 권한 설정
    sudo chown -R www-data:www-data build/
    
    log_success "React 프론트엔드 빌드 완료"
}

# 헬스체크 스크립트 생성
create_health_check() {
    log_info "헬스체크 스크립트를 생성합니다..."
    
    cat << 'EOF' > /var/www/stockpilot/scripts/health_check.sh
#!/bin/bash
# StockPilot AI 헬스체크 스크립트

check_service() {
    local service_name=$1
    local url=$2
    
    if systemctl is-active --quiet $service_name; then
        echo "✅ $service_name is running"
    else
        echo "❌ $service_name is not running"
        return 1
    fi
    
    if [[ -n "$url" ]]; then
        if curl -sf "$url" > /dev/null; then
            echo "✅ $service_name HTTP check passed"
        else
            echo "❌ $service_name HTTP check failed"
            return 1
        fi
    fi
}

echo "🔍 StockPilot AI 시스템 헬스체크 시작..."
echo "=================================="

# 시스템 서비스 체크
check_service "nginx" "http://localhost"
check_service "postgresql"
check_service "redis-server"
check_service "stockpilot-backend" "http://localhost:8000/health"

# 디스크 사용량 체크
disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $disk_usage -lt 80 ]; then
    echo "✅ 디스크 사용량: ${disk_usage}%"
else
    echo "⚠️ 디스크 사용량 높음: ${disk_usage}%"
fi

# 메모리 사용량 체크
mem_usage=$(free | grep Mem | awk '{printf("%.0f", $3/$2 * 100.0)}')
if [ $mem_usage -lt 80 ]; then
    echo "✅ 메모리 사용량: ${mem_usage}%"
else
    echo "⚠️ 메모리 사용량 높음: ${mem_usage}%"
fi

# CPU 로드 체크
cpu_load=$(uptime | awk -F'load average:' '{ print $2 }' | cut -d, -f1 | xargs)
echo "📊 CPU 로드: $cpu_load"

echo "=================================="
echo "🏁 헬스체크 완료"
EOF
    
    chmod +x /var/www/stockpilot/scripts/health_check.sh
    
    # 정기 헬스체크 cron 작업 추가
    (crontab -l 2>/dev/null; echo "*/5 * * * * /var/www/stockpilot/scripts/health_check.sh >> /var/log/stockpilot/health.log 2>&1") | crontab -
    
    log_success "헬스체크 스크립트 생성 완료"
}

# 백업 스크립트 설정
setup_backup() {
    log_info "자동 백업 시스템을 설정합니다..."
    
    mkdir -p /var/backups/stockpilot
    
    cat << EOF > /var/www/stockpilot/scripts/backup.sh
#!/bin/bash
# StockPilot AI 자동 백업 스크립트

BACKUP_DIR="/var/backups/stockpilot"
DATE=\$(date +%Y%m%d_%H%M%S)

# 데이터베이스 백업
pg_dump -U stockpilot stockpilot_db > "\$BACKUP_DIR/db_backup_\$DATE.sql"

# 애플리케이션 파일 백업
tar -czf "\$BACKUP_DIR/app_backup_\$DATE.tar.gz" /var/www/stockpilot --exclude="*/venv/*" --exclude="*/node_modules/*"

# 설정 파일 백업
tar -czf "\$BACKUP_DIR/config_backup_\$DATE.tar.gz" /etc/nginx/sites-available/stockpilot /var/www/stockpilot/backend/.env.production

# 오래된 백업 파일 삭제 (7일 이상)
find \$BACKUP_DIR -name "*.sql" -mtime +7 -delete
find \$BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "백업 완료: \$DATE"
EOF
    
    chmod +x /var/www/stockpilot/scripts/backup.sh
    
    # 일일 백업 cron 작업 추가
    (crontab -l 2>/dev/null; echo "0 2 * * * /var/www/stockpilot/scripts/backup.sh >> /var/log/stockpilot/backup.log 2>&1") | crontab -
    
    log_success "백업 시스템 설정 완료"
}

# 메인 실행 함수
main() {
    log_info "🚀 StockPilot AI 클라우드 서버 설정을 시작합니다!"
    
    # 사용자 입력 받기
    select_cloud_provider
    select_server_type  
    input_domain_email
    generate_secrets
    
    log_info "설정 정보 확인:"
    echo "- 클라우드: $CLOUD_PROVIDER"
    echo "- 서버 스펙: $SERVER_TYPE"
    echo "- 도메인: $DOMAIN"
    echo "- 이메일: $EMAIL"
    
    read -p "계속 진행하시겠습니까? (y/N): " confirm
    if [[ $confirm != [yY] ]]; then
        log_error "설정이 취소되었습니다."
        exit 1
    fi
    
    # 서버 설정 단계별 실행
    setup_ubuntu_server
    setup_postgresql
    setup_redis
    setup_firewall
    setup_nginx
    
    # SSL은 도메인이 실제로 서버를 가리킬 때만 실행
    log_warning "도메인이 이 서버를 가리키고 있는지 확인 후 SSL 설정을 진행합니다."
    read -p "도메인 설정이 완료되었나요? (y/N): " ssl_ready
    if [[ $ssl_ready == [yY] ]]; then
        setup_ssl
    else
        log_warning "SSL 설정을 건너뜁니다. 나중에 수동으로 실행하세요: sudo certbot --nginx -d $DOMAIN"
    fi
    
    # 애플리케이션 배포
    deploy_application
    setup_backend
    build_frontend
    
    # 모니터링 및 백업 설정
    create_health_check
    setup_backup
    
    log_success "🎉 StockPilot AI 서버 설정이 완료되었습니다!"
    echo ""
    echo "======================================="
    echo "📋 설정 완료 정보"
    echo "======================================="
    echo "🌐 웹사이트: https://$DOMAIN"
    echo "🔧 API 엔드포인트: https://$DOMAIN/api"
    echo "📊 헬스체크: /var/www/stockpilot/scripts/health_check.sh"
    echo "💾 백업 위치: /var/backups/stockpilot"
    echo "📝 로그 위치: /var/log/stockpilot"
    echo ""
    echo "🔐 생성된 패스워드들:"
    echo "- 데이터베이스: $DB_PASSWORD"
    echo "- Redis: $REDIS_PASSWORD"
    echo "- JWT 시크릿: $JWT_SECRET"
    echo ""
    echo "⚠️  중요: 이 패스워드들을 안전한 곳에 보관하세요!"
    echo "======================================="
}

# 스크립트가 직접 실행되었을 때만 main 함수 호출
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi