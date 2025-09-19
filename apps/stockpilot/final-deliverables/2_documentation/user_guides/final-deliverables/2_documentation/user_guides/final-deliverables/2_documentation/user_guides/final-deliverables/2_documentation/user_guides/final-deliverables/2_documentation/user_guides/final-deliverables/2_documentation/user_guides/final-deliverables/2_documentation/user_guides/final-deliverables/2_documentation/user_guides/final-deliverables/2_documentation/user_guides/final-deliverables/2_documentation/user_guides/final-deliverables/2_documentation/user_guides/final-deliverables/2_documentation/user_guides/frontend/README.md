# StockPilot AI Frontend

한국 주식시장에 특화된 AI 투자 코파일럿 대시보드 프론트엔드

## 🚀 기능

### 핵심 기능
- **실시간 대시보드**: 한국 주식시장 현황과 AI 투자 시그널 한눈에 확인
- **종목 분석**: 개별 종목에 대한 AI 분석, 기술적 지표, 뉴스 감정분석
- **포트폴리오 관리**: 보유 종목 관리 및 수익률 추적, AI 추천사항
- **AI 투자 시그널**: 실시간 AI 매수/매도 신호 및 신뢰도 점수
- **뉴스 분석**: 한국 주식 관련 뉴스 AI 감정분석 및 시장 영향도 평가

### 한국 시장 특화
- **KRX 시장 지원**: KOSPI, KOSDAQ, KONEX 시장 데이터
- **한국어 UI/UX**: 완전 한국어 인터페이스
- **한국 시장 시간**: 장중/장마감 실시간 표시 (09:00-15:30)
- **원화 표시**: 한국 원화 단위 및 포맷팅
- **한국 뉴스**: 국내 경제/증권 뉴스 소스 통합

## 🛠 기술 스택

- **Frontend Framework**: React 18 + TypeScript
- **UI 라이브러리**: Material-UI (MUI)
- **상태 관리**: TanStack Query (React Query)
- **라우팅**: React Router DOM
- **차트**: Recharts, TradingView 위젯
- **실시간 통신**: Socket.IO Client
- **HTTP 클라이언트**: Axios

## 📦 설치 및 실행

### 사전 요구사항
- Node.js 18+ 
- npm 또는 yarn

### 설치
```bash
# 의존성 설치
npm install

# 또는 yarn 사용 시
yarn install
```

### 환경 설정
```bash
# 환경변수 파일 생성
cp .env.example .env.local

# .env.local 파일을 열어 실제 값으로 수정
REACT_APP_API_BASE_URL=http://localhost:8000/api/v1
REACT_APP_WS_URL=ws://localhost:8000/ws
REACT_APP_TRADINGVIEW_API_KEY=your_api_key
```

### 개발 서버 실행
```bash
npm start
# 또는
yarn start
```

브라우저에서 http://localhost:3000 접속

### 빌드
```bash
npm run build
# 또는
yarn build
```

## 📁 프로젝트 구조

```
src/
├── components/           # 재사용 가능한 컴포넌트
│   ├── common/          # 공통 컴포넌트 (Layout, StockSearchBar 등)
│   └── charts/          # 차트 컴포넌트
├── pages/               # 페이지 컴포넌트
│   ├── Dashboard.tsx    # 메인 대시보드
│   ├── StockAnalysis.tsx # 종목 분석 페이지
│   ├── Portfolio.tsx    # 포트폴리오 관리
│   ├── Signals.tsx      # AI 시그널 페이지
│   └── News.tsx         # 뉴스 분석 페이지
├── services/            # API 서비스 레이어
│   ├── api.ts          # REST API 클라이언트
│   └── websocket.ts    # WebSocket 서비스
├── types/              # TypeScript 타입 정의
├── utils/              # 유틸리티 함수
├── env.ts              # 환경 설정
├── App.tsx             # 메인 앱 컴포넌트
└── index.tsx           # 엔트리 포인트
```

## 🔌 API 연동

### REST API 엔드포인트
- `/stocks/search` - 종목 검색
- `/stocks/{symbol}/analysis` - 종목 AI 분석
- `/dashboard/summary` - 대시보드 요약 데이터
- `/portfolio/` - 포트폴리오 관리
- `/signals/` - AI 투자 시그널
- `/news/` - 뉴스 분석 데이터

### WebSocket 이벤트
- `price_update` - 실시간 주가 업데이트
- `signal_update` - 새로운 AI 시그널
- `market_status` - 시장 상태 변경
- `news_update` - 새로운 뉴스

## 🎯 페이지별 기능

### 1. 대시보드 (`/dashboard`)
- 시장 지수 현황 (KOSPI, KOSDAQ)
- AI 시그널 분포 차트
- 인기 종목 및 급등락 종목
- 최신 뉴스 피드
- 포트폴리오 요약

### 2. 종목 분석 (`/analysis/:symbol`)
- AI 투자 분석 및 추천
- 실시간 차트 (TradingView)
- 기술적 지표
- 관련 뉴스 감정분석
- 재무 정보

### 3. 포트폴리오 (`/portfolio`)
- 보유 종목 관리
- 수익률 및 손익 현황
- 포트폴리오 구성 분석
- AI 리밸런싱 추천

### 4. AI 시그널 (`/signals`)
- 실시간 매수/매도 신호
- 신뢰도 점수 및 필터링
- 시그널 상세 분석
- 관심 종목 관리

### 5. 뉴스 분석 (`/news`)
- 주식 관련 뉴스 수집
- AI 감정 분석 결과
- 시장 영향도 평가
- 트렌딩 키워드

## 🔧 개발 가이드

### 컴포넌트 개발 규칙
- 모든 컴포넌트는 TypeScript로 작성
- Props 인터페이스 정의 필수
- 한국어 주석 작성
- Material-UI 디자인 시스템 준수

### API 서비스 사용법
```typescript
// 종목 검색 예시
import { StockService } from '../services/api';

const searchStocks = async (query: string) => {
  const results = await StockService.searchStocks(query, 10);
  return results;
};
```

### WebSocket 사용법
```typescript
// 실시간 가격 구독
import { WebSocketService } from '../services/websocket';

const wsService = WebSocketService.getInstance();
wsService.subscribePrices(['005930', '000660']);
wsService.onPriceUpdate((data) => {
  console.log('실시간 가격:', data);
});
```

## 🌐 배포

### 환경별 설정
- **개발**: 로컬 개발 서버
- **스테이징**: 테스트 환경 배포
- **프로덕션**: 실제 서비스 배포

### 빌드 최적화
- Tree shaking으로 번들 크기 최소화
- Code splitting으로 초기 로딩 시간 단축
- 이미지 및 폰트 최적화
- PWA 기능 지원

## 🚨 문제 해결

### 자주 발생하는 이슈
1. **WebSocket 연결 실패**: 백엔드 서버 상태 확인
2. **API 호출 에러**: CORS 설정 및 API 키 확인
3. **차트 렌더링 문제**: TradingView API 키 설정 확인

### 디버깅
```bash
# 개발 모드에서 로그 확인
npm start

# 네트워크 탭에서 API 호출 상태 확인
# 콘솔에서 에러 메시지 확인
```

## 📄 라이선스

MIT License

## 👥 기여

1. Fork 프로젝트
2. 기능 브랜치 생성 (`git checkout -b feature/new-feature`)
3. 변경사항 커밋 (`git commit -am 'Add new feature'`)
4. 브랜치 푸시 (`git push origin feature/new-feature`)
5. Pull Request 생성

---

💡 **문의사항**: [GitHub Issues](https://github.com/your-repo/stockpilot-ai/issues)를 통해 문의해 주세요.