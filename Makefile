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

# 🧪 플래키 테스트 관리 대시보드 명령어

# 플래키 테스트 통계 조회
flaky-stats:
	@echo "📊 플래키 테스트 통계 조회"
	@curl -s "http://localhost:8088/api/v1/flaky/stats?days=30" \
		-H "Content-Type: application/json" \
		| python3 -m json.tool || echo "⚠️ API 서버가 실행 중인지 확인하세요"

# 격리된 테스트 목록 조회
flaky-isolated:
	@echo "🔒 격리된 플래키 테스트 목록 조회"
	@curl -s "http://localhost:8088/api/v1/flaky/isolated?limit=20" \
		-H "Content-Type: application/json" \
		| python3 -m json.tool || echo "⚠️ API 서버가 실행 중인지 확인하세요"

# 플래키 테스트 재시도 (OPERATOR 권한 필요)
flaky-retry:
	@echo "🔄 플래키 테스트 재시도 (예시: test_flaky_login)"
	@if [ -z "$(TEST_NAME)" ]; then \
		echo "❌ 사용법: make flaky-retry TEST_NAME=test_name [RETRY_COUNT=3] [PRIORITY=normal]"; \
		echo "   예시: make flaky-retry TEST_NAME=test_flaky_login RETRY_COUNT=3 PRIORITY=high"; \
	else \
		curl -s -X POST "http://localhost:8088/api/v1/flaky/retry" \
			-H "Content-Type: application/json" \
			-H "X-User-Role: OPERATOR" \
			-d '{"test_names": ["$(TEST_NAME)"], "retry_count": $(or $(RETRY_COUNT),3), "priority": "$(or $(PRIORITY),normal)", "notes": "Makefile을 통한 재시도"}' \
			| python3 -m json.tool || echo "⚠️ API 서버가 실행 중인지 확인하세요"; \
	fi

# 플래키 테스트 격리 해제 (ADMIN 권한 필요)
flaky-unquarantine:
	@echo "🔓 플래키 테스트 격리 해제"
	@if [ -z "$(TEST_NAME)" ]; then \
		echo "❌ 사용법: make flaky-unquarantine TEST_NAME=test_name"; \
		echo "   예시: make flaky-unquarantine TEST_NAME=test_flaky_login"; \
	else \
		curl -s -X DELETE "http://localhost:8088/api/v1/flaky/$(TEST_NAME)" \
			-H "X-User-Role: ADMIN" \
			| python3 -m json.tool || echo "⚠️ API 서버가 실행 중인지 확인하세요"; \
	fi

# 플래키 테스트 대시보드 API 테스트
test-flaky-dashboard:
	@echo "🧪 플래키 테스트 대시보드 API 테스트"
	@python3 -m pytest tests/test_flaky_dashboard_api.py -v --tb=short

# 플래키 테스트 권한 시스템 테스트
test-flaky-auth:
	@echo "🔐 플래키 테스트 권한 시스템 테스트"
	@python3 -m pytest tests/test_flaky_dashboard_api.py::TestUserRoleAuthentication -v

# 플래키 테스트 API 엔드포인트 테스트
test-flaky-endpoints:
	@echo "🚀 플래키 테스트 API 엔드포인트 테스트"
	@python3 -m pytest tests/test_flaky_dashboard_api.py::TestFlakyRetryEndpoint -v
	@python3 -m pytest tests/test_flaky_dashboard_api.py::TestFlakyStatsEndpoint -v
	@python3 -m pytest tests/test_flaky_dashboard_api.py::TestIsolatedTestsEndpoint -v
	@python3 -m pytest tests/test_flaky_dashboard_api.py::TestDeleteFlakyTestEndpoint -v

# 플래키 테스트 통합 워크플로우 테스트
test-flaky-workflow:
	@echo "🔄 플래키 테스트 통합 워크플로우 테스트"
	@python3 -m pytest tests/test_flaky_dashboard_api.py::TestEndToEndWorkflow -v

