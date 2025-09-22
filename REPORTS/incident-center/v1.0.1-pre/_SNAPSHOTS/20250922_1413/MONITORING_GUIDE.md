# Incident Center v1.0.1-pre 운영 모니터링 가이드

## ❌ Weekly Monitor 실행 실패 로그

| 항목 | 값 |
|------|---|
| **실패 시각** | 2025-09-22 14:10:27 KST (Asia/Seoul) |
| **실패 잡명** | links-check (markdown-link-check 도구 오류) |
| **실행 ID** | 17905233557 |
| **실패 원인** | Node.js v18.20.8 환경에서 undici 라이브러리 호환성 문제 |
| **에러 메시지** | ReferenceError: File is not defined |
| **대응 상태** | 즉시 중단 - CI 워크플로 수정 필요 |

## 🔒 문서 잠금 (최종 고정)

| 항목 | 값 |
|------|---|
| **생성 시각** | 2025-09-22 14:45:00 KST (Asia/Seoul) |
| **갱신 시각** | 2025-09-22 14:10:30 KST (Asia/Seoul) |
| **대상 릴리스** | incident-center-v1.0.1-pre-merged |
| **커밋** | 0e332e7 (post-merge housekeeping 완료) |
| **작성자** | Claude Code + 김실장 검수 |
| **3개 파일 링크** | [LINKS_STATUS_2025-09-22.md](./WEEKLY/LINKS_STATUS_2025-09-22.md), [BADGES_STATUS_2025-09-22.md](./WEEKLY/BADGES_STATUS_2025-09-22.md), [INTEGRITY_2025-09-22.md](./WEEKLY/INTEGRITY_2025-09-22.md) |

## 📊 CI 스모크 테스트 루틴

### 자동 실행 모니터링
- **트리거**: PR 생성/업데이트 시 자동 실행
- **워크플로**: `.github/workflows/incident_smoke.yml`
- **실행 조건**: `scripts/**`, `Makefile`, `web/**`, `mcp/**`, `REPORTS/incident-center/**` 경로 변경 시

### 모니터링 포인트
1. **Dry-run 테스트**
   - 스크립트 존재 및 권한 확인
   - Makefile 타겟 구문 검증
   - 예상 결과: ✅ 100% 통과

2. **Real-run 테스트**
   - API 서버 없음으로 예상된 실패 허용
   - UI 테스트는 optional 모드로 실행
   - 예상 결과: ⚠️ API 실패, ✅ UI 통과

### 알림 설정
```yaml
# CI 실패 시 알림 예시
on_failure:
  - slack_webhook: "#incident-center-alerts"
  - email: "dev-team@company.com"
```

## 🔗 GitHub Release 링크 점검

### 정기 점검 (월 1회)
- **릴리스 URL**: https://github.com/youareplan-ceo/mcp-map-company/releases/tag/untagged-6456a5a0c1ee8f0a9d18
- **첨부 자산 확인**:
  - RAW_LOGS_dryrun5.txt (253 bytes)
  - RAW_LOGS_full5.txt (2,156 bytes)
  - COMPLETE_STATUS.md (5,832 bytes)
  - INDEX.md (2,156 bytes)
  - ENV_REQUIRED.md (3,245 bytes)

### 점검 스크립트
```bash
#!/bin/bash
# GitHub Release 자산 점검 스크립트

RELEASE_URL="https://api.github.com/repos/youareplan-ceo/mcp-map-company/releases"
TAG="incident-center-v1.0.1-pre-merged"

# 릴리스 존재 확인
curl -s "$RELEASE_URL" | jq -r ".[] | select(.tag_name==\"$TAG\") | .name"

# 자산 목록 확인
curl -s "$RELEASE_URL" | jq -r ".[] | select(.tag_name==\"$TAG\") | .assets[] | .name"
```

## 📈 로그 추적 및 분석

### 스모크 테스트 로그 위치
```
REPORTS/incident-center/v1.0.1-pre/
├── RAW_LOGS_dryrun5.txt    # 드라이런 테스트 로그
├── RAW_LOGS_full5.txt      # 풀 테스트 로그
├── COMPLETE_STATUS.md      # 종합 상태 보고서
└── PRE_MERGE_CHECK.md      # 병합 전 체크리스트
```

