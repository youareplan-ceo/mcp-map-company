# MCP Map Company 거버넌스 정책

## 🔒 문서 잠금 (최종 고정)

| 항목 | 값 |
|------|---|
| **잠금 시각** | 2025-09-22 14:00:00 KST (Asia/Seoul) |
| **브랜치** | main |
| **최신 커밋** | a83d98d chore(incident-center): normalize REPORTS links |
| **작성자** | Claude Code + 김실장 검수 |
| **상태** | 🔒 LOCKED - 거버넌스 정책 확정 |

---

## 📋 조직 구조 및 담당자

### 핵심 담당자
| 역할 | 담당자 | 연락 방법 | 책임 범위 |
|------|--------|-----------|-----------|
| **CEO** | 김실장 | GitHub @youareplan-ceo | 전략 승인, 최종 결정 |
| **기술 담당** | Claude Code | Auto-assignment | 개발, 문서화, CI/CD |
| **품질 관리** | 자동화 시스템 | weekly_monitor.yml | 링크, 배지, 무결성 검사 |
| **보안 담당** | 통합 관리 | ENV_REQUIRED.md | 시크릿 관리, 접근 제어 |

### 연락 루틴
- **일반 이슈**: GitHub Issues를 통한 자동 할당
- **긴급 상황**: PR 댓글 또는 직접 멘션 (@youareplan-ceo)
- **정기 보고**: 매주 월요일 weekly_monitor.yml 자동 실행
- **문서 업데이트**: commit 기반 자동 알림

---

## 🔄 CI/CD 거버넌스

### 자동화 주기 (weekly_monitor.yml)
| 작업 | 주기 | 담당 시스템 | 결과 저장 |
|------|------|-------------|-----------|
| **링크 검사** | 매주 월요일 00:00 UTC | GitHub Actions | `REPORTS/incident-center/WEEKLY/LINKS_STATUS_*.md` |
| **배지 상태** | 매주 월요일 00:00 UTC | GitHub Actions | `REPORTS/incident-center/WEEKLY/BADGES_STATUS_*.md` |
| **무결성 검사** | 매주 월요일 00:00 UTC | GitHub Actions | `REPORTS/incident-center/WEEKLY/INTEGRITY_*.md` |
| **요약 리포트** | 매주 월요일 00:01 UTC | GitHub Actions | `REPORTS/incident-center/WEEKLY/SUMMARY_*.md` |

### 승인 체계
1. **코드 변경**: PR 기반 리뷰 (최소 1명 승인)
2. **문서 업데이트**: 자동 승인 (Claude Code)
3. **CI 설정 변경**: 김실장 최종 승인 필요
4. **시크릿 추가**: ENV_REQUIRED.md에 키 이름만 기록, 값은 수동 설정

---

## 🚫 No-Deploy 정책

### 정책 원칙
| 항목 | 정책 | 예외 조건 |
|------|------|-----------|
| **실배포 금지** | Render/Vercel 등 프로덕션 배포 금지 | 김실장 명시적 승인 시만 |
| **태그/릴리스** | Draft 상태로만 생성 | 문서화 및 백업 목적 |
| **브랜치 전략** | main 브랜치 보호, hotfix 분리 | 긴급 패치는 별도 협의 |
| **코드 품질** | 모든 commit에 linting 적용 | CI 실패 시 merge 차단 |

### 배포 승인 프로세스
1. **사전 검토**: COMPLETE_STATUS.md 체크리스트 100% 완료
2. **보안 검사**: ENV_REQUIRED.md 시크릿 키 검증
3. **테스트 통과**: incident_smoke.yml 및 weekly_monitor.yml 성공
4. **문서 완성**: GOVERNANCE.md + ROLLBACK.md 잠금 확인
5. **최종 승인**: 김실장 서면 승인 + PR 코멘트

---

## 📊 모니터링 및 알림

### 자동 모니터링 대상
- **GitHub Actions 상태**: 모든 워크플로 실행 결과
- **PR 상태**: 활성 PR 개수 및 리뷰 상태
- **링크 무결성**: README, REPORTS 내 모든 링크 유효성
- **배지 상태**: Actions, PR 배지 렌더링 정상성
- **파일 무결성**: ARCHIVE_MANIFEST.md 기반 체크섬 검증

### 알림 규칙
| 상황 | 알림 방법 | 대응 담당자 |
|------|-----------|-------------|
| **CI 실패** | GitHub 자동 알림 | Claude Code |
| **링크 깨짐** | weekly_monitor.yml 리포트 | 기술 담당 |
| **보안 이슈** | 즉시 이슈 생성 | 보안 담당 |
| **문서 변조** | 무결성 검사 실패 | 전체 팀 |

---

## 🔧 문제 해결 및 에스컬레이션

### 1차 대응 (자동화)
- **CI 실패**: 자동 재시도 (최대 3회)
- **링크 검사 실패**: LINKS_STATUS.md에 상세 기록
- **배지 오류**: BADGES_STATUS.md에 HTTP 상태 기록

### 2차 대응 (Claude Code)
- **코드 리뷰**: PR 품질 검토 및 피드백
- **문서 업데이트**: 정책 변경 반영
- **CI 설정 조정**: 워크플로 최적화

### 3차 대응 (김실장)
- **정책 변경**: 거버넌스 룰 수정
- **시크릿 관리**: 민감 정보 설정
- **배포 승인**: 프로덕션 배포 최종 결정

---

## 📋 체크리스트 및 템플릿

### PR 생성 시 필수 체크리스트
- [ ] 모든 테스트 통과 (incident_smoke.yml)
- [ ] 문서 업데이트 완료 (해당 시)
- [ ] 시크릿 노출 없음 확인
- [ ] No-deploy 정책 준수
- [ ] 관련 이슈 연결

### 릴리스 생성 시 필수 체크리스트
- [ ] COMPLETE_STATUS.md 잠금 완료
- [ ] 모든 자산 파일 첨부 (5종)
- [ ] Draft 상태로 생성
- [ ] no-deploy 명시
- [ ] ROLLBACK.md 절차 확인

---

## 🔄 정기 점검 및 갱신

### 월간 정책 검토
- **첫째 주**: 거버넌스 정책 유효성 검토
- **둘째 주**: CI/CD 파이프라인 성능 분석
- **셋째 주**: 보안 정책 및 접근 권한 점검
- **넷째 주**: 문서 체계 및 아카이브 정리

### 정책 변경 프로세스
1. **변경 제안**: GitHub Issue로 RFC 생성
2. **검토 기간**: 최소 1주일 커뮤니티 피드백
3. **승인 투표**: 핵심 담당자 과반 동의
4. **적용 및 배포**: GOVERNANCE.md 업데이트
5. **전파**: README 배지 및 알림

---

**✅ 거버넌스 정책 확정 완료** - 조직 운영 체계 정립

*이 문서는 프로젝트의 공식 거버넌스 정책이며, 변경 시 상기 절차를 따라야 합니다.*