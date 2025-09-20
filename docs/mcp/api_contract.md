# API 계약(초안)

GET /health -> {"ok":true}
GET /api/v1/policy/match?applicant=... -> [MatchScore]
GET /api/v1/stock/signals?universe=... -> [Signal]

## 공통 응답 래퍼
{ "ok": true, "data": ... , "ts": "...ISO8601" }