# 플래키 테스트 데이터 정리
flaky-clean:
	@echo "🧹 플래키 테스트 데이터 정리"
	@if [ -d "data/flaky_tests" ]; then \
		echo "🗑️ 테스트 히스토리 백업 생성..."; \
		cp -r data/flaky_tests data/flaky_tests_backup_$(shell date +%Y%m%d_%H%M%S) 2>/dev/null || true; \
		echo "🧹 30일 이상 된 히스토리 정리..."; \
		curl -s -X DELETE "http://localhost:8088/api/v1/flaky-tests/test-history?older_than_days=30" \
			| python3 -m json.tool || echo "⚠️ API 서버가 실행 중인지 확인하세요"; \
	else \
		echo "📁 플래키 테스트 데이터 디렉토리가 없습니다."; \
	fi

# 플래키 테스트 설정 확인
flaky-config:
	@echo "⚙️ 플래키 테스트 설정 확인"
	@if [ -f "data/flaky_tests/config.json" ]; then \
		echo "📄 현재 설정:"; \
		cat data/flaky_tests/config.json | python3 -m json.tool; \
	else \
		echo "❌ 설정 파일이 없습니다. 기본 설정 생성 중..."; \
		mkdir -p data/flaky_tests; \
		echo '{"min_runs": 5, "failure_threshold": 0.3, "auto_quarantine": true, "auto_quarantine_threshold": 0.5, "quarantine_duration_days": 7, "retention_days": 30}' \
			| python3 -m json.tool > data/flaky_tests/config.json; \
		echo "✅ 기본 설정 파일이 생성되었습니다."; \
	fi

# 플래키 테스트 시스템 헬스체크
flaky-health-check:
	@echo "🏥 플래키 테스트 시스템 헬스체크"
	@echo "1️⃣ API 엔드포인트 확인..."
	@curl -s "http://localhost:8088/api/v1/flaky/stats" > /dev/null && echo "✅ 통계 API 정상" || echo "❌ 통계 API 오류"
	@curl -s "http://localhost:8088/api/v1/flaky/isolated" > /dev/null && echo "✅ 격리 목록 API 정상" || echo "❌ 격리 목록 API 오류"
	@echo "2️⃣ 데이터 파일 확인..."
	@test -f data/flaky_tests/config.json && echo "✅ 설정 파일 존재" || echo "❌ 설정 파일 없음"
	@test -f mcp/flaky_tests_api.py && echo "✅ API 모듈 존재" || echo "❌ API 모듈 없음"
	@echo "3️⃣ 테스트 스위트 확인..."
	@test -f tests/test_flaky_dashboard_api.py && echo "✅ 대시보드 테스트 존재" || echo "❌ 대시보드 테스트 없음"
	@echo "4️⃣ 웹 대시보드 확인..."
	@test -f web/admin_dashboard.html && echo "✅ 관리자 대시보드 존재" || echo "❌ 관리자 대시보드 없음"
	@echo "🏥 헬스체크 완료"

# 플래키 테스트 데모 실행
flaky-demo:
	@echo "🎭 플래키 테스트 관리 시스템 데모 실행"
	@echo "1️⃣ 시스템 헬스체크..."
	@make flaky-health-check
	@echo "2️⃣ 설정 확인..."
	@make flaky-config
	@echo "3️⃣ 통계 조회..."
	@make flaky-stats
	@echo "4️⃣ 격리된 테스트 조회..."
	@make flaky-isolated
	@echo "5️⃣ 핵심 기능 테스트..."
	@make test-flaky-auth
	@echo "🎭 데모 완료! 전체 시스템 테스트를 위해서는 'make test-flaky-dashboard' 명령을 사용하세요."
	@echo "💡 사용 팁:"
	@echo "   - 테스트 재시도: make flaky-retry TEST_NAME=test_name"
	@echo "   - 격리 해제: make flaky-unquarantine TEST_NAME=test_name"
	@echo "   - 웹 대시보드: http://localhost:8088/web/admin_dashboard.html"

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

# .PHONY 선언 (플래키 테스트 관리 대시보드 관련)
.PHONY: flaky-stats flaky-isolated flaky-retry flaky-unquarantine flaky-clean flaky-config
.PHONY: test-flaky-dashboard test-flaky-auth test-flaky-endpoints test-flaky-workflow
.PHONY: flaky-health-check flaky-demo

# 🧪 CI 안정성 시뮬레이션 시스템 명령어

# CI 안정성 시뮬레이션 실행 (기본 설정: 실패율 15%, 플래키율 5%, 100회 실행)
ci-stability-sim:
	@echo "🧪 CI 안정성 시뮬레이션 실행 (기본 설정)"
	@chmod +x scripts/ci_stability_sim.sh
	@./scripts/ci_stability_sim.sh --verbose

