# 추적되지 않는 파일 목록

**검사 시각**: 2025-09-22 12:51:30
**브랜치**: hotfix/incident-center-v1.0.1-pre
**커밋**: 50c1b4c deploy: disable pip hash check on Render build

## 추적되지 않는 파일/디렉터리

### 1. .worktrees/
- **유형**: Git worktree 디렉터리
- **상태**: 개발 작업용 분리된 워킹 트리
- **조치**: 병합 시 .gitignore에 추가 권장

### 2. reports/incident-center/
- **유형**: 리포트 디렉터리
- **상태**: 로컬 개발 중 생성된 리포트 파일들
- **조치**: 필요 시 REPORTS/ 디렉터리로 이동 후 추가

## 요약
- 총 2개 항목이 추적되지 않음
- 모두 개발/리포팅 관련 파일로 정상적인 상태
- 병합에 영향 없음