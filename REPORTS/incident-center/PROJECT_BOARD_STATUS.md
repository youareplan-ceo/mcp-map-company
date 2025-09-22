# GitHub 프로젝트 보드 상태
- 시각: 2025-09-22 16:54:15 KST (Asia/Seoul)
- 결과: ⚠️ 보드 미확인 — GitHub CLI 스코프 제한으로 웹 UI 수동 생성 필요

## 수동 생성 절차
1. **GitHub 웹 접속**: https://github.com/youareplan-ceo
2. **프로젝트 생성**: Profile → Projects → New project
3. **설정값**:
   - Title: `Incident Center v1.0.2`
   - Template: Kanban
   - Visibility: Private
4. **칸반 컬럼**: Backlog → Ready → In Progress → In Review → Done
5. **이슈 연결**: #11, #12, #13, #14, #15, #16 추가
6. **문서 업데이트**: 생성 후 PROJECTS.md에 URL/번호 반영

## GitHub CLI 제한사항
```
error: your authentication token is missing required scopes [read:project]
To request it, run: gh auth refresh -s read:project
```

- 필요 스코프: `project`, `read:project`, `repo`
- 현재 상태: 스코프 제한으로 자동화 불가

## Push 실패 최종 기록
- 시각: 2025-09-22 17:01:07 KST (Asia/Seoul)
- 브랜치: sprint1/feat-11-dom-stabilize
- 방법: HTTPS → HTTPS 대체 포함
- 조치: 번들 백업 생성 → REPORTS/incident-center/v1.0.2-planning/sprint1_feat-11-dom-stabilize_20250922_170114.bundle (SHA256: 9507890b22c4421088667e39e92cec9675540429a037a1ba97ea874d84236f03)
- 다음: SSH 공개키 등록 또는 gh auth login 후 재푸시

## Push 실패 기록
- 시각: 2025-09-22 17:07:54 KST (Asia/Seoul)
- 브랜치: sprint1/feat-11-dom-stabilize
- 방법: HTTPS → HTTPS 대체 포함
- 조치: GitHub에 SSH 공개키 등록 또는 'gh auth login' 후 재푸시 필요

## Push 실패 기록(code3)
- 시각: 2025-09-22 17:25:57 KST (Asia/Seoul)
- 브랜치: sprint1/feat-11-dom-stabilize
- 마지막 시도: HTTPS(with gh token)
- 조치 가이드:
  1) SSH 공개키 웹 UI 등록 후 SSH로 재시도 (Settings → SSH and GPG keys)
  2) 또는 gh auth login -w -s "repo,read:org,project" 재실행
  3) 또는 GITHUB_TOKEN 내리고 재실행
- 번들 백업: sprint1_feat-11-dom-stabilize_20250922_172604.bundle (SHA256: f8fc96e1835e051ccac3a63f3d6b4e21203c15b26bb080451f755b0970263d68)

## Push 실패 기록(code3)
- 시각: 2025-09-22 17:34:05 KST (Asia/Seoul)
- 브랜치: sprint1/feat-11-dom-stabilize
- 마지막 시도: HTTPS(with gh token)
- 번들 백업: sprint1_feat-11-dom-stabilize_20250922_173413.bundle (SHA256: 7f67391b15b667eee8c62d11f83dfa9cf875e78d0ed43e725c10185fda84cf0f)
- 가이드: SSH키 등록 또는 gh auth login -w -s "repo,read:org,project" 후 재시도

## #14 Batch-1 Finalization (code2)
- 시각: 2025-09-22 18:12:20 KST (Asia/Seoul)
- 브랜치: sprint1/fix-broken-links-from-15
- KPI: 404=0, 미존재=153, 앵커누락=24, 합계=177
- 조치: Manifest/Index 갱신 및 Batch-2 계획서 생성

## #14 Batch-2 준비(code2)
- 시각: 2025-09-22 18:18:31 KST (Asia/Seoul)
- 브랜치: sprint1/feat-14-batch2-prep
- 산출: BATCH2_BUCKETS(10개 단위), ISSUE_DRAFTS, META
- 정책: NO-DEPLOY(문서 전용) — 제품 코드/배포/시크릿 불변

## #14 Batch-2 Finalize(code2)
- 시각: 2025-09-22 18:24:49 KST (Asia/Seoul)
- 브랜치: sprint1/feat-14-batch2-prep
- GitHub 이슈 생성: 0개
- 산출: ISSUE_MAP.{md,json} / B2_BUCKET_01.md 링크 보강
- 정책: NO-DEPLOY (문서 전용)
