#!/bin/bash
# =============================================================================
# CI 캐시 정리 훅 스크립트 (CI Cache Cleanup Hook Script)
# =============================================================================
# 목적: CI 캐시 정리 작업 수행 (드라이런 메시지 + 가이드)
# Purpose: Perform CI cache cleanup operations with dry-run messages and guidance
#
# 주의사항:
# - 이 스크립트는 실제 파괴적 동작을 수행하지 않습니다
# - 드라이런 모드로 동작하며 가이드 메시지만 출력합니다
# - 실제 캐시 정리는 CI 플랫폼별로 적절한 명령어를 사용해야 합니다
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
        *)
            echo -e "${BLUE}[${level}]${NC} ${timestamp} - $message" >&2
            ;;
    esac
}

# 메인 실행 함수
main() {
    local error_data=""

    # stdin에서 에러 데이터 읽기
    if [[ -t 0 ]]; then
        # 터미널에서 직접 실행된 경우
        log_message "INFO" "CI 캐시 정리 훅 스크립트 단독 실행"
    else
        # 파이프를 통해 에러 데이터가 전달된 경우
        error_data=$(cat)
        log_message "INFO" "CI 캐시 정리 훅 스크립트 실행 - 에러 데이터 수신됨"
    fi

    log_message "WARN" "🚨 안전 모드: 실제 캐시 정리 작업은 수행되지 않습니다"

    echo "🧹 CI 캐시 정리 훅 실행 결과"
    echo "================================="
    echo
    echo "📋 수행할 작업 목록 (드라이런 모드):"
    echo "  1. 🗂️  빌드 캐시 정리"
    echo "  2. 📦 의존성 캐시 삭제"
    echo "  3. 🖼️  Docker 이미지 캐시 정리"
    echo "  4. 📄 임시 파일 정리"
    echo "  5. 🔄 캐시 인덱스 재구성"
    echo

    # CI 플랫폼별 가이드 제공
    log_message "GUIDE" "실제 캐시 정리를 위한 플랫폼별 명령어 가이드:"
    echo
    echo "📖 GitHub Actions:"
    echo "   gh api repos/OWNER/REPO/actions/caches --method DELETE"
    echo "   또는 Actions 탭에서 수동 삭제"
    echo
    echo "📖 GitLab CI:"
    echo "   curl -X DELETE \"https://gitlab.com/api/v4/projects/ID/job_artifacts\""
    echo "   또는 프로젝트 설정에서 수동 삭제"
    echo
    echo "📖 Jenkins:"
    echo "   jenkins-cli.jar delete-cache JOB_NAME"
    echo "   또는 작업 설정에서 \"Delete workspace before build\" 활성화"
    echo
    echo "📖 CircleCI:"
    echo "   curl -X DELETE https://circleci.com/api/v2/project/PROJECT_SLUG/cache"
    echo
    echo "📖 Docker 캐시:"
    echo "   docker system prune -af"
    echo "   docker builder prune -af"
    echo

    # 에러 데이터가 있는 경우 분석 정보 제공
    if [[ -n "$error_data" ]]; then
        log_message "INFO" "수신된 에러 데이터 분석 중..."

        # 에러 유형에 따른 구체적인 가이드 제공
        if echo "$error_data" | grep -q "dependency"; then
            log_message "GUIDE" "의존성 관련 에러 감지 - npm/pip/maven 캐시 정리 권장"
            echo "  🔧 Node.js: npm cache clean --force"
            echo "  🔧 Python: pip cache purge"
            echo "  🔧 Maven: mvn dependency:purge-local-repository"
        fi

        if echo "$error_data" | grep -q "build\|compile"; then
            log_message "GUIDE" "빌드 관련 에러 감지 - 빌드 아티팩트 정리 권장"
            echo "  🔧 Clean build: make clean && make"
            echo "  🔧 Gradle: ./gradlew clean"
            echo "  🔧 Maven: mvn clean"
        fi

        if echo "$error_data" | grep -q "disk\|space"; then
            log_message "GUIDE" "디스크 공간 관련 에러 감지 - 전체 시스템 정리 권장"
            echo "  🔧 시스템 정리: docker system prune -af"
            echo "  🔧 로그 정리: sudo journalctl --vacuum-time=7d"
        fi
    fi

    echo
    log_message "INFO" "캐시 정리 훅 실행 완료 (드라이런 모드)"
    log_message "WARN" "실제 적용을 원한다면 위의 가이드를 참조하여 수동으로 실행하세요"

    # 성공 상태로 종료
    echo "✅ CI 캐시 정리 훅 성공적으로 완료"
    exit 0
}

# 스크립트 실행
main "$@"