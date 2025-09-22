# DB ETL (주기화)

- GitHub Actions 워크플로: `.github/workflows/db-etl.yml`
- 매일 새벽 3시 KST 자동 실행
- 단계: db-init → db-ingest → db-health

## 로컬 확인
- `make db-init`
- `make db-ingest`
- `make db-health`

## 아티팩트/요약
- 워크플로 실행 후 **Artifacts → `etl-summary`**에서 `last_run.json` 다운로드 가능
- 로컬 원샷 실행: `make etl-all` (init→ingest→health→summary)
