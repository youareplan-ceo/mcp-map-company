#!/bin/bash
# StockPilot 백업 및 복구 스크립트
# 데이터베이스, 파일, 설정 등을 자동으로 백업하고 복구하는 스크립트

set -euo pipefail

# 스크립트 정보
SCRIPT_NAME="StockPilot 백업/복구 스크립트"
VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 기본 설정
DEFAULT_BACKUP_DIR="/var/backups/stockpilot"
DEFAULT_RETENTION_DAYS=30
DEFAULT_S3_BUCKET=""

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로깅 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
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
사용법: $0 [명령] [옵션]

명령:
    backup          백업 실행
    restore         복구 실행
    list            백업 목록 조회
    cleanup         오래된 백업 정리
    test            백업 테스트 (실제 백업 안함)

백업 옵션:
    --type TYPE     백업 타입 (all|db|files|config) [기본값: all]
    --dir DIR       백업 저장 디렉토리 [기본값: $DEFAULT_BACKUP_DIR]
    --compress      압축 활성화
    --encrypt       암호화 활성화
    --s3            S3에 업로드
    --name NAME     백업 이름 지정

복구 옵션:
    --backup NAME   복구할 백업 이름
    --type TYPE     복구 타입 (all|db|files|config)
    --force         확인 없이 강제 복구

공통 옵션:
    --config FILE   설정 파일 지정
    --verbose       상세 로그 출력
    --help          이 도움말 표시

예시:
    $0 backup --type all --compress --encrypt
    $0 backup --type db --s3
    $0 restore --backup stockpilot_20231201_120000 --type db
    $0 list
    $0 cleanup --days 30

EOF
}

# 설정 로드
load_config() {
    local config_file="${CONFIG_FILE:-$PROJECT_ROOT/.env}"
    
    if [[ -f "$config_file" ]]; then
        log_info "설정 파일 로드: $config_file"
        source "$config_file"
    else
        log_warning "설정 파일을 찾을 수 없습니다: $config_file"
    fi
    
    # 백업 설정 변수들
    export BACKUP_DIR="${BACKUP_PATH:-$DEFAULT_BACKUP_DIR}"
    export RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-$DEFAULT_RETENTION_DAYS}"
    export COMPRESS_BACKUPS="${BACKUP_COMPRESS:-true}"
    export ENCRYPT_BACKUPS="${BACKUP_ENCRYPT:-false}"
    export ENCRYPTION_KEY="${DB_BACKUP_ENCRYPT_KEY:-}"
    export S3_ENABLED="${S3_BACKUP_ENABLED:-false}"
    export S3_BUCKET="${S3_BUCKET:-$DEFAULT_S3_BUCKET}"
    export S3_ACCESS_KEY="${S3_ACCESS_KEY:-}"
    export S3_SECRET_KEY="${S3_SECRET_KEY:-}"
    export S3_REGION="${S3_REGION:-ap-northeast-2}"
}

# 백업 디렉토리 준비
prepare_backup_dir() {
    local backup_name="$1"
    local backup_path="$BACKUP_DIR/$backup_name"
    
    log_info "백업 디렉토리 준비: $backup_path"
    
    # 백업 디렉토리 생성
    if [[ ! -d "$BACKUP_DIR" ]]; then
        sudo mkdir -p "$BACKUP_DIR"
        sudo chown $USER:$USER "$BACKUP_DIR" 2>/dev/null || true
    fi
    
    mkdir -p "$backup_path"
    echo "$backup_path"
}

