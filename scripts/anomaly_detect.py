#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔎 이상탐지 및 예측 리포트 스크립트 (한국어 주석 포함)

목적: 메트릭 데이터에서 이상치를 탐지하고 향후 7일간의 위험 구간을 예측
입력: reports/metrics/*.json, logs/*.log, reports/ci_reports/*.json
출력: Markdown/JSON 형식의 종합 리포트

주요 기능:
- 데이터 전처리: 누락값/이상값 처리, 이동평균(EWMA) 스무딩
- 이상탐지: 롤링 윈도우 기반 Z-score 분석 (임계치 기본 3.0)
- 예측: 선형회귀 추세 분석 + EWMA를 통한 7일 전망치 생성
- 위험도 평가: 지표별 위험 등급 및 향후 예상 이상치 구간 제공

작성자: MCP Map Company 운영팀
생성일: 2024년 연간 운영 리포트 자동화 프로젝트
"""

import os
import sys
import json
import argparse
import logging
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Union
import warnings

# 과학적 계산 및 데이터 처리
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error

# 경고 메시지 무시 (numpy/pandas 호환성)
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

# 로깅 설정 (한국어 메시지)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/anomaly_detect.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class AnomalyDetector:
    """
    이상탐지 및 예측 분석 엔진 (한국어 주석 포함)

    주요 알고리즘:
    1. 전처리: 누락값 보간, 이상값 제거, EWMA 스무딩
    2. 이상탐지: 롤링 윈도우 Z-score (|z| > threshold)
    3. 예측: Linear Regression + EWMA 조합으로 7일 전망
    """

    def __init__(self,
                 window_size: int = 7,
                 threshold: float = 3.0,
                 forecast_days: int = 7,
                 ewma_alpha: float = 0.3):
        """
        이상탐지 엔진 초기화

        Args:
            window_size: 롤링 윈도우 크기 (기본 7일)
            threshold: Z-score 임계치 (기본 3.0, 99.7% 신뢰구간)
            forecast_days: 예측 기간 (기본 7일)
            ewma_alpha: EWMA 평활화 계수 (0.1~0.5 권장)
        """
        self.window_size = window_size
        self.threshold = threshold
        self.forecast_days = forecast_days
        self.ewma_alpha = ewma_alpha

        # 내부 상태 변수
        self.metrics_data = {}
        self.anomalies = {}
        self.forecasts = {}
        self.risk_levels = {}

        logger.info(f"🔎 이상탐지 엔진 초기화: window={window_size}, threshold={threshold}, forecast={forecast_days}일")

    def load_metric_sources(self,
                           metrics_dir: str = "reports/metrics",
                           logs_dir: str = "logs",
                           ci_reports_dir: str = "reports/ci_reports") -> Dict[str, pd.DataFrame]:
        """
        다양한 소스에서 메트릭 데이터를 로드하고 통합

        Args:
            metrics_dir: 메트릭 JSON 파일들이 있는 디렉토리
            logs_dir: 로그 파일들이 있는 디렉토리
            ci_reports_dir: CI 리포트 JSON 파일들이 있는 디렉토리

        Returns:
            Dict[str, pd.DataFrame]: 지표명별 시계열 데이터
        """
        logger.info("📊 메트릭 데이터 소스 로딩 시작")

        all_data = {}

        try:
            # 1. 메트릭 JSON 파일들 처리
            metrics_path = Path(metrics_dir)
            if metrics_path.exists():
                for json_file in metrics_path.glob("*.json"):
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)

                        # JSON 구조에 따라 시계열 데이터 추출
                        df = self._parse_metrics_json(data, json_file.stem)
                        if df is not None and not df.empty:
                            all_data[f"metrics_{json_file.stem}"] = df
                            logger.info(f"✅ 메트릭 파일 로드: {json_file.name} ({len(df)} 레코드)")

                    except Exception as e:
                        logger.warning(f"⚠️ 메트릭 파일 로드 실패: {json_file.name} - {str(e)}")

            # 2. 로그 파일들에서 수치 메트릭 추출
            logs_path = Path(logs_dir)
            if logs_path.exists():
                for log_file in logs_path.glob("*.log"):
                    try:
                        df = self._parse_log_file(log_file)
                        if df is not None and not df.empty:
                            all_data[f"logs_{log_file.stem}"] = df
                            logger.info(f"✅ 로그 파일 분석: {log_file.name} ({len(df)} 메트릭)")

                    except Exception as e:
                        logger.warning(f"⚠️ 로그 파일 분석 실패: {log_file.name} - {str(e)}")

            # 3. CI 리포트 JSON 파일들 처리
            ci_path = Path(ci_reports_dir)
            if ci_path.exists():
                for ci_file in ci_path.glob("*.json"):
                    try:
                        with open(ci_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)

                        df = self._parse_ci_report_json(data, ci_file.stem)
                        if df is not None and not df.empty:
                            all_data[f"ci_{ci_file.stem}"] = df
                            logger.info(f"✅ CI 리포트 로드: {ci_file.name} ({len(df)} 메트릭)")

                    except Exception as e:
                        logger.warning(f"⚠️ CI 리포트 로드 실패: {ci_file.name} - {str(e)}")

            logger.info(f"📊 총 {len(all_data)}개 데이터 소스 로드 완료")
            self.metrics_data = all_data
            return all_data

        except Exception as e:
            logger.error(f"❌ 메트릭 데이터 로딩 중 오류: {str(e)}")
            return {}

    def _parse_metrics_json(self, data: Dict, filename: str) -> Optional[pd.DataFrame]:
        """
        메트릭 JSON 파일을 파싱하여 시계열 DataFrame으로 변환

        Args:
            data: JSON 데이터
            filename: 파일명 (메트릭 이름으로 사용)

        Returns:
            pd.DataFrame: timestamp, value 컬럼을 가진 시계열 데이터
        """
        try:
            records = []

            # 다양한 JSON 구조 지원
            if isinstance(data, list):
                # [{"timestamp": "...", "value": ...}, ...] 형태
                for item in data:
                    if isinstance(item, dict) and 'timestamp' in item:
                        timestamp = pd.to_datetime(item['timestamp'])

                        # 여러 값 필드 지원
                        for key, value in item.items():
                            if key != 'timestamp' and isinstance(value, (int, float)):
                                records.append({
                                    'timestamp': timestamp,
                                    'metric': f"{filename}_{key}",
                                    'value': float(value)
                                })

            elif isinstance(data, dict):
                # {"metric_name": {"2024-01-01": value, ...}} 형태
                for metric_name, time_series in data.items():
                    if isinstance(time_series, dict):
                        for date_str, value in time_series.items():
                            try:
                                timestamp = pd.to_datetime(date_str)
                                if isinstance(value, (int, float)):
                                    records.append({
                                        'timestamp': timestamp,
                                        'metric': f"{filename}_{metric_name}",
                                        'value': float(value)
                                    })
                            except:
                                continue

            if records:
                df = pd.DataFrame(records)
                df = df.sort_values('timestamp')
                return df

            return None

        except Exception as e:
            logger.warning(f"JSON 파싱 오류 ({filename}): {str(e)}")
            return None

    def _parse_log_file(self, log_file: Path) -> Optional[pd.DataFrame]:
        """
        로그 파일에서 수치 메트릭을 추출

        Args:
            log_file: 로그 파일 경로

        Returns:
            pd.DataFrame: 추출된 수치 메트릭들
        """
        try:
            import re

            records = []
            metric_patterns = [
                # 일반적인 메트릭 패턴들
                r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}).*?cpu[_\s]*usage[:\s]*(\d+\.?\d*)%?',
                r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}).*?memory[_\s]*usage[:\s]*(\d+\.?\d*)%?',
                r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}).*?disk[_\s]*usage[:\s]*(\d+\.?\d*)%?',
                r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}).*?response[_\s]*time[:\s]*(\d+\.?\d*)(ms|s)?',
                r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}).*?blocked[_\s]*ips?[:\s]*(\d+)',
                r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}).*?requests?[_\s]*count[:\s]*(\d+)',
            ]

            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    if line_num > 50000:  # 성능을 위해 50K 라인으로 제한
                        break

                    for pattern in metric_patterns:
                        matches = re.findall(pattern, line, re.IGNORECASE)
                        for match in matches:
                            try:
                                timestamp_str = match[0]
                                value = float(match[1])

                                timestamp = pd.to_datetime(timestamp_str)
                                metric_name = f"log_{log_file.stem}_{pattern.split('.*?')[1].split('[')[0]}"

                                records.append({
                                    'timestamp': timestamp,
                                    'metric': metric_name,
                                    'value': value
                                })
                            except:
                                continue

            if records:
                df = pd.DataFrame(records)
                df = df.sort_values('timestamp')
                return df

            return None

        except Exception as e:
            logger.warning(f"로그 파일 분석 오류 ({log_file.name}): {str(e)}")
            return None

    def _parse_ci_report_json(self, data: Dict, filename: str) -> Optional[pd.DataFrame]:
        """
        CI 리포트 JSON에서 시계열 메트릭 추출

        Args:
            data: CI 리포트 JSON 데이터
            filename: 파일명

        Returns:
            pd.DataFrame: CI 관련 시계열 메트릭
        """
        try:
            records = []

            # CI 리포트에서 추출할 메트릭들
            ci_metrics = [
                'build_duration_seconds', 'test_duration_seconds', 'success_rate',
                'test_coverage_percent', 'build_size_mb', 'deployment_time_seconds'
            ]

            if isinstance(data, dict):
                # 타임스탬프 찾기
                timestamp = None
                for key in ['timestamp', 'created_at', 'build_time', 'date']:
                    if key in data:
                        try:
                            timestamp = pd.to_datetime(data[key])
                            break
                        except:
                            continue

                if timestamp is None:
                    # 파일명에서 날짜 추출 시도
                    import re
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
                    if date_match:
                        timestamp = pd.to_datetime(date_match.group(1))
                    else:
                        timestamp = datetime.now()

                # 메트릭 값들 추출
                for metric in ci_metrics:
                    value = self._extract_nested_value(data, metric)
                    if value is not None and isinstance(value, (int, float)):
                        records.append({
                            'timestamp': timestamp,
                            'metric': f"ci_{filename}_{metric}",
                            'value': float(value)
                        })

            if records:
                df = pd.DataFrame(records)
                return df

            return None

        except Exception as e:
            logger.warning(f"CI 리포트 파싱 오류 ({filename}): {str(e)}")
            return None

    def _extract_nested_value(self, data: Dict, key: str) -> Optional[Union[int, float]]:
        """
        중첩된 딕셔너리에서 키 값을 재귀적으로 추출

        Args:
            data: 딕셔너리 데이터
            key: 찾을 키

        Returns:
            찾은 값 또는 None
        """
        if isinstance(data, dict):
            if key in data:
                return data[key]

            for value in data.values():
                if isinstance(value, dict):
                    result = self._extract_nested_value(value, key)
                    if result is not None:
                        return result

        return None

    def preprocess_data(self) -> Dict[str, pd.DataFrame]:
        """
        로드된 메트릭 데이터를 전처리

        전처리 단계:
        1. 누락값 보간 (선형 보간)
        2. 이상값 제거 (IQR 방법)
        3. EWMA 스무딩 적용
        4. 표준화 (Z-score 계산용)

        Returns:
            Dict[str, pd.DataFrame]: 전처리된 메트릭 데이터
        """
        logger.info("🔧 메트릭 데이터 전처리 시작")

        processed_data = {}

        for source_name, df in self.metrics_data.items():
            try:
                if df.empty:
                    continue

                # 메트릭별로 그룹화하여 처리
                for metric_name in df['metric'].unique():
                    metric_df = df[df['metric'] == metric_name].copy()
                    metric_df = metric_df.sort_values('timestamp')

                    # 1. 누락값 처리 (선형 보간)
                    metric_df['value'] = metric_df['value'].interpolate(method='linear')
                    metric_df = metric_df.dropna()

                    if len(metric_df) < self.window_size:
                        continue  # 데이터가 너무 적으면 스킵

                    # 2. 이상값 제거 (IQR 방법)
                    Q1 = metric_df['value'].quantile(0.25)
                    Q3 = metric_df['value'].quantile(0.75)
                    IQR = Q3 - Q1
                    lower_bound = Q1 - 1.5 * IQR
                    upper_bound = Q3 + 1.5 * IQR

                    # 극단적 이상값만 제거 (90% 이상 데이터 보존)
                    outlier_mask = (metric_df['value'] < lower_bound - IQR) | (metric_df['value'] > upper_bound + IQR)
                    metric_df = metric_df[~outlier_mask]

                    # 3. EWMA 스무딩 적용
                    metric_df['ewma'] = metric_df['value'].ewm(alpha=self.ewma_alpha).mean()

                    # 4. 롤링 통계 계산 (Z-score용)
                    metric_df['rolling_mean'] = metric_df['ewma'].rolling(window=self.window_size, min_periods=1).mean()
                    metric_df['rolling_std'] = metric_df['ewma'].rolling(window=self.window_size, min_periods=1).std()

                    # 5. Z-score 계산
                    metric_df['z_score'] = (metric_df['ewma'] - metric_df['rolling_mean']) / (metric_df['rolling_std'] + 1e-8)

                    if len(metric_df) > 0:
                        processed_data[metric_name] = metric_df
                        logger.debug(f"✅ 전처리 완료: {metric_name} ({len(metric_df)} 포인트)")

            except Exception as e:
                logger.warning(f"⚠️ 전처리 실패 ({source_name}): {str(e)}")

        logger.info(f"🔧 전처리 완료: {len(processed_data)}개 메트릭")
        return processed_data

    def detect_anomalies(self, processed_data: Dict[str, pd.DataFrame]) -> Dict[str, List[Dict]]:
        """
        전처리된 데이터에서 이상치 탐지

        Args:
            processed_data: 전처리된 메트릭 데이터

        Returns:
            Dict[str, List[Dict]]: 메트릭별 이상치 리스트
        """
        logger.info(f"🔍 이상치 탐지 시작 (임계치: {self.threshold})")

        anomalies = {}

        for metric_name, df in processed_data.items():
            try:
                metric_anomalies = []

                # Z-score 기반 이상치 탐지
                anomaly_mask = np.abs(df['z_score']) > self.threshold
                anomaly_points = df[anomaly_mask]

                for idx, row in anomaly_points.iterrows():
                    anomaly = {
                        'timestamp': row['timestamp'].isoformat(),
                        'value': float(row['value']),
                        'ewma': float(row['ewma']),
                        'z_score': float(row['z_score']),
                        'severity': self._classify_anomaly_severity(abs(row['z_score'])),
                        'direction': 'increase' if row['z_score'] > 0 else 'decrease'
                    }
                    metric_anomalies.append(anomaly)

                if metric_anomalies:
                    anomalies[metric_name] = metric_anomalies
                    logger.info(f"🔍 {metric_name}: {len(metric_anomalies)}개 이상치 발견")

            except Exception as e:
                logger.warning(f"⚠️ 이상치 탐지 실패 ({metric_name}): {str(e)}")

        self.anomalies = anomalies
        total_anomalies = sum(len(anomaly_list) for anomaly_list in anomalies.values())
        logger.info(f"🔍 이상치 탐지 완료: 총 {total_anomalies}개 발견")

        return anomalies

    def _classify_anomaly_severity(self, abs_z_score: float) -> str:
        """
        Z-score 절댓값에 따른 이상치 심각도 분류

        Args:
            abs_z_score: Z-score 절댓값

        Returns:
            str: 심각도 ('low', 'medium', 'high', 'critical')
        """
        if abs_z_score >= 5.0:
            return 'critical'  # 매우 드문 사건 (0.0001% 확률)
        elif abs_z_score >= 4.0:
            return 'high'      # 드문 사건 (0.01% 확률)
        elif abs_z_score >= 3.5:
            return 'medium'    # 일반적이지 않은 사건 (0.05% 확률)
        else:
            return 'low'       # 비교적 흔한 이상치 (0.3% 확률)

    def generate_forecasts(self, processed_data: Dict[str, pd.DataFrame]) -> Dict[str, Dict]:
        """
        선형회귀 + EWMA를 이용한 7일 예측 생성

        Args:
            processed_data: 전처리된 메트릭 데이터

        Returns:
            Dict[str, Dict]: 메트릭별 예측 결과
        """
        logger.info(f"📈 {self.forecast_days}일 예측 생성 시작")

        forecasts = {}

        for metric_name, df in processed_data.items():
            try:
                if len(df) < 14:  # 최소 2주 데이터 필요
                    continue

                # 최근 30일 데이터로 예측 모델 학습
                recent_data = df.tail(min(30, len(df))).copy()
                recent_data = recent_data.reset_index(drop=True)

                # 1. 선형회귀로 장기 추세 파악
                X = np.arange(len(recent_data)).reshape(-1, 1)
                y = recent_data['ewma'].values

                lr_model = LinearRegression()
                lr_model.fit(X, y)

                # 2. EWMA의 최근 추세 반영
                ewma_trend = recent_data['ewma'].iloc[-3:].mean() - recent_data['ewma'].iloc[-7:-4].mean()

                # 3. 미래 7일 예측
                future_X = np.arange(len(recent_data), len(recent_data) + self.forecast_days).reshape(-1, 1)
                linear_forecast = lr_model.predict(future_X)

                # EWMA 추세 반영한 조정
                ewma_adjustment = np.array([ewma_trend * (i + 1) * 0.1 for i in range(self.forecast_days)])
                adjusted_forecast = linear_forecast + ewma_adjustment

                # 4. 신뢰구간 계산 (최근 데이터의 변동성 기반)
                recent_std = recent_data['ewma'].std()
                confidence_interval = 1.96 * recent_std  # 95% 신뢰구간

                # 5. 예측 결과 생성
                base_date = recent_data['timestamp'].iloc[-1]
                forecast_dates = [base_date + timedelta(days=i+1) for i in range(self.forecast_days)]

                forecast_points = []
                for i, (date, value) in enumerate(zip(forecast_dates, adjusted_forecast)):
                    forecast_points.append({
                        'date': date.isoformat(),
                        'predicted_value': float(value),
                        'lower_bound': float(value - confidence_interval),
                        'upper_bound': float(value + confidence_interval),
                        'confidence': 0.95
                    })

                # 6. 위험 구간 예측 (임계치 초과 가능성)
                risk_periods = self._identify_risk_periods(
                    recent_data, forecast_points, confidence_interval
                )

                forecasts[metric_name] = {
                    'forecast_points': forecast_points,
                    'trend_direction': 'increasing' if lr_model.coef_[0] > 0 else 'decreasing',
                    'trend_strength': abs(float(lr_model.coef_[0])),
                    'confidence_level': 0.95,
                    'model_accuracy': self._calculate_model_accuracy(recent_data, lr_model),
                    'risk_periods': risk_periods
                }

                logger.debug(f"📈 예측 완료: {metric_name} (정확도: {forecasts[metric_name]['model_accuracy']:.2%})")

            except Exception as e:
                logger.warning(f"⚠️ 예측 실패 ({metric_name}): {str(e)}")

        self.forecasts = forecasts
        logger.info(f"📈 예측 완료: {len(forecasts)}개 메트릭")

        return forecasts

    def _identify_risk_periods(self,
                              recent_data: pd.DataFrame,
                              forecast_points: List[Dict],
                              confidence_interval: float) -> List[Dict]:
        """
        예측된 값이 이상치 임계치를 초과할 가능성이 있는 위험 기간 식별

        Args:
            recent_data: 최근 데이터
            forecast_points: 예측 포인트들
            confidence_interval: 신뢰구간

        Returns:
            List[Dict]: 위험 기간 목록
        """
        risk_periods = []

        try:
            # 최근 데이터의 통계 계산
            recent_mean = recent_data['ewma'].mean()
            recent_std = recent_data['ewma'].std()

            # 이상치 임계치 계산
            upper_threshold = recent_mean + self.threshold * recent_std
            lower_threshold = recent_mean - self.threshold * recent_std

            for point in forecast_points:
                # 신뢰구간 상한/하한이 임계치를 넘을 확률 계산
                upper_risk = point['upper_bound'] > upper_threshold
                lower_risk = point['lower_bound'] < lower_threshold

                if upper_risk or lower_risk:
                    risk_type = []
                    if upper_risk:
                        risk_type.append('high_value')
                    if lower_risk:
                        risk_type.append('low_value')

                    risk_periods.append({
                        'date': point['date'],
                        'risk_type': risk_type,
                        'risk_probability': min(0.95, abs(point['predicted_value'] - recent_mean) / (recent_std * self.threshold)),
                        'predicted_value': point['predicted_value'],
                        'threshold_exceeded': upper_risk or lower_risk
                    })

        except Exception as e:
            logger.warning(f"위험 기간 식별 오류: {str(e)}")

        return risk_periods

    def _calculate_model_accuracy(self, data: pd.DataFrame, model: LinearRegression) -> float:
        """
        모델의 정확도 계산 (백테스팅)

        Args:
            data: 학습 데이터
            model: 훈련된 모델

        Returns:
            float: 정확도 (0~1)
        """
        try:
            if len(data) < 7:
                return 0.5

            # 마지막 7일을 테스트용으로 사용
            train_data = data.iloc[:-7]
            test_data = data.iloc[-7:]

            if len(train_data) < 7:
                return 0.5

            # 테스트 데이터 예측
            X_test = np.arange(len(train_data), len(data)).reshape(-1, 1)
            y_test = test_data['ewma'].values
            y_pred = model.predict(X_test)

            # MAPE (Mean Absolute Percentage Error) 계산
            mape = np.mean(np.abs((y_test - y_pred) / (y_test + 1e-8))) * 100
            accuracy = max(0, min(1, (100 - mape) / 100))

            return accuracy

        except Exception:
            return 0.5

    def calculate_risk_levels(self) -> Dict[str, str]:
        """
        각 메트릭의 전반적인 위험도 수준 계산

        Returns:
            Dict[str, str]: 메트릭별 위험도 ('low', 'medium', 'high', 'critical')
        """
        risk_levels = {}

        for metric_name in self.metrics_data:
            total_score = 0
            factors = 0

            # 1. 이상치 빈도 점수
            if metric_name in self.anomalies:
                anomaly_count = len(self.anomalies[metric_name])
                anomaly_score = min(10, anomaly_count)  # 최대 10점
                total_score += anomaly_score
                factors += 1

            # 2. 예측 위험도 점수
            if metric_name in self.forecasts:
                risk_periods = self.forecasts[metric_name].get('risk_periods', [])
                risk_score = len(risk_periods) * 2  # 위험 기간당 2점
                total_score += risk_score
                factors += 1

                # 3. 모델 정확도 점수 (낮을수록 위험)
                accuracy = self.forecasts[metric_name].get('model_accuracy', 0.5)
                accuracy_score = (1 - accuracy) * 5  # 최대 5점
                total_score += accuracy_score
                factors += 1

            # 평균 점수로 위험도 결정
            if factors > 0:
                avg_score = total_score / factors
                if avg_score >= 7:
                    risk_level = 'critical'
                elif avg_score >= 5:
                    risk_level = 'high'
                elif avg_score >= 3:
                    risk_level = 'medium'
                else:
                    risk_level = 'low'
            else:
                risk_level = 'low'

            risk_levels[metric_name] = risk_level

        self.risk_levels = risk_levels
        return risk_levels

    def generate_report(self, output_format: str = 'json') -> str:
        """
        분석 결과를 종합한 리포트 생성

        Args:
            output_format: 출력 형식 ('json' 또는 'markdown')

        Returns:
            str: 생성된 리포트 내용
        """
        logger.info(f"📋 {output_format.upper()} 리포트 생성 시작")

        # 요약 통계 계산
        total_anomalies = sum(len(anomaly_list) for anomaly_list in self.anomalies.values())
        high_risk_metrics = sum(1 for level in self.risk_levels.values() if level in ['high', 'critical'])
        total_risk_periods = sum(len(forecast['risk_periods']) for forecast in self.forecasts.values())

        # 상위 이상치 구간 추출 (Top N)
        top_anomalies = self._get_top_anomalies(limit=10)

        if output_format.lower() == 'markdown':
            return self._generate_markdown_report(
                total_anomalies, high_risk_metrics, total_risk_periods, top_anomalies
            )
        else:
            return self._generate_json_report(
                total_anomalies, high_risk_metrics, total_risk_periods, top_anomalies
            )

    def _get_top_anomalies(self, limit: int = 10) -> List[Dict]:
        """
        Z-score가 높은 상위 이상치들 추출

        Args:
            limit: 반환할 최대 개수

        Returns:
            List[Dict]: 상위 이상치 목록
        """
        all_anomalies = []

        for metric_name, anomaly_list in self.anomalies.items():
            for anomaly in anomaly_list:
                anomaly_copy = anomaly.copy()
                anomaly_copy['metric'] = metric_name
                all_anomalies.append(anomaly_copy)

        # Z-score 절댓값으로 정렬
        all_anomalies.sort(key=lambda x: abs(x['z_score']), reverse=True)

        return all_anomalies[:limit]

    def _generate_markdown_report(self,
                                total_anomalies: int,
                                high_risk_metrics: int,
                                total_risk_periods: int,
                                top_anomalies: List[Dict]) -> str:
        """
        Markdown 형식 리포트 생성
        """
        report_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        md_content = f"""# 🔎 이상탐지 및 예측 분석 리포트

**생성일시**: {report_time}
**분석 기간**: 최근 {self.window_size}일 롤링 윈도우
**임계치**: Z-score ± {self.threshold}
**예측 기간**: {self.forecast_days}일

## 📊 요약 통계

| 지표 | 값 |
|------|-----|
| 🚨 총 이상치 수 | {total_anomalies}개 |
| ⚠️ 고위험 메트릭 수 | {high_risk_metrics}개 |
| 📈 예측 위험 구간 | {total_risk_periods}개 |
| 📊 분석된 메트릭 수 | {len(self.metrics_data)}개 |

## 🔍 상위 이상치 구간 (Top {len(top_anomalies)})

"""

        for i, anomaly in enumerate(top_anomalies, 1):
            severity_emoji = {
                'critical': '🚨', 'high': '❌', 'medium': '⚠️', 'low': 'ℹ️'
            }
            direction_emoji = '📈' if anomaly['direction'] == 'increase' else '📉'

            md_content += f"""### {i}. {severity_emoji.get(anomaly['severity'], '🔍')} {anomaly['metric']}

- **시간**: {anomaly['timestamp'][:19]}
- **값**: {anomaly['value']:.2f} (EWMA: {anomaly['ewma']:.2f})
- **Z-score**: {anomaly['z_score']:.2f} {direction_emoji}
- **심각도**: {anomaly['severity']}

"""

        # 메트릭별 위험도 현황
        md_content += "\n## 📊 메트릭별 위험도 현황\n\n"
        risk_emoji = {'critical': '🚨', 'high': '❌', 'medium': '⚠️', 'low': '✅'}

        for metric, risk_level in sorted(self.risk_levels.items()):
            emoji = risk_emoji.get(risk_level, '❓')
            anomaly_count = len(self.anomalies.get(metric, []))
            risk_periods = len(self.forecasts.get(metric, {}).get('risk_periods', []))

            md_content += f"- {emoji} **{metric}**: {risk_level} "
            md_content += f"(이상치 {anomaly_count}개, 위험예측 {risk_periods}개)\n"

        # 향후 위험 예측
        md_content += "\n## 📈 향후 7일 위험 예측\n\n"

        future_risks = []
        for metric, forecast in self.forecasts.items():
            for risk in forecast.get('risk_periods', []):
                risk_copy = risk.copy()
                risk_copy['metric'] = metric
                future_risks.append(risk_copy)

        future_risks.sort(key=lambda x: x['risk_probability'], reverse=True)

        if future_risks:
            for risk in future_risks[:5]:  # 상위 5개만 표시
                date = risk['date'][:10]
                prob = risk['risk_probability'] * 100
                risk_types = ', '.join(risk['risk_type'])

                md_content += f"- **{date}**: {risk['metric']} ({risk_types}, 위험도 {prob:.1f}%)\n"
        else:
            md_content += "- ✅ 향후 7일간 특별한 위험 요소가 예측되지 않습니다.\n"

        # 권장사항
        md_content += f"""

## 💡 권장사항

### 즉시 조치 필요
"""
        critical_metrics = [m for m, r in self.risk_levels.items() if r == 'critical']
        if critical_metrics:
            for metric in critical_metrics:
                md_content += f"- 🚨 **{metric}**: 즉시 점검 및 대응 필요\n"
        else:
            md_content += "- ✅ 즉시 조치가 필요한 위험 요소 없음\n"

        md_content += """
### 모니터링 강화
"""
        high_risk_metrics_list = [m for m, r in self.risk_levels.items() if r == 'high']
        if high_risk_metrics_list:
            for metric in high_risk_metrics_list:
                md_content += f"- ❌ **{metric}**: 지속적인 모니터링 필요\n"
        else:
            md_content += "- ✅ 특별한 모니터링이 필요한 메트릭 없음\n"

        md_content += f"""

## 🔧 분석 설정

- **롤링 윈도우**: {self.window_size}일
- **Z-score 임계치**: ±{self.threshold}
- **EWMA 평활화 계수**: {self.ewma_alpha}
- **예측 기간**: {self.forecast_days}일
- **신뢰구간**: 95%

---
*본 리포트는 MCP Map Company 이상탐지 시스템에 의해 자동 생성되었습니다.*
"""

        return md_content

    def _generate_json_report(self,
                            total_anomalies: int,
                            high_risk_metrics: int,
                            total_risk_periods: int,
                            top_anomalies: List[Dict]) -> str:
        """
        JSON 형식 리포트 생성
        """
        report_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "analysis_window_days": self.window_size,
                "z_score_threshold": self.threshold,
                "forecast_days": self.forecast_days,
                "ewma_alpha": self.ewma_alpha,
                "total_metrics_analyzed": len(self.metrics_data)
            },
            "summary": {
                "total_anomalies": total_anomalies,
                "high_risk_metrics": high_risk_metrics,
                "total_future_risk_periods": total_risk_periods,
                "metrics_by_risk_level": {
                    "critical": len([r for r in self.risk_levels.values() if r == 'critical']),
                    "high": len([r for r in self.risk_levels.values() if r == 'high']),
                    "medium": len([r for r in self.risk_levels.values() if r == 'medium']),
                    "low": len([r for r in self.risk_levels.values() if r == 'low'])
                }
            },
            "top_anomalies": top_anomalies,
            "risk_levels": self.risk_levels,
            "detailed_anomalies": self.anomalies,
            "forecasts": self.forecasts,
            "recommendations": self._generate_recommendations()
        }

        return json.dumps(report_data, indent=2, ensure_ascii=False)

    def _generate_recommendations(self) -> List[Dict]:
        """
        위험도 수준에 따른 권장사항 생성
        """
        recommendations = []

        # Critical 메트릭 권장사항
        critical_metrics = [m for m, r in self.risk_levels.items() if r == 'critical']
        for metric in critical_metrics:
            recommendations.append({
                "priority": "critical",
                "metric": metric,
                "action": "즉시 점검 및 대응 필요",
                "description": f"{metric}에서 심각한 이상치가 다수 발견되었습니다. 즉시 시스템 점검을 실시하십시오."
            })

        # High 메트릭 권장사항
        high_metrics = [m for m, r in self.risk_levels.items() if r == 'high']
        for metric in high_metrics:
            recommendations.append({
                "priority": "high",
                "metric": metric,
                "action": "지속적인 모니터링 강화",
                "description": f"{metric}의 패턴 변화를 주의 깊게 관찰하고 예방적 조치를 준비하십시오."
            })

        # 향후 위험 예측 권장사항
        high_risk_forecasts = []
        for metric, forecast in self.forecasts.items():
            risk_periods = forecast.get('risk_periods', [])
            if len(risk_periods) >= 2:
                high_risk_forecasts.append(metric)

        for metric in high_risk_forecasts:
            recommendations.append({
                "priority": "medium",
                "metric": metric,
                "action": "예방적 조치 준비",
                "description": f"{metric}에서 향후 7일간 위험 구간이 예측됩니다. 사전 대응 계획을 수립하십시오."
            })

        return recommendations


def main():
    """
    메인 실행 함수 - 명령행 인자 처리 및 분석 실행
    """
    parser = argparse.ArgumentParser(
        description="🔎 이상탐지 및 예측 분석 스크립트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  %(prog)s                                    # 기본 실행 (30일, JSON 출력)
  %(prog)s --days 7 --md                      # 7일 데이터, Markdown 출력
  %(prog)s --threshold 2.5 --window 14        # 임계치 2.5, 윈도우 14일
  %(prog)s --json --verbose                   # JSON 출력, 상세 로그
  %(prog)s --dry-run                          # 테스트 실행 (가짜 데이터)
        """
    )

    # 명령행 인자 정의
    parser.add_argument('--days', type=int, default=30,
                       help='분석할 데이터 기간 (일) [기본값: 30]')
    parser.add_argument('--threshold', type=float, default=3.0,
                       help='Z-score 이상치 임계치 [기본값: 3.0]')
    parser.add_argument('--window', type=int, default=7,
                       help='롤링 윈도우 크기 (일) [기본값: 7]')
    parser.add_argument('--forecast', type=int, default=7,
                       help='예측 기간 (일) [기본값: 7]')
    parser.add_argument('--json', action='store_true',
                       help='JSON 형식으로 출력')
    parser.add_argument('--md', action='store_true',
                       help='Markdown 형식으로 출력')
    parser.add_argument('--verbose', action='store_true',
                       help='상세 로그 출력')
    parser.add_argument('--dry-run', action='store_true',
                       help='테스트 모드 (가짜 데이터 사용)')
    parser.add_argument('--output', type=str,
                       help='출력 파일 경로 (지정하지 않으면 stdout)')

    args = parser.parse_args()

    # 로깅 레벨 설정
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        logger.info("🔎 이상탐지 및 예측 분석 시작")
        logger.info(f"설정: days={args.days}, threshold={args.threshold}, window={args.window}")

        # 이상탐지 엔진 초기화
        detector = AnomalyDetector(
            window_size=args.window,
            threshold=args.threshold,
            forecast_days=args.forecast
        )

        if args.dry_run:
            logger.info("🧪 테스트 모드: 가짜 데이터 생성")
            detector.metrics_data = _generate_fake_data(args.days)
        else:
            # 실제 데이터 로드
            detector.load_metric_sources()

        if not detector.metrics_data:
            logger.error("❌ 분석할 메트릭 데이터가 없습니다")
            sys.exit(1)

        # 데이터 전처리
        processed_data = detector.preprocess_data()

        if not processed_data:
            logger.error("❌ 전처리된 데이터가 없습니다")
            sys.exit(1)

        # 이상치 탐지
        anomalies = detector.detect_anomalies(processed_data)

        # 예측 생성
        forecasts = detector.generate_forecasts(processed_data)

        # 위험도 계산
        risk_levels = detector.calculate_risk_levels()

        # 출력 형식 결정
        if args.md:
            output_format = 'markdown'
        else:
            output_format = 'json'

        # 리포트 생성
        report = detector.generate_report(output_format)

        # 출력
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"📄 리포트 저장: {args.output}")
        else:
            print(report)

        logger.info("✅ 이상탐지 및 예측 분석 완료")

    except KeyboardInterrupt:
        logger.info("⚠️ 사용자에 의해 중단됨")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 분석 중 오류 발생: {str(e)}")
        if args.verbose:
            logger.error(traceback.format_exc())
        sys.exit(1)


def _generate_fake_data(days: int) -> Dict[str, pd.DataFrame]:
    """
    테스트용 가짜 메트릭 데이터 생성

    Args:
        days: 생성할 데이터 기간 (일)

    Returns:
        Dict[str, pd.DataFrame]: 가짜 메트릭 데이터
    """
    logger.info(f"🧪 {days}일간의 가짜 데이터 생성")

    fake_data = {}

    # 메트릭 종류 정의
    metrics_config = [
        {"name": "cpu_usage", "base": 45, "noise": 10, "trend": 0.1, "anomaly_prob": 0.05},
        {"name": "memory_usage", "base": 60, "noise": 15, "trend": -0.05, "anomaly_prob": 0.03},
        {"name": "disk_usage", "base": 75, "noise": 5, "trend": 0.2, "anomaly_prob": 0.02},
        {"name": "response_time", "base": 200, "noise": 50, "trend": 0.5, "anomaly_prob": 0.08},
        {"name": "error_rate", "base": 2, "noise": 1, "trend": 0, "anomaly_prob": 0.1},
    ]

    # 시계열 데이터 생성
    base_date = datetime.now() - timedelta(days=days)

    for config in metrics_config:
        records = []
        current_value = config["base"]

        for i in range(days * 24):  # 시간당 데이터 포인트
            timestamp = base_date + timedelta(hours=i)

            # 기본 추세 + 노이즈
            trend_component = config["trend"] * i / 24  # 일별 추세
            noise_component = np.random.normal(0, config["noise"])

            # 이상치 생성 (확률적)
            if np.random.random() < config["anomaly_prob"]:
                anomaly_factor = np.random.choice([-1, 1]) * np.random.uniform(3, 6)
                noise_component += anomaly_factor * config["noise"]

            current_value = max(0, config["base"] + trend_component + noise_component)

            records.append({
                'timestamp': timestamp,
                'metric': f"fake_{config['name']}",
                'value': current_value
            })

        df = pd.DataFrame(records)
        fake_data[f"fake_metrics_{config['name']}"] = df

    logger.info(f"🧪 가짜 데이터 생성 완료: {len(fake_data)}개 메트릭")
    return fake_data


if __name__ == "__main__":
    main()