# CI 안정성 시뮬레이션 (커스텀 매개변수)
ci-stability-sim-custom:
	@echo "🧪 CI 안정성 시뮬레이션 (커스텀 매개변수)"
	@if [ -z "$(FAIL_RATE)" ] || [ -z "$(FLAKY_RATE)" ] || [ -z "$(RUNS)" ]; then \
		echo "❌ 사용법: make ci-stability-sim-custom FAIL_RATE=15 FLAKY_RATE=5 RUNS=100"; \
		echo "   예시: make ci-stability-sim-custom FAIL_RATE=20 FLAKY_RATE=8 RUNS=200"; \
	else \
		chmod +x scripts/ci_stability_sim.sh; \
		./scripts/ci_stability_sim.sh --fail-rate $(FAIL_RATE) --flaky-rate $(FLAKY_RATE) --runs $(RUNS) --verbose; \
	fi

# CI 안정성 시뮬레이션 (JSON 출력)
ci-stability-sim-json:
	@echo "🧪 CI 안정성 시뮬레이션 (JSON 출력)"
	@chmod +x scripts/ci_stability_sim.sh
	@./scripts/ci_stability_sim.sh --output-format json --output-file ci_stability_results.json --verbose

# CI 안정성 시뮬레이션 (Markdown 출력)
ci-stability-sim-md:
	@echo "🧪 CI 안정성 시뮬레이션 (Markdown 출력)"
	@chmod +x scripts/ci_stability_sim.sh
	@./scripts/ci_stability_sim.sh --output-format markdown --output-file ci_stability_report.md --verbose

# 런북 시스템 검증 실행
runbook-validate:
	@echo "📚 런북 시스템 검증 실행"
	@chmod +x scripts/runbook_validator.sh
	@./scripts/runbook_validator.sh --verbose

# 런북 시스템 검증 (JSON 출력)
runbook-validate-json:
	@echo "📚 런북 시스템 검증 (JSON 출력)"
	@chmod +x scripts/runbook_validator.sh
	@./scripts/runbook_validator.sh --output-format json --output-file runbook_validation_results.json --verbose

# CI 안정성 + 런북 검증 통합 실행
ci-stability-full:
	@echo "🔄 CI 안정성 시뮬레이션 + 런북 검증 통합 실행"
	@make ci-stability-sim-json
	@make runbook-validate-json
	@echo "✅ 통합 실행 완료. 결과 파일: ci_stability_results.json, runbook_validation_results.json"

# CI 안정성 시뮬레이션 테스트 실행
test-ci-stability:
	@echo "🧪 CI 안정성 시뮬레이션 테스트 실행"
	@python3 -m pytest tests/test_ci_stability_and_runbook.py::TestCIStabilitySimulation -v

# 런북 검증 시스템 테스트 실행
test-runbook-validation:
	@echo "📚 런북 검증 시스템 테스트 실행"
	@python3 -m pytest tests/test_ci_stability_and_runbook.py::TestRunbookValidator -v

# CI 안정성 시뮬레이션 전체 테스트 실행
test-ci-stability-full:
	@echo "🧪 CI 안정성 시뮬레이션 전체 테스트 스위트 실행"
	@python3 -m pytest tests/test_ci_stability_and_runbook.py -v

# CI 안정성 시뮬레이션 테스트 (커버리지 포함)
test-ci-stability-coverage:
	@echo "🧪 CI 안정성 시뮬레이션 테스트 (커버리지 포함)"
	@python3 -m pytest tests/test_ci_stability_and_runbook.py --cov=scripts --cov-report=html --cov-report=term

# 플래키 테스트 영향도 분석 (다양한 플래키율로 시뮬레이션)
ci-flaky-impact-analysis:
	@echo "📊 플래키 테스트 영향도 분석 실행"
	@mkdir -p analysis_results
	@for rate in 5 10 15 20 25; do \
		echo "🔄 플래키율 $$rate% 시뮬레이션 실행..."; \
		chmod +x scripts/ci_stability_sim.sh; \
		./scripts/ci_stability_sim.sh --flaky-rate $$rate --runs 200 \
			--output-format json --output-file "analysis_results/flaky_$$rate.json" --seed 12345; \
	done
	@echo "✅ 플래키 테스트 영향도 분석 완료. 결과: analysis_results/flaky_*.json"

