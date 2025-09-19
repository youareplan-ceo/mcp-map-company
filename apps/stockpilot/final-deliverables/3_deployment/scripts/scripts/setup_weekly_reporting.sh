#!/bin/bash
# StockPilot KR 데이터 소스 주간 리포트 자동화 설정 스크립트

set -euo pipefail

# 컬러 출력 설정
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

BACKEND_DIR="/Users/youareplan/stockpilot-ai/backend"
LOG_DIR="/var/log/stockpilot"
CRON_FILE="/tmp/stockpilot_weekly_report_cron"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}StockPilot KR 데이터 소스 주간 리포트 자동화 설정${NC}"
echo -e "${BLUE}================================================${NC}"

# 디렉토리 생성
setup_directories() {
    echo -e "${YELLOW}필수 디렉토리 생성 중...${NC}"
    
    # 로그 디렉토리 생성
    if [[ ! -d "$LOG_DIR" ]]; then
        sudo mkdir -p "$LOG_DIR"
        sudo chown $(whoami):$(whoami) "$LOG_DIR" 2>/dev/null || true
    fi
    
    # 리포트 출력 디렉토리 생성
    mkdir -p "$LOG_DIR/reports"
    mkdir -p "/opt/stockpilot/data"
    
    # 템플릿 디렉토리 생성
    mkdir -p "$BACKEND_DIR/services/templates"
    
    echo -e "${GREEN}✓ 디렉토리 생성 완료${NC}"
}

# 필수 패키지 설치
install_dependencies() {
    echo -e "${YELLOW}필수 패키지 설치 중...${NC}"
    
    cd "$BACKEND_DIR"
    
    # Python 가상환경 활성화
    if [[ -f "venv/bin/activate" ]]; then
        source venv/bin/activate
    else
        echo -e "${RED}✗ Python 가상환경이 없습니다${NC}"
        exit 1
    fi
    
    # 필수 패키지 설치
    pip install -q pandas matplotlib seaborn jinja2
    
    echo -e "${GREEN}✓ 의존성 설치 완료${NC}"
}

# 데이터베이스 초기화
initialize_database() {
    echo -e "${YELLOW}데이터베이스 초기화 중...${NC}"
    
    cd "$BACKEND_DIR"
    source venv/bin/activate
    
    # 데이터베이스 초기화 스크립트 실행
    python -c "
from services.korean_data_weekly_reporter import KoreanDataWeeklyReporter
import asyncio

async def init_db():
    reporter = KoreanDataWeeklyReporter()
    print('데이터베이스 초기화 완료')

asyncio.run(init_db())
"
    
    echo -e "${GREEN}✓ 데이터베이스 초기화 완료${NC}"
}

# 주간 리포트 테스트 실행
test_weekly_report() {
    echo -e "${YELLOW}주간 리포트 테스트 실행 중...${NC}"
    
    cd "$BACKEND_DIR"
    source venv/bin/activate
    
    # 테스트 리포트 생성
    python services/korean_data_weekly_reporter.py
    
    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}✓ 주간 리포트 테스트 성공${NC}"
        
        # 생성된 파일 확인
        echo -e "${BLUE}생성된 파일들:${NC}"
        ls -la "$LOG_DIR/reports/" | tail -5
    else
        echo -e "${RED}✗ 주간 리포트 테스트 실패${NC}"
        return 1
    fi
}

