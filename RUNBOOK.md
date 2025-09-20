# RUNBOOK — 사고 대응/복구 절차

## 0. 사전 체크
git status
curl -sS http://localhost:8088/health

## 1. 고객용 index.html이 관리자 화면으로 덮였을 때
cd ~/Desktop/mcp-map-company
mv web/index.html web/admin.html
cp web/index.html.backup_api_YYYYMMDD_HHMMSS web/index.html || cp web/index.html.backup_scroll_YYYYMMDD_HHMMSS web/index.html
git add web/index.html web/admin.html
git commit -m "revert: 고객용 index.html 복구 + admin.html 분리"
git push origin main

## 2. 최신 작업 동기화(다른 기기에서)
cd ~/Desktop/mcp-map-company
git pull origin main

## 3. 안정화 브랜치 생성(복구 포인트)
git checkout -b stable/YYYYMMDD
git push origin stable/YYYYMMDD
git checkout main

## 4. 서버 헬스체크
curl -sS http://localhost:8088/health  # 정상: {"ok":true}

## 5. Render 배포 확인
- main 반영 → Render 자동 배포
- 고객: /index.html, 관리자: /admin.html 접속 점검

## 6. 추가 권장 수칙
- admin.html에 <meta name="robots" content="noindex,nofollow">
- web/robots.txt에 Disallow: /admin.html
- 변경 전 scripts/backup-index.sh로 자동 백업
