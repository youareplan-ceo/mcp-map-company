# GitHub 프로젝트 보드 및 Kanban 규칙

## 📋 프로젝트 보드 구조

### 메인 프로젝트: "Incident Center v1.0.2"
**상태**: ⚠️ 수동 생성 필요 (GitHub CLI 스코프 권한 부족)
**수동 생성 URL**: https://github.com/youareplan-ceo
**설명**: v1.0.2 릴리스 전체 개발 진행 상황 추적

### 보드 컬럼 구성 (생성 시 적용)
| 컬럼 | 설명 | 이동 조건 |
|------|------|-----------|
| **📋 Backlog** | 계획된 작업 목록 | 이슈 생성 시 자동 배치 |
| **🎯 Ready** | 작업 준비 완료 | assignee 할당 + ready 라벨 |
| **🚀 In Progress** | 현재 진행 중인 작업 | in-progress 라벨 추가 |
| **👀 In Review** | 코드 리뷰 진행 중 | PR 생성 + ready-to-merge 라벨 |
| **✅ Done** | 완료된 작업 | PR 병합 완료 |

### 연결 대상 이슈 (생성 후 추가)
- Issue #11: CI/CD 파이프라인 완전 자동화 (Sprint-1)
- Issue #12: 실시간 모니터링 대시보드 구축 (Sprint-1)
- Issue #13: 운영 문서화 체계 정비 (Sprint-1)
- Issue #14: 반응형 웹 디자인 구현 (Sprint-2)
- Issue #15: 성능 최적화 및 코드 개선 (Sprint-2)
- Issue #16: 접근성 WCAG 2.1 AA 준수 (Sprint-2)

## 🏷️ Kanban 규칙 및 워크플로

### 1. Backlog → Ready
**담당**: Product Owner / Scrum Master
**조건**:
- [ ] 이슈 제목이 명확하게 정의됨
- [ ] 완료 조건(DoD)이 구체적으로 작성됨
- [ ] 우선순위(P0~P3) 라벨 할당
- [ ] 복잡도(Low/Medium/High) 예측 완료
- [ ] 관련 컴포넌트 라벨 적용

### 2. Ready → In Progress
**담당**: Developer
**조건**:
- [ ] 개발자 할당 완료
- [ ] 스프린트 계획에 포함됨
- [ ] 선행 작업 의존성 해결
- [ ] 개발 환경 설정 완료

### 3. In Progress → In Review
**담당**: Developer
**조건**:
- [ ] 기능 개발 완료
- [ ] 자체 테스트 통과
- [ ] PR 생성 및 연결
- [ ] CI 빌드 성공

### 4. In Review → Done
**담당**: Reviewer / QA Team
**조건**:
- [ ] 코드 리뷰 승인 (최소 1명)
- [ ] 모든 리뷰 코멘트 해결
- [ ] CI/CD 파이프라인 통과
- [ ] PR 병합 완료

---

**갱신 시각**: 2025-09-22 16:30:00 KST (Asia/Seoul)
**상태**: 📋 문서화 완료, 웹 UI 수동 생성 대기
