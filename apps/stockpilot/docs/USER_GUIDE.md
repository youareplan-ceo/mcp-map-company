# 📊 StockPilot 사용자 가이드

> AI 기반 주식 투자 분석 및 의사결정 지원 시스템

## 📋 목차

- [시작하기](#시작하기)
- [주요 기능](#주요-기능)
- [웹 인터페이스 사용법](#웹-인터페이스-사용법)
- [API 사용 가이드](#api-사용-가이드)
- [투자 스타일 설정](#투자-스타일-설정)
- [포트폴리오 관리](#포트폴리오-관리)
- [실시간 알림 설정](#실시간-알림-설정)
- [고급 기능](#고급-기능)
- [문제 해결](#문제-해결)

---

## 🚀 시작하기

### 1. 시스템 요구사항

**최소 요구사항:**
- CPU: 2코어 이상
- RAM: 4GB 이상
- 저장공간: 10GB 이상
- 네트워크: 안정적인 인터넷 연결

**권장 요구사항:**
- CPU: 4코어 이상
- RAM: 8GB 이상
- 저장공간: 20GB 이상
- 네트워크: 광대역 인터넷 연결

### 2. 지원 브라우저

- **Chrome** 90+ (권장)
- **Firefox** 88+
- **Safari** 14+
- **Edge** 90+

### 3. 첫 번째 접속

1. 웹 브라우저에서 `http://localhost:3000` 접속
2. 초기 설정 마법사 진행
3. API 키 설정 (선택사항)
4. 투자 성향 설정

---

## 🎯 주요 기능

### 📈 실시간 주식 분석
- **실시간 주가 모니터링**: WebSocket 기반 실시간 데이터
- **AI 분석 리포트**: GPT 기반 종합 분석
- **기술적 분석**: 차트 패턴 및 지표 분석
- **기본적 분석**: 재무제표 및 기업 가치 평가

### 🧠 AI 투자 추천
- **개인화된 추천**: 사용자 성향 기반 맞춤 추천
- **리스크 분석**: 포트폴리오 위험도 평가
- **수익률 예측**: 머신러닝 기반 수익률 예측
- **시장 트렌드 분석**: 거시경제 및 섹터 분석

### 📰 뉴스 감정 분석
- **실시간 뉴스 수집**: 다양한 금융 뉴스 소스
- **감정 점수**: 긍정/부정/중립 감정 분석
- **영향도 평가**: 주가에 미치는 영향도 측정
- **요약 제공**: AI 기반 뉴스 요약

### 💼 포트폴리오 관리
- **다중 포트폴리오**: 투자 목적별 포트폴리오 생성
- **자동 리밸런싱**: AI 기반 포트폴리오 최적화
- **성과 추적**: 실시간 수익률 및 위험도 모니터링
- **백테스팅**: 과거 데이터를 활용한 전략 검증

---

## 🖥️ 웹 인터페이스 사용법

### 대시보드 개요

![Dashboard Overview](screenshots/dashboard.png)

**주요 섹션:**
1. **시장 현황**: 주요 지수 및 시장 동향
2. **포트폴리오 요약**: 보유 포지션 및 수익률
3. **AI 추천**: 오늘의 투자 추천 종목
4. **뉴스 피드**: 최신 금융 뉴스

### 주식 검색 및 분석

#### 1. 주식 검색
```
검색창에 종목코드나 회사명 입력:
- 한국 주식: "삼성전자", "005930"
- 미국 주식: "Apple", "AAPL"
- 실시간 검색 결과 표시
```

#### 2. 종목 분석 페이지
- **기본 정보**: 현재가, 변동률, 거래량
- **차트 분석**: 기술적 지표 포함 인터랙티브 차트
- **AI 분석 리포트**: 종합 투자 의견
- **재무 정보**: 주요 재무지표 및 비율
- **뉴스 및 공시**: 관련 뉴스 및 기업 공시

#### 3. AI 분석 해석 가이드

**투자 등급:**
- 🔴 **강력매수**: 목표가 상승여력 20% 이상
- 🟠 **매수**: 목표가 상승여력 10-20%
- 🟡 **보유**: 목표가 상승여력 -5% ~ +10%
- 🔵 **매도**: 목표가 하락여력 -5% ~ -15%
- 🟣 **강력매도**: 목표가 하락여력 -15% 이하

**신뢰도 지표:**
- ⭐⭐⭐⭐⭐ (90%+): 매우 높은 신뢰도
- ⭐⭐⭐⭐ (80-90%): 높은 신뢰도
- ⭐⭐⭐ (70-80%): 보통 신뢰도
- ⭐⭐ (60-70%): 낮은 신뢰도
- ⭐ (60% 미만): 매우 낮은 신뢰도

---

## 🔌 API 사용 가이드

### API 키 발급

1. 설정 > API 관리 메뉴 접속
2. "새 API 키 생성" 버튼 클릭
3. 용도 및 권한 설정
4. API 키 안전하게 보관

### 기본 사용법

#### Python 예제
```python
import requests

# API 클라이언트 초기화
api_key = "your_api_key_here"
base_url = "http://localhost:8000"
headers = {"X-API-Key": api_key}

# 주식 데이터 조회
response = requests.get(
    f"{base_url}/api/v1/stocks/AAPL/data",
    headers=headers,
    params={"interval": "1d"}
)

if response.status_code == 200:
    data = response.json()
    print(f"AAPL 현재가: ${data['price']}")
else:
    print(f"오류: {response.status_code}")
```

#### JavaScript 예제
```javascript
// API 클라이언트
const apiKey = "your_api_key_here";
const baseUrl = "http://localhost:8000";

async function getStockData(symbol) {
    const response = await fetch(
        `${baseUrl}/api/v1/stocks/${symbol}/data`,
        {
            headers: {
                "X-API-Key": apiKey,
                "Content-Type": "application/json"
            }
        }
    );
    
    if (response.ok) {
        const data = await response.json();
        console.log(`${symbol} 현재가: $${data.price}`);
    } else {
        console.error("API 호출 실패:", response.status);
    }
}

getStockData("AAPL");
```

### 주요 API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|------------|--------|------|
| `/api/v1/stocks/{symbol}/data` | GET | 주식 데이터 조회 |
| `/api/v1/stocks/{symbol}/analysis` | GET | AI 분석 결과 |
| `/api/v1/portfolio` | GET/POST | 포트폴리오 관리 |
| `/api/v1/news` | GET | 금융 뉴스 조회 |
| `/api/v1/realtime/subscribe` | POST | 실시간 데이터 구독 |

---

## 🎨 투자 스타일 설정

### 투자 성향 유형

#### 🔥 공격형 (Aggressive)
- **목표**: 높은 수익률 추구
- **리스크**: 높은 변동성 수용
- **종목 선호**: 성장주, 테크주, 신흥시장
- **추천 비중**: 주식 80-90%, 현금 10-20%

**설정 방법:**
1. 설정 > 투자 설정 메뉴
2. "공격형" 선택
3. 리스크 허용도 설정 (7-10)
4. 목표 수익률 설정 (연 15% 이상)

#### ⚖️ 균형형 (Balanced)
- **목표**: 안정적 수익과 성장의 균형
- **리스크**: 중간 수준의 변동성
- **종목 선호**: 우량주, 배당주, 채권
- **추천 비중**: 주식 60-70%, 채권 20-30%, 현금 10%

**설정 방법:**
1. 투자 설정에서 "균형형" 선택
2. 리스크 허용도 설정 (4-6)
3. 목표 수익률 설정 (연 8-12%)
4. 섹터 분산 옵션 활성화

#### 🛡️ 안정형 (Conservative)
- **목표**: 원금 보전 및 안정적 배당
- **리스크**: 낮은 변동성 추구
- **종목 선호**: 우량 배당주, 채권, 현금성 자산
- **추천 비중**: 주식 30-40%, 채권 40-50%, 현금 20%

**설정 방법:**
1. 투자 설정에서 "안정형" 선택
2. 리스크 허용도 설정 (1-3)
3. 목표 수익률 설정 (연 4-8%)
4. 배당 우선 옵션 활성화

### 맞춤 설정

#### 고급 설정 옵션
```
📊 리스크 관리:
- 단일 종목 최대 비중: 5-20%
- 섹터별 최대 비중: 20-40%
- 손실 제한 (Stop Loss): 5-15%
- 이익 실현 (Take Profit): 10-50%

🌍 지역별 배분:
- 국내 주식: 30-70%
- 해외 선진국: 20-50%
- 해외 신흥국: 0-20%

📈 스타일별 배분:
- 성장주: 20-60%
- 가치주: 20-60%
- 배당주: 10-40%
```

---

## 💼 포트폴리오 관리

### 포트폴리오 생성

#### 1. 새 포트폴리오 만들기
```
단계별 가이드:
1. 포트폴리오 > "새 포트폴리오" 버튼 클릭
2. 기본 정보 입력:
   - 포트폴리오 이름
   - 투자 목적 (은퇴자금, 단기투자 등)
   - 초기 투자금액
   - 목표 수익률
3. 투자 설정:
   - 투자 성향 선택
   - 리밸런싱 주기 설정
   - 자동 투자 설정 (옵션)
4. 종목 추가 또는 AI 추천 수락
```

#### 2. 종목 추가/제거
- **수동 추가**: 검색 → 종목 선택 → 수량/금액 입력
- **AI 추천**: 추천 종목 목록에서 선택
- **일괄 추가**: CSV 파일 업로드
- **제거**: 포지션 목록에서 "매도" 버튼

### 포트폴리오 모니터링

#### 실시간 대시보드
```
📊 주요 지표:
- 총 자산 가치
- 일일/누적 손익
- 수익률 (일간, 주간, 월간, 연간)
- 위험도 지표 (베타, 변동성)
- 샤프 비율

📈 성과 차트:
- 수익률 추이 그래프
- 벤치마크 대비 성과
- 섹터별 기여도
- 자산 배분 차트
```

#### 포트폴리오 분석
- **리스크 분석**: VaR, 최대 손실폭, 상관관계
- **성과 분석**: 알파, 베타, 정보비율
- **배분 분석**: 섹터/지역/시가총액별 분포
- **리밸런싱 제안**: AI 기반 최적화 제안

### 자동 리밸런싱

#### 설정 방법
1. 포트폴리오 설정 > 자동 리밸런싱
2. 리밸런싱 조건 설정:
   - **시간 기반**: 매월/분기/반기
   - **임계값 기반**: 목표 비중에서 ±5% 이상 이탈시
   - **성과 기준**: 상대 성과가 기준치 이하일 때
3. 실행 방식 선택:
   - **자동 실행**: AI가 자동으로 매매 실행
   - **알림만**: 리밸런싱 제안 알림만 제공

---

## 🔔 실시간 알림 설정

### 알림 유형

#### 📱 가격 알림
- **목표가 도달**: 설정한 목표가 달성시
- **손실 제한**: 설정한 손실 한도 도달시
- **급등/급락**: 단시간 대폭 변동시
- **거래량 급증**: 평소 대비 거래량 3배 이상

#### 📰 뉴스 알림
- **보유 종목 관련**: 포트폴리오 종목 관련 뉴스
- **시장 이슈**: 주요 시장 이벤트 및 공시
- **감정 변화**: 뉴스 감정 점수 급변시
- **애널리스트 리포트**: 목표가 변경 및 투자의견 수정

#### 🤖 AI 알림
- **투자 추천**: 새로운 투자 기회 발견
- **위험 경고**: 포트폴리오 위험도 증가
- **리밸런싱 제안**: 자산 배분 조정 필요
- **시장 전망 변경**: AI 시장 전망 업데이트

### 알림 채널 설정

#### 웹 브라우저 알림
```javascript
// 브라우저 알림 권한 요청
Notification.requestPermission().then(permission => {
    if (permission === "granted") {
        console.log("알림 권한이 허용되었습니다");
    }
});
```

#### 이메일 알림
1. 설정 > 알림 > 이메일 설정
2. 이메일 주소 등록 및 인증
3. 알림 유형별 수신 여부 설정
4. 발송 빈도 설정 (즉시/매시간/일일 요약)

#### 슬랙(Slack) 연동
```
연동 단계:
1. Slack 워크스페이스에서 Incoming Webhook 생성
2. StockPilot 설정에서 Webhook URL 등록
3. 알림 채널 및 형식 설정
4. 테스트 메시지 발송으로 연동 확인
```

---

## 🔧 고급 기능

### 백테스팅

#### 전략 백테스트
```python
# 백테스팅 예제
strategy = {
    "name": "모멘텀 전략",
    "rules": {
        "buy_signal": "RSI < 30 and MA_cross_up",
        "sell_signal": "RSI > 70 or stop_loss",
        "position_size": 0.1,  # 10% 포지션
        "stop_loss": 0.05      # 5% 손실제한
    },
    "period": "2020-01-01 to 2023-12-31"
}

# 백테스트 실행
result = backtest.run_strategy(strategy)
print(f"연평균 수익률: {result.annual_return:.2%}")
print(f"최대 낙폭: {result.max_drawdown:.2%}")
print(f"샤프 비율: {result.sharpe_ratio:.2f}")
```

#### 결과 해석
- **수익률**: 연평균 수익률 및 누적 수익률
- **위험도**: 변동성, 최대 낙폭, VaR
- **효율성**: 샤프 비율, 소티노 비율, 칼마 비율
- **거래 통계**: 승률, 평균 보유기간, 거래 횟수

### API 스크립팅

#### 자동화 스크립트 작성
```python
import schedule
import time
from stockpilot_client import StockPilotClient

client = StockPilotClient("your_api_key")

def daily_portfolio_check():
    """매일 포트폴리오 점검"""
    portfolios = client.get_portfolios()
    
    for portfolio in portfolios:
        # 수익률 확인
        if portfolio['return_percent'] < -5:
            print(f"주의: {portfolio['name']} 수익률 -5% 돌파")
        
        # 리밸런싱 필요성 확인
        analysis = client.analyze_portfolio(portfolio['id'])
        if analysis['rebalancing_needed']:
            print(f"리밸런싱 필요: {portfolio['name']}")

# 매일 오후 6시에 실행
schedule.every().day.at("18:00").do(daily_portfolio_check)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### 데이터 내보내기

#### CSV 내보내기
```
포트폴리오 > 설정 > 데이터 내보내기
- 거래 내역 (CSV)
- 수익률 추이 (CSV)
- 보유 종목 현황 (CSV)
- 배당 수령 내역 (CSV)
```

#### API를 통한 데이터 추출
```python
# 거래 내역 조회
trades = client.get_trades(
    portfolio_id="port_123",
    start_date="2024-01-01",
    end_date="2024-12-31"
)

# 데이터프레임으로 변환
import pandas as pd
df = pd.DataFrame(trades)
df.to_csv("trades_2024.csv", index=False)
```

---

## 🔍 문제 해결

### 일반적인 문제

#### 로그인/인증 오류
```
증상: "인증에 실패했습니다" 오류 메시지
해결방법:
1. API 키 확인 및 재발급
2. 브라우저 쿠키/캐시 삭제
3. 시크릿 모드에서 접속 테스트
4. 방화벽/보안 프로그램 확인
```

#### 데이터 로딩 지연
```
증상: 주식 데이터나 차트가 느리게 로드됨
해결방법:
1. 인터넷 연결 상태 확인
2. 브라우저 하드웨어 가속 활성화
3. 다른 브라우저에서 테스트
4. 시스템 리소스 사용량 확인
```

#### WebSocket 연결 오류
```
증상: 실시간 데이터 수신 불가
해결방법:
1. 방화벽에서 WebSocket 포트(8765) 허용
2. 프록시 서버 설정 확인
3. 브라우저 WebSocket 지원 확인
4. 서버 상태 점검 (헬스체크 API 호출)
```

### 성능 최적화

#### 메모리 사용량 관리
- **차트 데이터 제한**: 표시 기간을 적절히 설정
- **실시간 구독 최소화**: 필요한 종목만 구독
- **브라우저 탭 정리**: 불필요한 탭 닫기
- **캐시 정리**: 정기적인 브라우저 캐시 삭제

#### 네트워크 최적화
- **데이터 압축**: gzip 압축 활성화
- **CDN 사용**: 정적 리소스 CDN 활용
- **배치 요청**: 여러 API 호출을 배치로 처리
- **캐싱 전략**: 적절한 캐시 TTL 설정

### 로그 분석

#### 클라이언트 로그 확인
```javascript
// 브라우저 개발자 도구에서 실행
console.log("StockPilot 디버그 정보:");
console.log("- WebSocket 상태:", window.stockpilot?.ws?.readyState);
console.log("- API 키 상태:", window.stockpilot?.hasApiKey);
console.log("- 마지막 업데이트:", window.stockpilot?.lastUpdate);
```

#### 서버 로그 확인
```bash
# 서버 로그 실시간 모니터링
tail -f /var/log/stockpilot/application.log

# 특정 에러 검색
grep "ERROR" /var/log/stockpilot/application.log | tail -20

# API 호출 통계
grep "API_CALL" /var/log/stockpilot/application.log | awk '{print $4}' | sort | uniq -c
```

---

## 📞 지원 및 문의

### 도움말 리소스
- 📖 **온라인 문서**: https://docs.stockpilot.ai
- 💬 **커뮤니티 포럼**: https://community.stockpilot.ai
- 📺 **비디오 튜토리얼**: https://youtube.com/stockpilot
- 📧 **이메일 지원**: support@stockpilot.ai

### 긴급 상황 대응
```
🚨 긴급 상황시:
1. 시스템 장애: emergency@stockpilot.ai
2. 보안 이슈: security@stockpilot.ai
3. 계정 잠금: account@stockpilot.ai
4. 24시간 핫라인: 02-1234-5678
```

### 피드백 및 제안
- **기능 요청**: features@stockpilot.ai
- **버그 리포트**: bugs@stockpilot.ai
- **사용성 개선**: ux@stockpilot.ai
- **GitHub Issues**: https://github.com/stockpilot/issues

---

## 📜 라이센스 및 면책조항

### 투자 면책조항
```
⚠️ 중요 고지사항:

1. StockPilot이 제공하는 모든 정보는 투자 참고용이며,
   투자 권유나 종목 추천이 아닙니다.

2. 모든 투자 결정의 책임은 투자자 본인에게 있으며,
   투자 손실에 대해 StockPilot은 책임지지 않습니다.

3. 과거 성과는 미래 수익을 보장하지 않습니다.

4. 투자 전 충분한 조사와 전문가 상담을 권장합니다.
```

### 소프트웨어 라이센스
- **오픈소스**: MIT License
- **상업적 이용**: 허용
- **수정 및 배포**: 허용 (라이센스 명시 필요)

---

*마지막 업데이트: 2024년 1월*

**Happy Investing! 🚀📈**