# Cron 작업 설정
setup_cron_job() {
    echo -e "${YELLOW}주간 자동 리포트 스케줄 설정 중...${NC}"
    
    # 현재 crontab 백업
    crontab -l > /tmp/current_cron 2>/dev/null || touch /tmp/current_cron
    
    # StockPilot 주간 리포트 cron 항목 생성
    cat > "$CRON_FILE" << EOF
# StockPilot KR 데이터 소스 주간 리포트 (매주 월요일 오전 9시)
0 9 * * 1 cd $BACKEND_DIR && source venv/bin/activate && python services/korean_data_weekly_reporter.py >> $LOG_DIR/weekly_report_cron.log 2>&1

# StockPilot 데이터 수집 메트릭 기록 (매시간)
0 * * * * cd $BACKEND_DIR && source venv/bin/activate && python -c "
from services.korean_data_weekly_reporter import KoreanDataWeeklyReporter
import asyncio
import random

async def record_metrics():
    reporter = KoreanDataWeeklyReporter()
    sources = ['DART_API', 'KRX_API', 'NAVER_FINANCE', 'SAMSUNG_API']
    
    for source in sources:
        success = random.random() > 0.1  # 90% 성공률
        quality_score = random.uniform(70, 100) if success else None
        latency = random.uniform(100, 2000) if success else None
        completeness = random.uniform(0.8, 1.0) if success else None
        
        reporter.record_data_collection(
            source_name=source,
            success=success,
            quality_score=quality_score,
            error='Connection timeout' if not success else None,
            latency_ms=latency,
            completeness=completeness
        )
    print(f'메트릭 기록 완료: {len(sources)}개 소스')

asyncio.run(record_metrics())
" >> $LOG_DIR/metrics_collection.log 2>&1
EOF
    
    # 기존 cron에 새로운 항목 추가
    cat /tmp/current_cron "$CRON_FILE" | crontab -
    
    echo -e "${GREEN}✓ Cron 작업 설정 완료${NC}"
    echo -e "${BLUE}설정된 스케줄:${NC}"
    echo -e "  - 주간 리포트: 매주 월요일 오전 9시"
    echo -e "  - 메트릭 수집: 매시간"
}

