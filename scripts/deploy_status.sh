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
CHECK_K8S=false
CHECK_SERVICES=false
CHECK_NGINX=false  # Nginx 상태 점검 플래그
CHECK_SSL=false    # SSL 인증서 검사 플래그
SHOW_LOGS=false    # 로그 표시 플래그

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

    # 새로운 기능들: Nginx, SSL, 로그 상태 수집
    local nginx_status="{}"
    if [[ "$CHECK_NGINX" == "true" ]]; then
        log "DEBUG" "Collecting Nginx status..."
        nginx_status=$(get_nginx_status)
    fi

    local ssl_status="{}"
    if [[ "$CHECK_SSL" == "true" ]]; then
        log "DEBUG" "Checking SSL certificates..."
        ssl_status=$(check_ssl_certificates)
    fi

    local logs_status="{}"
    if [[ "$SHOW_LOGS" == "true" ]]; then
        log "DEBUG" "Collecting recent logs..."
        logs_status=$(get_recent_logs)
    fi

    # K8s 상태 (기존 기능)
    local k8s_status="{}"
    local k8s_pods="{}"
    if [[ "$CHECK_K8S" == "true" ]]; then
        log "DEBUG" "Collecting Kubernetes status..."
        k8s_status=$(get_k8s_status)
        k8s_pods=$(get_k8s_pods)
    fi

    # 외부 서비스 상태 (기존 기능)
    local external_services="{}"
    if [[ "$CHECK_SERVICES" == "true" ]]; then
        log "DEBUG" "Checking external services..."
        external_services=$(get_external_services_status)
    fi

    # Combine all status information
    local combined_status=$(cat <<EOF
{
    "timestamp": "$(date -u '+%Y-%m-%d %H:%M:%S UTC')",
    "git": $git_status,
    "docker": $docker_status,
    "ports": $port_status,
    "system": $system_status,
    "nginx": $nginx_status,
    "ssl": $ssl_status,
    "logs": $logs_status,
    "kubernetes": $k8s_status,
    "k8s_pods": $k8s_pods,
    "external_services": $external_services
}
EOF
)

    echo "$combined_status"
}

# =============================================
# Kubernetes Status Functions
# =============================================

# Get Kubernetes cluster status
get_k8s_status() {
    if ! command_exists kubectl; then
        echo "{\"available\": false, \"reason\": \"kubectl not installed\"}"
        return
    fi

    # Test cluster connectivity
    if ! kubectl cluster-info >/dev/null 2>&1; then
        echo "{\"available\": false, \"reason\": \"cluster not accessible\"}"
        return
    fi

    # Get cluster info
    local cluster_info=$(kubectl cluster-info --short 2>/dev/null | head -1 || echo "unknown")
    local kubernetes_version=$(kubectl version --short --client 2>/dev/null | grep Client | awk '{print $3}' || echo "unknown")
    local server_version=$(kubectl version --short --server 2>/dev/null | grep Server | awk '{print $3}' || echo "unknown")

    # Get node status
    local node_count=0
    local ready_nodes=0
    local node_list=()

    while read -r name status; do
        if [[ -n "$name" && "$name" != "NAME" ]]; then
            node_count=$((node_count + 1))
            if [[ "$status" == "Ready" ]]; then
                ready_nodes=$((ready_nodes + 1))
            fi
            node_list+=("{\"name\": \"$name\", \"status\": \"$status\"}")
        fi
    done < <(kubectl get nodes --no-headers -o wide 2>/dev/null | awk '{print $1, $2}')

    local nodes_json="[$(IFS=','; echo "${node_list[*]}")]"

    echo "{
        \"available\": true,
        \"cluster_info\": \"$cluster_info\",
        \"kubernetes_version\": \"$kubernetes_version\",
        \"server_version\": \"$server_version\",
        \"node_count\": $node_count,
        \"ready_nodes\": $ready_nodes,
        \"nodes\": $nodes_json
    }"
}

