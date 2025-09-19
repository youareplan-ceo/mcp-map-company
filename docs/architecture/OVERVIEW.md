# MCP 컨트롤 타워 아키텍처(뼈대)
- Agents: collector, normalizer, db_sync, notifier, intake, matcher, scorer, reporter
- Flows: policy_auto, policy_daily/weekly, policy_match, policy_review
- Policies: policy_human_gate
- Config: registry.yaml, logging.yaml, .env(.template)
