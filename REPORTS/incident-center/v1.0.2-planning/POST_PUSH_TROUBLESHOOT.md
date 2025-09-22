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