# 데이터베이스 백업
backup_database() {
    local backup_path="$1"
    
    if [[ -z "${DATABASE_URL:-}" ]]; then
        log_warning "DATABASE_URL이 설정되지 않아 데이터베이스 백업을 건너뜁니다"
        return
    fi
    
    log_info "데이터베이스 백업 시작"
    
    local db_backup_file="$backup_path/database.sql"
    
    # PostgreSQL 백업
    if [[ "$DATABASE_URL" =~ ^postgresql:// ]]; then
        log_info "PostgreSQL 데이터베이스 백업"
        
        # 스키마와 데이터 모두 백업
        pg_dump "$DATABASE_URL" \
            --verbose \
            --format=custom \
            --file="$db_backup_file.backup" \
            || {
                log_error "PostgreSQL 백업 실패"
                return 1
            }
            
        # 텍스트 형태로도 백업 (복구 시 편의를 위해)
        pg_dump "$DATABASE_URL" \
            --verbose \
            --format=plain \
            --file="$db_backup_file" \
            || {
                log_warning "텍스트 형태 PostgreSQL 백업 실패"
            }
            
    else
        log_error "지원하지 않는 데이터베이스 타입입니다"
        return 1
    fi
    
    # 압축
    if [[ "$COMPRESS_BACKUPS" == "true" ]]; then
        log_info "데이터베이스 백업 압축 중"
        gzip "$db_backup_file"
        gzip "$db_backup_file.backup" 2>/dev/null || true
    fi
    
    log_success "데이터베이스 백업 완료"
}

# 애플리케이션 파일 백업
backup_files() {
    local backup_path="$1"
    
    log_info "애플리케이션 파일 백업 시작"
    
    local files_backup_file="$backup_path/application_files.tar"
    
    # 백업할 파일과 디렉토리들
    local backup_items=(
        "backend"
        "frontend"
        "scripts"
        "docs"
        ".env.example"
        ".env.production.example"
        "docker-compose.yml"
        "docker-compose.production.yml"
        "README.md"
    )
    
    # 제외할 패턴들
    local exclude_patterns=(
        "--exclude=node_modules"
        "--exclude=venv"
        "--exclude=.git"
        "--exclude=__pycache__"
        "--exclude=*.pyc"
        "--exclude=.DS_Store"
        "--exclude=*.log"
        "--exclude=build"
        "--exclude=dist"
        "--exclude=.coverage"
        "--exclude=htmlcov"
    )
    
    cd "$PROJECT_ROOT"
    
    # tar로 백업 생성
    tar "${exclude_patterns[@]}" -cf "$files_backup_file" "${backup_items[@]}" 2>/dev/null || {
        log_error "파일 백업 실패"
        return 1
    }
    
    # 압축
    if [[ "$COMPRESS_BACKUPS" == "true" ]]; then
        log_info "파일 백업 압축 중"
        gzip "$files_backup_file"
    fi
    
    log_success "애플리케이션 파일 백업 완료"
}

# 설정 파일 백업
backup_config() {
    local backup_path="$1"
    
    log_info "설정 파일 백업 시작"
    
    local config_backup_dir="$backup_path/config"
    mkdir -p "$config_backup_dir"
    
    # 백업할 설정 파일들
    local config_files=(
        ".env"
        ".env.production"
        ".env.staging"
        "docker-compose.yml"
        "docker-compose.production.yml"
        "docker-compose.staging.yml"
        "nginx.conf"
        "/etc/systemd/system/stockpilot.service"
    )
    
    for config_file in "${config_files[@]}"; do
        local full_path=""
        
        # 절대 경로인지 확인
        if [[ "$config_file" =~ ^/ ]]; then
            full_path="$config_file"
        else
            full_path="$PROJECT_ROOT/$config_file"
        fi
        
        if [[ -f "$full_path" ]]; then
            log_info "설정 파일 백업: $config_file"
            cp "$full_path" "$config_backup_dir/"
        else
            log_warning "설정 파일을 찾을 수 없습니다: $config_file"
        fi
    done
    
    # 메타데이터 생성
    cat > "$config_backup_dir/metadata.txt" << EOF
백업 생성 시간: $(date)
호스트명: $(hostname)
사용자: $(whoami)
Git 브랜치: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
Git 커밋: $(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
Python 버전: $(python3 --version 2>/dev/null || echo "unknown")
Node 버전: $(node --version 2>/dev/null || echo "unknown")
Docker 버전: $(docker --version 2>/dev/null || echo "unknown")
EOF
    
    log_success "설정 파일 백업 완료"
}

# 백업 암호화
encrypt_backup() {
    local backup_path="$1"
    
    if [[ "$ENCRYPT_BACKUPS" != "true" ]] || [[ -z "$ENCRYPTION_KEY" ]]; then
        return
    fi
    
    log_info "백업 암호화 중"
    
    # 백업 디렉토리를 tar로 압축
    local encrypted_file="$backup_path.encrypted.tar.gz"
    
    tar -czf - -C "$(dirname "$backup_path")" "$(basename "$backup_path")" | \
    openssl enc -aes-256-cbc -salt -pbkdf2 -pass pass:"$ENCRYPTION_KEY" -out "$encrypted_file"
    
    if [[ $? -eq 0 ]]; then
        # 원본 디렉토리 삭제
        rm -rf "$backup_path"
        log_success "백업 암호화 완료: $encrypted_file"
        echo "$encrypted_file"
    else
        log_error "백업 암호화 실패"
        return 1
    fi
}

# S3 업로드
upload_to_s3() {
    local backup_file="$1"
    local backup_name="$(basename "$backup_file")"
    
    if [[ "$S3_ENABLED" != "true" ]] || [[ -z "$S3_BUCKET" ]]; then
        return
    fi
    
    log_info "S3에 백업 업로드 중: $backup_name"
    
    # AWS CLI 설정
    export AWS_ACCESS_KEY_ID="$S3_ACCESS_KEY"
    export AWS_SECRET_ACCESS_KEY="$S3_SECRET_KEY"
    export AWS_DEFAULT_REGION="$S3_REGION"
    
    # S3 업로드
    if command -v aws >/dev/null 2>&1; then
        aws s3 cp "$backup_file" "s3://$S3_BUCKET/stockpilot-backups/$backup_name" || {
            log_error "S3 업로드 실패"
            return 1
        }
        
        # 백업 메타데이터도 업로드
        local metadata_file="/tmp/backup_metadata_$backup_name.json"
        cat > "$metadata_file" << EOF
{
    "backup_name": "$backup_name",
    "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "hostname": "$(hostname)",
    "git_commit": "$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")",
    "file_size": $(stat -f%z "$backup_file" 2>/dev/null || stat -c%s "$backup_file" 2>/dev/null || echo "0")
}
EOF
        
        aws s3 cp "$metadata_file" "s3://$S3_BUCKET/stockpilot-backups/metadata/$backup_name.json"
        rm -f "$metadata_file"
        
        log_success "S3 업로드 완료"
    else
        log_error "AWS CLI가 설치되어 있지 않습니다"
        return 1
    fi
}

# 백업 실행
run_backup() {
    local backup_type="${BACKUP_TYPE:-all}"
    local backup_name="${BACKUP_NAME:-stockpilot_$(date '+%Y%m%d_%H%M%S')}"
    
    log_info "백업 시작 - 타입: $backup_type, 이름: $backup_name"
    
    local backup_path=$(prepare_backup_dir "$backup_name")
    
    # 백업 타입에 따른 실행
    case $backup_type in
        all)
            backup_database "$backup_path"
            backup_files "$backup_path"
            backup_config "$backup_path"
            ;;
        db)
            backup_database "$backup_path"
            ;;
        files)
            backup_files "$backup_path"
            ;;
        config)
            backup_config "$backup_path"
            ;;
        *)
            log_error "지원하지 않는 백업 타입: $backup_type"
            return 1
            ;;
    esac
    
    # 백업 완료 정보 저장
    cat > "$backup_path/backup_info.txt" << EOF
