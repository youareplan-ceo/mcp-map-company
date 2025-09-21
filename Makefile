SHELL := /bin/zsh
ctl := ./scripts/stockctl.sh
상태: ; $(ctl) status
예열: ; $(ctl) prewarm
재시작: ; $(ctl) restart
메트릭: ; $(ctl) metrics
공격적: ; $(ctl) tune:aggressive
보수적: ; $(ctl) tune:conservative
로그정리: ; $(ctl) log:clear
load-test: ; @echo "부하 테스트를 위해 Locust 설치가 필요합니다:"; echo "pip3 install locust 또는 pip3 install -r requirements-dev.txt"; echo "설치 후 다음 명령어로 실행:"; echo "python3 scripts/load_test.py --users 100 --time 5m"
deploy-status: ; ./scripts/deploy_status.sh
deploy-status-k8s: ; ./scripts/deploy_status.sh --detailed
deploy-status-full: ; ./scripts/deploy_status.sh --detailed --nginx --ssl --logs

# 🔐 백업 관리 명령어

# 백업 검증 실행
verify-backups:
	@echo "🔍 백업 무결성 검증 시작..."
	./scripts/backup_verifier.sh --verbose

# 오래된 백업 자동 정리
clean-backups:
	@echo "🗑️ 오래된 백업 자동 정리..."
	./scripts/cleanup_old_backups.sh --yes

# 백업 검증 + 정리 통합 실행
backup-maintenance:
	@echo "♻️ 백업 검증 + 정리 통합 실행..."
	./scripts/backup_verifier.sh --verbose
	./scripts/cleanup_old_backups.sh --yes

# 🔄 일일 운영 자동화 명령어

# 일일 운영 작업 실행 (보안 로그 회전 + 백업 검증 + 정리)
daily-ops:
	@echo "🔄 일일 운영 자동화 작업 실행..."
	./scripts/daily_ops.sh --verbose

# 일일 운영 시뮬레이션 (변경 사항 없음)
daily-ops-dry:
	@echo "🔄 일일 운영 자동화 시뮬레이션..."
	./scripts/daily_ops.sh --dry-run --verbose

# 일일 운영 JSON 출력
daily-ops-json:
	@echo "🔄 일일 운영 작업 실행 (JSON 출력)..."
	./scripts/daily_ops.sh --json

# 🧹 CI 클린업 자동화 명령어

# CI 클린업 실행 (로그 압축, 오래된 리포트 삭제, 백업 검증)
ci-clean:
	@echo "🧹 CI 클린업 자동화 작업 실행..."
	./scripts/ci_cleanup.sh --verbose

# CI 클린업 시뮬레이션 (변경 사항 없음)
ci-clean-dry:
	@echo "🧹 CI 클린업 시뮬레이션 실행..."
	./scripts/ci_cleanup.sh --dry-run --verbose

# CI 클린업 JSON 출력
ci-clean-json:
	@echo "🧹 CI 클린업 작업 실행 (JSON 출력)..."
	./scripts/ci_cleanup.sh --json

# 📊 분기별 운영 리포트 자동화 명령어

# 분기별 운영 리포트 생성 (기본 Markdown)
quarterly-report:
	@echo "📊 분기별 운영 리포트 생성 중..."
	./scripts/quarterly_ops_report.sh --verbose

# 분기별 운영 리포트 JSON 출력
quarterly-report-json:
	@echo "📊 분기별 운영 리포트 생성 (JSON 출력)..."
	./scripts/quarterly_ops_report.sh --json --verbose

# 분기별 운영 리포트 Markdown 출력
quarterly-report-md:
	@echo "📊 분기별 운영 리포트 생성 (Markdown 출력)..."
	./scripts/quarterly_ops_report.sh --md --verbose

# 특정 연도/분기 리포트 생성 (예: make quarterly-report-specific YEAR=2024 QUARTER=3)
quarterly-report-specific:
	@echo "📊 특정 분기 운영 리포트 생성 ($(YEAR)년 $(QUARTER)분기)..."
	./scripts/quarterly_ops_report.sh --year $(YEAR) --quarter $(QUARTER) --verbose

# 분기별 운영 리포트 시뮬레이션 (변경 사항 없음)
quarterly-report-dry:
	@echo "📊 분기별 운영 리포트 시뮬레이션..."
	./scripts/quarterly_ops_report.sh --dry-run --verbose

# 분기별 운영 리포트 테스트 실행
quarterly-report-test:
	@echo "🧪 분기별 운영 리포트 테스트 실행..."
	python3 -m pytest tests/test_quarterly_ops_report.py -v
