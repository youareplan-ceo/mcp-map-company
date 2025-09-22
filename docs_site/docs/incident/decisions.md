# DECISIONS (Sprint-1 / Issue #11)

## 배경
스켈레톤 통과 후 'proposed'로 확대. DOM/선택자 안정화를 위한 체계적 접근 필요.

## 근거
- **데이터 속성 우선**: 코드 변경에 강한 테스트 안정성 확보
- **접두어 정책 통일**: class는 `.ic-…`, id는 `ic-…`로 네임스페이스 충돌 방지
- **불안정 선택자 금지**: `div:nth-child(...)`, 동적 index, 텍스트 매칭 XPath 제거

## 영향
- 테스트/문서 링크 안정화 달성
- 제품 코드 변경은 **후속 PR**에서 수행 (현재는 문서만)
- QA 가드를 통한 무결성 보장

## DoD (Definition of Done)
- [x] 레지스트리 8항목 이상 정의
- [ ] QA 3종 통과 (links, audit, anchors)
- [ ] 문서/체크섬 반영
- [ ] 브랜치 푸시 및 PR 드래프트

---
**작성일**: 2025-09-22 KST (Asia/Seoul)
**담당**: Claude Code
**정책**: 🔒 NO-DEPLOY (문서/자동화만)