# 정책자금 소스(뼈대)
- schemas/policy_sources.yaml 을 단일 진실원으로 사용
- 목록형(crawling) + API형 혼합
- cadence(주기)는 운영 스케줄러(bin/schedule)와 매핑
- 실제 네트워크/파싱 로직은 추후 구현
