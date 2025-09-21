# mcp/anomaly_rca.py
"""
이상탐지 원인분석(RCA) 및 계절성 분해 유틸리티

주요 기능:
- 단변량/다변량 지표 상관관계 및 기여도 분석
- 이상 구간과 기준 구간 비교를 통한 원인 항목 식별
- 계절성/추세 분해를 통한 시계열 패턴 분석
- 한국어 결과 포맷팅 및 설명

작성자: Claude Code Assistant
생성일: 2024-09-21
"""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional, Union
from datetime import datetime, timedelta
import json
from dataclasses import dataclass, asdict
from scipy import stats
from scipy.signal import periodogram
import warnings

# 로깅 설정
log = logging.getLogger("mcp.anomaly_rca")

# 경고 필터링 (통계 계산 시 발생하는 불필요한 경고 억제)
warnings.filterwarnings("ignore", category=RuntimeWarning)

@dataclass
class RCACause:
    """원인분석 결과 항목"""
    cause: str              # 원인 지표명 (한국어)
    contribution: float     # 기여도 (0-100%)
    delta: float           # 기준 대비 변화량
    evidence: str          # 증거/설명 (한국어)
    correlation: float     # 대상 지표와의 상관계수
    p_value: float        # 통계적 유의성 (p-value)

@dataclass
class SeasonalDecomposition:
    """계절성 분해 결과"""
    trend: List[float]          # 추세 성분
    seasonal: List[float]       # 계절성 성분
    residual: List[float]       # 잔차 성분
    timestamps: List[str]       # 타임스탬프
    seasonality_strength: float # 계절성 강도 (0-1)
    trend_strength: float      # 추세 강도 (0-1)
    dominant_period: int       # 주요 주기 (일/시간 단위)

