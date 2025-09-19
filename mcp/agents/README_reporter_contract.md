# policy_reporter I/O 계약(뼈대)
입력:
- data/scores.json
- docs/report_templates/policy_brief.md

출력:
- docs/out/{applicant_id}_brief.md

흐름(뼈대):
1) applicant_id 별 상위 N개 프로그램 정렬(score desc)
2) 템플릿 필드 바인딩(program_name, score, limit, rate 등)
3) 파일로 저장 후(경로 규칙 고정), 알림 단계에서 링크만 전송
