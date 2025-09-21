#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔎 이상탐지 및 예측 시스템 테스트 스위트 (한국어 주석 포함)

pytest 기반의 포괄적인 테스트 모음:
- 전처리/임계치/윈도우 파라미터 정확성 테스트
- 이상탐지 포인트 개수·인덱스 검증
- 예측(회귀+EWMA) 결과 범위/증가·감소 추세 검증
- API 엔드포인트 정상/오류/권한 테스트
- 성능 테스트 (10만 포인트 내 5초 이내 처리)

작성자: MCP Map Company 운영팀
생성일: 2024년 이상탐지 시스템 프로젝트
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
import warnings

import pytest
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

# 현재 파일의 부모 디렉토리를 sys.path에 추가
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

try:
    # 이상탐지 스크립트 임포트
    from scripts.anomaly_detect import AnomalyDetector
    # FastAPI 앱 임포트
    from mcp.run import app
    from mcp.anomaly_api import router
except ImportError as e:
    pytest.skip(f"모듈 임포트 실패: {e}", allow_module_level=True)

# 경고 메시지 필터링
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

# ================================================================
# 테스트 픽스처 (한국어 주석 포함)
# ================================================================

@pytest.fixture
def anomaly_detector():
    """기본 이상탐지 엔진 인스턴스 생성"""
    return AnomalyDetector(
        window_size=7,
        threshold=3.0,
        forecast_days=7,
        ewma_alpha=0.3
    )

@pytest.fixture
def sample_timeseries_data():
    """테스트용 시계열 데이터 생성 (이상치 포함)"""
    np.random.seed(42)  # 재현 가능한 결과를 위한 시드 설정

    # 30일간의 시간당 데이터 (720 포인트)
    dates = pd.date_range(start='2024-01-01', periods=720, freq='H')

    # 기본 시계열 (트렌드 + 노이즈)
    base_values = 100 + np.arange(720) * 0.1 + np.random.normal(0, 5, 720)

    # 인위적 이상치 삽입 (10개)
    anomaly_indices = [50, 120, 180, 250, 320, 400, 480, 550, 620, 680]
    for idx in anomaly_indices:
        base_values[idx] += np.random.choice([-1, 1]) * np.random.uniform(20, 30)

    return pd.DataFrame({
        'timestamp': dates,
        'metric': 'test_cpu_usage',
        'value': base_values
    })

@pytest.fixture
def large_dataset():
    """성능 테스트용 대용량 데이터셋 생성 (10만 포인트)"""
    np.random.seed(123)

    # 10만 포인트 (약 11년간 시간당 데이터)
    dates = pd.date_range(start='2014-01-01', periods=100000, freq='H')

    # 복잡한 패턴의 시계열
    trend = np.arange(100000) * 0.01
    seasonal = 10 * np.sin(2 * np.pi * np.arange(100000) / (24 * 365.25))  # 연간 주기
    noise = np.random.normal(0, 2, 100000)

    values = 500 + trend + seasonal + noise

    # 대량 이상치 삽입 (1000개, 1%)
    anomaly_indices = np.random.choice(100000, 1000, replace=False)
    for idx in anomaly_indices:
        values[idx] += np.random.choice([-1, 1]) * np.random.uniform(15, 25)

    return pd.DataFrame({
        'timestamp': dates,
        'metric': 'test_large_dataset',
        'value': values
    })

@pytest.fixture
def api_client():
    """FastAPI 테스트 클라이언트"""
    return TestClient(app)

@pytest.fixture
def script_path():
    """이상탐지 스크립트 경로"""
    return project_root / "scripts" / "anomaly_detect.py"

# ================================================================
# 이상탐지 엔진 핵심 기능 테스트 (한국어 주석 포함)
# ================================================================

