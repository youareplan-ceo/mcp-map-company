#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔎 이상탐지 백테스트 및 파라미터 튜닝 스크립트 (한국어 주석 포함)

주요 기능:
- CSV/JSON 시계열 데이터를 이용한 백테스트 실행
- Z-score 임계값, EWMA 알파, 윈도우 크기 등 파라미터 그리드 서치
- 재현율(Recall), 정밀도(Precision), F1 점수, 알림량 등 성능 지표 계산
- 과탐지율, 미탐지율 분석 및 최적 파라미터 추천
- Markdown/JSON 형식 리포트 생성

사용법:
    python scripts/anomaly_backtest.py --input data.csv --format csv
    python scripts/anomaly_backtest.py --input data.json --grid comprehensive --json
    python scripts/anomaly_backtest.py --help

작성자: Claude Code Assistant
생성일: 2024-09-21
"""

import argparse
import json
import csv
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional, Union

import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from mcp.anomaly_rca import AnomalyRCAAnalyzer
except ImportError:
    print("❌ mcp.anomaly_rca 모듈을 가져올 수 없습니다. 프로젝트 루트에서 실행하세요.")
    sys.exit(1)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

@dataclass
class BacktestConfig:
    """백테스트 설정"""
    input_file: str
    format: str = "csv"  # csv, json
    grid_preset: str = "basic"  # basic, comprehensive, custom
    output_format: str = "markdown"  # markdown, json, both
    output_file: Optional[str] = None
    dry_run: bool = False
    verbose: bool = False

@dataclass
class ParameterSet:
    """파라미터 세트"""
    threshold: float
    window_size: int
    ewma_alpha: float
    forecast_days: int = 7

@dataclass
class BacktestResult:
    """백테스트 결과"""
    parameters: ParameterSet
    precision: float
    recall: float
    f1_score: float
    total_alerts: int
    false_positive_rate: float
    false_negative_rate: float
    execution_time: float
    detected_anomalies: int
    missed_anomalies: int

@dataclass
class BacktestSummary:
    """백테스트 요약"""
    best_parameters: ParameterSet
    best_f1_score: float
    total_combinations: int
    execution_time: float
    data_points: int
    recommendation: str
    performance_matrix: List[BacktestResult]

class AnomalyBacktester:
    """이상탐지 백테스트 실행기"""

    def __init__(self, config: BacktestConfig):
        """초기화"""
        self.config = config
        self.data = None
        self.ground_truth = None  # 실제 이상치 라벨
        self.logger = logging.getLogger(f"{__name__}.AnomalyBacktester")

    def load_data(self) -> bool:
        """데이터 로드"""
        try:
            file_path = Path(self.config.input_file)
            if not file_path.exists():
                self.logger.error(f"입력 파일을 찾을 수 없습니다: {file_path}")
                return False

            if self.config.format.lower() == "csv":
                return self._load_csv_data(file_path)
            elif self.config.format.lower() == "json":
                return self._load_json_data(file_path)
            else:
                self.logger.error(f"지원하지 않는 형식: {self.config.format}")
                return False

        except Exception as e:
            self.logger.error(f"데이터 로드 실패: {e}")
            return False

    def _load_csv_data(self, file_path: Path) -> bool:
        """CSV 데이터 로드"""
        try:
            df = pd.read_csv(file_path)

            # 필수 컬럼 확인
            required_cols = ['timestamp', 'value']
            if not all(col in df.columns for col in required_cols):
                self.logger.error(f"필수 컬럼이 없습니다: {required_cols}")
                return False

            self.data = {
                'timestamps': df['timestamp'].tolist(),
                'values': df['value'].tolist()
            }

            # 실제 이상치 라벨이 있는 경우 로드
            if 'is_anomaly' in df.columns:
                self.ground_truth = df['is_anomaly'].astype(bool).tolist()
                self.logger.info(f"실제 이상치 라벨 로드: {sum(self.ground_truth)}개")
            else:
                self.logger.warning("실제 이상치 라벨이 없습니다. 합성 라벨을 생성합니다.")
                self.ground_truth = self._generate_synthetic_labels()

            self.logger.info(f"CSV 데이터 로드 완료: {len(self.data['values'])}개 포인트")
            return True

        except Exception as e:
            self.logger.error(f"CSV 로드 실패: {e}")
            return False

    def _load_json_data(self, file_path: Path) -> bool:
        """JSON 데이터 로드"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)

            # 형식 확인 및 변환
            if isinstance(json_data, dict):
                if 'data' in json_data:
                    # {data: [{timestamp, value, is_anomaly?}, ...]} 형식
                    data_list = json_data['data']
                    self.data = {
                        'timestamps': [item.get('timestamp', f'T{i}') for i, item in enumerate(data_list)],
                        'values': [item['value'] for item in data_list]
                    }

                    if 'is_anomaly' in data_list[0]:
                        self.ground_truth = [item['is_anomaly'] for item in data_list]
                elif 'values' in json_data:
                    # {timestamps: [...], values: [...], labels?: [...]} 형식
                    self.data = {
                        'timestamps': json_data.get('timestamps', [f'T{i}' for i in range(len(json_data['values']))]),
                        'values': json_data['values']
                    }
                    self.ground_truth = json_data.get('labels')
            elif isinstance(json_data, list):
                # 단순 값 배열 형식
                self.data = {
                    'timestamps': [f'T{i}' for i in range(len(json_data))],
                    'values': json_data
                }

            if self.ground_truth is None:
                self.logger.warning("실제 이상치 라벨이 없습니다. 합성 라벨을 생성합니다.")
                self.ground_truth = self._generate_synthetic_labels()

            self.logger.info(f"JSON 데이터 로드 완료: {len(self.data['values'])}개 포인트")
            return True

        except Exception as e:
            self.logger.error(f"JSON 로드 실패: {e}")
            return False

    def _generate_synthetic_labels(self) -> List[bool]:
        """합성 이상치 라벨 생성 (Z-score 3.0 기준)"""
        values = np.array(self.data['values'])
        mean_val = np.mean(values)
        std_val = np.std(values)

        if std_val == 0:
            return [False] * len(values)

        z_scores = np.abs((values - mean_val) / std_val)
        return (z_scores > 3.0).tolist()

    def get_parameter_grid(self) -> List[ParameterSet]:
        """파라미터 그리드 생성"""
        if self.config.grid_preset == "basic":
            return self._get_basic_grid()
        elif self.config.grid_preset == "comprehensive":
            return self._get_comprehensive_grid()
        else:
            return self._get_custom_grid()

    def _get_basic_grid(self) -> List[ParameterSet]:
        """기본 파라미터 그리드"""
        grid = []

        for threshold in [2.0, 2.5, 3.0, 3.5]:
            for window_size in [5, 7, 10]:
                for ewma_alpha in [0.2, 0.3, 0.5]:
                    grid.append(ParameterSet(
                        threshold=threshold,
                        window_size=window_size,
                        ewma_alpha=ewma_alpha,
                        forecast_days=7
                    ))

        return grid

    def _get_comprehensive_grid(self) -> List[ParameterSet]:
        """포괄적 파라미터 그리드"""
        grid = []

        for threshold in [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5]:
            for window_size in [3, 5, 7, 10, 14]:
                for ewma_alpha in [0.1, 0.2, 0.3, 0.4, 0.5, 0.7]:
                    for forecast_days in [3, 7, 14]:
                        grid.append(ParameterSet(
                            threshold=threshold,
                            window_size=window_size,
                            ewma_alpha=ewma_alpha,
                            forecast_days=forecast_days
                        ))

        return grid

    def _get_custom_grid(self) -> List[ParameterSet]:
        """커스텀 파라미터 그리드 (환경변수에서 로드)"""
        # 환경변수나 설정 파일에서 커스텀 그리드 로드
        # 현재는 기본 그리드 반환
        return self._get_basic_grid()

    def run_backtest(self) -> BacktestSummary:
        """백테스트 실행"""
        try:
            start_time = time.time()

            self.logger.info("🔎 이상탐지 백테스트 시작...")

            if not self.load_data():
                raise Exception("데이터 로드 실패")

            parameter_grid = self.get_parameter_grid()
            self.logger.info(f"📊 파라미터 조합 {len(parameter_grid)}개로 백테스트 시작")

            results = []
            best_result = None
            best_f1 = 0.0

            for i, params in enumerate(parameter_grid, 1):
                if self.config.verbose:
                    self.logger.info(f"진행상황: {i}/{len(parameter_grid)} - {params}")

                result = self._test_parameters(params)
                results.append(result)

                if result.f1_score > best_f1:
                    best_f1 = result.f1_score
                    best_result = result

            execution_time = time.time() - start_time

            # 추천 메시지 생성
            recommendation = self._generate_recommendation(best_result, results)

            summary = BacktestSummary(
                best_parameters=best_result.parameters,
                best_f1_score=best_f1,
                total_combinations=len(parameter_grid),
                execution_time=execution_time,
                data_points=len(self.data['values']),
                recommendation=recommendation,
                performance_matrix=results
            )

            self.logger.info(f"✅ 백테스트 완료: 최고 F1 점수 {best_f1:.3f} (실행시간: {execution_time:.1f}초)")

            return summary

        except Exception as e:
            self.logger.error(f"백테스트 실행 실패: {e}")
            raise

    def _test_parameters(self, params: ParameterSet) -> BacktestResult:
        """개별 파라미터 세트 테스트"""
        start_time = time.time()

        try:
            # 간단한 이상탐지 시뮬레이션
            values = np.array(self.data['values'])
            detected_anomalies = []

            # EWMA 적용
            ewma = np.zeros_like(values)
            ewma[0] = values[0]
            for i in range(1, len(values)):
                ewma[i] = params.ewma_alpha * values[i] + (1 - params.ewma_alpha) * ewma[i-1]

            # 롤링 윈도우로 이상탐지
            for i in range(params.window_size, len(values)):
                window_data = ewma[i-params.window_size:i]
                mean_val = np.mean(window_data)
                std_val = np.std(window_data)

                if std_val > 0:
                    z_score = abs((ewma[i] - mean_val) / std_val)
                    if z_score >= params.threshold:
                        detected_anomalies.append(i)

            # 성능 지표 계산
            predicted = [False] * len(values)
            for idx in detected_anomalies:
                predicted[idx] = True

            precision, recall, f1_score = self._calculate_metrics(self.ground_truth, predicted)

            # 추가 지표
            false_positives = sum(1 for i, (true, pred) in enumerate(zip(self.ground_truth, predicted))
                                if pred and not true)
            false_negatives = sum(1 for i, (true, pred) in enumerate(zip(self.ground_truth, predicted))
                                if true and not pred)

            total_predicted = sum(predicted)
            total_actual = sum(self.ground_truth)

            false_positive_rate = false_positives / (len(values) - total_actual) if (len(values) - total_actual) > 0 else 0
            false_negative_rate = false_negatives / total_actual if total_actual > 0 else 0

            execution_time = time.time() - start_time

            return BacktestResult(
                parameters=params,
                precision=precision,
                recall=recall,
                f1_score=f1_score,
                total_alerts=total_predicted,
                false_positive_rate=false_positive_rate,
                false_negative_rate=false_negative_rate,
                execution_time=execution_time,
                detected_anomalies=len(detected_anomalies),
                missed_anomalies=false_negatives
            )

        except Exception as e:
            self.logger.warning(f"파라미터 테스트 실패 {params}: {e}")
            return BacktestResult(
                parameters=params,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                total_alerts=0,
                false_positive_rate=1.0,
                false_negative_rate=1.0,
                execution_time=time.time() - start_time,
                detected_anomalies=0,
                missed_anomalies=sum(self.ground_truth)
            )

    def _calculate_metrics(self, y_true: List[bool], y_pred: List[bool]) -> Tuple[float, float, float]:
        """정밀도, 재현율, F1 점수 계산"""
        true_positives = sum(1 for true, pred in zip(y_true, y_pred) if true and pred)
        false_positives = sum(1 for true, pred in zip(y_true, y_pred) if not true and pred)
        false_negatives = sum(1 for true, pred in zip(y_true, y_pred) if true and not pred)

        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        return precision, recall, f1_score

    def _generate_recommendation(self, best_result: BacktestResult, all_results: List[BacktestResult]) -> str:
        """추천 메시지 생성"""
        if not best_result:
            return "최적 파라미터를 찾지 못했습니다. 데이터나 그리드 설정을 확인하세요."

        params = best_result.parameters

        # 성능 평가
        if best_result.f1_score >= 0.8:
            performance = "우수"
        elif best_result.f1_score >= 0.6:
            performance = "양호"
        elif best_result.f1_score >= 0.4:
            performance = "보통"
        else:
            performance = "개선 필요"

        # 추천 메시지
        recommendation = f"""
🎯 최적 파라미터 추천:
- Z-score 임계값: {params.threshold}
- 윈도우 크기: {params.window_size}일
- EWMA 알파: {params.ewma_alpha}
- 예측 기간: {params.forecast_days}일

📊 성능 평가: {performance} (F1: {best_result.f1_score:.3f})
- 정밀도: {best_result.precision:.3f}
- 재현율: {best_result.recall:.3f}
- 일일 평균 알림: {best_result.total_alerts}개
- 과탐지율: {best_result.false_positive_rate:.1%}
- 미탐지율: {best_result.false_negative_rate:.1%}

💡 권장사항:
"""

        # 맞춤형 권장사항
        if best_result.false_positive_rate > 0.1:
            recommendation += "- 임계값을 높여 과탐지를 줄이는 것을 고려하세요.\n"

        if best_result.false_negative_rate > 0.2:
            recommendation += "- 임계값을 낮춰 미탐지를 줄이는 것을 고려하세요.\n"

        if best_result.total_alerts > 50:
            recommendation += "- 알림량이 많습니다. 서프레션 룰 적용을 고려하세요.\n"

        if best_result.execution_time > 5.0:
            recommendation += "- 처리 시간이 깁니다. 윈도우 크기를 줄이는 것을 고려하세요.\n"

        return recommendation.strip()

    def save_results(self, summary: BacktestSummary) -> bool:
        """결과 저장"""
        try:
            if self.config.dry_run:
                self.logger.info("🔍 Dry-run 모드: 파일을 생성하지 않습니다")
                self._print_summary(summary)
                return True

            output_file = self.config.output_file
            if not output_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"anomaly_backtest_{timestamp}"

            success = True

            if self.config.output_format in ["markdown", "both"]:
                md_file = f"{output_file}.md"
                if self._save_markdown_report(summary, md_file):
                    self.logger.info(f"📝 Markdown 리포트 저장: {md_file}")
                else:
                    success = False

            if self.config.output_format in ["json", "both"]:
                json_file = f"{output_file}.json"
                if self._save_json_report(summary, json_file):
                    self.logger.info(f"📄 JSON 리포트 저장: {json_file}")
                else:
                    success = False

            return success

        except Exception as e:
            self.logger.error(f"결과 저장 실패: {e}")
            return False

    def _save_markdown_report(self, summary: BacktestSummary, filename: str) -> bool:
        """Markdown 리포트 저장"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self._generate_markdown_report(summary))
            return True
        except Exception as e:
            self.logger.error(f"Markdown 저장 실패: {e}")
            return False

    def _save_json_report(self, summary: BacktestSummary, filename: str) -> bool:
        """JSON 리포트 저장"""
        try:
            # dataclass를 dict로 변환
            json_data = {
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "input_file": self.config.input_file,
                    "data_format": self.config.format,
                    "grid_preset": self.config.grid_preset,
                    "data_points": summary.data_points
                },
                "summary": {
                    "best_parameters": asdict(summary.best_parameters),
                    "best_f1_score": summary.best_f1_score,
                    "total_combinations": summary.total_combinations,
                    "execution_time": summary.execution_time,
                    "recommendation": summary.recommendation
                },
                "results": [asdict(result) for result in summary.performance_matrix[:10]]  # 상위 10개만
            }

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"JSON 저장 실패: {e}")
            return False

    def _generate_markdown_report(self, summary: BacktestSummary) -> str:
        """Markdown 리포트 생성"""
        report = f"""# 🔎 이상탐지 백테스트 리포트

