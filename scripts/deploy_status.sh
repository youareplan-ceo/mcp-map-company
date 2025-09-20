#!/bin/bash

#
# MCP-MAP Company 배포 상태 점검 스크립트
#
# Git 브랜치, 커밋 상태, Docker 컨테이너, 포트 점유 상태, 시스템 리소스를
# 종합적으로 모니터링하여 배포 환경의 현재 상태를 실시간으로 확인합니다.
#
# 사용법:
#   ./scripts/deploy_status.sh [옵션]
#
# 옵션:
#   --json             JSON 형식으로 결과 출력
#   --detailed         상세 정보 포함
#   --watch            실시간 모니터링 모드 (5초마다 갱신)
#   --help             도움말 출력
#
# 예시:
#   ./scripts/deploy_status.sh
#   ./scripts/deploy_status.sh --json
#   ./scripts/deploy_status.sh --detailed --watch
#   make deploy-status
#

set -euo pipefail  # Exit on any error, undefined variable, or pipe failure

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MONITORED_PORTS=(8080 8088 8000 5000 3000 5432 6379 8001 8081)
MCP_SERVICES=("mcp-api" "mcp-web" "mcp-stock" "mcp-database")
CHECK_INTERVAL=5

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Flags
JSON_OUTPUT=false
DETAILED_MODE=false
WATCH_MODE=false

# Logging function
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    if [[ "$JSON_OUTPUT" == "true" ]]; then
        return  # Skip logs in JSON mode
    fi

    case "$level" in
        "INFO")
            echo -e "${GREEN}[INFO]${NC} $timestamp - $message"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} $timestamp - $message"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $timestamp - $message" >&2
            ;;
        "DEBUG")
            if [[ "$DETAILED_MODE" == "true" ]]; then
                echo -e "${BLUE}[DEBUG]${NC} $timestamp - $message"
            fi
            ;;
        *)
            echo "$timestamp - $message"
            ;;
    esac
}

# Error handler
error_exit() {
    log "ERROR" "$1"
    exit 1
}

# Check if command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Get Git information
get_git_status() {
    local git_info="{}"

    if ! command_exists git; then
        echo '{"error": "Git not installed"}'
        return
    fi

    if [[ ! -d "$PROJECT_ROOT/.git" ]]; then
        echo '{"error": "Not a Git repository"}'
        return
    fi

    cd "$PROJECT_ROOT"

    local branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    local commit=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
    local short_commit=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    local commit_date=$(git log -1 --format='%ci' 2>/dev/null || echo "unknown")
    local commit_author=$(git log -1 --format='%an' 2>/dev/null || echo "unknown")
    local commit_message=$(git log -1 --format='%s' 2>/dev/null || echo "unknown")

    # Check if working directory is clean
    local is_clean=true
    local uncommitted_files=0
    local untracked_files=0

    if git status --porcelain 2>/dev/null | grep -q .; then
        is_clean=false
        uncommitted_files=$(git status --porcelain 2>/dev/null | grep -E '^[AM]' | wc -l)
        untracked_files=$(git status --porcelain 2>/dev/null | grep -E '^\?\?' | wc -l)
    fi

    # Check remote sync status
    local remote_status="unknown"
    local ahead=0
    local behind=0

    if git rev-parse --abbrev-ref '@{u}' &>/dev/null; then
        ahead=$(git rev-list --count '@{u}'..HEAD 2>/dev/null || echo 0)
        behind=$(git rev-list --count HEAD..'@{u}' 2>/dev/null || echo 0)

        if [[ $ahead -eq 0 && $behind -eq 0 ]]; then
            remote_status="up-to-date"
        elif [[ $ahead -gt 0 && $behind -eq 0 ]]; then
            remote_status="ahead"
        elif [[ $ahead -eq 0 && $behind -gt 0 ]]; then
            remote_status="behind"
        else
            remote_status="diverged"
        fi
    fi

    # Get repository URL
    local repo_url=$(git config --get remote.origin.url 2>/dev/null || echo "unknown")

    echo "{
        \"branch\": \"$branch\",
        \"commit\": \"$commit\",
        \"short_commit\": \"$short_commit\",
        \"commit_date\": \"$commit_date\",
        \"commit_author\": \"$commit_author\",
        \"commit_message\": \"$commit_message\",
        \"is_clean\": $is_clean,
        \"uncommitted_files\": $uncommitted_files,
        \"untracked_files\": $untracked_files,
        \"remote_status\": \"$remote_status\",
        \"ahead\": $ahead,
        \"behind\": $behind,
        \"repository_url\": \"$repo_url\"
    }"
}