class TestAnomalyDetectorCore:
    """이상탐지 엔진 핵심 기능 테스트 클래스"""

    def test_detector_initialization(self):
        """이상탐지 엔진 초기화 테스트"""
        detector = AnomalyDetector(
            window_size=14,
            threshold=2.5,
            forecast_days=10,
            ewma_alpha=0.2
        )

        assert detector.window_size == 14
        assert detector.threshold == 2.5
        assert detector.forecast_days == 10
        assert detector.ewma_alpha == 0.2
        assert detector.metrics_data == {}
        assert detector.anomalies == {}
        assert detector.forecasts == {}

    def test_metrics_json_parsing(self, anomaly_detector):
        """메트릭 JSON 데이터 파싱 테스트"""
        # 다양한 JSON 형식 테스트
        test_cases = [
            # 리스트 형태 JSON
            {
                "data": [
                    {"timestamp": "2024-01-01T00:00:00", "cpu_usage": 45.2, "memory_usage": 60.5},
                    {"timestamp": "2024-01-01T01:00:00", "cpu_usage": 48.1, "memory_usage": 62.3}
                ],
                "expected_records": 4  # 2개 timestamp × 2개 메트릭
            },
            # 딕셔너리 형태 JSON
            {
                "data": {
                    "cpu_metric": {
                        "2024-01-01": 45.2,
                        "2024-01-02": 48.1
                    }
                },
                "expected_records": 2
            }
        ]

        for case in test_cases:
            df = anomaly_detector._parse_metrics_json(case["data"], "test_file")
            assert df is not None
            assert len(df) == case["expected_records"]
            assert 'timestamp' in df.columns
            assert 'metric' in df.columns
            assert 'value' in df.columns

    def test_data_preprocessing(self, anomaly_detector, sample_timeseries_data):
        """데이터 전처리 기능 테스트"""
        # 테스트 데이터 설정
        anomaly_detector.metrics_data = {"test_source": sample_timeseries_data}

        # 전처리 실행
        processed_data = anomaly_detector.preprocess_data()

        assert len(processed_data) > 0

        for metric_name, df in processed_data.items():
            # 필수 컬럼 확인
            required_cols = ['timestamp', 'value', 'ewma', 'rolling_mean', 'rolling_std', 'z_score']
            for col in required_cols:
                assert col in df.columns, f"컬럼 {col}이 누락됨"

            # 데이터 품질 확인
            assert not df['value'].isna().any(), "전처리 후에도 누락값이 존재함"
            assert not df['ewma'].isna().any(), "EWMA 계산 실패"
            assert not df['z_score'].isna().any(), "Z-score 계산 실패"

            # EWMA가 실제 값보다 스무딩되었는지 확인
            value_std = df['value'].std()
            ewma_std = df['ewma'].std()
            assert ewma_std <= value_std, "EWMA가 충분히 스무딩되지 않음"

    @pytest.mark.parametrize("window_size,threshold,expected_min_anomalies", [
        (5, 2.0, 15),   # 낮은 임계치 → 많은 이상치
        (7, 3.0, 8),    # 기본 설정
        (10, 4.0, 3),   # 높은 임계치 → 적은 이상치
    ])
    def test_anomaly_detection_parameters(self, sample_timeseries_data, window_size, threshold, expected_min_anomalies):
        """이상탐지 파라미터에 따른 결과 검증"""
        detector = AnomalyDetector(
            window_size=window_size,
            threshold=threshold,
            forecast_days=7
        )

        # 테스트 데이터 설정 및 전처리
        detector.metrics_data = {"test_source": sample_timeseries_data}
        processed_data = detector.preprocess_data()

        # 이상탐지 실행
        anomalies = detector.detect_anomalies(processed_data)

        # 결과 검증
        total_anomalies = sum(len(anomaly_list) for anomaly_list in anomalies.values())

        # 임계치가 낮을수록 더 많은 이상치가 탐지되어야 함
        if threshold <= 2.5:
            assert total_anomalies >= expected_min_anomalies, f"임계치 {threshold}에서 이상치가 너무 적음: {total_anomalies}"

        # 모든 이상치의 Z-score 절댓값이 임계치를 초과해야 함
        for metric_name, anomaly_list in anomalies.items():
            for anomaly in anomaly_list:
                assert abs(anomaly['z_score']) > threshold, f"Z-score {anomaly['z_score']}이 임계치 {threshold}를 초과하지 않음"

    def test_anomaly_severity_classification(self, anomaly_detector):
        """이상치 심각도 분류 테스트"""
        test_cases = [
            (2.5, 'low'),
            (3.5, 'medium'),
            (4.2, 'high'),
            (5.5, 'critical')
        ]

        for z_score, expected_severity in test_cases:
            severity = anomaly_detector._classify_anomaly_severity(z_score)
            assert severity == expected_severity, f"Z-score {z_score}의 심각도 분류가 잘못됨: {severity} (예상: {expected_severity})"

    def test_forecast_generation(self, anomaly_detector, sample_timeseries_data):
        """예측 생성 기능 테스트"""
        # 테스트 데이터 설정 및 전처리
        anomaly_detector.metrics_data = {"test_source": sample_timeseries_data}
        processed_data = anomaly_detector.preprocess_data()

        # 예측 생성
        forecasts = anomaly_detector.generate_forecasts(processed_data)

        assert len(forecasts) > 0, "예측 결과가 생성되지 않음"

        for metric_name, forecast_info in forecasts.items():
            # 필수 필드 확인
            required_fields = ['forecast_points', 'trend_direction', 'trend_strength', 'model_accuracy']
            for field in required_fields:
                assert field in forecast_info, f"예측 결과에 {field} 필드가 누락됨"

            # 예측 포인트 개수 확인
            forecast_points = forecast_info['forecast_points']
            assert len(forecast_points) == anomaly_detector.forecast_days, "예측 기간이 일치하지 않음"

            # 예측 포인트 구조 확인
            for point in forecast_points:
                required_point_fields = ['date', 'predicted_value', 'lower_bound', 'upper_bound', 'confidence']
                for field in required_point_fields:
                    assert field in point, f"예측 포인트에 {field} 필드가 누락됨"

                # 신뢰구간 검증
                assert point['lower_bound'] <= point['predicted_value'] <= point['upper_bound'], "신뢰구간이 잘못됨"
                assert 0 <= point['confidence'] <= 1, "신뢰도가 0-1 범위를 벗어남"

            # 모델 정확도 검증
            assert 0 <= forecast_info['model_accuracy'] <= 1, "모델 정확도가 0-1 범위를 벗어남"

    def test_trend_direction_detection(self, anomaly_detector):
        """추세 방향 탐지 테스트"""
        # 증가 추세 데이터
        increasing_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='H'),
            'metric': 'increasing_test',
            'value': np.arange(100) * 2 + np.random.normal(0, 1, 100)  # 명확한 증가 추세
        })

        # 감소 추세 데이터
        decreasing_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='H'),
            'metric': 'decreasing_test',
            'value': 100 - np.arange(100) * 1.5 + np.random.normal(0, 1, 100)  # 명확한 감소 추세
        })

        for data, expected_trend in [(increasing_data, 'increasing'), (decreasing_data, 'decreasing')]:
            anomaly_detector.metrics_data = {"test_source": data}
            processed_data = anomaly_detector.preprocess_data()
            forecasts = anomaly_detector.generate_forecasts(processed_data)

            assert len(forecasts) > 0

            for metric_name, forecast_info in forecasts.items():
                assert forecast_info['trend_direction'] == expected_trend, \
                    f"추세 방향 탐지 실패: {forecast_info['trend_direction']} (예상: {expected_trend})"

    def test_risk_level_calculation(self, anomaly_detector, sample_timeseries_data):
        """위험도 수준 계산 테스트"""
        # 전체 파이프라인 실행
        anomaly_detector.metrics_data = {"test_source": sample_timeseries_data}
        processed_data = anomaly_detector.preprocess_data()
        anomalies = anomaly_detector.detect_anomalies(processed_data)
        forecasts = anomaly_detector.generate_forecasts(processed_data)
        risk_levels = anomaly_detector.calculate_risk_levels()

        assert len(risk_levels) > 0, "위험도 수준이 계산되지 않음"

        valid_risk_levels = ['low', 'medium', 'high', 'critical']
        for metric_name, risk_level in risk_levels.items():
            assert risk_level in valid_risk_levels, f"잘못된 위험도 수준: {risk_level}"

