# GitHub 프로젝트 보드 및 Kanban 규칙

## 📋 프로젝트 보드 구조

### 메인 프로젝트: "v1.0.2 Development"
**URL**: https://github.com/youareplan-ceo/mcp-map-company/projects/1
**설명**: v1.0.2 릴리스 전체 개발 진행 상황 추적

### 보드 컬럼 구성 (v1.0.2 Sprint-1 적용)
| 컬럼 | 설명 | 이동 조건 |
|------|------|-----------|
| **📋 Backlog** | 계획된 작업 목록 | 이슈 생성 시 자동 배치 |
| **🎯 Ready** | 작업 준비 완료 | assignee 할당 + ready 라벨 |
| **🚀 In Progress** | 현재 진행 중인 작업 | in-progress 라벨 추가 |
| **👀 In Review** | 코드 리뷰 진행 중 | PR 생성 + ready-to-merge 라벨 |
| **✅ Done** | 완료된 작업 | PR 병합 완료 |

### 자동화 규칙 (문서화)
| 규칙 | 트리거 | 액션 | 조건 |
|------|--------|------|------|
| **Rule 1** | assignee 할당 + "ready" 라벨 | Backlog → Ready | 이슈 상태 "open" |
| **Rule 2** | "ready-to-merge" 라벨 추가 | In Progress → In Review | PR이 draft 아님 |
| **Rule 3** | PR 병합 완료 | In Review → Done | PR 상태 "merged" |

## 🏷️ Kanban 규칙 및 워크플로

### 1. Backlog → Sprint Ready
**담당**: Product Owner / Scrum Master
**조건**:
- [ ] 이슈 제목이 명확하게 정의됨
- [ ] 완료 조건(DoD)이 구체적으로 작성됨
- [ ] 우선순위(P0~P3) 라벨 할당
- [ ] 복잡도(Low/Medium/High) 예측 완료
- [ ] 관련 컴포넌트 라벨 적용

**자동화 규칙**:
```yaml
# GitHub Actions로 구현 예정
when:
  - issue labeled with "ready-for-sprint"
then:
  - move to "Sprint Ready" column
  - assign to milestone
```

### 2. Sprint Ready → In Progress
**담당**: Developer
**조건**:
- [ ] 개발자 할당 완료
- [ ] 스프린트 계획에 포함됨
- [ ] 선행 작업 의존성 해결
- [ ] 개발 환경 설정 완료

**자동화 규칙**:
```yaml
when:
  - issue assigned to developer
  - issue status changed to "in-progress"
then:
  - move to "In Progress" column
  - update sprint tracking
```

### 3. In Progress → In Review
**담당**: Developer
**조건**:
- [ ] 기능 개발 완료
- [ ] 자체 테스트 통과
- [ ] PR 생성 및 연결
- [ ] CI 빌드 성공

**자동화 규칙**:
```yaml
when:
  - pull_request opened
  - pull_request linked to issue
then:
  - move issue to "In Review" column
  - request review from team
```

### 4. In Review → Testing
**담당**: Reviewer
**조건**:
- [ ] 코드 리뷰 승인 (최소 1명)
- [ ] 모든 리뷰 코멘트 해결
- [ ] CI/CD 파이프라인 통과
- [ ] 코드 품질 기준 충족

**자동화 규칙**:
```yaml
when:
  - pull_request approved
  - all CI checks passed
then:
  - move to "Testing" column
  - trigger deployment to staging
```

### 5. Testing → Done
**담당**: QA Team / Tester
**조건**:
- [ ] 스모크 테스트 통과
- [ ] 기능 테스트 완료
- [ ] 회귀 테스트 통과
- [ ] PR 병합 완료

**자동화 규칙**:
```yaml
when:
  - pull_request merged
  - all tests passed
then:
  - move to "Done" column
  - close linked issue
  - update sprint metrics
```

## 📊 WIP (Work In Progress) 제한

### 컬럼별 WIP 한계
| 컬럼 | WIP 제한 | 이유 |
|------|----------|------|
| **Sprint Ready** | 10개 | 스프린트 범위 관리 |
| **In Progress** | 6개 | 개발자 집중도 유지 |
| **In Review** | 4개 | 리뷰 품질 보장 |
| **Testing** | 3개 | 테스트 리소스 한계 |

