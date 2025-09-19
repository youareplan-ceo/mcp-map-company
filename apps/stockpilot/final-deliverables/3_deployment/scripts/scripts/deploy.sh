#!/bin/bash
# StockPilot 배포 스크립트
# 개발, 스테이징, 프로덕션 환경별 배포 자동화

set -euo pipefail

# 스크립트 정보
SCRIPT_NAME="StockPilot 배포 스크립트"
VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로깅 함수
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

# 배너 출력
print_banner() {
    echo "=================================================="
    echo "    $SCRIPT_NAME v$VERSION"
    echo "=================================================="
    echo ""
}

# 도움말 출력
show_help() {
    cat << EOF
사용법: $0 [환경] [옵션]

환경:
    development     개발 환경 배포
    staging        스테이징 환경 배포
    production     프로덕션 환경 배포

옵션:
    --build-only   빌드만 수행 (배포 안함)
    --skip-tests   테스트 건너뛰기
    --skip-backup  백업 건너뛰기 (프로덕션에서만)
    --force        강제 배포 (확인 메시지 건너뛰기)
    --docker-tag   Docker 이미지 태그 지정
    --help         이 도움말 표시

예시:
    $0 development
    $0 production --docker-tag v1.2.3
    $0 staging --skip-tests --force

EOF
}

# 환경 변수 로드
load_environment() {
    local env=$1
    local env_file=""
    
    case $env in
        development)
            env_file="$PROJECT_ROOT/.env"
            ;;
        staging)
            env_file="$PROJECT_ROOT/.env.staging"
            ;;
        production)
            env_file="$PROJECT_ROOT/.env.production"
            ;;
        *)
            log_error "지원하지 않는 환경입니다: $env"
            show_help
            exit 1
            ;;
    esac
    
    if [[ -f "$env_file" ]]; then
        log_info "환경 변수 로드: $env_file"
        source "$env_file"
    else
        log_warning "환경 파일을 찾을 수 없습니다: $env_file"
        log_warning "기본값을 사용합니다"
    fi
    
    export DEPLOYMENT_ENV=$env
}

# 시스템 요구사항 확인
check_requirements() {
    log_info "시스템 요구사항 확인 중..."
    
    local missing_tools=()
    
    # 필수 도구들 확인
    command -v docker >/dev/null 2>&1 || missing_tools+=("docker")
    command -v docker-compose >/dev/null 2>&1 || missing_tools+=("docker-compose")
    command -v git >/dev/null 2>&1 || missing_tools+=("git")
    command -v node >/dev/null 2>&1 || missing_tools+=("node")
    command -v python3 >/dev/null 2>&1 || missing_tools+=("python3")
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "다음 도구들이 설치되어 있지 않습니다:"
        for tool in "${missing_tools[@]}"; do
            echo "  - $tool"
        done
        exit 1
    fi
    
    # Docker 데몬 확인
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker 데몬이 실행 중이지 않습니다"
        exit 1
    fi
    
    log_success "시스템 요구사항 확인 완료"
}

# 환경 변수 검증
validate_environment() {
    log_info "환경 변수 검증 중..."
    
    if [[ -f "$SCRIPT_DIR/env_validator.py" ]]; then
        if python3 "$SCRIPT_DIR/env_validator.py"; then
            log_success "환경 변수 검증 완료"
        else
            log_error "환경 변수 검증 실패"
            log_error "env_validator.py 실행 결과를 확인하세요"
            exit 1
        fi
    else
        log_warning "환경 변수 검증 스크립트를 찾을 수 없습니다"
    fi
}

