# 충돌 파일 분석 및 해결 전략

**분석 시각**: 2025-09-22 12:57:00
**브랜치**: hotfix/incident-center-v1.0.1-pre
**충돌 파일**: 2개

## 충돌 상황 요약

### 1. 충돌 유형
- **현재 브랜치**: 추적되지 않는 파일로 존재 (워크트리에서 복원)
- **main 브랜치**: 동일 파일이 이미 추적됨 (정식 커밋)
- **Git 에러**: "추적하지 않는 다음 작업 폴더의 파일을 덮어씁니다"

### 2. 충돌 파일 상세 분석

#### 📄 scripts/dashboard_smoke_incidents.sh
- **main 브랜치 상태**: 완전히 삭제된 상태 (deleted file mode 100755)
- **현재 브랜치**: 워크트리에서 복원된 전체 스크립트 (426줄)
- **충돌 성격**: 현재 브랜치에만 존재, main에서는 삭제됨

**핵심 기능 분석**:
- 인시던트 센터 전용 대시보드 UI 스모크 테스트
- 5개 통계 카드 DOM 검증: `totalIncidents`, `highSeverityIncidents`, `avgResolutionTime`, `slaViolationRate`, `activeIncidents`
- 2개 차트 DOM 검증: `incidentTrendChart`, `incidentSeverityChart`
- 한국어 로컬라이제이션 검증 (6개 키워드)
- 다크모드/반응형 디자인 지원 확인
- JSON 출력 옵션 지원

#### 📄 scripts/incident_post_release_smoke.sh
- **main 브랜치 상태**: 완전히 삭제된 상태 (deleted file mode 100755)
- **현재 브랜치**: 워크트리에서 복원된 전체 스크립트 (324줄)
- **충돌 성격**: 현재 브랜치에만 존재, main에서는 삭제됨

**핵심 기능 분석**:
- 인시던트 센터 v1.0.0 API 스모크 테스트
- 3개 엔드포인트 검증: `/health`, `/summary`, `/list?export_format=csv`
- RBAC 헤더 지원: `X-User-Role: VIEWER`
- 한국어 CSV 헤더 검증: `인시던트ID`, `생성일시`, `해결시간`
- 타임아웃 설정 가능 (기본 30초)
- JSON 출력 옵션 지원

## 🚨 핵심 발견사항

### 중요한 정보 손실 없음
- main 브랜치에서 두 스크립트가 **완전히 삭제**된 상태
- 현재 브랜치의 파일들이 **유일한 버전**
- 실제 "충돌"이 아닌 **파일 존재/부재 차이**

### 기능적 가치 분석
1. **dashboard_smoke_incidents.sh**: 인시던트 센터 전용 UI 검증 - **핵심 기능**
2. **incident_post_release_smoke.sh**: 인시던트 센터 API 검증 - **핵심 기능**
3. **Makefile 타겟 의존성**: 두 스크립트 모두 현재 Makefile에서 참조됨

## 🎯 권장 병합 전략

### 선택된 전략: **옵션 A - 현재 버전 유지**
**이유**: main에서 삭제된 파일을 복원하는 것이므로 충돌이 아닌 **복원 작업**

### 구체적 실행 계획
1. **충돌 파일 백업**: 현재 워크트리 버전을 안전하게 보관
2. **충돌 해결**: 추적되지 않는 파일을 Git에 추가
3. **실행권한 설정**: `chmod +x` 적용
4. **스모크 테스트 실행**: 복원된 스크립트로 전체 검증
5. **커밋 및 푸시**: 정상 동작 확인 후 main 병합

### 대안 전략 (비권장)
- **옵션 B**: 파일 삭제 후 main 병합 → **기능 손실**
- **옵션 C**: 수동 병합 → **불필요 (충돌 아님)**

## 📋 실행 체크리스트

### ✅ 즉시 실행
1. 현재 스크립트를 Git 추가: `git add scripts/dashboard_smoke_incidents.sh scripts/incident_post_release_smoke.sh`
2. 실행권한 확인: `chmod +x scripts/*.sh`
3. Makefile 타겟 검증: `make incident-smoke-all:dry-run`

### ✅ 검증 단계
1. 스모크 테스트 실행: `make incident-smoke-all`
2. JSON 출력 테스트: 각 스크립트 `--json` 옵션 확인
3. 한국어 메시지 검증: 에러 케이스 출력 확인

### ✅ 마무리
1. 모든 변경사항 커밋
2. main 브랜치와 병합
3. 기능 정상 동작 최종 확인

## 🔍 위험도 평가

### 낮은 위험도 ✅
- **기능 손실 없음**: main에서 삭제된 핵심 기능 복원
- **호환성 보장**: 기존 Makefile과 완전 호환
- **테스트 가능**: 로컬에서 충분히 검증 가능

### 주의사항
- 서버 의존성: API 테스트는 로컬 서버 실행 필요
- 환경 설정: `API_BASE_URL` 환경 변수 활용 가능