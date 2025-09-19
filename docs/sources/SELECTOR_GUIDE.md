# 셀렉터/포맷 가이드(뼈대)
- selectors.* : CSS 셀렉터 또는 "css@attr" 형식으로 속성 추출
- date_format.period_range : "시작~종료" 범위 문자열의 포맷 힌트
- 실제 파서는 이 힌트를 참고해 parse_period(periodText) 수행 (추후 구현)

예)
- item_link: "a.tit@href" → a.tit 의 href 속성 값
- period_range: "YYYY.MM.DD~YYYY.MM.DD" → 공백/구분자 차이는 파서에서 허용
