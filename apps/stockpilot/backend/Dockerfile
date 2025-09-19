# StockPilot 멀티 스테이지 Docker 빌드
# WebSocket 서버 (8765), Auth API (8002), Dashboard API (8003) 지원

FROM python:3.11-slim as base

# 시스템 패키지 업데이트 및 필수 도구 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# Python 의존성 파일 복사
COPY requirements.txt .

# Python 패키지 설치
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 소스 코드 복사
COPY . .

# 로그 및 데이터 디렉토리 생성
RUN mkdir -p logs data

# WebSocket 서버 스테이지
FROM base as websocket
EXPOSE 8765
CMD ["python", "websocket_server.py"]

# Auth API 서버 스테이지
FROM base as auth
EXPOSE 8002
CMD ["python", "auth_api.py"]

# Dashboard API 서버 스테이지
FROM base as dashboard
EXPOSE 8003
CMD ["python", "dashboard_api.py"]

# 헬스 모니터 스테이지
FROM base as health-monitor
CMD ["python", "health_monitor_daemon.py"]

# 비용 대시보드 API 스테이지
FROM base as cost-dashboard
EXPOSE 8004
CMD ["python", "cost_dashboard_api.py"]

# 프로덕션용 통합 스테이지 (모든 서비스 포함)
FROM base as production
EXPOSE 8765 8002 8003 8004

# supervisor 설치
RUN pip install supervisor

# 헬스체크 스크립트 추가
RUN cat > /app/healthcheck.py << 'EOF'
#!/usr/bin/env python3
"""
멀티 서비스 헬스체크 스크립트
"""
import sys
import asyncio
import aiohttp
import websockets

async def check_websocket():
    """WebSocket 서버 헬스체크"""
    try:
        uri = "ws://localhost:8765"
        async with websockets.connect(uri) as websocket:
            await websocket.ping()
            return True
    except:
        return False

async def check_http_service(port, path="/health"):
    """HTTP 서비스 헬스체크"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://localhost:{port}{path}") as response:
                return response.status == 200
    except:
        return False

async def main():
    """모든 서비스 헬스체크 실행"""
    services = [
        ("WebSocket", check_websocket()),
        ("Auth API", check_http_service(8002)),
        ("Dashboard API", check_http_service(8003)),
        ("Cost Dashboard API", check_http_service(8004))
    ]
    
    results = await asyncio.gather(*[service[1] for service in services], return_exceptions=True)
    
    all_healthy = True
    for i, (name, _) in enumerate(services):
        healthy = results[i] if not isinstance(results[i], Exception) else False
        print(f"{name}: {'✅ Healthy' if healthy else '❌ Unhealthy'}")
        if not healthy:
            all_healthy = False
    
    sys.exit(0 if all_healthy else 1)

if __name__ == "__main__":
    asyncio.run(main())
EOF

RUN chmod +x /app/healthcheck.py

# supervisor 설정 파일 생성
RUN cat > /app/supervisord.conf << 'EOF'
[supervisord]
nodaemon=true
user=root
logfile=/app/logs/supervisord.log
pidfile=/var/run/supervisord.pid

[program:websocket]
command=python websocket_server.py
directory=/app
autorestart=true
stderr_logfile=/app/logs/websocket.err.log
stdout_logfile=/app/logs/websocket.out.log

[program:auth-api]
command=python auth_api.py
directory=/app
autorestart=true
stderr_logfile=/app/logs/auth.err.log
stdout_logfile=/app/logs/auth.out.log

[program:dashboard-api]
command=python dashboard_api.py
directory=/app
autorestart=true
stderr_logfile=/app/logs/dashboard.err.log
stdout_logfile=/app/logs/dashboard.out.log

[program:cost-dashboard-api]
command=python cost_dashboard_api.py
directory=/app
autorestart=true
stderr_logfile=/app/logs/cost_dashboard.err.log
stdout_logfile=/app/logs/cost_dashboard.out.log
EOF

CMD ["supervisord", "-c", "/app/supervisord.conf"]

# 개발용 스테이지
FROM base as development
ENV ENVIRONMENT=development
CMD ["python", "websocket_server.py"]