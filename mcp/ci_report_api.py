#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CI/CD 성능 리포트 API (한국어 주석 포함)

기능:
1. scripts/ci_reporter.sh 실행 후 결과 반환
2. 최근 10회 CI 실행 결과 JSON 제공
3. 성능 요약 및 실패 테스트 필터링
4. JSON/Markdown 출력 형식 지원
"""

import os
import subprocess
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse, PlainTextResponse
import logging

# 로거 설정
logger = logging.getLogger(__name__)

# FastAPI Router 생성 (prefix=/api/v1/reports/ci)
router = APIRouter(
    prefix="/api/v1/reports/ci",
    tags=["ci-reports"],
    responses={
        404: {"description": "CI 리포트를 찾을 수 없음"},
        500: {"description": "서버 내부 오류"}
    }
)

# 프로젝트 루트 디렉토리 경로
PROJECT_ROOT = Path(__file__).parent.parent


class CIReportService:
    """CI/CD 성능 리포트 서비스 클래스"""

    def __init__(self):
        self.ci_reporter_script = PROJECT_ROOT / "scripts" / "ci_reporter.sh"
        self.cache_timeout = 300  # 5분 캐시
        self.last_cache_time = None
        self.cached_data = None

    async def execute_ci_reporter(self, format_type: str = "json", **kwargs) -> Dict[str, Any]:
        """
        scripts/ci_reporter.sh 실행 및 결과 반환

        Args:
            format_type: 출력 형식 ("json", "markdown")
            **kwargs: 추가 스크립트 옵션

        Returns:
            Dict[str, Any]: CI 리포트 데이터

        Raises:
            HTTPException: 스크립트 실행 실패 시
        """
        try:
            # 스크립트 파일 존재 확인
            if not self.ci_reporter_script.exists():
                logger.error(f"CI reporter 스크립트를 찾을 수 없음: {self.ci_reporter_script}")
                return self.get_fallback_data()

            # 스크립트 명령어 구성
            cmd = [str(self.ci_reporter_script)]

            if format_type == "json":
                cmd.append("--json")
            elif format_type == "markdown":
                cmd.append("--md")

            # 추가 옵션 처리
            if kwargs.get("runs"):
                cmd.extend(["--runs", str(kwargs["runs"])])
            if kwargs.get("days"):
                cmd.extend(["--days", str(kwargs["days"])])
            if kwargs.get("verbose"):
                cmd.append("--verbose")

            logger.info(f"CI reporter 스크립트 실행: {' '.join(cmd)}")

            # 스크립트 실행 (비동기)
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=PROJECT_ROOT
            )

            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)  # 5분 타임아웃

            if process.returncode != 0:
                error_msg = stderr.decode('utf-8') if stderr else "알 수 없는 오류"
                logger.error(f"CI reporter 스크립트 실행 실패 (코드: {process.returncode}): {error_msg}")

                # 폴백 데이터 반환
                return self.get_fallback_data()

            # 결과 파싱
            output = stdout.decode('utf-8')

            if format_type == "json":
                try:
                    return json.loads(output)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON 파싱 실패: {e}")
                    return self.get_fallback_data()
            else:
                return {"content": output, "format": "markdown"}

        except asyncio.TimeoutError:
            logger.error("CI reporter 스크립트 실행 시간 초과")
            return self.get_fallback_data()
        except Exception as e:
            logger.error(f"CI reporter 스크립트 실행 중 오류: {e}")
            return self.get_fallback_data()

    def get_fallback_data(self) -> Dict[str, Any]:
        """
        API 오류 시 사용할 폴백 데이터 생성

        Returns:
            Dict[str, Any]: 모의 CI 리포트 데이터
        """
        current_time = datetime.now()

        return {
            "report_metadata": {
                "generated_at": current_time.strftime('%Y-%m-%d %H:%M:%S'),
                "report_date": current_time.strftime('%Y%m%d'),
                "analysis_period_days": 7,
                "workflow_count": 15,
                "fallback_mode": True
            },
            "performance_summary": {
                "total_runs": 15,
                "success_count": 12,
                "failure_count": 2,
                "cancelled_count": 1,
                "success_rate": 80.0,
                "failure_rate": 13.3,
                "avg_duration_seconds": 420.5
            },
            "recent_workflows": [
                {
                    "id": "123456789",
                    "name": "CI Pipeline",
                    "status": "completed",
                    "conclusion": "success",
                    "branch": "main",
                    "created_at": (current_time - timedelta(hours=2)).isoformat(),
                    "updated_at": (current_time - timedelta(hours=2) + timedelta(minutes=7)).isoformat(),
                    "duration_seconds": 420,
                    "html_url": "https://github.com/youareplan/mcp-map-company/actions",
                    "run_number": 125
                },
                {
                    "id": "123456788",
                    "name": "Security Scan",
                    "status": "completed",
                    "conclusion": "failure",
                    "branch": "develop",
                    "created_at": (current_time - timedelta(hours=4)).isoformat(),
                    "updated_at": (current_time - timedelta(hours=4) + timedelta(minutes=5)).isoformat(),
                    "duration_seconds": 300,
                    "html_url": "https://github.com/youareplan/mcp-map-company/actions",
                    "run_number": 124
                },
                {
                    "id": "123456787",
                    "name": "Build & Test",
                    "status": "completed",
                    "conclusion": "success",
                    "branch": "main",
                    "created_at": (current_time - timedelta(hours=6)).isoformat(),
                    "updated_at": (current_time - timedelta(hours=6) + timedelta(minutes=8)).isoformat(),
                    "duration_seconds": 480,
                    "html_url": "https://github.com/youareplan/mcp-map-company/actions",
                    "run_number": 123
                }
            ],
            "failed_tests": [],
            "performance_issues": [
                "장시간 실행: 1개 워크플로우가 30분 이상 실행"
            ]
        }

    async def get_cached_or_fresh_data(self, **kwargs) -> Dict[str, Any]:
        """
        캐시된 데이터 반환 또는 새로운 데이터 가져오기

        Returns:
            Dict[str, Any]: CI 리포트 데이터
        """
        current_time = datetime.now()

        # 캐시 유효성 검사
        if (self.cached_data is None or
            self.last_cache_time is None or
            (current_time - self.last_cache_time).total_seconds() > self.cache_timeout):

            logger.info("CI 리포트 데이터 새로고침 중...")
            self.cached_data = await self.execute_ci_reporter("json", **kwargs)
            self.last_cache_time = current_time

        return self.cached_data


# 서비스 인스턴스 생성
ci_report_service = CIReportService()


@router.get("/summary", summary="CI/CD 성능 요약 조회")
async def get_ci_summary(
    runs: Optional[int] = 20,
    days: Optional[int] = 7
) -> JSONResponse:
    """
    CI/CD 성능 요약 데이터 조회

    Args:
        runs: 분석할 워크플로우 수 (기본값: 20)
        days: 분석 기간 일수 (기본값: 7)

    Returns:
        JSONResponse: CI 성능 요약 데이터
    """
    try:
        logger.info(f"CI 성능 요약 조회 요청 - runs: {runs}, days: {days}")

        data = await ci_report_service.get_cached_or_fresh_data(
            runs=runs,
            days=days
        )

        return JSONResponse(content=data)

    except Exception as e:
        logger.error(f"CI 성능 요약 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"성능 요약 조회 실패: {str(e)}")


@router.get("/recent", summary="최근 CI 실행 결과 조회")
async def get_recent_ci_runs(
    limit: Optional[int] = 10
) -> JSONResponse:
    """
    최근 10회 CI 실행 결과 조회

    Args:
        limit: 조회할 실행 결과 수 (기본값: 10)

    Returns:
        JSONResponse: 최근 CI 실행 결과 목록
    """
    try:
        logger.info(f"최근 CI 실행 결과 조회 요청 - limit: {limit}")

        data = await ci_report_service.get_cached_or_fresh_data(runs=limit)

        # 최근 워크플로우만 필터링
        recent_workflows = data.get("recent_workflows", [])[:limit]

        response_data = {
            "workflows": recent_workflows,
            "total_count": len(recent_workflows),
            "summary": data.get("performance_summary", {}),
            "generated_at": data.get("report_metadata", {}).get("generated_at")
        }

        return JSONResponse(content=response_data)

    except Exception as e:
        logger.error(f"최근 CI 실행 결과 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"실행 결과 조회 실패: {str(e)}")


@router.get("/failures", summary="실패한 테스트 필터링 조회")
async def get_failed_tests(
    days: Optional[int] = 7
) -> JSONResponse:
    """
    실패한 테스트만 필터링하여 조회

    Args:
        days: 분석 기간 일수 (기본값: 7)

    Returns:
        JSONResponse: 실패한 테스트 목록
    """
    try:
        logger.info(f"실패한 테스트 조회 요청 - days: {days}")

        data = await ci_report_service.get_cached_or_fresh_data(days=days)

        # 실패한 워크플로우만 필터링
        all_workflows = data.get("recent_workflows", [])
        failed_workflows = [w for w in all_workflows if w.get("conclusion") == "failure"]

        response_data = {
            "failed_workflows": failed_workflows,
            "failure_count": len(failed_workflows),
            "total_workflows": len(all_workflows),
            "failure_rate": (len(failed_workflows) / len(all_workflows) * 100) if all_workflows else 0,
            "failed_tests": data.get("failed_tests", []),
            "performance_issues": data.get("performance_issues", []),
            "generated_at": data.get("report_metadata", {}).get("generated_at")
        }

        return JSONResponse(content=response_data)

    except Exception as e:
        logger.error(f"실패한 테스트 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"실패 테스트 조회 실패: {str(e)}")


@router.get("/json", summary="CI 리포트 JSON 다운로드")
async def download_ci_report_json(
    runs: Optional[int] = 20,
    days: Optional[int] = 7
) -> JSONResponse:
    """
    CI 리포트 전체 JSON 데이터 다운로드

    Args:
        runs: 분석할 워크플로우 수 (기본값: 20)
        days: 분석 기간 일수 (기본값: 7)

    Returns:
        JSONResponse: 전체 CI 리포트 JSON 데이터
    """
    try:
        logger.info(f"CI 리포트 JSON 다운로드 요청 - runs: {runs}, days: {days}")

        data = await ci_report_service.execute_ci_reporter(
            "json",
            runs=runs,
            days=days
        )

        return JSONResponse(
            content=data,
            headers={"Content-Disposition": f"attachment; filename=ci_report_{datetime.now().strftime('%Y%m%d')}.json"}
        )

    except Exception as e:
        logger.error(f"CI 리포트 JSON 다운로드 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"JSON 리포트 생성 실패: {str(e)}")


@router.get("/markdown", summary="CI 리포트 Markdown 다운로드")
async def download_ci_report_markdown(
    runs: Optional[int] = 20,
    days: Optional[int] = 7
) -> PlainTextResponse:
    """
    CI 리포트 Markdown 형식 다운로드

    Args:
        runs: 분석할 워크플로우 수 (기본값: 20)
        days: 분석 기간 일수 (기본값: 7)

    Returns:
        PlainTextResponse: Markdown 형식의 CI 리포트
    """
    try:
        logger.info(f"CI 리포트 Markdown 다운로드 요청 - runs: {runs}, days: {days}")

        data = await ci_report_service.execute_ci_reporter(
            "markdown",
            runs=runs,
            days=days
        )

        content = data.get("content", "")
        if not content:
            # JSON 데이터에서 Markdown 생성
            json_data = await ci_report_service.execute_ci_reporter("json", runs=runs, days=days)
            content = generate_markdown_from_json(json_data)

        return PlainTextResponse(
            content=content,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename=ci_report_{datetime.now().strftime('%Y%m%d')}.md"}
        )

    except Exception as e:
        logger.error(f"CI 리포트 Markdown 다운로드 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"Markdown 리포트 생성 실패: {str(e)}")


@router.post("/refresh", summary="CI 리포트 캐시 새로고침")
async def refresh_ci_reports() -> JSONResponse:
    """
    CI 리포트 캐시 강제 새로고침

    Returns:
        JSONResponse: 새로고침 결과
    """
    try:
        logger.info("CI 리포트 캐시 강제 새로고침 요청")

        # 캐시 초기화
        ci_report_service.cached_data = None
        ci_report_service.last_cache_time = None

        # 새로운 데이터 로드
        data = await ci_report_service.get_cached_or_fresh_data()

        return JSONResponse(content={
            "message": "CI 리포트 캐시가 성공적으로 새로고침되었습니다",
            "refreshed_at": datetime.now().isoformat(),
            "data_summary": {
                "total_runs": data.get("performance_summary", {}).get("total_runs", 0),
                "success_rate": data.get("performance_summary", {}).get("success_rate", 0),
                "failure_rate": data.get("performance_summary", {}).get("failure_rate", 0)
            }
        })

    except Exception as e:
        logger.error(f"CI 리포트 캐시 새로고침 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"캐시 새로고침 실패: {str(e)}")


def generate_markdown_from_json(data: Dict[str, Any]) -> str:
    """
    JSON 데이터에서 Markdown 리포트 생성

    Args:
        data: CI 리포트 JSON 데이터

    Returns:
        str: Markdown 형식의 리포트
    """
    metadata = data.get("report_metadata", {})
    summary = data.get("performance_summary", {})
    workflows = data.get("recent_workflows", [])
    issues = data.get("performance_issues", [])

    md_content = f"""# 📊 CI/CD 성능 리포트