### WIP 초과 시 액션
1. **경고 알림**: Slack 채널에 자동 알림
2. **신규 이슈 차단**: 새로운 이슈를 해당 컬럼으로 이동 제한
3. **에스컬레이션**: Scrum Master에게 알림 전송

## 🏃‍♂️ 스프린트 관리

### Sprint-1 (2025-09-23 ~ 2025-09-30)
**목표**: 인프라 기반 구축
**할당 이슈**: #1, #2, #3
**Sprint Capacity**: 21 포인트 (3명 × 7일)

### Sprint-2 (2025-10-01 ~ 2025-10-15)
**목표**: 사용자 경험 개선
**할당 이슈**: #4, #5, #6
**Sprint Capacity**: 42 포인트 (3명 × 14일)

### 스프린트 시작 체크리스트
- [ ] 백로그 정리 및 우선순위 재조정
- [ ] 팀 capacity 확인
- [ ] 의존성 분석 완료
- [ ] Sprint Goal 설정

### 스프린트 종료 체크리스트
- [ ] Sprint Review 실시
- [ ] Sprint Retrospective 진행
- [ ] 미완료 이슈 처리 (연기/재할당)
- [ ] 다음 스프린트 계획 수립

## 📈 메트릭 및 KPI

### 추적 지표
| 지표 | 목표값 | 측정 주기 |
|------|--------|-----------|
| **Sprint Velocity** | 20-25 포인트/주 | 스프린트 종료 시 |
| **Lead Time** | < 5일 | 주간 |
| **Cycle Time** | < 3일 | 주간 |
| **Throughput** | 3-4개 이슈/주 | 주간 |
| **Bug Rate** | < 10% | 월간 |

### 대시보드 위치
- **GitHub Insights**: 기본 메트릭
- **프로젝트 보드**: 실시간 진행 상황
- **Weekly Report**: `REPORTS/incident-center/WEEKLY/`

## 🔄 자동화 설정

### GitHub Actions 워크플로
```yaml
# .github/workflows/project-automation.yml
name: Project Board Automation

on:
  issues:
    types: [opened, labeled, assigned]
  pull_request:
    types: [opened, ready_for_review, closed]

jobs:
  move-cards:
    runs-on: ubuntu-latest
    steps:
      - name: Move issue to appropriate column
        uses: alex-page/github-project-automation-plus@v0.8.1
        with:
          project: v1.0.2 Development
          column: In Progress
          repo-token: ${{ secrets.GITHUB_TOKEN }}
```

### 알림 설정
- **Slack 통합**: 주요 상태 변경 시 팀 채널 알림
- **이메일 알림**: 마일스톤 지연 시 이해관계자 알림
- **일일 스탠드업**: 자동 진행 상황 요약 생성

## 📋 이슈 생명주기 예시

### 이슈 #1: "CI/CD 파이프라인 자동화"
```
📋 Backlog (생성)
   ↓ (요구사항 정의 완료)
🎯 Sprint Ready (Sprint-1 할당)
   ↓ (개발자 김개발 할당)
🚀 In Progress (개발 시작)
   ↓ (PR #15 생성)
👀 In Review (코드 리뷰 진행)
   ↓ (리뷰 승인)
🧪 Testing (QA 테스트)
   ↓ (테스트 통과, PR 병합)
✅ Done (완료)
```

### 소요 시간: 총 7일
- Backlog → Sprint Ready: 1일
- Sprint Ready → In Progress: 0일
- In Progress → In Review: 4일
- In Review → Testing: 1일
- Testing → Done: 1일

## 🚨 에스컬레이션 프로세스

### 지연 경고 단계
1. **Yellow (3일 지연)**: 담당자에게 Slack DM
2. **Orange (5일 지연)**: 팀장에게 에스컬레이션
3. **Red (7일 지연)**: Scrum Master 개입 및 재계획

### 블로커 처리
1. **즉시 알림**: 블로커 라벨 적용 시 팀 채널 알림
2. **일일 추적**: 스탠드업에서 블로커 상황 보고
3. **해결 지원**: 필요 시 추가 리소스 할당

---

**생성일**: 2025-09-22 KST
**담당**: Claude Code
**승인**: 김실장 (검수 예정)
**상태**: 📋 규칙 정의 완료
**연결**: REPORTS/incident-center/INDEX.md