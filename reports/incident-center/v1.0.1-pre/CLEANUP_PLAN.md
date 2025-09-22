# Incident Center v1.0.1-pre 정리 계획서

## 🔒 문서 잠금 (최종 고정)

| 항목 | 값 |
|------|---|
| **갱신 시각** | 2025-09-22 14:50:00 KST (Asia/Seoul) |
| **브랜치** | main (병합 완료) |
| **최신 커밋** | d4a8a36 docs(incident-center): finalize post-merge archive |
| **태그** | incident-center-v1.0.1-pre-merged |
| **작성자** | Claude Code + 김실장 검수 |
| **상태** | 🔒 LOCKED - 병합/태그/릴리스 완료 |

## 📋 정리 대상

### 1. .worktrees 디렉토리 ✅ 완료
- **경로**: `/Users/youareplan/Desktop/mcp-map-company/.worktrees/`
- **상태**: 이미 제거됨
- **문제**: "File name too long" 에러 발생
- **해결**: 완전 삭제 및 .gitignore 추가

### 2. 백업 파일들
| 파일 | 크기 | 상태 |
|------|------|------|
| `scripts/dashboard_smoke_incidents.sh.backup` | 16,668 bytes | 보관 필요 |
| `scripts/incident_post_release_smoke.sh.backup` | 10,793 bytes | 보관 필요 |

### 3. 충돌 해결 diff 파일들
| 파일 | 크기 | 처리 |
|------|------|------|
| `reports/incident-center/v1.0.1-pre/dashboard_conflict.diff` | ~1KB | 문서화용 보관 |
| `reports/incident-center/v1.0.1-pre/post_release_conflict.diff` | ~1KB | 문서화용 보관 |

## 🗑️ 정리 권장사항

### 즉시 정리 가능 (계획서만 - 실행 금지)
```bash
# ⚠️ 계획서만 - 실제 삭제 금지
# 임시 로그 파일들 (RAW_LOGS_*1-4.txt 제거하고 최신 v5만 보관)
# rm -f reports/incident-center/v1.0.1-pre/RAW_LOGS_dryrun[1-4].txt
# rm -f reports/incident-center/v1.0.1-pre/RAW_LOGS_full[1-4].txt

# /tmp 임시 파일들 정리 (계획만)
# rm -f /tmp/pr_body_*.md
# rm -f /tmp/release_body.md
```

### 조건부 정리 (1주 후)
```bash
# diff 파일들 (문서화 완료 후)
rm -f reports/incident-center/v1.0.1-pre/*_conflict.diff

# 중간 상태 파일들
rm -f reports/incident-center/v1.0.1-pre/DIFF*.md
rm -f reports/incident-center/v1.0.1-pre/UNTRACKED.md
```

### 영구 보관
- `*.backup` 파일들: 복구용으로 영구 보관
- `COMPLETE_STATUS.md`, `POST_MERGE_TAG_RELEASE.md`: 프로젝트 히스토리
- `RAW_LOGS_dryrun5.txt`, `RAW_LOGS_full5.txt`: 최종 테스트 결과

## ⚠️ 주의사항

1. **백업 파일 보관**: `.backup` 파일들은 향후 롤백 시 필요할 수 있음
2. **GitHub 릴리스 자산**: 5개 파일은 GitHub Release에 첨부되어 별도 보관됨
3. **문서 무결성**: 완료된 문서들은 SHA256 체크섬으로 검증 가능

## 📊 정리 후 예상 공간 절약

- **즉시 정리**: ~8KB (구버전 RAW_LOGS)
- **조건부 정리**: ~15KB (diff 및 중간 파일들)
- **총 절약**: ~23KB

---

**✅ 정리 계획 수립 완료** - 단계별 정리 가이드라인 확정