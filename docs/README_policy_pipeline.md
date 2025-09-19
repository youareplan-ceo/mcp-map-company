# 정책자금 파이프라인 — 뼈대 운영 메모

## 흐름
Collector(fetch) → Normalizer(normalize) → DB Sync(save) → Notifier(notify)

## 경로
- 입력(raw): raw_data/policies.json
- 정리본: db/policies_normalized.json
- DB: duckdb/policies.db
- 스키마: schemas/policy_schema.yaml

## 해야 할 일(TODO)
- 수집 소스/주기 정의, 스키마 구체화, upsert 키 확정, 알림 템플릿/채널 연결
- 보안: .env에 채널 키 보관(SLACK_WEBHOOK_URL 등), 절대 git에 비밀값 커밋 금지

## 게이트(사람 승인)
- 스키마 변경, 신규 기관 추가, 알림 문구 변경은 회장님 승인 후 반영
