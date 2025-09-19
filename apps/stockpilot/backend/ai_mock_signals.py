#!/usr/bin/env python3
"""
Mock AI Signal Generator for Rate Limit Fallback
E2E 테스트 지원용 Mock 데이터 생성기
"""

import hashlib
import random
from datetime import datetime, timezone
from typing import List, Dict


def generate_mock_ai_signals(counter: int = 1) -> List[Dict]:
    """Rate Limit 시 사용할 Mock AI 시그널 생성"""
    
    # 주요 종목들
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    signals = []
    
    random.seed(counter)  # 일관된 무작위 수
    
    for i, symbol in enumerate(symbols[:2]):  # 2개 시그널
        # 학습된 패턴 기반 Mock 데이터
        signal_types = ["BUY", "SELL", "HOLD"]
        signal_type = signal_types[counter % 3]
        
        confidence = 0.65 + (random.random() * 0.3)  # 0.65 ~ 0.95
        current_price = 200 + (random.random() * 300)  # $200-500
        target_price = current_price * (1 + (random.random() * 0.2 - 0.1))  # ±10%
        expected_return = ((target_price - current_price) / current_price) * 100
        
        signal = {
            'id': hashlib.md5(f"mock_{symbol}_{counter}".encode()).hexdigest(),
            'symbol': symbol,
            'company_name': f'{symbol} Inc.',
            'signal_type': signal_type,
            'confidence': round(confidence, 2),
            'strength': 'HIGH' if confidence > 0.8 else 'MEDIUM',
            'current_price': round(current_price, 2),
            'target_price': round(target_price, 2),
            'expected_return': round(expected_return, 1),
            'risk_level': 'MEDIUM',
            'reasoning': f'고도화된 AI 기술적 분석에 따르면 {symbol} 주식은 현재 {signal_type.lower()} 시그널을 보여주고 있습니다. 신뢰도 {confidence:.0%}로 평가됩니다. (테스트 모드)',
            'technical_score': round((random.random() * 2) - 1, 2),  # -1 ~ 1
            'fundamental_score': round((random.random() * 2) - 1, 2),
            'sentiment_score': round((random.random() * 2) - 1, 2),
            'created_at': datetime.now(timezone.utc).isoformat(),
            'market_state': 'CLOSED'
        }
        signals.append(signal)
    
    return signals


def test_mock_signals():
    """Mock 시그널 테스트"""
    print("=== Mock AI Signal Generator Test ===")
    
    for i in range(3):
        signals = generate_mock_ai_signals(i + 1)
        print(f"\nTest {i + 1}:")
        for signal in signals:
            print(f"  {signal['symbol']}: {signal['signal_type']} ({signal['confidence']}) - {signal['reasoning'][:50]}...")


if __name__ == "__main__":
    test_mock_signals()