# Get pod status for MCP-related services
get_k8s_pods() {
    if ! command_exists kubectl || ! kubectl cluster-info >/dev/null 2>&1; then
        echo "{\"available\": false, \"pods\": []}"
        return
    fi

    local pod_list=()
    local total_pods=0
    local running_pods=0

    # Get all pods with MCP in the name or in specific namespaces
    local kubectl_output
    kubectl_output=$(kubectl get pods --all-namespaces -o wide 2>/dev/null | grep -i mcp || true)

    if [[ -z "$kubectl_output" ]]; then
        # If no MCP pods found, get pods from default namespace
        kubectl_output=$(kubectl get pods -o wide 2>/dev/null || true)
    fi

    while read -r namespace name ready status restarts age; do
        if [[ -n "$name" && "$name" != "NAME" ]]; then
            total_pods=$((total_pods + 1))
            if [[ "$status" == "Running" ]]; then
                running_pods=$((running_pods + 1))
            fi
            pod_list+=("{\"namespace\": \"$namespace\", \"name\": \"$name\", \"ready\": \"$ready\", \"status\": \"$status\", \"restarts\": \"$restarts\", \"age\": \"$age\"}")
        fi
    done <<< "$kubectl_output"

    local pods_json="[$(IFS=','; echo "${pod_list[*]}")]"

    echo "{
        \"available\": true,
        \"total_pods\": $total_pods,
        \"running_pods\": $running_pods,
        \"pods\": $pods_json
    }"
}

# =============================================
# Nginx Status Functions
# =============================================

# Get Nginx service status
get_nginx_status() {
    if ! $CHECK_NGINX; then
        echo "{\"available\": false, \"reason\": \"nginx check disabled\"}"
        return
    fi

    local nginx_info='{"available": false}'

    # Nginx 설정 파일 경로들
    local nginx_config_paths=(
        "/etc/nginx/nginx.conf"
        "/usr/local/nginx/conf/nginx.conf"
        "/opt/nginx/conf/nginx.conf"
        "/usr/local/etc/nginx/nginx.conf"  # macOS Homebrew
    )

    # Nginx 바이너리 경로들
    local nginx_binary_paths=(
        "/usr/sbin/nginx"
        "/usr/local/sbin/nginx"
        "/opt/nginx/sbin/nginx"
        "/usr/local/bin/nginx"  # macOS Homebrew
    )

    # Nginx 바이너리 찾기
    local nginx_binary=""
    for path in "${nginx_binary_paths[@]}"; do
        if [[ -x "$path" ]]; then
            nginx_binary="$path"
            break
        fi
    done

    # Nginx가 설치되지 않은 경우
    if [[ -z "$nginx_binary" ]] && ! command_exists nginx; then
        echo "{\"available\": false, \"reason\": \"nginx not installed\"}"
        return
    fi

    # Nginx 명령어 설정
    if [[ -n "$nginx_binary" ]]; then
        local nginx_cmd="$nginx_binary"
    else
        local nginx_cmd="nginx"
    fi

    # Nginx 프로세스 상태 확인
    local is_running=false
    local process_count=0
    local master_pid=""
    local worker_count=0

    if command_exists pgrep; then
        process_count=$(pgrep -c nginx 2>/dev/null || echo "0")
        if [[ $process_count -gt 0 ]]; then
            is_running=true
            master_pid=$(pgrep -f "nginx: master process" 2>/dev/null | head -1 || echo "unknown")
            worker_count=$(pgrep -c "nginx: worker process" 2>/dev/null || echo "0")
        fi
    elif command_exists ps; then
        if ps aux | grep -v grep | grep -q nginx; then
            is_running=true
            process_count=$(ps aux | grep -v grep | grep -c nginx || echo "0")
            master_pid=$(ps aux | grep -v grep | grep "nginx: master" | awk '{print $2}' | head -1 || echo "unknown")
            worker_count=$(ps aux | grep -v grep | grep -c "nginx: worker" || echo "0")
        fi
    fi

    # Nginx 설정 파일 찾기
    local config_file=""
    for path in "${nginx_config_paths[@]}"; do
        if [[ -f "$path" ]]; then
            config_file="$path"
            break
        fi
    done

    # Nginx 버전 정보
    local nginx_version="unknown"
    if [[ -n "$nginx_binary" ]] || command_exists nginx; then
        nginx_version=$($nginx_cmd -v 2>&1 | grep -o "nginx/[0-9.]*" || echo "unknown")
    fi

    # 설정 테스트
    local config_test="unknown"
    if [[ $is_running == true ]] && [[ -n "$nginx_binary" || -n "$(command -v nginx)" ]]; then
        if $nginx_cmd -t >/dev/null 2>&1; then
            config_test="valid"
        else
            config_test="invalid"
        fi
    fi

    # 포트 확인 (HTTP: 80, HTTPS: 443)
    local http_port_status="unknown"
    local https_port_status="unknown"

    if command_exists netstat; then
        if netstat -tulpn 2>/dev/null | grep -q ":80 "; then
            http_port_status="listening"
        else
            http_port_status="not_listening"
        fi

        if netstat -tulpn 2>/dev/null | grep -q ":443 "; then
            https_port_status="listening"
        else
            https_port_status="not_listening"
        fi
    elif command_exists ss; then
        if ss -tulpn 2>/dev/null | grep -q ":80 "; then
            http_port_status="listening"
        else
            http_port_status="not_listening"
        fi

        if ss -tulpn 2>/dev/null | grep -q ":443 "; then
            https_port_status="listening"
        else
            https_port_status="not_listening"
        fi
    fi

    echo "{
        \"available\": true,
        \"running\": $is_running,
        \"version\": \"$nginx_version\",
        \"process_count\": $process_count,
        \"master_pid\": \"$master_pid\",
        \"worker_count\": $worker_count,
        \"config_file\": \"$config_file\",
        \"config_test\": \"$config_test\",
        \"http_port_status\": \"$http_port_status\",
        \"https_port_status\": \"$https_port_status\"
    }"
}

