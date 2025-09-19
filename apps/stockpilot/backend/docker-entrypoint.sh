#!/bin/bash
# StockPilot Docker 엔트리포인트 스크립트
# 컨테이너 시작시 초기화 작업 수행

set -euo pipefail

echo "🚀 StockPilot Backend 컨테이너 시작"

# 환경 변수 검증
check_env_vars() {
    echo "🔍 환경 변수 검증 중..."
    
    required_vars=(
        "DATABASE_URL"
        "REDIS_URL"
        "JWT_SECRET_KEY"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            echo "❌ 필수 환경 변수가 설정되지 않음: $var"
            exit 1
        fi
    done
    
    echo "✅ 환경 변수 검증 완료"
}

# 데이터베이스 연결 대기
wait_for_database() {
    echo "⏳ 데이터베이스 연결 대기 중..."
    
    # DATABASE_URL에서 호스트 추출
    DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\).*/\1/p')
    DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    DB_PORT=${DB_PORT:-5432}
    
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if pg_isready -h "$DB_HOST" -p "$DB_PORT" > /dev/null 2>&1; then
            echo "✅ 데이터베이스 연결 확인"
            return 0
        fi
        
        echo "데이터베이스 연결 시도 $attempt/$max_attempts..."
        sleep 2
        ((attempt++))
    done
    
    echo "❌ 데이터베이스 연결 실패"
    exit 1
}

# Redis 연결 대기
wait_for_redis() {
    echo "⏳ Redis 연결 대기 중..."
    
    # REDIS_URL에서 호스트와 포트 추출
    REDIS_HOST=$(echo $REDIS_URL | sed -n 's/redis:\/\/\([^:]*\).*/\1/p')
    REDIS_PORT=$(echo $REDIS_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    REDIS_PORT=${REDIS_PORT:-6379}
    
    max_attempts=15
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping > /dev/null 2>&1; then
            echo "✅ Redis 연결 확인"
            return 0
        fi
        
        echo "Redis 연결 시도 $attempt/$max_attempts..."
        sleep 1
        ((attempt++))
    done
    
    echo "❌ Redis 연결 실패"
    exit 1
}

# 데이터베이스 마이그레이션
run_migrations() {
    echo "📊 데이터베이스 마이그레이션 실행 중..."
    
    # Alembic 마이그레이션 실행 (있는 경우)
    if [ -f "alembic.ini" ]; then
        alembic upgrade head
        echo "✅ 데이터베이스 마이그레이션 완료"
    else
        echo "ℹ️ 마이그레이션 파일이 없습니다"
    fi
}

# 초기 데이터 설정
setup_initial_data() {
    echo "🔧 초기 데이터 설정 중..."
    
    # 초기 데이터 스크립트 실행 (있는 경우)
    if [ -f "scripts/init_data.py" ]; then
        python scripts/init_data.py
        echo "✅ 초기 데이터 설정 완료"
    else
        echo "ℹ️ 초기 데이터 스크립트가 없습니다"
    fi
}

# 헬스체크 엔드포인트 대기
wait_for_health() {
    echo "🏥 헬스체크 엔드포인트 대기 중..."
    
    max_attempts=30
    attempt=1
    
    # 백그라운드에서 애플리케이션 시작
    "$@" &
    app_pid=$!
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:8000/api/v1/system/health > /dev/null 2>&1; then
            echo "✅ 애플리케이션 정상 시작"
            wait $app_pid
            return 0
        fi
        
        # 프로세스가 종료되었는지 확인
        if ! kill -0 $app_pid 2>/dev/null; then
            echo "❌ 애플리케이션 시작 실패"
            exit 1
        fi
        
        echo "헬스체크 시도 $attempt/$max_attempts..."
        sleep 2
        ((attempt++))
    done
    
    echo "❌ 헬스체크 실패"
    kill $app_pid 2>/dev/null || true
    exit 1
}

# 시그널 핸들러 설정
handle_signal() {
    echo "📡 종료 신호 수신, 정상 종료 중..."
    if [ -n "${app_pid:-}" ]; then
        kill -TERM $app_pid 2>/dev/null || true
        wait $app_pid 2>/dev/null || true
    fi
    exit 0
}

trap handle_signal SIGTERM SIGINT

# 메인 실행 로직
main() {
    echo "🏁 StockPilot Backend 초기화 시작"
    
    # 환경에 따른 다른 초기화
    if [ "${ENVIRONMENT:-production}" = "development" ]; then
        echo "🛠️ 개발 환경 모드"
        # 개발 환경 전용 설정
    else
        echo "🚀 프로덕션 환경 모드"
        # 프로덕션 환경 전용 설정
        
        # 보안 검증
        if [ "${JWT_SECRET_KEY:-}" = "default_secret" ] || [ ${#JWT_SECRET_KEY} -lt 32 ]; then
            echo "⚠️ 경고: JWT_SECRET_KEY가 안전하지 않습니다"
        fi
    fi
    
    check_env_vars
    wait_for_database
    wait_for_redis
    run_migrations
    setup_initial_data
    
    echo "✅ 초기화 완료, 애플리케이션 시작"
    
    # 헬스체크와 함께 애플리케이션 시작
    if [ "${1:-}" = "uvicorn" ]; then
        # 프로덕션 모드: 헬스체크 포함
        wait_for_health
    else
        # 기타 명령어는 직접 실행
        exec "$@"
    fi
}

# 스크립트 실행
main "$@"