# MCP-Map

## 📑 map-map 프로세스 방향
(방금 정리한 전체 설계 문서 내용 복붙)

# 🚀 MCP-MAP Project

AI 기반 주식 자동매매 시스템 with MCP (Model Context Protocol)

## 📁 프로젝트 구조

```
mcp-map/
├── 📱 web/              # Vercel 배포용 대시보드 (UI만)
│   ├── index.html       # 메인 대시보드
│   └── api.js           # API 연결 모듈
│
├── 🧠 mcp/              # MCP 서버 (로컬 실행)
│   ├── stockpilot/      # 주식 분석 MCP
│   ├── linear_server/   # 프로젝트 관리 MCP
│   └── github_server/   # GitHub 연동 MCP
│
├── 🤖 scripts/          # 자동화 스크립트 (로컬 실행)
│   ├── run_stockpilot.py
│   ├── paper_trading_analyzer.py
│   └── performance_dashboard.py
│
└── 📊 docs/             # 문서
```

## 🌐 배포 아키텍처

```
[Vercel Cloud] ← API 통신 → [회장님 로컬 서버]
     ↓                              ↓
  웹 대시보드                   MCP 서버들
  (UI 표시만)                 (실제 작업 수행)
```

### Vercel (클라우드)
- **역할**: UI 표시, 시각화
- **내용**: `web/` 폴더만 배포
- **용량**: < 1MB (가벼움)
- **접속**: https://mcp-map.vercel.app

### 로컬 서버 (회장님 컴퓨터)
- **역할**: 실제 데이터 처리, AI 분석
- **내용**: MCP 서버, Python 스크립트
- **보안**: API 키, 민감 정보 안전하게 보관

## 🚀 빠른 시작

### 1. UI 대시보드 접속
```
https://mcp-map.vercel.app
```

### 2. 로컬 MCP 서버 실행
```bash
# MCP 서버 시작
python run_stockpilot.py

# API 서버 시작 (대시보드와 연결용)
python stockpilot_master.py --api-mode
```

### 3. 연결 확인
- 대시보드 우측 상단 "⚡ 서버 상태" 확인
- 초록색 불 = 연결됨
- 빨간색 불 = 연결 안됨

## 📊 주요 기능

### 대시보드 (Vercel)
- ✅ 실시간 주식 현황
- ✅ 포트폴리오 구성 차트
- ✅ 수익률 추이 그래프
- ✅ AI 추천 종목 표시
- ✅ 모바일 반응형 디자인

### MCP 서버 (로컬)
- ✅ 실시간 주식 데이터 수집
- ✅ AI 기반 매매 신호 생성
- ✅ 자동 매매 실행
- ✅ 리스크 관리
- ✅ 백테스팅

## 🔧 설정

### Vercel 환경변수 (필요 없음!)
- UI만 배포하므로 API 키 불필요
- 모든 민감 정보는 로컬에 보관

### 로컬 환경변수 (.env)
```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
# 기타 API 키들
```

## 📝 개발 노트

### UI 수정하기
```bash
# web/index.html 편집
# 자동으로 Vercel에 배포됨
```

### 새 기능 추가
1. 로컬: Python 스크립트 추가
2. UI: web/index.html에 표시 추가
3. API: api.js에 연결 추가

## 🎯 로드맵

- [x] UI/백엔드 분리
- [x] Vercel 배포 설정
- [ ] WebSocket 실시간 연결
- [ ] 모바일 앱 개발
- [ ] AI 성능 개선

## 📞 문의

CEO: ceo@youareplan.co.kr

---

**Made with ❤️ by YouArePlan**