class AnomalyRCAAnalyzer:
    """이상탐지 원인분석기"""

    def __init__(self, min_correlation_threshold: float = 0.3):
        """
        초기화

        Args:
            min_correlation_threshold: 최소 상관계수 임계값 (기본값: 0.3)
        """
        self.min_correlation_threshold = min_correlation_threshold
        self.log = logging.getLogger(f"{__name__}.AnomalyRCAAnalyzer")

    def analyze_root_causes(
        self,
        series_dict: Dict[str, List[float]],
        anomaly_window: Tuple[int, int],
        baseline_window: Tuple[int, int],
        target_metric: str = None,
        top_n: int = 5
    ) -> Dict[str, Any]:
        """
        이상 구간의 원인 분석 수행

        Args:
            series_dict: 지표별 시계열 데이터 {"지표명": [값들]}
            anomaly_window: 이상 구간 (시작_인덱스, 끝_인덱스)
            baseline_window: 기준 구간 (시작_인덱스, 끝_인덱스)
            target_metric: 대상 지표명 (None이면 자동 선택)
            top_n: 상위 N개 원인 반환

        Returns:
            Dict: 원인분석 결과
        """
        try:
            self.log.info(f"원인분석 시작 - 이상구간: {anomaly_window}, 기준구간: {baseline_window}")

            # 입력 검증
            if not series_dict:
                raise ValueError("시계열 데이터가 비어있습니다")

            # 대상 지표 자동 선택 (가장 큰 변화를 보인 지표)
            if target_metric is None:
                target_metric = self._select_target_metric(series_dict, anomaly_window, baseline_window)

            if target_metric not in series_dict:
                raise ValueError(f"대상 지표 '{target_metric}'를 찾을 수 없습니다")

            # 각 지표별 기여도 계산
            causes = []
            target_series = np.array(series_dict[target_metric])

            for metric_name, metric_series in series_dict.items():
                if metric_name == target_metric:
                    continue

                try:
                    cause = self._calculate_metric_contribution(
                        metric_name,
                        np.array(metric_series),
                        target_series,
                        anomaly_window,
                        baseline_window
                    )

                    if cause and abs(cause.correlation) >= self.min_correlation_threshold:
                        causes.append(cause)

                except Exception as e:
                    self.log.warning(f"지표 '{metric_name}' 기여도 계산 실패: {e}")
                    continue

            # 기여도 순으로 정렬
            causes.sort(key=lambda x: abs(x.contribution), reverse=True)
            top_causes = causes[:top_n]

            # 결과 구성
            result = {
                "분석_시간": datetime.now().isoformat(),
                "대상_지표": target_metric,
                "이상_구간": {
                    "시작": anomaly_window[0],
                    "끝": anomaly_window[1],
                    "기간": anomaly_window[1] - anomaly_window[0] + 1
                },
                "기준_구간": {
                    "시작": baseline_window[0],
                    "끝": baseline_window[1],
                    "기간": baseline_window[1] - baseline_window[0] + 1
                },
                "주요_원인": [asdict(cause) for cause in top_causes],
                "전체_원인_수": len(causes),
                "분석_요약": self._generate_summary(target_metric, top_causes)
            }

            self.log.info(f"원인분석 완료 - 발견된 원인: {len(top_causes)}개")
            return result

        except Exception as e:
            self.log.error(f"원인분석 실패: {e}")
            raise

    def _select_target_metric(
        self,
        series_dict: Dict[str, List[float]],
        anomaly_window: Tuple[int, int],
        baseline_window: Tuple[int, int]
    ) -> str:
        """가장 큰 변화를 보인 지표를 대상 지표로 선택"""
        max_change = 0
        target_metric = list(series_dict.keys())[0]

        for metric_name, series in series_dict.items():
            series_arr = np.array(series)

            # 기준 구간과 이상 구간의 평균값 차이
            baseline_mean = np.mean(series_arr[baseline_window[0]:baseline_window[1]+1])
            anomaly_mean = np.mean(series_arr[anomaly_window[0]:anomaly_window[1]+1])

            if baseline_mean != 0:
                change_ratio = abs((anomaly_mean - baseline_mean) / baseline_mean)
                if change_ratio > max_change:
                    max_change = change_ratio
                    target_metric = metric_name

        return target_metric

    def _calculate_metric_contribution(
        self,
        metric_name: str,
        metric_series: np.ndarray,
        target_series: np.ndarray,
        anomaly_window: Tuple[int, int],
        baseline_window: Tuple[int, int]
    ) -> Optional[RCACause]:
        """개별 지표의 기여도 계산"""
        try:
            # 기준 구간 통계
            baseline_metric = metric_series[baseline_window[0]:baseline_window[1]+1]
            baseline_target = target_series[baseline_window[0]:baseline_window[1]+1]
            baseline_metric_mean = np.mean(baseline_metric)

            # 이상 구간 통계
            anomaly_metric = metric_series[anomaly_window[0]:anomaly_window[1]+1]
            anomaly_target = target_series[anomaly_window[0]:anomaly_window[1]+1]
            anomaly_metric_mean = np.mean(anomaly_metric)

            # 변화량 계산
            delta = anomaly_metric_mean - baseline_metric_mean
            delta_ratio = (delta / baseline_metric_mean * 100) if baseline_metric_mean != 0 else 0

            # 상관관계 계산 (전체 기간)
            correlation, p_value = stats.pearsonr(metric_series, target_series)

            # 기여도 계산 (변화량과 상관관계 기반)
            contribution = abs(delta_ratio) * abs(correlation)

            # 증거 문장 생성
            evidence = self._generate_evidence_text(
                metric_name, delta, delta_ratio, correlation, p_value
            )

            return RCACause(
                cause=metric_name,
                contribution=contribution,
                delta=delta,
                evidence=evidence,
                correlation=correlation,
                p_value=p_value
            )

        except Exception as e:
            self.log.warning(f"지표 '{metric_name}' 기여도 계산 오류: {e}")
            return None

    def _generate_evidence_text(
        self,
        metric_name: str,
        delta: float,
        delta_ratio: float,
        correlation: float,
        p_value: float
    ) -> str:
        """증거 텍스트 생성 (한국어)"""
        direction = "증가" if delta > 0 else "감소"
        correlation_strength = self._get_correlation_strength_korean(abs(correlation))
        significance = "유의함" if p_value < 0.05 else "유의하지 않음"

        return (f"{metric_name}가 {abs(delta_ratio):.1f}% {direction}하여 "
                f"{correlation_strength} 상관관계 (r={correlation:.3f}, p={p_value:.3f}, {significance})")

    def _get_correlation_strength_korean(self, abs_correlation: float) -> str:
        """상관관계 강도를 한국어로 변환"""
        if abs_correlation >= 0.8:
            return "매우 강한"
        elif abs_correlation >= 0.6:
            return "강한"
        elif abs_correlation >= 0.4:
            return "보통"
        elif abs_correlation >= 0.2:
            return "약한"
        else:
            return "매우 약한"

    def _generate_summary(self, target_metric: str, causes: List[RCACause]) -> str:
        """분석 요약 생성 (한국어)"""
        if not causes:
            return f"{target_metric}에 대한 유의미한 원인을 찾지 못했습니다."

        top_cause = causes[0]
        summary = (f"{target_metric}의 이상 원인: {top_cause.cause}가 "
                  f"{top_cause.contribution:.1f}% 기여 (상관계수: {top_cause.correlation:.3f})")

        if len(causes) > 1:
            summary += f". 총 {len(causes)}개 관련 요인 식별됨."

        return summary

    def decompose_seasonality(
        self,
        series: List[float],
        timestamps: List[str] = None,
        freq_hint: str = "D"
    ) -> Dict[str, Any]:
        """
        시계열 계절성 분해 (간단한 이동평균 기반)

        Args:
            series: 시계열 데이터
            timestamps: 타임스탬프 리스트 (없으면 자동 생성)
            freq_hint: 주기 힌트 ("D"=일간, "H"=시간, "W"=주간)

        Returns:
            Dict: 계절성 분해 결과
        """
        try:
            self.log.info(f"계절성 분해 시작 - 데이터 포인트: {len(series)}개")

            if len(series) < 14:
                raise ValueError("계절성 분해를 위해서는 최소 14개 데이터 포인트가 필요합니다")

            series_arr = np.array(series)

            # 타임스탬프 생성 (없는 경우)
            if timestamps is None:
                timestamps = [f"T{i}" for i in range(len(series))]

            # 주기 추정
            dominant_period = self._estimate_dominant_period(series_arr, freq_hint)

            # 추세 성분 추출 (이동평균)
            window_size = min(dominant_period, len(series) // 4)
            trend = self._calculate_trend(series_arr, window_size)

            # 추세 제거
            detrended = series_arr - trend

            # 계절성 성분 추출
            seasonal = self._calculate_seasonal(detrended, dominant_period)

            # 잔차 계산
            residual = series_arr - trend - seasonal

            # 강도 계산
            seasonality_strength = self._calculate_seasonality_strength(seasonal, residual)
            trend_strength = self._calculate_trend_strength(trend, series_arr)

            result = SeasonalDecomposition(
                trend=trend.tolist(),
                seasonal=seasonal.tolist(),
                residual=residual.tolist(),
                timestamps=timestamps,
                seasonality_strength=seasonality_strength,
                trend_strength=trend_strength,
                dominant_period=dominant_period
            )

            # Dict로 변환하여 반환
            decomp_dict = asdict(result)
            decomp_dict["분석_요약"] = self._generate_decomposition_summary(result)

            self.log.info(f"계절성 분해 완료 - 주기: {dominant_period}, 계절성 강도: {seasonality_strength:.3f}")
            return decomp_dict

        except Exception as e:
            self.log.error(f"계절성 분해 실패: {e}")
            raise

    def _estimate_dominant_period(self, series: np.ndarray, freq_hint: str) -> int:
        """주요 주기 추정"""
        try:
            # FFT 기반 주기 추정
            if len(series) > 50:
                freqs, power = periodogram(series)
                dominant_freq_idx = np.argmax(power[1:]) + 1  # DC 성분 제외
                period = int(1 / freqs[dominant_freq_idx]) if freqs[dominant_freq_idx] > 0 else 7
            else:
                period = 7  # 기본값

            # 주기 힌트에 따른 조정
            if freq_hint == "H":  # 시간 단위
                period = min(max(period, 24), 168)  # 1일~1주
            elif freq_hint == "W":  # 주간 단위
                period = min(max(period, 4), 52)   # 1달~1년
            else:  # 일간 단위 (기본)
                period = min(max(period, 7), 365)  # 1주~1년

            return period

        except Exception:
            return 7  # 기본값: 7일 주기

    def _calculate_trend(self, series: np.ndarray, window_size: int) -> np.ndarray:
        """추세 성분 계산 (중앙값 기반 이동평균)"""
        trend = np.zeros_like(series)
        half_window = window_size // 2

        for i in range(len(series)):
            start = max(0, i - half_window)
            end = min(len(series), i + half_window + 1)
            trend[i] = np.median(series[start:end])

        return trend

    def _calculate_seasonal(self, detrended: np.ndarray, period: int) -> np.ndarray:
        """계절성 성분 계산"""
        seasonal = np.zeros_like(detrended)

        for i in range(len(detrended)):
            # 같은 계절 위치의 값들 평균
            seasonal_indices = list(range(i % period, len(detrended), period))
            seasonal[i] = np.mean(detrended[seasonal_indices])

        return seasonal

    def _calculate_seasonality_strength(self, seasonal: np.ndarray, residual: np.ndarray) -> float:
        """계절성 강도 계산 (0-1)"""
        seasonal_var = np.var(seasonal)
        residual_var = np.var(residual)
        total_var = seasonal_var + residual_var

        return seasonal_var / total_var if total_var > 0 else 0

    def _calculate_trend_strength(self, trend: np.ndarray, original: np.ndarray) -> float:
        """추세 강도 계산 (0-1)"""
        detrended_var = np.var(original - trend)
        original_var = np.var(original)

        return 1 - (detrended_var / original_var) if original_var > 0 else 0

    def _generate_decomposition_summary(self, decomp: SeasonalDecomposition) -> str:
        """분해 요약 생성 (한국어)"""
        summary_parts = []

        if decomp.seasonality_strength > 0.6:
            summary_parts.append(f"강한 계절성 ({decomp.seasonality_strength:.1%})")
        elif decomp.seasonality_strength > 0.3:
            summary_parts.append(f"보통 계절성 ({decomp.seasonality_strength:.1%})")
        else:
            summary_parts.append(f"약한 계절성 ({decomp.seasonality_strength:.1%})")

        if decomp.trend_strength > 0.6:
            summary_parts.append(f"뚜렷한 추세 ({decomp.trend_strength:.1%})")
        elif decomp.trend_strength > 0.3:
            summary_parts.append(f"보통 추세 ({decomp.trend_strength:.1%})")
        else:
            summary_parts.append(f"약한 추세 ({decomp.trend_strength:.1%})")

        summary_parts.append(f"주기 {decomp.dominant_period}일")

        return ", ".join(summary_parts)


# 편의 함수들
def analyze_root_causes(
    series_dict: Dict[str, List[float]],
    anomaly_window: Tuple[int, int],
    baseline_window: Tuple[int, int],
    target_metric: str = None,
    top_n: int = 5
) -> Dict[str, Any]:
    """
    이상 구간 원인분석 수행 (편의 함수)

    Args:
        series_dict: 지표별 시계열 데이터
        anomaly_window: 이상 구간 (시작, 끝)
        baseline_window: 기준 구간 (시작, 끝)
        target_metric: 대상 지표명
        top_n: 상위 N개 원인

    Returns:
        Dict: 원인분석 결과
    """
    analyzer = AnomalyRCAAnalyzer()
    return analyzer.analyze_root_causes(
        series_dict, anomaly_window, baseline_window, target_metric, top_n
    )

def decompose_seasonality(
    series: List[float],
    timestamps: List[str] = None,
    freq_hint: str = "D"
) -> Dict[str, Any]:
    """
    시계열 계절성 분해 (편의 함수)

    Args:
        series: 시계열 데이터
        timestamps: 타임스탬프 리스트
        freq_hint: 주기 힌트

    Returns:
        Dict: 계절성 분해 결과
    """
    analyzer = AnomalyRCAAnalyzer()
    return analyzer.decompose_seasonality(series, timestamps, freq_hint)


# 샘플 데이터 생성 함수 (테스트용)
def generate_sample_data(days: int = 30) -> Dict[str, List[float]]:
    """테스트용 샘플 데이터 생성"""
    np.random.seed(42)

    # 기본 시간 축
    t = np.arange(days)

    # CPU 사용률 (주간 패턴 + 노이즈)
    cpu_baseline = 50 + 20 * np.sin(2 * np.pi * t / 7) + np.random.normal(0, 5, days)

    # 메모리 사용률 (CPU와 상관관계 + 추세)
    memory_baseline = 40 + 0.8 * cpu_baseline + 0.3 * t + np.random.normal(0, 3, days)

    # 네트워크 지연 (반대 상관관계)
    network_baseline = 100 - 0.5 * cpu_baseline + np.random.normal(0, 10, days)

    # 디스크 I/O (독립적 패턴)
    disk_baseline = 30 + 10 * np.sin(2 * np.pi * t / 3) + np.random.normal(0, 8, days)

    return {
        "cpu_usage": cpu_baseline.tolist(),
        "memory_usage": memory_baseline.tolist(),
        "network_latency": network_baseline.tolist(),
        "disk_io": disk_baseline.tolist()
    }


if __name__ == "__main__":
    # 샘플 실행
    print("🔎 이상탐지 원인분석 샘플 실행")

    # 샘플 데이터 생성
    sample_data = generate_sample_data(30)

    # 원인분석 실행
    anomaly_window = (20, 25)  # 20~25일차가 이상 구간
    baseline_window = (5, 15)  # 5~15일차가 기준 구간

    print("\n📊 원인분석 실행 중...")
    rca_result = analyze_root_causes(
        sample_data, anomaly_window, baseline_window, top_n=3
    )

    print(json.dumps(rca_result, ensure_ascii=False, indent=2))

    # 계절성 분해 실행
    print("\n🔄 계절성 분해 실행 중...")
    decomp_result = decompose_seasonality(sample_data["cpu_usage"])

    print(f"계절성 강도: {decomp_result['seasonality_strength']:.3f}")
    print(f"추세 강도: {decomp_result['trend_strength']:.3f}")
    print(f"주요 주기: {decomp_result['dominant_period']}일")
    print(f"요약: {decomp_result['분석_요약']}")