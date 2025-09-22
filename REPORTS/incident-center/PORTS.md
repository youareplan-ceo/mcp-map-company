# 포트/프로세스 안전 점검 리포트

| 항목 | 값 |
|------|------|
| **실행 커밋** | `hotfix/incident-center-v1.0.1-pre` |
| **실행 브랜치** | hotfix/incident-center-v1.0.1-pre |
| **실행 시각** | 2024-09-22 12:56:00 (Asia/Seoul) |
| **경로** | /Users/youareplan/Desktop/mcp-map-company |

## 🔌 현재 바인딩된 포트 현황

### 활성 프로세스 목록

| PID | 포트 | 프로세스명 | 명령어 | 상태 |
|-----|------|------------|--------|------|
| 36762 | 8099 | Python | `mcp/run.py` | 실행 중 |
| 51262 | 3000 | Python | `python -m http.server 3000` | 실행 중 |

### 상세 정보

#### PID 36762 (포트 8099)
- **명령어**: `/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/Resources/Python.app/Contents/MacOS/Python mcp/run.py`
- **포트**: 8099 (TCP, LISTEN)
- **CPU 사용률**: 0.1%
- **메모리**: 9024 KB
- **실행 시간**: 1:52.26 (4:52AM 시작)
- **용도**: MCP API 서버

#### PID 51262 (포트 3000)
- **명령어**: `/opt/homebrew/Cellar/python@3.13/3.13.7/Frameworks/Python.framework/Versions/3.13/Resources/Python.app/Contents/MacOS/Python -m http.server 3000`
- **포트**: 3000 (TCP, LISTEN)
- **CPU 사용률**: 0.0%
- **메모리**: 2368 KB
- **실행 시간**: 0:18.71 (토요일 03AM 시작)
- **용도**: HTTP 개발 서버

## ⚠️ 안전 점검 결과

- ✅ **충돌 검사**: 8099, 8088, 8000, 3000 포트 중 일부만 사용 중
- ✅ **프로세스 안전**: 모든 프로세스 정상 실행 중, 종료하지 않음
- ✅ **메모리 사용**: 정상 범위 내 메모리 사용량
- ✅ **시스템 부하**: 낮은 CPU 사용률로 안전한 상태

## 📋 권장사항

1. **포트 8088**: 현재 사용되지 않음 - incident center API 서버 실행 가능
2. **포트 8000**: 현재 사용되지 않음 - 웹 대시보드 서버 실행 가능
3. **기존 프로세스**: 모두 정상 동작 중이므로 종료 금지
4. **충돌 방지**: 새로운 서비스 실행 시 8088, 8000 포트 사용 권장

## 🔒 보안 고려사항

- 모든 프로세스가 localhost에서만 바인딩됨
- 외부 접근 차단된 안전한 개발 환경
- 프로세스 권한: 현재 사용자 계정으로 제한됨