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
