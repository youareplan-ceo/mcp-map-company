# LINK_AUDIT (shell fallback)
원인: Node/Bun readdir 경로 초과(ENAMETOOLONG). 쉘 기반 스캔으로 대체.
생성시각: 2025-09-22 14:30:40 KST / 브랜치: feature/reports-casing-guard

## 사건 요약
- **문제**: Node.js/Bun 기반 링크 스캐너가 ENAMETOOLONG 오류로 실패
- **영향**: 링크 감사 문서 생성 중단
- **해결책**: 쉘 기반(grep/find) 스캔으로 대체
- **상태**: 핫픽스 진행 중

## 링크 스캔 결과 (Shell-based)
_아래 결과는 쉘 명령어로 생성됨_

### 📊 전체 통계
- **총 마크다운 파일**: 190개 (경로 제한 적용)
- **README.md 링크**: 60개
- **REPORTS 내 링크 포함 파일**: 7개 (상위 20개 기준)

### 🔗 주요 링크 유형
```
HTTP/HTTPS 링크 상위 20개:
   5 http://localhost:8088/web/admin_dashboard.html
   4 http://localhost:8088/health
   3 https://hooks.slack.com/services/...
   3 https://discord.com/api/webhooks/...
   3 http://localhost:8000/api/v1/system/health
   2 https://yourdomain.com:3001
   2 https://yourdomain.com
   2 https://your-domain.com/web/admin_dashboard.html
   2 https://github.com/youareplan-ceo/mcp-map-company/releases/tag/...
   2 https://github.com/youareplan-ceo/mcp-map-company/pull/3
```

### 📁 상대 경로 링크 (주요)
```
   1 ](./REPORTS/incident-center/v1.0.1-pre/COMPLETE_STATUS.md
   1 ](./REPORTS/incident-center/v1.0.1-pre/ARCHIVE_MANIFEST.md
   1 ](./REPORTS/incident-center/MONITORING_GUIDE.md
   1 ](./REPORTS/incident-center/INDEX.md
   1 ](./ENV_REQUIRED.md
```

### ✅ 적용된 제외 규칙
weekly_monitor.yml 기반 경로 프루닝:
- `.git/` (Git 저장소 메타데이터)
- `node_modules/` (Node.js 의존성)
- `.venv/`, `venv/` (Python 가상환경)
- `.pytest_cache/` (테스트 캐시)

### 🛡️ ENAMETOOLONG 방지 조치
- find 명령어로 파일 수 제한 (head -50)
- 긴 경로 디렉토리 자동 배제
- 쉘 기반 스캔으로 Node.js readdir 회피

## 🚨 재발 방지 가이드

### 1. 경로 길이 모니터링
```bash
# 긴 경로 감지 (255자 초과)
find . -type f -name "*.md" | awk 'length > 255 {print length ": " $0}'

# 안전한 스캔 명령어 템플릿
find . -name "*.md" \
  -not -path "./.git/*" \
  -not -path "./node_modules/*" \
  -not -path "./.venv/*" \
  -not -path "./venv/*" \
  -not -path "./.pytest_cache/*" \
  | head -50 \
  | xargs grep -l 'https\?://' 2>/dev/null
```

### 2. weekly_monitor.yml 통합
- 동일한 제외 규칙을 모든 링크 스캔에 적용
- GitHub Actions에서 쉘 기반 스캔 우선 사용
- Node.js 기반 도구는 경로 길이 검증 후 사용

### 3. 긴급 대응 절차
1. **ENAMETOOLONG 발생 시**: 즉시 쉘 기반 스캔으로 대체
2. **장기 해결책**: `.worktrees/_SNAPSHOTS` 등 보존하며 긴 경로 정리
3. **모니터링**: weekly_monitor.yml과 동일한 패턴 유지

### 4. 권장 도구 체인
- **우선순위 1**: find + grep + xargs (쉘 기반)
- **우선순위 2**: markdown-link-check (경로 검증 후)
- **금지**: Node.js fs.readdir 기반 재귀 스캔 (긴 경로 환경에서)

---

**핫픽스 완료**: 2025-09-22 14:30:40 KST
**담당**: incident-center 자동화
**상태**: ✅ 쉘 기반 링크 감사 완료