# CI 실패율 영향도 분석 (다양한 실패율로 시뮬레이션)
ci-failure-impact-analysis:
	@echo "📊 CI 실패율 영향도 분석 실행"
	@mkdir -p analysis_results
	@for rate in 5 10 15 20 25 30; do \
		echo "🔄 실패율 $$rate% 시뮬레이션 실행..."; \
		chmod +x scripts/ci_stability_sim.sh; \
		./scripts/ci_stability_sim.sh --fail-rate $$rate --runs 200 \
			--output-format json --output-file "analysis_results/failure_$$rate.json" --seed 12345; \
	done
	@echo "✅ CI 실패율 영향도 분석 완료. 결과: analysis_results/failure_*.json"

# CI 안정성 시뮬레이션 시스템 헬스체크
ci-stability-health:
	@echo "🏥 CI 안정성 시뮬레이션 시스템 헬스체크"
	@echo "1️⃣ 스크립트 파일 존재 확인..."
	@test -f scripts/ci_stability_sim.sh && echo "✅ CI 안정성 시뮬레이션 스크립트 존재" || echo "❌ CI 안정성 시뮬레이션 스크립트 없음"
	@test -f scripts/runbook_validator.sh && echo "✅ 런북 검증 스크립트 존재" || echo "❌ 런북 검증 스크립트 없음"
	@echo "2️⃣ 테스트 스위트 확인..."
	@test -f tests/test_ci_stability_and_runbook.py && echo "✅ 테스트 스위트 존재" || echo "❌ 테스트 스위트 없음"
	@echo "3️⃣ 스크립트 실행 권한 확인..."
	@test -x scripts/ci_stability_sim.sh && echo "✅ CI 시뮬레이션 스크립트 실행 가능" || (chmod +x scripts/ci_stability_sim.sh && echo "🔧 실행 권한 부여")
	@test -x scripts/runbook_validator.sh && echo "✅ 런북 검증 스크립트 실행 가능" || (chmod +x scripts/runbook_validator.sh && echo "🔧 실행 권한 부여")
	@echo "4️⃣ 웹 대시보드 통합 확인..."
	@test -f web/admin_dashboard.html && echo "✅ 관리자 대시보드 존재 (CI 시뮬레이션 패널 포함)" || echo "❌ 관리자 대시보드 없음"
	@echo "5️⃣ 출력 디렉토리 확인..."
	@test -d analysis_results || (mkdir -p analysis_results && echo "📁 분석 결과 디렉토리 생성")
	@echo "🏥 CI 안정성 시뮬레이션 시스템 헬스체크 완료"

# CI 안정성 시뮬레이션 데모 실행
ci-stability-demo:
	@echo "🎭 CI 안정성 시뮬레이션 시스템 데모 실행"
	@echo "1️⃣ 시스템 헬스체크..."
	@make ci-stability-health
	@echo "2️⃣ 기본 시뮬레이션 실행..."
	@make ci-stability-sim
	@echo "3️⃣ 런북 시스템 검증..."
	@make runbook-validate
	@echo "4️⃣ JSON 출력 시뮬레이션..."
	@make ci-stability-sim-json
	@echo "5️⃣ 핵심 기능 테스트..."
	@make test-ci-stability
	@echo "🎭 데모 완료! 전체 시스템 테스트를 위해서는 'make test-ci-stability-full' 명령을 사용하세요."
	@echo "💡 사용 팁:"
	@echo "   - 커스텀 매개변수: make ci-stability-sim-custom FAIL_RATE=20 FLAKY_RATE=8 RUNS=200"
	@echo "   - 플래키 영향도 분석: make ci-flaky-impact-analysis"
	@echo "   - 실패율 영향도 분석: make ci-failure-impact-analysis"
	@echo "   - 웹 대시보드: http://localhost:8088/web/admin_dashboard.html"

# 결과 파일 정리
ci-stability-clean:
	@echo "🧹 CI 안정성 시뮬레이션 결과 파일 정리"
	@if [ -d analysis_results ]; then \
		echo "🗑️ 분석 결과 백업 생성..."; \
		mv analysis_results analysis_results_backup_$(shell date +%Y%m%d_%H%M%S) 2>/dev/null || true; \
		echo "✅ 백업 생성 완료"; \
	fi
	@rm -f ci_stability_results.json runbook_validation_results.json ci_stability_report.md
	@mkdir -p analysis_results
	@echo "🧹 정리 완료"