**생성 일시:** {metadata.get('generated_at', 'N/A')}
**분석 기간:** 최근 {metadata.get('analysis_period_days', 7)}일
**분석 워크플로우:** {metadata.get('workflow_count', 0)}개

## 📈 성능 요약

| 지표 | 값 | 비율 |
|------|-----|------|
| 총 실행 | {summary.get('total_runs', 0)}개 | 100% |
| ✅ 성공 | {summary.get('success_count', 0)}개 | {summary.get('success_rate', 0):.1f}% |
| ❌ 실패 | {summary.get('failure_count', 0)}개 | {summary.get('failure_rate', 0):.1f}% |
| ⏹️ 취소 | {summary.get('cancelled_count', 0)}개 | {((summary.get('cancelled_count', 0) * 100) / summary.get('total_runs', 1)):.1f}% |
| ⏱️ 평균 실행 시간 | {(summary.get('avg_duration_seconds', 0) / 60):.1f}분 | - |

## 🚨 성능 이슈

"""

    if issues:
        for issue in issues:
            md_content += f"- {issue}\n"
    else:
        md_content += "✅ 감지된 성능 이슈가 없습니다.\n"

    md_content += "\n## 📋 최근 워크플로우 실행 이력\n\n"
    md_content += "| 워크플로우 | 상태 | 브랜치 | 실행 시간 | 소요 시간 |\n"
    md_content += "|------------|------|---------|-----------|----------|\n"

    for workflow in workflows[:10]:  # 최근 10개만
        name = workflow.get('name', 'N/A')
        run_number = workflow.get('run_number', 'N/A')
        conclusion = workflow.get('conclusion', 'unknown')
        branch = workflow.get('branch', 'N/A')
        created_at = workflow.get('created_at', 'N/A')
        duration = workflow.get('duration_seconds', 0)

        status_icon = "✅" if conclusion == "success" else "❌" if conclusion == "failure" else "⏹️" if conclusion == "cancelled" else "⚪"
        duration_min = f"{duration // 60}분" if duration else "N/A"
        date_str = created_at.split('T')[0] if 'T' in created_at else created_at

        md_content += f"| {name} (#{run_number}) | {status_icon} {conclusion} | `{branch}` | {date_str} | {duration_min} |\n"

    md_content += f"""

---

📁 **리포트 생성:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔗 **GitHub Actions:** https://github.com/youareplan/mcp-map-company/actions

*이 리포트는 자동으로 생성되었습니다.*
"""

    return md_content


# 헬스체크 엔드포인트
@router.get("/health", summary="CI 리포트 API 헬스체크")
async def health_check() -> JSONResponse:
    """
    CI 리포트 API 상태 확인

    Returns:
        JSONResponse: API 상태 정보
    """
    try:
        script_exists = ci_report_service.ci_reporter_script.exists()

        return JSONResponse(content={
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "ci_reporter_script": {
                "path": str(ci_report_service.ci_reporter_script),
                "exists": script_exists,
                "executable": os.access(ci_report_service.ci_reporter_script, os.X_OK) if script_exists else False
            },
            "cache": {
                "has_data": ci_report_service.cached_data is not None,
                "last_update": ci_report_service.last_cache_time.isoformat() if ci_report_service.last_cache_time else None
            }
        })

    except Exception as e:
        logger.error(f"헬스체크 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"헬스체크 실패: {str(e)}")