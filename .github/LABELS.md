# GitHub Labels 표준화 명세

## 📋 레이블 세트 정의

| 레이블 | 색상 코드 | 설명 | 용례 |
|--------|-----------|------|------|
| **incident-center** | `#FF6B6B` | 인시던트 센터 관련 작업 | 스모크 테스트, 모니터링 시스템, 장애 대응 |
| **ci** | `#4ECDC4` | CI/CD 파이프라인 관련 | GitHub Actions, 워크플로, 자동화 스크립트 |
| **docs** | `#45B7D1` | 문서 작업 | README, 가이드, API 문서, 릴리스 노트 |
| **governance** | `#96CEB4` | 프로젝트 관리 및 거버넌스 | 정책, 프로세스, 품질 관리, 컴플라이언스 |
| **smoke** | `#FECA57` | 스모크 테스트 관련 | 기본 동작 검증, 헬스체크, 드라이런 테스트 |
| **no-deploy** | `#FF9FF3` | 배포 불필요 작업 | 문서만 변경, 로컬 스크립트, 계획 수립 |
| **task** | `#54A0FF` | 일반 작업 | 기능 구현, 개선, 리팩토링 |
| **bug** | `#FF6348` | 버그 수정 | 오류 해결, 핫픽스, 패치 |
| **enhancement** | `#2ED573` | 기능 개선 | 성능 향상, UX 개선, 기능 확장 |
| **planning** | `#A55EEA` | 계획 및 설계 | 마일스톤, 로드맵, 아키텍처 설계 |
| **ready-to-merge** | `#26DE81` | 병합 준비 완료 | 리뷰 완료, 테스트 통과, 승인됨 |

## 🏷️ 레이블 적용 규칙

### 필수 레이블
- 모든 이슈/PR은 **최소 1개** 레이블 필요
- **incident-center** 관련 작업은 해당 레이블 필수

### 조합 규칙
- `incident-center` + `smoke`: 스모크 테스트 관련
- `ci` + `no-deploy`: CI 설정만 변경
- `docs` + `governance`: 정책 문서
- `bug` + `ready-to-merge`: 핫픽스 준비 완료

### 우선순위
1. **incident-center** - 인시던트 센터 최우선
2. **bug** - 버그 수정 고우선순위
3. **ci** - CI/CD 안정성 중요
4. **enhancement** - 기능 개선
5. **docs** - 문서화
6. **planning** - 계획 수립

## 📊 사용 가이드라인

### 이슈 생성 시
```
Title: [레이블명] 간단한 설명
Labels: 해당하는 레이블들
```

### PR 생성 시
```
Title: feat/fix/docs/ci: 변경 내용
Labels: 작업 유형 + ready-to-merge (승인 후)
```

### 마일스톤 연동
- **Sprint-1**: `planning` + `task`
- **Sprint-2**: `enhancement` + `ci`
- **v1.0.2**: `incident-center` + `governance`

---

## 📊 GitHub 생성 현황

**생성 일시**: 2025-09-22 15:40:00 KST
**생성 완료**: ✅ 11개 라벨 등록
**gh 명령어**: `gh label create/edit` 사용

### 생성된 라벨 목록 (확인됨)
- ✅ incident-center (FF6B6B) - 기존 라벨 확인
- ✅ ci (4ECDC4) - 새로 생성
- ✅ docs (45B7D1) - 새로 생성
- ✅ governance (96CEB4) - 새로 생성
- ✅ task (54A0FF) - 새로 생성
- ✅ planning (A55EEA) - 새로 생성
- ✅ bug (FF6348) - 기존 라벨 업데이트
- ✅ enhancement (2ED573) - 기존 라벨 업데이트
- ✅ smoke (FECA57) - 기존 라벨 업데이트
- ✅ no-deploy (FF9FF3) - 기존 라벨 업데이트
- ✅ ready-to-merge (26DE81) - 기존 라벨 확인

---

**생성일**: 2025-09-22 KST
**담당**: Claude Code
**상태**: ✅ GitHub 등록 완료
**연결**: REPORTS/incident-center/INDEX.md