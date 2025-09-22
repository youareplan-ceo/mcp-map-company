# Incident Center Archive Manifest

## 📋 확정 정보

| 항목 | 값 |
|------|---|
| **확정 시각** | 2025-09-22 15:38:38 KST (Asia/Seoul) |
| **커밋** | e9979e2 Merge pull request #10 from youareplan-ceo/feature/reports-casing-guard |
| **태그** | reports-casing-guard-2025-09-22 |
| **릴리스** | https://github.com/youareplan-ceo/mcp-map-company/releases/tag/untagged-4bd60694c3fbe6a15bbe |
| **작성자** | Claude Code + 김실장 검수 |

## 🔐 핵심 자산 체크섬 (SHA256)

### 📊 상태 보고서
| 파일명 | SHA256 | 크기 | 설명 |
|--------|---------|------|------|
| INDEX.md | 9a9894a3d9cc28eac6b754442cf0c3415b909adef650f8c21a49ac2d5262c650 | 2,510 bytes | 인덱스 문서 (v1.0.2 구조) |
| POST_MERGE_AUDIT.md | f7053d72171c2026e1ffca7c558003e9d81eb9e69c458eeacbb8bd3a2aa74427 | 578 bytes | PR #10 병합 감사 보고서 |

## 🔄 Change Log (2025-09-22 15:38:38 KST)

### 신규 문서 추가
| 파일 | SHA256 해시 | 크기 | 변경 시각 |
|------|-------------|------|-----------|
| REPORTS/incident-center/INDEX.md | 9a9894a3d9cc28eac6b754442cf0c3415b909adef650f8c21a49ac2d5262c650 | 2,510 bytes | 2025-09-22 15:38:38 KST |
| REPORTS/incident-center/v1.0.2-planning/POST_MERGE_AUDIT.md | f7053d72171c2026e1ffca7c558003e9d81eb9e69c458eeacbb8bd3a2aa74427 | 578 bytes | 2025-09-22 15:38:38 KST |

## 🔍 무결성 검증

### ✅ 체크섬 확정 조건
- [x] 모든 핵심 문서 SHA256 계산 완료
- [x] main 브랜치 HEAD 커밋 고정 (e9979e2)
- [x] 태그 reports-casing-guard-2025-09-22 확인
- [x] GitHub 릴리스 자산 첨부 확인
- [x] 체크섬 불일치 없음

### 🔐 검증 방법
```bash
# 체크섬 재검증 명령어
cd REPORTS/incident-center/
shasum -a 256 INDEX.md  # 9a9894a3d9cc28eac6b754442cf0c3415b909adef650f8c21a49ac2d5262c650
shasum -a 256 v1.0.2-planning/POST_MERGE_AUDIT.md  # f7053d72171c2026e1ffca7c558003e9d81eb9e69c458eeacbb8bd3a2aa74427
```

## 📚 연관 자산

### GitHub 리소스
- **PR #10**: https://github.com/youareplan-ceo/mcp-map-company/pull/10 (MERGED)
- **Release**: https://github.com/youareplan-ceo/mcp-map-company/releases/tag/untagged-4bd60694c3fbe6a15bbe
- **Tag**: reports-casing-guard-2025-09-22 (e9979e2)

### 로컬 문서
- **리포트 인덱스**: REPORTS/incident-center/INDEX.md
- **병합 감사**: v1.0.2-planning/POST_MERGE_AUDIT.md

## ⚠️ 보존 정책

### 🔒 영구 보존 (삭제 금지)
- 모든 SHA256 확정된 파일
- GitHub 릴리스 첨부 자산
- 태그 및 커밋 이력

### 📋 변경 금지
이 매니페스트 확정 후 다음 작업 금지:
- 확정된 파일의 내용 수정
- SHA256 값 변경
- 릴리스 자산 교체

**결론**: ✅ Incident Center post-merge 체크섬 확정 완료