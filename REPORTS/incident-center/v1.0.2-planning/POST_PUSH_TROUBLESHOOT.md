# Post-Push Troubleshoot (자동 생성)
- 시각: 2025-09-22 16:15:33 KST (Asia/Seoul)
- 로컬 최신 커밋: dc8a2c5
- 증상: git push origin main 실패(네트워크/인증 추정)

## 복구(선택 1: SSH)
1) GitHub → Settings → SSH and GPG keys → 로컬 공개키 등록(~/.ssh/id_ed25519.pub)
2) 원격 확인: `git remote -v` (ssh 경로인지 확인)
3) 푸시: `git push origin main`

## 복구(선택 2: gh CLI)
1) `gh auth login` 실행(HTTPS → Browser Login)
2) `git push origin main`

## 오프라인 백업에서 복원
- 번들 파일: REPORTS/incident-center/v1.0.2-planning/mcp-map-company_main_20250922_161533.bundle
- 다른 환경에서:
  ```
  git clone --bare https://github.com/youareplan-ceo/mcp-map-company.git tmp.git || true
  git clone tmp.git work && cd work
  git bundle verify "../REPORTS/incident-center/v1.0.2-planning/mcp-map-company_main_20250922_161533.bundle"
  git pull "../REPORTS/incident-center/v1.0.2-planning/mcp-map-company_main_20250922_161533.bundle" main
  ```

> 주의: 문서/자동화 전용 변경(🔒 no-deploy). 시크릿 값 입력 금지.
