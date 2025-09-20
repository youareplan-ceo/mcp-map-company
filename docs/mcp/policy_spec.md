# Policy Module — 설계 명세

## 목표
- 정부/기관 공고 → 정규화 JSON → 매칭 스코어 산출

## 데이터 스키마(초안)
- Notice: {id, source, title, url, posted_at, deadline, agency, program, tags[], raw_html}
- Program: {id, name, category, eligibility{biz_age, revenue, region, tax_status}, limits{amount, rate}, docs[], contact}

## 수집 원천(1차 타겟)
- 기업마당(bizinfo), 중기부, SEMAS 공고

## 정규화 규칙
- 날짜 ISO8601, 금액 원화 정수, 지역코드 KSIC/행정동 맵

## 매칭 입력
- Applicant: {biz_no?, founder_birth?, region, industry_code, revenue_12m, tax_clearance}
## 출력
- MatchScore: {program_id, score(0~100), reasons[]}

## 매칭 규칙(초안 점수표)
- 업력(years): 0~0.5y=+5, 0.5~1y=+10, 1~3y=+20, 3~7y=+15, 7y+=+10
- 매출(최근12M, KRW): <50M=+5, 50~200M=+10, 200~500M=+15, 500M+=+10
- 지역: 본사/지점이 공고 대상 지역이면 +15, 인접권 +8
- 업종: 우대 업종 +15, 일반 +8, 제한 업종 0
- 체납: 국세/지방세 체납 無 +20, 유 +0
- 신용: 개인/기업 신용등급 상/중/하 = +15/+8/+0
- 가점: 정책 목적(청년·여성·SOC·SW 등) 해당 시 +10
- 컷오프: 총점 60 미만은 “관망”, 60~79 “조건부 가능”, 80+ “우선 대상”
