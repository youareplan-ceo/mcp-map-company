# Pull Request

## 📋 요약 (5줄)
<!-- PR의 핵심 변경사항을 5줄 이내로 요약해주세요 -->
-
-
-
-
-

## ✅ 체크리스트

- [ ] **CI 스모크 테스트**: dry-run과 full 테스트 모두 통과
- [ ] **시크릿 요구 없음**: ENV_REQUIRED.md 확인하여 새로운 환경변수 없음
- [ ] **리포트/링크 정상**: 모든 문서 링크가 404 없이 정상 동작
- [ ] **배포 없음**: no-deploy 라벨 유지 (실배포 금지)

## 📊 리포트 및 릴리스노트

| 항목 | 링크 |
|------|------|
| **리포트 인덱스** | [REPORTS/incident-center/INDEX.md](../REPORTS/incident-center/INDEX.md) |
| **릴리스노트** | [RELEASES/incident-center/](../RELEASES/incident-center/) |
| **환경 요구사항** | [REPORTS/incident-center/ENV_REQUIRED.md](../REPORTS/incident-center/ENV_REQUIRED.md) |

## 🏷️ 라벨 안내

이 PR은 다음 라벨이 적용되어야 합니다:
- `incident-center`: 인시던트 센터 관련 변경
- `smoke`: 스모크 테스트 관련
- `ready-to-merge`: 병합 준비 완료
- `no-deploy`: 실배포 금지

## ⚠️ no-deploy 고지

**이 PR은 실배포를 포함하지 않습니다.** 모든 변경사항은 로컬/CI 환경에서만 테스트되며, Render/Vercel 등 실제 서비스로의 배포는 수행하지 않습니다.

## 📝 추가 정보

<!-- 필요시 추가 설명을 작성해주세요 -->