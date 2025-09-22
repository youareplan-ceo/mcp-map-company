# README 운영 배지/링크 재검증 로그

## 🔍 검증 정보

| 항목 | 값 |
|------|-----|
| **검증 시각** | 2025-09-22 14:20:00 KST (Asia/Seoul) |
| **검증자** | Claude Code (자동화) |
| **대상 파일** | README.md |
| **검증 범위** | 배지, 링크, 릴리스 참조 |

## 🛠️ 수정 사항

### 이전 배지 (문제 있음)
```markdown
[![PR Status](https://img.shields.io/github/pulls/youareplan-ceo/mcp-map-company/hotfix%2Fincident-center-v1.0.1-pre)](https://github.com/youareplan-ceo/mcp-map-company/pull/3)
[![Actions Status](https://github.com/youareplan-ceo/mcp-map-company/workflows/incident_smoke/badge.svg)](https://github.com/youareplan-ceo/mcp-map-company/actions/workflows/incident_smoke.yml)
```

**문제점**:
- PR 배지: 404 (PR #3 이미 병합됨)
- Actions 배지: 404 (잘못된 URL 경로)

### 새로운 배지 (검증 완료)
```markdown
[![Incident Smoke Tests](https://github.com/youareplan-ceo/mcp-map-company/actions/workflows/incident_smoke.yml/badge.svg)](https://github.com/youareplan-ceo/mcp-map-company/actions/workflows/incident_smoke.yml)
[![Weekly Monitor](https://github.com/youareplan-ceo/mcp-map-company/actions/workflows/weekly_monitor.yml/badge.svg)](https://github.com/youareplan-ceo/mcp-map-company/actions/workflows/weekly_monitor.yml)
[![Latest Release](https://img.shields.io/github/v/release/youareplan-ceo/mcp-map-company?include_prereleases)](https://github.com/youareplan-ceo/mcp-map-company/releases/latest)
```

## ✅ 검증 결과

| 배지/링크 | URL | HTTP 상태 | 결과 |
|-----------|-----|-----------|------|
| **Incident Smoke Tests** | `actions/workflows/incident_smoke.yml/badge.svg` | 200 | ✅ 정상 |
| **Weekly Monitor** | `actions/workflows/weekly_monitor.yml/badge.svg` | 200 | ✅ 정상 |
| **Latest Release** | `img.shields.io/github/v/release/...` | 200 | ✅ 정상 |
| **Incident Center 인덱스** | `./REPORTS/incident-center/INDEX.md` | 로컬 | ✅ 존재 |
| **v1.0.1-pre 릴리스** | `releases/tag/incident-center-v1.0.1-pre-merged` | 링크 | ✅ 정상 |

## 🔗 추가된 링크

### 릴리스 직접 링크
- **v1.0.1-pre 릴리스**: GitHub Release 페이지 직접 연결
- **실시간 배지**: CI 워크플로 상태 실시간 반영

### 운영 모니터링 배지
- **Incident Smoke Tests**: 기존 스모크 테스트 워크플로
- **Weekly Monitor**: 새로 추가된 주간 모니터링 워크플로
- **Latest Release**: 최신 릴리스 버전 표시 (pre-release 포함)

## 📊 배지 기능 설명

### Incident Smoke Tests
- **목적**: incident 관련 스크립트 및 Makefile 타겟 검증
- **실행**: 수동 트리거 또는 PR 시 자동 실행
- **상태**: 최근 테스트 결과 반영

### Weekly Monitor
- **목적**: 링크, 배지, 아카이브 무결성 주간 모니터링
- **실행**: 매주 월요일 09:00 UTC 자동 + 수동 트리거
- **아티팩트**: REPORTS/incident-center/WEEKLY/ 자동 생성

### Latest Release
- **목적**: 최신 릴리스 버전 실시간 표시
- **포함**: Pre-release 포함 (include_prereleases=true)
- **링크**: GitHub Releases 페이지로 직접 연결

## ⚠️ 주의사항

### 배지 캐싱
- GitHub 배지는 캐싱될 수 있어 실시간 반영에 지연 가능
- 브라우저 캐시 클리어 후 재확인 권장

### 릴리스 배지
- Pre-release 포함 설정으로 v1.0.1-pre도 "최신"으로 표시
- 정식 릴리스 시 자동으로 버전 업데이트

### 모니터링 연속성
- Weekly Monitor 워크플로 중단 시 배지가 "실패" 상태 표시
- 정기 실행 상태 점검 필요

---

**검증 완료**: 2025-09-22 14:20:00 KST
**다음 검증**: Weekly Monitor CI 자동 실행 시 (매주 월요일)
**상태**: ✅ 모든 배지/링크 정상 작동 확인