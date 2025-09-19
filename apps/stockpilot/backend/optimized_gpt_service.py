"""
StockPilot GPT API 비용 최적화 서비스
- GPT-3.5-turbo 사용으로 비용 절감
- 캐싱으로 중복 분석 방지
- 토큰 제한으로 비용 통제
- 일일 호출 한도 관리
"""

import os
import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from openai import OpenAI
import redis
from redis.exceptions import ConnectionError as RedisConnectionError

# 로깅 설정
logger = logging.getLogger(__name__)

@dataclass
class GPTUsageStats:
    """GPT 사용량 통계"""
    daily_calls: int = 0
    daily_cost: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    last_reset: str = ""

class OptimizedGPTService:
    """비용 최적화된 GPT API 서비스"""
    
    def __init__(self):
        # 환경 변수 로드
        self.api_key = os.getenv('OPENAI_API_KEY', 'demo-key')
        self.model = os.getenv('GPT_MODEL', 'gpt-3.5-turbo')
        self.max_input_tokens = int(os.getenv('GPT_MAX_INPUT_TOKENS', '500'))
        self.max_output_tokens = int(os.getenv('GPT_MAX_OUTPUT_TOKENS', '100'))
        self.daily_limit = int(os.getenv('GPT_DAILY_LIMIT', '100'))
        self.cache_minutes = int(os.getenv('GPT_CACHE_MINUTES', '60'))
        
        # OpenAI 클라이언트 초기화
        if self.api_key == 'demo-key':
            logger.warning("⚠️ OpenAI API 키가 설정되지 않았습니다. Mock 데이터를 사용합니다.")
            self.client = None
        else:
            self.client = OpenAI(api_key=self.api_key)
        
        # Redis 캐시 연결 시도 (없으면 메모리 캐시 사용)
        self.cache = {}
        self.redis_client = None
        try:
            self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            self.redis_client.ping()
            logger.info("✅ Redis 캐시 연결 성공")
        except (RedisConnectionError, Exception) as e:
            logger.info("📝 Redis 없음. 메모리 캐시 사용")
        
        # 사용량 통계 초기화
        self.usage_stats = self._load_usage_stats()
        
        # GPT-3.5-turbo 비용 (2024년 기준 - USD)
        self.input_cost_per_1k = 0.0015  # $0.0015 / 1K tokens
        self.output_cost_per_1k = 0.002  # $0.002 / 1K tokens
        
        logger.info(f"🤖 최적화된 GPT 서비스 초기화: {self.model}")
        logger.info(f"💰 일일 한도: {self.daily_limit}회, 캐시: {self.cache_minutes}분")
    
    def _load_usage_stats(self) -> GPTUsageStats:
        """사용량 통계 로드"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        if self.redis_client:
            try:
                stats_data = self.redis_client.get(f"gpt_stats:{today}")
                if stats_data:
                    data = json.loads(stats_data)
                    return GPTUsageStats(**data)
            except Exception as e:
                logger.error(f"Redis 통계 로드 실패: {e}")
        
        # 첫 실행이거나 Redis 없을 때
        return GPTUsageStats(last_reset=today)
    
    def _save_usage_stats(self):
        """사용량 통계 저장"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 날짜가 바뀌면 통계 리셋
        if self.usage_stats.last_reset != today:
            self.usage_stats = GPTUsageStats(last_reset=today)
        
        if self.redis_client:
            try:
                stats_data = json.dumps({
                    'daily_calls': self.usage_stats.daily_calls,
                    'daily_cost': self.usage_stats.daily_cost,
                    'total_input_tokens': self.usage_stats.total_input_tokens,
                    'total_output_tokens': self.usage_stats.total_output_tokens,
                    'last_reset': self.usage_stats.last_reset
                })
                self.redis_client.setex(f"gpt_stats:{today}", 86400, stats_data)  # 24시간 유지
            except Exception as e:
                logger.error(f"Redis 통계 저장 실패: {e}")
    
    def _get_cache_key(self, prompt: str, symbol: str = "") -> str:
        """캐시 키 생성"""
        content = f"{symbol}:{prompt}"
        return f"gpt_cache:{hashlib.md5(content.encode()).hexdigest()}"
    
    def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """캐시된 응답 조회"""
        if self.redis_client:
            try:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    logger.info("💾 캐시된 분석 결과 사용")
                    return json.loads(cached_data)
            except Exception as e:
                logger.error(f"캐시 조회 실패: {e}")
        else:
            # 메모리 캐시 사용
            if cache_key in self.cache:
                cache_data = self.cache[cache_key]
                # 캐시 만료 확인
                if datetime.now() < cache_data['expires']:
                    logger.info("💾 메모리 캐시된 분석 결과 사용")
                    return cache_data['response']
                else:
                    del self.cache[cache_key]
        
        return None
    
    def _save_to_cache(self, cache_key: str, response: Dict[str, Any]):
        """응답 캐시 저장"""
        if self.redis_client:
            try:
                cache_data = json.dumps(response)
                self.redis_client.setex(cache_key, self.cache_minutes * 60, cache_data)
            except Exception as e:
                logger.error(f"캐시 저장 실패: {e}")
        else:
            # 메모리 캐시 저장
            expires = datetime.now() + timedelta(minutes=self.cache_minutes)
            self.cache[cache_key] = {
                'response': response,
                'expires': expires
            }
    
    def _check_daily_limit(self) -> bool:
        """일일 호출 한도 확인"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 날짜가 바뀌면 통계 리셋
        if self.usage_stats.last_reset != today:
            self.usage_stats = GPTUsageStats(last_reset=today)
            self._save_usage_stats()
        
        if self.usage_stats.daily_calls >= self.daily_limit:
            logger.warning(f"⚠️ 일일 GPT 호출 한도 초과: {self.usage_stats.daily_calls}/{self.daily_limit}")
            return False
        
        return True
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """토큰 사용량 기반 비용 계산"""
        input_cost = (input_tokens / 1000) * self.input_cost_per_1k
        output_cost = (output_tokens / 1000) * self.output_cost_per_1k
        return input_cost + output_cost
    
    def _is_important_event(self, content: str) -> bool:
        """중요 이벤트 필터링 (비용 절감)"""
        important_keywords = [
            '금리', '연준', 'fed', '실적', 'earnings',
            '전쟁', '인플레이션', '경제지표', 'gdp',
            '합병', '인수', '파산', '배당', '분할'
        ]
        
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in important_keywords)
    
    def analyze_investment(self, symbol: str, news_content: str = "", held_stocks: List[str] = None) -> Dict[str, Any]:
        """투자 분석 (비용 최적화)"""
        
        # 일일 한도 확인
        if not self._check_daily_limit():
            return self._get_limit_exceeded_response()
        
        # 중요 이벤트만 분석 (비용 절감)
        if news_content and not self._is_important_event(news_content):
            logger.info("📰 일반 뉴스는 분석하지 않음 (비용 절감)")
            return self._get_general_news_response(symbol)
        
        # 캐시 확인
        cache_key = self._get_cache_key(f"invest:{symbol}:{news_content[:100]}", symbol)
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            return cached_response
        
        # 실제 API 키가 없으면 Mock 데이터 반환
        if not self.client:
            return self._get_mock_analysis(symbol)
        
        try:
            # 간결한 프롬프트 생성 (토큰 절약)
            held_stocks_str = ", ".join(held_stocks[:3]) if held_stocks else "없음"
            
            prompt = f"""종목: {symbol}
