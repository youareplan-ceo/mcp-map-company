# CI 통합 가이드: weekly_monitor 워크플로

## 📋 개요

`weekly_monitor.yml` 워크플로는 매주 자동으로 실행되어 시스템 상태와 문서 무결성을 검증하는 CI 통합 시스템입니다.

### 주요 기능
- **링크 상태 검사**: README.md 및 REPORTS 디렉토리 링크 유효성 검증
- **배지 상태 모니터링**: GitHub Actions 및 워크플로 배지 HTTP 응답 확인
- **무결성 검사**: ARCHIVE_MANIFEST.md 기반 파일 체크섬 검증
- **자동 보고서 생성**: 주간 모니터링 결과를 WEEKLY 디렉토리에 저장

## 🔄 실행 스케줄

### 자동 실행
- **주기**: 매주 월요일 00:00 UTC (한국 시간 09:00)
- **cron 설정**: `"0 0 * * 1"`
- **타겟 브랜치**: main

### 수동 실행
```yaml
workflow_dispatch: # GitHub Actions UI에서 수동 트리거 가능
```

**수동 실행 방법**:
1. GitHub → Actions → "Weekly Monitoring" 워크플로 선택
2. "Run workflow" 버튼 클릭
3. 브랜치 선택 후 실행

## 🏗️ 워크플로 구조

### Job 1: links-check
**목적**: 링크 유효성 검사
**러너**: ubuntu-latest
**주요 단계**:
1. 리포지토리 체크아웃
2. Node.js 18 설정
3. markdown-link-check 설치
4. README.md 링크 검사
5. REPORTS 디렉토리 GitHub 링크 검사 (curl 기반)
6. 링크 상태 보고서 생성

**산출물**:
- `REPORTS/incident-center/WEEKLY/LINKS_STATUS_YYYY-MM-DD.md`
- GitHub Actions 아티팩트: `links-status-report`

### Job 2: badges-check
**목적**: GitHub 배지 상태 모니터링
**러너**: ubuntu-latest
**주요 단계**:
1. GitHub Actions 페이지 HTTP 상태 확인
2. incident_smoke.yml 워크플로 배지 상태 확인
3. 배지 상태 보고서 생성

**산출물**:
- `REPORTS/incident-center/WEEKLY/BADGES_STATUS_YYYY-MM-DD.md`
- GitHub Actions 아티팩트: `badges-status-report`

### Job 3: integrity-check
**목적**: 리포트 무결성 검증
**러너**: ubuntu-latest
**주요 단계**:
1. ARCHIVE_MANIFEST.md 존재 여부 확인
2. v1.0.1-pre 디렉토리 파일 SHA256 체크섬 재계산
3. 무결성 검사 보고서 생성

**산출물**:
- `REPORTS/incident-center/WEEKLY/INTEGRITY_YYYY-MM-DD.md`
- GitHub Actions 아티팩트: `integrity-check-report`

### Job 4: summary
**목적**: 주간 모니터링 종합 요약
**러너**: ubuntu-latest
**의존성**: `needs: [links-check, badges-check, integrity-check]`
**주요 단계**:
1. 모든 보고서 아티팩트 다운로드
2. 종합 요약 보고서 생성
3. 변경사항 자동 커밋 (선택적)

**산출물**:
- `REPORTS/incident-center/WEEKLY/SUMMARY_YYYY-MM-DD.md`

## 📊 모니터링 지표

### 링크 검사 지표
```yaml
검사 대상:
  - README.md의 모든 마크다운 링크
  - GitHub Actions 페이지 (HTTP 상태)
  - Workflow 배지 SVG (HTTP 상태)
  - 릴리스 페이지 (HTTP 상태)

성공 기준:
  - HTTP 200: 정상
  - HTTP 404: 링크 오류
  - HTTP 000: 네트워크 오류
```

### 배지 상태 지표
```yaml
배지 유형:
  - GitHub Actions 전체 상태
  - incident_smoke.yml 워크플로 배지

HTTP 응답 코드:
  - 200: 정상
  - 404: 배지 없음
  - 500: 서버 오류
```

### 무결성 검사 지표
```yaml
검사 파일:
  - ARCHIVE_MANIFEST.md (필수)
  - v1.0.1-pre/*.md (전체)
  - v1.0.1-pre/*.txt (전체)

체크섬 알고리즘: SHA256
변조 감지: 이전 체크섬과 비교
```

## 🚨 알림 및 에러 처리

### 실패 처리
```yaml
continue-on-error: true  # 커밋 실패 시에도 워크플로 계속
```