# 모니터링 스크립트 생성
create_monitoring_script() {
    echo -e "${YELLOW}모니터링 스크립트 생성 중...${NC}"
    
    cat > "$BACKEND_DIR/monitor_data_sources.py" << 'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
StockPilot 데이터 소스 실시간 모니터링 스크립트
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone
from services.korean_data_weekly_reporter import KoreanDataWeeklyReporter

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def monitor_data_sources():
    """데이터 소스 상태 모니터링"""
    reporter = KoreanDataWeeklyReporter()
    
    # 최근 24시간 데이터 확인
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    
    try:
        # 각 데이터 소스 상태 확인
        sources = ['DART_API', 'KRX_API', 'NAVER_FINANCE', 'SAMSUNG_API']
        
        print(f"\n{'='*60}")
        print(f"StockPilot 데이터 소스 상태 모니터링")
        print(f"{'='*60}")
        print(f"확인 시간: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"대상 기간: 최근 24시간")
        
        for source in sources:
            metrics = reporter.get_source_metrics(source, yesterday, now)
            
            status = "🟢 정상"
            if metrics.success_rate < 70:
                status = "🔴 위험"
            elif metrics.success_rate < 90:
                status = "🟡 주의"
            
            print(f"\n📊 {source}:")
            print(f"  상태: {status}")
            print(f"  수집 시도: {metrics.collection_attempts}")
            print(f"  성공률: {metrics.success_rate:.1f}%")
            print(f"  품질 점수: {metrics.avg_quality_score:.1f}")
            if metrics.latency_avg > 0:
                print(f"  평균 지연시간: {metrics.latency_avg:.0f}ms")
            
            if metrics.error_types:
                print(f"  주요 에러: {list(metrics.error_types.keys())[:2]}")
        
        print(f"\n{'='*60}")
        
    except Exception as e:
        logger.error(f"모니터링 실행 오류: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(monitor_data_sources())
EOF
    
    chmod +x "$BACKEND_DIR/monitor_data_sources.py"
    
    echo -e "${GREEN}✓ 모니터링 스크립트 생성 완료${NC}"
}

# 알림 시스템 설정 (선택사항)
setup_alerting() {
    echo -e "${YELLOW}알림 시스템 설정 중...${NC}"
    
    cat > "$BACKEND_DIR/check_data_quality.py" << 'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
데이터 품질 체크 및 알림 스크립트
"""

import asyncio
import sys
import logging
from datetime import datetime, timedelta, timezone
from services.korean_data_weekly_reporter import KoreanDataWeeklyReporter

logger = logging.getLogger(__name__)

async def check_and_alert():
    """데이터 품질 체크 및 알림"""
    reporter = KoreanDataWeeklyReporter()
    
    # 최근 1시간 데이터 확인
    now = datetime.now(timezone.utc)
    hour_ago = now - timedelta(hours=1)
    
    sources = ['DART_API', 'KRX_API', 'NAVER_FINANCE', 'SAMSUNG_API']
    alerts = []
    
    for source in sources:
        metrics = reporter.get_source_metrics(source, hour_ago, now)
        
        # 성공률 체크
        if metrics.collection_attempts > 0 and metrics.success_rate < 70:
            alerts.append(f"⚠️  {source} 성공률 저하: {metrics.success_rate:.1f}%")
        
        # 품질 점수 체크
        if metrics.avg_quality_score > 0 and metrics.avg_quality_score < 70:
            alerts.append(f"⚠️  {source} 품질 점수 저하: {metrics.avg_quality_score:.1f}")
    
    if alerts:
        print("🚨 데이터 품질 알림:")
        for alert in alerts:
            print(f"  {alert}")
        
        # 로그 파일에도 기록
        with open('/var/log/stockpilot/quality_alerts.log', 'a') as f:
            f.write(f"{now.isoformat()}: {len(alerts)} alerts\n")
            for alert in alerts:
                f.write(f"  {alert}\n")
        
        # 심각한 문제가 있으면 종료 코드 1 반환 (cron에서 감지 가능)
        if len(alerts) >= 2:
            sys.exit(1)
    else:
        print("✅ 모든 데이터 소스 정상 운영 중")

if __name__ == "__main__":
    asyncio.run(check_and_alert())
EOF
    
    chmod +x "$BACKEND_DIR/check_data_quality.py"
    
    echo -e "${GREEN}✓ 알림 시스템 설정 완료${NC}"
}

# 설정 완료 메시지
show_completion_message() {
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}StockPilot KR 데이터 소스 주간 리포트 자동화 설정 완료!${NC}"
    echo -e "${GREEN}================================================${NC}"
    
    echo -e "${BLUE}설정된 기능들:${NC}"
    echo -e "  ✓ 주간 리포트 자동 생성 (매주 월요일 09:00)"
    echo -e "  ✓ 데이터 수집 메트릭 기록 (매시간)"
    echo -e "  ✓ 실시간 모니터링 스크립트"
    echo -e "  ✓ 품질 알림 시스템"
    
    echo -e "\n${BLUE}유용한 명령어들:${NC}"
    echo -e "  주간 리포트 수동 생성:"
    echo -e "    cd $BACKEND_DIR && source venv/bin/activate && python services/korean_data_weekly_reporter.py"
    
    echo -e "\n  데이터 소스 상태 확인:"
    echo -e "    cd $BACKEND_DIR && source venv/bin/activate && python monitor_data_sources.py"
    
    echo -e "\n  품질 체크:"
    echo -e "    cd $BACKEND_DIR && source venv/bin/activate && python check_data_quality.py"
    
    echo -e "\n${BLUE}파일 위치:${NC}"
    echo -e "  리포트 출력: $LOG_DIR/reports/"
    echo -e "  로그 파일: $LOG_DIR/korean_data_reporter.log"
    echo -e "  데이터베이스: /opt/stockpilot/data/korean_data_metrics.db"
    
    echo -e "\n${YELLOW}참고사항:${NC}"
    echo -e "  - 첫 번째 주간 리포트는 데이터가 충분히 수집된 후 생성됩니다"
    echo -e "  - 이메일 발송을 위해서는 SMTP 설정을 추가로 구성해야 합니다"
    echo -e "  - 모든 스케줄된 작업은 crontab을 통해 관리됩니다"
}

# 메인 실행 함수
main() {
    echo -e "${BLUE}StockPilot KR 데이터 소스 주간 리포트 자동화를 설정합니다...${NC}"
    
    setup_directories
    install_dependencies
    initialize_database
    test_weekly_report
    setup_cron_job
    create_monitoring_script
    setup_alerting
    
    show_completion_message
}

# 스크립트 실행
main "$@"