# =============================================
# SSL Certificate Functions
# =============================================

# Check SSL certificate status for domains
check_ssl_certificates() {
    if ! $CHECK_SSL; then
        echo "{\"available\": false, \"reason\": \"ssl check disabled\"}"
        return
    fi

    # 확인할 도메인 목록 (환경변수 또는 기본값)
    local domains_to_check="${SSL_DOMAINS:-localhost,127.0.0.1,mcp-map.company}"
    IFS=',' read -ra DOMAIN_ARRAY <<< "$domains_to_check"

    local ssl_results=()
    local total_domains=0
    local valid_certificates=0

    for domain in "${DOMAIN_ARRAY[@]}"; do
        domain=$(echo "$domain" | tr -d ' ') # 공백 제거
        if [[ -z "$domain" ]]; then
            continue
        fi

        total_domains=$((total_domains + 1))
        local ssl_info=$(check_domain_ssl "$domain")

        # 유효한 인증서인지 확인
        if echo "$ssl_info" | jq -e '.valid == true' >/dev/null 2>&1; then
            valid_certificates=$((valid_certificates + 1))
        fi

        ssl_results+=("$ssl_info")
    done

    local certificates_json="[$(IFS=','; echo "${ssl_results[*]}")]"

    echo "{
        \"available\": true,
        \"total_domains\": $total_domains,
        \"valid_certificates\": $valid_certificates,
        \"certificates\": $certificates_json
    }"
}

