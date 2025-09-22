# Incident Center v1.0.1-pre 롤백 가이드

## 🎯 롤백 범위

| 항목 | 대상 | 방법 |
|------|------|------|
| **PR #3 병합** | hotfix/incident-center-v1.0.1-pre → main | Merge commit revert |
| **릴리스/태그** | incident-center-v1.0.1-pre-merged | Draft 삭제, 태그 제거 |
| **문서 상태** | REPORTS/incident-center/ | 잠금 상태 원복 |

## 🔄 PR #3 병합 Revert 절차

### 1. Merge Commit 확인
```bash
# main 브랜치로 전환
git checkout main
git pull origin main

# 병합 커밋 확인 (예상: "Merge pull request #3 from...")
git log --oneline -5 --grep="Merge pull request #3"
```

### 2. Merge Commit Revert 실행
```bash
# 병합 커밋 해시 확인 후 revert (예시: abc1234)
git revert -m 1 [MERGE_COMMIT_HASH]

# revert 커밋 메시지 예시:
# "Revert merge of PR #3 (hotfix/incident-center-v1.0.1-pre)
#
# - Reason: [롤백 사유]
# - Date: 2025-09-22
# - Operator: [운영자명]"
```

### 3. Revert 결과 검증
```bash
# 변경사항 확인
git show HEAD

# 롤백 후 상태 확인
ls -la scripts/incident_post_release_smoke.sh scripts/dashboard_smoke_incidents.sh
grep -A 5 "incident-smoke" Makefile
```

## 🏷️ 릴리스/태그 제거 절차 (필요 시)

### 1. Draft 릴리스 삭제
```bash
# GitHub CLI로 릴리스 목록 확인
gh release list

# Draft 릴리스 삭제 (해당하는 경우)
gh release delete incident-center-v1.0.1-pre-merged --yes
```

### 2. 태그 제거
```bash
# 로컬 태그 확인
git tag -l | grep incident-center-v1.0.1-pre

# 로컬 태그 삭제
git tag -d incident-center-v1.0.1-pre-merged

# 원격 태그 삭제
git push origin --delete incident-center-v1.0.1-pre-merged
```

## 📄 문서 원복 체크리스트

### 1. 핵심 문서 상태 확인
- [ ] `REPORTS/incident-center/INDEX.md` - 🔒 잠금 표기 제거
- [ ] `REPORTS/incident-center/ENV_REQUIRED.md` - 🔒 잠금 표기 제거
- [ ] `REPORTS/incident-center/v1.0.1-pre/COMPLETE_STATUS.md` - 🔒 잠금 표기 제거

### 2. 문서 재잠금 (롤백 완료 후)
```bash
# 롤백 시각으로 문서 재잠금
ROLLBACK_TIME=$(date '+%Y-%m-%d %H:%M:%S %Z')
ROLLBACK_COMMIT=$(git log --oneline -1 | cut -d' ' -f1)

# 각 문서 상단 잠금 표 업데이트:
# | **롤백 시각** | $ROLLBACK_TIME |
# | **롤백 커밋** | $ROLLBACK_COMMIT |
# | **작업자** | [운영자명] |
# | **상태** | 롤백 완료 |
```

### 3. 연관 파일 정리
- [ ] `GOVERNANCE.md` - 삭제 또는 롤백 상태로 업데이트
- [ ] `TAG_RELEASE_DRAFT.md` - 삭제 또는 비활성화
- [ ] `.github/workflows/incident_smoke.yml` - 롤백 여부 결정
- [ ] `.github/ISSUE_TEMPLATE/`, `.github/pull_request_template.md` - 유지 여부 결정

## ⚠️ 실패 시 연락 및 조치

### 1. 롤백 실패 시나리오

| 실패 유형 | 증상 | 즉시 조치 |
|----------|------|-----------|
| **Merge conflict** | revert 시 충돌 발생 | `git merge --abort` → 수동 파일 복원 |
| **태그 삭제 실패** | 권한 부족 | GitHub 관리자 연락 |
| **CI 장애** | 워크플로 오류 지속 | .github/workflows/ 임시 비활성화 |

### 2. 연락 루틴

#### 즉시 연락 (1시간 이내)
- **책임자**: 김실장
- **연락 방법**: [내부 연락처]
- **보고 내용**: 실패 유형, 현재 상태, 시도한 조치

#### 추가 지원 (필요 시)
- **기술 지원**: Claude Code 시스템 로그 확인
- **GitHub 관리**: 저장소 권한, Actions 설정 검토
- **문서 정합성**: REPORTS/ 디렉토리 전체 재검토

### 3. 복구 절차

```bash
# 1. 현재 상태 백업
git stash push -m "rollback-attempt-$(date +%Y%m%d_%H%M%S)"

# 2. 강제 리셋 (최후 수단)
git reset --hard origin/main

# 3. 수동 파일 복원 (필요 시)
git checkout HEAD~1 -- scripts/incident_post_release_smoke.sh
git checkout HEAD~1 -- scripts/dashboard_smoke_incidents.sh
git checkout HEAD~1 -- Makefile

# 4. 상태 검증
make incident-smoke-all-dry-run
```

## 🔒 롤백 완료 확인

### 검증 체크리스트
- [ ] **스크립트 상태**: incident 관련 스크립트 삭제/복원 확인
- [ ] **Makefile**: incident-smoke-* 타겟 삭제/복원 확인
- [ ] **CI 워크플로**: incident_smoke.yml 상태 확인
- [ ] **문서 정합성**: README 배지, 링크 정상 동작
- [ ] **브랜치 상태**: main 브랜치 정상, hotfix 브랜치 정리

### 최종 보고
```markdown
# 롤백 완료 보고서

## 실행 정보
- **롤백 시각**: [시각]
- **대상 PR**: #3 (hotfix/incident-center-v1.0.1-pre → main)
- **롤백 방법**: Merge commit revert
- **실행자**: [운영자명]

## 복원 상태
- [x] PR 병합 revert 완료
- [x] 태그/릴리스 정리 완료
- [x] 문서 상태 원복 완료
- [x] 시스템 정상 동작 확인

## 후속 조치
- [ ] 핫픽스 재작업 계획 수립
- [ ] 문제 원인 분석 및 개선 방안 도출
```

---

**⚠️ 주의**: 이 가이드는 사전 준비된 절차입니다. 실제 롤백 시에는 반드시 책임자 승인 하에 신중히 진행하세요.