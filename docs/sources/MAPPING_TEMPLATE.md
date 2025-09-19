# 파싱 매핑 템플릿(뼈대)
- 입력: raw_data/policies.json (원시 항목 예시)
  - { source_id, anncnId, title, agency, regionText, categoryText, periodText, limit, rate, ... }

- 출력: db/policies_normalized.json (schemas/policy_schema.yaml 준수)
  - program_id = <source_id>-<anncnId>
  - title = title
  - agency = agency
  - region = tokenize(regionText)
  - category = normalize_category(categoryText)
  - apply_period = parse_period(periodText)
  - finance.limit_max = parse_amount(limit)
  - finance.rate_min/max = parse_rate(rate)
  - eligibility.* = 추후 규칙 반영
  - links.detail_url = from detail_url_template
  - raw = 원문 필드 전체 보관
