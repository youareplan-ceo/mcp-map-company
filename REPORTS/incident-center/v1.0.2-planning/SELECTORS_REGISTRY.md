# SELECTORS_REGISTRY (Sprint-1 / Issue #11)
> DOM/선택자 안정화 대상과 규칙을 문서로 선(先)정의합니다. 실제 코드 변경 전 문서·테스트만 생성합니다. (🔒 NO-DEPLOY)

**상태**: proposed (문서 기준, 코드 변경 없음)

## 규칙
- 모든 선택자는 **데이터 속성(data-testid, data-role)** 우선
- ID/클래스 사용 시 **접두어 정책**: class는 `.ic-…`, id는 `ic-…` 로만 허용
- URL/라우팅 변경과 무관한 **구조적 앵커**만 허용
- 금지 목록: `div:nth-child(...)`, 동적 index 기반, 텍스트 매칭 XPath
- 문서 변경 전/후 `make incident-links`, `make incident-audit` 필수

## 카탈로그(확장)
| 키 | 타입 | 셀렉터 | 설명 | 상태 |
|---|---|---|---|---|
| nav.home | data | [data-role="ic-nav-home"] | 네비 홈 버튼 | proposed |
| panel.summary | data | [data-testid="ic-summary"] | 요약 패널 | proposed |
| table.incidents | class | .ic-table-incidents | 인시던트 테이블 | proposed |
| row.incident | data | [data-testid="ic-incident-row"] | 인시던트 행 | proposed |
| btn.refresh | data | [data-role="ic-btn-refresh"] | 새로고침 버튼 | proposed |
| filter.status | data | [data-testid="ic-filter-status"] | 상태 필터 | proposed |
| chip.open | class | .ic-chip-open | 오픈 상태 칩 | proposed |
| modal.detail | data | [data-role="ic-modal-detail"] | 상세 모달 | proposed |

> 상태: draft → proposed → locked (PR 병합 시 locked)

**변경 전/후 must-run**: make incident-links / make incident-audit / make qa-all
