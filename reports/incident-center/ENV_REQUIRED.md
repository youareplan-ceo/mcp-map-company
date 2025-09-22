# Incident Center 환경 변수 요구사항 (통합)

## 실행 정보
- **실행 커밋**: 2b761c0 (hotfix/incident-center-v1.0.1-pre)
- **최종 업데이트**: 2025-09-22 13:20 (Asia/Seoul)
- **복원 상태**: 스크립트 및 Makefile 타깃 복원 완료, 문서 표준화 완료
- **경로**: /Users/youareplan/Desktop/mcp-map-company

## API 스모크 테스트 필수 변수

### 기본 환경 변수
- `API_BASE_URL`: 인시던트 센터 API 베이스 URL
  - 기본값: `http://localhost:8000/api/v1/incidents`
  - 운영 환경: `https://your-app.onrender.com/api/v1/incidents`

### 선택적 환경 변수
- `TIMEOUT`: API 요청 타임아웃 (초, 기본값: 30)
- `DEBUG`: 상세 로그 출력 (기본값: false)
- `TEST_ENV`: 테스트 환경 지정 (local/staging/production)

## .env 파일 예시

### 로컬 개발
```bash
# Incident Center Local Development
API_BASE_URL=http://localhost:8000/api/v1/incidents
TIMEOUT=30
DEBUG=true
TEST_ENV=local
```

### Render.com 배포
```bash
# Incident Center Production
API_BASE_URL=https://mcp-map-company.onrender.com/api/v1/incidents
TIMEOUT=60
DEBUG=false
TEST_ENV=production
```

## 포트 충돌 확인

### 현재 사용 중인 포트
실행 시점에서 포트 8000번 사용 현황:
```bash
lsof -i :8000
# 결과: 사용 중인 프로세스 없음
```

### 포트 8099 (대시보드)
실행 시점에서 포트 8099번 사용 현황:
```bash
lsof -i :8099
# 결과: 사용 중인 프로세스 없음
```

## 서버 시작 명령어

### FastAPI 서버 (인시던트 센터 API)
```bash
# 방법 1: uvicorn 직접 실행
uvicorn mcp.incident_api:app --host 0.0.0.0 --port 8000 --reload

# 방법 2: Makefile 사용 (구현 필요)
make incident-server-start

# 방법 3: Python 모듈로 실행
python -m uvicorn mcp.incident_api:app --port 8000
```

### 대시보드 정적 서버
```bash
# 방법 1: Python 내장 서버
python3 -m http.server 8080 --directory web/

# 방법 2: Node.js 서버 (optional)
npx http-server web/ -p 8080
```

## 누락 키 목록 (v1.0.1-pre 기준)

현재 누락되어 API 테스트가 실패하는 항목들:
1. **API 서버 미실행**: incident center API 서버 없음
2. **환경 변수 파일**: `.env` 파일 생성 필요
3. **데이터베이스**: incident 데이터 초기화 필요

## 헬스체크 스크립트 (권장)
```bash
#!/bin/bash
# scripts/incident_health_check.sh

echo "🏥 인시던트 센터 헬스체크..."

# API 서버 확인
if curl -s "http://localhost:8000/api/v1/incidents/health" > /dev/null; then
    echo "✅ API 서버 정상"
else
    echo "❌ API 서버 비정상 또는 중단"
fi

# 대시보드 파일 확인
if [ -f "web/admin_dashboard.html" ]; then
    echo "✅ 대시보드 파일 존재"
else
    echo "❌ 대시보드 파일 없음"
fi

echo "🏥 헬스체크 완료"
```