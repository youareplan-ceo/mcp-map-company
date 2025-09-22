# GitHub 프로젝트 보드 생성 상태

## 🚨 권한 이슈 발생

**시도 일시**: 2025-09-22 15:55:00 KST
**명령어**: `gh project create --title "Incident Center v1.0.2" --owner youareplan-ceo`
**에러**: 인증 토큰에 필수 scope 부족

### 에러 메시지
```
error: your authentication token is missing required scopes [project read:project]
To request it, run:  gh auth refresh -s project,read:project
```

## 📋 대안 방안

### 수동 생성 가이드
GitHub 웹 UI에서 다음 절차로 프로젝트 보드 수동 생성:

1. **GitHub 프로젝트 생성**
   - https://github.com/youareplan-ceo/mcp-map-company/projects
   - "New project" 클릭
   - 제목: "Incident Center v1.0.2"
   - 템플릿: "Board" 선택

2. **컬럼 구성**
   ```
   📋 Backlog        - 계획된 작업 목록
   🎯 Ready          - 작업 준비 완료
   🚀 In Progress    - 현재 진행 중인 작업
   👀 In Review      - 코드 리뷰 진행 중
   ✅ Done           - 완료된 작업
   ```

3. **이슈 연결**
   - Issue #11-13: Sprint-1 (Backlog 컬럼에 추가)
   - Issue #14-16: Sprint-2 (Backlog 컬럼에 추가)

### 자동화 규칙 (수동 설정)
```yaml
Rule 1:
  Trigger: assignee 할당 + "ready" 라벨
  Action: Backlog → Ready

Rule 2:
  Trigger: "ready-to-merge" 라벨 추가
  Action: In Progress → In Review

Rule 3:
  Trigger: PR 병합 완료
  Action: In Review → Done
```

## 🔄 PROJECTS.md 업데이트 필요

생성 완료 후 다음 정보 추가:
- 프로젝트 URL
- 프로젝트 번호
- 컬럼 구성 확인
- 자동화 규칙 적용 여부

---

**생성일**: 2025-09-22 KST
**담당**: Claude Code
**상태**: ⚠️ 권한 이슈로 수동 생성 필요
**참조**: SUPPORT.md에 권한 이슈 기록됨