# Check SSL certificate for a specific domain
check_domain_ssl() {
    local domain="$1"
    local port="${2:-443}"

    # OpenSSL이 설치되어 있는지 확인
    if ! command_exists openssl; then
        echo "{\"domain\": \"$domain\", \"valid\": false, \"reason\": \"openssl not available\"}"
        return
    fi

    # 도메인 연결 테스트
    if ! timeout 10 bash -c "</dev/tcp/$domain/$port" 2>/dev/null; then
        echo "{\"domain\": \"$domain\", \"valid\": false, \"reason\": \"connection failed\"}"
        return
    fi

    # SSL 인증서 정보 가져오기
    local cert_info
    cert_info=$(timeout 10 openssl s_client -connect "$domain:$port" -servername "$domain" 2>/dev/null | openssl x509 -noout -dates -subject -issuer 2>/dev/null)

    if [[ -z "$cert_info" ]]; then
        echo "{\"domain\": \"$domain\", \"valid\": false, \"reason\": \"failed to retrieve certificate\"}"
        return
    fi

    # 만료일 추출
    local not_after
    not_after=$(echo "$cert_info" | grep "notAfter=" | cut -d= -f2)

    if [[ -z "$not_after" ]]; then
        echo "{\"domain\": \"$domain\", \"valid\": false, \"reason\": \"failed to parse expiry date\"}"
        return
    fi

    # 발급자 정보 추출
    local issuer
    issuer=$(echo "$cert_info" | grep "issuer=" | cut -d= -f2- | sed 's/^[[:space:]]*//')

    # 주체 정보 추출
    local subject
    subject=$(echo "$cert_info" | grep "subject=" | cut -d= -f2- | sed 's/^[[:space:]]*//')

    # 만료일까지 남은 일수 계산
    local expiry_timestamp
    if command_exists date; then
        # macOS와 Linux 호환성을 위한 날짜 파싱
        if [[ "$OSTYPE" == "darwin"* ]]; then
            expiry_timestamp=$(date -j -f "%b %d %H:%M:%S %Y %Z" "$not_after" "+%s" 2>/dev/null || echo "0")
        else
            expiry_timestamp=$(date -d "$not_after" "+%s" 2>/dev/null || echo "0")
        fi
    else
        expiry_timestamp="0"
    fi

    local current_timestamp=$(date "+%s")
    local days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))

    # 인증서 유효성 판단
    local is_valid=true
    local status="valid"
    local warnings=()

    if [[ $days_until_expiry -lt 0 ]]; then
        is_valid=false
        status="expired"
    elif [[ $days_until_expiry -lt 7 ]]; then
        status="expiring_soon"
        warnings+=("expires in $days_until_expiry days")
    elif [[ $days_until_expiry -lt 30 ]]; then
        status="warning"
        warnings+=("expires in $days_until_expiry days")
    fi

    local warnings_json="[]"
    if [[ ${#warnings[@]} -gt 0 ]]; then
        warnings_json="[\"$(IFS='","'; echo "${warnings[*]}")\"]"
    fi

    echo "{
        \"domain\": \"$domain\",
        \"valid\": $is_valid,
        \"status\": \"$status\",
        \"expiry_date\": \"$not_after\",
        \"days_until_expiry\": $days_until_expiry,
        \"issuer\": \"$issuer\",
        \"subject\": \"$subject\",
        \"warnings\": $warnings_json
    }"
}

# =============================================
# Log Display Functions
# =============================================

# Get recent deployment logs
get_recent_logs() {
    if ! $SHOW_LOGS; then
        echo "{\"available\": false, \"reason\": \"logs display disabled\"}"
        return
    fi

    # 확인할 로그 파일들 (우선순위 순)
    local log_files=(
        "$PROJECT_ROOT/logs/deploy.log"
        "$PROJECT_ROOT/logs/app.log"
        "$PROJECT_ROOT/logs/api.log"
        "$PROJECT_ROOT/logs/scheduler.log"
        "/var/log/nginx/access.log"
        "/var/log/nginx/error.log"
        "/var/log/syslog"
        "/var/log/messages"
    )

    local available_logs=()
    local log_summaries=()

    for log_file in "${log_files[@]}"; do
        if [[ -f "$log_file" && -r "$log_file" ]]; then
            local file_size=$(stat -f%z "$log_file" 2>/dev/null || stat -c%s "$log_file" 2>/dev/null || echo "0")
            local line_count=$(wc -l < "$log_file" 2>/dev/null || echo "0")
            local last_modified

            if [[ "$OSTYPE" == "darwin"* ]]; then
                last_modified=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$log_file" 2>/dev/null || echo "unknown")
            else
                last_modified=$(stat -c "%y" "$log_file" 2>/dev/null | cut -d. -f1 || echo "unknown")
            fi

            # 최근 10줄의 로그 내용 (에러나 중요한 내용 우선)
            local recent_content=""
            if command_exists tail; then
                recent_content=$(tail -10 "$log_file" 2>/dev/null | sed 's/"/\\"/g' | tr '\n' '\\n' || echo "")
            fi

            available_logs+=("\"$log_file\"")
            log_summaries+=("{
                \"file\": \"$log_file\",
                \"size_bytes\": $file_size,
                \"line_count\": $line_count,
                \"last_modified\": \"$last_modified\",
                \"recent_content\": \"$recent_content\"
            }")
        fi
    done

    local logs_json="[$(IFS=','; echo "${log_summaries[*]}")]"
    local available_logs_json="[$(IFS=','; echo "${available_logs[*]}")]"

    echo "{
        \"available\": true,
        \"total_log_files\": ${#available_logs[@]},
        \"available_logs\": $available_logs_json,
        \"log_details\": $logs_json
    }"
}

