# Incident Center 환경 변수 요구사항

## API 스모크 테스트 필요 변수

### 필수 환경 변수
- `API_BASE_URL`: 인시던트 센터 API 베이스 URL
  - 기본값: `http://localhost:8000/api/v1/incidents`
  - 예시: `https://your-app.onrender.com/api/v1/incidents`

### 선택적 환경 변수
- `TIMEOUT`: API 요청 타임아웃 (초)
  - 기본값: 10초
- `DEBUG`: 상세 로그 출력
  - 기본값: false

## .env 파일 예시
```bash
# Incident Center API Configuration
API_BASE_URL=http://localhost:8000/api/v1/incidents
TIMEOUT=30
DEBUG=true
```

## Render.com 배포 시 필요 변수
```bash
# Production Environment
API_BASE_URL=https://your-app.onrender.com/api/v1/incidents
TIMEOUT=30
```

## 로컬 개발 서버 시작
```bash
# Python FastAPI 서버 실행
cd /path/to/incident-center
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# 또는 Makefile 사용
make incident-server-start
```