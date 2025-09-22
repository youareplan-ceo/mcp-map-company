# SELECTORS_REGISTRY (Sprint-1 / Issue #11)
> DOM/선택자 안정화 대상과 규칙을 문서로 선(先)정의합니다. 실제 코드 변경 전 문서·테스트만 생성합니다. (🔒 NO-DEPLOY)

## 규칙
- 모든 선택자는 **데이터 속성(data-testid, data-role)** 우선
- ID/클래스 사용 시 **접두어 정책**: `ic-` (incident-center)
- URL/라우팅 변경과 무관한 **구조적 앵커**만 허용
- 문서 변경 전/후 `make incident-links`, `make incident-audit` 필수

## 카탈로그(초안)
| 키 | 타입 | 셀렉터 | 설명 | 상태 |
|---|---|---|---|---|
| nav.home | data | [data-role="ic-nav-home"] | 네비 홈 버튼 | draft |
| panel.summary | data | [data-testid="ic-summary"] | 요약 패널 | draft |
| table.incidents | class | .ic-table-incidents | 인시던트 테이블 | draft |

> 상태: draft → proposed → locked (PR 병합 시 locked)
