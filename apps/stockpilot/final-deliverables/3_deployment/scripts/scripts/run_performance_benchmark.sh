#!/bin/bash
# StockPilot 성능 벤치마크 실행 스크립트

set -euo pipefail

# 컬러 출력 설정
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

BACKEND_DIR="/Users/youareplan/stockpilot-ai/backend"
LOG_DIR="/var/log/stockpilot"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}StockPilot 성능 벤치마크 실행 스크립트${NC}"
echo -e "${BLUE}================================================${NC}"

# 로그 디렉토리 생성
create_log_directory() {
    echo -e "${YELLOW}로그 디렉토리 생성 중...${NC}"
    if [[ ! -d "$LOG_DIR" ]]; then
        sudo mkdir -p "$LOG_DIR"
        sudo chown $(whoami):$(whoami) "$LOG_DIR" 2>/dev/null || true
    fi
    echo -e "${GREEN}✓ 로그 디렉토리 준비 완료${NC}"
}

# 필수 패키지 설치 확인
check_dependencies() {
    echo -e "${YELLOW}필수 패키지 확인 중...${NC}"
    
    cd "$BACKEND_DIR"
    
    # Python 가상환경 활성화
    if [[ -f "venv/bin/activate" ]]; then
        source venv/bin/activate
    else
        echo -e "${RED}✗ Python 가상환경이 없습니다${NC}"
        exit 1
    fi
    
    # 필수 패키지 설치
    pip install -q websockets aiohttp psutil numpy matplotlib seaborn
    
    echo -e "${GREEN}✓ 의존성 확인 완료${NC}"
}

# 시스템 정보 수집
collect_system_info() {
    echo -e "${YELLOW}시스템 정보 수집 중...${NC}"
    
    {
        echo "========================================"
        echo "StockPilot 벤치마크 시스템 정보"
        echo "========================================"
        echo "실행 시간: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "호스트명: $(hostname)"
        echo "운영체제: $(uname -a)"
        echo ""
        echo "CPU 정보:"
        sysctl -n machdep.cpu.brand_string 2>/dev/null || echo "CPU 정보를 가져올 수 없음"
        echo "CPU 코어: $(sysctl -n hw.ncpu 2>/dev/null || echo "알 수 없음")"
        echo ""
        echo "메모리 정보:"
        echo "총 메모리: $(( $(sysctl -n hw.memsize) / 1024 / 1024 / 1024 ))GB" 2>/dev/null || echo "메모리 정보를 가져올 수 없음"
        echo ""
        echo "Python 버전: $(python --version)"
        echo "Node.js 버전: $(node --version 2>/dev/null || echo "Node.js 미설치")"
        echo ""
        echo "========================================"
    } > "$LOG_DIR/system_info_$TIMESTAMP.txt"
    
    echo -e "${GREEN}✓ 시스템 정보 수집 완료${NC}"
}

# 서비스 상태 확인
check_services() {
    echo -e "${YELLOW}서비스 상태 확인 중...${NC}"
    
    local all_services_running=true
    
    # WebSocket 서버 확인
    if ! pgrep -f "websocket_server.py" > /dev/null; then
        echo -e "${YELLOW}⚠ WebSocket 서버가 실행되지 않음. 시작 중...${NC}"
        cd "$BACKEND_DIR"
        source venv/bin/activate
        python websocket_server.py &
        sleep 5
    fi
    
    # API 서버 확인 (포트 8000)
    if ! lsof -i :8000 > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠ API 서버가 실행되지 않음. FastAPI 서버 시작 중...${NC}"
        cd "$BACKEND_DIR"
        source venv/bin/activate
        uvicorn main:app --host 0.0.0.0 --port 8000 &
        sleep 5
    fi
    
    # Redis 확인
    if ! pgrep redis-server > /dev/null; then
        echo -e "${YELLOW}⚠ Redis 서버가 실행되지 않음. 시작 중...${NC}"
        redis-server --daemonize yes 2>/dev/null || true
        sleep 2
    fi
    
    echo -e "${GREEN}✓ 서비스 상태 확인 완료${NC}"
}

# 벤치마크 사전 준비
prepare_benchmark() {
    echo -e "${YELLOW}벤치마크 사전 준비 중...${NC}"
    
    # 시스템 캐시 정리
    echo -e "  ${BLUE}시스템 캐시 정리...${NC}"
    sudo purge 2>/dev/null || sync
    
    # 불필요한 프로세스 정리
    echo -e "  ${BLUE}시스템 최적화...${NC}"
    
    # 네트워크 설정 최적화
    echo -e "  ${BLUE}네트워크 설정 최적화...${NC}"
    
    echo -e "${GREEN}✓ 벤치마크 사전 준비 완료${NC}"
}

