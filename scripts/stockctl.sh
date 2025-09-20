#!/bin/zsh
set -euo pipefail
ROOT="$HOME/Desktop/mcp-map-company"
LOG="$ROOT/scripts/stock_api.log"
PL_MAIN="$HOME/Library/LaunchAgents/com.youareplan.stockapi.plist"
PL_WARM="$HOME/Library/LaunchAgents/com.youareplan.stockapi.prewarm.plist"
dry=""; [[ "${1:-}" == "--dry-run" ]] && { dry=echo; shift; }
cmd="${1:-}"; shift || true
sx(){ [[ -n "$dry" ]] && echo "[DRY] $*" || eval "$*"; }
case "$cmd" in
  status)  sx "launchctl list | grep youareplan.stockapi || true"; sx "tail -n 40 \"$LOG\" || true" ;;
  start)   sx "launchctl load -w \"$PL_MAIN\""; sx "launchctl load -w \"$PL_WARM\"" ;;
  stop)    sx "launchctl unload \"$PL_WARM\" 2>/dev/null || true"; sx "launchctl unload \"$PL_MAIN\" 2>/dev/null || true" ;;
  restart) "$0" ${dry:+--dry-run} stop || true; "$0" ${dry:+--dry-run} start ;;
  prewarm) sx "\"$ROOT/scripts/prewarm.sh\"" ;;
  metrics) sx "curl -sS http://127.0.0.1:8099/metrics | jq" ;;
  tune:aggressive)
    for k v in SP_RSI_OVERBOUGHT 70 SP_RSI_OVERSOLD 35 SP_GAP_BREAKOUT_PCT 0.02 SP_GAP_BREAKDOWN_PCT 0.02 SP_VOLUME_SURGE_MULT 1.5 SP_SCORE_BUY_THRESHOLD 1.5 SP_SCORE_SELL_THRESHOLD -1.5; do
      sx "sed -i '' 's/^$k=.*/$k=$v/' \"$ROOT/.env\""
    done; sx "set -a; source \"$ROOT/.env\"; set +a"; "$0" ${dry:+--dry-run} restart ;;
  tune:conservative)
    for k v in SP_RSI_OVERBOUGHT 75 SP_RSI_OVERSOLD 25 SP_GAP_BREAKOUT_PCT 0.04 SP_GAP_BREAKDOWN_PCT 0.04 SP_VOLUME_SURGE_MULT 2.2 SP_SCORE_BUY_THRESHOLD 2.5 SP_SCORE_SELL_THRESHOLD -2.5; do
      sx "sed -i '' 's/^$k=.*/$k=$v/' \"$ROOT/.env\""
    done; sx "set -a; source \"$ROOT/.env\"; set +a"; "$0" ${dry:+--dry-run} restart ;;
  log:clear) sx ": > \"$LOG\"" ;;
  *) echo "사용법: $0 [--dry-run] {status|start|stop|restart|prewarm|metrics|tune:aggressive|tune:conservative|log:clear}" >&2; exit 2 ;;
esac