# Git 상태 확인
check_git_status() {
    log_info "Git 저장소 상태 확인 중..."
    
    cd "$PROJECT_ROOT"
    
    # Git 저장소인지 확인
    if ! git rev-parse --git-dir >/dev/null 2>&1; then
        log_warning "Git 저장소가 아닙니다"
        return
    fi
    
    # 커밋되지 않은 변경사항 확인
    if ! git diff-index --quiet HEAD --; then
        if [[ "$FORCE_DEPLOY" != "true" ]]; then
            log_error "커밋되지 않은 변경사항이 있습니다"
            log_error "--force 옵션을 사용하거나 변경사항을 커밋하세요"
            exit 1
        else
            log_warning "커밋되지 않은 변경사항이 있지만 강제 배포 중"
        fi
    fi
    
    # 현재 브랜치와 커밋 정보
    local current_branch=$(git rev-parse --abbrev-ref HEAD)
    local commit_hash=$(git rev-parse --short HEAD)
    
    log_info "현재 브랜치: $current_branch"
    log_info "커밋 해시: $commit_hash"
    
    export GIT_BRANCH="$current_branch"
    export GIT_COMMIT="$commit_hash"
}

# 테스트 실행
run_tests() {
    if [[ "$SKIP_TESTS" == "true" ]]; then
        log_warning "테스트를 건너뜁니다"
        return
    fi
    
    log_info "테스트 실행 중..."
    
    cd "$PROJECT_ROOT"
    
    # 백엔드 테스트
    if [[ -f "backend/requirements-test.txt" ]]; then
        log_info "백엔드 테스트 실행"
        cd backend
        if [[ -d "venv" ]]; then
            source venv/bin/activate
        fi
        
        # 테스트 실행
        if command -v pytest >/dev/null 2>&1; then
            pytest tests/ -v --tb=short
        else
            python -m pytest tests/ -v --tb=short
        fi
        
        cd ..
    fi
    
    # 프론트엔드 테스트
    if [[ -f "frontend/package.json" ]]; then
        log_info "프론트엔드 테스트 실행"
        cd frontend
        npm test -- --watchAll=false --coverage
        cd ..
    fi
    
    log_success "모든 테스트 통과"
}

# 백업 생성 (프로덕션 전용)
create_backup() {
    if [[ "$DEPLOYMENT_ENV" != "production" ]]; then
        return
    fi
    
    if [[ "$SKIP_BACKUP" == "true" ]]; then
        log_warning "백업을 건너뜁니다"
        return
    fi
    
    log_info "프로덕션 백업 생성 중..."
    
    local backup_dir="/var/backups/stockpilot"
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_name="stockpilot_backup_${timestamp}"
    
    # 백업 디렉토리 생성
    sudo mkdir -p "$backup_dir"
    
    # 데이터베이스 백업
    if [[ -n "${DATABASE_URL:-}" ]]; then
        log_info "데이터베이스 백업 중..."
        pg_dump "$DATABASE_URL" | gzip > "$backup_dir/${backup_name}_db.sql.gz"
    fi
    
    # 애플리케이션 파일 백업
    log_info "애플리케이션 파일 백업 중..."
    tar -czf "$backup_dir/${backup_name}_app.tar.gz" \
        --exclude='node_modules' \
        --exclude='venv' \
        --exclude='.git' \
        --exclude='__pycache__' \
        "$PROJECT_ROOT"
    
    log_success "백업 완료: $backup_name"
}

# Docker 이미지 빌드
build_docker_images() {
    log_info "Docker 이미지 빌드 중..."
    
    cd "$PROJECT_ROOT"
    
    local docker_tag="${DOCKER_TAG:-latest}"
    local build_args=(
        "--build-arg" "GIT_COMMIT=${GIT_COMMIT:-unknown}"
        "--build-arg" "BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
        "--build-arg" "ENVIRONMENT=${DEPLOYMENT_ENV}"
    )
    
    # 백엔드 이미지 빌드
    if [[ "$DEPLOYMENT_ENV" == "production" ]]; then
        log_info "프로덕션 백엔드 이미지 빌드"
        docker build -f backend/Dockerfile.prod -t "stockpilot-backend:$docker_tag" "${build_args[@]}" backend/
    else
        log_info "개발용 백엔드 이미지 빌드"
        docker build -f backend/Dockerfile -t "stockpilot-backend:$docker_tag" "${build_args[@]}" backend/
    fi
    
    # 프론트엔드 이미지 빌드 (필요한 경우)
    if [[ -f "frontend/Dockerfile" ]]; then
        log_info "프론트엔드 이미지 빌드"
        docker build -f frontend/Dockerfile -t "stockpilot-frontend:$docker_tag" "${build_args[@]}" frontend/
    fi
    
    log_success "Docker 이미지 빌드 완료"
}

