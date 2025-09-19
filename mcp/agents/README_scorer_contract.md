# policy_scorer I/O 계약(뼈대)
입력:
- data/matches.json                 # matcher 결과
- schemas/policy_scoring_rules.yaml # 가점/감점 규칙
- schemas/policy_exception_rules.yaml # 예외 규칙(경미 체납 등)

출력:
- data/scores.json                  # [{ applicant_id, program_id, score:int, notes:[...] }]

흐름(뼈대):
1) eligible=True 만 스코어링 대상
2) 가점(특구/청년/여성/수출 등) + 감점(체납/부채비율 등)
3) 예외 규칙 적용(경미 체납 등) → score_delta 반영
4) 결과 저장 (data/scores.json)
