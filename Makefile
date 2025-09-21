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