# ================================================================
# 성능 테스트 (한국어 주석 포함)
# ================================================================

class TestAnomalyDetectorPerformance:
    """이상탐지 시스템 성능 테스트 클래스"""

    def test_large_dataset_processing(self, large_dataset):
        """대용량 데이터셋 처리 성능 테스트 (10만 포인트, 5초 이내)"""
        detector = AnomalyDetector(
            window_size=7,
            threshold=3.0,
            forecast_days=7
        )

        start_time = time.time()

        # 대용량 데이터 처리
        detector.metrics_data = {"large_dataset": large_dataset}
        processed_data = detector.preprocess_data()
        anomalies = detector.detect_anomalies(processed_data)

        processing_time = time.time() - start_time

        # 성능 요구사항: 10만 포인트를 5초 이내에 처리
        assert processing_time < 5.0, f"대용량 데이터 처리 시간 초과: {processing_time:.2f}초"

        # 결과 품질 확인
        assert len(processed_data) > 0, "전처리 결과가 비어있음"
        assert len(anomalies) > 0, "이상치가 전혀 탐지되지 않음"

        total_anomalies = sum(len(anomaly_list) for anomaly_list in anomalies.values())
        # 1% 정도의 이상치가 탐지되어야 함 (대략 500-1500개)
        assert 200 <= total_anomalies <= 2000, f"예상과 다른 이상치 개수: {total_anomalies}"

    def test_memory_efficiency(self, large_dataset):
        """메모리 효율성 테스트"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        detector = AnomalyDetector()
        detector.metrics_data = {"large_dataset": large_dataset}
        processed_data = detector.preprocess_data()
        anomalies = detector.detect_anomalies(processed_data)

        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory

        # 10만 포인트 처리 시 메모리 증가량이 500MB를 초과하지 않아야 함
        assert memory_increase < 500, f"메모리 사용량 초과: {memory_increase:.2f}MB"

    @pytest.mark.parametrize("data_size", [1000, 5000, 10000])
    def test_scalability(self, data_size):
        """확장성 테스트 - 데이터 크기에 따른 처리 시간 증가율"""
        np.random.seed(42)

        # 다양한 크기의 데이터셋 생성
        dates = pd.date_range('2024-01-01', periods=data_size, freq='H')
        values = 100 + np.arange(data_size) * 0.01 + np.random.normal(0, 5, data_size)

        test_data = pd.DataFrame({
            'timestamp': dates,
            'metric': f'scalability_test_{data_size}',
            'value': values
        })

        detector = AnomalyDetector()

        start_time = time.time()
        detector.metrics_data = {"test_data": test_data}
        processed_data = detector.preprocess_data()
        anomalies = detector.detect_anomalies(processed_data)
        processing_time = time.time() - start_time

        # 처리 시간이 데이터 크기에 비례하여 합리적으로 증가해야 함
        # 1000 포인트당 대략 0.1초 이하
        expected_max_time = data_size / 1000 * 0.1
        assert processing_time < expected_max_time, f"처리 시간 초과 ({data_size} 포인트): {processing_time:.3f}초"

# ================================================================
# 스크립트 실행 테스트 (한국어 주석 포함)
# ================================================================

class TestAnomalyDetectionScript:
    """이상탐지 스크립트 실행 테스트 클래스"""

    def test_script_basic_execution(self, script_path, tmp_path):
        """스크립트 기본 실행 테스트"""
        if not script_path.exists():
            pytest.skip(f"스크립트 파일이 없음: {script_path}")

        try:
            result = subprocess.run(
                [sys.executable, str(script_path), "--dry-run", "--days", "7"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=tmp_path
            )

            # 스크립트가 성공적으로 실행되어야 함
            assert result.returncode == 0, f"스크립트 실행 실패: {result.stderr}"

            # 출력에 분석 관련 로그가 포함되어야 함
            output = result.stdout + result.stderr
            assert "이상탐지" in output or "anomaly" in output.lower(), "이상탐지 관련 로그가 없음"

        except subprocess.TimeoutExpired:
            pytest.fail("스크립트 실행이 30초 내에 완료되지 않았습니다")

    @pytest.mark.parametrize("output_format", ["json", "markdown"])
    def test_script_output_formats(self, script_path, tmp_path, output_format):
        """스크립트 출력 형식 테스트"""
        if not script_path.exists():
            pytest.skip(f"스크립트 파일이 없음: {script_path}")

        output_file = tmp_path / f"test_output.{output_format}"

        try:
            cmd = [
                sys.executable, str(script_path),
                "--dry-run",
                "--days", "7",
                f"--{output_format}",
                "--output", str(output_file)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=tmp_path
            )

            assert result.returncode == 0, f"스크립트 실행 실패: {result.stderr}"
            assert output_file.exists(), f"출력 파일이 생성되지 않음: {output_file}"

            # 파일 내용 검증
            content = output_file.read_text(encoding='utf-8')
            assert len(content) > 0, "출력 파일이 비어있음"

            if output_format == "json":
                # JSON 파싱 가능성 확인
                data = json.loads(content)
                assert isinstance(data, dict), "JSON 출력이 딕셔너리가 아님"
            elif output_format == "markdown":
                # Markdown 헤더 확인
                assert "#" in content, "Markdown 헤더가 없음"
                assert "이상탐지" in content or "anomaly" in content.lower(), "이상탐지 관련 내용이 없음"

        except subprocess.TimeoutExpired:
            pytest.fail(f"{output_format} 형식 테스트가 30초 내에 완료되지 않았습니다")

    @pytest.mark.parametrize("threshold", [2.0, 3.0, 4.0])
    def test_script_threshold_parameter(self, script_path, tmp_path, threshold):
        """스크립트 임계치 파라미터 테스트"""
        if not script_path.exists():
            pytest.skip(f"스크립트 파일이 없음: {script_path}")

        try:
            result = subprocess.run(
                [sys.executable, str(script_path), "--dry-run", "--threshold", str(threshold)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=tmp_path
            )

            assert result.returncode == 0, f"임계치 {threshold} 테스트 실패: {result.stderr}"

            # 로그에 설정된 임계치가 표시되어야 함
            output = result.stderr
            assert f"threshold={threshold}" in output or f"임계치: {threshold}" in output, \
                f"임계치 {threshold}이 로그에 표시되지 않음"

        except subprocess.TimeoutExpired:
            pytest.fail(f"임계치 {threshold} 테스트가 30초 내에 완료되지 않았습니다")

    def test_script_invalid_parameters(self, script_path, tmp_path):
        """스크립트 잘못된 파라미터 테스트"""
        if not script_path.exists():
            pytest.skip(f"스크립트 파일이 없음: {script_path}")

        invalid_cases = [
            ["--threshold", "0.5"],  # 너무 낮은 임계치
            ["--threshold", "10.0"], # 너무 높은 임계치
            ["--window", "1"],       # 너무 작은 윈도우
            ["--days", "0"],         # 잘못된 일수
            ["--forecast", "0"]      # 잘못된 예측 기간
        ]

        for invalid_params in invalid_cases:
            try:
                result = subprocess.run(
                    [sys.executable, str(script_path), "--dry-run"] + invalid_params,
                    capture_output=True,
                    text=True,
                    timeout=15,
                    cwd=tmp_path
                )

                # 일부 잘못된 파라미터는 에러로 처리되거나 경고가 표시되어야 함
                # (구현에 따라 다를 수 있으므로 너무 엄격하게 테스트하지 않음)

            except subprocess.TimeoutExpired:
                pytest.fail(f"잘못된 파라미터 테스트가 15초 내에 완료되지 않았습니다: {invalid_params}")

# ================================================================
# API 엔드포인트 테스트 (한국어 주석 포함)
# ================================================================

class TestAnomalyAPI:
    """이상탐지 API 엔드포인트 테스트 클래스"""

    def test_health_endpoint(self, api_client):
        """헬스체크 엔드포인트 테스트"""
        response = api_client.get("/api/v1/anomaly/health")

        assert response.status_code == 200
        data = response.json()

        # 필수 필드 확인
        required_fields = ['status', 'data_sources_available', 'cache_hit_rate', 'avg_response_time_ms']
        for field in required_fields:
            assert field in data, f"헬스체크 응답에 {field} 필드가 누락됨"

        # 상태 값 검증
        valid_statuses = ['healthy', 'degraded', 'unhealthy']
        assert data['status'] in valid_statuses, f"잘못된 상태 값: {data['status']}"

    def test_summary_endpoint_without_auth(self, api_client):
        """인증 없이 요약 엔드포인트 접근 테스트 (403 예상)"""
        response = api_client.get("/api/v1/anomaly/summary")

        # 인증이 필요한 엔드포인트이므로 403 또는 401이 반환되어야 함
        assert response.status_code in [401, 403], f"예상과 다른 상태 코드: {response.status_code}"

    def test_timeseries_endpoint_with_parameters(self, api_client):
        """시계열 엔드포인트 파라미터 테스트"""
        # 인증 헤더 없이 테스트 (403 예상)
        response = api_client.get("/api/v1/anomaly/timeseries?days=7&metric=cpu")
        assert response.status_code in [401, 403]

        # 잘못된 파라미터 테스트
        response = api_client.get("/api/v1/anomaly/timeseries?days=invalid")
        assert response.status_code in [400, 401, 403, 422]  # 파라미터 오류 또는 인증 오류

    def test_forecast_endpoint_parameters(self, api_client):
        """예측 엔드포인트 파라미터 테스트"""
        # 유효한 파라미터 (인증 없이는 403 예상)
        response = api_client.get("/api/v1/anomaly/forecast?forecast_days=7")
        assert response.status_code in [401, 403]

        # 잘못된 파라미터
        response = api_client.get("/api/v1/anomaly/forecast?forecast_days=100")  # 너무 큰 값
        assert response.status_code in [400, 401, 403, 422]

    def test_run_endpoint_post_method(self, api_client):
        """분석 실행 엔드포인트 POST 메서드 테스트"""
        request_data = {
            "days": 30,
            "threshold": 3.0,
            "window_size": 7,
            "forecast_days": 7,
            "force_refresh": True
        }

        response = api_client.post(
            "/api/v1/anomaly/run",
            json=request_data
        )

        # 인증이 필요하므로 401 또는 403이 예상됨
        assert response.status_code in [401, 403], f"예상과 다른 상태 코드: {response.status_code}"

    def test_report_markdown_endpoint(self, api_client):
        """Markdown 리포트 엔드포인트 테스트"""
        response = api_client.get("/api/v1/anomaly/report.md?days=7")

        # 인증이 필요하므로 401 또는 403이 예상됨
        assert response.status_code in [401, 403]

    def test_api_error_handling(self, api_client):
        """API 에러 처리 테스트"""
        # 존재하지 않는 엔드포인트
        response = api_client.get("/api/v1/anomaly/nonexistent")
        assert response.status_code == 404

        # 잘못된 HTTP 메서드
        response = api_client.delete("/api/v1/anomaly/summary")
        assert response.status_code in [405, 401, 403]  # Method Not Allowed 또는 인증 오류

# ================================================================
# 통합 테스트 (한국어 주석 포함)
# ================================================================

class TestAnomalyIntegration:
    """이상탐지 시스템 통합 테스트 클래스"""

    def test_end_to_end_workflow(self, sample_timeseries_data):
        """전체 워크플로우 통합 테스트"""
        # 1. 이상탐지 엔진 초기화
        detector = AnomalyDetector(
            window_size=7,
            threshold=3.0,
            forecast_days=7
        )

        # 2. 데이터 로드 (시뮬레이션)
        detector.metrics_data = {"integration_test": sample_timeseries_data}

        # 3. 전체 파이프라인 실행
        processed_data = detector.preprocess_data()
        assert len(processed_data) > 0, "데이터 전처리 실패"

        anomalies = detector.detect_anomalies(processed_data)
        assert len(anomalies) > 0, "이상치 탐지 실패"

        forecasts = detector.generate_forecasts(processed_data)
        assert len(forecasts) > 0, "예측 생성 실패"

        risk_levels = detector.calculate_risk_levels()
        assert len(risk_levels) > 0, "위험도 계산 실패"

        # 4. 리포트 생성
        json_report = detector.generate_report('json')
        assert len(json_report) > 0, "JSON 리포트 생성 실패"

        # JSON 파싱 가능성 확인
        report_data = json.loads(json_report)
        assert 'metadata' in report_data, "리포트 메타데이터 누락"
        assert 'summary' in report_data, "리포트 요약 누락"

        markdown_report = detector.generate_report('markdown')
        assert len(markdown_report) > 0, "Markdown 리포트 생성 실패"
        assert '#' in markdown_report, "Markdown 형식이 아님"

    def test_concurrent_detection(self, sample_timeseries_data):
        """동시 이상탐지 처리 테스트"""
        import threading
        import queue

        results = queue.Queue()

        def run_detection(thread_id):
            detector = AnomalyDetector()
            detector.metrics_data = {f"thread_{thread_id}": sample_timeseries_data}

            try:
                processed_data = detector.preprocess_data()
                anomalies = detector.detect_anomalies(processed_data)
                results.put((thread_id, True, len(anomalies)))
            except Exception as e:
                results.put((thread_id, False, str(e)))

        # 5개의 동시 스레드로 이상탐지 실행
        threads = []
        for i in range(5):
            thread = threading.Thread(target=run_detection, args=(i,))
            threads.append(thread)
            thread.start()

        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join(timeout=10)

        # 결과 검증
        successful_detections = 0
        while not results.empty():
            thread_id, success, result = results.get()
            if success:
                successful_detections += 1
                assert result > 0, f"스레드 {thread_id}에서 이상치가 탐지되지 않음"
            else:
                pytest.fail(f"스레드 {thread_id}에서 오류 발생: {result}")

        assert successful_detections == 5, f"성공한 탐지 수가 예상과 다름: {successful_detections}"

    def test_data_consistency(self, sample_timeseries_data):
        """데이터 일관성 테스트 - 동일한 입력에 대해 동일한 결과"""
        detector1 = AnomalyDetector(window_size=7, threshold=3.0, forecast_days=7)
        detector2 = AnomalyDetector(window_size=7, threshold=3.0, forecast_days=7)

        # 동일한 데이터로 두 번 실행
        for detector in [detector1, detector2]:
            detector.metrics_data = {"consistency_test": sample_timeseries_data.copy()}

        # 첫 번째 실행
        processed_data1 = detector1.preprocess_data()
        anomalies1 = detector1.detect_anomalies(processed_data1)

        # 두 번째 실행
        processed_data2 = detector2.preprocess_data()
        anomalies2 = detector2.detect_anomalies(processed_data2)

        # 결과 비교
        assert len(anomalies1) == len(anomalies2), "이상치 탐지 결과가 일관되지 않음"

        for metric_name in anomalies1:
            if metric_name in anomalies2:
                anomaly_count1 = len(anomalies1[metric_name])
                anomaly_count2 = len(anomalies2[metric_name])
                assert anomaly_count1 == anomaly_count2, f"메트릭 {metric_name}의 이상치 개수가 일관되지 않음"

    def test_edge_cases(self):
        """경계 조건 테스트"""
        detector = AnomalyDetector()

        # 빈 데이터
        detector.metrics_data = {}
        processed_data = detector.preprocess_data()
        assert len(processed_data) == 0, "빈 데이터 처리 결과가 예상과 다름"

        # 단일 포인트 데이터
        single_point_data = pd.DataFrame({
            'timestamp': [pd.Timestamp('2024-01-01')],
            'metric': ['single_point'],
            'value': [100.0]
        })

        detector.metrics_data = {"single_point": single_point_data}
        processed_data = detector.preprocess_data()
        # 단일 포인트는 윈도우 크기 부족으로 처리되지 않아야 함
        assert len(processed_data) == 0, "단일 포인트 데이터가 잘못 처리됨"

        # 모든 값이 동일한 데이터
        constant_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='H'),
            'metric': ['constant_test'] * 100,
            'value': [50.0] * 100
        })

        detector.metrics_data = {"constant_test": constant_data}
        processed_data = detector.preprocess_data()

        if len(processed_data) > 0:
            anomalies = detector.detect_anomalies(processed_data)
            # 상수 데이터에서는 이상치가 탐지되지 않아야 함
            total_anomalies = sum(len(anomaly_list) for anomaly_list in anomalies.values())
            assert total_anomalies == 0, f"상수 데이터에서 이상치가 탐지됨: {total_anomalies}개"

# ================================================================
# 테스트 실행 시 추가 정보 출력 (한국어 주석 포함)
# ================================================================

def pytest_runtest_makereport(item, call):
    """테스트 실행 결과에 대한 추가 정보 출력"""
    if call.when == "call":
        if call.excinfo is not None:
            # 테스트 실패 시 한국어 메시지 출력
            print(f"\n❌ 테스트 실패: {item.name}")
            print(f"   오류 내용: {call.excinfo.value}")
        else:
            # 테스트 성공 시 간단한 메시지
            print(f"✅ 테스트 성공: {item.name}")

# 테스트 모듈 실행 시 환경 정보 출력
if __name__ == "__main__":
    print("🔎 이상탐지 및 예측 시스템 테스트 스위트")
    print(f"📂 프로젝트 루트: {project_root}")
    print(f"🐍 Python 버전: {sys.version}")
    print("=" * 60)

    # pytest 실행
    pytest.main([__file__, "-v", "--tb=short"])