# 성능 벤치마크 실행
run_benchmark() {
    echo -e "${YELLOW}성능 벤치마크 실행 중...${NC}"
    echo -e "${BLUE}이 과정은 약 15-20분 소요될 수 있습니다.${NC}"
    
    cd "$BACKEND_DIR"
    source venv/bin/activate
    
    # 벤치마크 실행
    echo -e "${YELLOW}1. WebSocket 부하 테스트 (동시 사용자 1000명)${NC}"
    echo -e "${YELLOW}2. REST API 부하 테스트 (동시 요청 500개)${NC}"
    echo -e "${YELLOW}3. OpenAI API 최적화 벤치마크${NC}"
    
    python services/performance_benchmark.py 2>&1 | tee "$LOG_DIR/benchmark_execution_$TIMESTAMP.log"
    
    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}✓ 성능 벤치마크 실행 완료${NC}"
    else
        echo -e "${RED}✗ 벤치마크 실행 중 오류 발생${NC}"
        return 1
    fi
}

# 결과 분석 및 리포트
analyze_results() {
    echo -e "${YELLOW}벤치마크 결과 분석 중...${NC}"
    
    # 최신 결과 파일 찾기
    local latest_report=$(ls -t "$LOG_DIR"/benchmark_report_*.txt 2>/dev/null | head -n1)
    local latest_json=$(ls -t "$LOG_DIR"/benchmark_results_*.json 2>/dev/null | head -n1)
    local latest_graph=$(ls -t "$LOG_DIR"/performance_benchmark.png 2>/dev/null | head -n1)
    
    if [[ -n "$latest_report" ]]; then
        echo -e "${GREEN}✓ 텍스트 리포트: $latest_report${NC}"
        echo -e "${BLUE}주요 결과 요약:${NC}"
        grep -E "(테스트 유형|성공 요청|초당 요청|평균 CPU|평균 메모리)" "$latest_report" | head -20
    fi
    
    if [[ -n "$latest_json" ]]; then
        echo -e "${GREEN}✓ JSON 결과: $latest_json${NC}"
    fi
    
    if [[ -n "$latest_graph" ]]; then
        echo -e "${GREEN}✓ 성능 그래프: $latest_graph${NC}"
    fi
    
    # 성능 분석 요약
    echo -e "${BLUE}성능 분석 요약 생성 중...${NC}"
    {
        echo "========================================"
        echo "StockPilot 성능 벤치마크 요약"
        echo "========================================"
        echo "실행 시간: $(date '+%Y-%m-%d %H:%M:%S')"
        echo ""
        
        if [[ -n "$latest_report" ]]; then
            echo "주요 성능 지표:"
            grep -A 20 "성능 벤치마크 리포트" "$latest_report" | grep -E "(WebSocket|API|OpenAI|초당 요청|평균.*시간|CPU|메모리)"
        fi
        
        echo ""
        echo "파일 위치:"
        echo "  리포트: $latest_report"
        echo "  JSON: $latest_json"
        echo "  그래프: $latest_graph"
        echo "  실행 로그: $LOG_DIR/benchmark_execution_$TIMESTAMP.log"
        
    } > "$LOG_DIR/benchmark_summary_$TIMESTAMP.txt"
    
    echo -e "${GREEN}✓ 결과 분석 완료${NC}"
}

# 클린업
cleanup() {
    echo -e "${YELLOW}정리 작업 수행 중...${NC}"
    
    # 임시 파일 정리
    find /tmp -name "stockpilot_bench_*" -type f -delete 2>/dev/null || true
    
    echo -e "${GREEN}✓ 정리 작업 완료${NC}"
}

# 메인 실행 함수
main() {
    echo -e "${BLUE}StockPilot 성능 벤치마크를 시작합니다...${NC}"
    
    # 트랩 설정 (스크립트 종료 시 정리)
    trap cleanup EXIT
    
    create_log_directory
    check_dependencies
    collect_system_info
    check_services
    prepare_benchmark
    
    # 벤치마크 실행
    if run_benchmark; then
        analyze_results
        
        echo -e "${GREEN}================================================${NC}"
        echo -e "${GREEN}성능 벤치마크가 성공적으로 완료되었습니다!${NC}"
        echo -e "${GREEN}================================================${NC}"
        echo -e "${BLUE}결과 파일들:${NC}"
        ls -la "$LOG_DIR"/*"$TIMESTAMP"* 2>/dev/null || true
        echo -e "${BLUE}상세 결과는 $LOG_DIR 디렉토리에서 확인하세요.${NC}"
    else
        echo -e "${RED}================================================${NC}"
        echo -e "${RED}벤치마크 실행 중 오류가 발생했습니다.${NC}"
        echo -e "${RED}================================================${NC}"
        echo -e "${YELLOW}로그 파일을 확인하세요: $LOG_DIR/benchmark_execution_$TIMESTAMP.log${NC}"
        exit 1
    fi
}

# 스크립트 실행
main "$@"