생성일시: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 📊 백테스트 요약

- **입력 파일**: {self.config.input_file}
- **데이터 포인트**: {summary.data_points:,}개
- **파라미터 조합**: {summary.total_combinations}개
- **실행 시간**: {summary.execution_time:.1f}초

## 🎯 최적 파라미터

| 파라미터 | 값 |
|---------|-----|
| Z-score 임계값 | {summary.best_parameters.threshold} |
| 윈도우 크기 | {summary.best_parameters.window_size}일 |
| EWMA 알파 | {summary.best_parameters.ewma_alpha} |
| 예측 기간 | {summary.best_parameters.forecast_days}일 |

## 📈 성능 지표

| 지표 | 값 |
|------|-----|
| **F1 점수** | **{summary.best_f1_score:.3f}** |
| 정밀도 | {summary.performance_matrix[0].precision:.3f} |
| 재현율 | {summary.performance_matrix[0].recall:.3f} |
| 총 알림 수 | {summary.performance_matrix[0].total_alerts}개 |
| 과탐지율 | {summary.performance_matrix[0].false_positive_rate:.1%} |
| 미탐지율 | {summary.performance_matrix[0].false_negative_rate:.1%} |

## 💡 권장사항

{summary.recommendation}

## 📋 상위 성능 결과

