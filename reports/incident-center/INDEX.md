# Incident Center 리포트 인덱스

## 🔒 문서 잠금 (최종 고정)

| 항목 | 값 |
|------|---|
| **잠금 시각** | 2025-09-22 15:10:00 KST (Asia/Seoul) |
| **브랜치** | feature/reports-casing-guard |
| **최신 커밋** | 2112f36 feat(incident-center): complete REPORTS path normalization and metadata lock |
| **태그** | incident-center-v1.0.1-pre-merged |
| **릴리스** | https://github.com/youareplan-ceo/mcp-map-company/releases/tag/incident-center-v1.0.1-pre-merged |
| **경로** | /Users/youareplan/Desktop/mcp-map-company/REPORTS/incident-center/ |
| **작성자** | Claude Code + 김실장 검수 |
| **상태** | 🔒 LOCKED - 케이스 가드 구현 완료 |

## v1.0.1-pre 핵심 산출물

| 문서명 | 설명 | 경로 |
|--------|------|------|
| **SUMMARY.md** | 스모크 테스트 종합 요약 | [v1.0.1-pre/SUMMARY.md](./v1.0.1-pre/SUMMARY.md) |
| **COMPARE.md** | 버전 간 비교 분석 | [v1.0.1-pre/COMPARE.md](./v1.0.1-pre/COMPARE.md) |
| **RAW_LOGS_dryrun.txt** | 드라이런 테스트 로그 | [v1.0.1-pre/RAW_LOGS_dryrun.txt](./v1.0.1-pre/RAW_LOGS_dryrun.txt) |
| **RAW_LOGS_full.txt** | 전체 테스트 로그 | [v1.0.1-pre/RAW_LOGS_full.txt](./v1.0.1-pre/RAW_LOGS_full.txt) |
| **COMPLETE_STATUS.md** | 종합 완료 보고서 | [v1.0.1-pre/COMPLETE_STATUS.md](./v1.0.1-pre/COMPLETE_STATUS.md) |

## 릴리스 노트

| 버전 | 릴리스 노트 경로 |
|------|------------------|
| **v1.0.1-pre** | [RELEASES/incident-center/v1.0.1-pre.md](../../RELEASES/incident-center/v1.0.1-pre.md) |

## 운영 체계 문서

| 문서명 | 설명 | 경로 |
|--------|------|------|
| **README_VERIFICATION_LOG.md** | README 배지/링크 검증 로그 | [README_VERIFICATION_LOG.md](./README_VERIFICATION_LOG.md) |
| **DIFF_CASE_FIX.md** | 소문자 reports/ 경로 정리 보고서 | [DIFF_CASE_FIX.md](./DIFF_CASE_FIX.md) |
| **NEXT_MILESTONE.md** | v1.0.2-planning 마일스톤 계획 | [NEXT_MILESTONE.md](./NEXT_MILESTONE.md) |
| **POST_FIX_SUMMARY.md** | 경로 정규화 사후 정리 요약 | [POST_FIX_SUMMARY.md](./POST_FIX_SUMMARY.md) |

## 🛡️ 케이스 가드 시스템

| 구성 요소 | 설명 | 경로 |
|----------|------|------|
| **pre-commit 훅** | 로컬 커밋 시 reports/ 차단 | `.git/hooks/pre-commit` |
| **CI 가드 워크플로** | PR에서 자동 케이스 검증 | `.github/workflows/reports_casing_guard.yml` |
| **검증 스크립트** | 범용 케이스 검사 도구 | `scripts/check_reports_casing.sh` |
| **마이그레이션 가이드** | 케이스 변경 가이드 | [../../MIGRATIONS/2025-09-22-reports-to-REPORTS.md](../../MIGRATIONS/2025-09-22-reports-to-REPORTS.md) |

## v1.0.2-planning 통합 점검 로그

| 로그 파일 | 설명 | 실행 시각 |
|----------|------|-----------|
| **RAW_incident_links_guard.txt** | 로컬 링크 상태 점검 | [v1.0.2-planning/RAW_incident_links_guard.txt](./v1.0.2-planning/RAW_incident_links_guard.txt) |
| **RAW_incident_audit_guard.txt** | 로컬 무결성 감사 | [v1.0.2-planning/RAW_incident_audit_guard.txt](./v1.0.2-planning/RAW_incident_audit_guard.txt) |

**점검 결과**: ✅ 모든 로컬 점검 통과 (2025-09-22 15:10:00 KST)

## 바로가기

- 📊 [종합 상태 대시보드](./v1.0.1-pre/SUMMARY.md#테스트-결과-비교)
- 🔧 [Makefile 타겟 가이드](../../README.md#빠른-사용법)
- ⚙️ [환경 설정 요구사항](./ENV_REQUIRED.md)
- 🚀 [PR #3 - 병합 준비](https://github.com/youareplan-ceo/mcp-map-company/pull/3)
- 🔗 [v1.0.1-pre 릴리스](https://github.com/youareplan-ceo/mcp-map-company/releases/tag/incident-center-v1.0.1-pre-merged)