# =============================================
# External Services Monitoring Functions
# =============================================

# Define external services to monitor
declare -a EXTERNAL_SERVICES=(
    "redis://localhost:6379"
    "mongodb://localhost:27017"
    "http://localhost:3000/health"
    "http://localhost:8080/health"
    "https://api.github.com"
)

# Check external service connectivity
check_external_service() {
    local service_url="$1"
    local protocol=$(echo "$service_url" | cut -d: -f1)
    local host_port=$(echo "$service_url" | cut -d/ -f3)
    local host=$(echo "$host_port" | cut -d: -f1)
    local port=$(echo "$host_port" | cut -d: -f2)
    local path=$(echo "$service_url" | cut -d/ -f4-)

    case "$protocol" in
        "http" | "https")
            if command_exists curl; then
                local response_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$service_url" 2>/dev/null || echo "000")
                local response_time=$(curl -s -o /dev/null -w "%{time_total}" --max-time 5 "$service_url" 2>/dev/null || echo "999")
                if [[ "$response_code" -ge 200 && "$response_code" -lt 400 ]]; then
                    echo "{\"status\": \"healthy\", \"response_code\": $response_code, \"response_time\": $response_time}"
                else
                    echo "{\"status\": \"unhealthy\", \"response_code\": $response_code, \"response_time\": $response_time}"
                fi
            else
                echo "{\"status\": \"unknown\", \"reason\": \"curl not available\"}"
            fi
            ;;
        "redis")
            if command_exists redis-cli; then
                if timeout 5 redis-cli -h "$host" -p "${port:-6379}" ping >/dev/null 2>&1; then
                    echo "{\"status\": \"healthy\", \"type\": \"redis\"}"
                else
                    echo "{\"status\": \"unhealthy\", \"type\": \"redis\"}"
                fi
            elif command_exists nc; then
                if timeout 3 nc -z "$host" "${port:-6379}" >/dev/null 2>&1; then
                    echo "{\"status\": \"reachable\", \"type\": \"redis\", \"note\": \"port accessible but redis-cli not available\"}"
                else
                    echo "{\"status\": \"unreachable\", \"type\": \"redis\"}"
                fi
            else
                echo "{\"status\": \"unknown\", \"type\": \"redis\", \"reason\": \"no redis-cli or nc available\"}"
            fi
            ;;
        "mongodb")
            if command_exists mongosh; then
                if timeout 5 mongosh "$service_url" --eval "db.runCommand('ping')" >/dev/null 2>&1; then
                    echo "{\"status\": \"healthy\", \"type\": \"mongodb\"}"
                else
                    echo "{\"status\": \"unhealthy\", \"type\": \"mongodb\"}"
                fi
            elif command_exists mongo; then
                if timeout 5 mongo "$service_url" --eval "db.runCommand('ping')" >/dev/null 2>&1; then
                    echo "{\"status\": \"healthy\", \"type\": \"mongodb\"}"
                else
                    echo "{\"status\": \"unhealthy\", \"type\": \"mongodb\"}"
                fi
            elif command_exists nc; then
                if timeout 3 nc -z "$host" "${port:-27017}" >/dev/null 2>&1; then
                    echo "{\"status\": \"reachable\", \"type\": \"mongodb\", \"note\": \"port accessible but mongo client not available\"}"
                else
                    echo "{\"status\": \"unreachable\", \"type\": \"mongodb\"}"
                fi
            else
                echo "{\"status\": \"unknown\", \"type\": \"mongodb\", \"reason\": \"no mongo client or nc available\"}"
            fi
            ;;
        *)
            echo "{\"status\": \"unknown\", \"reason\": \"unsupported protocol: $protocol\"}"
            ;;
    esac
}

