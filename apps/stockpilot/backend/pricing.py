#!/usr/bin/env python3
"""
StockPilot AI 구독 모델 관리 시스템
투자자문업 규제 준수를 위한 가격 정책 구현
"""
from enum import Enum
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class SubscriptionTier(Enum):
    """구독 등급 정의"""
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    PREMIUM = "premium"

class PricingPlan:
    """가격 정책 클래스"""

    PLANS = {
        SubscriptionTier.FREE: {
            "name": "무료 플랜",
            "price": 0,
            "currency": "KRW",
            "billing_cycle": "monthly",
            "features": {
                "basic_quotes": True,
                "ai_analysis": 0,  # 월 0회
                "realtime_alerts": False,
                "advanced_charts": False,
                "api_calls_per_day": 100
            },
            "description": "기본 시세 정보만 제공"
        },
        SubscriptionTier.BASIC: {
            "name": "베이직 플랜",
            "price": 19900,
            "currency": "KRW",
            "billing_cycle": "monthly",
            "features": {
                "basic_quotes": True,
                "ai_analysis": 10,  # 월 10회
                "realtime_alerts": False,
                "advanced_charts": True,
                "api_calls_per_day": 500
            },
            "description": "AI 기반 분석 서비스 월 10회 제공"
        },
        SubscriptionTier.PRO: {
            "name": "프로 플랜",
            "price": 49900,
            "currency": "KRW",
            "billing_cycle": "monthly",
            "features": {
                "basic_quotes": True,
                "ai_analysis": -1,  # 무제한
                "realtime_alerts": True,
                "advanced_charts": True,
                "api_calls_per_day": 2000
            },
            "description": "AI 분석 무제한 + 고급 차트 분석"
        },
        SubscriptionTier.PREMIUM: {
            "name": "프리미엄 플랜",
            "price": 99900,
            "currency": "KRW",
            "billing_cycle": "monthly",
            "features": {
                "basic_quotes": True,
                "ai_analysis": -1,  # 무제한
                "realtime_alerts": True,
                "advanced_charts": True,
                "api_calls_per_day": 10000,
                "priority_support": True,
                "custom_indicators": True
            },
            "description": "실시간 알림 + 프리미엄 지원 포함"
        }
    }

    @classmethod
    def get_plan(cls, tier: SubscriptionTier) -> Dict:
        """특정 플랜 정보 조회"""
        return cls.PLANS.get(tier, cls.PLANS[SubscriptionTier.FREE])

    @classmethod
    def get_all_plans(cls) -> Dict:
        """모든 플랜 정보 조회"""
        return cls.PLANS

    @classmethod
    def validate_feature_access(cls, user_tier: SubscriptionTier, feature: str) -> bool:
        """사용자 플랜에서 특정 기능 접근 가능 여부 확인"""
        plan = cls.get_plan(user_tier)
        return plan["features"].get(feature, False)

class UsageTracker:
    """사용량 추적 클래스"""

    def __init__(self):
        # 실제 구현에서는 데이터베이스 사용
        self.usage_data = {}

    def track_api_call(self, user_id: str, endpoint: str) -> bool:
        """API 호출 추적 및 제한 검증"""
        today = datetime.now().date()
        key = f"{user_id}:{today}"

        if key not in self.usage_data:
            self.usage_data[key] = {"api_calls": 0, "ai_analysis": 0}

        self.usage_data[key]["api_calls"] += 1

        # 사용자 플랜에 따른 제한 확인
        # 실제 구현에서는 데이터베이스에서 사용자 플랜 조회
        return True

    def track_ai_analysis(self, user_id: str) -> bool:
        """AI 분석 사용량 추적"""
        today = datetime.now().date()
        key = f"{user_id}:{today}"

        if key not in self.usage_data:
            self.usage_data[key] = {"api_calls": 0, "ai_analysis": 0}

        self.usage_data[key]["ai_analysis"] += 1
        return True

    def get_usage_stats(self, user_id: str) -> Dict:
        """사용자 이용 통계 조회"""
        today = datetime.now().date()
        key = f"{user_id}:{today}"

        return self.usage_data.get(key, {"api_calls": 0, "ai_analysis": 0})

class ComplianceManager:
    """규제 준수 관리자"""

    DISCLAIMERS = {
        "general": "본 정보는 투자 참고 자료이며, 투자 결정은 이용자 책임입니다",
        "analysis": "AI 분석 결과는 참고용이며, 투자 권유가 아닙니다",
        "signals": "기술적 신호는 교육 목적이며, 실제 투자 결정에 활용하지 마시기 바랍니다"
    }

    @classmethod
    def get_disclaimer(cls, content_type: str) -> str:
        """콘텐츠 유형별 면책조항 반환"""
        return cls.DISCLAIMERS.get(content_type, cls.DISCLAIMERS["general"])

    @classmethod
    def validate_content(cls, content: Dict) -> Dict:
        """콘텐츠 규제 준수 검증 및 면책조항 추가"""
        # 투자 권유 키워드 필터링
        prohibited_words = ["매수 권유", "매도 권유", "투자 추천", "확실한 수익"]

        content_str = str(content).lower()
        for word in prohibited_words:
            if word in content_str:
                logger.warning(f"규제 위반 가능 키워드 감지: {word}")

        # 면책조항 추가
        content["disclaimer"] = cls.get_disclaimer("general")
        content["compliance_timestamp"] = datetime.now().isoformat()

        return content

# 전역 인스턴스
usage_tracker = UsageTracker()
pricing_manager = PricingPlan()
compliance_manager = ComplianceManager()

def format_price(price: int, currency: str = "KRW") -> str:
    """가격 포맷팅 유틸리티"""
    if currency == "KRW":
        return f"{price:,}원"
    return f"{price} {currency}"

def calculate_upgrade_savings(current_tier: SubscriptionTier, target_tier: SubscriptionTier) -> Dict:
    """플랜 업그레이드 시 절약액 계산"""
    current_plan = pricing_manager.get_plan(current_tier)
    target_plan = pricing_manager.get_plan(target_tier)

    price_diff = target_plan["price"] - current_plan["price"]

    return {
        "current_plan": current_plan["name"],
        "target_plan": target_plan["name"],
        "price_difference": price_diff,
        "formatted_difference": format_price(price_diff),
        "additional_features": []  # 추가 기능 목록
    }

if __name__ == "__main__":
    # 테스트 코드
    print("StockPilot AI 구독 모델 시스템")
    print("=" * 40)

    for tier in SubscriptionTier:
        plan = pricing_manager.get_plan(tier)
        print(f"\n{plan['name']} - {format_price(plan['price'])}")
        print(f"  AI 분석: {plan['features']['ai_analysis']}회/월")
        print(f"  설명: {plan['description']}")