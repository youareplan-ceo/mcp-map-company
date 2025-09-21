#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔎 이상탐지 및 예측 API 엔드포인트 (한국어 주석 포함)

FastAPI 라우터로 이상탐지 분석 결과를 RESTful API로 제공
캐시 및 RBAC(Role-Based Access Control) 적용

주요 엔드포인트:
- GET /api/v1/anomaly/summary          # 최신 요약 정보
- GET /api/v1/anomaly/timeseries       # 시계열 이상치 마킹 데이터
- GET /api/v1/anomaly/forecast         # 7일 예측 정보
- POST /api/v1/anomaly/run             # 분석 실행 트리거
- GET /api/v1/anomaly/report.md        # Markdown 리포트
- GET /api/v1/anomaly/health           # 헬스체크

작성자: MCP Map Company 운영팀
생성일: 2024년 이상탐지 시스템 프로젝트
"""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel, Field
import aiofiles

# 내부 모듈
from .auth import require_role, get_current_user, RoleEnum
from .cache import cache_response, get_cached_data, set_cache_data

# 로깅 설정
logger = logging.getLogger(__name__)

# ================================================================
# 데이터 모델 (Pydantic Models) - 한국어 주석 포함
# ================================================================

class AnomalySummary(BaseModel):
    """이상탐지 요약 정보 모델"""
    total_anomalies: int = Field(..., description="총 이상치 개수")
    high_risk_metrics: int = Field(..., description="고위험 메트릭 수")
    future_risk_periods: int = Field(..., description="7일 예측 위험 구간 수")
    confidence_score: float = Field(..., ge=0, le=1, description="전체 신뢰도 점수")
    last_updated: str = Field(..., description="마지막 분석 시간 (ISO 형식)")
    analysis_period_days: int = Field(..., description="분석 기간 (일)")
    metrics_analyzed: int = Field(..., description="분석된 메트릭 수")

class AnomalyPoint(BaseModel):
    """개별 이상치 포인트 모델"""
    timestamp: str = Field(..., description="이상치 발생 시간")
    metric: str = Field(..., description="메트릭 이름")
    value: float = Field(..., description="실제 값")
    expected_value: float = Field(..., description="예상 값 (EWMA)")
    z_score: float = Field(..., description="Z-score 값")
    severity: str = Field(..., description="심각도 (low/medium/high/critical)")
    direction: str = Field(..., description="방향 (increase/decrease)")

class TimeSeriesData(BaseModel):
    """시계열 데이터 모델"""
    metric: str = Field(..., description="메트릭 이름")
    timestamps: List[str] = Field(..., description="시간 배열")
    values: List[float] = Field(..., description="값 배열")
    expected_values: List[float] = Field(..., description="예상 값 배열 (EWMA)")
    anomaly_points: List[AnomalyPoint] = Field(..., description="이상치 포인트들")
    risk_level: str = Field(..., description="위험도 수준")

class ForecastPoint(BaseModel):
    """예측 포인트 모델"""
    date: str = Field(..., description="예측 날짜")
    predicted_value: float = Field(..., description="예측 값")
    lower_bound: float = Field(..., description="신뢰구간 하한")
    upper_bound: float = Field(..., description="신뢰구간 상한")
    confidence: float = Field(..., ge=0, le=1, description="신뢰도")

class ForecastData(BaseModel):
    """예측 데이터 모델"""
    metric: str = Field(..., description="메트릭 이름")
    forecast_points: List[ForecastPoint] = Field(..., description="예측 포인트들")
    trend_direction: str = Field(..., description="추세 방향 (increasing/decreasing)")
    trend_strength: float = Field(..., description="추세 강도")
    model_accuracy: float = Field(..., ge=0, le=1, description="모델 정확도")
    risk_periods: List[Dict[str, Any]] = Field(..., description="위험 예측 구간들")

class AnalysisRequest(BaseModel):
    """분석 실행 요청 모델"""
    days: Optional[int] = Field(30, ge=1, le=365, description="분석 기간 (일)")
    threshold: Optional[float] = Field(3.0, ge=1.0, le=5.0, description="Z-score 임계치")
    window_size: Optional[int] = Field(7, ge=3, le=30, description="롤링 윈도우 크기")
    forecast_days: Optional[int] = Field(7, ge=1, le=30, description="예측 기간 (일)")
    force_refresh: Optional[bool] = Field(False, description="캐시 무시 강제 실행")

class HealthStatus(BaseModel):
    """헬스체크 상태 모델"""
    status: str = Field(..., description="서비스 상태 (healthy/degraded/unhealthy)")
    last_analysis_time: Optional[str] = Field(None, description="마지막 분석 시간")
    data_sources_available: Dict[str, bool] = Field(..., description="데이터 소스별 가용성")
    cache_hit_rate: float = Field(..., description="캐시 히트율")
    avg_response_time_ms: float = Field(..., description="평균 응답 시간 (밀리초)")

# ================================================================
# FastAPI 라우터 생성
# ================================================================

router = APIRouter(
    prefix="/api/v1/anomaly",
    tags=["anomaly"],
    responses={
        404: {"description": "요청한 리소스를 찾을 수 없음"},
        403: {"description": "접근 권한 없음"},
        500: {"description": "내부 서버 오류"}
    }
)

# ================================================================
# 유틸리티 함수들 (한국어 주석 포함)
# ================================================================

async def run_anomaly_script(
    days: int = 30,
    threshold: float = 3.0,
    window: int = 7,
    forecast: int = 7,
    output_format: str = "json"
) -> Optional[str]:
    """
    이상탐지 스크립트를 비동기로 실행

    Args:
        days: 분석 기간 (일)
        threshold: Z-score 임계치
        window: 롤링 윈도우 크기
        forecast: 예측 기간
        output_format: 출력 형식 (json/markdown)

    Returns:
        str: 스크립트 실행 결과 또는 None (실패시)
    """
    try:
        script_path = Path(__file__).parent.parent / "scripts" / "anomaly_detect.py"

        if not script_path.exists():
            logger.error(f"이상탐지 스크립트를 찾을 수 없음: {script_path}")
            return None

        # 임시 출력 파일 생성
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{output_format}', delete=False) as temp_file:
            temp_output_path = temp_file.name

        # 스크립트 실행 명령 구성
        cmd = [
            "python3", str(script_path),
            "--days", str(days),
            "--threshold", str(threshold),
            "--window", str(window),
            "--forecast", str(forecast),
            "--output", temp_output_path
        ]

        if output_format == "json":
            cmd.append("--json")
        elif output_format == "markdown":
            cmd.append("--md")

        logger.info(f"이상탐지 스크립트 실행: {' '.join(cmd)}")

        # 비동기 프로세스 실행
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=script_path.parent.parent
        )

        # 타임아웃 60초로 프로세스 완료 대기
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60.0)
        except asyncio.TimeoutError:
            process.kill()
            logger.error("이상탐지 스크립트 실행 타임아웃 (60초)")
            return None

        if process.returncode == 0:
            # 성공적으로 실행됨 - 결과 파일 읽기
            try:
                async with aiofiles.open(temp_output_path, 'r', encoding='utf-8') as f:
                    result = await f.read()

                # 임시 파일 정리
                os.unlink(temp_output_path)

                logger.info(f"이상탐지 스크립트 실행 성공 ({len(result)} bytes)")
                return result

            except Exception as e:
                logger.error(f"결과 파일 읽기 실패: {str(e)}")
                return None
        else:
            # 실행 실패
            error_msg = stderr.decode('utf-8') if stderr else "알 수 없는 오류"
            logger.error(f"이상탐지 스크립트 실행 실패 (코드 {process.returncode}): {error_msg}")
            return None

    except Exception as e:
        logger.error(f"이상탐지 스크립트 실행 중 예외 발생: {str(e)}")
        return None

def parse_analysis_result(result_json: str) -> Optional[Dict[str, Any]]:
    """
    스크립트 실행 결과 JSON을 파싱하여 구조화된 데이터로 변환

    Args:
        result_json: JSON 형식의 분석 결과

    Returns:
        Dict: 파싱된 분석 결과
    """
    try:
        data = json.loads(result_json)

        # 필수 필드 검증
        required_fields = ['metadata', 'summary', 'top_anomalies', 'risk_levels']
        for field in required_fields:
            if field not in data:
                logger.warning(f"분석 결과에 필수 필드 누락: {field}")
                return None

        return data

    except json.JSONDecodeError as e:
        logger.error(f"분석 결과 JSON 파싱 실패: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"분석 결과 처리 중 오류: {str(e)}")
        return None

def check_data_source_availability() -> Dict[str, bool]:
    """
    데이터 소스들의 가용성 확인

    Returns:
        Dict[str, bool]: 소스별 가용성 상태
    """
    sources = {
        "metrics_json": False,
        "log_files": False,
        "ci_reports": False
    }

    try:
        base_path = Path(__file__).parent.parent

        # 메트릭 JSON 파일들 확인
        metrics_dir = base_path / "reports" / "metrics"
        if metrics_dir.exists() and any(metrics_dir.glob("*.json")):
            sources["metrics_json"] = True

        # 로그 파일들 확인
        logs_dir = base_path / "logs"
        if logs_dir.exists() and any(logs_dir.glob("*.log")):
            sources["log_files"] = True

        # CI 리포트 파일들 확인
        ci_dir = base_path / "reports" / "ci_reports"
        if ci_dir.exists() and any(ci_dir.glob("*.json")):
            sources["ci_reports"] = True

    except Exception as e:
        logger.warning(f"데이터 소스 확인 중 오류: {str(e)}")

    return sources

# ================================================================
# API 엔드포인트들 (한국어 주석 포함)
# ================================================================

@router.get("/health", response_model=HealthStatus,
           summary="헬스체크", description="이상탐지 서비스의 상태를 확인합니다")
async def health_check():
    """
    이상탐지 서비스 헬스체크

    접근 권한: 모든 사용자
    캐시: 30초
    """
    try:
        # 캐시 확인
        cached_health = await get_cached_data("anomaly_health")
        if cached_health:
            return JSONResponse(cached_health)

        # 데이터 소스 가용성 확인
        data_sources = check_data_source_availability()

        # 마지막 분석 시간 확인
        last_analysis_cache = await get_cached_data("anomaly_last_analysis")
        last_analysis_time = last_analysis_cache.get("timestamp") if last_analysis_cache else None

        # 캐시 히트율 계산 (간단한 추정)
        cache_hit_rate = 0.75  # 실제로는 캐시 통계에서 가져와야 함

        # 전체 상태 판정
        available_sources = sum(data_sources.values())
        if available_sources >= 2:
            status = "healthy"
        elif available_sources == 1:
            status = "degraded"
        else:
            status = "unhealthy"

        health_data = {
            "status": status,
            "last_analysis_time": last_analysis_time,
            "data_sources_available": data_sources,
            "cache_hit_rate": cache_hit_rate,
            "avg_response_time_ms": 150.0  # 실제로는 메트릭에서 수집
        }

        # 캐시에 30초간 저장
        await set_cache_data("anomaly_health", health_data, ttl=30)

        return JSONResponse(health_data)

    except Exception as e:
        logger.error(f"헬스체크 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="헬스체크 실행 중 오류 발생")

@router.get("/summary", response_model=AnomalySummary,
           summary="이상탐지 요약", description="최신 이상탐지 분석 요약 정보를 반환합니다")
async def get_anomaly_summary(
    current_user = Depends(require_role([RoleEnum.ADMIN, RoleEnum.OPERATOR]))
):
    """
    이상탐지 분석 요약 정보 조회

    접근 권한: admin, operator
    캐시: 5분
    """
    try:
        # 캐시 확인 (5분)
        cached_summary = await get_cached_data("anomaly_summary")
        if cached_summary:
            return JSONResponse(cached_summary)

        logger.info("이상탐지 요약 정보 생성 시작")

        # 최신 분석 결과 가져오기
        result_json = await run_anomaly_script(days=30, output_format="json")
        if not result_json:
            raise HTTPException(status_code=503, detail="이상탐지 분석 실행 실패")

        analysis_data = parse_analysis_result(result_json)
        if not analysis_data:
            raise HTTPException(status_code=502, detail="분석 결과 파싱 실패")

        # 요약 정보 추출
        metadata = analysis_data.get("metadata", {})
        summary = analysis_data.get("summary", {})

        # 신뢰도 점수 계산 (예측 모델 정확도 평균)
        forecasts = analysis_data.get("forecasts", {})
        accuracy_scores = [f.get("model_accuracy", 0.5) for f in forecasts.values()]
        confidence_score = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0.5

        summary_data = {
            "total_anomalies": summary.get("total_anomalies", 0),
            "high_risk_metrics": summary.get("high_risk_metrics", 0),
            "future_risk_periods": summary.get("total_future_risk_periods", 0),
            "confidence_score": confidence_score,
            "last_updated": metadata.get("generated_at", datetime.now().isoformat()),
            "analysis_period_days": metadata.get("analysis_window_days", 30),
            "metrics_analyzed": metadata.get("total_metrics_analyzed", 0)
        }

        # 캐시에 5분간 저장
        await set_cache_data("anomaly_summary", summary_data, ttl=300)

        logger.info("이상탐지 요약 정보 생성 완료")
        return JSONResponse(summary_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"요약 정보 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="요약 정보 조회 중 오류 발생")

@router.get("/timeseries", response_model=List[TimeSeriesData],
           summary="시계열 이상치 데이터", description="메트릭별 시계열 데이터와 이상치 마킹 정보를 반환합니다")
async def get_timeseries_data(
    metric: Optional[str] = Query(None, description="특정 메트릭 필터링"),
    days: int = Query(7, ge=1, le=30, description="조회 기간 (일)"),
    current_user = Depends(require_role([RoleEnum.ADMIN, RoleEnum.OPERATOR]))
):
    """
    시계열 이상치 마킹 데이터 조회

    접근 권한: admin, operator
    캐시: 5분
    """
    try:
        cache_key = f"anomaly_timeseries_{metric or 'all'}_{days}"
        cached_data = await get_cached_data(cache_key)
        if cached_data:
            return JSONResponse(cached_data)

        logger.info(f"시계열 데이터 조회: metric={metric}, days={days}")

        # 분석 실행
        result_json = await run_anomaly_script(days=days, output_format="json")
        if not result_json:
            raise HTTPException(status_code=503, detail="이상탐지 분석 실행 실패")

        analysis_data = parse_analysis_result(result_json)
        if not analysis_data:
            raise HTTPException(status_code=502, detail="분석 결과 파싱 실패")

        # 시계열 데이터 구성
        timeseries_list = []

        anomalies = analysis_data.get("detailed_anomalies", {})
        risk_levels = analysis_data.get("risk_levels", {})

        for metric_name, anomaly_list in anomalies.items():
            # 특정 메트릭 필터링
            if metric and metric not in metric_name:
                continue

            # 이상치 포인트들을 AnomalyPoint 모델로 변환
            anomaly_points = []
            timestamps = []
            values = []
            expected_values = []

            for anomaly in anomaly_list:
                point = AnomalyPoint(
                    timestamp=anomaly["timestamp"],
                    metric=metric_name,
                    value=anomaly["value"],
                    expected_value=anomaly["ewma"],
                    z_score=anomaly["z_score"],
                    severity=anomaly["severity"],
                    direction=anomaly["direction"]
                )
                anomaly_points.append(point)
                timestamps.append(anomaly["timestamp"])
                values.append(anomaly["value"])
                expected_values.append(anomaly["ewma"])

            if anomaly_points:  # 이상치가 있는 메트릭만 포함
                timeseries_data = TimeSeriesData(
                    metric=metric_name,
                    timestamps=timestamps,
                    values=values,
                    expected_values=expected_values,
                    anomaly_points=anomaly_points,
                    risk_level=risk_levels.get(metric_name, "low")
                )
                timeseries_list.append(timeseries_data.dict())

        # 캐시에 5분간 저장
        await set_cache_data(cache_key, timeseries_list, ttl=300)

        logger.info(f"시계열 데이터 조회 완료: {len(timeseries_list)}개 메트릭")
        return JSONResponse(timeseries_list)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"시계열 데이터 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="시계열 데이터 조회 중 오류 발생")

@router.get("/forecast", response_model=List[ForecastData],
           summary="예측 데이터", description="향후 7일간의 메트릭 예측 정보를 반환합니다")
async def get_forecast_data(
    metric: Optional[str] = Query(None, description="특정 메트릭 필터링"),
    forecast_days: int = Query(7, ge=1, le=30, description="예측 기간 (일)"),
    current_user = Depends(require_role([RoleEnum.ADMIN, RoleEnum.OPERATOR]))
):
    """
    메트릭 예측 데이터 조회

    접근 권한: admin, operator
    캐시: 10분
    """
    try:
        cache_key = f"anomaly_forecast_{metric or 'all'}_{forecast_days}"
        cached_data = await get_cached_data(cache_key)
        if cached_data:
            return JSONResponse(cached_data)

        logger.info(f"예측 데이터 조회: metric={metric}, forecast_days={forecast_days}")

        # 분석 실행
        result_json = await run_anomaly_script(forecast=forecast_days, output_format="json")
        if not result_json:
            raise HTTPException(status_code=503, detail="이상탐지 분석 실행 실패")

        analysis_data = parse_analysis_result(result_json)
        if not analysis_data:
            raise HTTPException(status_code=502, detail="분석 결과 파싱 실패")

        # 예측 데이터 구성
        forecast_list = []

        forecasts = analysis_data.get("forecasts", {})

        for metric_name, forecast_info in forecasts.items():
            # 특정 메트릭 필터링
            if metric and metric not in metric_name:
                continue

            # 예측 포인트들을 ForecastPoint 모델로 변환
            forecast_points = []
            for point in forecast_info.get("forecast_points", []):
                forecast_point = ForecastPoint(
                    date=point["date"],
                    predicted_value=point["predicted_value"],
                    lower_bound=point["lower_bound"],
                    upper_bound=point["upper_bound"],
                    confidence=point["confidence"]
                )
                forecast_points.append(forecast_point)

            if forecast_points:  # 예측 데이터가 있는 메트릭만 포함
                forecast_data = ForecastData(
                    metric=metric_name,
                    forecast_points=[p.dict() for p in forecast_points],
                    trend_direction=forecast_info.get("trend_direction", "stable"),
                    trend_strength=forecast_info.get("trend_strength", 0.0),
                    model_accuracy=forecast_info.get("model_accuracy", 0.5),
                    risk_periods=forecast_info.get("risk_periods", [])
                )
                forecast_list.append(forecast_data.dict())

        # 캐시에 10분간 저장
        await set_cache_data(cache_key, forecast_list, ttl=600)

        logger.info(f"예측 데이터 조회 완료: {len(forecast_list)}개 메트릭")
        return JSONResponse(forecast_list)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"예측 데이터 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="예측 데이터 조회 중 오류 발생")

@router.post("/run", summary="분석 실행", description="이상탐지 분석을 즉시 실행합니다")
async def run_analysis(
    request: AnalysisRequest,
    current_user = Depends(require_role([RoleEnum.ADMIN, RoleEnum.OPERATOR]))
):
    """
    이상탐지 분석 즉시 실행

    접근 권한: admin, operator
    비동기 실행으로 빠른 응답
    """
    try:
        logger.info(f"이상탐지 분석 실행 요청: {request.dict()}")

        # 캐시 무효화 (force_refresh가 True인 경우)
        if request.force_refresh:
            cache_keys = [
                "anomaly_summary",
                "anomaly_timeseries_all_*",
                "anomaly_forecast_all_*"
            ]
            for key_pattern in cache_keys:
                # 실제로는 패턴 매칭으로 캐시 삭제해야 함
                pass

        # 분석 실행 (비동기)
        result_json = await run_anomaly_script(
            days=request.days,
            threshold=request.threshold,
            window=request.window_size,
            forecast=request.forecast_days,
            output_format="json"
        )

        if not result_json:
            raise HTTPException(status_code=503, detail="이상탐지 분석 실행 실패")

        analysis_data = parse_analysis_result(result_json)
        if not analysis_data:
            raise HTTPException(status_code=502, detail="분석 결과 파싱 실패")

        # 분석 완료 시간 캐시 업데이트
        await set_cache_data("anomaly_last_analysis", {
            "timestamp": datetime.now().isoformat(),
            "parameters": request.dict()
        }, ttl=3600)

        # 결과 요약 반환
        summary = analysis_data.get("summary", {})

        return JSONResponse({
            "status": "completed",
            "message": "이상탐지 분석이 성공적으로 완료되었습니다",
            "execution_time": datetime.now().isoformat(),
            "parameters": request.dict(),
            "results_preview": {
                "total_anomalies": summary.get("total_anomalies", 0),
                "high_risk_metrics": summary.get("high_risk_metrics", 0),
                "future_risk_periods": summary.get("total_future_risk_periods", 0)
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"분석 실행 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="분석 실행 중 오류 발생")

@router.get("/report.md", response_class=PlainTextResponse,
           summary="Markdown 리포트", description="최신 이상탐지 분석 결과를 Markdown 형식으로 반환합니다")
async def get_markdown_report(
    days: int = Query(30, ge=1, le=365, description="분석 기간 (일)"),
    current_user = Depends(require_role([RoleEnum.ADMIN, RoleEnum.OPERATOR]))
):
    """
    Markdown 형식 분석 리포트 조회

    접근 권한: admin, operator
    캐시: 10분
    """
    try:
        cache_key = f"anomaly_report_md_{days}"
        cached_report = await get_cached_data(cache_key)
        if cached_report:
            return PlainTextResponse(cached_report, media_type="text/markdown")

        logger.info(f"Markdown 리포트 생성: days={days}")

        # Markdown 형식으로 분석 실행
        result_md = await run_anomaly_script(days=days, output_format="markdown")
        if not result_md:
            raise HTTPException(status_code=503, detail="리포트 생성 실패")

        # 캐시에 10분간 저장
        await set_cache_data(cache_key, result_md, ttl=600)

        logger.info("Markdown 리포트 생성 완료")
        return PlainTextResponse(result_md, media_type="text/markdown")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Markdown 리포트 생성 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="리포트 생성 중 오류 발생")

# ================================================================
# 에러 핸들러 및 미들웨어 (한국어 주석 포함)
# ================================================================

@router.middleware("http")
async def add_korean_error_headers(request: Request, call_next):
    """
    한국어 에러 메시지 헤더 추가 미들웨어
    """
    response = await call_next(request)

    # 에러 응답에 한국어 설명 헤더 추가
    if response.status_code >= 400:
        error_messages = {
            400: "잘못된 요청입니다",
            401: "인증이 필요합니다",
            403: "접근 권한이 없습니다",
            404: "요청한 리소스를 찾을 수 없습니다",
            429: "요청 한도를 초과했습니다",
            500: "내부 서버 오류가 발생했습니다",
            502: "잘못된 게이트웨이 응답입니다",
            503: "서비스를 사용할 수 없습니다"
        }

        korean_message = error_messages.get(response.status_code, "알 수 없는 오류가 발생했습니다")
        response.headers["X-Error-Message-KR"] = korean_message

    return response

# ================================================================
# RCA 및 계절성 분해 엔드포인트 (새로 추가)
# ================================================================

class RCARequest(BaseModel):
    """원인분석 요청 모델"""
    target_metric: Optional[str] = Field(None, description="대상 지표명 (없으면 자동 선택)")
    anomaly_start: int = Field(..., ge=0, description="이상 구간 시작 인덱스")
    anomaly_end: int = Field(..., ge=0, description="이상 구간 종료 인덱스")
    baseline_start: int = Field(..., ge=0, description="기준 구간 시작 인덱스")
    baseline_end: int = Field(..., ge=0, description="기준 구간 종료 인덱스")
    metrics_data: Dict[str, List[float]] = Field(..., description="지표별 시계열 데이터")
    top_n: int = Field(5, ge=1, le=20, description="상위 N개 원인")

    @validator('anomaly_end')
    def validate_anomaly_window(cls, v, values):
        if 'anomaly_start' in values and v <= values['anomaly_start']:
            raise ValueError('이상 구간 종료는 시작보다 커야 합니다')
        return v

    @validator('baseline_end')
    def validate_baseline_window(cls, v, values):
        if 'baseline_start' in values and v <= values['baseline_start']:
            raise ValueError('기준 구간 종료는 시작보다 커야 합니다')
        return v

@router.post("/rca", summary="이상탐지 원인분석(RCA)")
async def run_root_cause_analysis(
    rca_request: RCARequest,
    current_user = Depends(require_role([RoleEnum.ADMIN, RoleEnum.OPERATOR]))
):
    """
    이상 구간에 대한 원인분석 수행

    접근 권한: admin, operator
    캐시: 5분
    """
    try:
        # 캐시 키 생성
        cache_key = f"rca_{hash(str(rca_request.dict()))}"
        cached_data = await get_cached_data(cache_key)
        if cached_data:
            return JSONResponse(cached_data)

        logger.info(f"원인분석 요청: 이상구간={rca_request.anomaly_start}-{rca_request.anomaly_end}")

        # RCA 분석 실행
        from .anomaly_rca import analyze_root_causes

        rca_result = analyze_root_causes(
            series_dict=rca_request.metrics_data,
            anomaly_window=(rca_request.anomaly_start, rca_request.anomaly_end),
            baseline_window=(rca_request.baseline_start, rca_request.baseline_end),
            target_metric=rca_request.target_metric,
            top_n=rca_request.top_n
        )

        response_data = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "analysis_results": rca_result,
            "request_params": {
                "anomaly_window": f"{rca_request.anomaly_start}-{rca_request.anomaly_end}",
                "baseline_window": f"{rca_request.baseline_start}-{rca_request.baseline_end}",
                "target_metric": rca_request.target_metric or "자동 선택",
                "top_n": rca_request.top_n
            }
        }

        # 5분 캐시
        await set_cache_data(cache_key, response_data, ttl=300)

        return JSONResponse(response_data)

    except Exception as e:
        logger.error(f"원인분석 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"원인분석 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/decompose", summary="시계열 계절성 분해")
async def decompose_timeseries(
    metric: str = Query(..., description="분해할 지표명"),
    days: int = Query(30, ge=14, le=365, description="분석 기간 (일)"),
    freq_hint: str = Query("D", regex="^(D|H|W)$", description="주기 힌트 (D=일간, H=시간, W=주간)"),
    current_user = Depends(require_role([RoleEnum.ADMIN, RoleEnum.OPERATOR]))
):
    """
    시계열 데이터의 계절성, 추세, 잔차 분해

    접근 권한: admin, operator
    캐시: 5분
    """
    try:
        cache_key = f"decompose_{metric}_{days}_{freq_hint}"
        cached_data = await get_cached_data(cache_key)
        if cached_data:
            return JSONResponse(cached_data)

        logger.info(f"계절성 분해 요청: metric={metric}, days={days}, freq={freq_hint}")

        # 분석 스크립트 실행하여 데이터 가져오기
        result_json = await run_anomaly_script(days=days, output_format="json")
        if not result_json:
            raise HTTPException(status_code=503, detail="데이터 수집 실패")

        analysis_data = parse_analysis_result(result_json)
        if not analysis_data:
            raise HTTPException(status_code=502, detail="분석 결과 파싱 실패")

        # 지표 데이터 추출
        metric_series = []
        timestamps = []

        # 상세 이상치 데이터에서 시계열 추출
        detailed_anomalies = analysis_data.get("detailed_anomalies", {})
        if metric in detailed_anomalies:
            anomaly_data = detailed_anomalies[metric]
            for item in anomaly_data:
                metric_series.append(item.get("value", 0))
                timestamps.append(item.get("timestamp", ""))

        if len(metric_series) < 14:
            raise HTTPException(status_code=400, detail=f"지표 '{metric}'의 데이터가 부족합니다 (최소 14개 필요, 현재 {len(metric_series)}개)")

        # 계절성 분해 실행
        from .anomaly_rca import decompose_seasonality

        decomp_result = decompose_seasonality(
            series=metric_series,
            timestamps=timestamps,
            freq_hint=freq_hint
        )

        response_data = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "metric_name": metric,
            "analysis_period_days": days,
            "frequency_hint": freq_hint,
            "decomposition": decomp_result,
            "data_points": len(metric_series)
        }

        # 5분 캐시
        await set_cache_data(cache_key, response_data, ttl=300)

        return JSONResponse(response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"계절성 분해 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"계절성 분해 중 오류가 발생했습니다: {str(e)}"
        )

# ================================================================
# 폴백 데이터 제공 함수들 (한국어 주석 포함)
# ================================================================

def get_fallback_summary() -> Dict[str, Any]:
    """
    분석 실패 시 사용할 폴백 요약 데이터

    Returns:
        Dict: 기본 요약 정보
    """
    return {
        "total_anomalies": 0,
        "high_risk_metrics": 0,
        "future_risk_periods": 0,
        "confidence_score": 0.0,
        "last_updated": datetime.now().isoformat(),
        "analysis_period_days": 30,
        "metrics_analyzed": 0,
        "status": "분석 데이터 없음 - 기본값 반환"
    }

def get_fallback_health() -> Dict[str, Any]:
    """
    헬스체크 실패 시 사용할 폴백 상태 데이터

    Returns:
        Dict: 기본 헬스 상태
    """
    return {
        "status": "unhealthy",
        "last_analysis_time": None,
        "data_sources_available": {
            "metrics_json": False,
            "log_files": False,
            "ci_reports": False
        },
        "cache_hit_rate": 0.0,
        "avg_response_time_ms": 0.0,
        "message": "데이터 소스를 사용할 수 없음"
    }

# ================================================================
# 모듈 초기화 (한국어 주석 포함)
# ================================================================

logger.info("🔎 이상탐지 API 모듈 로드 완료")
logger.info("엔드포인트: /api/v1/anomaly/* (admin, operator 권한 필요)")
logger.info("캐시 TTL: 요약 5분, 시계열 5분, 예측 10분, 리포트 10분")