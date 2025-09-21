#!/bin/bash
# 🗑️ MCP-MAP 오래된 백업 정리 스크립트 (한국어 주석 포함)
# 기능:
# 1. 지정된 기간(기본 30일) 이상 된 백업 파일 정리
# 2. 시뮬레이션 모드 지원 (--dry-run)
# 3. JSON 출력 형식 지원 (--json)
# 4. 정리 결과 상세 로그 출력
# 5. 에러 발생 시 보안 로그에 기록

BACKUP_DIR="backups"
DAYS_KEEP=30
DRY_RUN=false
JSON_OUTPUT=false
AUTO_YES=false

# 📝 사용법 출력
show_usage() {
    echo "사용법: $0 [옵션]"
    echo "옵션:"
    echo "  --dir DIR      백업 디렉토리 지정 (기본: backups)"
    echo "  --days DAYS    보관 기간 지정 (기본: 30일)"
    echo "  --dry-run      시뮬레이션 모드 (실제 삭제 안함)"
    echo "  --json         JSON 형식으로 결과 출력"
    echo "  --yes          확인 없이 자동 실행"
    echo "  --help         이 도움말 표시"
}

# 📊 JSON 형식 결과 출력 함수
output_json() {
    local deleted_count=$1
    local total_size=$2
    local files_list=$3

    echo "{"
    echo "  \"timestamp\": \"$(date -Iseconds)\","
    echo "  \"deleted_count\": $deleted_count,"
    echo "  \"total_size_bytes\": $total_size,"
    echo "  \"backup_dir\": \"$BACKUP_DIR\","
    echo "  \"days_keep\": $DAYS_KEEP,"
    echo "  \"dry_run\": $DRY_RUN,"
    echo "  \"deleted_files\": [$files_list]"
    echo "}"
}

# 📂 인자 파싱
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --dir) BACKUP_DIR="$2"; shift ;;
        --days) DAYS_KEEP="$2"; shift ;;
        --dry-run) DRY_RUN=true ;;
        --json) JSON_OUTPUT=true ;;
        --yes) AUTO_YES=true ;;
        --help) show_usage; exit 0 ;;
        *) echo "❌ 알 수 없는 옵션: $1"; show_usage; exit 1 ;;
    esac
    shift
done

# 🔍 백업 디렉토리 존재 확인
if [ ! -d "$BACKUP_DIR" ]; then
    if $JSON_OUTPUT; then
        echo "{\"error\": \"백업 디렉토리를 찾을 수 없습니다: $BACKUP_DIR\"}"
    else
        echo "❌ 백업 디렉토리를 찾을 수 없습니다: $BACKUP_DIR"
    fi
    exit 1
fi

# 🗂️ 오래된 파일 찾기
OLD_FILES=$(find "$BACKUP_DIR" -type f -mtime +$DAYS_KEEP)

if [ -z "$OLD_FILES" ]; then
    if $JSON_OUTPUT; then
        output_json 0 0 ""
    else
        echo "✅ 정리할 오래된 백업이 없습니다 (${DAYS_KEEP}일 이상)"
    fi
    exit 0
fi

# 📊 통계 계산
FILE_COUNT=$(echo "$OLD_FILES" | wc -l)
TOTAL_SIZE=0
FILES_JSON=""

while IFS= read -r file; do
    if [ -f "$file" ]; then
        size=$(stat -f%z "$file" 2>/dev/null || echo 0)
        TOTAL_SIZE=$((TOTAL_SIZE + size))

        if [ -n "$FILES_JSON" ]; then
            FILES_JSON="$FILES_JSON, "
        fi
        FILES_JSON="$FILES_JSON\"$(basename "$file")\""
    fi
done <<< "$OLD_FILES"

# 🤔 사용자 확인 (시뮬레이션이 아닌 경우)
if [ "$DRY_RUN" = false ] && [ "$AUTO_YES" = false ]; then
    echo "⚠️  다음 파일들이 삭제됩니다:"
    echo "$OLD_FILES"
    echo ""
    echo "📊 총 ${FILE_COUNT}개 파일, $(echo "scale=2; $TOTAL_SIZE/1024/1024" | bc)MB"
    echo ""
    read -p "계속하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ 작업이 취소되었습니다"
        exit 1
    fi
fi

# 🗑️ 파일 삭제 실행
if [ "$DRY_RUN" = true ]; then
    if $JSON_OUTPUT; then
        output_json $FILE_COUNT $TOTAL_SIZE "$FILES_JSON"
    else
        echo "🧪 시뮬레이션 모드: 다음 파일들이 삭제될 예정입니다"
        echo "$OLD_FILES"
        echo "📊 총 ${FILE_COUNT}개 파일, $(echo "scale=2; $TOTAL_SIZE/1024/1024" | bc)MB"
    fi
else
    # 실제 삭제 실행
    deleted_count=0
    while IFS= read -r file; do
        if [ -f "$file" ] && rm "$file" 2>/dev/null; then
            deleted_count=$((deleted_count + 1))
        fi
    done <<< "$OLD_FILES"

    if $JSON_OUTPUT; then
        output_json $deleted_count $TOTAL_SIZE "$FILES_JSON"
    else
        echo "✅ 오래된 백업 정리 완료"
        echo "📊 삭제된 파일: ${deleted_count}개"
        echo "💾 절약된 공간: $(echo "scale=2; $TOTAL_SIZE/1024/1024" | bc)MB"
    fi

    # 🔐 보안 로그에 기록 (성공)
    if command -v python3 &> /dev/null; then
        python3 -c "
from mcp.security_logger import log_security_event
log_security_event('BACKUP_CLEANUP', '오래된 백업 ${deleted_count}개 정리 완료 (${TOTAL_SIZE} bytes)')
        " 2>/dev/null || true
    fi
fi

exit 0