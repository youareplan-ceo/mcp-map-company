# MCP Map Company 롤백 절차서

## 🔒 문서 잠금 (최종 고정)

| 항목 | 값 |
|------|---|
| **잠금 시각** | 2025-09-22 14:01:00 KST (Asia/Seoul) |
| **브랜치** | main |
| **최신 커밋** | a83d98d chore(incident-center): normalize REPORTS links |
| **작성자** | Claude Code + 김실장 검수 |
| **상태** | 🔒 LOCKED - 롤백 절차 확정 |

---

## 📋 롤백 유형별 절차

### 1. 태그/릴리스 Draft 원복

#### 🎯 대상 상황
- GitHub Release Draft 내용 오류
- 첨부 자산 파일 문제
- 릴리스 메타데이터 수정 필요

#### ✅ 점검표 (Tag/Release Rollback)
- [ ] **현재 상태 확인**
  - [ ] `git tag -l | grep incident-center` → 태그 목록 확인
  - [ ] GitHub Releases 페이지에서 Draft 상태 확인
  - [ ] 첨부 자산 파일 다운로드 백업

- [ ] **Draft 롤백 실행**
  - [ ] GitHub UI에서 Release Draft 삭제
  - [ ] 로컬 태그 삭제: `git tag -d incident-center-v1.0.1-pre-merged`
  - [ ] 원격 태그 삭제: `git push --delete origin incident-center-v1.0.1-pre-merged`

- [ ] **재생성 준비**
  - [ ] POST_MERGE_TAG_RELEASE.md에서 "✅ 생성 완료" → "⏳ 롤백 후 재생성 예정" 변경
  - [ ] TAG_RELEASE_DRAFT.md 내용 수정 (오류 사항 반영)
  - [ ] 자산 파일 재검토 및 크기 확인

- [ ] **재생성 실행**
  - [ ] 수정된 내용으로 태그 재생성
  - [ ] 새 Release Draft 생성
  - [ ] 자산 파일 재첨부 및 검증

#### 🔄 복구 시간
- **예상 소요**: 15-30분
- **확인 단계**: 5분
- **롤백 실행**: 10분
- **재생성**: 10-15분

---

### 2. Merge Revert (병합 되돌리기)

#### 🎯 대상 상황
- 병합 후 치명적 오류 발견
- 코드 품질 심각한 문제
- 보안 취약점 감지

#### ⚠️ 위험 경고
**이 작업은 매우 위험하므로 김실장 승인 후에만 실행**

#### ✅ 점검표 (Merge Revert)
- [ ] **사전 준비**
  - [ ] 현재 main HEAD 확인: `git rev-parse HEAD`
  - [ ] 병합 커밋 해시 확인: `git log --oneline -10`
  - [ ] 백업 브랜치 생성: `git checkout -b backup/pre-revert-$(date +%Y%m%d)`

- [ ] **영향도 분석**
  - [ ] 병합 이후 추가 커밋 개수 확인
  - [ ] 다른 개발자의 작업 영향 범위 검토
  - [ ] CI/CD 파이프라인 중단 필요성 판단

- [ ] **Revert 실행**
  - [ ] 병합 커밋 revert: `git revert -m 1 <merge-commit-hash>`
  - [ ] 관련 태그 삭제 (상기 1번 절차 참조)
  - [ ] Release Draft 삭제

- [ ] **후속 조치**
  - [ ] COMPLETE_STATUS.md 상태를 "REVERTED" 변경
  - [ ] INDEX.md에서 revert 사유 기록
  - [ ] 팀 전체 알림 (GitHub Issue 생성)

#### 🔄 복구 시간
- **예상 소요**: 1-2시간
- **영향도 분석**: 30분
- **Revert 실행**: 15분
- **문서 업데이트**: 30분
- **검증 및 알림**: 30분

---

### 3. 문서 잠금 해제/재잠금

#### 🎯 대상 상황
- 문서 내용 긴급 수정 필요
- 메타데이터 오류 발견
- 정책 변경 반영

#### ✅ 점검표 (Document Lock Management)
- [ ] **잠금 해제**
  - [ ] 해당 문서의 "🔒 문서 잠금" 섹션 주석 처리
  - [ ] 상태를 "🔓 UNLOCKED - 수정 중" 변경
  - [ ] 수정 사유 및 담당자 기록

- [ ] **내용 수정**
  - [ ] 필요한 변경사항 적용
  - [ ] 관련 링크 및 참조 일관성 확인
  - [ ] 체크리스트 및 메타데이터 갱신

