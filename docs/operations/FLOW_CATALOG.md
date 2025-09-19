# 플로우 카탈로그(뼈대)
- policy_auto:           수집→정규화→DB→알림
- policy_daily:          일일 자동 수집
- policy_weekly:         주간 리프레시
- policy_match:          인테이크→policy_auto→매칭→알림
- policy_match_validate: 인테이크→policy_auto→검증→매칭
- policy_review:         매칭→스코어→리포트→사람승인→알림
