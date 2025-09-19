"""
주식 데이터 분석 엔진
기술적 지표 계산, 가격 예측, 패턴 분석 등의 기능 제공
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import yfinance as yf
import ta
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
import joblib
import logging

logger = logging.getLogger(__name__)


class StockAnalyzer:
    """
    주식 분석 메인 클래스
    """
    
    def __init__(self):
        self.scaler = MinMaxScaler()
        self.model = None
        
    def fetch_stock_data(self, symbol: str, period: str = "1y") -> pd.DataFrame:
        """
        야후 파이낸스에서 주식 데이터 가져오기
        
        Args:
            symbol: 주식 심볼 (예: "AAPL", "005930.KS")
            period: 기간 ("1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max")
            
        Returns:
            DataFrame: 주식 데이터 (Date, Open, High, Low, Close, Volume)
        """
        try:
            stock = yf.Ticker(symbol)
            data = stock.history(period=period)
            
            if data.empty:
                logger.warning(f"No data found for symbol: {symbol}")
                return pd.DataFrame()
                
            return data
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return pd.DataFrame()
    
    def calculate_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        기술적 지표 계산
        
        Args:
            data: 주식 데이터
            
        Returns:
            DataFrame: 기술적 지표가 추가된 데이터
        """
        if data.empty:
            return data
            
        df = data.copy()
        
        # 이동평균선
        df['MA_5'] = ta.trend.sma_indicator(df['Close'], window=5)
        df['MA_20'] = ta.trend.sma_indicator(df['Close'], window=20)
        df['MA_60'] = ta.trend.sma_indicator(df['Close'], window=60)
        
        # 지수이동평균선
        df['EMA_12'] = ta.trend.ema_indicator(df['Close'], window=12)
        df['EMA_26'] = ta.trend.ema_indicator(df['Close'], window=26)
        
        # MACD
        df['MACD'] = ta.trend.macd_diff(df['Close'])
        df['MACD_signal'] = ta.trend.macd_signal(df['Close'])
        
        # RSI
        df['RSI'] = ta.momentum.rsi(df['Close'])
        
        # 볼린저 밴드
        df['BB_upper'] = ta.volatility.bollinger_hband(df['Close'])
        df['BB_lower'] = ta.volatility.bollinger_lband(df['Close'])
        df['BB_middle'] = ta.volatility.bollinger_mavg(df['Close'])
        
        # 스토캐스틱
        df['Stoch_K'] = ta.momentum.stoch(df['High'], df['Low'], df['Close'])
        df['Stoch_D'] = ta.momentum.stoch_signal(df['High'], df['Low'], df['Close'])
        
        # ATR (Average True Range)
        df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'])
        
        # 거래량 지표
        df['Volume_MA'] = ta.volume.volume_sma(df['Close'], df['Volume'])
        df['OBV'] = ta.volume.on_balance_volume(df['Close'], df['Volume'])
        
        return df
    
    def detect_patterns(self, data: pd.DataFrame) -> Dict[str, List[datetime]]:
        """
        가격 패턴 감지
        
        Args:
            data: 기술적 지표가 포함된 주식 데이터
            
        Returns:
            Dict: 패턴별 발생 날짜 리스트
        """
        patterns = {
            'golden_cross': [],
            'death_cross': [],
            'support_break': [],
            'resistance_break': [],
            'oversold': [],
            'overbought': []
        }
        
        if data.empty or len(data) < 50:
            return patterns
            
        # 골든크로스/데드크로스 감지
        for i in range(1, len(data)):
            prev_ma5 = data.iloc[i-1]['MA_5']
            prev_ma20 = data.iloc[i-1]['MA_20']
            curr_ma5 = data.iloc[i]['MA_5']
            curr_ma20 = data.iloc[i]['MA_20']
            
            if pd.notna(prev_ma5) and pd.notna(prev_ma20) and pd.notna(curr_ma5) and pd.notna(curr_ma20):
                # 골든크로스 (단기 이평선이 장기 이평선을 상향 돌파)
                if prev_ma5 <= prev_ma20 and curr_ma5 > curr_ma20:
                    patterns['golden_cross'].append(data.index[i])
                
                # 데드크로스 (단기 이평선이 장기 이평선을 하향 돌파)
                elif prev_ma5 >= prev_ma20 and curr_ma5 < curr_ma20:
                    patterns['death_cross'].append(data.index[i])
        
        # RSI 과매수/과매도 구간
        for i, rsi in enumerate(data['RSI']):
            if pd.notna(rsi):
                if rsi <= 30:
                    patterns['oversold'].append(data.index[i])
                elif rsi >= 70:
                    patterns['overbought'].append(data.index[i])
        
        return patterns
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        매매 신호 생성
        
        Args:
            data: 기술적 지표가 포함된 주식 데이터
            
        Returns:
            DataFrame: 매매 신호가 추가된 데이터
        """
        df = data.copy()
        df['Signal'] = 0  # 0: 보유, 1: 매수, -1: 매도
        df['Position'] = 0  # 포지션
        
        if len(df) < 50:
            return df
        
        # 복합 신호 생성 로직
        for i in range(20, len(df)):
            buy_signals = 0
            sell_signals = 0
            
            # RSI 기반 신호
            if pd.notna(df.iloc[i]['RSI']):
                if df.iloc[i]['RSI'] < 30:
                    buy_signals += 1
                elif df.iloc[i]['RSI'] > 70:
                    sell_signals += 1
            
            # MACD 신호
            if (pd.notna(df.iloc[i]['MACD']) and pd.notna(df.iloc[i-1]['MACD']) and 
                pd.notna(df.iloc[i]['MACD_signal']) and pd.notna(df.iloc[i-1]['MACD_signal'])):
                
                if (df.iloc[i-1]['MACD'] <= df.iloc[i-1]['MACD_signal'] and 
                    df.iloc[i]['MACD'] > df.iloc[i]['MACD_signal']):
                    buy_signals += 1
                elif (df.iloc[i-1]['MACD'] >= df.iloc[i-1]['MACD_signal'] and 
                      df.iloc[i]['MACD'] < df.iloc[i]['MACD_signal']):
                    sell_signals += 1
            
            # 볼린저 밴드 신호
            if (pd.notna(df.iloc[i]['BB_lower']) and pd.notna(df.iloc[i]['BB_upper']) and
                pd.notna(df.iloc[i]['Close'])):
                
                if df.iloc[i]['Close'] <= df.iloc[i]['BB_lower']:
                    buy_signals += 1
                elif df.iloc[i]['Close'] >= df.iloc[i]['BB_upper']:
                    sell_signals += 1
            
            # 신호 결정
            if buy_signals >= 2:
                df.iloc[i, df.columns.get_loc('Signal')] = 1
            elif sell_signals >= 2:
                df.iloc[i, df.columns.get_loc('Signal')] = -1
        
        # 포지션 계산
        position = 0
        for i in range(len(df)):
            if df.iloc[i]['Signal'] == 1:
                position = 1
            elif df.iloc[i]['Signal'] == -1:
                position = 0
            df.iloc[i, df.columns.get_loc('Position')] = position
        
        return df
    
    def backtest_strategy(self, data: pd.DataFrame, initial_cash: float = 10000.0) -> Dict:
        """
        백테스팅 수행
        
        Args:
            data: 신호가 포함된 주식 데이터
            initial_cash: 초기 자금
            
        Returns:
            Dict: 백테스팅 결과
        """
        if 'Signal' not in data.columns:
            data = self.generate_signals(data)
        
        cash = initial_cash
        shares = 0
        transactions = []
        portfolio_values = []
        
        for i, row in data.iterrows():
            price = row['Close']
            signal = row['Signal']
            
            if signal == 1 and shares == 0 and cash > price:  # 매수
                shares = int(cash / price)
                cash -= shares * price
                transactions.append({
                    'date': i,
                    'type': 'buy',
                    'price': price,
                    'shares': shares,
                    'cash': cash
                })
            
            elif signal == -1 and shares > 0:  # 매도
                cash += shares * price
                transactions.append({
                    'date': i,
                    'type': 'sell',
                    'price': price,
                    'shares': shares,
                    'cash': cash
                })
                shares = 0
            
            # 포트폴리오 가치 계산
            portfolio_value = cash + shares * price
            portfolio_values.append(portfolio_value)
        
        # 최종 결과 계산
        final_value = cash + shares * data.iloc[-1]['Close']
        total_return = (final_value - initial_cash) / initial_cash * 100
        
        # 벤치마크 수익률 (단순 보유)
        benchmark_return = (data.iloc[-1]['Close'] - data.iloc[0]['Close']) / data.iloc[0]['Close'] * 100
        
        return {
            'initial_cash': initial_cash,
            'final_value': final_value,
            'total_return': total_return,
            'benchmark_return': benchmark_return,
            'alpha': total_return - benchmark_return,
            'num_transactions': len(transactions),
            'transactions': transactions,
            'portfolio_values': portfolio_values
        }
    
    def get_analysis(self, symbol: str) -> Dict:
        """
        종합 시장 분석 생성 (투자 권유 아님)

        Args:
            symbol: 주식 심볼

        Returns:
            Dict: 시장 분석 정보
        """
        try:
            # 데이터 가져오기 및 분석
            data = self.fetch_stock_data(symbol)
            if data.empty:
                return {'error': '데이터를 가져올 수 없습니다'}
            
            data_with_indicators = self.calculate_technical_indicators(data)
            patterns = self.detect_patterns(data_with_indicators)
            signals_data = self.generate_signals(data_with_indicators)
            backtest_result = self.backtest_strategy(signals_data)
            
            # 최신 데이터 분석
            latest = data_with_indicators.iloc[-1]
            
            signal_type = 'NEUTRAL'
            confidence = 50

            # 신호 기반 분석
            if latest['Signal'] == 1:
                signal_type = 'BULLISH_INDICATOR'
                confidence = 70
            elif latest['Signal'] == -1:
                signal_type = 'BEARISH_INDICATOR'
                confidence = 70
            
            # 추가 분석 요소들
            analysis_points = []
            
            if pd.notna(latest['RSI']):
                if latest['RSI'] < 30:
                    analysis_points.append("RSI 지표가 과매도 구간에 있습니다 (참고용)")
                elif latest['RSI'] > 70:
                    analysis_points.append("RSI 지표가 과매수 구간에 있습니다 (참고용)")
            
            if len(patterns['golden_cross']) > 0:
                last_golden_cross = max(patterns['golden_cross'])
                if (datetime.now().date() - last_golden_cross.date()).days <= 5:
                    analysis_points.append("최근 골든크로스 패턴이 감지되었습니다 (참고용)")
            
            return {
                'symbol': symbol,
                'analysis_type': signal_type,
                'confidence': confidence,
                'current_price': latest['Close'],
                'analysis_points': analysis_points,
                'patterns': patterns,
                'backtest_performance': backtest_result['total_return'],
                'technical_indicators': {
                    'RSI': latest['RSI'],
                    'MACD': latest['MACD'],
                    'MA_20': latest['MA_20'],
                    'BB_position': 'middle'  # 볼린저 밴드 위치
                },
                'disclaimer': '본 정보는 투자 참고 자료이며, 투자 결정은 이용자 책임입니다'
            }
            
        except Exception as e:
            logger.error(f"Error generating analysis for {symbol}: {str(e)}")
            return {'error': f'분석 생성 중 오류가 발생했습니다: {str(e)}', 'disclaimer': '본 정보는 투자 참고 자료이며, 투자 결정은 이용자 책임입니다'}