# 보안 스캔 실행 (프로덕션)
security_scan() {
    if [[ "$DEPLOYMENT_ENV" != "production" ]]; then
        return
    fi
    
    log_info "보안 스캔 실행 중..."
    
    # Trivy를 사용한 취약점 스캔 (설치되어 있는 경우)
    if command -v trivy >/dev/null 2>&1; then
        log_info "Docker 이미지 취약점 스캔"
        trivy image "stockpilot-backend:${DOCKER_TAG:-latest}"
        
        # 심각한 취약점이 발견된 경우 배포 중단
        if trivy image --severity HIGH,CRITICAL --exit-code 1 "stockpilot-backend:${DOCKER_TAG:-latest}"; then
            log_success "보안 스캔 통과"
        else
            log_error "심각한 보안 취약점이 발견되었습니다"
            if [[ "$FORCE_DEPLOY" != "true" ]]; then
                exit 1
            else
                log_warning "강제 배포로 인해 계속 진행"
            fi
        fi
    else
        log_warning "Trivy가 설치되어 있지 않습니다. 보안 스캔을 건너뜁니다"
    fi
}

# 서비스 배포
deploy_services() {
    if [[ "$BUILD_ONLY" == "true" ]]; then
        log_info "빌드만 수행합니다. 배포를 건너뜁니다"
        return
    fi
    
    log_info "$DEPLOYMENT_ENV 환경에 서비스 배포 중..."
    
    cd "$PROJECT_ROOT"
    
    # Docker Compose 파일 선택
    local compose_file="docker-compose.yml"
    if [[ -f "docker-compose.$DEPLOYMENT_ENV.yml" ]]; then
        compose_file="docker-compose.$DEPLOYMENT_ENV.yml"
    fi
    
    # 환경에 따른 배포 방식
    case $DEPLOYMENT_ENV in
        development)
            log_info "개발 환경 배포"
            docker-compose -f "$compose_file" up -d --build
            ;;
        staging)
            log_info "스테이징 환경 배포"
            docker-compose -f "$compose_file" up -d --build
            ;;
        production)
            log_info "프로덕션 환경 배포 (제로 다운타임)"
            
            # 기존 서비스 확인
            if docker-compose -f "$compose_file" ps | grep -q "Up"; then
                log_info "롤링 업데이트 수행"
                docker-compose -f "$compose_file" up -d --no-deps --build stockpilot-backend
                
                # 헬스체크 대기
                wait_for_health_check
                
                # 기존 컨테이너 정리
                docker-compose -f "$compose_file" up -d --remove-orphans
            else
                docker-compose -f "$compose_file" up -d --build
            fi
            ;;
    esac
    
    log_success "서비스 배포 완료"
}

# 헬스체크 대기
wait_for_health_check() {
    log_info "헬스체크 대기 중..."
    
    local max_attempts=30
    local attempt=1
    local health_url="${HEALTH_CHECK_URL:-http://localhost:8000/api/v1/system/health}"
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f "$health_url" >/dev/null 2>&1; then
            log_success "헬스체크 통과"
            return 0
        fi
        
        log_info "헬스체크 시도 $attempt/$max_attempts..."
        sleep 10
        ((attempt++))
    done
    
    log_error "헬스체크 실패"
    return 1
}