| 순위 | F1 점수 | 임계값 | 윈도우 | EWMA | 정밀도 | 재현율 | 알림수 |
|------|---------|--------|--------|------|--------|--------|--------|
"""

        # 상위 10개 결과 추가
        sorted_results = sorted(summary.performance_matrix, key=lambda x: x.f1_score, reverse=True)
        for i, result in enumerate(sorted_results[:10], 1):
            report += f"| {i} | {result.f1_score:.3f} | {result.parameters.threshold} | {result.parameters.window_size} | {result.parameters.ewma_alpha} | {result.precision:.3f} | {result.recall:.3f} | {result.total_alerts} |\n"

        report += f"""

## 🔧 실행 정보

- **실행 명령**: `python scripts/anomaly_backtest.py --input {self.config.input_file} --format {self.config.format} --grid {self.config.grid_preset}`
- **설정**:
  - 그리드 프리셋: {self.config.grid_preset}
  - 출력 형식: {self.config.output_format}
  - Dry-run 모드: {self.config.dry_run}
- **총 테스트 시간**: {summary.execution_time:.1f}초

---
*이 리포트는 anomaly_backtest.py 스크립트로 자동 생성되었습니다.*
"""

        return report

    def _print_summary(self, summary: BacktestSummary):
        """콘솔에 요약 출력"""
        print(f"""
