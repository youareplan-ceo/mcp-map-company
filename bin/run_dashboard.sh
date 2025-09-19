#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."          # 레포 루트
source .venv/bin/activate
export PYTHONPATH="$PWD"
exec streamlit run apps/policypilot/app.py
