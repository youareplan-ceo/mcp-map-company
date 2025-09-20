# Stock Module — 설계 명세

## 목표
- 시세/뉴스/재무 지표 → 규칙/ML 혼합 시그널

## 입력
- Universe: tickers[], user_positions?
- MarketData(agg): {t, o,h,l,c,v}, News: {id, title, url, published_at, sentiment}, Fundamentals: {metric: value}

## 출력
- Signal: {ticker, action(BUY|SELL|HOLD), confidence(0~1), horizon(D|W|M), reasons[]}

## 제약
- 한국 법규: 자동 매매 금지 → 알림/시나리오만 제공

## 유니버스 규칙(확장)
- `.env`의 `STOCK_UNIVERSE`는 다음을 허용:
  - 특정 심볼 리스트: `AAPL,MSFT,005930`
  - 토큰형 전시장: `ALL:US`, `ALL:KR`
  - 혼합: `ALL:US,ALL:KR,TSLA`
- 내부 해석:
  - `ALL:US` → `data/universe/us_all.csv` 로드
  - `ALL:KR` → `data/universe/kr_all.csv` 로드
- 대규모 유니버스 처리:
  - 페이징(예: 500종목 배치), 속도 제한, 리트라이 백오프 적용
  - 저장: 단계별 캐시(분봉/일봉), 시그널은 배치/증분 방식
\n> US: nasdaqtrader.com SymDir (nasdaqtraded.txt + otherlisted.txt)\n> KR: FinanceDataReader KRX/KOSDAQ 목록 사용
