# mcp-map-company

유아플랜 MCP(멀티-앱 컨트롤 플레인) 회사용 리포지토리.  
프론트(`web/`), API(`mcp/run.py` FastAPI), 배포(Render), 협업(GitHub) 흐름을 표준화.

## 구조
- `web/index.html` : 고객용 메인
- `web/admin.html` : 관리자 전용(분리된 화면, 검색/인덱싱 차단 권장)
- `mcp/run.py` : FastAPI 서버(CORS 패치 포함)
- `scripts/` : 운영 스크립트(백업/헬스체크 등)

## 로컬 실행
uvicorn mcp.run:app --reload --port 8088

헬스체크:
curl -sS http://localhost:8088/health

## 배포(Render)
1. GitHub main → Render 연결(오토 디플로이)
2. 변경 후 Push → Render 자동 배포

## 브랜치 전략
- main : 운영 기본 라인
- stable/yyyymmdd : 복구 포인트(중요 변경 직후 생성)

## 변경/복구 안전 절차 (요약)
1) 잘못 덮어쓴 고객용 index.html → admin.html로 이동
2) 백업본에서 index.html 복원
3) Git 커밋/푸시 → Render 자동배포

## 알림 시스템 및 배포 상태 점검

### 알림 시스템 (mcp/utils/notifier.py)
심각도별 알림 시스템으로 Slack, Discord, Email 채널을 지원합니다.

**심각도별 분류:**
- 🚨 **Critical**: 시스템 중단, 최근 로그 50줄 첨부
- ❌ **Error**: 오류 발생, 최근 로그 20줄 첨부
- ⚠️ **Warning**: 경고 상황, 로그 요약 첨부
- ℹ️ **Info**: 일반 정보, 단순 메시지

**신규 강화 기능:**
- 🔄 **자동 재시도**: 전송 실패 시 최대 3회 재시도 (지수 백오프)
- 🔗 **로그 링크**: 심각도별 관련 로그 파일 링크 자동 포함
- 📊 **알림 로그**: `logs/notifier.log`에 성공/실패 내역 기록
- ⏱️ **속도 제한**: 심각도별 전송 간격 조정 (Critical: 즉시, Warning: 3초)

**사용 예시:**
```python
from mcp.utils.notifier import NotificationLevel, SlackNotifier

notifier = SlackNotifier("https://hooks.slack.com/...")
await notifier.send_notification(
    title="시스템 알림",
    message="서버 재시작이 필요합니다",
    level=NotificationLevel.WARNING,
    attach_logs=True
)
```

**로그 링크 자동 첨부:**
- Critical/Error: 보안 로그, API 로그, 시스템 로그
- Warning: API 로그, 시스템 로그
- Info: 시스템 로그

**재시도 로그 예시:**
```
2024-01-15 14:30:25 - INFO - Slack 알림 전송 시작: 시스템 알림 - warning
2024-01-15 14:30:26 - WARNING - 알림 전송 실패 (시도 1/3): Connection timeout, 1.5초 후 재시도
2024-01-15 14:30:28 - INFO - 재시도 성공: 2회 시도 후 성공
2024-01-15 14:30:28 - INFO - Slack 알림 최종 성공: 시스템 알림
```

### 관리자 대시보드 알림 패널 (web/admin_dashboard.html)
최근 20개 알림을 실시간으로 표시하며 심각도별 색상과 아이콘으로 구분됩니다.

**기본 기능:**
- 심각도별 통계 카드 (Critical/Error/Warning/Info)
- 실시간 알림 목록 (제목, 시간, 심각도)
- 테스트 알림 생성 버튼
- 자동 새로고침 (30초 간격)

**신규 고급 기능:**
- 📅 **날짜 필터**: 오늘, 7일, 30일, 전체 기간별 알림 필터링
- 🔍 **통합 검색**: 제목, 메시지, 소스, ID로 알림 검색
- 📋 **세부 정보 모달**: 알림 클릭 시 상세 정보 팝업 표시
- 📤 **내보내기 기능**: JSON/CSV 형식으로 알림 데이터 내보내기
- 💾 **개별 내보내기**: 모달에서 선택한 알림의 세부 정보 내보내기

**세부 정보 모달 내용:**
- 알림 기본 정보 (제목, 심각도, 시간, ID, 채널, 상태)
- 알림 메시지 전문
- 관련 로그 링크 (클릭 가능)
- 추가 정보 (IP 주소, 오류 코드 등)
- 첨부된 로그 내용 (Critical/Error의 경우)

**내보내기 형식:**
- **JSON**: 구조화된 데이터, API 연동에 적합
- **CSV**: 스프레드시트 분석용, 한글 지원 (UTF-8 BOM)

**사용법:**
1. 날짜 필터 버튼으로 조회 기간 선택
2. 검색창에 키워드 입력하여 알림 필터링
3. 알림 항목 클릭으로 세부 정보 확인
4. 내보내기 버튼으로 데이터 다운로드

### 배포 상태 점검 스크립트 (scripts/deploy_status.sh)
시스템 전반의 배포 상태를 종합적으로 점검합니다.

**기본 점검 항목:**
- **Git 상태**: 현재 브랜치, 마지막 커밋, 동기화 여부
- **Docker 컨테이너**: MCP 관련 서비스 실행 상태
- **포트 점유**: 8080, 8088 등 주요 포트 사용 현황
- **시스템 리소스**: CPU, 메모리, 디스크 사용률

**신규 확장 기능:**
- 🌐 **Nginx 상태**: 웹서버 프로세스, 설정 파일, 포트 80/443 상태
- 🔒 **SSL 인증서**: 도메인별 인증서 유효성, 만료일 확인
- 📜 **로그 모니터링**: 최근 배포 및 시스템 로그 tail 기능

**실행 방법:**
```bash
# 기본 실행 (요약 정보)
make deploy-status
./scripts/deploy_status.sh

# JSON 출력
./scripts/deploy_status.sh --json

# 상세 정보
./scripts/deploy_status.sh --detailed

# 실시간 모니터링 (5초 간격)
./scripts/deploy_status.sh --watch

# 새로운 확장 기능들
./scripts/deploy_status.sh --nginx        # Nginx 상태 포함
./scripts/deploy_status.sh --ssl          # SSL 인증서 검사
./scripts/deploy_status.sh --logs         # 최근 로그 표시

# 전체 점검 (모든 기능 포함)
make deploy-status-full
./scripts/deploy_status.sh --detailed --nginx --ssl --logs
```

**SSL 도메인 설정:**
```bash
# 환경변수로 확인할 도메인 지정
export SSL_DOMAINS="mcp-map.company,api.mcp-map.company,admin.mcp-map.company"
./scripts/deploy_status.sh --ssl
```

**출력 예시:**
```
=== 배포 상태 점검 ===
Git: main 브랜치 (2a74681) ✓ 동기화됨
Docker: 3개 컨테이너 실행 중
포트: 8080(FastAPI), 8088(Admin) 사용 중
Nginx: nginx/1.20.1 실행 중 (Master PID: 1234, Workers: 4)
SSL: mcp-map.company ✅ 유효 (90일 남음)
로그: 5개 파일 확인됨 (최근 업데이트: 2분 전)
시스템: CPU 15% | 메모리 2.1GB/8GB | 디스크 45GB/100GB
```

**SSL 인증서 상태:**
- ✅ 유효 (30일 이상 남음)
- ⚠️ 경고 (7-30일 남음)
- 🚨 곧 만료 (7일 미만)
- ❌ 만료됨

**로그 파일 우선순위:**
1. `logs/deploy.log` - 배포 관련 로그
2. `logs/app.log` - 애플리케이션 로그
3. `logs/api.log` - API 요청 로그
4. `/var/log/nginx/` - Nginx 로그
5. `/var/log/syslog` - 시스템 로그

## 보안 및 Rate Limiting

### Rate Limiting 미들웨어 (mcp/utils/rate_limiter.py)
IP별 요청 횟수를 제한하여 DDoS 공격과 과도한 API 호출을 방지합니다.

**주요 기능:**
- IP별 분당 요청 수 제한 (기본값: 100회/분)
- 초과 시 HTTP 429 Too Many Requests 응답
- 위반 이벤트를 `logs/security.log`에 자동 기록
- 화이트리스트 IP 관리 (로컬/원격 차단 우회)
- 차단된 IP 목록 및 통계 제공

**설정 방법:**
```python
from mcp.utils.rate_limiter import RateLimiter

# 커스텀 설정으로 Rate Limiter 생성
rate_limiter = RateLimiter(
    requests_per_minute=50,     # 분당 50회 제한
    cleanup_interval=300,       # 5분마다 오래된 기록 정리
    log_file="logs/custom_security.log"
)

# 화이트리스트에 IP 추가
rate_limiter.add_to_whitelist("192.168.1.100")
```

**FastAPI 통합:**
Rate Limiting 미들웨어가 자동으로 모든 요청에 적용됩니다:
```python
# mcp/run.py에서 자동 적용됨
app.middleware("http")(rate_limit_middleware)
```

**응답 헤더:**
- `X-RateLimit-Limit`: 분당 허용 요청 수
- `X-RateLimit-Remaining`: 남은 요청 수
- `Retry-After`: 차단 해제까지 대기 시간 (초)

### 관리자 대시보드 보안 패널 (web/admin_dashboard.html)
실시간 보안 상황을 모니터링하고 차단된 IP를 관리할 수 있습니다.

**보안 통계 카드:**
- 🚫 **차단된 IP**: 현재 Rate Limit으로 차단된 IP 수
- ⚠️ **Rate Limit 위반**: 최근 24시간 위반 횟수
- ✅ **화이트리스트**: 등록된 화이트리스트 IP 수
- 👀 **모니터링 IP**: 현재 추적 중인 IP 수

**차단 이벤트 추이 차트:**
- Chart.js 기반 실시간 차트
- 최근 24시간 동안의 차단 이벤트 추이
- 다크모드 테마 자동 적용

**차단된 IP 목록:**
- IP 주소, 위반 횟수, 마지막 위반 시간 표시
- 국가별 플래그 아이콘 표시
- 개별 IP 차단 해제 기능

**IP 화이트리스트 관리:**
- 새 IP 주소를 화이트리스트에 추가
- IP 주소 형식 유효성 검사
- 로컬스토리지 및 API 연동 지원

**사용 방법:**
1. 관리자 대시보드(`/admin_dashboard.html`) 접속
2. 🔒 보안 모니터링 패널에서 실시간 현황 확인
3. IP 화이트리스트 관리 섹션에서 신뢰할 수 있는 IP 추가
4. 🔄 새로고침 버튼으로 최신 보안 데이터 갱신

### 보안 테스트 (tests/test_security.py)
포괄적인 보안 테스트로 Rate Limiting 시스템의 안정성을 검증합니다.

**테스트 시나리오:**
1. **기본 Rate Limiting 테스트**
   - 동일 IP에서 200회 요청 시 429 응답 확인
   - 제한 초과 후 차단 IP 목록 등록 확인

2. **서로 다른 IP 독립성 테스트**
   - 서로 다른 IP는 서로 영향받지 않음 확인
   - 한 IP 차단이 다른 IP에 미치는 영향 없음 검증

3. **화이트리스트 우회 테스트**
   - 화이트리스트 IP는 무제한 요청 허용 확인
   - 화이트리스트 추가/제거 기능 검증

4. **보안 로그 기록 테스트**
   - `logs/security.log` 파일 생성 확인
   - 위반 이벤트의 상세 정보 기록 검증

**테스트 실행:**
```bash
# 모든 보안 테스트 실행
python -m pytest tests/test_security.py -v

# 특정 테스트 클래스만 실행
python -m pytest tests/test_security.py::TestRateLimiter -v

# 보안 시나리오 테스트
python -m pytest tests/test_security.py::TestSecurityScenarios -v

# 상세 출력과 함께 실행
python -m pytest tests/test_security.py -v --tb=long
```

**테스트 결과 예시:**
```
tests/test_security.py::TestRateLimiter::test_rate_limiting_logic PASSED
tests/test_security.py::TestRateLimiter::test_different_ips_not_affected PASSED
tests/test_security.py::TestRateLimiter::test_security_logs_created PASSED
tests/test_security.py::TestSecurityScenarios::test_scenario_massive_requests_from_single_ip PASSED
```

### 보안 API 엔드포인트
Rate Limiting 시스템과 상호작용할 수 있는 RESTful API를 제공합니다.

**GET /api/v1/security/stats**
현재 보안 통계 정보를 반환합니다:
```json
{
  "blocked_count": 5,
  "blocked_ips": ["192.168.100.45", "203.142.78.23"],
  "whitelist_count": 4,
  "requests_per_minute_limit": 100,
  "current_monitored_ips": 25
}
```

**POST /api/v1/security/whitelist/{ip}**
지정된 IP를 화이트리스트에 추가합니다:
```bash
curl -X POST http://localhost:8088/api/v1/security/whitelist/192.168.1.100
```

응답:
```json
{
  "success": true,
  "ip": "192.168.1.100",
  "message": "IP가 화이트리스트에 추가되었습니다."
}
```

### 보안 설정 파일
시스템 보안 설정을 파일로 관리할 수 있습니다.

**config/whitelist_ips.json** - 화이트리스트 IP 목록:
```json
{
  "ips": [
    "192.168.1.0/24",
    "10.0.0.0/8",
    "172.16.0.0/12"
  ]
}
```

**logs/security.log** - 보안 이벤트 로그:
```
2024-01-15 14:30:25 - WARNING - Rate limit exceeded - IP: 203.142.78.23, Requests: 156/100, Endpoint: GET /api/v1/portfolio, User-Agent: AttackBot/1.0
2024-01-15 14:30:26 - INFO - IP added to whitelist: 192.168.1.100
```

### 보안 모니터링 대시보드 활용

**일일 보안 점검 체크리스트:**
- [ ] 차단된 IP 수 확인 (`블록된 IP` 카드)
- [ ] Rate Limit 위반 급증 여부 확인 (차트 패턴)
- [ ] 의심스러운 IP의 위반 횟수 점검 (차단 IP 목록)
- [ ] 필요시 신뢰할 수 있는 IP를 화이트리스트에 추가

**보안 이벤트 대응 절차:**
1. 보안 패널에서 비정상적인 활동 감지
2. `logs/security.log`에서 상세 정보 확인
3. 필요시 화이트리스트 또는 차단 목록 수정
4. 시스템 로그 패널에서 전체적인 영향 평가

### 실시간 보안 알림 시스템
보안 이벤트 발생 시 자동으로 다중 채널 알림을 전송합니다.

**지원 채널:**
- 🔔 **Slack**: 웹훅을 통한 실시간 알림
- 🎮 **Discord**: 임베드 메시지로 상세 정보 제공
- 📧 **Email**: HTML/텍스트 형식의 상세 보고서

**자동 알림 이벤트:**
- **IP 차단 발생**: Rate Limit 초과 시 Critical 알림 + 보안 로그 50줄 첨부
- **Rate Limit 위반**: 임계값 접근 시 Warning 알림
- **화이트리스트 변경**: IP 추가/제거 시 Info 알림
- **일일 보안 요약**: 차단 통계 및 신규 위협 분석

**사용법:**
```python
from mcp.utils.notifier import send_ip_blocked_alert, send_security_summary_alert

# IP 차단 알림 전송
await send_ip_blocked_alert(
    client_ip="192.168.1.100",
    violation_count=156,
    endpoint="/api/v1/portfolio",
    user_agent="AttackBot/1.0"
)

# 일일 보안 요약 알림
await send_security_summary_alert(
    blocked_count=25,
    violations_24h=342,
    new_ips=["192.168.1.100", "203.0.113.50"]
)
```

**환경변수 설정:**
```bash
# Slack 알림
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

# Discord 알림
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."

# 이메일 알림
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"
export NOTIFY_EMAIL="security@company.com"
export NOTIFY_PASSWORD="app_password"
export NOTIFY_RECIPIENTS="admin1@company.com,admin2@company.com"
```

### 확장된 관리자 대시보드 보안 기능

**새로운 보안 통계 카드:**
- 🚫 **차단된 IP**: 실시간 차단된 IP 수량 표시
- ⚠️ **Rate Limit 위반**: 최근 24시간 위반 통계
- ✅ **화이트리스트**: 등록된 신뢰 IP 수량
- 👀 **모니터링 IP**: 현재 추적 중인 IP 현황

**차단 이벤트 추이 차트:**
- Chart.js 기반 실시간 시각화
- 최근 24시간 차단 패턴 분석
- 다크/라이트 모드 자동 테마 적용
- 시간대별 공격 패턴 식별 가능

**실시간 보안 알림 설정:**
- 알림 채널 개별 활성화/비활성화
- 차단 임계값 동적 조정 (1-1000 요청/분)
- 알림 전송 간격 설정 (1-60분)
- 설정값 localStorage 자동 저장

**보안 관리 기능:**
- 테스트 알림 전송 버튼
- 보안 로그 CSV 내보내기
- 최근 보안 이벤트 실시간 표시
- 보안 점수 자동 계산 및 색상 표시

**사용 예시:**
```javascript
// 테스트 알림 전송
await testSecurityAlert();

// 보안 로그 내보내기
exportSecurityLog();

// 보안 설정 저장
saveSecuritySettings();
```

### 강화된 보안 테스트

**새로운 테스트 시나리오:**

1. **알림 시스템 통합 테스트**
   - notifier 모듈 import 및 함수 호출 검증
   - 보안 알림 전송 성공/실패 처리 확인
   - 보안 로그 파일 생성 및 내용 검증

2. **분산 공격 시뮬레이션**
   - 100개 IP에서 각각 50회 요청 (총 5,000회)
   - IP별 독립적인 Rate Limiting 확인
   - 대규모 공격 시나리오 방어 능력 검증

3. **점진적 공격 패턴 테스트**
   - 정상 → 과부하 → 공격 단계별 시나리오
   - 각 단계별 적절한 대응 확인
   - 공격 패턴 변화에 따른 차단 로직 검증

4. **프록시 IP 처리 테스트**
   - X-Forwarded-For 헤더 파싱 정확성
   - 실제 클라이언트 IP 추출 검증
   - 프록시 환경에서의 Rate Limiting 동작

5. **성능 벤치마크 테스트**
   - 10,000회 요청 5초 이내 처리 검증
   - 메모리 사용량 최적화 확인
   - 대용량 트래픽 처리 능력 측정

**테스트 실행 예시:**
```bash
# 전체 보안 테스트 실행
python -m pytest tests/test_security.py -v

# 알림 시스템 테스트만 실행
python -m pytest tests/test_security.py::TestNotifierIntegration -v

# 고급 시나리오 테스트
python -m pytest tests/test_security.py::TestAdvancedSecurityScenarios -v

# 성능 테스트 포함 (시간이 오래 걸림)
python -m pytest tests/test_security.py::TestAdvancedSecurityScenarios::test_rate_limiter_performance -v -s
```

### 보안 시스템 아키텍처

**컴포넌트 구조:**
```
mcp/utils/
├── rate_limiter.py     # 핵심 Rate Limiting 엔진
├── notifier.py         # 다중 채널 알림 시스템
└── ...

web/
└── admin_dashboard.html # 실시간 보안 모니터링 UI

tests/
└── test_security.py    # 포괄적 보안 테스트 스위트

logs/
├── security.log        # 보안 이벤트 로그
└── notifications.log   # 알림 전송 로그

config/
└── whitelist_ips.json  # 화이트리스트 IP 관리
```

**데이터 흐름:**
1. 클라이언트 요청 → FastAPI 미들웨어
2. Rate Limiter → IP별 요청 수 검사
3. 위반 감지 → 보안 로그 기록 + 알림 전송
4. 관리자 대시보드 → 실시간 현황 표시
5. 화이트리스트 관리 → 예외 처리 적용

### 보안 모니터링 대시보드 고급 활용

**실시간 모니터링 워크플로우:**
1. **일일 점검 (오전 9시)**
   - 보안 점수 확인 (90점 이상 유지)
   - 전날 차단된 IP 수 분석
   - 새로운 공격 패턴 식별

2. **정기 검토 (주간)**
   - 차단 이벤트 추이 차트 분석
   - 화이트리스트 IP 유효성 검토
   - 알림 임계값 튜닝

3. **보안 사고 대응**
   - 실시간 알림 확인 → 로그 분석
   - 공격 IP 패턴 분석 → 추가 차단 조치
   - 피해 범위 평가 → 복구 계획 수립

**보안 지표 해석:**
- **보안 점수 90-100**: 안전 (녹색)
- **보안 점수 70-89**: 주의 (노란색) - 모니터링 강화 필요
- **보안 점수 50-69**: 위험 (빨간색) - 즉시 조치 필요
- **보안 점수 50 미만**: 긴급 (깜빡임) - 보안팀 즉시 대응

---
## 📘 시스템 문서 업데이트 (2025-09-20)

### 📢 알림 시스템 및 배포 상태 점검
- 전체 시스템 개요와 주요 기능 설명
- notifier.py: 재시도 로직, 로그 링크, 알림 로깅 기능
- admin_dashboard.html: 날짜 필터, 상세 모달, 내보내기 기능
- deploy_status.sh: Nginx, SSL, 로그 모니터링 확장 기능
- 보안 및 Rate Limiting: 포괄적인 보안 체계

### 📝 주요 특징
- 모든 코드와 문서에 **한국어 주석** 포함
- 실제 사용 시나리오와 출력 예시 제공
- 환경 변수 및 API 엔드포인트 상세 설명
- CI/CD와 운영 자동화 통합 가이드
