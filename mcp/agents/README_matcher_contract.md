# policy_matcher I/O 계약(뼈대)
입력:
- data/applicants.json            # 신청자 배열 [{...}]
- db/policies_normalized.json     # 정책 배열 [{...}]
- schemas/policy_matching_rules.yaml

출력:
- data/matches.json               # [{ applicant_id, program_id, eligible:boolean, reasons:[...]}]

판단 흐름(뼈대):
1) 신청자 한 명씩 반복
2) 규칙(rules) 한 건씩 적용 → when.* 조건 모두 충족하면 eligible=True
3) 미충족 항목은 reasons에 기록(예: "revenue_last12m_gte: need≥1억, got=7천만")
4) 결과를 data/matches.json에 누적

주의:
- 실제 구현은 나중에(지금은 뼈대/주석만)
- 예외/가점은 scoring 단계에서 반영
