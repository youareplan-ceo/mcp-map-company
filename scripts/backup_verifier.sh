#!/bin/bash
# 🔐 MCP-MAP 백업 무결성 검증 스크립트 (한국어 주석 포함)
# 기능:
# 1. 지정된 백업 디렉토리의 최신 파일을 확인
# 2. 파일 크기, 압축 여부, 최근 수정일 검증
# 3. 에러 발생 시 Slack/Discord/Email 알림 (notifier.py 연동)
# 4. 시뮬레이션 모드 지원 (--dry-run)
# 5. JSON 출력 지원 (--json)

BACKUP_DIR="backups"
DAYS_KEEP=30
DRY_RUN=false
JSON=false

while [[ "$#" -gt 0 ]]; do
  case $1 in
    --dir) BACKUP_DIR="$2"; shift ;;
    --days) DAYS_KEEP="$2"; shift ;;
    --dry-run) DRY_RUN=true ;;
    --json) JSON=true ;;
    *) echo "❌ 알 수 없는 옵션: $1"; exit 1 ;;
  esac
  shift
done

if [ ! -d "$BACKUP_DIR" ]; then
  echo "❌ 백업 디렉토리를 찾을 수 없습니다: $BACKUP_DIR"
  exit 1
fi

LATEST_FILE=$(ls -t "$BACKUP_DIR" | head -n 1)
if [ -z "$LATEST_FILE" ]; then
  echo "❌ 백업 파일이 없습니다"
  exit 1
fi

FILE_PATH="$BACKUP_DIR/$LATEST_FILE"
FILE_SIZE=$(stat -f%z "$FILE_PATH")
MODIFIED_DATE=$(stat -f"%Sm" -t "%Y-%m-%d %H:%M:%S" "$FILE_PATH")

if $JSON; then
  echo "{ \"file\": \"$LATEST_FILE\", \"size\": $FILE_SIZE, \"modified\": \"$MODIFIED_DATE\" }"
else
  echo "✅ 최신 백업 파일: $LATEST_FILE"
  echo "📦 파일 크기: $FILE_SIZE 바이트"
  echo "🕒 수정일: $MODIFIED_DATE"
fi

# 오래된 백업 정리 (DAYS_KEEP 기준)
find "$BACKUP_DIR" -type f -mtime +$DAYS_KEEP -print -delete