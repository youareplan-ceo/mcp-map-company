#!/bin/bash
# StockPilot 프로덕션 배포 스크립트
# 멀티 서비스 오케스트레이션 자동 배포

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
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

# 스크립트 시작
echo "🚀 StockPilot 프로덕션 배포 시작"
echo "=" * 50

# 1. 환경 확인
log_info "환경 확인 중..."

# Docker 설치 확인
if ! command -v docker &> /dev/null; then
    log_error "Docker가 설치되지 않았습니다."
    exit 1
fi

# Docker Compose 설치 확인
if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose가 설치되지 않았습니다."
    exit 1
fi

log_success "Docker 환경 확인 완료"

# 2. 기존 컨테이너 정리
log_info "기존 컨테이너 정리 중..."
docker-compose -f docker-compose.production.yml down --remove-orphans || true
docker system prune -f || true
log_success "컨테이너 정리 완료"

# 3. 환경 변수 파일 확인
log_info "환경 변수 파일 확인 중..."
if [ ! -f .env.production ]; then
    log_error ".env.production 파일이 없습니다."
    log_info "템플릿을 복사하여 설정해주세요."
    exit 1
fi

# 중요한 환경 변수들 확인
source .env.production
if [[ -z "$POSTGRES_PASSWORD" || "$POSTGRES_PASSWORD" == "change_this_strong_password_123!" ]]; then
    log_warning "POSTGRES_PASSWORD를 실제 값으로 변경해주세요."
fi

if [[ -z "$JWT_SECRET_KEY" || "$JWT_SECRET_KEY" == "change_this_jwt_secret_key_very_long_and_secure_789!" ]]; then
    log_warning "JWT_SECRET_KEY를 실제 값으로 변경해주세요."
fi

if [[ -z "$OPENAI_API_KEY" || "$OPENAI_API_KEY" == "sk-your-openai-api-key-here" ]]; then
    log_warning "OPENAI_API_KEY를 실제 값으로 설정해주세요."
fi

log_success "환경 변수 확인 완료"

# 4. 데이터 디렉토리 생성
log_info "데이터 디렉토리 생성 중..."
sudo mkdir -p /opt/stockpilot/data/{postgres,redis,prometheus,grafana}
sudo mkdir -p /opt/stockpilot/logs/{nginx,backend}
sudo chown -R $USER:$USER /opt/stockpilot/
log_success "데이터 디렉토리 생성 완료"

# 5. SSL 인증서 생성 (자체 서명)
log_info "SSL 인증서 확인 중..."
if [ ! -f "nginx/ssl/stockpilot.ai.crt" ]; then
    log_info "SSL 인증서 생성 중..."
    chmod +x scripts/generate_ssl_cert.sh
    ./scripts/generate_ssl_cert.sh
    log_success "SSL 인증서 생성 완료"
else
    log_success "SSL 인증서 이미 존재"
fi

# 6. 네트워크 생성
log_info "Docker 네트워크 생성 중..."
docker network create stockpilot_network || log_warning "네트워크가 이미 존재합니다."

# 7. 프로덕션 이미지 빌드
log_info "프로덕션 이미지 빌드 중..."
docker-compose -f docker-compose.production.yml build --no-cache
log_success "이미지 빌드 완료"

# 8. 서비스 시작
log_info "프로덕션 서비스 시작 중..."
docker-compose -f docker-compose.production.yml up -d

# 9. 서비스 헬스체크
log_info "서비스 헬스체크 수행 중..."
sleep 30  # 서비스 시작 대기

# WebSocket 서버 체크
if curl -f http://localhost:8765 &> /dev/null; then
    log_success "WebSocket 서버 (8765) 정상 작동"
else
    log_error "WebSocket 서버 (8765) 연결 실패"
fi

# Auth API 체크
if curl -f http://localhost:8002/health &> /dev/null; then
    log_success "Auth API (8002) 정상 작동"
else
    log_error "Auth API (8002) 연결 실패"
fi

# Dashboard API 체크
if curl -f http://localhost:8003/health &> /dev/null; then
    log_success "Dashboard API (8003) 정상 작동"
else
    log_error "Dashboard API (8003) 연결 실패"
fi

# Nginx 체크
if curl -f http://localhost:80/health &> /dev/null; then
    log_success "Nginx (80) 정상 작동"
else
    log_error "Nginx (80) 연결 실패"
fi

# 10. 배포 완료 정보 출력
echo ""
echo "🎉 StockPilot 프로덕션 배포 완료!"
echo "=" * 50
echo ""
echo "📋 서비스 접속 정보:"
echo "  🌐 웹사이트: https://localhost (또는 도메인)"
echo "  📊 Grafana: http://localhost:3000"
echo "  🔍 Prometheus: http://localhost:9090"
echo ""
echo "🔧 관리 명령어:"
echo "  서비스 상태: docker-compose -f docker-compose.production.yml ps"
echo "  로그 확인: docker-compose -f docker-compose.production.yml logs -f [서비스명]"
echo "  서비스 재시작: docker-compose -f docker-compose.production.yml restart [서비스명]"
echo "  서비스 중지: docker-compose -f docker-compose.production.yml down"
echo ""
echo "📝 다음 단계:"
echo "  1. DNS 설정: 도메인을 서버 IP로 연결"
echo "  2. Let's Encrypt 설정: 실제 SSL 인증서 적용"
echo "  3. 모니터링 설정: Grafana 대시보드 구성"
echo "  4. 백업 설정: 데이터베이스 자동 백업 구성"
echo ""
echo "⚠️  보안 주의사항:"
echo "  - .env.production 파일의 모든 기본 비밀번호를 변경하세요"
echo "  - 방화벽 설정으로 필요한 포트만 개방하세요"
echo "  - 정기적인 보안 업데이트를 수행하세요"
echo ""
log_success "배포 스크립트 실행 완료"