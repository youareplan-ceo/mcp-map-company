#!/bin/bash
# StockPilot 다중 프로바이더 페일오버 시스템 설정 스크립트

set -euo pipefail

# 컬러 출력 설정
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

BACKEND_DIR="/Users/youareplan/stockpilot-ai/backend"
LOG_DIR="/var/log/stockpilot"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}StockPilot 다중 프로바이더 페일오버 시스템 설정${NC}"
echo -e "${BLUE}================================================${NC}"

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
    pip install -q aiohttp
    
    echo -e "${GREEN}✓ 의존성 설치 완료${NC}"
}

# 프로바이더 설정 파일 생성
create_provider_config() {
    echo -e "${YELLOW}프로바이더 설정 파일 생성 중...${NC}"
    
    cat > "$BACKEND_DIR/config/provider_config.json" << 'EOF'
{
  "providers": {
    "yahoo_finance": {
      "enabled": true,
      "api_key": null,
      "rate_limit": 200,
      "timeout": 10,
      "priority": 1,
      "data_types": ["market_data"]
    },
    "alpha_vantage": {
      "enabled": true,
      "api_key": "YOUR_ALPHA_VANTAGE_API_KEY",
      "rate_limit": 5,
      "timeout": 15,
      "priority": 2,
      "data_types": ["market_data", "financial_reports"]
    },
    "reuters_news": {
      "enabled": true,
      "api_key": null,
      "rate_limit": 50,
      "timeout": 12,
      "priority": 1,
      "data_types": ["news"]
    },
    "newsapi": {
      "enabled": true,
      "api_key": "YOUR_NEWSAPI_KEY",
      "rate_limit": 100,
      "timeout": 10,
      "priority": 2,
      "data_types": ["news"]
    },
    "fred_economic": {
      "enabled": true,
      "api_key": "YOUR_FRED_API_KEY",
      "rate_limit": 120,
      "timeout": 8,
      "priority": 1,
      "data_types": ["economic_data"]
    },
    "krx_data": {
      "enabled": true,
      "api_key": null,
      "rate_limit": 30,
      "timeout": 15,
      "priority": 1,
      "data_types": ["market_data"]
    },
    "dart_api": {
      "enabled": true,
      "api_key": "YOUR_DART_API_KEY",
      "rate_limit": 10,
      "timeout": 20,
      "priority": 1,
      "data_types": ["financial_reports"]
    }
  },
  "failover": {
    "circuit_breaker": {
      "failure_threshold": 5,
      "recovery_timeout": 300,
      "half_open_retry_count": 3
    },
    "cache": {
      "default_ttl": 300,
      "max_entries": 1000,
      "cleanup_interval": 3600
    },
    "health_check": {
      "interval": 300,
      "timeout": 30,
      "enabled": true
    }
  }
}
EOF
    
    echo -e "${GREEN}✓ 프로바이더 설정 파일 생성 완료${NC}"
    echo -e "${YELLOW}참고: config/provider_config.json에서 실제 API 키를 설정해주세요${NC}"
}

