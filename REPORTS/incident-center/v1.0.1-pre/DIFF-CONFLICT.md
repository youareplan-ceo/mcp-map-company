# 병합 충돌 기록

**발생 시각**: 2025-09-22 12:55:30
**브랜치**: hotfix/incident-center-v1.0.1-pre → main
**충돌 유형**: 추적되지 않는 파일 덮어쓰기

## 충돌 세부사항

### 충돌 파일
1. `scripts/dashboard_smoke_incidents.sh`
   - **상태**: 현재 브랜치에 추적되지 않는 파일로 존재
   - **main 브랜치**: 동일한 파일이 추적됨
   - **원인**: 워크트리에서 복원된 파일이 main에 이미 존재

2. `scripts/incident_post_release_smoke.sh`
   - **상태**: 현재 브랜치에 추적되지 않는 파일로 존재
   - **main 브랜치**: 동일한 파일이 추적됨
   - **원인**: 워크트리에서 복원된 파일이 main에 이미 존재

## Git 에러 메시지
```
error: 병합 때문에 추적하지 않는 다음 작업 폴더의 파일을 덮어씁니다:
	scripts/dashboard_smoke_incidents.sh
	scripts/incident_post_release_smoke.sh
병합하기 전에 이 파일을 옮기거나 제거하십시오.
중지함
전략 ort(으)로 병합이 실패했습니다.
```

## 분석 및 해결방안

### 원인 분석
- v1.0.1-pre 브랜치에서 `.worktrees/`에서 스크립트를 복원했으나 추적하지 않음
- main 브랜치에는 동일한 스크립트가 이미 커밋되어 추적됨
- Git이 추적되지 않는 파일 덮어쓰기를 방지

### 권장 해결방안
1. **충돌 파일 백업**: 현재 버전을 다른 위치에 백업
2. **충돌 파일 제거**: `rm scripts/dashboard_smoke_incidents.sh scripts/incident_post_release_smoke.sh`
3. **병합 재시도**: `git merge main --no-edit`
4. **차이점 비교**: 백업본과 병합된 파일 비교 후 필요시 수정

## 수동 수정 미수행
- 작업 지시에 따라 충돌 발생 시 리포트만 생성
- 실제 병합 중단하고 현재 상태 유지
- 다음 단계 진행 보류

## 권장 액션
1. 개발팀과 충돌 해결 방안 협의
2. 스크립트 버전 차이 분석
3. 안전한 병합 전략 수립