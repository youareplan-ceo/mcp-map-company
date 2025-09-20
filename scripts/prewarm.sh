#!/bin/zsh
sleep 3
curl -sS "http://127.0.0.1:8099/api/v1/stock/signals?exchange=NASDAQ&limit=40&batch_size=40" >/dev/null
curl -sS "http://127.0.0.1:8099/api/v1/stock/signals?exchange=KRX&limit=40&batch_size=40" >/dev/null
