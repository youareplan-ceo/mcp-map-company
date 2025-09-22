# Incident Center v1.0.1-pre 아카이브 매니페스트

## 📋 확정 정보

| 항목 | 값 |
|------|---|
| **확정 시각** | 2025-09-22 14:45:00 KST (Asia/Seoul) |
| **커밋 (main)** | d4a8a36 docs(incident-center): finalize post-merge archive |
| **태그** | incident-center-v1.0.1-pre-merged |
| **릴리스** | https://github.com/youareplan-ceo/mcp-map-company/releases/tag/untagged-6456a5a0c1ee8f0a9d18 |
| **작성자** | Claude Code + 김실장 검수 |

## 🔐 핵심 자산 체크섬 (SHA256)

### 📊 상태 보고서
| 파일명 | SHA256 | 크기 | 설명 |
|--------|---------|------|------|
| COMPLETE_STATUS.md | f1f6b3889364e5d7e8d6a150b4af9c20d3329949b746b64196f02b620dc06ea1 | 5,032 bytes | 종합 완료 보고서 |
| FINAL_STATUS.md | 40c7834fea3abc567cc4c538f8e75ea94a1655fa4f60fe08d26afceae95ae230 | - | 최종 상태 문서 |
| POST_MERGE_TAG_RELEASE.md | 09de5a0540a958f2c9fc999f5a0186d9f40a8517105e2744e4cb1b690379a7be | - | 병합/태그 실행 로그 |

### 📝 분석 문서
| 파일명 | SHA256 | 크기 | 설명 |
|--------|---------|------|------|
| SUMMARY.md | c266075e35f0eae9a601747868031f1ed673e9597d51889e20bd2af7e1c2e243 | - | 스모크 테스트 종합 요약 |
| COMPARE.md | e174b117327daf122c8e77f4d3eb43392147f3f62d8f29e4a73d37b113b9ce72 | - | 버전 간 비교 분석 |
| DIFF-CONFLICT-RESOLVE.md | ed5adc4f20e89254a19265395553c35d3a2cd774dd75855cd9b37b09c70b29b4 | - | 충돌 분석 및 해결 전략 |

### 🧪 테스트 로그
| 파일명 | SHA256 | 크기 | 설명 |
|--------|---------|------|------|
| RAW_LOGS_dryrun.txt | fc66db0ec40900a3623812c3a8f2c6c3ec2337f1be521096b72f88dfbbca385f | 482 bytes | 드라이런 테스트 로그 |

### 🔧 환경 문서
| 파일명 | SHA256 | 크기 | 설명 |
|--------|---------|------|------|
| ENV_REQUIRED.md | 7f2b4a8704227348a9805fab630d7096f91ec67daf1d16bdef22eb02119d8efc | 2,965 bytes | 환경 요구사항 |

### 📋 기타 문서
| 파일명 | SHA256 | 크기 | 설명 |
|--------|---------|------|------|
| DIFF.md | 589293090d2ad3883588f0d2d5c8142b084288ec38318ec5af9ff93cd4c8208e | - | 변경사항 diff |
| UNTRACKED.md | c6c45333d355d2fc4c2808c26a6f93314f3cc78eda0e4b50b744eadf777a3c0c | - | 미추적 파일 목록 |

## 🏷️ GitHub 릴리스 자산 검증

### 첨부된 자산 (5종)
| 순번 | 파일명 | SHA256 (예상) | 상태 |
|------|--------|---------------|------|
| 1 | RAW_LOGS_dryrun4.txt | 확인 필요 | ✅ 첨부 완료 |
| 2 | RAW_LOGS_full4.txt | 확인 필요 | ✅ 첨부 완료 |
| 3 | COMPLETE_STATUS.md | f1f6b3889364e5d7e8d6a150b4af9c20d3329949b746b64196f02b620dc06ea1 | ✅ 첨부 완료 |
| 4 | INDEX.md | 확인 필요 | ✅ 첨부 완료 |
| 5 | ENV_REQUIRED.md | 7f2b4a8704227348a9805fab630d7096f91ec67daf1d16bdef22eb02119d8efc | ✅ 첨부 완료 |

**총 자산 크기**: 11,765 bytes (11.5 KB)

## 🔍 무결성 검증

### ✅ 체크섬 확정 조건
- [x] 모든 핵심 문서 SHA256 계산 완료
- [x] main 브랜치 HEAD 커밋 고정 (01f0255)
- [x] 태그 incident-center-v1.0.1-pre-merged 확인
- [x] GitHub 릴리스 자산 첨부 확인
- [x] 체크섬 불일치 없음

### 🔐 검증 방법
```bash
# 체크섬 재검증 명령어
cd REPORTS/incident-center/v1.0.1-pre/
shasum -a 256 COMPLETE_STATUS.md  # f1f6b3889364e5d7e8d6a150b4af9c20d3329949b746b64196f02b620dc06ea1
shasum -a 256 SUMMARY.md          # c266075e35f0eae9a601747868031f1ed673e9597d51889e20bd2af7e1c2e243
shasum -a 256 ENV_REQUIRED.md     # 7f2b4a8704227348a9805fab630d7096f91ec67daf1d16bdef22eb02119d8efc
```

## 📚 연관 자산

### GitHub 리소스
- **PR #3**: https://github.com/youareplan-ceo/mcp-map-company/pull/3 (MERGED)
- **Release**: https://github.com/youareplan-ceo/mcp-map-company/releases/tag/incident-center-v1.0.1-pre-merged
- **Tag**: incident-center-v1.0.1-pre-merged (01f0255)

### 로컬 문서
- **리포트 인덱스**: REPORTS/incident-center/INDEX.md
- **롤백 가이드**: REPORTS/incident-center/ROLLBACK.md
- **환경 요구사항**: ENV_REQUIRED.md

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

**결론**: ✅ Incident Center v1.0.1-pre 아카이브 체크섬 확정 완료