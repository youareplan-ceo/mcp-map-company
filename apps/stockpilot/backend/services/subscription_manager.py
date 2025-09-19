"""
StockPilot 사용자 구독 프리셋 관리 시스템
투자 성향별 필터링, 맞춤형 알림 라우팅, 포트폴리오 추천 엔진
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

# 로깅 설정
logger = logging.getLogger(__name__)

class InvestmentStyle(Enum):
    """투자 성향"""
    AGGRESSIVE = "aggressive"    # 공격형 - 고위험 고수익
    BALANCED = "balanced"        # 균형형 - 중위험 중수익
    CONSERVATIVE = "conservative" # 안정형 - 저위험 저수익

class AlertSeverity(Enum):
    """알림 심각도"""
    HIGH = "high"       # 즉시 알림
    MEDIUM = "medium"   # 일반 알림
    LOW = "low"         # 낮은 우선순위

class SignalStrength(Enum):
    """시그널 강도"""
    STRONG = "strong"   # 강한 시그널 (80% 이상)
    MODERATE = "moderate" # 보통 시그널 (60-80%)
    WEAK = "weak"       # 약한 시그널 (60% 미만)

@dataclass
class UserPreferences:
    """사용자 선호 설정"""
    user_id: str
    investment_style: InvestmentStyle
    risk_tolerance: float  # 0.0 (매우 보수적) ~ 1.0 (매우 공격적)
    min_signal_strength: float  # 최소 시그널 강도 (0.0 ~ 1.0)
    max_daily_alerts: int  # 일일 최대 알림 수
    preferred_markets: List[str]  # 선호 시장 ["US", "KR"]
    preferred_sectors: List[str]  # 선호 섹터
    excluded_symbols: List[str]  # 제외할 종목
    notification_channels: List[str]  # 알림 채널 ["email", "sms", "push", "slack"]
    trading_hours_only: bool  # 거래 시간에만 알림 받기
    weekend_alerts: bool  # 주말 알림 허용
    created_at: datetime
    updated_at: datetime

@dataclass 
class SubscriptionPreset:
    """구독 프리셋"""
    preset_id: str
    name: str
    description: str
    investment_style: InvestmentStyle
    default_preferences: UserPreferences
    channels: List[str]  # 구독할 채널들
    filters: Dict[str, Any]  # 필터 설정
    is_active: bool
    created_at: datetime

@dataclass
class AlertRule:
    """알림 규칙"""
    rule_id: str
    user_id: str
    condition: Dict[str, Any]  # 조건
    action: Dict[str, Any]  # 액션
    priority: AlertSeverity
    is_enabled: bool
    created_at: datetime

@dataclass
class PortfolioRecommendation:
    """포트폴리오 추천"""
    recommendation_id: str
    user_id: str
    investment_style: InvestmentStyle
    recommended_stocks: List[Dict[str, Any]]
    allocation_weights: Dict[str, float]  # 종목별 비중
    expected_return: float
    risk_score: float
    reasoning: str
    confidence_score: float
    valid_until: datetime
    created_at: datetime

class SubscriptionManager:
    """구독 프리셋 관리자"""
    
    def __init__(self):
        self.users_preferences = {}  # 사용자별 선호도 저장
        self.subscription_presets = {}  # 프리셋 저장
        self.alert_rules = {}  # 알림 규칙 저장
        self.user_alert_history = {}  # 사용자별 알림 히스토리
        
        # 기본 프리셋 생성
        self._create_default_presets()
    
    def _create_default_presets(self):
        """기본 구독 프리셋 생성"""
        
        # 공격형 투자자 프리셋
        aggressive_preset = SubscriptionPreset(
            preset_id="aggressive_default",
            name="공격형 투자자",
            description="고위험 고수익을 추구하는 투자자를 위한 프리셋",
            investment_style=InvestmentStyle.AGGRESSIVE,
            default_preferences=UserPreferences(
                user_id="",
                investment_style=InvestmentStyle.AGGRESSIVE,
                risk_tolerance=0.8,
                min_signal_strength=0.6,
                max_daily_alerts=20,
                preferred_markets=["US", "KR"],
                preferred_sectors=["기술", "바이오", "신재생에너지", "암호화폐"],
                excluded_symbols=[],
                notification_channels=["push", "email"],
                trading_hours_only=False,
                weekend_alerts=True,
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            channels=["us_stocks", "ai_signals", "kr_stocks", "exchange_rates"],
            filters={
                "volatility_min": 0.15,  # 최소 변동성 15%
                "market_cap_min": 1000000000,  # 시가총액 10억 이상
                "signal_confidence_min": 0.6,
                "sectors": ["기술", "바이오", "신재생에너지"]
            },
            is_active=True,
            created_at=datetime.now()
        )
        
        # 균형형 투자자 프리셋
        balanced_preset = SubscriptionPreset(
            preset_id="balanced_default",
            name="균형형 투자자",
            description="안정성과 수익성의 균형을 추구하는 투자자를 위한 프리셋",
            investment_style=InvestmentStyle.BALANCED,
            default_preferences=UserPreferences(
                user_id="",
                investment_style=InvestmentStyle.BALANCED,
                risk_tolerance=0.5,
                min_signal_strength=0.7,
                max_daily_alerts=10,
                preferred_markets=["US", "KR"],
                preferred_sectors=["IT", "금융", "소비재", "헬스케어"],
                excluded_symbols=[],
                notification_channels=["email", "push"],
                trading_hours_only=True,
                weekend_alerts=False,
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            channels=["us_stocks", "ai_signals", "market_status"],
            filters={
                "volatility_max": 0.25,  # 최대 변동성 25%
                "market_cap_min": 5000000000,  # 시가총액 50억 이상
                "signal_confidence_min": 0.7,
                "pe_ratio_max": 30
            },
            is_active=True,
            created_at=datetime.now()
        )
        
        # 안정형 투자자 프리셋
        conservative_preset = SubscriptionPreset(
            preset_id="conservative_default",
            name="안정형 투자자",
            description="안정성을 최우선으로 하는 보수적 투자자를 위한 프리셋",
            investment_style=InvestmentStyle.CONSERVATIVE,
            default_preferences=UserPreferences(
                user_id="",
                investment_style=InvestmentStyle.CONSERVATIVE,
                risk_tolerance=0.2,
                min_signal_strength=0.8,
                max_daily_alerts=5,
                preferred_markets=["US"],
                preferred_sectors=["유틸리티", "소비재", "통신", "금융"],
                excluded_symbols=[],
                notification_channels=["email"],
                trading_hours_only=True,
                weekend_alerts=False,
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            channels=["us_stocks", "market_status"],
            filters={
                "volatility_max": 0.15,  # 최대 변동성 15%
                "market_cap_min": 10000000000,  # 시가총액 100억 이상
                "signal_confidence_min": 0.8,
                "dividend_yield_min": 0.02,  # 배당수익률 2% 이상
                "debt_ratio_max": 0.5
            },
            is_active=True,
            created_at=datetime.now()
        )
        
        self.subscription_presets = {
            "aggressive_default": aggressive_preset,
            "balanced_default": balanced_preset,
            "conservative_default": conservative_preset
        }

    def create_user_preferences(self, user_id: str, preset_id: str, 
                              custom_preferences: Optional[Dict[str, Any]] = None) -> UserPreferences:
        """사용자 선호도 생성"""
        
        if preset_id not in self.subscription_presets:
            raise ValueError(f"프리셋 '{preset_id}'를 찾을 수 없습니다.")
        
        preset = self.subscription_presets[preset_id]
        preferences = preset.default_preferences
        preferences.user_id = user_id
        
        # 커스텀 설정 적용
        if custom_preferences:
            for key, value in custom_preferences.items():
                if hasattr(preferences, key):
                    setattr(preferences, key, value)
        
        preferences.updated_at = datetime.now()
        self.users_preferences[user_id] = preferences
        
        logger.info(f"사용자 {user_id}의 선호도 생성 완료 (프리셋: {preset_id})")
        return preferences

    def update_user_preferences(self, user_id: str, updates: Dict[str, Any]) -> UserPreferences:
        """사용자 선호도 업데이트"""
        
        if user_id not in self.users_preferences:
            raise ValueError(f"사용자 '{user_id}'의 선호도를 찾을 수 없습니다.")
        
        preferences = self.users_preferences[user_id]
        
        for key, value in updates.items():
            if hasattr(preferences, key):
                setattr(preferences, key, value)
            else:
                logger.warning(f"알 수 없는 선호도 항목: {key}")
        
        preferences.updated_at = datetime.now()
        
        logger.info(f"사용자 {user_id}의 선호도 업데이트 완료")
        return preferences

    def should_send_alert(self, user_id: str, signal_data: Dict[str, Any]) -> tuple[bool, str]:
        """알림 전송 여부 결정"""
        
        if user_id not in self.users_preferences:
            return False, "사용자 선호도가 설정되지 않음"
        
        preferences = self.users_preferences[user_id]
        
        # 시그널 강도 체크
        signal_confidence = signal_data.get('confidence', 0.0)
        if signal_confidence < preferences.min_signal_strength:
            return False, f"시그널 강도 부족 ({signal_confidence:.2f} < {preferences.min_signal_strength:.2f})"
        
        # 시장 체크
        market = signal_data.get('market', '')
        if market and market not in preferences.preferred_markets:
            return False, f"선호하지 않는 시장: {market}"
        
        # 섹터 체크
        sector = signal_data.get('sector', '')
        if sector and preferences.preferred_sectors and sector not in preferences.preferred_sectors:
            return False, f"선호하지 않는 섹터: {sector}"
        
        # 제외 종목 체크
        symbol = signal_data.get('symbol', '')
        if symbol in preferences.excluded_symbols:
            return False, f"제외된 종목: {symbol}"
        
        # 일일 알림 수 체크
        today = datetime.now().date()
        user_alerts_today = self.user_alert_history.get(user_id, {}).get(str(today), 0)
        if user_alerts_today >= preferences.max_daily_alerts:
            return False, f"일일 알림 한도 초과 ({user_alerts_today}/{preferences.max_daily_alerts})"
        
        # 거래 시간 체크
        if preferences.trading_hours_only:
            current_hour = datetime.now().hour
            if not (9 <= current_hour <= 16):  # 간단한 거래 시간 체크
                return False, "거래 시간 외"
        
        # 주말 체크
        if not preferences.weekend_alerts:
            if datetime.now().weekday() >= 5:  # 토요일, 일요일
                return False, "주말 알림 비활성화"
        
        return True, "알림 조건 만족"

    def filter_signals_by_preferences(self, user_id: str, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """사용자 선호도에 따른 시그널 필터링"""
        
        if user_id not in self.users_preferences:
            logger.warning(f"사용자 {user_id}의 선호도가 없어 필터링하지 않음")
            return signals
        
        preferences = self.users_preferences[user_id]
        filtered_signals = []
        
        for signal in signals:
            should_send, reason = self.should_send_alert(user_id, signal)
            if should_send:
                # 사용자 위험 성향에 따른 가중치 적용
                risk_multiplier = self._calculate_risk_multiplier(preferences.risk_tolerance, signal)
                signal['user_risk_score'] = signal.get('risk_level', 0.5) * risk_multiplier
                signal['personalized_confidence'] = min(1.0, signal.get('confidence', 0.5) * 1.2 if 
                                                       signal.get('sector') in preferences.preferred_sectors else 
                                                       signal.get('confidence', 0.5))
                filtered_signals.append(signal)
            else:
                logger.debug(f"시그널 필터링됨 ({signal.get('symbol', 'Unknown')}): {reason}")
        
        # 선호도별 정렬
        filtered_signals.sort(key=lambda x: (
            x.get('personalized_confidence', 0),
            -x.get('user_risk_score', 0) if preferences.investment_style == InvestmentStyle.AGGRESSIVE else x.get('user_risk_score', 1),
            x.get('impact_score', 0)
        ), reverse=True)
        
        logger.info(f"사용자 {user_id}: {len(signals)}개 시그널 중 {len(filtered_signals)}개 필터링 통과")
        return filtered_signals

    def _calculate_risk_multiplier(self, risk_tolerance: float, signal_data: Dict[str, Any]) -> float:
        """위험 성향에 따른 가중치 계산"""
        base_risk = signal_data.get('risk_level', 0.5)
        
        if risk_tolerance > 0.7:  # 고위험 선호
            return 1.2 if base_risk > 0.6 else 0.8
        elif risk_tolerance < 0.3:  # 저위험 선호
            return 0.8 if base_risk > 0.6 else 1.2
        else:  # 중위험 선호
            return 1.0

    def generate_portfolio_recommendation(self, user_id: str, 
                                        available_stocks: List[Dict[str, Any]]) -> PortfolioRecommendation:
        """포트폴리오 추천 생성"""
        
        if user_id not in self.users_preferences:
            raise ValueError(f"사용자 '{user_id}'의 선호도가 설정되지 않음")
        
        preferences = self.users_preferences[user_id]
        investment_style = preferences.investment_style
        
        # 사용자 선호도에 따른 종목 필터링
        filtered_stocks = self.filter_signals_by_preferences(user_id, available_stocks)
        
        # 투자 성향별 포트폴리오 구성
        if investment_style == InvestmentStyle.AGGRESSIVE:
            # 공격형: 고성장주 위주, 집중 투자
            selected_stocks = filtered_stocks[:5]  # 상위 5개 종목
            base_weights = [0.3, 0.25, 0.2, 0.15, 0.1]
            expected_return = 0.15  # 15% 기대수익률
            risk_score = 0.8
            reasoning = "고성장 기술주와 신흥 섹터 중심의 공격적 포트폴리오입니다. 높은 변동성과 함께 높은 수익을 기대할 수 있습니다."
            
        elif investment_style == InvestmentStyle.BALANCED:
            # 균형형: 대형주와 안정주 혼합
            selected_stocks = filtered_stocks[:8]  # 상위 8개 종목
            base_weights = [0.2, 0.18, 0.15, 0.13, 0.12, 0.1, 0.08, 0.04]
            expected_return = 0.10  # 10% 기대수익률
            risk_score = 0.5
            reasoning = "성장성과 안정성의 균형을 맞춘 포트폴리오입니다. 적절한 위험 수준에서 꾸준한 수익을 추구합니다."
            
        else:  # CONSERVATIVE
            # 안정형: 대형 우량주, 배당주 위주
            selected_stocks = filtered_stocks[:10]  # 상위 10개 종목
            base_weights = [0.15, 0.14, 0.12, 0.11, 0.1, 0.1, 0.09, 0.08, 0.07, 0.04]
            expected_return = 0.06  # 6% 기대수익률
            risk_score = 0.3
            reasoning = "안정적인 대형주와 배당주 중심의 보수적 포트폴리오입니다. 낮은 변동성으로 꾸준한 수익을 추구합니다."
        
        # 실제 종목 수에 맞게 가중치 조정
        actual_count = min(len(selected_stocks), len(base_weights))
        if actual_count == 0:
            raise ValueError("추천할 종목이 없습니다.")
        
        selected_stocks = selected_stocks[:actual_count]
        weights = base_weights[:actual_count]
        
        # 가중치 정규화
        total_weight = sum(weights)
        normalized_weights = [w/total_weight for w in weights]
        
        # 종목별 할당 비중 딕셔너리 생성
        allocation_weights = {}
        recommended_stocks = []
        
        for i, stock in enumerate(selected_stocks):
            symbol = stock.get('symbol', f'STOCK_{i}')
            weight = normalized_weights[i]
            allocation_weights[symbol] = weight
            
            recommended_stocks.append({
                'symbol': symbol,
                'company_name': stock.get('company_name', 'Unknown'),
                'weight': weight,
                'current_price': stock.get('current_price', 0),
                'expected_return': stock.get('expected_return', expected_return),
                'confidence': stock.get('personalized_confidence', stock.get('confidence', 0.5)),
                'reason': stock.get('reasoning', '데이터 기반 추천'),
                'sector': stock.get('sector', 'Unknown')
            })
        
        # 신뢰도 점수 계산
        avg_confidence = sum(stock.get('confidence', 0.5) for stock in recommended_stocks) / len(recommended_stocks)
        confidence_score = min(0.95, avg_confidence * 1.1)  # 최대 95%
        
        recommendation = PortfolioRecommendation(
            recommendation_id=str(uuid.uuid4()),
            user_id=user_id,
            investment_style=investment_style,
            recommended_stocks=recommended_stocks,
            allocation_weights=allocation_weights,
            expected_return=expected_return,
            risk_score=risk_score,
            reasoning=reasoning,
            confidence_score=confidence_score,
            valid_until=datetime.now() + timedelta(days=7),  # 7일간 유효
            created_at=datetime.now()
        )
        
        logger.info(f"사용자 {user_id}의 {investment_style.value} 포트폴리오 추천 생성 완료 ({len(recommended_stocks)}개 종목)")
        return recommendation

    def record_alert_sent(self, user_id: str):
        """알림 전송 기록"""
        today = str(datetime.now().date())
        
        if user_id not in self.user_alert_history:
            self.user_alert_history[user_id] = {}
        
        if today not in self.user_alert_history[user_id]:
            self.user_alert_history[user_id][today] = 0
        
        self.user_alert_history[user_id][today] += 1

    def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """사용자 통계 조회"""
        
        if user_id not in self.users_preferences:
            return {"error": "사용자 선호도가 설정되지 않음"}
        
        preferences = self.users_preferences[user_id]
        today = str(datetime.now().date())
        alerts_today = self.user_alert_history.get(user_id, {}).get(today, 0)
        
        # 최근 7일간 알림 수
        alerts_week = 0
        for i in range(7):
            date_key = str((datetime.now() - timedelta(days=i)).date())
            alerts_week += self.user_alert_history.get(user_id, {}).get(date_key, 0)
        
        return {
            "user_id": user_id,
            "investment_style": preferences.investment_style.value,
            "risk_tolerance": preferences.risk_tolerance,
            "min_signal_strength": preferences.min_signal_strength,
            "alerts_today": alerts_today,
            "max_daily_alerts": preferences.max_daily_alerts,
            "alerts_this_week": alerts_week,
            "preferred_markets": preferences.preferred_markets,
            "preferred_sectors": preferences.preferred_sectors,
            "notification_channels": preferences.notification_channels,
            "last_updated": preferences.updated_at.isoformat()
        }

    def get_all_presets(self) -> Dict[str, Dict[str, Any]]:
        """모든 프리셋 조회"""
        return {
            preset_id: {
                "name": preset.name,
                "description": preset.description,
                "investment_style": preset.investment_style.value,
                "channels": preset.channels,
                "filters": preset.filters,
                "is_active": preset.is_active
            }
            for preset_id, preset in self.subscription_presets.items()
        }

# 구독 관리자 인스턴스 생성용 팩토리 함수
def create_subscription_manager() -> SubscriptionManager:
    """구독 관리자 인스턴스 생성"""
    return SubscriptionManager()