### 에러 시나리오
1. **링크 오류**: 404 링크 발견 시 보고서에 기록
2. **배지 오류**: 배지 로딩 실패 시 HTTP 상태 기록
3. **무결성 오류**: 파일 누락 또는 체크섬 불일치 시 경고
4. **커밋 실패**: 권한 오류 등으로 자동 커밋 실패 시 무시

### 알림 채널
- **GitHub Actions 알림**: 워크플로 실패 시 자동 이메일
- **보고서 기반 모니터링**: WEEKLY 디렉토리 파일 검토
- **수동 확인**: 필요 시 Actions 탭에서 로그 확인

## 🔧 v1.0.2 연계 계획

### Sprint-1 통합 (2025-09-30)
- **CI/CD 파이프라인 자동화**와 연계
- weekly_monitor 워크플로를 핵심 모니터링 시스템으로 확장
- 실시간 대시보드와 연동

### Sprint-2 통합 (2025-10-15)
- **성능 모니터링** 지표 추가
- **접근성 검사** 자동화 통합
- 모바일 호환성 검증 추가

### 확장 계획
```yaml
추가 Job 계획:
  performance-check:
    - Lighthouse 성능 점수 측정
    - 페이지 로딩 속도 검증
    - 응답 시간 모니터링

  accessibility-check:
    - aXe 자동 접근성 검사
    - WCAG 2.1 AA 준수 확인
    - 색상 대비 검증

  security-scan:
    - 의존성 취약점 스캔
    - 코드 보안 검사
    - 시크릿 누출 감지
```

## 📁 보고서 저장 구조

```
REPORTS/incident-center/WEEKLY/
├── LINKS_STATUS_2025-09-22.md      # 링크 검사 결과
├── BADGES_STATUS_2025-09-22.md     # 배지 상태 결과
├── INTEGRITY_2025-09-22.md         # 무결성 검사 결과
├── SUMMARY_2025-09-22.md           # 종합 요약
├── LINKS_STATUS_2025-09-29.md      # 다음 주 보고서
└── ...
```

### 보고서 보존 정책
- **보존 기간**: 12주 (3개월)
- **아카이브**: 분기별로 압축 아카이브 생성
- **정리 규칙**: 12주 초과 파일 자동 삭제 (예정)

## 🔐 보안 고려사항

### GitHub Secrets
```yaml
사용 중인 시크릿:
  - GITHUB_TOKEN: 기본 제공 (자동 설정)

필요 권한:
  - contents: read (리포지토리 읽기)
  - actions: write (아티팩트 업로드)
  - pull-requests: write (커밋 권한)
```

### 민감 정보 처리
- **API 키 없음**: 외부 서비스 호출 없이 GitHub API만 사용
- **개인정보 없음**: 공개 리포지토리 메타데이터만 수집
- **로그 필터링**: 민감한 URL이나 토큰 노출 방지

## 📈 성능 최적화

### 워크플로 실행 시간
- **예상 시간**: 5-10분
- **병렬 실행**: 3개 Job 동시 실행 (links, badges, integrity)
- **리소스 사용**: ubuntu-latest (GitHub 호스팅)

### 최적화 기법
```yaml
캐싱 전략:
  - Node.js 의존성 캐싱 (setup-node@v4 기본 제공)
  - 아티팩트 압축으로 저장 공간 절약

효율성 개선:
  - curl을 통한 경량 HTTP 검사
  - 필요한 파일만 체크섬 계산
  - 조건부 커밋 (변경사항 있을 때만)
```

## 🛠️ 트러블슈팅

### 일반적인 문제

#### 1. 링크 검사 실패
```bash
# 원인: 외부 링크 일시 장애
# 해결: 보고서에서 HTTP 상태 코드 확인 후 수동 재검증
```

#### 2. 배지 로딩 실패
```bash
# 원인: GitHub 서비스 일시 장애
# 해결: GitHub Status 페이지 확인 후 재실행
```

#### 3. 무결성 검사 실패
```bash
# 원인: 파일 누락 또는 변조
# 해결: ARCHIVE_MANIFEST.md와 실제 파일 비교 검증
```

#### 4. 자동 커밋 실패
```bash
# 원인: 브랜치 보호 규칙 또는 권한 문제
# 해결: 수동으로 보고서 파일 커밋
```

### 디버깅 방법
1. **Actions 로그 확인**: GitHub → Actions → 실패한 워크플로 선택
2. **아티팩트 다운로드**: 생성된 보고서 파일 직접 확인
3. **수동 실행**: workflow_dispatch로 즉시 재실행
4. **로컬 테스트**: 동일한 명령어로 로컬에서 디버깅

---

**생성일**: 2025-09-22 KST
**담당**: Claude Code
**상태**: 📋 CI 통합 가이드 완료
**연결**: `.github/workflows/weekly_monitor.yml`