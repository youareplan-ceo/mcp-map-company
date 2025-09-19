# 🚀 StockPilot AI 프로덕션 배포 가이드

## 📋 배포 전 체크리스트

### 1. 환경 설정 확인
- [ ] `.env.production` 파일 설정 완료
- [ ] SSL 인증서 준비 (Let's Encrypt 권장)
- [ ] 도메인 DNS 설정 완료
- [ ] 방화벽 규칙 설정 (80, 443 포트 오픈)

### 2. 보안 설정 확인
- [ ] 데이터베이스 비밀번호 강화
- [ ] Redis 비밀번호 설정
- [ ] JWT Secret Key 생성
- [ ] OpenAI API 키 보안 저장
- [ ] CORS Origins 프로덕션 도메인으로 제한

### 3. 인프라 준비
- [ ] 서버 리소스 확인 (최소 4GB RAM, 20GB 디스크)
- [ ] Docker & Docker Compose 설치
- [ ] 백업 전략 수립
- [ ] 모니터링 설정

---

## 🔧 배포 단계별 가이드

### Step 1: 서버 환경 준비

```bash
# 1. 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 2. Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 3. Docker Compose 설치
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 4. 방화벽 설정
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw --force enable
```

### Step 2: 프로젝트 배포

```bash
# 1. 프로젝트 클론
git clone https://github.com/your-org/stockpilot-ai.git
cd stockpilot-ai

# 2. 프로덕션 환경 변수 설정
cp .env.example .env.production
nano .env.production  # 환경 변수 편집

# 3. 데이터 디렉토리 생성
sudo mkdir -p /opt/stockpilot/data/{postgres,redis,prometheus,grafana}
sudo chown -R $USER:$USER /opt/stockpilot

# 4. SSL 인증서 설정 (Let's Encrypt)
sudo apt install certbot
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com
sudo cp /etc/letsencrypt/live/yourdomain.com/*.pem ./nginx/ssl/
```

### Step 3: 프로덕션 빌드 및 실행

```bash
# 1. 프로덕션 컨테이너 빌드
docker-compose -f docker-compose.production.yml build

# 2. 데이터베이스 초기화
docker-compose -f docker-compose.production.yml up -d postgres redis
sleep 30  # 데이터베이스 초기화 대기

# 3. 전체 서비스 시작
docker-compose -f docker-compose.production.yml up -d

# 4. 서비스 상태 확인
docker-compose -f docker-compose.production.yml ps
```

---

## 🔍 배포 후 검증

### 1. 서비스 상태 확인

```bash
# 컨테이너 상태 확인
docker ps

# 로그 확인
docker-compose -f docker-compose.production.yml logs -f backend
docker-compose -f docker-compose.production.yml logs -f frontend

# 헬스체크
curl http://localhost/health
curl http://localhost/api/v1/health
```

### 2. 기능 테스트

| 기능 | 엔드포인트 | 예상 결과 |
|------|------------|-----------|
| 프론트엔드 | `https://yourdomain.com` | React 앱 로드 |
| API 상태 | `https://yourdomain.com/api/v1/status` | JSON 응답 |
| WebSocket | `wss://yourdomain.com/ws` | 연결 성공 |
| 모니터링 | `https://yourdomain.com:3001` | Grafana 대시보드 |

### 3. 성능 및 보안 테스트

```bash
# SSL 등급 확인
curl -I https://yourdomain.com

# 보안 헤더 확인
curl -I https://yourdomain.com | grep -E "(X-Frame-Options|X-XSS-Protection|Content-Security-Policy)"

# 응답 시간 측정
curl -w "@curl-format.txt" -o /dev/null -s https://yourdomain.com/api/v1/status
```

---

## 📊 모니터링 및 알림 설정

### 1. Grafana 대시보드 접속
- URL: `https://yourdomain.com:3001`
- 기본 계정: 환경 변수에서 설정한 관리자 계정

### 2. 주요 모니터링 지표
- **시스템 리소스**: CPU, 메모리, 디스크 사용률
- **애플리케이션**: 응답 시간, 에러율, 처리량
- **데이터베이스**: 연결 수, 쿼리 성능
- **OpenAI API**: 사용량, 비용, 응답 시간

### 3. 알림 설정
```bash
# Slack 웹훅 설정 (Grafana)
# 1. Grafana → Alerting → Notification channels
# 2. Slack 웹훅 URL 입력
# 3. 임계값 설정:
#    - CPU 사용률 > 80%
#    - 메모리 사용률 > 90%
#    - API 에러율 > 5%
#    - 응답 시간 > 2초
```

---

## 🔄 배포 자동화 (CI/CD)

### GitHub Actions 워크플로우

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to server
        uses: appleboy/ssh-action@v0.1.5
        with:
          host: ${{ secrets.HOST }}
          username: ${{ secrets.USERNAME }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /opt/stockpilot-ai
            git pull origin main
            docker-compose -f docker-compose.production.yml build
            docker-compose -f docker-compose.production.yml up -d
            
      - name: Health check
        run: |
          sleep 60
          curl -f https://yourdomain.com/health || exit 1
```

---

## 🔐 보안 설정

### 1. 네트워크 보안
```bash
# 방화벽 강화 (UFW)
sudo ufw deny 5432  # PostgreSQL 외부 접근 차단
sudo ufw deny 6379  # Redis 외부 접근 차단
sudo ufw deny 9090  # Prometheus 외부 접근 차단

# fail2ban 설치 (brute force 공격 방지)
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

### 2. 컨테이너 보안
```yaml
# docker-compose.production.yml 보안 설정
security_opt:
  - no-new-privileges:true
read_only: true
cap_drop:
  - ALL
cap_add:
  - CHOWN
  - SETGID
  - SETUID
```

### 3. 정기 보안 업데이트
```bash
# 자동 보안 업데이트 설정
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

# Docker 이미지 정기 업데이트 (cron 작업)
0 2 * * 0 cd /opt/stockpilot-ai && docker-compose -f docker-compose.production.yml pull && docker-compose -f docker-compose.production.yml up -d
```

---

## 📂 백업 및 복구

### 1. 데이터베이스 백업
```bash
# 자동 백업 스크립트
#!/bin/bash
# /opt/stockpilot/scripts/backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/stockpilot/backups"

# PostgreSQL 백업
docker exec stockpilot_postgres_prod pg_dump -U $DB_USER $DB_NAME > $BACKUP_DIR/postgres_$DATE.sql

# Redis 백업
docker exec stockpilot_redis_prod redis-cli BGSAVE
docker cp stockpilot_redis_prod:/data/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# 7일 이상 된 백업 파일 삭제
find $BACKUP_DIR -type f -mtime +7 -delete

# S3 업로드 (선택사항)
# aws s3 cp $BACKUP_DIR s3://your-backup-bucket/stockpilot/ --recursive
```

### 2. 복구 절차
```bash
# 1. 서비스 중지
docker-compose -f docker-compose.production.yml down

# 2. 데이터베이스 복구
docker-compose -f docker-compose.production.yml up -d postgres
docker exec -i stockpilot_postgres_prod psql -U $DB_USER $DB_NAME < backup_file.sql

# 3. 서비스 재시작
docker-compose -f docker-compose.production.yml up -d
```

---

## 🎯 성능 최적화

### 1. 데이터베이스 최적화
```sql
-- PostgreSQL 인덱스 최적화
CREATE INDEX CONCURRENTLY idx_stocks_symbol ON stocks(symbol);
CREATE INDEX CONCURRENTLY idx_signals_created_at ON signals(created_at);
CREATE INDEX CONCURRENTLY idx_usage_stats_date ON usage_stats(date);

-- 연결 풀 설정
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
```

### 2. Redis 최적화
```bash
# Redis 메모리 최적화
redis-cli CONFIG SET maxmemory 512mb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### 3. Nginx 캐싱
```nginx
# Nginx 캐시 설정
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

---

## 🚨 트러블슈팅

### 일반적인 문제들

| 문제 | 원인 | 해결책 |
|------|------|--------|
| 컨테이너 시작 실패 | 포트 충돌 | `sudo netstat -tulpn \| grep :8000` |
| 데이터베이스 연결 실패 | 비밀번호/네트워크 | 환경 변수 및 네트워크 설정 확인 |
| SSL 인증서 오류 | 인증서 만료/설정 | `sudo certbot renew` |
| 높은 메모리 사용량 | 메모리 누수 | 컨테이너 재시작, 로그 분석 |

### 로그 분석
```bash
# 실시간 로그 모니터링
docker-compose -f docker-compose.production.yml logs -f --tail=100

# 에러 로그 필터링
docker-compose -f docker-compose.production.yml logs | grep ERROR

# 특정 서비스 로그
docker logs stockpilot_backend_prod
```

---

## 📞 지원 및 연락처

- **기술 지원**: support@stockpilot.ai
- **문서**: https://docs.stockpilot.ai
- **GitHub**: https://github.com/your-org/stockpilot-ai
- **모니터링 대시보드**: https://yourdomain.com:3001

---

**배포 성공을 위한 핵심 포인트:**
1. ✅ 충분한 서버 리소스 확보
2. ✅ 보안 설정 철저히 점검
3. ✅ 백업 전략 수립 및 테스트
4. ✅ 모니터링 및 알림 설정
5. ✅ 정기적인 업데이트 및 유지보수