# reports/ → REPORTS/ 경로 마이그레이션 가이드

## 📋 개요

**마이그레이션 일자**: 2025-09-22
**베이스 커밋**: 2112f36 (feat: complete REPORTS path normalization and metadata lock)
**브랜치**: feature/reports-casing-guard
**목적**: macOS case-insensitive 파일시스템 이슈 해결 및 경로 표준화

## 🔍 배경

### 문제 상황
- macOS의 case-insensitive 파일시스템에서 `reports/`와 `REPORTS/` 경로가 혼재
- git mv 작업이 완전하지 않아 소문자 경로가 잔존
- workflow 파일에서 경로 참조 불일치 발생
- 문서 링크에서 케이스 불일치로 인한 접근성 문제

### 기술적 원인
```bash
# macOS HFS+/APFS는 case-insensitive (기본 설정)
ls -la reports/     # 동일한 디렉토리를 가리킴
ls -la REPORTS/     # 동일한 디렉토리를 가리킴

# Git은 case-sensitive 하지만 파일시스템이 case-insensitive
git mv reports REPORTS  # 실제로는 변경되지 않음
```

## 📏 개발 수칙

### ✅ 준수 사항
1. **항상 대문자 사용**: `REPORTS/` 경로만 사용
2. **일관성 유지**: 모든 문서, 스크립트, workflow에서 동일한 케이스 사용
3. **검증 필수**: 커밋 전 `./scripts/check_reports_casing.sh` 실행

### ❌ 금지 사항
1. **소문자 경로 생성**: `reports/` 새 파일/폴더 금지
2. **혼재 사용**: 같은 파일 내에서 다른 케이스 혼용 금지
3. **자동 생성 도구**: IDE나 도구의 자동 경로 생성 주의

## 🚫 실패 패턴 및 대응

### 자주 발생하는 실패 사례

#### 1. IDE 자동 완성
```bash
# ❌ 잘못된 예
cd reports/incident-center  # IDE 자동완성으로 생성

# ✅ 올바른 예
cd REPORTS/incident-center
```

#### 2. 상대 경로 링크
```markdown
<!-- ❌ 잘못된 예 -->
[링크](../reports/incident-center/INDEX.md)

<!-- ✅ 올바른 예 -->
[링크](../REPORTS/incident-center/INDEX.md)
```

#### 3. Workflow 경로
```yaml
# ❌ 잘못된 예
path: reports/incident-center/WEEKLY/

# ✅ 올바른 예
path: REPORTS/incident-center/WEEKLY/
```

### 대응 방법

#### 로컬 개발 시
```bash
# 1. 사전 검사
./scripts/check_reports_casing.sh

# 2. 문제 발견 시 수정
find . -name "*reports*" -type f | grep -v REPORTS/
# → 발견된 파일들을 REPORTS/로 이동

# 3. 재검증
./scripts/check_reports_casing.sh
```

#### CI/CD에서
- pre-commit 훅이 자동으로 차단
- PR에서 `reports_casing_guard.yml` 워크플로가 검증
- 실패 시 자동 코멘트로 해결 방법 안내

## 🔧 마이그레이션 절차

### 신규 파일 생성 시
```bash
# 1. 올바른 경로에 생성
touch REPORTS/incident-center/new-report.md

# 2. 검증
./scripts/check_reports_casing.sh

# 3. 커밋 (pre-commit 훅이 자동 검사)
git add REPORTS/incident-center/new-report.md
git commit -m "docs: add new incident report"
```

### 기존 파일 이동 시
```bash
# macOS에서 안전한 이동 방법
git mv reports REPORTS_tmp
git mv REPORTS_tmp REPORTS

# 링크 참조 업데이트
sed -i '' 's/reports\//REPORTS\//g' file.md

# 검증
./scripts/check_reports_casing.sh
```

## 🔄 롤백 가이드

### 긴급 롤백이 필요한 경우
```bash
# 1. 베이스 커밋으로 복원
git checkout 2112f36

# 2. 새 브랜치 생성
git checkout -b hotfix/revert-casing-guard

# 3. 필요한 파일만 선택적 복원
git checkout main -- specific-file.md

# 4. 검증 후 푸시
./scripts/check_reports_casing.sh
git push origin hotfix/revert-casing-guard
```

### 부분 롤백
- **코드 변경 없음**: 문서 이동만 있으므로 안전
- **선택적 복원**: 특정 문서만 이전 경로로 복원 가능
- **점진적 적용**: 단계별로 경로 변경 적용 가능

## 🛡️ 재발 방지 시스템

### 1. Pre-commit 훅 (로컬)
- **위치**: `.git/hooks/pre-commit`
- **기능**: 커밋 시점에 `reports/` 경로 차단
- **설치**: 자동 (클론 시 수동 설치 필요)

### 2. CI 가드 (GitHub Actions)
- **파일**: `.github/workflows/reports_casing_guard.yml`
- **트리거**: PR 생성/업데이트 시
- **기능**: `reports/` 발견 시 PR 자동 실패

### 3. 검증 스크립트 (범용)
- **파일**: `scripts/check_reports_casing.sh`
- **사용**: 로컬/CI 모두 호환
- **기능**: 전체 레포지토리 케이스 검증

## 📞 지원 및 문의

### 기술 지원
- **Slack**: #dev-infrastructure
- **GitHub Issues**: incident-center 라벨 사용
- **문서**: 이 마이그레이션 가이드 참조

### 추가 자료
- [README 개발 규칙](../README.md#개발-규칙)
- [LINK_AUDIT Casing Guard 섹션](../reports/incident-center/v1.0.1-pre/LINK_AUDIT.md#casing-guard-설치-상태)
- [POST_FIX_SUMMARY](../reports/incident-center/POST_FIX_SUMMARY.md)

---

**⚠️ 중요**: 이 가이드는 macOS 개발 환경을 기준으로 작성되었습니다. Linux/Windows 환경에서는 case-sensitive 이슈가 다르게 나타날 수 있습니다.