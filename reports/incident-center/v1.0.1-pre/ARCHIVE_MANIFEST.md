# Incident Center v1.0.1-pre 아카이브 매니페스트

## 📊 아카이브 메타데이터

| 항목 | 값 |
|------|---|
| **생성 시각** | 2025-09-22 13:41:58 KST (Asia/Seoul) |
| **브랜치** | hotfix/incident-center-v1.0.1-pre |
| **커밋** | 9ef0c25 final(incident-center): status snapshot locked; smoke logs v4; PR finalized; tag/release drafts ready (no deploy) |
| **아카이브 범위** | v1.0.1-pre 전체 산출물 |

## 📁 아카이브 대상 파일 및 체크섬 (SHA256)

### 1. 핵심 리포트 파일

| 파일명 | 경로 | SHA256 체크섬 | 크기 |
|--------|------|---------------|------|
| **SUMMARY.md** | reports/incident-center/v1.0.1-pre/ | `c266075e35f0eae9a601747868031f1ed673e9597d51889e20bd2af7e1c2e243` | 2,479 bytes |
| **DIFF.md** | reports/incident-center/v1.0.1-pre/ | `589293090d2ad3883588f0d2d5c8142b084288ec38318ec5af9ff93cd4c8208e` | 2,195 bytes |
| **COMPARE.md** | reports/incident-center/v1.0.1-pre/ | `e174b117327daf122c8e77f4d3eb43392147f3f62d8f29e4a73d37b113b9ce72` | 3,707 bytes |
| **COMPLETE_STATUS.md** | reports/incident-center/v1.0.1-pre/ | `5ecc46856e3b86921af4efcfc66f80bd740c54449b0b935b2dfb8749ec9f3498` | 5,122 bytes |
| **PRE_MERGE_CHECK.md** | reports/incident-center/v1.0.1-pre/ | `5cf828c581c6b5d2adc21f9039326fdc4f1f533d49a1c739a7351558ef617a3a` | 3,288 bytes |

### 2. 스모크 테스트 로그

| 파일명 | 경로 | SHA256 체크섬 | 크기 |
|--------|------|---------------|------|
| **RAW_LOGS_dryrun4.txt** | reports/incident-center/v1.0.1-pre/ | `46847fd62127e4c097ebb6c7f78ea13c42042c523062952d22a8fe29ecc0ec3f` | 482 bytes |
| **RAW_LOGS_full4.txt** | reports/incident-center/v1.0.1-pre/ | `953df821962127d8e1349042f6b9cb3b796b3e8bc91de2bfeec6dd3f73d8f980` | 1,634 bytes |

### 3. 거버넌스 및 관리 문서

| 파일명 | 경로 | SHA256 체크섬 | 크기 |
|--------|------|---------------|------|
| **INDEX.md** | reports/incident-center/ | `4d5d10a86b87a6f797bf7983b71e2f68a0a34ac8afc9f42d71df5615a28e46c2` | 1,652 bytes |
| **ENV_REQUIRED.md** | reports/incident-center/ | `6534199802df584c4b5f5f47ab33eed5197d5dffb35830e39b17031d9762df12` | 2,965 bytes |
| **GOVERNANCE.md** | 루트 | `bb827458a233ba7ea0ed9c6df837a7802beaf5fa78f954c3194dbf2da36309cc` | 4,167 bytes |
| **TAG_RELEASE_DRAFT.md** | 루트 | `56c493d8d8055eff45744efe180c80aab2d4e1a16fba9672f02b39abb3cbbc99` | 3,850 bytes |
| **ROLLBACK.md** | reports/incident-center/ | `f90e17b013c82b70c0af112be6308abd893692e10d1deb08c74639d2418d50c0` | 4,721 bytes |

### 4. 추가 생성 예정 파일

| 파일명 | 경로 | SHA256 체크섬 | 상태 |
|--------|------|---------------|------|
| **POST_MERGE_TAG_RELEASE.md** | reports/incident-center/v1.0.1-pre/ | PENDING | 병합 후 생성 |
| **ARCHIVE_MANIFEST.md** | reports/incident-center/v1.0.1-pre/ | SELF | 현재 문서 |

## 📊 아카이브 통계

| 구분 | 파일 수 | 총 크기 |
|------|---------|---------|
| **핵심 리포트** | 5개 | 16,791 bytes |
| **스모크 로그** | 2개 | 2,116 bytes |
| **거버넌스 문서** | 5개 | 17,355 bytes |
| **총합** | 12개 | 36,262 bytes (35.4 KB) |

## 🔐 무결성 검증

### 체크섬 검증 명령어
```bash
# 개별 파일 검증 예시
echo "c266075e35f0eae9a601747868031f1ed673e9597d51889e20bd2af7e1c2e243  SUMMARY.md" | shasum -a 256 -c

# 전체 매니페스트 검증 (아카이브 전)
find reports/incident-center/v1.0.1-pre/ -name "*.md" -o -name "*.txt" | \
  xargs shasum -a 256 > archive_checksums.txt
```

### 아카이브 완료 후 검증
```bash
# 아카이브에서 추출 후 무결성 검증
tar -tzf incident-center-v1.0.1-pre-archive.tar.gz | head -10
tar -xzf incident-center-v1.0.1-pre-archive.tar.gz
shasum -a 256 -c archive_checksums.txt
```

## 📋 아카이브 절차 (권장)

### 1. 아카이브 생성
```bash
# 아카이브 디렉토리 준비
mkdir -p archives/incident-center-v1.0.1-pre/

# 핵심 파일 복사
cp -r reports/incident-center/ archives/incident-center-v1.0.1-pre/
cp GOVERNANCE.md TAG_RELEASE_DRAFT.md archives/incident-center-v1.0.1-pre/

# 압축 아카이브 생성
tar -czf incident-center-v1.0.1-pre-archive.tar.gz -C archives/ incident-center-v1.0.1-pre/
```

### 2. 아카이브 검증
```bash
# 압축 파일 무결성 확인
tar -tzf incident-center-v1.0.1-pre-archive.tar.gz | wc -l
shasum -a 256 incident-center-v1.0.1-pre-archive.tar.gz
```

## 🔒 아카이브 고정

| 항목 | 값 |
|------|---|
| **매니페스트 생성 시각** | 2025-09-22 13:41:58 KST (Asia/Seoul) |
| **대상 브랜치** | hotfix/incident-center-v1.0.1-pre |
| **기준 커밋** | 9ef0c25 |
| **아카이브 범위** | v1.0.1-pre 전체 산출물 |
| **작성자** | Claude Code + 김실장 검수 |

---

**✅ 아카이브 매니페스트 완료** - 12개 파일, 35.4 KB, SHA256 체크섬 검증 가능