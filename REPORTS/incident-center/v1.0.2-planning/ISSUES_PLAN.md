# v1.0.2 이슈 설계 문서

## 📋 개요

**목적**: v1.0.2 Sprint별 이슈 6건의 상세 설계 및 연결 관계 문서화
**범위**: Sprint 1-3에 걸친 이슈 계획 및 산출물 경로 정의
**정책**: 🚫 **NO-DEPLOY** (문서 및 자동화만)

## 🎯 이슈 목록 및 연결 관계

### Sprint 1 이슈 (3건)

#### #11 DOM/선택자 안정화
| 항목 | 내용 |
|------|------|
| **제목** | DOM/선택자 안정화 |
| **설명** | CSS 선택자 표준화 및 DOM 구조 최적화 |
| **우선순위** | P1 (High) |
| **라벨** | `sprint-1`, `type/enhancement`, `priority/high` |
| **예상 기간** | 5일 |
| **참조 문서** | [SPRINTS/SPRINT_1.md](./SPRINTS/SPRINT_1.md#dom-stabilization) |
| **예상 산출물 경로** | `web/assets/css/selectors.css`, `docs/DOM_GUIDE.md` |

**상세 범위**:
- CSS 선택자 표준화 (BEM 방법론 적용)
- DOM 구조 최적화 및 일관성 확보
- 선택자 가이드 문서 작성

#### #12 CI 매트릭스 확장
| 항목 | 내용 |
|------|------|
| **제목** | CI 매트릭스 확장 (Python 3.11-3.13, macOS+Ubuntu) |
| **설명** | GitHub Actions CI 매트릭스 확장 및 플랫폼 지원 강화 |
| **우선순위** | P0 (Critical) |
| **라벨** | `sprint-1`, `type/automation`, `priority/critical` |
| **예상 기간** | 3일 |
| **참조 문서** | [SPRINTS/SPRINT_1.md](./SPRINTS/SPRINT_1.md#ci-matrix) |
| **예상 산출물 경로** | `.github/workflows/test.yml`, `.github/workflows/build.yml` |

**상세 범위**:
- Python 3.11, 3.12, 3.13 지원 추가
- macOS 및 Ubuntu 플랫폼 테스트 확장
- 매트릭스 최적화 및 성능 개선

#### #14 Link Audit 엄격 모드
| 항목 | 내용 |
|------|------|
| **제목** | Link Audit 엄격 모드 구현 |
| **설명** | 404 링크 완전 제거 및 실시간 검증 시스템 |
| **우선순위** | P1 (High) |
| **라벨** | `sprint-1`, `type/automation`, `priority/high` |
| **예상 기간** | 4일 |
| **참조 문서** | [PLAN.md](./PLAN.md#link-audit) |
| **예상 산출물 경로** | `scripts/link_audit_strict.sh`, `Makefile` |

**상세 범위**:
- 엄격 모드 스크립트 개발
- 실시간 링크 검증 시스템
- CI/CD 파이프라인 통합

---

### Sprint 2 이슈 (1건)

#### #15 문서 자동 점검
| 항목 | 내용 |
|------|------|
| **제목** | 문서 자동 점검 시스템 구축 |
| **설명** | 문서 품질 자동 검증 및 일관성 유지 시스템 |
| **우선순위** | P2 (Medium) |
| **라벨** | `sprint-2`, `type/automation`, `priority/medium` |
| **예상 기간** | 3일 |
| **참조 문서** | [TODO.md](./TODO.md#docs-check) |
| **예상 산출물 경로** | `scripts/docs_check.sh`, `.github/workflows/docs_quality.yml` |

**상세 범위**:
- 마크다운 문법 검증
- 링크 무결성 자동 점검
- 문서 메타데이터 검증

---

### Sprint 3 이슈 (2건)

#### #13 대시보드 카피/툴팁
| 항목 | 내용 |
|------|------|
| **제목** | 대시보드 카피 및 툴팁 고도화 |
| **설명** | 사용자 친화적 텍스트 및 도움말 시스템 개선 |
| **우선순위** | P2 (Medium) |
| **라벨** | `sprint-3`, `type/documentation`, `priority/medium` |
| **예상 기간** | 2일 |
| **참조 문서** | [SPRINTS/SPRINT_3.md](./SPRINTS/SPRINT_3.md#ux-copy) |
| **예상 산출물 경로** | `web/assets/js/tooltips.js`, `docs/COPY_GUIDE.md` |

**상세 범위**:
- 대시보드 텍스트 개선
- 툴팁 시스템 구축
- 사용자 가이드 작성

#### #16 아카이브 스냅샷 자동화
| 항목 | 내용 |
|------|------|
| **제목** | 아카이브 스냅샷 자동화 시스템 |
| **설명** | 버전별 스냅샷 자동 생성 및 관리 시스템 |
| **우선순위** | P1 (High) |
| **라벨** | `sprint-3`, `type/automation`, `priority/high` |
| **예상 기간** | 3일 |
| **참조 문서** | [RELEASES_DRAFT.md](./RELEASES_DRAFT.md#post-hook) |
| **예상 산출물 경로** | `scripts/auto_snapshot.sh`, `.github/workflows/snapshot.yml` |

**상세 범위**:
- 자동 스냅샷 생성 스크립트
- 체크섬 계산 및 검증
- 릴리스 후 훅 시스템

## 📊 이슈 의존성 매트릭스

| 이슈 | 의존성 | 차단 요소 | 선행 조건 |
|------|--------|----------|-----------|
| **#11 DOM/선택자** | 없음 | 없음 | 기존 CSS 분석 완료 |
| **#12 CI 매트릭스** | 없음 | 없음 | Python 환경 준비 |
| **#14 Link Audit** | #11 (선택적) | 없음 | 기존 감사 시스템 분석 |
| **#15 문서 점검** | #14 | 없음 | Link Audit 완료 |
| **#13 대시보드** | #11 | 없음 | DOM 구조 안정화 |
| **#16 스냅샷** | #15 | 없음 | 문서 점검 시스템 완료 |

## 🔗 연결된 참조 문서

### 계획 문서
- [MILESTONES.md](./MILESTONES.md) - Sprint 구조 및 일정
- [PLAN.md](./PLAN.md) - 전체 실행 계획
- [TODO.md](./TODO.md) - 상세 작업 체크리스트
- [RELEASES_DRAFT.md](./RELEASES_DRAFT.md) - 릴리스 계획

### Sprint 노트
- [SPRINTS/SPRINT_1.md](./SPRINTS/SPRINT_1.md) - Foundation & Automation
- [SPRINTS/SPRINT_2.md](./SPRINTS/SPRINT_2.md) - Monitoring & Integrity
- [SPRINTS/SPRINT_3.md](./SPRINTS/SPRINT_3.md) - UI/UX & Final Validation

### 운영 문서
- [../PROJECTS.md](../PROJECTS.md) - 프로젝트 보드 규칙
- [../LINK_AUDIT.md](../LINK_AUDIT.md) - 링크 감사 현황

## 📈 진행률 추적

### Sprint별 진행률
| Sprint | 총 이슈 | 완료 | 진행 중 | 대기 중 | 진행률 |
|--------|---------|------|---------|---------|--------|
| **Sprint 1** | 3 | 0 | 0 | 3 | 0% |
| **Sprint 2** | 1 | 0 | 0 | 1 | 0% |
| **Sprint 3** | 2 | 0 | 0 | 2 | 0% |
| **전체** | 6 | 0 | 0 | 6 | 0% |

### 예상 완료 일정
- **#11, #12, #14**: 2025-10-15 (Sprint 1 종료)
- **#15**: 2025-10-25 (Sprint 2 종료)
- **#13, #16**: 2025-10-31 (Sprint 3 종료)

---

**작성일**: 2025-09-22 15:42:00 KST (Asia/Seoul)
**최종 업데이트**: 2025-09-22 15:42:00 KST
**담당**: Claude Code
**상태**: 📋 이슈 설계 완료