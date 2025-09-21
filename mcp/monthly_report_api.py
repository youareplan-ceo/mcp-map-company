#!/usr/bin/env python3
"""
월간 운영 리포트 API 모듈
Monthly Operations Report API Module

이 모듈은 월간 운영 리포트 생성, 조회, 다운로드를 위한 FastAPI 엔드포인트를 제공합니다.
This module provides FastAPI endpoints for monthly operations report generation, retrieval, and download.
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse
from typing import Optional, Dict, List, Any
import subprocess
import json
import os
import glob
from pathlib import Path
from datetime import datetime, timedelta
import asyncio
import logging

# 로깅 설정 (Korean comments)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 라우터 생성 (월간 리포트 전용)
router = APIRouter(
    prefix="/api/v1/reports/monthly",
    tags=["monthly-reports"],
    responses={404: {"description": "리포트를 찾을 수 없습니다"}}
)

# 프로젝트 루트 경로 (상대 경로로 스크립트 위치 계산)
PROJECT_ROOT = Path(__file__).parent.parent
MONTHLY_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "monthly_ops_report.sh"
REPORTS_DIR = PROJECT_ROOT / "reports" / "monthly"

# 월간 리포트 생성 상태 추적 (백그라운드 작업용)
report_generation_status = {
    "is_running": False,
    "last_run": None,
    "last_error": None
}


@router.get("/", response_model=Dict[str, Any])
async def get_monthly_reports_summary():
    """
    월간 리포트 목록 및 요약 정보 반환
    Returns monthly reports list and summary information

    Returns:
        Dict containing recent reports, latest performance data, and system status
    """
    try:
        # 리포트 디렉토리 생성 (존재하지 않을 경우)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        # 최근 6개월 리포트 파일 검색
        report_files = []
        markdown_files = glob.glob(str(REPORTS_DIR / "monthly-report-*.md"))
        json_files = glob.glob(str(REPORTS_DIR / "monthly-report-*.json"))

        # 파일 정보 수집 및 정렬 (최신순)
        for md_file in sorted(markdown_files, reverse=True)[:6]:
            base_name = Path(md_file).stem
            json_file = str(REPORTS_DIR / f"{base_name}.json")

            file_info = {
                "date": base_name.replace("monthly-report-", ""),
                "markdown_file": md_file,
                "json_file": json_file if os.path.exists(json_file) else None,
                "created_at": datetime.fromtimestamp(os.path.getctime(md_file)).isoformat(),
                "size_mb": round(os.path.getsize(md_file) / (1024 * 1024), 2)
            }
            report_files.append(file_info)

        # 최신 리포트에서 성과 데이터 추출 (JSON 파일이 있는 경우)
        latest_performance = None
        if report_files and report_files[0]["json_file"] and os.path.exists(report_files[0]["json_file"]):
            try:
                with open(report_files[0]["json_file"], 'r', encoding='utf-8') as f:
                    latest_data = json.load(f)
                    if 'performance_score' in latest_data:
                        latest_performance = latest_data['performance_score']
            except Exception as e:
                logger.warning(f"최신 성과 데이터 로드 실패: {e}")

        return {
            "status": "success",
            "reports_count": len(report_files),
            "latest_reports": report_files,
            "latest_performance": latest_performance,
            "generation_status": report_generation_status,
            "script_available": MONTHLY_SCRIPT_PATH.exists(),
            "reports_directory": str(REPORTS_DIR)
        }

    except Exception as e:
        logger.error(f"월간 리포트 요약 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"리포트 요약 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/latest", response_model=Dict[str, Any])
async def get_latest_monthly_report():
    """
    최신 월간 리포트 데이터 반환 (JSON 형식)
    Returns the latest monthly report data in JSON format

    Returns:
        Dict containing the latest monthly report data
    """
    try:
        # 최신 JSON 리포트 파일 찾기
        json_files = glob.glob(str(REPORTS_DIR / "monthly-report-*.json"))

        if not json_files:
            raise HTTPException(
                status_code=404,
                detail="월간 리포트를 찾을 수 없습니다. 먼저 리포트를 생성해주세요."
            )

        # 최신 파일 선택 (파일명 기준 정렬)
        latest_file = max(json_files, key=lambda x: os.path.getctime(x))

        # JSON 파일 읽기
        with open(latest_file, 'r', encoding='utf-8') as f:
            report_data = json.load(f)

        # 메타데이터 추가
        file_stats = os.stat(latest_file)
        report_data["file_info"] = {
            "file_path": latest_file,
            "created_at": datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
            "size_bytes": file_stats.st_size
        }

        return report_data

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="최신 월간 리포트 파일을 찾을 수 없습니다.")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"리포트 파일 파싱 오류: {str(e)}")
    except Exception as e:
        logger.error(f"최신 월간 리포트 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"리포트 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/performance-trend", response_model=Dict[str, Any])
async def get_performance_trend(months: int = Query(6, ge=1, le=12)):
    """
    월별 성과 추이 데이터 반환 (차트용)
    Returns monthly performance trend data for charts

    Args:
        months: 조회할 개월 수 (기본값: 6개월, 최대 12개월)

    Returns:
        Dict containing performance trend data for the specified number of months
    """
    try:
        # 지정된 개월 수만큼 JSON 파일 검색
        json_files = glob.glob(str(REPORTS_DIR / "monthly-report-*.json"))

        if not json_files:
            return {
                "status": "no_data",
                "message": "월간 리포트 데이터가 없습니다.",
                "trend_data": [],
                "summary": {}
            }

        # 파일을 날짜 순으로 정렬 (최신순)
        sorted_files = sorted(json_files, reverse=True)[:months]

        trend_data = []
        total_scores = []
        security_scores = []
        backup_scores = []
        system_scores = []
        grades = {"우수": 0, "보통": 0, "개선 필요": 0}

        for file_path in sorted_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 성과 점수 추출
                performance = data.get('performance_score', {})
                metadata = data.get('report_metadata', {})

                month_data = {
                    "period": metadata.get('period_end', ''),
                    "total_score": performance.get('total_score', 0),
                    "security_score": performance.get('security_score', 0),
                    "backup_score": performance.get('backup_score', 0),
                    "system_score": performance.get('system_score', 0),
                    "grade": performance.get('grade', '알 수 없음')
                }

                trend_data.append(month_data)

                # 통계 계산용 데이터 수집
                total_scores.append(month_data["total_score"])
                security_scores.append(month_data["security_score"])
                backup_scores.append(month_data["backup_score"])
                system_scores.append(month_data["system_score"])

                grade = month_data["grade"]
                if grade in grades:
                    grades[grade] += 1

            except Exception as e:
                logger.warning(f"파일 처리 중 오류 ({file_path}): {e}")
                continue

        # 데이터를 시간순으로 정렬 (오래된 것부터)
        trend_data.reverse()

        # 요약 통계 계산
        summary = {}
        if total_scores:
            summary = {
                "average_total_score": round(sum(total_scores) / len(total_scores), 1),
                "average_security_score": round(sum(security_scores) / len(security_scores), 1),
                "average_backup_score": round(sum(backup_scores) / len(backup_scores), 1),
                "average_system_score": round(sum(system_scores) / len(system_scores), 1),
                "grade_distribution": grades,
                "data_points": len(trend_data)
            }

        return {
            "status": "success",
            "trend_data": trend_data,
            "summary": summary,
            "period_months": months
        }

    except Exception as e:
        logger.error(f"성과 추이 데이터 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"성과 추이 조회 중 오류가 발생했습니다: {str(e)}")


@router.post("/generate")
async def generate_monthly_report(
    background_tasks: BackgroundTasks,
    period: Optional[str] = Query(None, description="리포트 기간 (예: 2024-09)")
):
    """
    새로운 월간 리포트 생성 (백그라운드 작업)
    Generates a new monthly report as a background task

    Args:
        period: 선택적 리포트 기간 (예: "2024-09")

    Returns:
        Dict containing generation status and estimated completion time
    """
    try:
        # 이미 생성 중인지 확인
        if report_generation_status["is_running"]:
            raise HTTPException(
                status_code=429,
                detail="이미 월간 리포트 생성이 진행 중입니다. 잠시 후 다시 시도해주세요."
            )

        # 스크립트 파일 존재 확인
        if not MONTHLY_SCRIPT_PATH.exists():
            raise HTTPException(
                status_code=404,
                detail=f"월간 리포트 스크립트를 찾을 수 없습니다: {MONTHLY_SCRIPT_PATH}"
            )

        # 백그라운드 작업으로 리포트 생성 시작
        background_tasks.add_task(run_monthly_report_generation, period)

        # 상태 업데이트
        report_generation_status["is_running"] = True
        report_generation_status["last_error"] = None

        return {
            "status": "started",
            "message": "월간 리포트 생성이 시작되었습니다.",
            "estimated_duration": "5-10분",
            "period": period or "최근 30일",
            "check_status_url": "/api/v1/reports/monthly/status"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"월간 리포트 생성 시작 오류: {e}")
        raise HTTPException(status_code=500, detail=f"리포트 생성 시작 중 오류가 발생했습니다: {str(e)}")


@router.get("/status")
async def get_generation_status():
    """
    월간 리포트 생성 상태 확인
    Returns monthly report generation status

    Returns:
        Dict containing current generation status and progress information
    """
    return {
        "status": "running" if report_generation_status["is_running"] else "idle",
        "is_running": report_generation_status["is_running"],
        "last_run": report_generation_status["last_run"],
        "last_error": report_generation_status["last_error"],
        "script_path": str(MONTHLY_SCRIPT_PATH),
        "reports_directory": str(REPORTS_DIR)
    }


@router.get("/download/{report_date}")
async def download_monthly_report(
    report_date: str,
    format: str = Query("markdown", regex="^(markdown|json)$")
):
    """
    특정 날짜의 월간 리포트 다운로드
    Downloads monthly report for a specific date

    Args:
        report_date: 리포트 날짜 (YYYY-MM-DD 형식)
        format: 다운로드 형식 ("markdown" 또는 "json")

    Returns:
        File response with the requested report
    """
    try:
        # 파일 확장자 결정
        file_ext = "md" if format == "markdown" else "json"
        file_path = REPORTS_DIR / f"monthly-report-{report_date}.{file_ext}"

        # 파일 존재 확인
        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"{report_date} 날짜의 {format} 리포트를 찾을 수 없습니다."
            )

        # 파일 내용 읽기
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 응답 형식 결정
        if format == "json":
            # JSON 형식 유효성 검사
            try:
                json_data = json.loads(content)
                return JSONResponse(content=json_data)
            except json.JSONDecodeError:
                raise HTTPException(status_code=500, detail="JSON 파일이 손상되었습니다.")
        else:
            # Markdown 형식
            return PlainTextResponse(
                content=content,
                headers={
                    "Content-Disposition": f"attachment; filename=monthly-report-{report_date}.md"
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"월간 리포트 다운로드 오류: {e}")
        raise HTTPException(status_code=500, detail=f"리포트 다운로드 중 오류가 발생했습니다: {str(e)}")


async def run_monthly_report_generation(period: Optional[str] = None):
    """
    월간 리포트 생성 백그라운드 작업
    Background task for monthly report generation

    Args:
        period: 선택적 리포트 기간
    """
    try:
        # 리포트 디렉토리 생성
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        # 스크립트 실행 인수 준비
        script_args = [str(MONTHLY_SCRIPT_PATH), "--json"]
        if period:
            script_args.extend(["--period", period])

        logger.info(f"월간 리포트 생성 시작: {' '.join(script_args)}")

        # 스크립트 실행 (10분 타임아웃)
        result = subprocess.run(
            script_args,
            capture_output=True,
            text=True,
            timeout=600,  # 10분
            cwd=str(PROJECT_ROOT)
        )

        # 실행 결과 처리
        if result.returncode == 0:
            logger.info("월간 리포트 생성 완료")
            report_generation_status["last_run"] = datetime.now().isoformat()
            report_generation_status["last_error"] = None
        else:
            error_msg = f"스크립트 실행 실패 (코드: {result.returncode}): {result.stderr}"
            logger.error(error_msg)
            report_generation_status["last_error"] = error_msg

    except subprocess.TimeoutExpired:
        error_msg = "월간 리포트 생성 타임아웃 (10분)"
        logger.error(error_msg)
        report_generation_status["last_error"] = error_msg

    except Exception as e:
        error_msg = f"월간 리포트 생성 중 예외 발생: {str(e)}"
        logger.error(error_msg)
        report_generation_status["last_error"] = error_msg

    finally:
        # 실행 상태 초기화
        report_generation_status["is_running"] = False


@router.get("/test")
async def test_monthly_report_system():
    """
    월간 리포트 시스템 테스트 엔드포인트
    Test endpoint for monthly report system

    Returns:
        Dict containing system test results
    """
    test_results = {
        "script_exists": MONTHLY_SCRIPT_PATH.exists(),
        "script_executable": MONTHLY_SCRIPT_PATH.exists() and os.access(MONTHLY_SCRIPT_PATH, os.X_OK),
        "reports_dir_exists": REPORTS_DIR.exists(),
        "reports_dir_writable": REPORTS_DIR.exists() and os.access(REPORTS_DIR, os.W_OK),
        "existing_reports": len(glob.glob(str(REPORTS_DIR / "monthly-report-*.json"))),
        "project_root": str(PROJECT_ROOT),
        "current_status": report_generation_status
    }

    # 전체 시스템 상태 결정
    system_ready = all([
        test_results["script_exists"],
        test_results["script_executable"],
        test_results["reports_dir_exists"] or True,  # 디렉토리는 생성 가능
        test_results["reports_dir_writable"] or True
    ])

    return {
        "status": "ready" if system_ready else "not_ready",
        "system_ready": system_ready,
        "test_results": test_results,
        "recommendations": [
            "스크립트 실행 권한 확인" if not test_results["script_executable"] else None,
            "리포트 디렉토리 권한 확인" if not test_results["reports_dir_writable"] else None,
            "첫 번째 리포트 생성" if test_results["existing_reports"] == 0 else None
        ]
    }