# CI 안정성 성과 벤치마크 (대용량 시뮬레이션)
ci-stability-benchmark:
	@echo "📊 CI 안정성 시뮬레이션 성능 벤치마크"
	@echo "🔄 소규모 (100회)..."
	@time make ci-stability-sim-custom FAIL_RATE=15 FLAKY_RATE=5 RUNS=100
	@echo "🔄 중규모 (500회)..."
	@time make ci-stability-sim-custom FAIL_RATE=15 FLAKY_RATE=5 RUNS=500
	@echo "🔄 대규모 (1000회)..."
	@time make ci-stability-sim-custom FAIL_RATE=15 FLAKY_RATE=5 RUNS=1000
	@echo "📊 벤치마크 완료"

# .PHONY 선언 (CI 안정성 시뮬레이션 관련)
.PHONY: ci-stability-sim ci-stability-sim-custom ci-stability-sim-json ci-stability-sim-md
.PHONY: runbook-validate runbook-validate-json ci-stability-full
.PHONY: test-ci-stability test-runbook-validation test-ci-stability-full test-ci-stability-coverage
.PHONY: ci-flaky-impact-analysis ci-failure-impact-analysis ci-stability-health ci-stability-demo
.PHONY: ci-stability-clean ci-stability-benchmark

# .PHONY 선언 (이상탐지 고도화 관련)
.PHONY: anomaly-rca-sample anomaly-decompose-sample anomaly-policies-list
.PHONY: anomaly-backtest anomaly-backtest-tune test-anomaly-system test-anomaly-rca
.PHONY: test-anomaly-policy test-anomaly-performance test-anomaly-dashboard
.PHONY: anomaly-health-check anomaly-demo


# =====================================
# 🧩 인시던트 센터 전용 명령어
# =====================================

incident-smoke-api: ## 인시던트 센터 API 스모크 테스트 실행
	@echo "🚨 인시던트 센터 API 스모크 테스트 실행 중..."
	@echo "💡 테스트 대상: /health, /summary, /list (CSV)"
	@./scripts/incident_post_release_smoke.sh || { \
		echo "❌ API 스모크 테스트 실패"; \
		echo "💡 문제 해결:"; \
		echo "   1. API 서버 상태: make incident-health"; \
		echo "   2. 상세 로그: ./scripts/incident_post_release_smoke.sh --verbose"; \
		echo "   3. 롤백 검토: make incident-rollback-dry"; \
		exit 1; \
	}
	@echo "✅ API 스모크 테스트 통과"

incident-smoke-ui: ## 인시던트 센터 대시보드 UI 스모크 테스트 실행
	@echo "🌐 인시던트 센터 대시보드 UI 스모크 테스트 실행 중..."
	@echo "💡 테스트 대상: 파일 접근성, 카드/차트 DOM, 한국어 지원"
	@./scripts/dashboard_smoke_incidents.sh --optional || { \
		echo "❌ UI 스모크 테스트 실패"; \
		echo "💡 문제 해결:"; \
		echo "   1. 파일 상태: ls -la web/admin_dashboard.html"; \
		echo "   2. 상세 로그: ./scripts/dashboard_smoke_incidents.sh --verbose"; \
		echo "   3. 원본 복원: git checkout web/admin_dashboard.html"; \
		exit 1; \
	}
	@echo "✅ UI 스모크 테스트 통과"

incident-smoke-all: ## 인시던트 센터 전체 스모크 테스트 (API + UI) 실행
	@echo "🔥 인시던트 센터 전체 스모크 테스트 실행 중..."
	@echo "📋 실행 순서: API → UI → 요약 출력"
	@echo ""
	@echo "1️⃣  API 스모크 테스트..."
	@make incident-smoke-api
	@echo ""
	@echo "2️⃣  UI 스모크 테스트..."
	@make incident-smoke-ui
	@echo ""
	@echo "🎉 전체 스모크 테스트 완료\!"
	@echo "📊 테스트 요약:"
	@echo "   ✅ API 엔드포인트 정상 (health, summary, list/CSV)"
	@echo "   ✅ UI 구조 정상 (5개 카드, 2개 차트, 한국어 지원)"
	@echo "   ✅ 인시던트 센터 v1.0.0 릴리스 품질 검증 완료"

