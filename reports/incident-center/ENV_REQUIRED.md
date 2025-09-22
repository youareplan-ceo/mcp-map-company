# Incident Center 환경 변수 요구사항

| 항목 | 값 |
|------|------|
| **실행 커밋** | `hotfix/incident-center-v1.0.1-pre` |
| **실행 브랜치** | hotfix/incident-center-v1.0.1-pre |
| **실행 시각** | 2024-09-22 12:57:00 (Asia/Seoul) |
| **경로** | /Users/youareplan/Desktop/mcp-map-company |

## 🔑 필수 환경 변수 목록

### CI/CD 파이프라인 환경 변수

| 변수명 | 용도 | 필수 여부 | 기본값/더미값 |
|--------|------|-----------|---------------|
| `PYTHON_VERSION` | Python 버전 지정 | 선택 | `3.9` |
| `NODE_VERSION` | Node.js 버전 지정 | 선택 | `18` |
| `CI` | CI 환경 플래그 | 자동 | `true` |
| `GITHUB_TOKEN` | GitHub API 액세스 | 자동 | GitHub Actions 제공 |

### 스모크 테스트 환경 변수

| 변수명 | 용도 | 필수 여부 | 기본값/더미값 |
|--------|------|-----------|---------------|
| `API_BASE_URL` | API 서버 베이스 URL | 선택 | `http://localhost:8088` |
| `WEB_BASE_URL` | 웹 서버 베이스 URL | 선택 | `http://localhost:8000` |
| `SMOKE_TIMEOUT` | 스모크 테스트 타임아웃 | 선택 | `30` |
| `LOG_LEVEL` | 로그 레벨 | 선택 | `INFO` |

### 보안 관련 환경 변수 (CI에서 미요구)

| 변수명 | 용도 | CI에서 요구 | 비고 |
|--------|------|-------------|------|
| `RENDER_API_KEY` | Render 배포 키 | ❌ | 로컬 검증만 수행 |
| `VERCEL_TOKEN` | Vercel 배포 토큰 | ❌ | 로컬 검증만 수행 |
| `DATABASE_URL` | 데이터베이스 연결 | ❌ | 더미 DB 사용 |
| `SECRET_KEY` | 암호화 키 | ❌ | 더미 키 사용 |

## 🛠️ GitHub Actions 워크플로 설정

### 환경 변수 설정 예시

```yaml
env:
  # 기본 환경 설정
  PYTHON_VERSION: "3.9"
  NODE_VERSION: "18"

  # 스모크 테스트 설정
  API_BASE_URL: "http://localhost:8088"
  WEB_BASE_URL: "http://localhost:8000"
  SMOKE_TIMEOUT: "30"
  LOG_LEVEL: "INFO"

  # 더미 값 (실제 배포 없음)
  DATABASE_URL: "sqlite:///dummy.db"
  SECRET_KEY: "dummy-secret-for-testing"
```

### 시크릿 미요구 사유

- **배포 없음**: 로컬 검증만 수행하므로 실제 배포 키 불필요
- **더미 환경**: 테스트용 더미 값으로 충분
- **보안 고려**: 민감한 정보를 CI 환경에 노출하지 않음

## 📋 환경 설정 체크리스트

### CI 환경에서 확인 필요

- ✅ Python 3.9+ 설치 확인
- ✅ 필요한 패키지 설치 (requirements.txt)
- ✅ 스모크 테스트 스크립트 실행 권한
- ✅ 더미 환경 변수 설정
- ❌ 실제 서비스 배포 (금지됨)

### 로컬 환경에서 확인 필요

- ✅ MCP API 서버 실행 (포트 8088)
- ✅ 웹 대시보드 접근 가능
- ✅ 스모크 테스트 스크립트 존재
- ✅ Makefile 타깃 정의