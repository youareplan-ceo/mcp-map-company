# 🔧 StockPilot 운영자 매뉴얼

> 시스템 관리자를 위한 종합 운영 가이드

## 📋 목차

- [시스템 아키텍처](#시스템-아키텍처)
- [설치 및 배포](#설치-및-배포)
- [일상 운영](#일상-운영)
- [모니터링 및 알림](#모니터링-및-알림)
- [백업 및 복구](#백업-및-복구)
- [성능 튜닝](#성능-튜닝)
- [보안 관리](#보안-관리)
- [트러블슈팅](#트러블슈팅)
- [장애 대응](#장애-대응)

---

## 🏗️ 시스템 아키텍처

### 전체 구조도

```
┌─────────────────────────────────────────────────────────────────┐
│                        StockPilot 시스템                         │
├─────────────────────────────────────────────────────────────────┤
│  Frontend (React)                                               │
│  ├── 포트: 3000                                                 │
│  ├── 정적 파일 서빙                                              │
│  └── WebSocket 클라이언트                                        │
├─────────────────────────────────────────────────────────────────┤
│  API Gateway / Load Balancer                                   │
│  ├── Nginx (포트: 80, 443)                                      │
│  ├── SSL 터미네이션                                              │
│  └── 요청 라우팅                                                │
├─────────────────────────────────────────────────────────────────┤
│  Backend Services                                              │
│  ├── FastAPI 서버 (포트: 8000)                                  │
│  ├── WebSocket 서버 (포트: 8765)                                │
│  ├── 비용 대시보드 (포트: 8004)                                  │
│  └── 헬스 모니터링 (systemd)                                     │
├─────────────────────────────────────────────────────────────────┤
│  Data Layer                                                    │
│  ├── PostgreSQL (포트: 5432)                                    │
│  ├── Redis (포트: 6379)                                         │
│  └── 파일 스토리지 (/opt/stockpilot/data)                        │
├─────────────────────────────────────────────────────────────────┤
│  External APIs                                                 │
│  ├── OpenAI GPT                                                │
│  ├── Yahoo Finance                                             │
│  ├── Alpha Vantage                                             │
│  ├── Korean Data Sources (DART, KRX)                          │
│  └── News Providers (Reuters, NewsAPI)                        │
└─────────────────────────────────────────────────────────────────┘
```

### 핵심 컴포넌트

#### 1. 웹 서버 (Nginx)
```nginx
# /etc/nginx/sites-available/stockpilot
server {
    listen 80;
    listen [::]:80;
    server_name stockpilot.ai www.stockpilot.ai;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name stockpilot.ai www.stockpilot.ai;
    
    ssl_certificate /etc/letsencrypt/live/stockpilot.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/stockpilot.ai/privkey.pem;
    
    # Frontend
    location / {
        root /opt/stockpilot/frontend/build;
        index index.html;
        try_files $uri $uri/ /index.html;
    }
    
    # API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # WebSocket
    location /ws {
        proxy_pass http://localhost:8765;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

#### 2. 시스템 서비스 구조
```
systemd 서비스:
├── stockpilot-api.service          # FastAPI 메인 서버
├── stockpilot-websocket.service    # WebSocket 서버
├── stockpilot-health.service       # 헬스 모니터링
├── stockpilot-cost-dashboard.service # 비용 대시보드
├── stockpilot-korean-data.service  # KR 데이터 수집
└── stockpilot-failover.service     # 다중 프로바이더 페일오버
```

#### 3. 데이터 플로우
```
데이터 수집 → 처리 → 저장 → API → 프론트엔드
     ↓
외부 API → 페일오버 → 캐싱 → 분석 → WebSocket → 실시간 업데이트
     ↓
모니터링 → 알림 → 로깅 → 백업
```

---

## 🚀 설치 및 배포

### 시스템 요구사항

#### 최소 사양 (개발/테스트)
```
CPU: 2코어 2GHz 이상
RAM: 4GB 이상
디스크: 20GB SSD
네트워크: 10Mbps 이상
OS: Ubuntu 20.04+ 또는 CentOS 8+
```

#### 권장 사양 (프로덕션)
```
CPU: 4코어 3GHz 이상 (ARM64 또는 x86_64)
RAM: 16GB 이상
디스크: 100GB SSD (NVMe 권장)
네트워크: 100Mbps 이상, 낮은 지연시간
OS: Ubuntu 22.04 LTS
백업: 별도 스토리지 200GB+
```

### 자동 설치 스크립트

#### 1. 기본 설치
```bash
#!/bin/bash
# install_stockpilot.sh

set -euo pipefail

echo "🚀 StockPilot 자동 설치 시작"

# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 필수 패키지 설치
sudo apt install -y \
    git curl wget \
    python3 python3-pip python3-venv \
    nodejs npm \
    nginx redis-server postgresql postgresql-contrib \
    certbot python3-certbot-nginx \
    htop iotop netstat-nat \
    docker.io docker-compose

# Python 가상환경 설정
cd /opt
sudo git clone https://github.com/youareplan/stockpilot-ai.git
sudo chown -R $USER:$USER stockpilot-ai
cd stockpilot-ai/backend

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Node.js 의존성 설치
cd ../frontend
npm install
npm run build

# 데이터베이스 설정
sudo -u postgres createdb stockpilot
sudo -u postgres createuser stockpilot --pwprompt

# systemd 서비스 등록
cd ../systemd
sudo cp *.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable stockpilot-*.service

# Nginx 설정
sudo cp ../nginx/stockpilot.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/stockpilot.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

echo "✅ StockPilot 설치 완료"
echo "📝 다음 단계: 환경 변수 설정 및 서비스 시작"
```

#### 2. 환경 변수 설정
```bash
# /opt/stockpilot/.env.production
# 데이터베이스
DATABASE_URL=postgresql://stockpilot:password@localhost:5432/stockpilot
REDIS_URL=redis://localhost:6379/0

# API 키들 (실제 값으로 교체)
OPENAI_API_KEY=sk-...
ALPHA_VANTAGE_API_KEY=...
NEWSAPI_KEY=...
DART_API_KEY=...

# 보안
JWT_SECRET_KEY=$(openssl rand -hex 32)
ENCRYPT_KEY=$(openssl rand -hex 32)

# 로깅
LOG_LEVEL=INFO
LOG_DIR=/var/log/stockpilot

# 알림
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_USERNAME=...
EMAIL_PASSWORD=...

# 모니터링
ENABLE_METRICS=true
PROMETHEUS_PORT=9090
GRAFANA_PORT=3001
```

#### 3. 서비스 시작
```bash
#!/bin/bash
# start_services.sh

# 로그 디렉토리 생성
sudo mkdir -p /var/log/stockpilot
sudo chown stockpilot:stockpilot /var/log/stockpilot

# 데이터 디렉토리 생성
sudo mkdir -p /opt/stockpilot/data
sudo chown stockpilot:stockpilot /opt/stockpilot/data

# 서비스 시작
sudo systemctl start stockpilot-api
sudo systemctl start stockpilot-websocket
sudo systemctl start stockpilot-health
sudo systemctl start stockpilot-cost-dashboard

# 상태 확인
systemctl status stockpilot-*

# 웹 서버 시작
sudo systemctl start nginx

echo "🎉 모든 서비스가 시작되었습니다"
echo "🌐 http://localhost 에서 접속 가능"
```

### Docker 배포

#### Docker Compose 설정
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl/certs
    depends_on:
      - backend
      - frontend

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    environment:
      - DATABASE_URL=postgresql://stockpilot:${DB_PASSWORD}@db:5432/stockpilot
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./data:/opt/stockpilot/data
      - ./logs:/var/log/stockpilot

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
    volumes:
      - frontend_build:/app/build

  websocket:
    build:
      context: ./backend
      dockerfile: Dockerfile.websocket
    ports:
      - "8765:8765"
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=stockpilot
      - POSTGRES_USER=stockpilot
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  monitoring:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

volumes:
  postgres_data:
  redis_data:
  frontend_build:
```

---

## 📊 일상 운영

### 일일 체크리스트

#### 아침 점검 (09:00)
```bash
#!/bin/bash
# daily_morning_check.sh

echo "📅 $(date '+%Y-%m-%d %H:%M:%S') - 일일 아침 점검 시작"

# 1. 시스템 상태 확인
echo "🖥️ 시스템 리소스 확인"
echo "CPU 사용률: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')"
echo "메모리 사용률: $(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')"
echo "디스크 사용률: $(df -h | grep '/opt' | awk '{print $5}')"

# 2. 서비스 상태 확인
echo "🔧 서비스 상태 확인"
for service in stockpilot-api stockpilot-websocket stockpilot-health; do
    if systemctl is-active --quiet $service; then
        echo "✅ $service: 실행 중"
    else
        echo "❌ $service: 중단됨"
        sudo systemctl start $service
    fi
done

# 3. 로그 확인 (최근 1시간 에러)
echo "📝 최근 에러 로그 확인"
error_count=$(grep -i error /var/log/stockpilot/*.log | grep "$(date '+%Y-%m-%d %H')" | wc -l)
echo "최근 1시간 에러 수: $error_count"

if [ $error_count -gt 10 ]; then
    echo "⚠️ 에러가 많습니다. 로그를 확인하세요."
fi

# 4. API 헬스 체크
echo "🌐 API 헬스 체크"
health_response=$(curl -s -w "%{http_code}" http://localhost:8000/api/v1/system/health)
health_code="${health_response: -3}"

if [ "$health_code" = "200" ]; then
    echo "✅ API 서버: 정상"
else
    echo "❌ API 서버: 이상 (HTTP $health_code)"
fi

# 5. 데이터베이스 연결 확인
echo "💾 데이터베이스 연결 확인"
if pg_isready -h localhost -p 5432 -U stockpilot > /dev/null 2>&1; then
    echo "✅ PostgreSQL: 연결 정상"
else
    echo "❌ PostgreSQL: 연결 실패"
fi

# 6. Redis 연결 확인
echo "🔴 Redis 연결 확인"
if redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis: 연결 정상"
else
    echo "❌ Redis: 연결 실패"
fi

echo "✅ 일일 아침 점검 완료"
```

#### 저녁 점검 (18:00)
```bash
#!/bin/bash
# daily_evening_check.sh

echo "🌅 $(date '+%Y-%m-%d %H:%M:%S') - 일일 저녁 점검 시작"

# 1. 백업 상태 확인
echo "💾 백업 상태 확인"
latest_backup=$(ls -t /opt/stockpilot/backups/db_backup_*.sql.gz 2>/dev/null | head -n1)
if [ -n "$latest_backup" ]; then
    backup_date=$(basename "$latest_backup" | grep -o '[0-9]\{8\}')
    today=$(date +%Y%m%d)
    if [ "$backup_date" = "$today" ]; then
        echo "✅ 오늘 백업: 완료"
    else
        echo "⚠️ 오늘 백업: 미완료 - 백업 실행"
        /opt/stockpilot/scripts/backup_database.sh
    fi
else
    echo "❌ 백업 파일 없음 - 백업 실행"
    /opt/stockpilot/scripts/backup_database.sh
fi

# 2. 로그 로테이션
echo "📜 로그 로테이션"
find /var/log/stockpilot -name "*.log" -size +100M -exec logrotate -f /etc/logrotate.d/stockpilot {} \;

# 3. 캐시 정리
echo "🧹 캐시 정리"
redis-cli FLUSHDB

# 4. 성능 통계
echo "📊 일일 성능 통계"
echo "API 호출 수: $(grep "API_CALL" /var/log/stockpilot/api.log | grep "$(date +%Y-%m-%d)" | wc -l)"
echo "WebSocket 연결 수: $(grep "WS_CONNECT" /var/log/stockpilot/websocket.log | grep "$(date +%Y-%m-%d)" | wc -l)"
echo "오류 발생 수: $(grep -i error /var/log/stockpilot/*.log | grep "$(date +%Y-%m-%d)" | wc -l)"

echo "✅ 일일 저녁 점검 완료"
```

### 주간 점검

#### 주간 리포트 생성
```python
#!/usr/bin/env python3
# weekly_report.py

import psycopg2
import json
from datetime import datetime, timedelta
from collections import defaultdict

def generate_weekly_report():
    """주간 운영 리포트 생성"""
    
    # 데이터베이스 연결
    conn = psycopg2.connect(
        host="localhost",
        database="stockpilot",
        user="stockpilot",
        password="password"
    )
    
    cur = conn.cursor()
    
    # 지난 주 날짜 범위
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    report = {
        "period": f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}",
        "generated_at": datetime.now().isoformat()
    }
    
    # 사용자 활동 통계
    cur.execute("""
        SELECT DATE(created_at) as date, COUNT(*) as api_calls
        FROM api_usage_log
        WHERE created_at >= %s AND created_at <= %s
        GROUP BY DATE(created_at)
        ORDER BY date
    """, (start_date, end_date))
    
    daily_stats = cur.fetchall()
    report["daily_api_calls"] = [{"date": str(row[0]), "calls": row[1]} for row in daily_stats]
    
    # 에러 통계
    cur.execute("""
        SELECT error_type, COUNT(*) as count
        FROM error_log
        WHERE created_at >= %s AND created_at <= %s
        GROUP BY error_type
        ORDER BY count DESC
    """, (start_date, end_date))
    
    error_stats = cur.fetchall()
    report["error_statistics"] = [{"type": row[0], "count": row[1]} for row in error_stats]
    
    # 성능 지표
    cur.execute("""
        SELECT AVG(response_time) as avg_response_time,
               MAX(response_time) as max_response_time,
               MIN(response_time) as min_response_time
        FROM performance_log
        WHERE created_at >= %s AND created_at <= %s
    """, (start_date, end_date))
    
    perf_stats = cur.fetchone()
    report["performance"] = {
        "avg_response_time": float(perf_stats[0]) if perf_stats[0] else 0,
        "max_response_time": float(perf_stats[1]) if perf_stats[1] else 0,
        "min_response_time": float(perf_stats[2]) if perf_stats[2] else 0
    }
    
    # 인기 종목 TOP 10
    cur.execute("""
        SELECT symbol, COUNT(*) as requests
        FROM stock_request_log
        WHERE created_at >= %s AND created_at <= %s
        GROUP BY symbol
        ORDER BY requests DESC
        LIMIT 10
    """, (start_date, end_date))
    
    popular_stocks = cur.fetchall()
    report["popular_stocks"] = [{"symbol": row[0], "requests": row[1]} for row in popular_stocks]
    
    cur.close()
    conn.close()
    
    # 리포트 저장
    report_file = f"/var/log/stockpilot/weekly_report_{datetime.now().strftime('%Y%m%d')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"📊 주간 리포트 생성 완료: {report_file}")
    return report

if __name__ == "__main__":
    generate_weekly_report()
```

### 월간 유지보수

#### 시스템 최적화
```bash
#!/bin/bash
# monthly_maintenance.sh

echo "🔧 월간 유지보수 작업 시작"

# 1. 패키지 업데이트
echo "📦 시스템 패키지 업데이트"
sudo apt update && sudo apt upgrade -y

# 2. 데이터베이스 최적화
echo "💾 데이터베이스 최적화"
sudo -u postgres psql stockpilot -c "VACUUM FULL;"
sudo -u postgres psql stockpilot -c "REINDEX DATABASE stockpilot;"

# 3. 오래된 로그 삭제 (30일 이상)
echo "🗑️ 오래된 로그 삭제"
find /var/log/stockpilot -name "*.log*" -mtime +30 -delete

# 4. 오래된 백업 삭제 (90일 이상)
echo "🗂️ 오래된 백업 삭제"
find /opt/stockpilot/backups -name "*.sql.gz" -mtime +90 -delete

# 5. SSL 인증서 갱신
echo "🔒 SSL 인증서 갱신"
sudo certbot renew --nginx

# 6. 보안 스캔
echo "🛡️ 보안 스캔 실행"
sudo chkrootkit
sudo rkhunter --update
sudo rkhunter --checkall --skip-keypress

# 7. 성능 벤치마크
echo "⚡ 성능 벤치마크 실행"
cd /opt/stockpilot/backend
source venv/bin/activate
python services/performance_benchmark.py

echo "✅ 월간 유지보수 작업 완료"
```

---

## 📈 모니터링 및 알림

### 시스템 메트릭 수집

#### Prometheus 설정
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "stockpilot_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  - job_name: 'stockpilot-api'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'

  - job_name: 'stockpilot-system'
    static_configs:
      - targets: ['localhost:9100']
    
  - job_name: 'postgres'
    static_configs:
      - targets: ['localhost:9187']
    
  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:9121']
```

#### 알림 규칙
```yaml
# stockpilot_rules.yml
groups:
  - name: stockpilot_alerts
    rules:
      # API 서버 다운
      - alert: APIServerDown
        expr: up{job="stockpilot-api"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "StockPilot API 서버가 다운되었습니다"
          
      # 높은 응답 시간
      - alert: HighResponseTime
        expr: http_request_duration_seconds{quantile="0.95"} > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API 응답 시간이 2초를 초과했습니다"
          
      # 높은 에러율
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "5xx 에러율이 10%를 초과했습니다"
          
      # 메모리 사용량 높음
      - alert: HighMemoryUsage
        expr: (node_memory_Active_bytes / node_memory_MemTotal_bytes) * 100 > 80
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "메모리 사용률이 80%를 초과했습니다"
          
      # 디스크 공간 부족
      - alert: DiskSpaceLow
        expr: (node_filesystem_free_bytes / node_filesystem_size_bytes) * 100 < 10
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "디스크 여유 공간이 10% 미만입니다"
```

### 커스텀 모니터링

#### 비즈니스 메트릭 수집
```python
#!/usr/bin/env python3
# business_metrics_collector.py

import psycopg2
import redis
import time
from prometheus_client import start_http_server, Gauge, Counter, Histogram
import logging

# Prometheus 메트릭 정의
active_users = Gauge('stockpilot_active_users', '현재 활성 사용자 수')
api_requests_total = Counter('stockpilot_api_requests_total', 'API 요청 총 수', ['endpoint', 'method', 'status'])
response_time = Histogram('stockpilot_response_time_seconds', 'API 응답 시간', ['endpoint'])
stock_analysis_requests = Counter('stockpilot_stock_analysis_requests', '주식 분석 요청 수', ['symbol'])
websocket_connections = Gauge('stockpilot_websocket_connections', 'WebSocket 연결 수')
portfolio_count = Gauge('stockpilot_portfolios_total', '총 포트폴리오 수')
ai_model_usage = Counter('stockpilot_ai_model_usage', 'AI 모델 사용량', ['model', 'provider'])
cost_tracking = Gauge('stockpilot_daily_cost_usd', '일일 비용 (USD)', ['category'])

class BusinessMetricsCollector:
    def __init__(self):
        self.db_conn = psycopg2.connect(
            host="localhost",
            database="stockpilot",
            user="stockpilot",
            password="password"
        )
        self.redis_conn = redis.Redis(host='localhost', port=6379, db=0)
        
    def collect_user_metrics(self):
        """사용자 관련 메트릭 수집"""
        try:
            cur = self.db_conn.cursor()
            
            # 활성 사용자 수 (최근 1시간 이내 활동)
            cur.execute("""
                SELECT COUNT(DISTINCT user_id)
                FROM user_activity_log
                WHERE last_activity > NOW() - INTERVAL '1 hour'
            """)
            active_count = cur.fetchone()[0]
            active_users.set(active_count)
            
            # 총 포트폴리오 수
            cur.execute("SELECT COUNT(*) FROM portfolios WHERE active = true")
            portfolio_total = cur.fetchone()[0]
            portfolio_count.set(portfolio_total)
            
            cur.close()
            
        except Exception as e:
            logging.error(f"사용자 메트릭 수집 실패: {e}")
    
    def collect_api_metrics(self):
        """API 관련 메트릭 수집"""
        try:
            cur = self.db_conn.cursor()
            
            # 최근 5분간 API 요청 통계
            cur.execute("""
                SELECT endpoint, method, status_code, COUNT(*), AVG(response_time)
                FROM api_request_log
                WHERE timestamp > NOW() - INTERVAL '5 minutes'
                GROUP BY endpoint, method, status_code
            """)
            
            for row in cur.fetchall():
                endpoint, method, status, count, avg_time = row
                api_requests_total.labels(
                    endpoint=endpoint,
                    method=method,
                    status=str(status)
                ).inc(count)
                
                if avg_time:
                    response_time.labels(endpoint=endpoint).observe(avg_time / 1000)
            
            cur.close()
            
        except Exception as e:
            logging.error(f"API 메트릭 수집 실패: {e}")
    
    def collect_business_metrics(self):
        """비즈니스 메트릭 수집"""
        try:
            cur = self.db_conn.cursor()
            
            # 인기 종목 분석 요청
            cur.execute("""
                SELECT symbol, COUNT(*)
                FROM stock_analysis_log
                WHERE timestamp > NOW() - INTERVAL '1 hour'
                GROUP BY symbol
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """)
            
            for symbol, count in cur.fetchall():
                stock_analysis_requests.labels(symbol=symbol).inc(count)
            
            # AI 모델 사용량
            cur.execute("""
                SELECT model_name, provider, COUNT(*), SUM(cost)
                FROM ai_model_usage
                WHERE timestamp > NOW() - INTERVAL '1 hour'
                GROUP BY model_name, provider
            """)
            
            total_cost = 0
            for model, provider, count, cost in cur.fetchall():
                ai_model_usage.labels(model=model, provider=provider).inc(count)
                total_cost += cost or 0
            
            cost_tracking.labels(category='ai_models').set(total_cost)
            
            cur.close()
            
        except Exception as e:
            logging.error(f"비즈니스 메트릭 수집 실패: {e}")
    
    def collect_websocket_metrics(self):
        """WebSocket 메트릭 수집"""
        try:
            # Redis에서 활성 WebSocket 연결 수 조회
            connection_count = self.redis_conn.scard("websocket:connections")
            websocket_connections.set(connection_count)
            
        except Exception as e:
            logging.error(f"WebSocket 메트릭 수집 실패: {e}")
    
    def run(self):
        """메트릭 수집 실행"""
        while True:
            self.collect_user_metrics()
            self.collect_api_metrics()
            self.collect_business_metrics()
            self.collect_websocket_metrics()
            
            time.sleep(30)  # 30초마다 수집

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Prometheus HTTP 서버 시작
    start_http_server(8001)
    logging.info("Prometheus 메트릭 서버 시작: http://localhost:8001/metrics")
    
    # 메트릭 수집기 시작
    collector = BusinessMetricsCollector()
    collector.run()
```

### Grafana 대시보드

#### 시스템 대시보드
```json
{
  "dashboard": {
    "title": "StockPilot 시스템 모니터링",
    "panels": [
      {
        "title": "시스템 리소스",
        "type": "graph",
        "targets": [
          {
            "expr": "100 - (avg(irate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
            "legendFormat": "CPU 사용률"
          },
          {
            "expr": "(node_memory_Active_bytes / node_memory_MemTotal_bytes) * 100",
            "legendFormat": "메모리 사용률"
          }
        ]
      },
      {
        "title": "API 성능",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "초당 요청 수"
          },
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile 응답시간"
          }
        ]
      },
      {
        "title": "에러율",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m]) / rate(http_requests_total[5m]) * 100"
          }
        ]
      },
      {
        "title": "활성 사용자",
        "type": "singlestat",
        "targets": [
          {
            "expr": "stockpilot_active_users"
          }
        ]
      }
    ]
  }
}
```

---

## 💾 백업 및 복구

### 자동 백업 시스템

#### 데이터베이스 백업
```bash
#!/bin/bash
# backup_database.sh

set -euo pipefail

BACKUP_DIR="/opt/stockpilot/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_NAME="stockpilot"
DB_USER="stockpilot"

# 백업 디렉토리 생성
mkdir -p "$BACKUP_DIR"

echo "🗄️ 데이터베이스 백업 시작: $TIMESTAMP"

# PostgreSQL 덤프
pg_dump -h localhost -U "$DB_USER" -W "$DB_NAME" | gzip > "$BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz"

if [ $? -eq 0 ]; then
    echo "✅ 데이터베이스 백업 완료: db_backup_$TIMESTAMP.sql.gz"
    
    # 백업 파일 크기 확인
    backup_size=$(du -h "$BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz" | cut -f1)
    echo "📁 백업 파일 크기: $backup_size"
    
    # 백업 무결성 검증
    echo "🔍 백업 무결성 검증 중..."
    if gunzip -t "$BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz"; then
        echo "✅ 백업 파일 무결성 확인됨"
    else
        echo "❌ 백업 파일 손상됨"
        exit 1
    fi
    
    # 오래된 백업 삭제 (30일 이상)
    find "$BACKUP_DIR" -name "db_backup_*.sql.gz" -mtime +30 -delete
    echo "🗑️ 30일 이상된 백업 파일 삭제 완료"
    
else
    echo "❌ 데이터베이스 백업 실패"
    exit 1
fi

# 설정 파일 백업
echo "⚙️ 설정 파일 백업 중..."
tar -czf "$BACKUP_DIR/config_backup_$TIMESTAMP.tar.gz" \
    /opt/stockpilot/.env* \
    /etc/nginx/sites-available/stockpilot* \
    /etc/systemd/system/stockpilot*.service

echo "✅ 설정 파일 백업 완료: config_backup_$TIMESTAMP.tar.gz"

# 원격 백업 (S3, rsync 등)
if [ -n "${AWS_S3_BUCKET:-}" ]; then
    echo "☁️ S3 원격 백업 중..."
    aws s3 cp "$BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz" "s3://$AWS_S3_BUCKET/stockpilot/backups/"
    aws s3 cp "$BACKUP_DIR/config_backup_$TIMESTAMP.tar.gz" "s3://$AWS_S3_BUCKET/stockpilot/backups/"
    echo "✅ S3 원격 백업 완료"
fi

echo "🎉 전체 백업 프로세스 완료"
```

#### 실시간 백업 (WAL 아카이빙)
```bash
#!/bin/bash
# setup_wal_archiving.sh

# PostgreSQL 설정 수정
sudo -u postgres psql -c "ALTER SYSTEM SET wal_level = replica;"
sudo -u postgres psql -c "ALTER SYSTEM SET archive_mode = on;"
sudo -u postgres psql -c "ALTER SYSTEM SET archive_command = 'cp %p /opt/stockpilot/backups/wal_archive/%f';"

# WAL 아카이브 디렉토리 생성
sudo mkdir -p /opt/stockpilot/backups/wal_archive
sudo chown postgres:postgres /opt/stockpilot/backups/wal_archive

# PostgreSQL 재시작
sudo systemctl restart postgresql

echo "✅ WAL 아카이빙 설정 완료"
```

### 데이터 복구

#### 전체 복구 절차
```bash
#!/bin/bash
# restore_database.sh

set -euo pipefail

BACKUP_FILE="$1"
DB_NAME="stockpilot"
DB_USER="stockpilot"

if [ -z "$BACKUP_FILE" ]; then
    echo "사용법: $0 <백업파일경로>"
    echo "예시: $0 /opt/stockpilot/backups/db_backup_20240101_120000.sql.gz"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ 백업 파일을 찾을 수 없습니다: $BACKUP_FILE"
    exit 1
fi

echo "⚠️ 위험: 현재 데이터베이스가 백업 데이터로 완전히 교체됩니다!"
echo "백업 파일: $BACKUP_FILE"
read -p "계속하시겠습니까? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "복구 작업이 취소되었습니다."
    exit 0
fi

echo "🛑 모든 StockPilot 서비스 중단 중..."
sudo systemctl stop stockpilot-*

echo "💾 현재 데이터베이스 백업 생성 중..."
current_backup="/tmp/pre_restore_backup_$(date +%Y%m%d_%H%M%S).sql.gz"
pg_dump -h localhost -U "$DB_USER" -W "$DB_NAME" | gzip > "$current_backup"
echo "✅ 현재 상태 백업 완료: $current_backup"

echo "🗄️ 데이터베이스 복구 시작..."

# 기존 데이터베이스 삭제 및 재생성
sudo -u postgres psql -c "DROP DATABASE IF EXISTS $DB_NAME;"
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

# 백업에서 복구
if [[ "$BACKUP_FILE" == *.gz ]]; then
    gunzip -c "$BACKUP_FILE" | sudo -u postgres psql "$DB_NAME"
else
    sudo -u postgres psql "$DB_NAME" < "$BACKUP_FILE"
fi

if [ $? -eq 0 ]; then
    echo "✅ 데이터베이스 복구 완료"
    
    # 서비스 재시작
    echo "🚀 서비스 재시작 중..."
    sudo systemctl start stockpilot-*
    
    # 헬스 체크
    sleep 10
    health_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/system/health)
    if [ "$health_response" = "200" ]; then
        echo "✅ 시스템 정상 복구 완료"
    else
        echo "⚠️ 시스템 복구는 완료되었으나 헬스 체크 실패 (HTTP $health_response)"
        echo "서비스 상태를 확인하세요."
    fi
    
else
    echo "❌ 데이터베이스 복구 실패"
    echo "이전 상태 백업이 있습니다: $current_backup"
    exit 1
fi
```

#### Point-in-Time 복구
```bash
#!/bin/bash
# point_in_time_recovery.sh

TARGET_TIME="$1"  # 예: "2024-01-01 12:00:00"
BASE_BACKUP="$2"

if [ -z "$TARGET_TIME" ] || [ -z "$BASE_BACKUP" ]; then
    echo "사용법: $0 '<복구시점>' '<베이스백업파일>'"
    echo "예시: $0 '2024-01-01 12:00:00' /opt/stockpilot/backups/db_backup_20240101_000000.sql.gz"
    exit 1
fi

echo "⏰ Point-in-Time 복구 시작"
echo "목표 시점: $TARGET_TIME"
echo "베이스 백업: $BASE_BACKUP"

# PostgreSQL 중단
sudo systemctl stop postgresql

# 데이터 디렉토리 백업
sudo cp -r /var/lib/postgresql/15/main /var/lib/postgresql/15/main.backup

# 베이스 백업 복원
sudo -u postgres rm -rf /var/lib/postgresql/15/main/*
sudo -u postgres tar -xzf "$BASE_BACKUP" -C /var/lib/postgresql/15/main

# recovery.conf 설정
cat << EOF | sudo -u postgres tee /var/lib/postgresql/15/main/recovery.conf
restore_command = 'cp /opt/stockpilot/backups/wal_archive/%f %p'
recovery_target_time = '$TARGET_TIME'
recovery_target_action = 'promote'
EOF

# PostgreSQL 시작
sudo systemctl start postgresql

echo "✅ Point-in-Time 복구 완료"
```

---

## ⚡ 성능 튜닝

### 데이터베이스 최적화

#### PostgreSQL 튜닝
```sql
-- postgresql.conf 최적화 설정

-- 메모리 설정 (16GB RAM 기준)
shared_buffers = '4GB'                    -- 총 RAM의 25%
effective_cache_size = '12GB'             -- 총 RAM의 75%
work_mem = '256MB'                        -- 정렬/조인용 메모리
maintenance_work_mem = '1GB'              -- 유지보수 작업용 메모리

-- 커넥션 설정
max_connections = 200                     -- 최대 동시 연결
max_prepared_statements = 100

-- WAL 설정
wal_buffers = '64MB'
checkpoint_completion_target = 0.9
wal_writer_delay = '200ms'

-- 쿼리 플래너
random_page_cost = 1.1                    -- SSD 기준
effective_io_concurrency = 200

-- 로깅
log_min_duration_statement = 1000         -- 1초 이상 쿼리 로깅
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
```

#### 인덱스 최적화
```sql
-- 자주 사용되는 쿼리용 인덱스
CREATE INDEX CONCURRENTLY idx_stocks_symbol ON stocks(symbol);
CREATE INDEX CONCURRENTLY idx_stock_prices_symbol_date ON stock_prices(symbol, date DESC);
CREATE INDEX CONCURRENTLY idx_news_published_sentiment ON news(published_at DESC, sentiment);
CREATE INDEX CONCURRENTLY idx_portfolios_user_active ON portfolios(user_id) WHERE active = true;
CREATE INDEX CONCURRENTLY idx_api_logs_timestamp ON api_request_log(timestamp DESC);

-- 복합 인덱스
CREATE INDEX CONCURRENTLY idx_user_activity_user_time ON user_activity_log(user_id, last_activity DESC);
CREATE INDEX CONCURRENTLY idx_analysis_symbol_date ON stock_analysis(symbol, created_at DESC);

-- 부분 인덱스
CREATE INDEX CONCURRENTLY idx_active_subscriptions ON subscriptions(user_id) WHERE active = true;
CREATE INDEX CONCURRENTLY idx_recent_errors ON error_log(timestamp) WHERE timestamp > NOW() - INTERVAL '1 day';
```

#### 파티셔닝 설정
```sql
-- 시계열 데이터 파티셔닝 (stock_prices 테이블)
CREATE TABLE stock_prices (
    id BIGSERIAL,
    symbol VARCHAR(10) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    volume BIGINT,
    date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
) PARTITION BY RANGE (date);

-- 월별 파티션 생성
CREATE TABLE stock_prices_2024_01 PARTITION OF stock_prices
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
    
CREATE TABLE stock_prices_2024_02 PARTITION OF stock_prices
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- 자동 파티션 생성 함수
CREATE OR REPLACE FUNCTION create_monthly_partition(table_name text, start_date date)
RETURNS void AS $$
DECLARE
    partition_name text;
    end_date date;
BEGIN
    partition_name := table_name || '_' || to_char(start_date, 'YYYY_MM');
    end_date := start_date + interval '1 month';
    
    EXECUTE format('CREATE TABLE %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
                   partition_name, table_name, start_date, end_date);
END;
$$ LANGUAGE plpgsql;
```

### 애플리케이션 최적화

#### 캐싱 전략
```python
# redis_cache.py
import redis
import json
from functools import wraps
from typing import Any, Callable

class CacheManager:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
    
    def cache_result(self, ttl: int = 300, key_prefix: str = ""):
        """결과 캐싱 데코레이터"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 캐시 키 생성
                cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
                
                # 캐시에서 조회
                cached_result = self.redis_client.get(cache_key)
                if cached_result:
                    return json.loads(cached_result)
                
                # 함수 실행 및 결과 캐싱
                result = func(*args, **kwargs)
                self.redis_client.setex(
                    cache_key, 
                    ttl, 
                    json.dumps(result, default=str)
                )
                
                return result
            return wrapper
        return decorator
    
    def invalidate_pattern(self, pattern: str):
        """패턴에 맞는 캐시 무효화"""
        keys = self.redis_client.keys(pattern)
        if keys:
            self.redis_client.delete(*keys)

# 사용 예시
cache = CacheManager()

@cache.cache_result(ttl=300, key_prefix="stock_data")
async def get_stock_data(symbol: str, interval: str = "1d"):
    # 실제 데이터 조회 로직
    pass

@cache.cache_result(ttl=600, key_prefix="stock_analysis")
async def get_stock_analysis(symbol: str):
    # AI 분석 로직 (비용이 높으므로 긴 캐시)
    pass
```

#### 비동기 처리
```python
# async_processor.py
import asyncio
from concurrent.futures import ThreadPoolExecutor
import aioredis
from typing import List

class AsyncTaskProcessor:
    def __init__(self):
        self.redis = None
        self.executor = ThreadPoolExecutor(max_workers=20)
        self.queue_name = "stockpilot:tasks"
    
    async def init_redis(self):
        self.redis = await aioredis.from_url("redis://localhost:6379")
    
    async def add_task(self, task_type: str, data: dict):
        """비동기 작업 큐에 추가"""
        task = {
            "type": task_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        await self.redis.lpush(self.queue_name, json.dumps(task))
    
    async def process_tasks(self):
        """작업 큐 처리"""
        while True:
            try:
                # 블로킹 방식으로 작업 대기
                _, task_data = await self.redis.brpop([self.queue_name], timeout=1)
                if task_data:
                    task = json.loads(task_data)
                    await self.execute_task(task)
                    
            except Exception as e:
                logger.error(f"작업 처리 오류: {e}")
                await asyncio.sleep(1)
    
    async def execute_task(self, task: dict):
        """개별 작업 실행"""
        task_type = task.get("type")
        data = task.get("data", {})
        
        if task_type == "stock_analysis":
            await self.process_stock_analysis(data)
        elif task_type == "news_sentiment":
            await self.process_news_sentiment(data)
        elif task_type == "portfolio_update":
            await self.process_portfolio_update(data)
    
    async def process_stock_analysis(self, data: dict):
        """주식 분석 작업 처리"""
        symbol = data.get("symbol")
        # CPU 집약적 작업을 별도 스레드에서 실행
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self.executor, 
            self.analyze_stock_sync, 
            symbol
        )
        
        # 결과를 캐시에 저장
        cache_key = f"analysis:{symbol}"
        await self.redis.setex(cache_key, 3600, json.dumps(result))
    
    def analyze_stock_sync(self, symbol: str):
        """동기적 주식 분석 (CPU 집약적)"""
        # 실제 분석 로직
        pass
```

#### 데이터베이스 연결 풀링
```python
# db_pool.py
import asyncpg
import asyncio
from typing import Optional

class DatabasePool:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def init_pool(self):
        """연결 풀 초기화"""
        self.pool = await asyncpg.create_pool(
            host="localhost",
            port=5432,
            user="stockpilot",
            password="password",
            database="stockpilot",
            min_size=10,
            max_size=50,
            max_queries=50000,
            max_inactive_connection_lifetime=300,
            command_timeout=60
        )
    
    async def execute_query(self, query: str, *args):
        """쿼리 실행"""
        async with self.pool.acquire() as connection:
            return await connection.fetch(query, *args)
    
    async def execute_transaction(self, queries: list):
        """트랜잭션 실행"""
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                results = []
                for query, args in queries:
                    result = await connection.fetch(query, *args)
                    results.append(result)
                return results
    
    async def close_pool(self):
        """연결 풀 종료"""
        if self.pool:
            await self.pool.close()

# 전역 인스턴스
db_pool = DatabasePool()
```

### 프론트엔드 최적화

#### React 성능 최적화
```javascript
// performance_optimizations.js
import React, { memo, useMemo, useCallback, lazy, Suspense } from 'react';
import { debounce } from 'lodash';

// 1. 컴포넌트 메모이제이션
const StockCard = memo(({ stock, onSelect }) => {
  return (
    <div onClick={() => onSelect(stock.symbol)}>
      <h3>{stock.symbol}</h3>
      <p>${stock.price}</p>
    </div>
  );
});

// 2. 코드 스플리팅
const StockAnalysis = lazy(() => import('./StockAnalysis'));
const Portfolio = lazy(() => import('./Portfolio'));

// 3. 가상화된 리스트
import { VariableSizeList as List } from 'react-window';

const VirtualizedStockList = ({ stocks }) => {
  const getItemSize = useCallback((index) => {
    return stocks[index].expanded ? 200 : 80;
  }, [stocks]);

  const renderItem = useCallback(({ index, style }) => (
    <div style={style}>
      <StockCard stock={stocks[index]} />
    </div>
  ), [stocks]);

  return (
    <List
      height={600}
      itemCount={stocks.length}
      itemSize={getItemSize}
    >
      {renderItem}
    </List>
  );
};

// 4. API 호출 최적화
const useStockData = (symbol) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchData = useCallback(
    debounce(async (sym) => {
      setLoading(true);
      try {
        const response = await fetch(`/api/v1/stocks/${sym}/data`);
        const result = await response.json();
        setData(result);
      } finally {
        setLoading(false);
      }
    }, 300),
    []
  );

  useEffect(() => {
    if (symbol) {
      fetchData(symbol);
    }
  }, [symbol, fetchData]);

  return { data, loading };
};

// 5. WebSocket 연결 최적화
const useWebSocket = (url, options = {}) => {
  const [socket, setSocket] = useState(null);
  const [data, setData] = useState(null);

  useEffect(() => {
    const ws = new WebSocket(url);
    
    ws.onopen = () => {
      setSocket(ws);
    };

    ws.onmessage = (event) => {
      const newData = JSON.parse(event.data);
      setData(prevData => ({
        ...prevData,
        ...newData
      }));
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      // 자동 재연결 로직
      setTimeout(() => {
        setSocket(null);
      }, 5000);
    };

    return () => {
      ws.close();
    };
  }, [url]);

  return { socket, data };
};
```

---

## 🛡️ 보안 관리

### 시스템 보안

#### 방화벽 설정
```bash
#!/bin/bash
# setup_firewall.sh

# UFW 초기 설정
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing

# SSH 접근 허용 (특정 IP만)
sudo ufw allow from 192.168.1.0/24 to any port 22
sudo ufw allow from 10.0.0.0/8 to any port 22

# HTTP/HTTPS 허용
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 내부 서비스 포트 (로컬호스트만)
sudo ufw allow from 127.0.0.1 to any port 5432  # PostgreSQL
sudo ufw allow from 127.0.0.1 to any port 6379  # Redis
sudo ufw allow from 127.0.0.1 to any port 8000  # API
sudo ufw allow from 127.0.0.1 to any port 8765  # WebSocket

# 모니터링 포트 (관리자 네트워크만)
sudo ufw allow from 192.168.1.0/24 to any port 9090  # Prometheus
sudo ufw allow from 192.168.1.0/24 to any port 3001  # Grafana

# 방화벽 활성화
sudo ufw --force enable

echo "✅ 방화벽 설정 완료"
```

#### SSL/TLS 설정
```bash
#!/bin/bash
# setup_ssl.sh

# Let's Encrypt 인증서 발급
sudo certbot --nginx -d stockpilot.ai -d www.stockpilot.ai --non-interactive --agree-tos -m admin@stockpilot.ai

# SSL 설정 강화
cat << 'EOF' > /etc/nginx/snippets/ssl-params.conf
ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers on;
ssl_dhparam /etc/nginx/dhparam.pem;
ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-SHA384;
ssl_ecdh_curve secp384r1;
ssl_session_timeout  10m;
ssl_session_cache shared:SSL:10m;
ssl_session_tickets off;
ssl_stapling on;
ssl_stapling_verify on;
resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;

# 보안 헤더
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
add_header X-XSS-Protection "1; mode=block";
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self' wss: https:";
EOF

# DH 파라미터 생성
sudo openssl dhparam -out /etc/nginx/dhparam.pem 2048

# 자동 갱신 설정
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -

echo "✅ SSL/TLS 설정 완료"
```

#### 침입 탐지 시스템
```bash
#!/bin/bash
# setup_intrusion_detection.sh

# Fail2ban 설치 및 설정
sudo apt install -y fail2ban

# SSH 보호 설정
cat << 'EOF' > /etc/fail2ban/jail.local
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3
ignoreip = 127.0.0.1/8 192.168.1.0/24

[sshd]
enabled = true
port = 22
filter = sshd
logpath = /var/log/auth.log

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/error.log

[nginx-req-limit]
enabled = true
filter = nginx-req-limit
action = iptables-multiport[name=ReqLimit, port="http,https", protocol=tcp]
logpath = /var/log/nginx/access.log
findtime = 600
bantime = 7200
maxretry = 10
EOF

# 커스텀 필터 생성
cat << 'EOF' > /etc/fail2ban/filter.d/stockpilot-api.conf
[Definition]
failregex = ^<HOST> .* "POST /api/v1/auth/login" 401
            ^<HOST> .* "POST /api/v1/auth/login" 429
ignoreregex =
EOF

# StockPilot API 보호 규칙
cat << 'EOF' >> /etc/fail2ban/jail.local

[stockpilot-api]
enabled = true
port = http,https
filter = stockpilot-api
logpath = /var/log/nginx/access.log
maxretry = 5
bantime = 1800
EOF

sudo systemctl enable fail2ban
sudo systemctl restart fail2ban

echo "✅ 침입 탐지 시스템 설정 완료"
```

### 애플리케이션 보안

#### 인증 및 권한 관리
```python
# security.py
import jwt
import bcrypt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app
import redis

class SecurityManager:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=1)
        self.jwt_algorithm = 'HS256'
        
    def hash_password(self, password: str) -> str:
        """비밀번호 해시화"""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """비밀번호 검증"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def generate_jwt_token(self, user_id: str, expires_in: int = 3600) -> str:
        """JWT 토큰 생성"""
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(seconds=expires_in),
            'iat': datetime.utcnow(),
            'iss': 'stockpilot.ai'
        }
        return jwt.encode(payload, current_app.config['JWT_SECRET_KEY'], algorithm=self.jwt_algorithm)
    
    def verify_jwt_token(self, token: str) -> dict:
        """JWT 토큰 검증"""
        try:
            # 블랙리스트 확인
            if self.redis_client.get(f"blacklist:{token}"):
                raise jwt.InvalidTokenError("Token is blacklisted")
            
            payload = jwt.decode(
                token, 
                current_app.config['JWT_SECRET_KEY'], 
                algorithms=[self.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise jwt.InvalidTokenError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise e
    
    def blacklist_token(self, token: str, expires_in: int = 3600):
        """토큰 블랙리스트 등록"""
        self.redis_client.setex(f"blacklist:{token}", expires_in, "1")
    
    def require_auth(self, f):
        """인증 필수 데코레이터"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Missing or invalid token'}), 401
            
            token = auth_header.split(' ')[1]
            try:
                payload = self.verify_jwt_token(token)
                request.current_user = payload
                return f(*args, **kwargs)
            except jwt.InvalidTokenError as e:
                return jsonify({'error': str(e)}), 401
        
        return decorated_function
    
    def require_permission(self, permission: str):
        """권한 확인 데코레이터"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not hasattr(request, 'current_user'):
                    return jsonify({'error': 'Authentication required'}), 401
                
                user_id = request.current_user['user_id']
                if not self.check_user_permission(user_id, permission):
                    return jsonify({'error': 'Insufficient permissions'}), 403
                
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    def check_user_permission(self, user_id: str, permission: str) -> bool:
        """사용자 권한 확인"""
        # 실제 구현에서는 데이터베이스에서 사용자 권한 조회
        user_permissions = self.get_user_permissions(user_id)
        return permission in user_permissions
    
    def get_user_permissions(self, user_id: str) -> list:
        """사용자 권한 목록 조회"""
        # 캐시에서 먼저 확인
        cached_permissions = self.redis_client.get(f"permissions:{user_id}")
        if cached_permissions:
            return json.loads(cached_permissions)
        
        # 데이터베이스에서 조회 후 캐싱
        # 실제 구현 필요
        permissions = []  # DB 쿼리 결과
        self.redis_client.setex(f"permissions:{user_id}", 300, json.dumps(permissions))
        return permissions

# 사용 예시
security = SecurityManager()

@app.route('/api/v1/admin/users')
@security.require_auth
@security.require_permission('admin.users.read')
def get_users():
    # 관리자만 접근 가능한 사용자 목록
    pass
```

#### API 보안 강화
```python
# api_security.py
from flask import request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import hashlib
import hmac
import time

class APISecurityMiddleware:
    def __init__(self, app):
        self.app = app
        
        # Rate Limiting 설정
        self.limiter = Limiter(
            app,
            key_func=get_remote_address,
            default_limits=["100 per hour", "10 per minute"]
        )
        
        self.setup_security_middleware()
    
    def setup_security_middleware(self):
        """보안 미들웨어 설정"""
        
        @self.app.before_request
        def security_checks():
            # 1. API 키 검증
            if request.path.startswith('/api/'):
                if not self.verify_api_key():
                    return jsonify({'error': 'Invalid API key'}), 401
            
            # 2. 요청 서명 검증 (중요한 엔드포인트)
            if request.path.startswith('/api/v1/admin/'):
                if not self.verify_request_signature():
                    return jsonify({'error': 'Invalid request signature'}), 401
            
            # 3. IP 화이트리스트 확인 (관리 기능)
            if request.path.startswith('/api/v1/admin/'):
                if not self.check_ip_whitelist():
                    return jsonify({'error': 'Access denied'}), 403
        
        @self.app.after_request
        def security_headers(response):
            """보안 헤더 추가"""
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            return response
    
    def verify_api_key(self) -> bool:
        """API 키 검증"""
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return False
        
        # 데이터베이스에서 API 키 검증
        # 실제 구현에서는 해시된 API 키와 비교
        valid_keys = self.get_valid_api_keys()
        return api_key in valid_keys
    
    def verify_request_signature(self) -> bool:
        """요청 서명 검증"""
        signature = request.headers.get('X-Signature')
        timestamp = request.headers.get('X-Timestamp')
        
        if not signature or not timestamp:
            return False
        
        # 타임스탬프 검증 (5분 이내)
        current_time = int(time.time())
        if abs(current_time - int(timestamp)) > 300:
            return False
        
        # 서명 생성 및 검증
        secret_key = self.get_secret_key_for_request()
        payload = request.get_data() + timestamp.encode()
        expected_signature = hmac.new(
            secret_key.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def check_ip_whitelist(self) -> bool:
        """IP 화이트리스트 확인"""
        client_ip = get_remote_address()
        whitelist = self.get_ip_whitelist()
        return client_ip in whitelist
    
    def get_valid_api_keys(self) -> set:
        """유효한 API 키 목록 조회"""
        # 실제 구현: 데이터베이스 또는 캐시에서 조회
        return {'api_key_1', 'api_key_2'}
    
    def get_secret_key_for_request(self) -> str:
        """요청별 비밀 키 조회"""
        # 실제 구현: API 키별 고유 비밀 키 반환
        return "secret_key"
    
    def get_ip_whitelist(self) -> set:
        """IP 화이트리스트 조회"""
        return {'127.0.0.1', '192.168.1.0/24'}

# Rate Limiting 설정
@limiter.limit("5 per minute")
def login_endpoint():
    pass

@limiter.limit("100 per hour")
def api_endpoint():
    pass

# 브루트 포스 공격 방지
@limiter.limit("3 per minute", per_method=True)
def password_reset():
    pass
```

### 데이터 보호

#### 데이터 암호화
```python
# encryption.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

class DataEncryption:
    def __init__(self, password: str = None):
        if password:
            self.key = self.derive_key_from_password(password)
        else:
            self.key = self.generate_key()
        self.cipher = Fernet(self.key)
    
    def generate_key(self) -> bytes:
        """새 암호화 키 생성"""
        return Fernet.generate_key()
    
    def derive_key_from_password(self, password: str) -> bytes:
        """패스워드에서 키 유도"""
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def encrypt(self, data: str) -> str:
        """데이터 암호화"""
        encrypted_data = self.cipher.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """데이터 복호화"""
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted_data = self.cipher.decrypt(encrypted_bytes)
        return decrypted_data.decode()
    
    def encrypt_file(self, file_path: str, output_path: str):
        """파일 암호화"""
        with open(file_path, 'rb') as file:
            file_data = file.read()
        
        encrypted_data = self.cipher.encrypt(file_data)
        
        with open(output_path, 'wb') as encrypted_file:
            encrypted_file.write(encrypted_data)

# 사용 예시
encryption = DataEncryption(password="your_secure_password")

# 민감한 데이터 암호화
api_key = "sk-..."
encrypted_api_key = encryption.encrypt(api_key)

# 데이터베이스에 암호화된 데이터 저장
def store_encrypted_api_key(user_id: str, api_key: str):
    encrypted_key = encryption.encrypt(api_key)
    # 데이터베이스 저장 로직
    pass

def retrieve_api_key(user_id: str) -> str:
    # 데이터베이스에서 암호화된 키 조회
    encrypted_key = get_encrypted_key_from_db(user_id)
    return encryption.decrypt(encrypted_key)
```

---

## 🚨 트러블슈팅

### 일반적인 문제들

#### 1. 서비스 시작 실패
```bash
# 문제: systemctl start stockpilot-api 실패

# 1단계: 상태 확인
sudo systemctl status stockpilot-api

# 2단계: 상세 로그 확인
sudo journalctl -u stockpilot-api -n 50 -f

# 3단계: 설정 파일 검증
# 환경 변수 확인
cat /opt/stockpilot/.env.production

# Python 가상환경 확인
cd /opt/stockpilot/backend
source venv/bin/activate
python -c "import sys; print(sys.path)"

# 4단계: 의존성 문제 해결
pip install --upgrade -r requirements.txt

# 5단계: 권한 문제 확인
ls -la /opt/stockpilot/
sudo chown -R stockpilot:stockpilot /opt/stockpilot/
```

#### 2. 데이터베이스 연결 오류
```bash
# 문제: PostgreSQL 연결 실패

# 1단계: PostgreSQL 서비스 상태 확인
sudo systemctl status postgresql
sudo systemctl restart postgresql

# 2단계: 연결 테스트
psql -h localhost -U stockpilot -d stockpilot

# 3단계: 연결 설정 확인
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"

# 4단계: pg_hba.conf 확인
sudo nano /etc/postgresql/15/main/pg_hba.conf
# 다음 라인이 있는지 확인:
# local   all             stockpilot                              md5
# host    all             stockpilot      127.0.0.1/32            md5

# 5단계: PostgreSQL 설정 파일 확인
sudo nano /etc/postgresql/15/main/postgresql.conf
# listen_addresses = 'localhost'
# port = 5432

sudo systemctl restart postgresql
```

#### 3. 메모리 부족 문제
```bash
# 문제: Out of Memory 에러

# 1단계: 메모리 사용량 확인
free -h
ps aux --sort=-%mem | head -10

# 2단계: 스왑 파일 생성
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 영구적 스왑 설정
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 3단계: Python 메모리 제한 설정
# systemd 서비스 파일에 추가:
# MemoryMax=2G
# MemoryHigh=1.5G

# 4단계: PostgreSQL 메모리 튜닝
sudo -u postgres psql -c "
ALTER SYSTEM SET shared_buffers = '512MB';
ALTER SYSTEM SET work_mem = '64MB';
ALTER SYSTEM SET maintenance_work_mem = '256MB';
SELECT pg_reload_conf();
"
```

#### 4. 높은 CPU 사용률
```bash
# 문제: CPU 사용률 100%

# 1단계: 프로세스 확인
top -o %CPU
htop

# 2단계: 특정 프로세스 분석
# Python 프로파일링
cd /opt/stockpilot/backend
source venv/bin/activate
python -m cProfile -o profile.out main.py

# 3단계: 데이터베이스 쿼리 최적화
sudo -u postgres psql stockpilot -c "
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY total_time DESC LIMIT 10;
"

# 4단계: 비동기 작업 큐 확인
redis-cli LLEN stockpilot:tasks
redis-cli LRANGE stockpilot:tasks 0 -1
```

#### 5. WebSocket 연결 문제
```bash
# 문제: WebSocket 연결 실패

# 1단계: WebSocket 서비스 상태 확인
sudo systemctl status stockpilot-websocket
sudo netstat -tlnp | grep :8765

# 2단계: 방화벽 설정 확인
sudo ufw status
sudo ufw allow 8765/tcp

# 3단계: Nginx WebSocket 프록시 설정 확인
sudo nginx -t
sudo systemctl reload nginx

# 4단계: WebSocket 연결 테스트
wscat -c ws://localhost:8765

# 5단계: 클라이언트 로그 확인
# 브라우저 개발자 도구 Console에서:
# WebSocket connection error 메시지 확인
```

### 성능 문제 진단

#### 1. 응답 시간 지연
```python
#!/usr/bin/env python3
# performance_diagnosis.py

import asyncio
import aiohttp
import time
import statistics

async def diagnose_api_performance():
    """API 성능 진단"""
    
    endpoints = [
        '/api/v1/system/health',
        '/api/v1/stocks/AAPL/data',
        '/api/v1/news',
        '/api/v1/portfolio'
    ]
    
    results = {}
    
    for endpoint in endpoints:
        print(f"\n🔍 {endpoint} 성능 테스트")
        response_times = []
        
        async with aiohttp.ClientSession() as session:
            for i in range(10):
                start_time = time.time()
                
                try:
                    async with session.get(f'http://localhost:8000{endpoint}') as response:
                        await response.text()
                        response_time = (time.time() - start_time) * 1000
                        response_times.append(response_time)
                        
                        print(f"  요청 {i+1}: {response_time:.1f}ms (HTTP {response.status})")
                        
                except Exception as e:
                    print(f"  요청 {i+1}: 실패 - {e}")
        
        if response_times:
            results[endpoint] = {
                'avg': statistics.mean(response_times),
                'min': min(response_times),
                'max': max(response_times),
                'p95': sorted(response_times)[int(len(response_times) * 0.95)]
            }
            
            print(f"  평균: {results[endpoint]['avg']:.1f}ms")
            print(f"  최소: {results[endpoint]['min']:.1f}ms")
            print(f"  최대: {results[endpoint]['max']:.1f}ms")
            print(f"  95th: {results[endpoint]['p95']:.1f}ms")
    
    return results

if __name__ == "__main__":
    results = asyncio.run(diagnose_api_performance())
```

#### 2. 데이터베이스 쿼리 분석
```sql
-- slow_query_analysis.sql

-- 1. 가장 느린 쿼리 TOP 10
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows,
    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;

-- 2. 자주 실행되는 쿼리 TOP 10
SELECT 
    query,
    calls,
    total_time,
    mean_time
FROM pg_stat_statements
ORDER BY calls DESC
LIMIT 10;

-- 3. 인덱스 사용량 분석
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation,
    most_common_vals,
    most_common_freqs
FROM pg_stats
WHERE schemaname = 'public'
ORDER BY tablename, attname;

-- 4. 인덱스 효율성 확인
SELECT 
    t.tablename,
    indexname,
    c.reltuples AS num_rows,
    pg_size_pretty(pg_relation_size(quote_ident(t.tablename)::text)) AS table_size,
    pg_size_pretty(pg_relation_size(quote_ident(indexrelname)::text)) AS index_size,
    CASE WHEN indisunique THEN 'Y' ELSE 'N' END AS UNIQUE,
    idx_scan AS number_of_scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched
FROM pg_tables t
LEFT OUTER JOIN pg_class c ON c.relname = t.tablename
LEFT OUTER JOIN (
    SELECT 
        c.relname AS ctablename, 
        ipg.relname AS indexname, 
        x.indnatts AS number_of_columns, 
        idx_scan, 
        idx_tup_read, 
        idx_tup_fetch, 
        indexrelname, 
        indisunique 
    FROM pg_index x
    JOIN pg_class c ON c.oid = x.indrelid
    JOIN pg_class ipg ON ipg.oid = x.indexrelid
    JOIN pg_stat_user_indexes psui ON x.indexrelid = psui.indexrelid
) AS foo ON t.tablename = foo.ctablename
WHERE t.schemaname = 'public'
ORDER BY 1, 2;
```

### 장애 대응 플레이북

#### 1. 전체 서비스 다운
```bash
#!/bin/bash
# emergency_recovery.sh

echo "🚨 긴급 복구 프로세스 시작"

# 1. 서비스 상태 확인
echo "1. 서비스 상태 점검"
systemctl status stockpilot-* | grep -E "(Active|Main PID)"

# 2. 로그 확인
echo "2. 최근 에러 로그 확인"
tail -100 /var/log/stockpilot/*.log | grep -i error

# 3. 시스템 리소스 확인
echo "3. 시스템 리소스 확인"
echo "CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}')"
echo "Memory: $(free -m | awk 'NR==2{printf "%.1f%%", $3*100/$2}')"
echo "Disk: $(df -h | grep '/opt' | awk '{print $5}')"

# 4. 네트워크 연결 확인
echo "4. 네트워크 연결 확인"
netstat -tlnp | grep -E "(5432|6379|8000|8765)"

# 5. 데이터베이스 연결 테스트
echo "5. 데이터베이스 연결 테스트"
if pg_isready -h localhost -p 5432 -U stockpilot; then
    echo "✅ PostgreSQL 연결 정상"
else
    echo "❌ PostgreSQL 연결 실패 - 재시작 시도"
    sudo systemctl restart postgresql
    sleep 5
fi

# 6. Redis 연결 테스트
echo "6. Redis 연결 테스트"
if redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis 연결 정상"
else
    echo "❌ Redis 연결 실패 - 재시작 시도"
    sudo systemctl restart redis-server
    sleep 5
fi

# 7. 서비스 재시작
echo "7. StockPilot 서비스 재시작"
sudo systemctl restart stockpilot-*

# 8. 헬스 체크
echo "8. 헬스 체크 실행"
sleep 10
for i in {1..5}; do
    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/system/health)
    if [ "$response" = "200" ]; then
        echo "✅ 서비스 정상 복구 완료"
        exit 0
    else
        echo "⏳ 헬스 체크 재시도 $i/5 (HTTP $response)"
        sleep 10
    fi
done

echo "❌ 서비스 복구 실패 - 수동 점검 필요"
exit 1
```

#### 2. 데이터베이스 장애
```bash
#!/bin/bash
# database_recovery.sh

echo "💾 데이터베이스 장애 복구 시작"

# 1. PostgreSQL 상태 확인
if ! systemctl is-active --quiet postgresql; then
    echo "PostgreSQL 서비스 중단됨 - 재시작 시도"
    sudo systemctl start postgresql
    sleep 5
fi

# 2. 데이터베이스 연결 확인
if ! pg_isready -h localhost -p 5432 -U stockpilot; then
    echo "데이터베이스 연결 불가 - 상세 진단 시작"
    
    # 로그 확인
    sudo tail -50 /var/log/postgresql/postgresql-*.log
    
    # 디스크 공간 확인
    df -h /var/lib/postgresql
    
    # 프로세스 확인
    ps aux | grep postgres
fi

# 3. 데이터 무결성 검사
echo "데이터 무결성 검사 시작"
sudo -u postgres psql stockpilot -c "
SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del, n_tup_hot_upd
FROM pg_stat_user_tables
ORDER BY schemaname, tablename;
"

# 4. 백업에서 복구 (최후 수단)
if [ "$1" = "--restore-from-backup" ]; then
    echo "⚠️ 백업에서 데이터베이스 복구 시작"
    latest_backup=$(ls -t /opt/stockpilot/backups/db_backup_*.sql.gz | head -n1)
    if [ -n "$latest_backup" ]; then
        echo "최신 백업 파일: $latest_backup"
        /opt/stockpilot/scripts/restore_database.sh "$latest_backup"
    else
        echo "❌ 백업 파일을 찾을 수 없음"
        exit 1
    fi
fi
```

#### 3. 높은 부하 상황
```bash
#!/bin/bash
# high_load_mitigation.sh

echo "⚡ 높은 부하 상황 대응 시작"

# 1. 현재 부하 상태 확인
load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
cpu_count=$(nproc)
load_threshold=$(echo "$cpu_count * 2" | bc)

echo "현재 Load Average: $load_avg"
echo "CPU 코어 수: $cpu_count"
echo "부하 임계값: $load_threshold"

if (( $(echo "$load_avg > $load_threshold" | bc -l) )); then
    echo "🚨 높은 부하 감지됨"
    
    # 2. 리소스 사용량이 높은 프로세스 식별
    echo "리소스 사용량 높은 프로세스:"
    ps aux --sort=-%cpu | head -10
    
    # 3. 데이터베이스 연결 수 확인
    active_connections=$(sudo -u postgres psql -t -c "SELECT count(*) FROM pg_stat_activity;")
    echo "활성 DB 연결 수: $active_connections"
    
    if [ "$active_connections" -gt 100 ]; then
        echo "⚠️ DB 연결 수가 과도함 - 연결 종료"
        sudo -u postgres psql -c "
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE state = 'idle'
        AND query_start < NOW() - INTERVAL '10 minutes';
        "
    fi
    
    # 4. 캐시 정리
    echo "캐시 정리 실행"
    redis-cli FLUSHALL
    
    # 5. 불필요한 서비스 임시 중단
    echo "비필수 서비스 임시 중단"
    sudo systemctl stop stockpilot-cost-dashboard
    
    # 6. Rate Limiting 강화
    echo "Rate Limiting 강화"
    # Nginx 설정에서 rate limit 강화
    sudo nginx -s reload
    
else
    echo "✅ 부하 수준 정상"
fi
```

---

## 📊 장애 대응

### 장애 알림 시스템

#### 자동 알림 설정
```python
#!/usr/bin/env python3
# alert_manager.py

import smtplib
import requests
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging

class AlertManager:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def send_email_alert(self, subject: str, message: str, priority: str = "high"):
        """이메일 알림 발송"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config['email']['sender']
            msg['To'] = ', '.join(self.config['email']['recipients'])
            msg['Subject'] = f"[{priority.upper()}] {subject}"
            
            body = f"""
StockPilot 시스템 알림

시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
우선순위: {priority.upper()}

메시지:
{message}

---
StockPilot 모니터링 시스템
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.config['email']['smtp_server'], 587) as server:
                server.starttls()
                server.login(self.config['email']['username'], self.config['email']['password'])
                server.send_message(msg)
            
            self.logger.info(f"이메일 알림 발송 완료: {subject}")
            
        except Exception as e:
            self.logger.error(f"이메일 발송 실패: {e}")
    
    def send_slack_alert(self, message: str, channel: str = "#alerts", priority: str = "high"):
        """Slack 알림 발송"""
        try:
            color = {
                "critical": "#FF0000",
                "high": "#FF8C00", 
                "medium": "#FFD700",
                "low": "#00FF00"
            }.get(priority, "#FFD700")
            
            payload = {
                "channel": channel,
                "username": "StockPilot Monitor",
                "icon_emoji": ":warning:",
                "attachments": [{
                    "color": color,
                    "title": f"{priority.upper()} Priority Alert",
                    "text": message,
                    "timestamp": datetime.now().timestamp(),
                    "fields": [
                        {"title": "System", "value": "StockPilot", "short": True},
                        {"title": "Environment", "value": "Production", "short": True}
                    ]
                }]
            }
            
            response = requests.post(
                self.config['slack']['webhook_url'],
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info("Slack 알림 발송 완료")
            else:
                self.logger.error(f"Slack 발송 실패: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Slack 알림 실패: {e}")
    
    def send_sms_alert(self, message: str, priority: str = "critical"):
        """SMS 알림 발송 (중요한 알림만)"""
        if priority not in ["critical", "high"]:
            return
        
        try:
            # Twilio, AWS SNS 등을 사용한 SMS 발송
            # 실제 구현 필요
            pass
        except Exception as e:
            self.logger.error(f"SMS 발송 실패: {e}")
    
    def trigger_alert(self, alert_type: str, message: str, priority: str = "high"):
        """통합 알림 발송"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        full_message = f"[{timestamp}] {alert_type}: {message}"
        
        # 우선순위에 따라 알림 방식 결정
        if priority == "critical":
            self.send_email_alert(alert_type, full_message, priority)
            self.send_slack_alert(full_message, priority=priority)
            self.send_sms_alert(full_message, priority)
        elif priority == "high":
            self.send_email_alert(alert_type, full_message, priority)
            self.send_slack_alert(full_message, priority=priority)
        else:
            self.send_slack_alert(full_message, priority=priority)

# 시스템 모니터링과 연동
class SystemMonitor:
    def __init__(self):
        self.alert_manager = AlertManager(config)
        
    def check_system_health(self):
        """시스템 헬스 체크"""
        issues = []
        
        # API 서버 확인
        try:
            response = requests.get('http://localhost:8000/api/v1/system/health', timeout=5)
            if response.status_code != 200:
                issues.append(f"API 서버 이상 (HTTP {response.status_code})")
        except:
            issues.append("API 서버 연결 불가")
        
        # 데이터베이스 확인
        try:
            import psycopg2
            conn = psycopg2.connect(
                host="localhost", database="stockpilot", 
                user="stockpilot", password="password"
            )
            conn.close()
        except:
            issues.append("데이터베이스 연결 실패")
        
        # 메모리 사용량 확인
        import psutil
        memory_percent = psutil.virtual_memory().percent
        if memory_percent > 90:
            issues.append(f"메모리 사용률 위험 ({memory_percent}%)")
        elif memory_percent > 80:
            issues.append(f"메모리 사용률 주의 ({memory_percent}%)")
        
        # 디스크 사용량 확인
        disk_percent = psutil.disk_usage('/').percent
        if disk_percent > 90:
            issues.append(f"디스크 사용률 위험 ({disk_percent}%)")
        
        # 알림 발송
        if issues:
            priority = "critical" if any("위험" in issue for issue in issues) else "high"
            message = "\n".join(issues)
            self.alert_manager.trigger_alert("시스템 헬스체크", message, priority)
        
        return len(issues) == 0

if __name__ == "__main__":
    monitor = SystemMonitor()
    monitor.check_system_health()
```

### 장애 대응 체크리스트

#### 📋 Level 1: 경고 (Warning)
```
□ 시스템 리소스 사용량 70% 이상
□ API 응답시간 2초 이상
□ 에러율 5% 이상
□ 데이터베이스 연결 수 80% 이상

대응 절차:
1. 모니터링 대시보드 확인
2. 로그 파일 점검
3. 리소스 사용량 최적화
4. 15분 후 재점검
```

#### 🚨 Level 2: 심각 (Critical)
```
□ 시스템 리소스 사용량 90% 이상
□ API 서비스 중단
□ 데이터베이스 연결 실패
□ 대량의 5xx 에러 발생

대응 절차:
1. 즉시 담당자 호출
2. 서비스 상태 점검
3. 긴급 복구 스크립트 실행
4. 백업 시스템으로 전환 고려
5. 사용자 공지 준비
```

#### 🔥 Level 3: 재해 (Disaster)
```
□ 전체 시스템 다운
□ 데이터 손상 의심
□ 보안 침해 의심
□ 복구 불가능한 장애

대응 절차:
1. 전체 팀 소집
2. 사용자 서비스 중단 공지
3. 백업에서 완전 복구
4. 보안 점검 실시
5. 근본 원인 분석
6. 재발 방지책 수립
```

---

*이 운영 매뉴얼은 StockPilot 시스템의 안정적 운영을 위한 종합 가이드입니다. 정기적으로 업데이트하고 실제 운영 환경에 맞게 조정하여 사용하시기 바랍니다.*

**📞 긴급 연락처:**
- 시스템 관리자: admin@stockpilot.ai
- 기술 지원: support@stockpilot.ai  
- 24시간 핫라인: 02-1234-5678