백업 이름: $backup_name
백업 타입: $backup_type
생성 시간: $(date)
호스트명: $(hostname)
백업 크기: $(du -sh "$backup_path" | cut -f1)
EOF
    
    # 암호화
    local final_backup_path="$backup_path"
    if [[ "$ENCRYPT_BACKUPS" == "true" ]]; then
        final_backup_path=$(encrypt_backup "$backup_path")
    fi
    
    # S3 업로드
    if [[ "$S3_ENABLED" == "true" ]]; then
        if [[ -f "$final_backup_path" ]]; then
            upload_to_s3 "$final_backup_path"
        else
            # 디렉토리인 경우 압축 후 업로드
            local temp_archive="/tmp/${backup_name}.tar.gz"
            tar -czf "$temp_archive" -C "$(dirname "$final_backup_path")" "$(basename "$final_backup_path")"
            upload_to_s3 "$temp_archive"
            rm -f "$temp_archive"
        fi
    fi
    
    log_success "백업 완료: $backup_name"
    log_info "백업 위치: $final_backup_path"
}

# 백업 목록 조회
list_backups() {
    log_info "백업 목록 조회"
    
    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_warning "백업 디렉토리가 없습니다: $BACKUP_DIR"
        return
    fi
    
    echo ""
    echo "로컬 백업 목록:"
    echo "----------------------------------------"
    
    local found_backups=false
    for backup in "$BACKUP_DIR"/stockpilot_*; do
        if [[ -e "$backup" ]]; then
            local backup_name=$(basename "$backup")
            local backup_date="unknown"
            local backup_size="unknown"
            
            # 백업 정보 파일에서 정보 추출
            if [[ -f "$backup/backup_info.txt" ]]; then
                backup_date=$(grep "생성 시간:" "$backup/backup_info.txt" | cut -d: -f2- | xargs)
                backup_size=$(grep "백업 크기:" "$backup/backup_info.txt" | cut -d: -f2 | xargs)
            elif [[ -f "$backup" ]]; then
                backup_date=$(stat -f%Sm -t "%Y-%m-%d %H:%M:%S" "$backup" 2>/dev/null || stat -c %y "$backup" 2>/dev/null | cut -d. -f1)
                backup_size=$(du -sh "$backup" | cut -f1)
            elif [[ -d "$backup" ]]; then
                backup_date=$(stat -f%Sm -t "%Y-%m-%d %H:%M:%S" "$backup" 2>/dev/null || stat -c %y "$backup" 2>/dev/null | cut -d. -f1)
                backup_size=$(du -sh "$backup" | cut -f1)
            fi
            
            echo "이름: $backup_name"
            echo "생성: $backup_date"
            echo "크기: $backup_size"
            echo "경로: $backup"
            echo ""
            found_backups=true
        fi
    done
    
    if [[ "$found_backups" != "true" ]]; then
        echo "백업을 찾을 수 없습니다."
    fi
    
    # S3 백업 목록도 조회
    if [[ "$S3_ENABLED" == "true" ]] && command -v aws >/dev/null 2>&1; then
        echo ""
        echo "S3 백업 목록:"
        echo "----------------------------------------"
        
        export AWS_ACCESS_KEY_ID="$S3_ACCESS_KEY"
        export AWS_SECRET_ACCESS_KEY="$S3_SECRET_KEY"
        export AWS_DEFAULT_REGION="$S3_REGION"
        
        aws s3 ls "s3://$S3_BUCKET/stockpilot-backups/" --human-readable || {
            log_warning "S3 백업 목록 조회 실패"
        }
    fi
}