- [ ] **재잠금**
  - [ ] 새로운 잠금 시각 기록
  - [ ] 최신 커밋 해시 업데이트
  - [ ] 상태를 "🔒 LOCKED - 재잠금 완료" 변경
  - [ ] 변경 이력 CHANGELOG에 기록

#### 📋 대상 문서 목록
| 문서명 | 경로 | 잠금 여부 |
|--------|------|-----------|
| COMPLETE_STATUS.md | reports/incident-center/v1.0.1-pre/ | 🔒 |
| INDEX.md | reports/incident-center/ | 🔒 |
| ENV_REQUIRED.md | reports/incident-center/ | 🔒 |
| GOVERNANCE.md | 루트 | 🔒 |
| ROLLBACK.md | 루트 | 🔒 |

#### 🔄 복구 시간
- **예상 소요**: 10-20분
- **해제**: 2분
- **수정**: 5-15분
- **재잠금**: 3분

---

## 🚨 긴급 롤백 절차

### 즉시 대응 (30초 내)
1. **CI 중단**: GitHub Actions에서 실행 중인 워크플로 Cancel
2. **배포 차단**: Render/Vercel 자동 배포 설정 비활성화 (해당 시)
3. **알림 발송**: Slack/Discord 긴급 채널 알림

### 1차 대응 (5분 내)
1. **현재 상태 백업**: 모든 변경사항 백업 브랜치 생성
2. **원인 파악**: 에러 로그, CI 결과, PR 내용 점검
3. **롤백 유형 결정**: 상기 1-3번 중 해당 절차 선택

### 2차 대응 (30분 내)
1. **선택된 롤백 절차 실행**: 체크리스트 기반 단계별 수행
2. **검증 테스트**: incident_smoke.yml 수동 실행으로 상태 확인
3. **문서 업데이트**: 롤백 사유 및 결과 기록

---

## 📞 연락 체계

### 롤백 승인 권한
| 롤백 유형 | 승인 권한자 | 연락 방법 |
|-----------|-------------|-----------|
| **Tag/Release Draft** | Claude Code | 자동 승인 |
| **Merge Revert** | 김실장 | GitHub @youareplan-ceo 멘션 |
| **Document Lock** | Claude Code | 자동 승인 |
| **긴급 상황** | 김실장 | GitHub Issue + 즉시 멘션 |

### 에스컬레이션 체계
1. **1차**: Claude Code 자동 대응
2. **2차**: GitHub Issue 생성하여 상황 공유
3. **3차**: 김실장 직접 멘션 및 긴급 알림
4. **최종**: 외부 전문가 컨설팅 (필요 시)

---

## 📊 롤백 후 검증

### 필수 검증 항목
- [ ] **Git 상태**: `git status` 깨끗한 상태 확인
- [ ] **CI 통과**: incident_smoke.yml 성공 실행
- [ ] **링크 검사**: 주요 문서 간 링크 정상 동작
- [ ] **배지 상태**: README 배지 정상 렌더링
- [ ] **무결성**: 핵심 파일 SHA256 체크섬 일치

### 사후 보고서 작성
1. **롤백 사유**: 구체적인 문제 상황 기술
2. **실행 과정**: 실제 수행한 단계 및 소요 시간
3. **검증 결과**: 상기 검증 항목 체크 결과
4. **예방 대책**: 동일 문제 재발 방지 방안
5. **개선 제안**: 롤백 절차 개선 아이디어

---

## 🔧 롤백 도구 및 스크립트

### 자동화 스크립트 (예정)
```bash
# scripts/rollback_helper.sh (향후 개발 예정)
# - 태그 삭제 자동화
# - 문서 잠금 상태 일괄 변경
# - 백업 브랜치 자동 생성
```

### 유용한 Git 명령어
```bash
# 최근 커밋 상태 확인
git log --oneline -10

# 특정 커밋으로 되돌리기 (soft)
git reset --soft <commit-hash>

# 병합 커밋 revert
git revert -m 1 <merge-commit-hash>

# 태그 목록 확인
git tag -l | grep incident

# 원격 태그 삭제
git push --delete origin <tag-name>
```

---

**✅ 롤백 절차서 확정 완료** - 위기 상황 대응 체계 정립

*이 문서는 긴급 상황 시 참조하는 공식 절차서이며, 정기적으로 업데이트되어야 합니다.*