# Get status of all external services
get_external_services_status() {
    local service_list=()
    local healthy_count=0
    local total_count=0

    for service in "${EXTERNAL_SERVICES[@]}"; do
        total_count=$((total_count + 1))
        local service_status=$(check_external_service "$service")
        local status=$(echo "$service_status" | jq -r '.status' 2>/dev/null || echo "unknown")

        if [[ "$status" == "healthy" ]]; then
            healthy_count=$((healthy_count + 1))
        fi

        service_list+=("{\"url\": \"$service\", \"status\": $service_status}")
    done

    local services_json="[$(IFS=','; echo "${service_list[*]}")]"

    echo "{
        \"total_services\": $total_count,
        \"healthy_services\": $healthy_count,
        \"services\": $services_json
    }"
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
    --k8s           Kubernetes 클러스터 및 Pod 상태 점검
    --services      외부 서비스 연결 상태 점검 (Redis, MongoDB 등)
    --nginx         Nginx 웹서버 상태 점검
    --ssl           SSL 인증서 유효성 검사 및 만료일 확인
    --logs          최근 배포 및 시스템 로그 표시
    --help, -h      이 도움말 출력

예시:
    $0                          # 기본 상태 체크
    $0 --json                   # JSON 형식 출력
    $0 --detailed --watch       # 상세 정보와 함께 실시간 모니터링
    $0 --nginx --ssl            # Nginx 및 SSL 인증서 상태 포함
    $0 --logs                   # 최근 로그 표시
    $0 --k8s --services         # Kubernetes 및 외부 서비스 상태 포함
    $0 --nginx --ssl --logs     # 웹서버 전체 점검

이 스크립트는 다음 항목들을 점검합니다:
    - Git 브랜치 및 커밋 상태
    - Docker 컨테이너 상태 (MCP 서비스 포함)
    - 포트 점유 상태 (8080, 8088, 8000, 5000, 3000, 5432, 6379, 8001, 8081)
    - 시스템 리소스 (상세 모드)
    - Nginx 웹서버 상태 (--nginx 옵션)
    - SSL 인증서 유효성 검사 (--ssl 옵션)
    - 최근 배포 및 시스템 로그 (--logs 옵션)
    - Kubernetes 클러스터 및 Pod 상태 (--k8s 옵션)
    - 외부 서비스 연결 상태 (--services 옵션)

외부 서비스 모니터링:
    - Redis (localhost:6379)
    - MongoDB (localhost:27017)
    - HTTP Health 엔드포인트 (localhost:3000, localhost:8080)
    - GitHub API 연결성

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
        --k8s)
            CHECK_K8S=true
            shift
            ;;
        --services)
            CHECK_SERVICES=true
            shift
            ;;
        --nginx)
            CHECK_NGINX=true
            shift
            ;;
        --ssl)
            CHECK_SSL=true
            shift
            ;;
        --logs)
            SHOW_LOGS=true
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