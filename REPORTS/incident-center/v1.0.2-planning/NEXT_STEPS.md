# NEXT_STEPS - 다음 단계 안내 (v1.0.2)

## 🎯 Sprint-1 이슈 착수 순서

**우선 순위**: #11 → #12 → #14 → #15 → #13 → #16

1. **#11**: 핵심 인프라 기반 작업
2. **#12**: 문서화 표준 정립
3. **#14**: 자동화 확장
4. **#15**: 품질 보증 시스템
5. **#13**: 사용자 경험 개선
6. **#16**: 성능 최적화

## 📊 주간 점검 프로세스

**주간 모니터**: weekly_monitor 결과를 WEEKLY/*로 보관(3문서)

### 필수 산출물
- `WEEKLY/LINKS_STATUS_YYYY-MM-DD.md` - 링크 상태 검증
- `WEEKLY/BADGES_STATUS_YYYY-MM-DD.md` - 배지 상태 체크
- `WEEKLY/INTEGRITY_YYYY-MM-DD.md` - 무결성 검증

### 보관 정책
- 매주 금요일 실행 권장
- MONITORING_GUIDE.md 상단 표에 결과 링크 추가
- 3개월 이상 보관 (삭제 금지)

## 🔧 문서 변경 시 필수 절차

**변경 전/후**: make incident-links / make incident-audit 필수

### 워크플로
1. 문서 수정 전: `make incident-links` (링크 검증)
2. 문서 수정 진행
3. 문서 수정 후: `make incident-audit` (무결성 검증)
4. 체크섬 갱신 (ARCHIVE_MANIFEST.md)

## ⚠️ casing guard/CI 실패 시 대응

**실패 시**: REPORTS/incident-center/LINK_AUDIT.md 최상단에 사유 기록 후 중단

### 에러 처리 절차
1. LINK_AUDIT.md 최상단에 실패 원인/시각 기록
2. 작업 중단 (추가 변경 금지)
3. 근본 원인 분석 후 수정
4. 재검증 완료 후 작업 재개

## 🚀 배포 정책

**NO-DEPLOY**: 문서/자동화만

### 제한 사항
- Render/Vercel 배포 금지
- 라이브 서비스 영향 차단
- 문서 및 CI/CD 자동화 변경만 허용
- 인프라 변경 시 별도 승인 필요

---

**생성 일시**: 2025-09-22 15:59:00 KST (Asia/Seoul)
**담당**: Claude Code v1.0.2 Planning
**상태**: 🔒 LOCKED - 변경 시 ARCHIVE_MANIFEST 갱신 필수