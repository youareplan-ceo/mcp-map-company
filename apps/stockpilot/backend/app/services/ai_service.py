"""
AI 분석 서비스
OpenAI GPT를 활용한 주식 투자 분석 및 추천
모델 라우팅 정책 v2 적용: nano→mini→5→o3 자동 승급
"""

import openai
import json
import time
import asyncio
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from enum import Enum
from loguru import logger

from app.models import AIAnalysis, InvestmentSignal, TechnicalIndicator
from app.config import get_settings
from app.services.stock_service import StockService
from app.services.news_service import NewsService
from app.middleware.usage_tracker import get_usage_tracker

settings = get_settings()


class ModelTier(Enum):
    """모델 티어 정의"""
    NANO = "gpt-4o-mini-2024-07-18"  # 기본 분석용
    MINI = "gpt-4o-mini"             # 중간 복잡도
    GPT4 = "gpt-4-turbo-2024-04-09" # JSON 스키마 엄격시
    GPT5 = "gpt-4o"                  # 설명 필요시
    O3 = "o1-preview"                # 최고 추론


class TaskType(Enum):
    """작업 타입별 모델 선택 기준"""
    SIMPLE_ANALYSIS = "simple"      # 단순 분석 - NANO
    STRUCTURED_JSON = "json"        # JSON 구조화 - GPT4
    COMPLEX_REASONING = "reasoning" # 복잡한 추론 - GPT5
    CRITICAL_DECISION = "critical"  # 중요한 판단 - O3


class ModelRoutingError(Exception):
    """모델 라우팅 관련 에러"""
    pass


