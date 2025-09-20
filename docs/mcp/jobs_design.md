# 스케줄러/잡 설계

- pull_*: 외부 수집(HTML/API)
- normalize_*: 정규화
- score_*: 정책 매칭/시그널 생성

## 주기(초안)
- policy: pull 2h, normalize 2h, score on-demand
- stock: pull 1m(시세), 뉴스 10m, signal 5m
