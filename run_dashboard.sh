#!/bin/bash

echo "🚀 MCP-MAP 대시보드 시작 중..."
echo ""
echo "==================================="
echo "📱 로컬 테스트 서버 시작"
echo "==================================="
echo ""

cd web

# Python 간단 서버 실행 (Mac에 기본 설치됨)
echo "🌐 http://localhost:8080 에서 접속 가능합니다"
echo "🛑 종료하려면 Ctrl+C를 누르세요"
echo ""

python3 -m http.server 8080