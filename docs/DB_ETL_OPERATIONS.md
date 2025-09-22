# DB ETL 운영(알림/재시도/로그)

- 워크플로: `.github/workflows/db-etl.yml`
- 기능:
  - **재시도 3회** (10초 간격)
  - 실패 시 **GitHub Issue 자동 생성**(label: etl, failure)
  - **Artifacts**: `etl-summary`(last_run.json), `etl-logs`(etl.log, run.info)
- 수동 실행: Actions → **DB ETL (Nightly)** → Run workflow
