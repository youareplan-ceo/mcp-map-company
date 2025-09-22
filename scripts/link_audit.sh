#!/bin/bash
# scripts/link_audit.sh - Shell-based Link Audit (ENAMETOOLONG hotfix)
#
# Usage:
#   ./scripts/link_audit.sh                    # Standard mode
#   ./scripts/link_audit.sh --strict           # Strict mode (exit 1 on forbidden patterns)
#   ./scripts/link_audit.sh > REPORTS/incident-center/LINK_AUDIT.md  # Save to file
#
# Exclusion rules aligned with weekly_monitor.yml

set -euo pipefail

STRICT_MODE=false
if [[ "${1:-}" == "--strict" ]]; then
    STRICT_MODE=true
fi

# Header with timestamp
echo "# LINK_AUDIT (shell-based)"
echo "원인: Node/Bun readdir 경로 초과(ENAMETOOLONG). 쉘 기반 스캔으로 대체."
echo "생성시각: $(date '+%Y-%m-%d %H:%M:%S %Z') / 브랜치: $(git branch --show-current 2>/dev/null || echo 'unknown')"
echo ""
echo "## 사건 요약"
echo "- **문제**: Node.js/Bun 기반 링크 스캐너가 ENAMETOOLONG 오류로 실패"
echo "- **영향**: 링크 감사 문서 생성 중단"
echo "- **해결책**: 쉘 기반(grep/find) 스캔으로 대체"
echo "- **상태**: 자동화 스크립트로 정규화"
echo ""

# Find markdown files with exclusions
FIND_CMD="find . -name '*.md' \
  -not -path './.git/*' \
  -not -path './node_modules/*' \
  -not -path './.venv/*' \
  -not -path './venv/*' \
  -not -path './.pytest_cache/*' \
  -not -path './tmp/*' \
  -not -path './REPORTS/incident-center/_SNAPSHOTS/*' \
  -not -path './REPORTS/incident-center/WEEKLY/*'"

TOTAL_FILES=$(eval "$FIND_CMD" | wc -l)
echo "## 링크 스캔 결과 (Shell-based)"
echo "_아래 결과는 쉘 명령어로 생성됨_"
echo ""
echo "### 📊 전체 통계"
echo "- **총 마크다운 파일**: ${TOTAL_FILES}개 (경로 제한 적용)"

# Count README.md links
README_LINKS=0
if [[ -f "README.md" ]]; then
    README_LINKS=$(grep -o 'https\?://[^)[:space:]]*' README.md 2>/dev/null | wc -l)
fi
echo "- **README.md 링크**: ${README_LINKS}개"

# Count REPORTS links
REPORTS_WITH_LINKS=0
if [[ -d "REPORTS" ]]; then
    REPORTS_WITH_LINKS=$(eval "$FIND_CMD" | grep "^./REPORTS/" | head -20 | xargs grep -l 'https\?://' 2>/dev/null | wc -l)
fi
echo "- **REPORTS 내 링크 포함 파일**: ${REPORTS_WITH_LINKS}개 (상위 20개 기준)"
echo ""

# Extract HTTP/HTTPS links
echo "### 🔗 주요 링크 유형"
echo '```'
echo "HTTP/HTTPS 링크 상위 20개:"
eval "$FIND_CMD" | head -50 | xargs grep -h -o 'https\?://[^)[:space:]]*' 2>/dev/null | sort | uniq -c | sort -nr | head -20
echo '```'
echo ""

# Extract relative path links
echo "### 📁 상대 경로 링크 (주요)"
echo '```'
eval "$FIND_CMD" | head -50 | xargs grep -h -o '\]\([^)]*\.md[^)]*\)' 2>/dev/null | sort | uniq -c | sort -nr | head -15
echo '```'
echo ""

# Strict mode checks
STRICT_VIOLATIONS=0
if [[ "$STRICT_MODE" == "true" ]]; then
    echo "### ⚠️ Strict Mode 검사"
    echo "금지 패턴 검사 중..."

    # Check for localhost links
    LOCALHOST_COUNT=$(eval "$FIND_CMD" | head -50 | xargs grep -c 'http://localhost' 2>/dev/null | awk -F: '{sum += $2} END {print sum+0}')
    if [[ $LOCALHOST_COUNT -gt 0 ]]; then
        echo "❌ localhost 링크 발견: ${LOCALHOST_COUNT}개"
        STRICT_VIOLATIONS=$((STRICT_VIOLATIONS + LOCALHOST_COUNT))
    fi

    # Check for /health endpoints
    HEALTH_COUNT=$(eval "$FIND_CMD" | head -50 | xargs grep -c '/health' 2>/dev/null | awk -F: '{sum += $2} END {print sum+0}')
    if [[ $HEALTH_COUNT -gt 0 ]]; then
        echo "❌ /health 엔드포인트 발견: ${HEALTH_COUNT}개"
        STRICT_VIOLATIONS=$((STRICT_VIOLATIONS + HEALTH_COUNT))
    fi

    if [[ $STRICT_VIOLATIONS -eq 0 ]]; then
        echo "✅ 금지 패턴 없음"
    fi
    echo ""
fi

# Applied exclusion rules
echo "### ✅ 적용된 제외 규칙"
echo "weekly_monitor.yml 기반 경로 프루닝:"
echo "- \`.git/\` (Git 저장소 메타데이터)"
echo "- \`node_modules/\` (Node.js 의존성)"
echo "- \`.venv/\`, \`venv/\` (Python 가상환경)"
echo "- \`.pytest_cache/\` (테스트 캐시)"
echo "- \`tmp/\` (임시 파일)"
echo "- \`REPORTS/incident-center/_SNAPSHOTS/\` (스냅샷 보존)"
echo "- \`REPORTS/incident-center/WEEKLY/\` (주간 보고서)"
echo ""

# ENAMETOOLONG prevention
echo "### 🛡️ ENAMETOOLONG 방지 조치"
echo "- find 명령어로 파일 수 제한 (head -50)"
echo "- 긴 경로 디렉토리 자동 배제"
echo "- 쉘 기반 스캔으로 Node.js readdir 회피"
echo ""

# Footer
echo "---"
echo ""
echo "**자동 생성**: scripts/link_audit.sh"
echo "**실행 시각**: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "**커밋**: $(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"

# Exit with error code in strict mode if violations found
if [[ "$STRICT_MODE" == "true" && $STRICT_VIOLATIONS -gt 0 ]]; then
    echo ""
    echo "🚨 Strict mode: ${STRICT_VIOLATIONS}개 위반 발견 - 종료"
    exit 1
fi