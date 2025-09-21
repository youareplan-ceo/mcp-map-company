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

# 🛠️ CI 자동 완화 시스템 명령어

# CI 자동 완화 실행 (드라이런 모드)
ci-autofix-dry:
	@echo "🛠️ CI 자동 완화 시스템 (드라이런 모드)"
	@chmod +x scripts/ci_autoremediate.sh scripts/hooks/*.sh
	@./scripts/ci_autoremediate.sh --dry-run --error-type dependency_install_failed
	@./scripts/ci_autoremediate.sh --dry-run --error-type test_timeout
	@./scripts/ci_autoremediate.sh --dry-run --error-type build_timeout

# CI 자동 완화 실행 (실제 액션)
ci-autofix:
	@echo "🛠️ CI 자동 완화 시스템 (실제 실행)"
	@chmod +x scripts/ci_autoremediate.sh scripts/hooks/*.sh
	@./scripts/ci_autoremediate.sh --error-type dependency_install_failed --max-actions 3
	@./scripts/ci_autoremediate.sh --error-type test_timeout --max-actions 5

# 개별 완화 액션 테스트
ci-test-hooks:
	@echo "🔧 완화 훅 테스트 실행"
	@chmod +x scripts/hooks/*.sh
	@./scripts/hooks/clear_ci_cache.sh --dry-run
	@./scripts/hooks/retry_failed_tests.sh --dry-run --test-framework pytest
	@./scripts/hooks/restart_worker.sh --dry-run --platform github-actions

# CI 캐시 정리
ci-clear-cache:
	@echo "🧹 CI 캐시 정리"
	@./scripts/hooks/clear_ci_cache.sh

# 실패한 테스트 재시도
ci-retry-tests:
	@echo "🔄 실패한 테스트 재시도"
	@./scripts/hooks/retry_failed_tests.sh --test-framework pytest

# 🔍 플래키 테스트 격리 시스템 명령어

# 플래키 테스트 격리 시스템 테스트
test-flaky-isolation:
	@echo "🔍 플래키 테스트 격리 시스템 테스트"
	@python3 -m pytest tests/test_autoremediate_and_flaky.py::TestFlakyTestsAPI -v

# 자동 완화 시스템 전체 테스트
test-autoremediation:
	@echo "🛠️ 자동 완화 시스템 전체 테스트"
	@python3 -m pytest tests/test_autoremediate_and_flaky.py -v --tb=short

# 런북 시스템 테스트
test-runbooks:
	@echo "📚 런북 시스템 테스트"
	@python3 -m pytest tests/test_autoremediate_and_flaky.py::TestRunbookSystem -v

# 웹 대시보드 자동 완화 패널 테스트
test-dashboard-remediation:
	@echo "🖥️ 대시보드 자동 완화 패널 테스트"
	@python3 -m pytest tests/test_autoremediate_and_flaky.py::TestAdminDashboardIntegration -v

# 📈 자동 완화 모니터링 명령어

# 자동 완화 상태 모니터링
monitor-autoremediation:
	@echo "📊 자동 완화 시스템 상태 모니터링"
	@if [ -f scripts/monitor_autoremediation.sh ]; then \
		chmod +x scripts/monitor_autoremediation.sh && \
		./scripts/monitor_autoremediation.sh; \
	else \
		echo "⚠️ 모니터링 스크립트가 없습니다. README.md의 샘플을 참조하여 생성하세요."; \
	fi

# 완화 통계 JSON 출력
autoremediation-stats:
	@echo "📈 자동 완화 시스템 통계 조회"
	@if [ -f logs/remediation_stats.json ]; then \
		echo "📊 최근 완화 통계:"; \
		cat logs/remediation_stats.json | python3 -m json.tool; \
	else \
		echo "📊 통계 파일이 없습니다. 먼저 모니터링을 실행하세요: make monitor-autoremediation"; \
	fi

# 🚀 통합 CI 완화 워크플로

# 전체 CI 자동 완화 시스템 헬스체크
ci-remediation-health:
	@echo "🏥 CI 자동 완화 시스템 헬스체크"
	@echo "1️⃣ 스크립트 파일 존재 확인..."
	@test -f scripts/ci_autoremediate.sh && echo "✅ 메인 스크립트 존재" || echo "❌ 메인 스크립트 없음"
	@test -f scripts/hooks/clear_ci_cache.sh && echo "✅ 캐시 정리 훅 존재" || echo "❌ 캐시 정리 훅 없음"
	@test -f scripts/hooks/retry_failed_tests.sh && echo "✅ 테스트 재시도 훅 존재" || echo "❌ 테스트 재시도 훅 없음"
	@test -f scripts/hooks/restart_worker.sh && echo "✅ 워커 재시작 훅 존재" || echo "❌ 워커 재시작 훅 없음"
	@echo "2️⃣ Python 모듈 존재 확인..."
	@test -f mcp/utils/runbook.py && echo "✅ 런북 시스템 존재" || echo "❌ 런북 시스템 없음"
	@test -f mcp/flaky_tests_api.py && echo "✅ 플래키 테스트 API 존재" || echo "❌ 플래키 테스트 API 없음"
	@echo "3️⃣ 테스트 스위트 존재 확인..."
	@test -f tests/test_autoremediate_and_flaky.py && echo "✅ 통합 테스트 스위트 존재" || echo "❌ 통합 테스트 스위트 없음"
	@echo "4️⃣ 로그 디렉토리 확인..."
	@test -d logs && echo "✅ 로그 디렉토리 존재" || (mkdir -p logs && echo "📁 로그 디렉토리 생성")
	@echo "🏥 헬스체크 완료"

# 빠른 CI 완화 데모 실행
ci-remediation-demo:
	@echo "🎭 CI 자동 완화 시스템 데모 실행"
	@echo "1️⃣ 드라이런 모드로 모든 에러 타입 테스트..."
	@make ci-autofix-dry
	@echo "2️⃣ 개별 훅 테스트..."
	@make ci-test-hooks
	@echo "3️⃣ 런북 시스템 테스트..."
	@make test-runbooks
	@echo "4️⃣ 플래키 테스트 API 테스트..."
	@make test-flaky-isolation
	@echo "🎭 데모 완료! 실제 사용을 위해서는 'make ci-autofix' 명령을 사용하세요."

# 🔎 이상탐지 고도화 명령어

# RCA 원인분석 샘플 실행
anomaly-rca-sample:
	@echo "🔍 RCA 원인분석 샘플 실행"
	@curl -X POST http://localhost:8088/api/v1/anomaly/rca \
		-H "Content-Type: application/json" \
		-d '{"target_metric": "cpu_usage", "time_range": "1h", "correlation_threshold": 0.7}' \
		| python3 -m json.tool

# 계절성 분해 샘플 실행
anomaly-decompose-sample:
	@echo "📈 계절성 분해 분석 샘플 실행"
	@curl "http://localhost:8088/api/v1/anomaly/decompose?metric=memory_usage&period=7d" \
		| python3 -m json.tool

# 이상탐지 정책 목록 조회
anomaly-policies-list:
	@echo "⚙️ 이상탐지 정책 목록 조회"
	@curl http://localhost:8088/api/v1/anomaly/policies | python3 -m json.tool

# 백테스트 실행 (기본 설정)
anomaly-backtest:
	@echo "🧪 이상탐지 백테스트 실행"
	@python3 scripts/anomaly_backtest.py --config configs/backtest_config.yaml --verbose

# 백테스트 파라미터 튜닝
anomaly-backtest-tune:
	@echo "🎯 백테스트 파라미터 튜닝 실행"
	@python3 scripts/anomaly_backtest.py --tune --output results/tuning_results.json --verbose

# 이상탐지 시스템 전체 테스트
test-anomaly-system:
	@echo "🧪 이상탐지 시스템 전체 테스트"
	@python3 -m pytest tests/test_anomaly_rca_and_policy.py -v --tb=short

# RCA 엔진 단위 테스트
test-anomaly-rca:
	@echo "🔍 RCA 엔진 단위 테스트"
	@python3 -m pytest tests/test_anomaly_rca_and_policy.py::TestAnomalyRCACore -v

# 정책 API 테스트
test-anomaly-policy:
	@echo "⚙️ 이상탐지 정책 API 테스트"
	@python3 -m pytest tests/test_anomaly_rca_and_policy.py::TestAnomalyPolicyAPI -v

# 성능 벤치마크 테스트 (대용량 데이터)
test-anomaly-performance:
	@echo "📊 이상탐지 성능 벤치마크 테스트"
	@python3 -m pytest tests/test_anomaly_rca_and_policy.py::TestAnomalyRCAPerformance -v

# 이상탐지 대시보드 통합 테스트
test-anomaly-dashboard:
	@echo "📊 이상탐지 대시보드 통합 테스트"
	@python3 -m pytest tests/test_anomaly_rca_and_policy.py::TestAdminDashboardIntegration -v

# 이상탐지 시스템 헬스체크
anomaly-health-check:
	@echo "🏥 이상탐지 시스템 헬스체크"
	@echo "1️⃣ RCA 엔진 모듈 확인..."
	@test -f mcp/anomaly_rca.py && echo "✅ RCA 엔진 존재" || echo "❌ RCA 엔진 없음"
	@test -f mcp/anomaly_policy_api.py && echo "✅ 정책 API 존재" || echo "❌ 정책 API 없음"
	@echo "2️⃣ 백테스트 스크립트 확인..."
	@test -f scripts/anomaly_backtest.py && echo "✅ 백테스트 스크립트 존재" || echo "❌ 백테스트 스크립트 없음"
	@echo "3️⃣ 테스트 스위트 확인..."
	@test -f tests/test_anomaly_rca_and_policy.py && echo "✅ 테스트 스위트 존재" || echo "❌ 테스트 스위트 없음"
	@echo "4️⃣ 정책 설정 파일 확인..."
	@test -f data/anomaly_policy.yaml && echo "✅ 정책 설정 파일 존재" || echo "📄 정책 설정 파일 생성 필요"
	@echo "5️⃣ 결과 디렉토리 확인..."
	@test -d results && echo "✅ 결과 디렉토리 존재" || (mkdir -p results && echo "📁 결과 디렉토리 생성")
	@echo "🏥 이상탐지 시스템 헬스체크 완료"

# 이상탐지 시스템 데모 실행
anomaly-demo:
	@echo "🎭 이상탐지 고도화 시스템 데모 실행"
	@echo "1️⃣ 시스템 헬스체크..."
	@make anomaly-health-check
	@echo "2️⃣ RCA 원인분석 샘플..."
	@make anomaly-rca-sample
	@echo "3️⃣ 계절성 분해 샘플..."
	@make anomaly-decompose-sample
	@echo "4️⃣ 정책 목록 조회..."
	@make anomaly-policies-list
	@echo "5️⃣ 핵심 기능 테스트..."
	@make test-anomaly-rca
	@echo "🎭 데모 완료! 전체 시스템 테스트를 위해서는 'make test-anomaly-system' 명령을 사용하세요."

# .PHONY 선언 (CI 자동 완화 관련)
.PHONY: ci-autofix-dry ci-autofix ci-test-hooks ci-clear-cache ci-retry-tests
.PHONY: test-flaky-isolation test-autoremediation test-runbooks test-dashboard-remediation
.PHONY: monitor-autoremediation autoremediation-stats ci-remediation-health ci-remediation-demo

# .PHONY 선언 (이상탐지 고도화 관련)
.PHONY: anomaly-rca-sample anomaly-decompose-sample anomaly-policies-list
.PHONY: anomaly-backtest anomaly-backtest-tune test-anomaly-system test-anomaly-rca
.PHONY: test-anomaly-policy test-anomaly-performance test-anomaly-dashboard
.PHONY: anomaly-health-check anomaly-demo
