# Weekly Monitoring Integration Guide

## 📋 개요

**목적**: weekly_monitor.yml 워크플로와 Sprint 진행 상황 연동 가이드
**범위**: 주간 점검 보고서에 Sprint 메모 자동 적용 시스템
**정책**: 🚫 **NO-DEPLOY** (모니터링 및 문서화만)

## 🔄 weekly_monitor 워크플로 개요

| 항목 | 값 |
|------|-----|
| **실행 주기** | 매주 월요일 00:00 UTC (한국 시간 09:00) |
| **실행 방식** | 자동 스케줄링 + 수동 실행 허용 |
| **생성 파일 경로** | `REPORTS/incident-center/WEEKLY/` |
| **생성 파일 종류** | LINKS_STATUS_*.md, BADGES_STATUS_*.md, INTEGRITY_*.md, SUMMARY_*.md |

## 📊 주간 점검 로그

| 검사 항목 | 실행 job | 산출 파일 | 메모 규칙 적용 | 상태 |
|----------|----------|-----------|----------------|------|
| **링크 상태 검사** | links-check | LINKS_STATUS_${DATE}.md | ✅ Sprint-1 진행 메모 추가 | 🔄 자동화 |
| **배지 상태 검사** | badges-check | BADGES_STATUS_${DATE}.md | ✅ Sprint-1 진행 메모 추가 | 🔄 자동화 |
| **무결성 검사** | integrity-check | INTEGRITY_${DATE}.md | ✅ Sprint-1 진행 메모 추가 | 🔄 자동화 |
| **주간 요약** | summary | SUMMARY_${DATE}.md | ✅ Sprint-1 진행 메모 추가 | 🔄 자동화 |

## 🚀 Sprint-1 진행 메모 규칙

### 메모 형식 표준
```markdown
## 🚀 Sprint-1 진행 메모

**기간**: 2025-09-23 09:00 KST ~ 2025-10-15 18:00 KST
**상태**: [진행중/완료/지연]

### 이슈 진행 상황
- **#11 DOM/선택자 안정화**: [상태] - [비고]
- **#12 CI 매트릭스 확장**: [상태] - [비고]
- **#14 Link Audit 엄격모드**: [상태] - [비고]

### 주간 체크포인트
- [ ] CI 매트릭스 테스트 통과 (Python 3.11-3.13)
- [ ] 링크 404 오류 0건 달성
- [ ] DOM 선택자 표준화 진행률 확인

**업데이트**: $(date -u '+%Y-%m-%d %H:%M:%S') UTC
```

### 자동 적용 로직
weekly_monitor.yml의 각 job에서 생성되는 보고서 파일 하단에 위 메모 형식이 자동으로 추가됩니다.

**적용 위치**:
- `REPORTS/incident-center/WEEKLY/LINKS_STATUS_*.md`
- `REPORTS/incident-center/WEEKLY/BADGES_STATUS_*.md`
- `REPORTS/incident-center/WEEKLY/INTEGRITY_*.md`
- `REPORTS/incident-center/WEEKLY/SUMMARY_*.md`

## 📝 메모 업데이트 절차

### 1. 자동 업데이트 (weekly_monitor 실행 시)
```bash
# GitHub Actions에서 자동 실행
echo "## 🚀 Sprint-1 진행 메모" >> report_file.md
echo "**기간**: 2025-09-23 09:00 KST ~ 2025-10-15 18:00 KST" >> report_file.md
echo "**상태**: 진행중" >> report_file.md
# ... 이슈 상태 추가
```

### 2. 수동 업데이트 (필요 시)
```bash
# 로컬에서 수동 업데이트
cd /Users/youareplan/Desktop/mcp-map-company
find REPORTS/incident-center/WEEKLY -name "*.md" -exec echo "메모 추가 필요" {} \;
```

## 🎯 Sprint-1 이슈 매핑

| 이슈 번호 | 제목 | 우선순위 | 예상 완료일 | 모니터링 연관성 |
|----------|------|----------|-------------|----------------|
| **#11** | DOM/선택자 안정화 | P1 (High) | 2025-10-05 | 배지 상태 검사와 연관 |
| **#12** | CI 매트릭스 확장 | P0 (Critical) | 2025-09-30 | 링크 상태 검사와 연관 |
| **#14** | Link Audit 엄격모드 | P1 (High) | 2025-10-10 | 링크/무결성 검사와 직접 연관 |

## 📊 주간 모니터링 KPI

### 목표 지표
- **링크 검사 성공률**: > 95%
- **배지 HTTP 200 응답률**: 100%
- **무결성 체크섬 일치율**: 100%
- **Sprint-1 이슈 진행률**: 주간 20% 이상

### 알람 조건
- 링크 404 오류 1건 이상 발견 시
- 배지 HTTP 오류 발생 시
- 체크섬 불일치 발견 시
- Sprint-1 이슈 지연 발생 시

## 🔧 워크플로 커스터마이징

### weekly_monitor.yml 주요 수정 사항
```yaml
# 최종 커밋 단계에서 Sprint-1 메모 규칙 적용
- name: Commit weekly reports (if any changes)
  run: |
    # ... 기존 커밋 로직
  continue-on-error: true
  # NOTE: Sprint-1 진행 메모 규칙 적용
  # WEEKLY/* 파일 하단에 'Sprint-1 진행 메모: #11~#16 이슈 상태' 단락을 편집 반영
```

### 메모 템플릿 확장 (향후)
Sprint-2, Sprint-3 진행 시 메모 형식을 다음과 같이 확장:
```markdown
## 🚀 Sprint-2 진행 메모
- #15 문서 자동 점검: [상태]

## 🚀 Sprint-3 진행 메모
- #13 대시보드 카피/툴팁: [상태]
- #16 아카이브 스냅샷 자동화: [상태]
```

## 📋 체크리스트

### weekly_monitor 실행 전
- [ ] Sprint-1 이슈 상태 최신화
- [ ] 메모 규칙 템플릿 확인
- [ ] 워크플로 권한 확인

### weekly_monitor 실행 후
- [ ] 생성된 보고서 파일 확인
- [ ] Sprint-1 메모 자동 적용 검증
- [ ] GitHub commit 성공 확인
- [ ] 다음 주 스케줄 확인

---

**작성일**: 2025-09-22 15:45:00 KST (Asia/Seoul)
**담당**: Claude Code
**연결**: weekly_monitor.yml, v1.0.2-planning/ISSUES_PLAN.md
**상태**: 📋 모니터링 연동 가이드 완료