#!/bin/bash
# =============================================================================
# 워커 재시작 훅 스크립트 (Worker Restart Hook Script)
# =============================================================================
# 목적: 워커 재시작 모의 (로그만 기록)
# Purpose: Simulate worker restart operations (logging only)
#
# 주의사항:
# - 이 스크립트는 실제 워커 재시작을 수행하지 않습니다
# - 시뮬레이션 모드로 동작하며 가이드 메시지만 출력합니다
# - 실제 워커 재시작은 CI 플랫폼의 관리 API를 사용해야 합니다
#
# 작성자: CI/CD 자동화 팀
# 버전: 1.0.0
# 최종 수정: 2025-09-21
# =============================================================================

set -euo pipefail

# 색상 코드 (터미널 출력용)
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly PURPLE='\033[0;35m'
readonly NC='\033[0m' # No Color

# 로깅 함수
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    case "$level" in
        "INFO")
            echo -e "${GREEN}[INFO]${NC} ${timestamp} - $message" >&2
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} ${timestamp} - $message" >&2
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} ${timestamp} - $message" >&2
            ;;
        "GUIDE")
            echo -e "${CYAN}[가이드]${NC} ${timestamp} - $message" >&2
            ;;
        "SIM")
            echo -e "${PURPLE}[시뮬레이션]${NC} ${timestamp} - $message" >&2
            ;;
        *)
            echo -e "${BLUE}[${level}]${NC} ${timestamp} - $message" >&2
            ;;
    esac
}

# 워커 상태 시뮬레이션 함수
simulate_worker_status() {
    log_message "SIM" "워커 상태 조회 중..."
    sleep 1

    echo "🔍 현재 워커 상태 (시뮬레이션):"
    echo "================================"
    echo "  📍 워커 ID: worker-node-001"
    echo "  📊 상태: UNHEALTHY"
    echo "  💾 메모리 사용률: 95%"
    echo "  🔥 CPU 사용률: 90%"
    echo "  🕐 가동 시간: 48h 32m"
    echo "  ❌ 최근 실패: 3건"
    echo
}

# 워커 재시작 시뮬레이션 함수
simulate_worker_restart() {
    log_message "SIM" "워커 재시작 프로세스 시작..."

    echo "🔄 워커 재시작 단계 (시뮬레이션):"
    echo "================================"

    # 단계별 시뮬레이션
    log_message "SIM" "1단계: 현재 작업 완료 대기..."
    sleep 1
    echo "  ✅ 진행 중인 빌드 작업 완료 대기"

    log_message "SIM" "2단계: 워커 graceful shutdown..."
    sleep 1
    echo "  ✅ 워커 프로세스 정상 종료"

    log_message "SIM" "3단계: 리소스 정리..."
    sleep 1
    echo "  ✅ 임시 파일 및 메모리 정리"

    log_message "SIM" "4단계: 워커 프로세스 재시작..."
    sleep 2
    echo "  ✅ 새 워커 인스턴스 시작"

    log_message "SIM" "5단계: 헬스체크 수행..."
    sleep 1
    echo "  ✅ 워커 상태 확인 완료"

    echo
    log_message "INFO" "워커 재시작 시뮬레이션 완료!"
}

# 워커 타입별 가이드 제공 함수
provide_worker_guides() {
    local error_data="$1"

    log_message "GUIDE" "CI 플랫폼별 워커 재시작 가이드:"
    echo

    echo "📖 GitHub Actions Self-hosted Runners:"
    echo "   # 러너 서비스 재시작"
    echo "   sudo systemctl restart actions.runner.*"
    echo "   # 또는 러너 등록 해제 후 재등록"
    echo "   ./config.sh remove && ./config.sh --url ... --token ..."
    echo

    echo "📖 GitLab CI Runners:"
    echo "   # GitLab Runner 재시작"
    echo "   sudo gitlab-runner restart"
    echo "   # 특정 러너만 재시작"
    echo "   sudo gitlab-runner restart --config /etc/gitlab-runner/config.toml"
    echo

    echo "📖 Jenkins Agents:"
    echo "   # Jenkins 에이전트 재시작 (Master에서)"
    echo "   curl -X POST http://jenkins/computer/NODE_NAME/doDisconnect"
    echo "   curl -X POST http://jenkins/computer/NODE_NAME/launchSlaveAgent"
    echo

    echo "📖 CircleCI Runners:"
    echo "   # CircleCI Runner 재시작"
    echo "   sudo systemctl restart circleci-runner"
    echo "   # Runner 토큰 재생성 필요한 경우"
    echo "   circleci runner resource-class create-token NAMESPACE/RESOURCE_CLASS"
    echo

    echo "📖 Azure DevOps Agents:"
    echo "   # Azure DevOps 에이전트 재시작"
    echo "   sudo systemctl restart vsts-agent*"
    echo "   # 에이전트 재구성"
    echo "   ./config.sh remove && ./config.sh --unattended ..."
    echo

    echo "📖 Docker 기반 워커:"
    echo "   # 컨테이너 재시작"
    echo "   docker restart ci-worker-container"
    echo "   # 새 컨테이너로 교체"
    echo "   docker stop ci-worker && docker run ... new-worker"
    echo

    echo "📖 Kubernetes 기반 워커:"
    echo "   # Pod 재시작"
    echo "   kubectl delete pod -l app=ci-worker"
    echo "   # Deployment 롤링 업데이트"
    echo "   kubectl rollout restart deployment/ci-worker"
    echo
}