🔎 이상탐지 백테스트 결과 요약

📊 데이터: {summary.data_points:,}개 포인트, {summary.total_combinations}개 조합 테스트
⏱️  실행시간: {summary.execution_time:.1f}초

🎯 최적 파라미터:
   임계값: {summary.best_parameters.threshold}
   윈도우: {summary.best_parameters.window_size}일
   EWMA α: {summary.best_parameters.ewma_alpha}

📈 최고 성능:
   F1 점수: {summary.best_f1_score:.3f}
   정밀도: {summary.performance_matrix[0].precision:.3f}
   재현율: {summary.performance_matrix[0].recall:.3f}

{summary.recommendation}
""")

def create_sample_data(filename: str = "sample_anomaly_data.csv", size: int = 1000):
    """샘플 데이터 생성"""
    logger.info(f"📝 샘플 데이터 생성: {filename} ({size}개 포인트)")

    np.random.seed(42)

    # 기본 시계열 + 노이즈
    timestamps = [f"2024-09-{(i//24)+1:02d} {i%24:02d}:00:00" for i in range(size)]

    # 정상 패턴 생성
    t = np.arange(size)
    normal_pattern = 50 + 20 * np.sin(2 * np.pi * t / 24) + np.random.normal(0, 5, size)

    # 이상치 주입 (5% 정도)
    anomaly_indices = np.random.choice(size, size=size//20, replace=False)
    values = normal_pattern.copy()
    is_anomaly = np.zeros(size, dtype=bool)

    for idx in anomaly_indices:
        values[idx] += np.random.choice([-1, 1]) * np.random.uniform(30, 50)
        is_anomaly[idx] = True

    # CSV 저장
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'value', 'is_anomaly'])
        for ts, val, anomaly in zip(timestamps, values, is_anomaly):
            writer.writerow([ts, f"{val:.2f}", anomaly])

    logger.info(f"✅ 샘플 데이터 생성 완료: 이상치 {sum(is_anomaly)}개 포함")

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="🔎 이상탐지 백테스트 및 파라미터 튜닝",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  %(prog)s --input data.csv --format csv
  %(prog)s --input data.json --grid comprehensive --json
  %(prog)s --sample  # 샘플 데이터 생성
  %(prog)s --input sample_anomaly_data.csv --grid basic --md
        """
    )

    parser.add_argument('--input', type=str, help='입력 데이터 파일 경로')
    parser.add_argument('--format', choices=['csv', 'json'], default='csv',
                       help='입력 데이터 형식 (기본값: csv)')
    parser.add_argument('--grid', choices=['basic', 'comprehensive', 'custom'], default='basic',
                       help='파라미터 그리드 프리셋 (기본값: basic)')
    parser.add_argument('--output-file', type=str, help='출력 파일 경로 (확장자 제외)')
    parser.add_argument('--json', action='store_true', help='JSON 형식으로 출력')
    parser.add_argument('--md', action='store_true', help='Markdown 형식으로 출력')
    parser.add_argument('--both', action='store_true', help='JSON과 Markdown 모두 출력')
    parser.add_argument('--dry-run', action='store_true', help='파일을 생성하지 않고 결과만 출력')
    parser.add_argument('--verbose', '-v', action='store_true', help='상세 출력')
    parser.add_argument('--sample', action='store_true', help='샘플 데이터 생성 후 종료')

    args = parser.parse_args()

    # 샘플 데이터 생성
    if args.sample:
        create_sample_data()
        return

    # 입력 파일 검증
    if not args.input:
        parser.error("--input 파라미터가 필요합니다 (또는 --sample 사용)")

    # 출력 형식 결정
    if args.both:
        output_format = "both"
    elif args.json:
        output_format = "json"
    elif args.md:
        output_format = "markdown"
    else:
        output_format = "markdown"  # 기본값

    # 설정 생성
    config = BacktestConfig(
        input_file=args.input,
        format=args.format,
        grid_preset=args.grid,
        output_format=output_format,
        output_file=args.output_file,
        dry_run=args.dry_run,
        verbose=args.verbose
    )

    try:
        # 백테스터 실행
        backtester = AnomalyBacktester(config)
        summary = backtester.run_backtest()

        # 결과 저장
        if backtester.save_results(summary):
            logger.info("✅ 백테스트 완료 및 결과 저장 성공")
        else:
            logger.error("❌ 결과 저장 실패")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단되었습니다")
        sys.exit(1)
    except Exception as e:
        logger.error(f"백테스트 실행 실패: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()