class AIService:
    """AI 투자 분석 서비스 - 모델 라우팅 정책 v2 적용"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
        self.usage_tracker = None
        self.stock_service = StockService()
        self.news_service = NewsService()
        
        # 모델별 토큰 제한
        self.token_limits = {
            ModelTier.NANO: getattr(settings, 'token_limit_nano', 512),
            ModelTier.MINI: getattr(settings, 'token_limit_mini', 1024),
            ModelTier.GPT4: getattr(settings, 'token_limit_gpt4', 2048),
            ModelTier.GPT5: getattr(settings, 'token_limit_gpt5', 4096),
            ModelTier.O3: getattr(settings, 'token_limit_o3', 8192)
        }
        
        # 모델 승급 체인
        self.upgrade_chain = [
            ModelTier.NANO,
            ModelTier.MINI,
            ModelTier.GPT5,
            ModelTier.O3
        ]
        
        logger.info("AI 서비스 초기화 완료 - 모델 라우팅 정책 v2 적용")
    
    def _select_initial_model(self, task_type: TaskType, prompt_length: int) -> ModelTier:
        """작업 타입과 프롬프트 길이에 따른 초기 모델 선택"""
        # JSON 스키마가 엄격하게 필요한 경우
        if task_type == TaskType.STRUCTURED_JSON:
            return ModelTier.GPT4
        
        # 복잡한 설명이 필요한 경우
        elif task_type == TaskType.COMPLEX_REASONING:
            return ModelTier.GPT5
        
        # 중요한 판단이 필요한 경우
        elif task_type == TaskType.CRITICAL_DECISION:
            return ModelTier.O3
        
        # 기본적으로 NANO에서 시작
        else:
            # 프롬프트가 너무 길면 MINI로 시작
            if prompt_length > self.token_limits[ModelTier.NANO]:
                return ModelTier.MINI
            return ModelTier.NANO
    
    def _can_upgrade_model(self, current_model: ModelTier) -> Optional[ModelTier]:
        """현재 모델에서 상위 모델로 승급 가능 여부 확인"""
        try:
            current_index = self.upgrade_chain.index(current_model)
            if current_index < len(self.upgrade_chain) - 1:
                return self.upgrade_chain[current_index + 1]
            return None
        except ValueError:
            # GPT4인 경우 GPT5로 승급
            if current_model == ModelTier.GPT4:
                return ModelTier.GPT5
            return None
    
    def _validate_json_response(self, response: str) -> Tuple[bool, Dict[str, Any]]:
        """JSON 응답 검증"""
        try:
            data = json.loads(response)
            
            # 필수 필드 확인
            required_fields = ["signal", "confidence", "reasoning"]
            for field in required_fields:
                if field not in data:
                    logger.warning(f"필수 필드 누락: {field}")
                    return False, {}
            
            # 신호 타입 검증
            valid_signals = ["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]
            if data.get("signal") not in valid_signals:
                logger.warning(f"유효하지 않은 신호: {data.get('signal')}")
                return False, {}
            
            # 신뢰도 범위 검증
            confidence = data.get("confidence", 0)
            if not isinstance(confidence, (int, float)) or not (0 <= confidence <= 100):
                logger.warning(f"유효하지 않은 신뢰도: {confidence}")
                return False, {}
            
            return True, data
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 파싱 실패: {str(e)}")
            return False, {}
        except Exception as e:
            logger.warning(f"응답 검증 오류: {str(e)}")
            return False, {}
    
    async def _call_openai_with_routing(
        self,
        prompt: str,
        task_type: TaskType = TaskType.SIMPLE_ANALYSIS,
        system_message: str = None,
        max_retries: int = 1
    ) -> Tuple[str, ModelTier]:
        """모델 라우팅 정책을 적용한 OpenAI API 호출"""
        
        # 사용량 추적기 초기화
        if not self.usage_tracker:
            self.usage_tracker = await get_usage_tracker()
        
        # 비용 한도 체크
        can_proceed, limit_msg = await self.usage_tracker.check_cost_limits()
        if not can_proceed:
            raise ModelRoutingError(f"비용 한도 초과: {limit_msg}")
        
        prompt_length = len(prompt)
        current_model = self._select_initial_model(task_type, prompt_length)
        
        logger.info(f"초기 모델 선택: {current_model.value}, 작업 타입: {task_type.value}")
        
        for attempt in range(max_retries + 1):
            try:
                # 토큰 제한 확인
                max_tokens = min(
                    self.token_limits[current_model],
                    getattr(settings, 'max_gpt_tokens', 2048)
                )
                
                # API 호출
                start_time = time.time()
                
                messages = []
                if system_message:
                    messages.append({"role": "system", "content": system_message})
                messages.append({"role": "user", "content": prompt})
                
                logger.debug(f"API 호출 - 모델: {current_model.value}, 토큰 제한: {max_tokens}")
                
                response = self.client.chat.completions.create(
                    model=current_model.value,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.3,
                    timeout=30
                )
                
                response_time = time.time() - start_time
                response_content = response.choices[0].message.content
                
                # 사용량 추적 및 비용 기록 - 확장된 메트릭스
                if hasattr(response, 'usage'):
                    cost = await self.usage_tracker.record_usage(
                        model=current_model.value,
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        task_type=task_type.value,
                        endpoint="ai_service",
                        status_code=200,
                        response_time_ms=response_time * 1000,
                        request_id=f"ai_{int(time.time())}"
                    )
                    
                    logger.info(
                        f"토큰 사용량 - 입력: {response.usage.prompt_tokens}, "
                        f"출력: {response.usage.completion_tokens}, "
                        f"총합: {response.usage.total_tokens}, "
                        f"비용: ${cost:.4f}, 응답시간: {response_time:.2f}초"
                    )
                
                # JSON 응답 검증 (JSON 작업 타입인 경우)
                if task_type == TaskType.STRUCTURED_JSON:
                    is_valid, parsed_data = self._validate_json_response(response_content)
                    
                    if not is_valid and attempt < max_retries:
                        # 상위 모델로 승급 시도
                        next_model = self._can_upgrade_model(current_model)
                        if next_model:
                            logger.warning(
                                f"JSON 검증 실패, 모델 승급: {current_model.value} → {next_model.value}"
                            )
                            current_model = next_model
                            continue
                    elif not is_valid:
                        logger.error("JSON 검증 실패, 더 이상 승급할 모델 없음")
                        raise ModelRoutingError("JSON 응답 검증 실패")
                
                logger.info(f"API 호출 성공 - 최종 모델: {current_model.value}")
                return response_content, current_model
                
            except (openai.APIError, openai.Timeout) as e:
                logger.warning(f"API 오류 (시도 {attempt + 1}): {str(e)}")
                
                if attempt < max_retries:
                    # 상위 모델로 승급 시도
                    next_model = self._can_upgrade_model(current_model)
                    if next_model:
                        logger.info(f"API 오류로 인한 모델 승급: {current_model.value} → {next_model.value}")
                        current_model = next_model
                        # 백오프 지연
                        await asyncio.sleep(2 ** attempt)
                        continue
                
                raise ModelRoutingError(f"API 호출 실패: {str(e)}")
                
            except Exception as e:
                logger.error(f"예상치 못한 오류: {str(e)}")
                if attempt >= max_retries:
                    raise ModelRoutingError(f"API 호출 중 예상치 못한 오류: {str(e)}")
        
        raise ModelRoutingError("모든 재시도 실패")
    
    async def analyze_stock(
        self, 
        symbol: str, 
        include_news: bool = True,
        analysis_type: str = "comprehensive"
    ) -> AIAnalysis:
        """종합 주식 분석"""
        try:
            logger.info(f"AI 주식 분석 시작: {symbol}")
            
            # 기본 주식 정보 수집
            stock_info = await self.stock_service.get_stock_info(symbol)
            if not stock_info:
                raise Exception(f"종목 정보를 찾을 수 없습니다: {symbol}")
            
            # 가격 정보 수집
            price_info = await self.stock_service.get_current_price(symbol)
            
            # 기술적 지표 수집
            technical_indicators = await self.stock_service.get_technical_indicators(symbol)
            
            # 뉴스 정보 수집 (선택적)
            news_summary = ""
            if include_news:
                try:
                    news_data = await self.news_service.get_stock_related_news(symbol, hours=24)
                    if news_data:
                        news_summary = await self._summarize_news(news_data[:5])  # 최근 5개 뉴스
                except Exception as e:
                    logger.warning(f"뉴스 수집 실패: {str(e)}")
            
            # GPT 분석 요청
            analysis_prompt = self._create_analysis_prompt(
                stock_info, price_info, technical_indicators, news_summary
            )
            
            # 모델 라우팅 정책 v2 적용하여 GPT 분석 수행
            system_message = "당신은 한국 주식시장 전문 투자 분석가입니다. 객관적이고 신중한 분석을 제공하며, 항상 정확한 JSON 형식으로 응답합니다."
            
            gpt_response, used_model = await self._call_openai_with_routing(
                analysis_prompt,
                task_type=TaskType.STRUCTURED_JSON,  # JSON 응답이 필요한 작업
                system_message=system_message,
                max_retries=1
            )
            
            logger.info(f"주식 분석 완료 - 사용 모델: {used_model.value}")
            
            # GPT 응답 파싱
            analysis_result = self._parse_gpt_response(gpt_response)
            
            # AI 분석 결과 생성
            ai_analysis = AIAnalysis(
                symbol=symbol,
                signal=analysis_result.get("signal", InvestmentSignal.HOLD),
                confidence=min(max(analysis_result.get("confidence", 50), 0), 100),
                target_price=analysis_result.get("target_price"),
                reasoning=analysis_result.get("reasoning", "분석 결과를 가져올 수 없습니다."),
                technical_indicators=technical_indicators,
                risk_level=analysis_result.get("risk_level", "중간"),
                time_horizon=analysis_result.get("time_horizon", "1-3개월"),
                created_at=datetime.now()
            )
            
            logger.info(f"AI 분석 완료: {symbol}, 시그널: {ai_analysis.signal}")
            return ai_analysis
            
        except Exception as e:
            logger.error(f"AI 분석 오류: {symbol}, {str(e)}")
            # 기본 분석 결과 반환
            return AIAnalysis(
                symbol=symbol,
                signal=InvestmentSignal.HOLD,
                confidence=0,
                reasoning=f"분석 중 오류가 발생했습니다: {str(e)}",
                technical_indicators=[],
                risk_level="알 수 없음",
                time_horizon="알 수 없음",
                created_at=datetime.now()
            )
    
    def _create_analysis_prompt(
        self, 
        stock_info, 
        price_info, 
        technical_indicators: List[TechnicalIndicator], 
        news_summary: str
    ) -> str:
        """GPT 분석용 프롬프트 생성"""
        
        # 기술적 지표 요약
        tech_summary = "\n".join([
            f"- {ind.name}: {ind.value:.2f} ({ind.description})"
            for ind in technical_indicators
        ])
        
        # 가격 정보 요약
        price_summary = ""
        if price_info:
            price_summary = f"""