# Get Docker information
get_docker_status() {
    local docker_info='{"available": false, "containers": []}'

    if ! command_exists docker; then
        echo "$docker_info"
        return
    fi

    # Check if Docker daemon is running
    if ! docker info &>/dev/null; then
        echo '{"available": false, "error": "Docker daemon not running"}'
        return
    fi

    local containers='[]'
    local container_count=0
    local running_count=0

    # Get container information
    if command_exists docker; then
        local container_list=()

        while IFS= read -r container_line; do
            if [[ -n "$container_line" ]]; then
                container_count=$((container_count + 1))

                # Parse container info
                local name=$(echo "$container_line" | awk '{print $NF}')
                local status=$(echo "$container_line" | awk '{for(i=5;i<NF;i++) printf "%s ", $i; print $NF}' | sed 's/ [^ ]*$//')
                local image=$(echo "$container_line" | awk '{print $2}')

                if [[ "$status" == *"Up"* ]]; then
                    running_count=$((running_count + 1))
                fi

                container_list+=("{\"name\": \"$name\", \"status\": \"$status\", \"image\": \"$image\"}")
            fi
        done < <(docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" | tail -n +2 2>/dev/null)

        if [[ ${#container_list[@]} -gt 0 ]]; then
            containers="[$(IFS=','; echo "${container_list[*]}")]"
        fi
    fi

    # Check specific MCP services
    local service_status=()
    for service in "${MCP_SERVICES[@]}"; do
        local status="not_found"
        local container_id=""

        if docker ps --filter "name=$service" --format "{{.ID}}" | grep -q .; then
            status="running"
            container_id=$(docker ps --filter "name=$service" --format "{{.ID}}")
        elif docker ps -a --filter "name=$service" --format "{{.ID}}" | grep -q .; then
            status="stopped"
            container_id=$(docker ps -a --filter "name=$service" --format "{{.ID}}")
        fi

        service_status+=("{\"name\": \"$service\", \"status\": \"$status\", \"container_id\": \"$container_id\"}")
    done

    local services_json="[$(IFS=','; echo "${service_status[*]}")]"

    echo "{
        \"available\": true,
        \"total_containers\": $container_count,
        \"running_containers\": $running_count,
        \"containers\": $containers,
        \"mcp_services\": $services_json
    }"
}

# Get port information
get_port_status() {
    local port_info='{"ports": []}'
    local port_list=()

    for port in "${MONITORED_PORTS[@]}"; do
        local status="free"
        local process=""
        local pid=""

        # Check if port is in use
        if command_exists lsof; then
            local lsof_output=$(lsof -i ":$port" -t 2>/dev/null || echo "")
            if [[ -n "$lsof_output" ]]; then
                status="occupied"
                pid=$(echo "$lsof_output" | head -1)
                process=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
            fi
        elif command_exists netstat; then
            if netstat -tulpn 2>/dev/null | grep -q ":$port "; then
                status="occupied"
                process="netstat_detected"
            fi
        elif command_exists ss; then
            if ss -tulpn 2>/dev/null | grep -q ":$port "; then
                status="occupied"
                process="ss_detected"
            fi
        fi

        port_list+=("{\"port\": $port, \"status\": \"$status\", \"process\": \"$process\", \"pid\": \"$pid\"}")
    done

    local ports_json="[$(IFS=','; echo "${port_list[*]}")]"
    echo "{\"ports\": $ports_json}"
}

# Get system resource information
get_system_resources() {
    local cpu_usage=""
    local memory_usage=""
    local disk_usage=""
    local load_avg=""
    local uptime=""

    # CPU usage (Linux)
    if [[ -f "/proc/stat" ]]; then
        cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//' 2>/dev/null || echo "unknown")
    # CPU usage (macOS)
    elif command_exists top; then
        cpu_usage=$(top -l1 -s0 | grep "CPU usage" | awk '{print $3}' 2>/dev/null || echo "unknown")
    fi

    # Memory usage (Linux)
    if [[ -f "/proc/meminfo" ]]; then
        local mem_total=$(grep MemTotal /proc/meminfo | awk '{print $2}')
        local mem_available=$(grep MemAvailable /proc/meminfo | awk '{print $2}')
        memory_usage="$((($mem_total - $mem_available) * 100 / $mem_total))%"
    # Memory usage (macOS)
    elif command_exists vm_stat; then
        local vm_stat_output=$(vm_stat)
        memory_usage=$(echo "$vm_stat_output" | grep "Pages active" | awk '{print $3}' | tr -d '.' || echo "unknown")
    fi

    # Disk usage
    if command_exists df; then
        disk_usage=$(df -h "$PROJECT_ROOT" | tail -1 | awk '{print $5}' 2>/dev/null || echo "unknown")
    fi

    # Load average
    if [[ -f "/proc/loadavg" ]]; then
        load_avg=$(cat /proc/loadavg | awk '{print $1, $2, $3}')
    elif command_exists uptime; then
        load_avg=$(uptime | grep -o 'load average.*' | cut -d' ' -f3- 2>/dev/null || echo "unknown")
    fi

    # System uptime
    if command_exists uptime; then
        uptime=$(uptime | awk '{print $3, $4}' | sed 's/,//' 2>/dev/null || echo "unknown")
    fi

    echo "{
        \"cpu_usage\": \"$cpu_usage\",
        \"memory_usage\": \"$memory_usage\",
        \"disk_usage\": \"$disk_usage\",
        \"load_average\": \"$load_avg\",
        \"uptime\": \"$uptime\",
        \"timestamp\": \"$(date -u '+%Y-%m-%d %H:%M:%S UTC')\"
    }"
}

# Display status in human-readable format
display_status() {
    local status_json="$1"

    echo -e "${CYAN}===============================================${NC}"
    echo -e "${CYAN}🚀 MCP-MAP Company 배포 상태 점검 리포트${NC}"
    echo -e "${CYAN}===============================================${NC}"

    # Git Status
    echo ""
    echo -e "${YELLOW}📋 Git 상태${NC}"
    echo "────────────────────────────────────────────"

    local git_status=$(echo "$status_json" | jq -r '.git')
    if echo "$git_status" | jq -e '.error' >/dev/null 2>&1; then
        local error=$(echo "$git_status" | jq -r '.error')
        echo -e "  ${RED}❌ $error${NC}"
    else
        local branch=$(echo "$git_status" | jq -r '.branch')
        local short_commit=$(echo "$git_status" | jq -r '.short_commit')
        local is_clean=$(echo "$git_status" | jq -r '.is_clean')
        local remote_status=$(echo "$git_status" | jq -r '.remote_status')

        echo "  브랜치: $branch"
        echo "  커밋: $short_commit"

        if [[ "$is_clean" == "true" ]]; then
            echo -e "  상태: ${GREEN}✅ 클린${NC}"
        else
            local uncommitted=$(echo "$git_status" | jq -r '.uncommitted_files')
            local untracked=$(echo "$git_status" | jq -r '.untracked_files')
            echo -e "  상태: ${YELLOW}⚠️ 미커밋 파일 ${uncommitted}개, 미추적 파일 ${untracked}개${NC}"
        fi

        echo "  원격 상태: $remote_status"

        if [[ "$DETAILED_MODE" == "true" ]]; then
            local commit_author=$(echo "$git_status" | jq -r '.commit_author')
            local commit_date=$(echo "$git_status" | jq -r '.commit_date')
            local commit_message=$(echo "$git_status" | jq -r '.commit_message')
            echo "  마지막 커밋: $commit_message"
            echo "  작성자: $commit_author"
            echo "  날짜: $commit_date"
        fi
    fi

    # Docker Status
    echo ""
    echo -e "${YELLOW}🐳 Docker 상태${NC}"
    echo "────────────────────────────────────────────"

    local docker_status=$(echo "$status_json" | jq -r '.docker')
    local docker_available=$(echo "$docker_status" | jq -r '.available')

    if [[ "$docker_available" == "true" ]]; then
        local total=$(echo "$docker_status" | jq -r '.total_containers')
        local running=$(echo "$docker_status" | jq -r '.running_containers')

        echo -e "  상태: ${GREEN}✅ 사용 가능${NC}"
        echo "  컨테이너: 총 ${total}개, 실행 중 ${running}개"

        # MCP Services
        echo "  MCP 서비스:"
        echo "$docker_status" | jq -r '.mcp_services[] | "    " + .name + ": " + .status' | while read line; do
            if [[ "$line" == *"running"* ]]; then
                echo -e "    ${GREEN}${line}${NC}"
            elif [[ "$line" == *"stopped"* ]]; then
                echo -e "    ${YELLOW}${line}${NC}"
            else
                echo -e "    ${RED}${line}${NC}"
            fi
        done
    else
        local error=$(echo "$docker_status" | jq -r '.error // "Docker not available"')
        echo -e "  ${RED}❌ $error${NC}"
    fi

    # Port Status
    echo ""
    echo -e "${YELLOW}🔌 포트 상태${NC}"
    echo "────────────────────────────────────────────"

    local port_status=$(echo "$status_json" | jq -r '.ports')

    echo "$port_status" | jq -r '.ports[] | select(.status == "occupied") | "  🔴 점유: " + (.port | tostring) + " - " + .process + " (PID: " + .pid + ")"' | while read line; do
        if [[ -n "$line" ]]; then
            echo -e "  ${RED}$line${NC}"
        fi
    done

    echo "$port_status" | jq -r '.ports[] | select(.status == "free") | (.port | tostring)' | while read port; do
        if [[ -n "$port" ]]; then
            echo -e "  ${GREEN}🟢 사용 가능: $port${NC}"
        fi
    done

    # System Resources (if detailed mode)
    if [[ "$DETAILED_MODE" == "true" ]]; then
        echo ""
        echo -e "${YELLOW}💻 시스템 리소스${NC}"
        echo "────────────────────────────────────────────"

        local system_status=$(echo "$status_json" | jq -r '.system')
        echo "  CPU 사용률: $(echo "$system_status" | jq -r '.cpu_usage')"
        echo "  메모리 사용률: $(echo "$system_status" | jq -r '.memory_usage')"
        echo "  디스크 사용률: $(echo "$system_status" | jq -r '.disk_usage')"
        echo "  로드 평균: $(echo "$system_status" | jq -r '.load_average')"
        echo "  업타임: $(echo "$system_status" | jq -r '.uptime')"
    fi

    echo ""
    echo -e "${CYAN}===============================================${NC}"
    echo "✅ 점검 완료: $(date '+%Y-%m-%d %H:%M:%S')"
    echo -e "${CYAN}===============================================${NC}"
}

# Collect all status information
collect_status() {
    log "DEBUG" "Collecting Git status..."
    local git_status=$(get_git_status)

    log "DEBUG" "Collecting Docker status..."
    local docker_status=$(get_docker_status)

    log "DEBUG" "Collecting port status..."
    local port_status=$(get_port_status)

    local system_status="{}"
    if [[ "$DETAILED_MODE" == "true" ]]; then
        log "DEBUG" "Collecting system resources..."
        system_status=$(get_system_resources)
    fi

    # Combine all status information
    local combined_status=$(cat <<EOF
{
    "timestamp": "$(date -u '+%Y-%m-%d %H:%M:%S UTC')",
    "git": $git_status,
    "docker": $docker_status,
    "ports": $port_status,
    "system": $system_status
}
EOF
)

    echo "$combined_status"
}

# Main execution function
main() {
    log "INFO" "🚀 MCP-MAP Company 배포 상태 점검 시작..."

    # Change to project directory
    cd "$PROJECT_ROOT"

    while true; do
        local status_json=$(collect_status)

        if [[ "$JSON_OUTPUT" == "true" ]]; then
            echo "$status_json" | jq .
        else
            if [[ "$WATCH_MODE" == "true" ]]; then
                clear
            fi
            display_status "$status_json"
        fi

        if [[ "$WATCH_MODE" == "false" ]]; then
            break
        fi

        if [[ "$JSON_OUTPUT" == "false" ]]; then
            echo ""
            log "INFO" "다음 갱신까지 ${CHECK_INTERVAL}초... (Ctrl+C로 종료)"
        fi

        sleep "$CHECK_INTERVAL"
    done

    log "INFO" "✅ 배포 상태 점검 완료"
}

# Handle script arguments
show_help() {
    cat << EOF
MCP-MAP Company 배포 상태 점검 스크립트

사용법: $0 [OPTIONS]

OPTIONS:
    --json          JSON 형식으로 결과 출력
    --detailed      상세 정보 포함 (시스템 리소스 등)
    --watch         실시간 모니터링 모드 (5초마다 갱신)
    --help, -h      이 도움말 출력

예시:
    $0                      # 기본 상태 체크
    $0 --json               # JSON 형식 출력
    $0 --detailed --watch   # 상세 정보와 함께 실시간 모니터링

이 스크립트는 다음 항목들을 점검합니다:
    - Git 브랜치 및 커밋 상태
    - Docker 컨테이너 상태 (MCP 서비스 포함)
    - 포트 점유 상태 (8080, 8088, 8000, 5000, 3000, 5432, 6379, 8001, 8081)
    - 시스템 리소스 (상세 모드)

환경 변수:
    CHECK_INTERVAL      모니터링 갱신 간격 (기본값: 5초)
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        --detailed)
            DETAILED_MODE=true
            shift
            ;;
        --watch)
            WATCH_MODE=true
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information."
            exit 1
            ;;
    esac
done

# Validate environment
if ! command_exists jq; then
    error_exit "jq is required but not installed. Please install jq first."
fi

# Handle Ctrl+C gracefully in watch mode
if [[ "$WATCH_MODE" == "true" ]]; then
    trap 'echo ""; log "INFO" "모니터링 종료"; exit 0' INT
fi

# Run main function
main "$@"