### 로그 분석 방법
1. **성공 패턴**
   ```bash
   grep "✅" REPORTS/incident-center/v1.0.1-pre/RAW_LOGS_dryrun5.txt
   # 예상 출력: "✅ 드라이런 v5 완료"
   ```

2. **실패 패턴**
   ```bash
   grep "❌\|HTTP 000" REPORTS/incident-center/v1.0.1-pre/RAW_LOGS_full5.txt
   # 예상 출력: API 서버 미실행 관련 에러
   ```

### 성능 추적
- **드라이런 실행 시간**: < 5초 (목표)
- **풀 테스트 실행 시간**: < 30초 (목표)
- **스크립트 크기 변화**: dashboard_smoke_incidents.sh (16,668 bytes), incident_post_release_smoke.sh (10,793 bytes)

## 🔧 환경 변수 모니터링

### CI 환경 변수 점검
- **API_BASE_URL**: `http://localhost:8000/api/v1/incidents` (더미값)
- **TIMEOUT**: `30` (초)
- **DEBUG**: `false`
- **TEST_ENV**: `ci`

### 시크릿 요구사항 점검
```bash
# 시크릿 미사용 확인 스크립트
grep -r "secrets\." .github/workflows/incident_smoke.yml
# 예상 결과: 매칭 없음 (시크릿 불필요)
```

## 📋 일일/주간 점검 체크리스트

### 일일 점검 (자동화 권장)
- [ ] CI 워크플로 실행 상태 확인
- [ ] 최근 24시간 내 스모크 테스트 실행 이력
- [ ] GitHub Actions 실행 시간 모니터링

### 주간 점검
- [ ] Release Draft 상태 확인
- [ ] 첨부 자산 무결성 검증 (SHA256)
- [ ] 문서 링크 200 응답 확인
- [ ] 환경 변수 설정 검토

### 월간 점검
- [ ] ARCHIVE_MANIFEST.md 체크섬 재검증
- [ ] 스크립트 권한 및 크기 변화 추적
- [ ] CI 성능 지표 분석
- [ ] 문서 버전 관리 상태 점검

## 🚨 알림 및 에스컬레이션

### Critical 알림 (즉시 대응)
- CI 워크플로 3회 연속 실패
- GitHub Release 자산 누락/손상
- 스크립트 실행 권한 변경

### Warning 알림 (24시간 내 대응)
- 스모크 테스트 성능 저하 (>30초)
- 문서 링크 404 에러
- 환경 변수 설정 불일치

### Info 알림 (주간 리포트)
- 정상 실행 통계
- 성능 트렌드 분석
- 사용량 리포트

## 🔄 장애 대응 절차

### 1단계: 즉시 대응
```bash
# 긴급 상태 점검
make incident-smoke-all-dry-run
git status
git log --oneline -5
```

### 2단계: 원인 분석
- 최근 커밋 이력 확인
- CI 로그 상세 분석
- 환경 변수 설정 검토

### 3단계: 복구 작업
- 필요 시 롤백 실행: `git checkout incident-center-v1.0.0`
- 스크립트 권한 재설정: `chmod +x scripts/*.sh`
- CI 워크플로 재실행

## 📞 연락처 및 지원

### 기술 지원
- **개발팀**: Slack #incident-center-dev
- **CI/CD 문의**: Slack #devops-support
- **긴급 연락**: dev-team@company.com

### 문서 및 리소스
- **리포트 인덱스**: [REPORTS/incident-center/INDEX.md](./INDEX.md)
- **환경 요구사항**: [ENV_REQUIRED.md](./ENV_REQUIRED.md)
- **완료 상태**: [v1.0.1-pre/COMPLETE_STATUS.md](./v1.0.1-pre/COMPLETE_STATUS.md)

---

**참고**: 이 가이드는 incident-center-v1.0.1-pre-merged 릴리스 기준으로 작성되었습니다. 향후 버전 업데이트 시 재검토가 필요합니다.