현재가: {price_info.current_price:,.0f}원
전일 대비: {price_info.change_amount:+.0f}원 ({price_info.change_rate:+.2f}%)
거래량: {price_info.volume:,}주
"""
        
        prompt = f"""
한국 주식 투자 전문가로서 다음 종목을 분석해주세요.

종목 정보:
- 종목명: {stock_info.name}
- 종목코드: {stock_info.symbol}
- 시장: {stock_info.market.value}
- 업종: {stock_info.sector}

{price_summary}

기술적 지표:
{tech_summary}

뉴스 요약:
{news_summary}

다음 형식으로 JSON 응답해주세요:
{{
    "signal": "STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL",
    "confidence": 0-100 (신뢰도 점수),
    "target_price": 목표주가 (숫자, 없으면 null),
    "reasoning": "투자 판단 근거 (3-5문장으로 요약)",
    "risk_level": "낮음/중간/높음",
    "time_horizon": "투자 기간 추천 (예: 1-3개월, 6개월-1년)"
}}

한국 주식시장의 특성을 고려하여 신중하고 객관적으로 분석해주세요.
"""
        return prompt
    
    async def _call_gpt_analysis(self, prompt: str) -> str:
        """레거시 GPT API 호출 (하위 호환성용)"""
        try:
            response, _ = await self._call_openai_with_routing(
                prompt,
                task_type=TaskType.STRUCTURED_JSON,
                system_message="당신은 한국 주식시장 전문 투자 분석가입니다. 객관적이고 신중한 분석을 제공하며, 항상 JSON 형식으로 응답합니다."
            )
            return response
            
        except Exception as e:
            logger.error(f"GPT API 호출 오류: {str(e)}")
            # 기본 응답 반환
            return json.dumps({
                "signal": "HOLD",
                "confidence": 0,
                "reasoning": f"AI 분석 중 오류가 발생했습니다: {str(e)}",
                "risk_level": "알 수 없음",
                "time_horizon": "알 수 없음"
            })
    
    def _parse_gpt_response(self, response: str) -> Dict[str, Any]:
        """GPT 응답 파싱"""
        try:
            # JSON 응답 파싱
            result = json.loads(response)
            
            # 시그널 검증
            valid_signals = ["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]
            if result.get("signal") not in valid_signals:
                result["signal"] = "HOLD"
            
            # 신뢰도 검증
            confidence = result.get("confidence", 50)
            if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 100:
                result["confidence"] = 50
            
            return result
            
        except json.JSONDecodeError:
            logger.error("GPT 응답 JSON 파싱 실패")
            return {
                "signal": "HOLD",
                "confidence": 0,
                "reasoning": "AI 응답 형식 오류가 발생했습니다.",
                "risk_level": "알 수 없음",
                "time_horizon": "알 수 없음"
            }
        except Exception as e:
            logger.error(f"GPT 응답 파싱 오류: {str(e)}")
            return {
                "signal": "HOLD",
                "confidence": 0,
                "reasoning": f"응답 처리 중 오류: {str(e)}",
                "risk_level": "알 수 없음",
                "time_horizon": "알 수 없음"
            }
    
    async def _summarize_news(self, news_articles: List[Dict[str, Any]]) -> str:
        """뉴스 요약"""
        if not news_articles:
            return "관련 뉴스가 없습니다."
        
        try:
            news_text = "\n".join([
                f"- {article.get('title', '')}: {article.get('summary', '')}"
                for article in news_articles
            ])
            
            summary_prompt = f"""