# 메인 실행 함수
main() {
    local error_data=""

    # stdin에서 에러 데이터 읽기
    if [[ -t 0 ]]; then
        # 터미널에서 직접 실행된 경우
        log_message "INFO" "워커 재시작 훅 스크립트 단독 실행"
        error_data='{"type":"worker_unavailable","message":"Worker node unresponsive"}'
    else
        # 파이프를 통해 에러 데이터가 전달된 경우
        error_data=$(cat)
        log_message "INFO" "워커 재시작 훅 스크립트 실행 - 에러 데이터 수신됨"
    fi

    log_message "WARN" "🚨 안전 모드: 실제 워커 재시작은 수행되지 않습니다"

    echo "🔄 워커 재시작 훅 실행 결과"
    echo "============================"
    echo

    # 에러 데이터 분석
    if [[ -n "$error_data" ]]; then
        log_message "INFO" "수신된 에러 데이터 분석 중..."

        # 에러 유형에 따른 구체적인 분석
        if echo "$error_data" | grep -qi "memory\|oom"; then
            log_message "WARN" "메모리 관련 문제 감지 - 메모리 부족으로 인한 워커 불안정"
            echo "  💡 권장 조치: 메모리 사용량 모니터링 및 제한 설정"
        fi

        if echo "$error_data" | grep -qi "cpu\|load"; then
            log_message "WARN" "CPU 부하 관련 문제 감지 - 과도한 CPU 사용"
            echo "  💡 권장 조치: CPU 집약적 작업 분산 및 병렬 처리 제한"
        fi

        if echo "$error_data" | grep -qi "timeout\|unresponsive"; then
            log_message "WARN" "응답 시간 초과 감지 - 워커 통신 문제"
            echo "  💡 권장 조치: 네트워크 연결 상태 및 방화벽 설정 확인"
        fi

        if echo "$error_data" | grep -qi "disk\|storage"; then
            log_message "WARN" "저장소 관련 문제 감지 - 디스크 공간 부족"
            echo "  💡 권장 조치: 디스크 공간 정리 및 임시 파일 삭제"
        fi
        echo
    fi

    # 워커 상태 시뮬레이션
    simulate_worker_status

    # 워커 재시작 시뮬레이션
    simulate_worker_restart

    # 플랫폼별 가이드 제공
    provide_worker_guides "$error_data"

    # 모니터링 및 예방 조치 안내
    log_message "GUIDE" "워커 모니터링 및 예방 조치:"
    echo
    echo "📊 모니터링 설정:"
    echo "  1. 📈 CPU/메모리 사용률 임계치 설정"
    echo "  2. 🕐 응답 시간 모니터링"
    echo "  3. 📊 작업 큐 길이 추적"
    echo "  4. 🔄 자동 스케일링 설정"
    echo
    echo "🛡️ 예방 조치:"
    echo "  1. 📅 정기적인 워커 재시작 스케줄"
    echo "  2. 🧹 자동 정리 스크립트 설정"
    echo "  3. 🔍 로그 로테이션 설정"
    echo "  4. 💾 리소스 제한 설정"
    echo

    # 새 워커 상태 시뮬레이션
    echo "✨ 재시작 후 워커 상태 (시뮬레이션):"
    echo "====================================="
    echo "  📍 워커 ID: worker-node-001"
    echo "  📊 상태: HEALTHY"
    echo "  💾 메모리 사용률: 15%"
    echo "  🔥 CPU 사용률: 8%"
    echo "  🕐 가동 시간: 0h 1m"
    echo "  ✅ 최근 실패: 0건"
    echo

    log_message "INFO" "워커 재시작 훅 실행 완료 (시뮬레이션 모드)"
    log_message "WARN" "실제 재시작을 원한다면 위의 가이드를 참조하여 수동으로 실행하세요"

    # 성공 상태로 종료
    echo "✅ 워커 재시작 훅 성공적으로 완료"
    exit 0
}

# 스크립트 실행
main "$@"