# 페일오버 서비스 데몬 생성
create_failover_service() {
    echo -e "${YELLOW}페일오버 서비스 데몬 생성 중...${NC}"
    
    cat > "$BACKEND_DIR/failover_daemon.py" << 'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
StockPilot 다중 프로바이더 페일오버 데몬
"""

import asyncio
import signal
import logging
import json
from pathlib import Path
from services.multi_provider_failover import MultiProviderFailover, DataSourceType, DataRequest

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/stockpilot/failover_daemon.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FailoverDaemon:
    def __init__(self):
        self.failover = None
        self.running = False
        
    async def start(self):
        """데몬 시작"""
        logger.info("StockPilot 페일오버 데몬 시작")
        
        try:
            # 설정 로드
            config_path = Path(__file__).parent / 'config' / 'provider_config.json'
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    logger.info("설정 파일 로드 완료")
            else:
                config = {}
                logger.warning("설정 파일이 없습니다. 기본 설정 사용")
            
            # 페일오버 시스템 초기화
            self.failover = MultiProviderFailover(config)
            
            # 백그라운드 작업 시작
            await self.failover.start_background_tasks()
            
            # 초기 헬스 체크
            await self.failover.health_check_all_providers()
            
            self.running = True
            logger.info("페일오버 데몬 시작 완료")
            
            # 데몬 루프
            while self.running:
                await asyncio.sleep(60)  # 1분마다 상태 체크
                
                # 프로바이더 상태 로그
                status_report = self.failover.get_provider_status()
                active_providers = sum(1 for status in status_report.values() 
                                     if status['status'] == 'active')
                total_providers = len(status_report)
                
                logger.info(f"프로바이더 상태: {active_providers}/{total_providers} 활성")
                
        except Exception as e:
            logger.error(f"데몬 실행 중 오류: {str(e)}")
            raise
        finally:
            await self.stop()
    
    async def stop(self):
        """데몬 중단"""
        logger.info("페일오버 데몬 중단 중...")
        self.running = False
        
        if self.failover:
            await self.failover.stop_background_tasks()
        
        logger.info("페일오버 데몬 중단 완료")
    
    def signal_handler(self, signum, frame):
        """시그널 핸들러"""
        logger.info(f"시그널 수신: {signum}")
        asyncio.create_task(self.stop())

async def main():
    daemon = FailoverDaemon()
    
    # 시그널 핸들러 설정
    signal.signal(signal.SIGTERM, daemon.signal_handler)
    signal.signal(signal.SIGINT, daemon.signal_handler)
    
    try:
        await daemon.start()
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"데몬 오류: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
EOF
    
    chmod +x "$BACKEND_DIR/failover_daemon.py"
    
    echo -e "${GREEN}✓ 페일오버 서비스 데몬 생성 완료${NC}"
}

# API 통합 래퍼 생성
create_api_wrapper() {
    echo -e "${YELLOW}API 통합 래퍼 생성 중...${NC}"
    
    cat > "$BACKEND_DIR/services/data_api_wrapper.py" << 'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
StockPilot 통합 데이터 API 래퍼
다중 프로바이더 페일오버를 활용한 데이터 조회 인터페이스
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from .multi_provider_failover import (
    MultiProviderFailover, DataSourceType, DataRequest, DataResponse
)

logger = logging.getLogger(__name__)

class StockPilotDataAPI:
    """StockPilot 통합 데이터 API"""
    
    def __init__(self):
        self.failover = MultiProviderFailover()
        self._initialized = False
    
    async def initialize(self):
        """API 초기화"""
        if not self._initialized:
            await self.failover.start_background_tasks()
            self._initialized = True
            logger.info("StockPilot 데이터 API 초기화 완료")
    
    async def get_stock_data(self, symbol: str, interval: str = "1d", 
                           period: str = "1mo", realtime: bool = False) -> Optional[Dict]:
        """주식 데이터 조회"""
        request = DataRequest(
            data_type=DataSourceType.MARKET_DATA,
            symbol=symbol,
            parameters={
                "interval": interval,
                "period": period
            },
            require_realtime=realtime
        )
        
        response = await self.failover.get_data(request)
        return response.data if response else None
    
    async def get_news(self, symbol: str, limit: int = 20) -> Optional[List[Dict]]:
        """뉴스 데이터 조회"""
        request = DataRequest(
            data_type=DataSourceType.NEWS,
            symbol=symbol,
            parameters={"limit": limit}
        )
        
        response = await self.failover.get_data(request)
        if response and response.data:
            return response.data.get('articles', [])
        return []
    
    async def get_financial_reports(self, symbol: str, year: str = "2024") -> Optional[Dict]:
        """재무 보고서 데이터 조회"""
        request = DataRequest(
            data_type=DataSourceType.FINANCIAL_REPORTS,
            symbol=symbol,
            parameters={"year": year}
        )
        
        response = await self.failover.get_data(request)
        return response.data if response else None
    
    async def get_economic_data(self, series_id: str) -> Optional[Dict]:
        """경제 데이터 조회"""
        request = DataRequest(
            data_type=DataSourceType.ECONOMIC_DATA,
            symbol=series_id,
            parameters={}
        )
        
        response = await self.failover.get_data(request)
        return response.data if response else None
    
    async def get_multiple_stocks(self, symbols: List[str], 
                                interval: str = "1d") -> Dict[str, Optional[Dict]]:
        """다중 주식 데이터 조회"""
        tasks = []
        for symbol in symbols:
            task = self.get_stock_data(symbol, interval=interval)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            symbol: result if not isinstance(result, Exception) else None
            for symbol, result in zip(symbols, results)
        }
    
    def get_provider_status(self) -> Dict[str, Dict]:
        """프로바이더 상태 조회"""
        return self.failover.get_provider_status()
    
    async def health_check(self) -> Dict[str, bool]:
        """헬스 체크 실행"""
        results = await self.failover.health_check_all_providers()
        
        return {
            provider.name: result 
            for provider, result in zip(self.failover.providers, results)
        }
    
    async def cleanup(self):
        """리소스 정리"""
        if self._initialized:
            await self.failover.stop_background_tasks()
            self._initialized = False
            logger.info("StockPilot 데이터 API 정리 완료")

# 전역 인스턴스
data_api = StockPilotDataAPI()

# 편의 함수들
async def get_stock_data(symbol: str, **kwargs) -> Optional[Dict]:
    """주식 데이터 조회 편의 함수"""
    await data_api.initialize()
    return await data_api.get_stock_data(symbol, **kwargs)

async def get_news(symbol: str, limit: int = 20) -> List[Dict]:
    """뉴스 조회 편의 함수"""
    await data_api.initialize()
    result = await data_api.get_news(symbol, limit)
    return result or []

async def get_provider_status() -> Dict[str, Dict]:
    """프로바이더 상태 조회 편의 함수"""
    await data_api.initialize()
    return data_api.get_provider_status()
EOF
    
    echo -e "${GREEN}✓ API 통합 래퍼 생성 완료${NC}"
}

# 모니터링 대시보드 생성
create_monitoring_dashboard() {
    echo -e "${YELLOW}프로바이더 모니터링 대시보드 생성 중...${NC}"
    
    cat > "$BACKEND_DIR/provider_monitor.py" << 'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
StockPilot 프로바이더 모니터링 대시보드
"""

import asyncio
import json
from datetime import datetime
from services.multi_provider_failover import MultiProviderFailover

class ProviderMonitor:
    def __init__(self):
        self.failover = MultiProviderFailover()
    
    async def display_status(self):
        """프로바이더 상태 표시"""
        await self.failover.start_background_tasks()
        
        try:
            while True:
                # 화면 클리어
                print("\033[2J\033[H", end="")
                
                print("=" * 80)
                print("StockPilot 다중 프로바이더 페일오버 시스템 모니터")
                print("=" * 80)
                print(f"업데이트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print()
                
                # 프로바이더 상태 조회
                status_report = self.failover.get_provider_status()
                
                # 상태별 색상
                status_colors = {
                    'active': '\033[92m',      # 녹색
                    'degraded': '\033[93m',    # 노란색
                    'failed': '\033[91m',      # 빨간색
                    'maintenance': '\033[94m'  # 파란색
                }
                reset_color = '\033[0m'
                
                # 프로바이더별 상태 표시
                for provider_name, status in status_report.items():
                    color = status_colors.get(status['status'], '')
                    
                    print(f"{color}● {provider_name:<20}{reset_color}", end="")
                    print(f" 상태: {status['status']:<10}", end="")
                    print(f" 가동율: {status['uptime_percentage']:>6.1f}%", end="")
                    print(f" 성공/실패: {status['success_count']:>4}/{status['failure_count']:<4}", end="")
                    print(f" 응답시간: {status['avg_response_time']:>6.1f}ms", end="")
                    print(f" 품질: {status['quality_score']:>4.2f}")
                
                # 전체 요약
                total_providers = len(status_report)
                active_providers = sum(1 for s in status_report.values() if s['status'] == 'active')
                degraded_providers = sum(1 for s in status_report.values() if s['status'] == 'degraded')
                failed_providers = sum(1 for s in status_report.values() if s['status'] == 'failed')
                
                print("\n" + "-" * 80)
                print(f"전체 요약: 활성 {active_providers}, 저하 {degraded_providers}, 실패 {failed_providers} / 총 {total_providers}")
                
                # 평균 메트릭
                avg_uptime = sum(s['uptime_percentage'] for s in status_report.values()) / len(status_report)
                avg_response_time = sum(s['avg_response_time'] for s in status_report.values()) / len(status_report)
                
                print(f"평균 가동율: {avg_uptime:.1f}%, 평균 응답시간: {avg_response_time:.1f}ms")
                print("\n[Ctrl+C로 종료]")
                
                # 10초 대기
                await asyncio.sleep(10)
                
        except KeyboardInterrupt:
            print(f"\n{reset_color}모니터링 종료")
        finally:
            await self.failover.stop_background_tasks()

async def main():
    monitor = ProviderMonitor()
    await monitor.display_status()

if __name__ == "__main__":
    asyncio.run(main())
EOF
    
    chmod +x "$BACKEND_DIR/provider_monitor.py"
    
    echo -e "${GREEN}✓ 모니터링 대시보드 생성 완료${NC}"
}

# 테스트 스크립트 생성
create_test_scripts() {
    echo -e "${YELLOW}테스트 스크립트 생성 중...${NC}"
    
    cat > "$BACKEND_DIR/test_failover.py" << 'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
다중 프로바이더 페일오버 시스템 테스트 스크립트
"""

import asyncio
import logging
from services.data_api_wrapper import StockPilotDataAPI

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_failover_system():
    """페일오버 시스템 종합 테스트"""
    print("=" * 60)
    print("StockPilot 다중 프로바이더 페일오버 시스템 테스트")
    print("=" * 60)
    
    api = StockPilotDataAPI()
    await api.initialize()
    
    try:
        # 1. 단일 주식 데이터 테스트
        print("\n1. 단일 주식 데이터 테스트")
        print("-" * 30)
        
        symbols = ["AAPL", "MSFT", "GOOGL", "005930"]  # 삼성전자 포함
        
        for symbol in symbols:
            print(f"테스트 중: {symbol}")
            data = await api.get_stock_data(symbol)
            
            if data:
                print(f"  ✓ 성공: {data.get('source', 'unknown')} 프로바이더")
            else:
                print(f"  ✗ 실패")
        
        # 2. 다중 주식 데이터 테스트
        print("\n2. 다중 주식 데이터 테스트")
        print("-" * 30)
        
        multi_symbols = ["AAPL", "TSLA", "NVDA"]
        results = await api.get_multiple_stocks(multi_symbols)
        
        for symbol, data in results.items():
            if data:
                print(f"  ✓ {symbol}: 성공")
            else:
                print(f"  ✗ {symbol}: 실패")
        
        # 3. 뉴스 데이터 테스트
        print("\n3. 뉴스 데이터 테스트")
        print("-" * 30)
        
        news = await api.get_news("AAPL", limit=5)
        if news:
            print(f"  ✓ 뉴스 {len(news)}개 조회 성공")
            for article in news[:2]:
                print(f"    - {article.get('title', 'No title')}")
        else:
            print("  ✗ 뉴스 조회 실패")
        
        # 4. 프로바이더 상태 확인
        print("\n4. 프로바이더 상태 확인")
        print("-" * 30)
        
        status = api.get_provider_status()
        for provider_name, provider_status in status.items():
            status_emoji = {
                'active': '🟢',
                'degraded': '🟡', 
                'failed': '🔴',
                'maintenance': '🔧'
            }.get(provider_status['status'], '⚪')
            
            print(f"  {status_emoji} {provider_name}: {provider_status['status']} "
                  f"(가동율: {provider_status['uptime_percentage']:.1f}%)")
        
        # 5. 헬스 체크 테스트
        print("\n5. 헬스 체크 테스트")
        print("-" * 30)
        
        health_results = await api.health_check()
        healthy_count = sum(1 for result in health_results.values() if result)
        total_count = len(health_results)
        
        print(f"  헬스 체크 결과: {healthy_count}/{total_count} 프로바이더 정상")
        
        for provider, is_healthy in health_results.items():
            status = "✓ 정상" if is_healthy else "✗ 이상"
            print(f"    {provider}: {status}")
        
        print("\n" + "=" * 60)
        print("페일오버 시스템 테스트 완료")
        print("=" * 60)
        
    finally:
        await api.cleanup()

if __name__ == "__main__":
    asyncio.run(test_failover_system())
EOF
    
    chmod +x "$BACKEND_DIR/test_failover.py"
    
    echo -e "${GREEN}✓ 테스트 스크립트 생성 완료${NC}"
}

# systemd 서비스 파일 생성
create_systemd_service() {
    echo -e "${YELLOW}systemd 서비스 파일 생성 중...${NC}"
    
    mkdir -p "$BACKEND_DIR/../systemd"
    
    cat > "$BACKEND_DIR/../systemd/stockpilot-failover.service" << EOF
[Unit]
Description=StockPilot Multi-Provider Failover Service
Documentation=https://stockpilot.ai/docs/failover
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=stockpilot
Group=stockpilot
WorkingDirectory=$BACKEND_DIR
Environment=PATH=$BACKEND_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=$BACKEND_DIR
Environment=LOG_LEVEL=INFO
EnvironmentFile=-/opt/stockpilot/.env.production
ExecStart=$BACKEND_DIR/venv/bin/python $BACKEND_DIR/failover_daemon.py
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=stockpilot-failover

# 보안 강화 설정
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/stockpilot /tmp /opt/stockpilot/data
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictRealtime=true
RestrictSUIDSGID=true
MemoryDenyWriteExecute=true
SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM

# 리소스 제한
MemoryMax=2G
CPUQuota=100%
TasksMax=500

[Install]
WantedBy=multi-user.target
EOF
    
    echo -e "${GREEN}✓ systemd 서비스 파일 생성 완료${NC}"
}

# 설정 완료 메시지
show_completion_message() {
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}StockPilot 다중 프로바이더 페일오버 시스템 설정 완료!${NC}"
    echo -e "${GREEN}================================================${NC}"
    
    echo -e "${BLUE}생성된 구성 요소:${NC}"
    echo -e "  ✓ 다중 프로바이더 페일오버 엔진"
    echo -e "  ✓ 회로 차단기 및 Rate Limiting"
    echo -e "  ✓ 자동 헬스 체크 시스템"
    echo -e "  ✓ 데이터 캐싱 메커니즘"
    echo -e "  ✓ 통합 API 래퍼"
    echo -e "  ✓ 실시간 모니터링 대시보드"
    echo -e "  ✓ systemd 서비스 설정"
    
    echo -e "\n${BLUE}지원하는 프로바이더:${NC}"
    echo -e "  📈 시장 데이터: Yahoo Finance, Alpha Vantage, KRX"
    echo -e "  📰 뉴스 데이터: Reuters, NewsAPI"
    echo -e "  📊 경제 데이터: FRED"
    echo -e "  📋 재무 데이터: Alpha Vantage, DART API"
    
    echo -e "\n${BLUE}유용한 명령어:${NC}"
    echo -e "  페일오버 시스템 테스트:"
    echo -e "    cd $BACKEND_DIR && source venv/bin/activate && python test_failover.py"
    
    echo -e "\n  실시간 모니터링:"
    echo -e "    cd $BACKEND_DIR && source venv/bin/activate && python provider_monitor.py"
    
    echo -e "\n  다중 프로바이더 데이터 조회 (Python):"
    echo -e "    from services.data_api_wrapper import get_stock_data, get_news"
    echo -e "    data = await get_stock_data('AAPL')"
    echo -e "    news = await get_news('TSLA', limit=10)"
    
    echo -e "\n  페일오버 데몬 시작:"
    echo -e "    cd $BACKEND_DIR && source venv/bin/activate && python failover_daemon.py"
    
    echo -e "\n${BLUE}파일 위치:${NC}"
    echo -e "  페일오버 엔진: $BACKEND_DIR/services/multi_provider_failover.py"
    echo -e "  API 래퍼: $BACKEND_DIR/services/data_api_wrapper.py"
    echo -e "  설정 파일: $BACKEND_DIR/config/provider_config.json"
    echo -e "  로그 파일: $LOG_DIR/multi_provider.log"
    echo -e "  systemd 서비스: ../systemd/stockpilot-failover.service"
    
    echo -e "\n${YELLOW}다음 단계:${NC}"
    echo -e "  1. config/provider_config.json에서 실제 API 키 설정"
    echo -e "  2. 페일오버 시스템 테스트 실행"
    echo -e "  3. 프로덕션 환경에서 systemd 서비스 등록"
    echo -e "  4. 모니터링 대시보드로 프로바이더 상태 확인"
    
    echo -e "\n${BLUE}페일오버 특징:${NC}"
    echo -e "  🔄 자동 프로바이더 전환"
    echo -e "  ⚡ 지능형 우선순위 기반 라우팅"
    echo -e "  🛡️ 회로 차단기 패턴"
    echo -e "  ⏱️ Rate Limiting 및 백프레셔 제어"
    echo -e "  📊 실시간 품질 점수 기반 선택"
    echo -e "  💾 스마트 캐싱 시스템"
    echo -e "  🔍 자동 헬스 체크 및 복구"
}

# 메인 실행 함수
main() {
    echo -e "${BLUE}StockPilot 다중 프로바이더 페일오버 시스템을 설정합니다...${NC}"
    
    # 설정 디렉토리 생성
    mkdir -p "$BACKEND_DIR/config"
    mkdir -p "$LOG_DIR"
    
    install_dependencies
    create_provider_config
    create_failover_service
    create_api_wrapper
    create_monitoring_dashboard
    create_test_scripts
    create_systemd_service
    
    show_completion_message
}

# 스크립트 실행
main "$@"