#!/usr/bin/env bash
set -e
# 경로 자동 추적
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"
# venv 활성화
source .venv/bin/activate
# 로그 폴더
mkdir -p logs
# 인자: 플로우 이름 (예: stocks_intraday / news_daily)
FLOW="$1"
STAMP="$(date +"%Y-%m-%d_%H-%M-%S")"
LOG="logs/${FLOW}_${STAMP}.log"
# 실행
echo "[run_flow] $(date) :: $FLOW" | tee -a "$LOG"
bin/flow "$FLOW" 2>&1 | tee -a "$LOG"
