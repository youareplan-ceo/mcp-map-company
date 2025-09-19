# StockPilot AI Backend

한국 주식시장에 특화된 AI 투자 코파일럿 백엔드 API

## 🚀 주요 기능

### REST API 엔드포인트
- **GET /api/v1/health** - 헬스체크
- **GET /api/v1/market/status** - 한국 시장 상태
- **GET /api/v1/stocks/search** - 종목 검색
- **POST /api/v1/stocks/{symbol}/analysis** - AI 종목 분석
- **GET /api/v1/signals/** - AI 투자 시그널
- **GET /api/v1/news/** - 뉴스 및 감정분석
- **GET /api/v1/portfolio/** - 포트폴리오 관리

### WebSocket 실시간 서비스
- **ws://localhost:8000/ws** - 실시간 데이터 스트리밍
  - 주가 실시간 업데이트
  - 새로운 AI 시그널 알림
  - 뉴스 업데이트
  - 시장 상태 변경

## 🛠 기술 스택

- **FastAPI** - 고성능 웹 프레임워크
- **WebSocket** - 실시간 양방향 통신
- **OpenAI GPT** - AI 투자 분석
- **Yahoo Finance** - 실시간 주식 데이터
- **Pydantic** - 데이터 검증 및 직렬화
- **Loguru** - 고급 로깅

## 📦 설치 및 실행

### 사전 요구사항
- Python 3.11+
- OpenAI API 키

### 설치
```bash
# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일을 편집하여 OpenAI API 키 등을 설정
```

### 개발 서버 실행
```bash
# FastAPI 개발 서버 실행
python -m app.main

# 또는 uvicorn 직접 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 프로덕션 실행
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 🔧 설정

### 환경 변수
```env
# 필수 설정
OPENAI_API_KEY=your_openai_api_key_here

# 서버 설정
HOST=0.0.0.0
PORT=8000
DEBUG=true

# CORS 설정
ALLOWED_ORIGINS=["http://localhost:3000"]

# 로깅
LOG_LEVEL=INFO
```

### 주요 설정 파일
- `app/config.py` - 전체 애플리케이션 설정
- `app/models.py` - Pydantic 데이터 모델
- `.env` - 환경 변수

## 📡 API 사용법

### 1. 헬스체크
```bash
curl http://localhost:8000/api/v1/health
```

### 2. 종목 검색
```bash
curl "http://localhost:8000/api/v1/stocks/search?q=삼성전자"
```

### 3. AI 투자 분석
```bash
curl -X POST "http://localhost:8000/api/v1/stocks/005930.KS/analysis" \
  -H "Content-Type: application/json"
```

### 4. 실시간 시장 상태
```bash
curl http://localhost:8000/api/v1/market/status
```

### 5. AI 투자 시그널
```bash
curl "http://localhost:8000/api/v1/signals/?page=1&size=20"
```

## 🔌 WebSocket 연결

### JavaScript 예시
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

// 주가 구독
ws.send(JSON.stringify({
    type: 'subscribe_prices',
    data: { symbols: ['005930.KS', '035420.KS'] }
}));

// 메시지 수신
ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('실시간 데이터:', data);
};
```

## 🏗 프로젝트 구조

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 애플리케이션
│   ├── config.py            # 설정 관리
│   ├── models.py            # Pydantic 모델
│   ├── api/
│   │   └── v1/
│   │       ├── api.py       # API 라우터 통합
│   │       └── endpoints/   # API 엔드포인트들
│   │           ├── stocks.py
│   │           ├── signals.py
│   │           ├── news.py
│   │           ├── portfolio.py
│   │           ├── market.py
│   │           └── dashboard.py
│   ├── services/           # 비즈니스 로직
│   │   ├── stock_service.py
│   │   ├── ai_service.py
│   │   ├── news_service.py
│   │   ├── signal_service.py
│   │   ├── market_service.py
│   │   ├── portfolio_service.py
│   │   └── dashboard_service.py
│   └── websocket/         # WebSocket 관리
│       ├── manager.py     # 연결 관리자
│       └── handlers.py    # 이벤트 핸들러
├── requirements.txt
├── .env.example
└── README.md
```

## 🎯 한국 시장 특화 기능

### 지원 시장
- **KOSPI** - 한국종합주가지수
- **KOSDAQ** - 코스닥시장
- **KONEX** - 코넥스시장

### 시장 시간
- **정규거래**: 09:00 - 15:30 (KST)
- **시간외거래**: 08:30-09:00, 15:30-16:00
- **휴장일**: 주말, 한국 공휴일

### 종목 검색
- 한글 종목명 검색 지원
- 종목 코드 (.KS, .KQ 접미사)
- 업종별 분류

## 🤖 AI 기능

### GPT 기반 투자 분석
- 기술적 분석 통합
- 뉴스 감정 분석 반영
- 위험도 평가
- 목표가 제시

### 투자 시그널
- STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
- 신뢰도 점수 (0-100)
- 투자 기간 추천
- 위험 요소 분석

## 📊 실시간 데이터

### WebSocket 이벤트
- `price_update` - 주가 실시간 업데이트
- `signal_update` - 새로운 AI 시그널
- `news_update` - 뉴스 업데이트
- `market_status` - 시장 상태 변경

### 구독 관리
```javascript
// 주가 구독
ws.send(JSON.stringify({
    type: 'subscribe_prices',
    data: { symbols: ['005930.KS', '035420.KS'] }
}));

// 시장 상태 구독
ws.send(JSON.stringify({
    type: 'subscribe_market',
    data: {}
}));
```

## 🔍 디버깅 및 모니터링

### 로그 확인
- 애플리케이션 로그는 콘솔에 출력
- 로그 레벨: DEBUG, INFO, WARNING, ERROR
- 구조화된 로그 포맷 (시간, 레벨, 모듈, 메시지)

### API 문서
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 서버 상태
- 헬스체크: http://localhost:8000/api/v1/health
- 서비스 상태: http://localhost:8000/api/v1/status

## 🚀 배포

### Docker 배포 (권장)
```bash
# Dockerfile 생성 후
docker build -t stockpilot-ai-backend .
docker run -p 8000:8000 --env-file .env stockpilot-ai-backend
```

### 환경별 설정
- **개발**: DEBUG=true, 상세 로깅
- **스테이징**: 테스트 환경 설정
- **프로덕션**: DEBUG=false, 최적화된 설정

## 🔐 보안

### API 보안
- CORS 설정으로 허용된 도메인만 접근
- OpenAI API 키 환경 변수로 관리
- 민감 정보 로깅 방지

### WebSocket 보안
- 연결 수 제한
- 비활성 연결 자동 정리
- 메시지 크기 제한

## 🤝 프론트엔드 연동

### CORS 설정
```python
ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React 개발 서버
    "http://127.0.0.1:3000"
]
```

### API 베이스 URL
- 개발: `http://localhost:8000/api/v1`
- WebSocket: `ws://localhost:8000/ws`

## 📝 개발 가이드

### 새 엔드포인트 추가
1. `app/api/v1/endpoints/` 에 파일 생성
2. `app/api/v1/api.py` 에 라우터 등록
3. 필요시 `app/models.py` 에 모델 추가

### 서비스 로직 추가
1. `app/services/` 에 서비스 클래스 생성
2. 엔드포인트에서 서비스 호출
3. 에러 처리 및 로깅 추가

## ❗ 문제 해결

### 자주 발생하는 이슈
1. **OpenAI API 키 오류**: `.env` 파일에 올바른 API 키 설정
2. **CORS 오류**: `ALLOWED_ORIGINS`에 프론트엔드 주소 추가
3. **포트 충돌**: `PORT` 환경 변수로 포트 변경

### 로그 확인
```bash
# 실시간 로그 확인
python -m app.main

# 특정 레벨만 확인
LOG_LEVEL=DEBUG python -m app.main
```

---

💡 **문의사항**: GitHub Issues를 통해 문의해 주세요.
🚀 **StockPilot AI - 한국 주식 투자의 새로운 경험**