incident-smoke-all-dry-run: ## 인시던트 센터 스모크 테스트 드라이런 (실행 없이 확인만)
	@echo "🔄 인시던트 센터 스모크 테스트 드라이런"
	@echo "📋 실행 예정 명령어:"
	@echo "   1. API 스모크: ./scripts/incident_post_release_smoke.sh"
	@echo "   2. UI 스모크: ./scripts/dashboard_smoke_incidents.sh"
	@echo "📊 스크립트 상태:"
	@ls -la scripts/incident_post_release_smoke.sh scripts/dashboard_smoke_incidents.sh || echo "   ⚠️ 일부 스크립트가 없습니다"
	@echo "✅ 드라이런 완료 - 실제 실행은 'make incident-smoke-all'"

incident-rollback-dry: ## 인시던트 센터 v1.0.0 롤백 시뮬레이션 (실제 checkout 없이 안내만)
	@echo "🔄 인시던트 센터 v1.0.0 롤백 시뮬레이션"
	@echo ""
	@echo "📋 현재 상태:"
	@echo "   - 현재 브랜치: $(shell git branch --show-current)"
	@echo "   - 최근 커밋: $(shell git log --oneline -1)"
	@echo ""
	@echo "🏷️  롤백 가능한 태그:"
	@git tag -l | grep incident | head -3 | xargs -I {} echo "   📌 {}"
	@echo ""
	@echo "⚠️  롤백 시뮬레이션 - 실제 변경 없음"
	@echo "💡 실제 롤백 명령어 (신중히 실행):"
	@echo "   1. 백업: tar -czf backup_$(shell date +%Y%m%d_%H%M%S).tar.gz ."
	@echo "   2. 롤백: git checkout incident-center-v1.0.0"
	@echo "   3. 검증: make incident-smoke-all"

# 🔍 로컬 점검 타깃 (운영 고도화)

incident-audit: ## 인시던트 센터 로컬 점검 (파일 무결성, 권한, 크기)
	@echo "🔍 인시던트 센터 로컬 점검 시작..."
	@echo "📋 스크립트 파일 점검:"
	@ls -la scripts/incident_* scripts/dashboard_smoke_incidents.sh 2>/dev/null || echo "❌ 스크립트 파일 누락"
	@echo "📋 Makefile 타깃 점검:"
	@grep -c "incident-" Makefile || echo "❌ Makefile 타깃 문제"
	@echo "📋 리포트 파일 점검:"
	@find reports/incident-center -name "*.md" | wc -l | awk '{print "✅ 리포트 파일: " $$1 "개"}'
	@echo "📋 CI 워크플로 점검:"
	@ls -la .github/workflows/incident_smoke.yml .github/workflows/weekly_monitor.yml 2>/dev/null || echo "❌ CI 워크플로 누락"
	@echo "✅ 로컬 점검 완료"

incident-links: ## 인시던트 센터 링크 상태 점검 (로컬 파일 기반)
	@echo "🔗 인시던트 센터 링크 상태 점검..."
	@echo "📋 핵심 문서 존재 확인:"
	@ls -1 reports/incident-center/INDEX.md reports/incident-center/ENV_REQUIRED.md 2>/dev/null | wc -l | awk '{print "✅ 핵심 문서: " $$1 "/2개"}'
	@echo "📋 v1.0.1-pre 리포트 확인:"
	@ls -1 reports/incident-center/v1.0.1-pre/COMPLETE_STATUS.md reports/incident-center/v1.0.1-pre/SUMMARY.md 2>/dev/null | wc -l | awk '{print "✅ v1.0.1-pre 리포트: " $$1 "/2개"}'
	@echo "📋 GitHub Actions 배지 (로컬 확인):"
	@grep -c "badge.svg" README.md 2>/dev/null | awk '{print "✅ 배지 링크: " $$1 "개"}'
	@echo "📋 상대 경로 링크 (reports 내부):"
	@find reports -name "*.md" -exec grep -l "\]\(\./\|\.\./" {} \; 2>/dev/null | wc -l | awk '{print "✅ 상대 경로 문서: " $$1 "개"}'
	@echo "✅ 링크 점검 완료"

# .PHONY 선언 (인시던트 센터 관련)
.PHONY: incident-smoke-api incident-smoke-ui incident-smoke-all incident-smoke-all-dry-run incident-rollback-dry incident-audit incident-links