다음 뉴스들을 주식 투자 관점에서 3-4문장으로 요약해주세요:

{news_text}

투자에 미칠 수 있는 긍정적/부정적 영향을 중심으로 요약해주세요.
"""
            
            response, _ = await self._call_openai_with_routing(
                summary_prompt,
                task_type=TaskType.SIMPLE_ANALYSIS,  # 단순 요약 작업
                system_message="당신은 투자 뉴스 분석 전문가입니다.",
                max_retries=0  # 뉴스 요약은 재시도 없이
            )
            
            return response
            
        except Exception as e:
            logger.error(f"뉴스 요약 오류: {str(e)}")
            return "뉴스 요약 중 오류가 발생했습니다."
    
    async def generate_market_insight(self, market_data: Dict[str, Any]) -> str:
        """시장 전체 인사이트 생성"""
        try:
            insight_prompt = f"""
한국 주식시장의 현재 상황을 분석해주세요:

시장 데이터:
{json.dumps(market_data, indent=2, ensure_ascii=False)}

다음 관점에서 3-4문장으로 시장 인사이트를 제공해주세요:
1. 전체 시장 흐름
2. 주요 관심 섹터
3. 투자자들이 주의해야 할 점

전문적이지만 이해하기 쉽게 설명해주세요.
"""
            
            response, _ = await self._call_openai_with_routing(
                insight_prompt,
                task_type=TaskType.COMPLEX_REASONING,  # 복잡한 시장 분석
                system_message="당신은 한국 주식시장 전문 애널리스트입니다.",
                max_retries=1
            )
            
            return response
            
        except Exception as e:
            logger.error(f"시장 인사이트 생성 오류: {str(e)}")
            return "시장 분석을 수행할 수 없습니다."