뉴스: {news_content[:200]}...
보유종목: {held_stocks_str}

다음 형식으로 한줄 답변:
결정: [매수/매도/홀드]
이유: [핵심 이유 1줄, 20자 이내]
신뢰도: [1-10]"""
            
            # GPT API 호출 (토큰 제한)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 간결한 투자 분석가입니다. 핵심만 말하세요."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_output_tokens,
                temperature=0.7
            )
            
            # 사용량 통계 업데이트
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            cost = self._calculate_cost(input_tokens, output_tokens)
            
            self.usage_stats.daily_calls += 1
            self.usage_stats.daily_cost += cost
            self.usage_stats.total_input_tokens += input_tokens
            self.usage_stats.total_output_tokens += output_tokens
            self._save_usage_stats()
            
            logger.info(f"💰 GPT 호출 완료: {input_tokens}+{output_tokens} 토큰, ${cost:.4f}")
            
            # 응답 파싱
            analysis_result = self._parse_gpt_response(response.choices[0].message.content, symbol)
            
            # 캐시 저장
            self._save_to_cache(cache_key, analysis_result)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"GPT 분석 실패 - {symbol}: {e}")
            # 에러시 즉시 중단 (재시도 안 함)
            return self._get_error_response(symbol, str(e))
    
    def _parse_gpt_response(self, gpt_content: str, symbol: str) -> Dict[str, Any]:
        """GPT 응답 파싱"""
        try:
            lines = gpt_content.strip().split('\n')
            decision = "hold"
            reason = "분석 결과를 파싱할 수 없음"
            confidence = 5
            
            for line in lines:
                if "결정:" in line or "매수" in line or "매도" in line or "홀드" in line:
                    if "매수" in line:
                        decision = "buy"
                    elif "매도" in line:
                        decision = "sell"
                    else:
                        decision = "hold"
                elif "이유:" in line:
                    reason = line.split("이유:")[-1].strip()[:50]  # 50자 제한
                elif "신뢰도:" in line:
                    try:
                        confidence = int(''.join(filter(str.isdigit, line)))
                        confidence = max(1, min(10, confidence))
                    except:
                        confidence = 5
            
            return {
                "success": True,
                "data": {
                    "symbol": symbol,
                    "recommendation": decision,
                    "reason": reason,
                    "confidence_score": confidence * 10,  # 1-10을 10-100으로 변환
                    "analysis_summary": f"{symbol} 종목에 대한 간단 분석: {reason}",
                    "timestamp": datetime.now().isoformat()
                },
                "usage": {
                    "daily_calls": self.usage_stats.daily_calls,
                    "daily_cost": round(self.usage_stats.daily_cost, 4),
                    "remaining_calls": self.daily_limit - self.usage_stats.daily_calls
                }
            }
            
        except Exception as e:
            logger.error(f"GPT 응답 파싱 실패: {e}")
            return self._get_error_response(symbol, "응답 파싱 실패")
    
    def _get_mock_analysis(self, symbol: str) -> Dict[str, Any]:
        """Mock 분석 데이터 (API 키 없을 때)"""
        mock_recommendations = {
            "AAPL": {"decision": "buy", "reason": "실적 개선 전망", "confidence": 75},
            "TSLA": {"decision": "hold", "reason": "변동성 높음", "confidence": 60},
            "MSFT": {"decision": "buy", "reason": "클라우드 성장", "confidence": 80},
        }
        
        default = {"decision": "hold", "reason": "분석 정보 부족", "confidence": 50}
        mock_data = mock_recommendations.get(symbol, default)
        
        return {
            "success": True,
            "data": {
                "symbol": symbol,
                "recommendation": mock_data["decision"],
                "reason": mock_data["reason"],
                "confidence_score": mock_data["confidence"],
                "analysis_summary": f"Mock 분석: {mock_data['reason']}",
                "timestamp": datetime.now().isoformat()
            },
            "usage": {
                "daily_calls": 0,
                "daily_cost": 0.0,
                "remaining_calls": self.daily_limit
            }
        }
    
    def _get_limit_exceeded_response(self) -> Dict[str, Any]:
        """일일 한도 초과시 응답"""
        return {
            "success": False,
            "error": "daily_limit_exceeded",
            "message": f"일일 GPT 호출 한도({self.daily_limit}회)를 초과했습니다.",
            "usage": {
                "daily_calls": self.usage_stats.daily_calls,
                "daily_cost": round(self.usage_stats.daily_cost, 4),
                "remaining_calls": 0
            }
        }
    
    def _get_general_news_response(self, symbol: str) -> Dict[str, Any]:
        """일반 뉴스에 대한 기본 응답"""
        return {
            "success": True,
            "data": {
                "symbol": symbol,
                "recommendation": "hold",
                "reason": "일반 뉴스, 추가 분석 불필요",
                "confidence_score": 50,
                "analysis_summary": "중요 이벤트가 아니므로 현재 포지션 유지 권장",
                "timestamp": datetime.now().isoformat()
            },
            "usage": {
                "daily_calls": self.usage_stats.daily_calls,
                "daily_cost": round(self.usage_stats.daily_cost, 4),
                "remaining_calls": self.daily_limit - self.usage_stats.daily_calls
            }
        }
    
    def _get_error_response(self, symbol: str, error_msg: str) -> Dict[str, Any]:
        """에러 응답"""
        return {
            "success": False,
            "error": "analysis_failed",
            "message": f"분석 실패: {error_msg}",
            "data": {
                "symbol": symbol,
                "recommendation": "hold",
                "reason": "분석 실패",
                "confidence_score": 0,
                "analysis_summary": "기술적 문제로 분석 불가",
                "timestamp": datetime.now().isoformat()
            }
        }
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """현재 사용량 통계 반환"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 날짜가 바뀌면 통계 리셋
        if self.usage_stats.last_reset != today:
            self.usage_stats = GPTUsageStats(last_reset=today)
            self._save_usage_stats()
        
        return {
            "date": today,
            "daily_calls": self.usage_stats.daily_calls,
            "daily_limit": self.daily_limit,
            "remaining_calls": self.daily_limit - self.usage_stats.daily_calls,
            "daily_cost_usd": round(self.usage_stats.daily_cost, 4),
            "daily_cost_krw": round(self.usage_stats.daily_cost * 1300, 0),  # 대략적인 환율
            "total_input_tokens": self.usage_stats.total_input_tokens,
            "total_output_tokens": self.usage_stats.total_output_tokens,
            "cache_hits": len(self.cache) if not self.redis_client else "Redis 사용중",
            "model": self.model,
            "status": "정상" if self.usage_stats.daily_calls < self.daily_limit else "한도초과"
        }

# 전역 인스턴스
optimized_gpt_service = OptimizedGPTService()