# 배포 후 검증
post_deploy_verification() {
    if [[ "$BUILD_ONLY" == "true" ]]; then
        return
    fi
    
    log_info "배포 후 검증 중..."
    
    # 서비스 상태 확인
    if ! wait_for_health_check; then
        log_error "배포 후 검증 실패"
        return 1
    fi
    
    # 기본 API 엔드포인트 테스트
    local api_url="${API_BASE_URL:-http://localhost:8000}"
    
    if curl -f "$api_url/api/v1/system/version" >/dev/null 2>&1; then
        log_success "API 엔드포인트 접근 가능"
    else
        log_warning "API 엔드포인트 접근 실패"
    fi
    
    # 로그 확인 (최근 에러)
    if docker-compose logs --tail=50 stockpilot-backend | grep -i error; then
        log_warning "로그에서 에러가 발견되었습니다"
    fi
    
    log_success "배포 후 검증 완료"
}

# 정리 작업
cleanup() {
    log_info "정리 작업 수행 중..."
    
    # 사용하지 않는 Docker 이미지 정리
    docker image prune -f
    
    # 빌드 캐시 정리 (프로덕션에서는 제외)
    if [[ "$DEPLOYMENT_ENV" != "production" ]]; then
        docker builder prune -f
    fi
    
    log_success "정리 작업 완료"
}

# 배포 요약 출력
print_summary() {
    echo ""
    echo "=================================================="
    echo "           배포 완료 요약"
    echo "=================================================="
    echo "환경: $DEPLOYMENT_ENV"
    echo "브랜치: ${GIT_BRANCH:-unknown}"
    echo "커밋: ${GIT_COMMIT:-unknown}"
    echo "Docker 태그: ${DOCKER_TAG:-latest}"
    echo "배포 시간: $(date)"
    echo ""
    
    if [[ "$BUILD_ONLY" == "true" ]]; then
        echo "🔨 빌드만 수행됨"
    else
        echo "🚀 배포 완료"
        echo ""
        echo "접근 URL:"
        case $DEPLOYMENT_ENV in
            development)
                echo "  - API: http://localhost:8000"
                echo "  - Web: http://localhost:3000"
                ;;
            staging)
                echo "  - API: https://staging-api.stockpilot.ai"
                echo "  - Web: https://staging.stockpilot.ai"
                ;;
            production)
                echo "  - API: https://api.stockpilot.ai"
                echo "  - Web: https://stockpilot.ai"
                ;;
        esac
    fi
    
    echo "=================================================="
}

# 메인 실행 함수
main() {
    # 매개변수 파싱
    DEPLOYMENT_ENV=""
    BUILD_ONLY=false
    SKIP_TESTS=false
    SKIP_BACKUP=false
    FORCE_DEPLOY=false
    DOCKER_TAG=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            development|staging|production)
                DEPLOYMENT_ENV="$1"
                shift
                ;;
            --build-only)
                BUILD_ONLY=true
                shift
                ;;
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --skip-backup)
                SKIP_BACKUP=true
                shift
                ;;
            --force)
                FORCE_DEPLOY=true
                shift
                ;;
            --docker-tag)
                DOCKER_TAG="$2"
                shift 2
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "알 수 없는 옵션: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 환경 매개변수 확인
    if [[ -z "$DEPLOYMENT_ENV" ]]; then
        log_error "배포 환경을 지정해야 합니다"
        show_help
        exit 1
    fi
    
    # 배너 출력
    print_banner
    
    # 배포 확인 (프로덕션)
    if [[ "$DEPLOYMENT_ENV" == "production" && "$FORCE_DEPLOY" != "true" ]]; then
        echo -n "프로덕션 환경에 배포하시겠습니까? (y/N): "
        read -r confirmation
        if [[ "$confirmation" != "y" && "$confirmation" != "Y" ]]; then
            log_info "배포가 취소되었습니다"
            exit 0
        fi
    fi
    
    # 배포 단계 실행
    log_info "배포 시작: $DEPLOYMENT_ENV 환경"
    
    check_requirements
    load_environment "$DEPLOYMENT_ENV"
    validate_environment
    check_git_status
    run_tests
    create_backup
    build_docker_images
    security_scan
    deploy_services
    post_deploy_verification
    cleanup
    
    print_summary
    
    log_success "배포가 성공적으로 완료되었습니다! 🎉"
}

# 스크립트 실행
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi