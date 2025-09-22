# Incident Center 운영 모니터링 가이드

## 📋 문서 정보

| 항목 | 값 |
|------|---|
| **생성 시각** | 2025-09-22 13:51:50 KST (Asia/Seoul) |
| **대상 버전** | v1.0.1-pre (태그: incident-center-v1.0.1-pre-merged) |
| **기준 커밋** | 01f0255a8d11d66c7e5489e9e05146cd5706e841 |
| **작성자** | Claude Code + 김실장 검수 |

## 🔍 일일 모니터링 루틴

### 1. CI 스모크 워크플로 확인

#### 📊 통과율 모니터링
```bash
# 최근 5개 워크플로 실행 결과 확인
gh run list --workflow="Incident Center Smoke Tests" --limit=5 --json conclusion,status,url

# 성공률 계산 (주간 기준)
gh run list --workflow="Incident Center Smoke Tests" --limit=20 --json conclusion | \
  jq '[.[] | select(.conclusion == "success")] | length' | \
  awk '{print "Success Rate: " ($1/20)*100 "%"}'
```

#### ⚠️ 경고 기준
| 지표 | 정상 | 주의 | 경고 |
|------|------|------|------|
| **Dry-run 성공률** | 95% 이상 | 90-95% | 90% 미만 |
| **Real-run 예상 실패** | HTTP 000 | 기타 에러 | Timeout/권한 에러 |
| **아티팩트 업로드** | 100% | 90% 이상 | 90% 미만 |

### 2. GitHub 링크 상태 검증

#### 🔗 핵심 링크 200 응답 체크
```bash
# PR #3 상태 확인
curl -s -o /dev/null -w "%{http_code}" https://github.com/youareplan-ceo/mcp-map-company/pull/3

# Release 상태 확인
curl -s -o /dev/null -w "%{http_code}" https://github.com/youareplan-ceo/mcp-map-company/releases/tag/incident-center-v1.0.1-pre-merged

# Actions 워크플로 확인
curl -s -o /dev/null -w "%{http_code}" https://github.com/youareplan-ceo/mcp-map-company/actions/workflows/incident_smoke.yml
```

#### 📋 체크리스트 (일일)
- [ ] PR #3 접근 가능 (200 응답)
- [ ] 릴리스 페이지 정상 (200 응답)
- [ ] CI 워크플로 페이지 정상 (200 응답)
- [ ] README 배지 정상 표시
- [ ] 릴리스 자산 다운로드 가능

## 📈 주간 모니터링 루틴

### 1. 에러 로그 추적

#### 🔍 시스템 로그 분석
```bash
# 보안 로그 확인 (에러 패턴)
tail -n 100 logs/security.log | grep -i "error\|failed\|exception"

# 실행 로그 확인
tail -n 100 logs/run.log | grep -i "incident"

# 웹서버 로그 확인
tail -n 100 scripts/web_server.log | grep -E "(5xx|error|incident)"
```

#### 📊 로그 분석 기준
| 로그 유형 | 정상 | 주의 필요 |
|----------|------|-----------|
| **보안 로그** | 인증 성공 위주 | 실패 증가, 비정상 접근 |
| **실행 로그** | 정상 시작/종료 | timeout, permission denied |
| **웹서버 로그** | 2xx, 3xx 응답 | 4xx 증가, 5xx 발생 |

### 2. 리포트 무결성 검증

#### 🔐 체크섬 검증 (주간)
```bash
cd REPORTS/incident-center/v1.0.1-pre/

# 핵심 파일 체크섬 재검증
echo "f1f6b3889364e5d7e8d6a150b4af9c20d3329949b746b64196f02b620dc06ea1  COMPLETE_STATUS.md" | sha256sum -c
echo "c266075e35f0eae9a601747868031f1ed673e9597d51889e20bd2af7e1c2e243  SUMMARY.md" | sha256sum -c
echo "7f2b4a8704227348a9805fab630d7096f91ec67daf1d16bdef22eb02119d8efc  ENV_REQUIRED.md" | sha256sum -c
```

#### 📋 무결성 체크리스트
- [ ] ARCHIVE_MANIFEST.md 체크섬 일치
- [ ] 핵심 3개 파일 SHA256 일치
- [ ] GitHub 릴리스 자산 크기 일치 (11.5 KB)
- [ ] 문서 잠금 상태 유지

## 🚨 장애 대응 프로세스

### 1. 긴급 상황 분류

#### 🟥 긴급 (1시간 이내 대응)
- CI 워크플로 완전 실패 (3회 연속)
- GitHub 링크 전체 접근 불가
- 보안 로그 침입 시도 감지
- 릴리스 자산 손실

#### 🟨 주의 (4시간 이내 대응)
- CI 성공률 90% 미만
- 특정 링크 간헐적 실패
- 로그 파일 비정상 증가
- 체크섬 불일치 발견

#### 🟢 모니터링 (24시간 이내 확인)
- CI 성공률 95% 미만
- 로그 경고 메시지 증가
- 문서 접근 지연

### 2. 연락 루틴

#### 즉시 연락 (긴급 상황)
| 담당자 | 연락처 | 대응 범위 |
|--------|--------|-----------|
| **김실장** | [내부 연락처] | 전체 시스템 관리 |
| **개발팀 슬랙** | #incident-center-urgent | 기술적 이슈 |
| **GitHub 관리자** | [관리자 연락처] | 권한/설정 문제 |

#### 보고 템플릿
```markdown
# 🚨 Incident Center 모니터링 알림

## 상황 정보
- **발생 시각**: [UTC+9 시각]
- **문제 유형**: [긴급/주의/모니터링]
- **영향 범위**: [CI/링크/로그/문서]

## 현재 상태
- **CI 워크플로**: [정상/실패/부분실패]
- **GitHub 링크**: [정상/접근불가/느림]
- **문서 무결성**: [정상/체크섬불일치/손실]

## 시도한 조치
1. [첫 번째 조치]
2. [두 번째 조치]

## 요청 지원
- [ ] 긴급 기술 지원 필요
- [ ] GitHub 관리자 개입 필요
- [ ] 시스템 점검 필요
```

### 3. 롤백 트리거 조건

#### 🔄 자동 롤백 고려 상황
- CI 워크플로 5회 연속 실패
- 핵심 GitHub 링크 24시간 접근 불가
- 보안 로그 공격 패턴 확인
- 체크섬 변조 확인

#### 📋 롤백 실행 전 확인
- [ ] 책임자 승인 확보
- [ ] 롤백 가이드 (ROLLBACK.md) 숙지
- [ ] 백업 상태 확인
- [ ] 영향 범위 분석 완료

## 📊 성능 지표 (KPI)

### 월간 리포트 메트릭

#### 🎯 목표 지표
| 지표 | 목표 | 측정 방법 |
|------|------|-----------|
| **CI 성공률** | 95% 이상 | GitHub Actions 통계 |
| **링크 가용성** | 99% 이상 | HTTP 상태 코드 체크 |
| **체크섬 일치율** | 100% | 주간 검증 결과 |
| **평균 응답시간** | 5초 이하 | 링크 접근 시간 측정 |

#### 📈 트렌드 분석
```bash
# 월간 CI 성공률 트렌드
gh run list --workflow="Incident Center Smoke Tests" --limit=100 --json conclusion,createdAt | \
  jq -r '.[] | [.createdAt[0:10], .conclusion] | @csv' | \
  sort | uniq -c

# 주간 에러 로그 트렌드
for week in {1..4}; do
  echo "Week $week:"
  grep -c "error\|failed" logs/security.log | tail -7 | head -7
done
```

## 🛠️ 자동화 권장사항

### 1. 모니터링 자동화 스크립트

#### 📝 일일 체크 스크립트 (crontab)
```bash
#!/bin/bash
# /scripts/daily_incident_check.sh

LOG_FILE="logs/monitoring_$(date +%Y%m%d).log"

echo "$(date): Starting daily incident center check" >> $LOG_FILE

# CI 상태 확인
CI_STATUS=$(gh run list --workflow="Incident Center Smoke Tests" --limit=1 --json conclusion | jq -r '.[0].conclusion')
echo "$(date): CI Status: $CI_STATUS" >> $LOG_FILE

# 링크 상태 확인
PR_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://github.com/youareplan-ceo/mcp-map-company/pull/3)
RELEASE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://github.com/youareplan-ceo/mcp-map-company/releases/tag/incident-center-v1.0.1-pre-merged)

echo "$(date): PR Status: $PR_STATUS, Release Status: $RELEASE_STATUS" >> $LOG_FILE

# 경고 조건 체크
if [ "$CI_STATUS" != "success" ] || [ "$PR_STATUS" != "200" ] || [ "$RELEASE_STATUS" != "200" ]; then
    echo "$(date): WARNING: Incident center monitoring alert" >> $LOG_FILE
    # 슬랙 알림 등 추가 액션
fi
```

### 2. 알림 설정

#### 📱 슬랙 웹훅 연동
```bash
# 슬랙 알림 함수
send_slack_alert() {
    local message="$1"
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"🚨 Incident Center Alert: '"$message"'"}' \
        [SLACK_WEBHOOK_URL]
}
```

---

**📋 이 가이드 사용법**: 일일/주간 체크리스트를 따라 정기 모니터링을 수행하고, 경고 상황 발생 시 연락 루틴에 따라 대응하세요.