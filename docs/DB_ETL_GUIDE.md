# DB ETL (주기화)

- GitHub Actions 워크플로: `.github/workflows/db-etl.yml`
- 매일 새벽 3시 KST 자동 실행
- 단계: db-init → db-ingest → db-health

## 로컬 확인
- `make db-init`
- `make db-ingest`
- `make db-health`
