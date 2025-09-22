# Post-Push Troubleshoot
- 시간: 2025-09-22 16:18:10 KST (Asia/Seoul)
- 로컬 HEAD: 5d78749
- 증상: HTTPS 인증/네트워크로 push 실패

## 복구(권장: SSH)
1) GitHub → Settings → SSH and GPG keys → 로컬 공개키 등록(~/.ssh/id_ed25519.pub)
2) 원격 확인: `git remote -v` (ssh 경로 여부)
3) 푸시: `git push origin main`

## 대안(gh CLI)
- `gh auth login` 후 `git push origin main`

## 오프라인 백업
- 번들: REPORTS/incident-center/v1.0.2-planning/main_backup_20250922_161810.bundle
- SHA256: 9b6930a6267e10d405bd945a841fb83e0b0c190b7b0f7b0f61b8552ded4b5513
# Post-Push Manual SSH Key Guide
- 시각: 2025-09-22 16:22:20 KST (Asia/Seoul)
- 공개키(복사하여 GitHub → Settings → SSH and GPG keys → New SSH key):
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBgGWLKztR8aoxjk7eg0VQvEBggudI9Uu3GiJcIPi09H youareplan-ceo@mcp-map-company
```

## Push Result
- 시각: 2025-09-22 16:22:20 KST (Asia/Seoul)
- 결과: ❌ 실패
- 조치 가이드:
  1) GitHub 웹에서 SSH 공개키 수동 등록(Settings → SSH and GPG keys)
  2) 'git remote -v' 확인 후 재시도: git push origin main
  3) 또는 'gh auth login' 다시 수행 후 재시도
# Post-Push Manual SSH Key Guide
- 시각: 2025-09-22 16:23:19 KST (Asia/Seoul)
- 공개키(복사하여 GitHub → Settings → SSH and GPG keys → New SSH key):
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBgGWLKztR8aoxjk7eg0VQvEBggudI9Uu3GiJcIPi09H youareplan-ceo@mcp-map-company
```

## Push Result
- 시각: 2025-09-22 16:23:19 KST (Asia/Seoul)
- 결과: ❌ 실패
- 조치:
  1) 웹에서 SSH 공개키 수동 등록 후 재시도
  2) 또는 'gh auth login' 재실행 후 'git push origin main'

## Push Result
- 시각: 2025-09-22 16:28:35 KST (Asia/Seoul)
- 결과: ❌ 실패(SSH/HTTPS)
- 임시 조치: 번들 백업 생성 → REPORTS/incident-center/v1.0.2-planning/main_backup_20250922_162845.bundle

### 복구 가이드
1) SSH 경로 복원: `git remote set-url origin git@github.com:youareplan-ceo/mcp-map-company.git`
   - known_hosts 등록 완료 상태
   - 필요 시 GitHub에 SSH 공개키 등록 후 재시도
2) 또는 gh auth login(브라우저 로그인) 후 HTTPS로 재시도

## Push Result
- 시각: 2025-09-22 16:29:33 KST (Asia/Seoul)
- 방법: HTTPS
- 결과: ❌ 실패
- 조치:
  1) GitHub → Settings → SSH and GPG keys → 위 공개키 수동 등록
  2) 'git remote -v' 확인 후 재시도: git push origin main
  3) 또는 'gh auth login' 재실행

## Push Result
- 시각: 2025-09-22 16:35:34 KST (Asia/Seoul)
- 결과: ❌ 실패(SSH/HTTPS) — 원격 권한/인증 확인 필요
- 조치: 1) GitHub에 SSH 공개키 수동 등록  2) gh auth login 재실행  3) 재푸시: git push origin main
