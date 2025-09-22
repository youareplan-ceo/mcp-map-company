#!/bin/bash
# REPORTS Casing Guard Script
# CI/로컬 겸용 - 소문자 'reports/' 경로 검사
# Usage: ./scripts/check_reports_casing.sh
# Exit codes: 0=OK, 1=forbidden paths found
# Generated: 2025-09-22 by Claude Code

set -e

echo "🛡️  REPORTS Casing Guard: 전체 레포지토리 검사 중..."

# 모든 추적 중인 파일 검사
tracked_files=$(git ls-files)
forbidden_tracked=$(echo "$tracked_files" | grep -E "(^|/)reports(/|$)" || true)

# 스테이징된 파일 검사 (로컬 실행 시)
if git rev-parse --git-dir > /dev/null 2>&1; then
    staged_files=$(git diff --cached --name-only 2>/dev/null || true)
    forbidden_staged=$(echo "$staged_files" | grep -E "(^|/)reports(/|$)" || true)
else
    forbidden_staged=""
fi

# 결과 취합
all_forbidden=$(echo -e "$forbidden_tracked\\n$forbidden_staged" | grep -v "^$" | sort -u || true)

if [ -n "$all_forbidden" ]; then
    echo ""
    echo "❌ REPORTS Casing Guard: 소문자 'reports/' 경로가 발견되었습니다!"
    echo ""
    echo "🚫 금지된 파일들:"
    echo "$all_forbidden" | sed 's/^/   - /'
    echo ""
    echo "📋 해결 방법:"
    echo "   1. 'reports/' → 'REPORTS/' 경로로 변경"
    echo "   2. git mv reports REPORTS_tmp && git mv REPORTS_tmp REPORTS"
    echo "   3. 문서에서 경로 참조를 'REPORTS/'로 수정"
    echo ""
    echo "📖 자세한 가이드: MIGRATIONS/2025-09-22-reports-to-REPORTS.md"
    echo "🔗 참고: https://github.com/youareplan-ceo/mcp-map-company/pull/[PR번호]"
    echo ""
    exit 1
fi

echo "✅ OK: REPORTS casing only - 소문자 reports/ 경로 없음"
exit 0