# 백업 복구
restore_backup() {
    local backup_name="$1"
    local restore_type="${RESTORE_TYPE:-all}"
    
    if [[ -z "$backup_name" ]]; then
        log_error "복구할 백업 이름을 지정해야 합니다"
        return 1
    fi
    
    log_info "백업 복구 시작 - 백업: $backup_name, 타입: $restore_type"
    
    # 백업 파일/디렉토리 찾기
    local backup_path=""
    local temp_extract_dir=""
    
    # 로컬에서 백업 찾기
    if [[ -d "$BACKUP_DIR/$backup_name" ]]; then
        backup_path="$BACKUP_DIR/$backup_name"
    elif [[ -f "$BACKUP_DIR/$backup_name" ]]; then
        backup_path="$BACKUP_DIR/$backup_name"
    elif [[ -f "$BACKUP_DIR/${backup_name}.tar.gz" ]]; then
        backup_path="$BACKUP_DIR/${backup_name}.tar.gz"
    elif [[ -f "$BACKUP_DIR/${backup_name}.encrypted.tar.gz" ]]; then
        backup_path="$BACKUP_DIR/${backup_name}.encrypted.tar.gz"
    else
        # S3에서 다운로드 시도
        if [[ "$S3_ENABLED" == "true" ]] && command -v aws >/dev/null 2>&1; then
            log_info "S3에서 백업 다운로드 중"
            
            export AWS_ACCESS_KEY_ID="$S3_ACCESS_KEY"
            export AWS_SECRET_ACCESS_KEY="$S3_SECRET_KEY"
            export AWS_DEFAULT_REGION="$S3_REGION"
            
            local temp_backup="/tmp/$backup_name"
            aws s3 cp "s3://$S3_BUCKET/stockpilot-backups/$backup_name" "$temp_backup" || {
                log_error "S3에서 백업 다운로드 실패"
                return 1
            }
            backup_path="$temp_backup"
        else
            log_error "백업을 찾을 수 없습니다: $backup_name"
            return 1
        fi
    fi
    
    # 압축/암호화된 백업 해제
    if [[ -f "$backup_path" ]]; then
        temp_extract_dir="/tmp/restore_$backup_name_$(date +%s)"
        mkdir -p "$temp_extract_dir"
        
        if [[ "$backup_path" =~ \.encrypted\. ]]; then
            # 암호화된 백업 복호화
            if [[ -z "$ENCRYPTION_KEY" ]]; then
                log_error "암호화된 백업이지만 복호화 키가 없습니다"
                return 1
            fi
            
            log_info "암호화된 백업 복호화 중"
            openssl enc -aes-256-cbc -d -salt -pbkdf2 -pass pass:"$ENCRYPTION_KEY" -in "$backup_path" | \
            tar -xzf - -C "$temp_extract_dir" || {
                log_error "백업 복호화 실패"
                return 1
            }
            
        elif [[ "$backup_path" =~ \.tar\.gz$ ]]; then
            # 압축된 백업 해제
            log_info "압축된 백업 해제 중"
            tar -xzf "$backup_path" -C "$temp_extract_dir" || {
                log_error "백업 압축 해제 실패"
                return 1
            }
        fi
        
        # 해제된 디렉토리를 backup_path로 설정
        local extracted_dir=$(find "$temp_extract_dir" -maxdepth 1 -type d -name "stockpilot_*" | head -1)
        if [[ -n "$extracted_dir" ]]; then
            backup_path="$extracted_dir"
        else
            backup_path="$temp_extract_dir"
        fi
    fi
    
    # 복구 확인
    if [[ "$FORCE_RESTORE" != "true" ]]; then
        echo -n "백업을 복구하시겠습니까? 기존 데이터가 덮어쓰여질 수 있습니다 (y/N): "
        read -r confirmation
        if [[ "$confirmation" != "y" && "$confirmation" != "Y" ]]; then
            log_info "복구가 취소되었습니다"
            [[ -n "$temp_extract_dir" ]] && rm -rf "$temp_extract_dir"
            return 0
        fi
    fi
    
    # 복구 타입에 따른 실행
    case $restore_type in
        all|db)
            restore_database "$backup_path"
            [[ "$restore_type" == "db" ]] && break
            ;;&
        all|files)
            restore_files "$backup_path"
            [[ "$restore_type" == "files" ]] && break
            ;;&
        all|config)
            restore_config "$backup_path"
            [[ "$restore_type" == "config" ]] && break
            ;;
        *)
            log_error "지원하지 않는 복구 타입: $restore_type"
            [[ -n "$temp_extract_dir" ]] && rm -rf "$temp_extract_dir"
            return 1
            ;;
    esac
    
    # 임시 파일 정리
    [[ -n "$temp_extract_dir" ]] && rm -rf "$temp_extract_dir"
    
    log_success "백업 복구 완료"
}

