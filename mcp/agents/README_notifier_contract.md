# policy_notifier I/O 계약(뼈대)
입력:
- docs/out/{applicant_id}_brief.md (리포트 경로)
- 환경변수: SLACK_WEBHOOK_URL / SENDER_EMAIL / RECEIVER_EMAIL

출력(예정):
- Slack: 요약 메시지 + 상위 N개 프로그램 하이라이트
- Email: 동일 요약 + 리포트 링크

주의:
- 지금은 자리만. 실제 전송 로직은 추후 구현.