# 데이터베이스 복구
restore_database() {
    local backup_path="$1"
    
    if [[ -z "${DATABASE_URL:-}" ]]; then
        log_warning "DATABASE_URL이 설정되지 않아 데이터베이스 복구를 건너뜁니다"
        return
    fi
    
    log_info "데이터베이스 복구 시작"
    
    # 백업 파일 찾기
    local db_backup_file=""
    if [[ -f "$backup_path/database.sql.gz" ]]; then
        db_backup_file="$backup_path/database.sql.gz"
    elif [[ -f "$backup_path/database.sql" ]]; then
        db_backup_file="$backup_path/database.sql"
    elif [[ -f "$backup_path/database.sql.backup.gz" ]]; then
        db_backup_file="$backup_path/database.sql.backup.gz"
    elif [[ -f "$backup_path/database.sql.backup" ]]; then
        db_backup_file="$backup_path/database.sql.backup"
    else
        log_error "데이터베이스 백업 파일을 찾을 수 없습니다"
        return 1
    fi
    
    log_info "데이터베이스 백업 파일: $db_backup_file"
    
    # PostgreSQL 복구
    if [[ "$DATABASE_URL" =~ ^postgresql:// ]]; then
        log_info "PostgreSQL 데이터베이스 복구"
        
        if [[ "$db_backup_file" =~ \.gz$ ]]; then
            # 압축된 백업 복구
            if [[ "$db_backup_file" =~ \.backup\.gz$ ]]; then
                # custom 형식 복구
                gunzip -c "$db_backup_file" | pg_restore -d "$DATABASE_URL" --clean --if-exists --verbose || {
                    log_error "PostgreSQL 복구 실패"
                    return 1
                }
            else
                # plain 형식 복구
                gunzip -c "$db_backup_file" | psql "$DATABASE_URL" || {
                    log_error "PostgreSQL 복구 실패"
                    return 1
                }
            fi
        else
            # 비압축 백업 복구
            if [[ "$db_backup_file" =~ \.backup$ ]]; then
                # custom 형식 복구
                pg_restore -d "$DATABASE_URL" --clean --if-exists --verbose "$db_backup_file" || {
                    log_error "PostgreSQL 복구 실패"
                    return 1
                }
            else
                # plain 형식 복구
                psql "$DATABASE_URL" < "$db_backup_file" || {
                    log_error "PostgreSQL 복구 실패"
                    return 1
                }
            fi
        fi
    else
        log_error "지원하지 않는 데이터베이스 타입입니다"
        return 1
    fi
    
    log_success "데이터베이스 복구 완료"
}

# 파일 복구
restore_files() {
    local backup_path="$1"
    
    log_info "애플리케이션 파일 복구 시작"
    
    # 백업 파일 찾기
    local files_backup_file=""
    if [[ -f "$backup_path/application_files.tar.gz" ]]; then
        files_backup_file="$backup_path/application_files.tar.gz"
    elif [[ -f "$backup_path/application_files.tar" ]]; then
        files_backup_file="$backup_path/application_files.tar"
    else
        log_error "파일 백업을 찾을 수 없습니다"
        return 1
    fi
    
    log_info "파일 백업: $files_backup_file"
    
    cd "$PROJECT_ROOT"
    
    # 기존 파일 백업 (안전장치)
    local backup_timestamp=$(date '+%Y%m%d_%H%M%S')
    local safety_backup_dir="/tmp/stockpilot_restore_backup_$backup_timestamp"
    mkdir -p "$safety_backup_dir"
    
    log_info "안전을 위해 기존 파일 임시 백업: $safety_backup_dir"
    cp -r backend frontend scripts docs "$safety_backup_dir/" 2>/dev/null || true
    
    # 파일 복구
    if [[ "$files_backup_file" =~ \.gz$ ]]; then
        tar -xzf "$files_backup_file" || {
            log_error "파일 복구 실패"
            return 1
        }
    else
        tar -xf "$files_backup_file" || {
            log_error "파일 복구 실패"
            return 1
        }
    fi
    
    log_success "애플리케이션 파일 복구 완료"
    log_info "기존 파일 백업 위치: $safety_backup_dir (수동으로 삭제하세요)"
}

# 설정 복구
restore_config() {
    local backup_path="$1"
    
    log_info "설정 파일 복구 시작"
    
    local config_backup_dir="$backup_path/config"
    
    if [[ ! -d "$config_backup_dir" ]]; then
        log_error "설정 백업을 찾을 수 없습니다"
        return 1
    fi
    
    # 설정 파일들 복구
    for config_file in "$config_backup_dir"/*; do
        local filename=$(basename "$config_file")
        
        # 메타데이터 파일 건너뛰기
        [[ "$filename" == "metadata.txt" ]] && continue
        
        local target_path=""
        
        # 시스템 파일인지 확인
        if [[ "$filename" == "stockpilot.service" ]]; then
            target_path="/etc/systemd/system/$filename"
            log_info "시스템 설정 파일 복구: $target_path"
            sudo cp "$config_file" "$target_path"
            sudo systemctl daemon-reload
        else
            target_path="$PROJECT_ROOT/$filename"
            log_info "설정 파일 복구: $target_path"
            cp "$config_file" "$target_path"
        fi
    done
    
    log_success "설정 파일 복구 완료"
}

# 오래된 백업 정리
cleanup_old_backups() {
    local retention_days="${CLEANUP_DAYS:-$RETENTION_DAYS}"
    
    log_info "오래된 백업 정리 시작 (보관기간: ${retention_days}일)"
    
    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_warning "백업 디렉토리가 없습니다: $BACKUP_DIR"
        return
    fi
    
    local deleted_count=0
    
    # 로컬 백업 정리
    find "$BACKUP_DIR" -name "stockpilot_*" -type d -mtime +$retention_days -exec rm -rf {} + 2>/dev/null || true
    find "$BACKUP_DIR" -name "stockpilot_*.tar.gz" -type f -mtime +$retention_days -exec rm -f {} + 2>/dev/null || true
    find "$BACKUP_DIR" -name "stockpilot_*.encrypted.tar.gz" -type f -mtime +$retention_days -exec rm -f {} + 2>/dev/null || true
    
    log_success "로컬 백업 정리 완료"
    
    # S3 백업 정리 (선택사항)
    if [[ "$S3_ENABLED" == "true" ]] && command -v aws >/dev/null 2>&1; then
        log_info "S3 백업 정리 중"
        
        export AWS_ACCESS_KEY_ID="$S3_ACCESS_KEY"
        export AWS_SECRET_ACCESS_KEY="$S3_SECRET_KEY"
        export AWS_DEFAULT_REGION="$S3_REGION"
        
        # 30일 이상 된 S3 백업 삭제
        local cutoff_date=$(date -u -d "$retention_days days ago" +"%Y-%m-%d" 2>/dev/null || date -u -v-${retention_days}d +"%Y-%m-%d" 2>/dev/null)
        
        aws s3api list-objects-v2 --bucket "$S3_BUCKET" --prefix "stockpilot-backups/" --query "Contents[?LastModified<'$cutoff_date'].Key" --output text | \
        while read -r key; do
            if [[ -n "$key" ]]; then
                aws s3 rm "s3://$S3_BUCKET/$key"
                ((deleted_count++))
            fi
        done
        
        log_success "S3 백업 정리 완료 ($deleted_count 개 파일 삭제)"
    fi
    
    log_success "백업 정리 완료"
}

# 백업 테스트
test_backup() {
    log_info "백업 테스트 시작 (실제 백업은 생성되지 않음)"
    
    # 시스템 요구사항 확인
    local missing_tools=()
    
    command -v pg_dump >/dev/null 2>&1 || missing_tools+=("postgresql-client")
    command -v tar >/dev/null 2>&1 || missing_tools+=("tar")
    command -v gzip >/dev/null 2>&1 || missing_tools+=("gzip")
    
    if [[ "$ENCRYPT_BACKUPS" == "true" ]]; then
        command -v openssl >/dev/null 2>&1 || missing_tools+=("openssl")
    fi
    
    if [[ "$S3_ENABLED" == "true" ]]; then
        command -v aws >/dev/null 2>&1 || missing_tools+=("awscli")
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "다음 도구들이 설치되어 있지 않습니다:"
        for tool in "${missing_tools[@]}"; do
            echo "  - $tool"
        done
        return 1
    fi
    
    # 데이터베이스 연결 테스트
    if [[ -n "${DATABASE_URL:-}" ]]; then
        log_info "데이터베이스 연결 테스트"
        if pg_isready -d "$DATABASE_URL" >/dev/null 2>&1; then
            log_success "데이터베이스 연결 성공"
        else
            log_error "데이터베이스 연결 실패"
            return 1
        fi
    fi
    
    # S3 연결 테스트
    if [[ "$S3_ENABLED" == "true" ]]; then
        log_info "S3 연결 테스트"
        
        export AWS_ACCESS_KEY_ID="$S3_ACCESS_KEY"
        export AWS_SECRET_ACCESS_KEY="$S3_SECRET_KEY"
        export AWS_DEFAULT_REGION="$S3_REGION"
        
        if aws s3 ls "s3://$S3_BUCKET" >/dev/null 2>&1; then
            log_success "S3 연결 성공"
        else
            log_error "S3 연결 실패"
            return 1
        fi
    fi
    
    # 백업 디렉토리 쓰기 권한 테스트
    if mkdir -p "$BACKUP_DIR" 2>/dev/null && touch "$BACKUP_DIR/.test" 2>/dev/null; then
        rm -f "$BACKUP_DIR/.test"
        log_success "백업 디렉토리 쓰기 권한 확인"
    else
        log_error "백업 디렉토리 쓰기 권한 없음: $BACKUP_DIR"
        return 1
    fi
    
    log_success "모든 백업 테스트 통과"
}

# 메인 함수
main() {
    # 매개변수 파싱
    COMMAND=""
    BACKUP_TYPE="all"
    RESTORE_TYPE="all"
    BACKUP_NAME=""
    CONFIG_FILE=""
    VERBOSE=false
    FORCE_RESTORE=false
    CLEANUP_DAYS=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            backup|restore|list|cleanup|test)
                COMMAND="$1"
                shift
                ;;
            --type)
                if [[ "$COMMAND" == "restore" ]]; then
                    RESTORE_TYPE="$2"
                else
                    BACKUP_TYPE="$2"
                fi
                shift 2
                ;;
            --backup)
                BACKUP_NAME="$2"
                shift 2
                ;;
            --name)
                BACKUP_NAME="$2"
                shift 2
                ;;
            --dir)
                BACKUP_DIR="$2"
                shift 2
                ;;
            --config)
                CONFIG_FILE="$2"
                shift 2
                ;;
            --days)
                CLEANUP_DAYS="$2"
                shift 2
                ;;
            --compress)
                COMPRESS_BACKUPS=true
                shift
                ;;
            --encrypt)
                ENCRYPT_BACKUPS=true
                shift
                ;;
            --s3)
                S3_ENABLED=true
                shift
                ;;
            --force)
                FORCE_RESTORE=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
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
    
    # 명령어 확인
    if [[ -z "$COMMAND" ]]; then
        log_error "명령을 지정해야 합니다"
        show_help
        exit 1
    fi
    
    # 배너 출력
    print_banner
    
    # 설정 로드
    load_config
    
    # 상세 로그 설정
    if [[ "$VERBOSE" == "true" ]]; then
        set -x
    fi
    
    # 명령 실행
    case $COMMAND in
        backup)
            run_backup
            ;;
        restore)
            if [[ -z "$BACKUP_NAME" ]]; then
                log_error "복구할 백업 이름을 지정해야 합니다 (--backup NAME)"
                exit 1
            fi
            restore_backup "$BACKUP_NAME"
            ;;
        list)
            list_backups
            ;;
        cleanup)
            cleanup_old_backups
            ;;
        test)
            test_backup
            ;;
        *)
            log_error "지원하지 않는 명령: $COMMAND"
            exit 1
            ;;
    esac
    
    log_success "작업이 성공적으로 완료되었습니다! 🎉"
}

# 스크립트 실행
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi