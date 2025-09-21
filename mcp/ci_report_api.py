#!/usr/bin/env python3
"""
CI/CD 성능 리포트 API
CI 빌드 결과, 테스트 통계, 성능 메트릭 정보 제공
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse

# 로거 설정
logger = logging.getLogger(__name__)

# FastAPI 라우터 생성
router = APIRouter(
    prefix="/api/v1/ci",
    tags=["ci-reports"],
    responses={404: {"description": "Not found"}}
)

# CI 리포트 디렉토리 경로
REPORTS_DIR = Path(__file__).parent.parent / "reports" / "ci_reports"


class CIReportManager:
    """CI 리포트 관리 클래스"""

    def __init__(self):
        self.reports_dir = REPORTS_DIR
        self._ensure_reports_dir()

    def _ensure_reports_dir(self):
        """리포트 디렉토리 생성 확인"""
        try:
            self.reports_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"CI 리포트 디렉토리 확인: {self.reports_dir}")
        except Exception as e:
            logger.error(f"리포트 디렉토리 생성 실패: {e}")

    def _load_report_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """단일 리포트 파일 로드"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 오류 - {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"파일 로드 오류 - {file_path}: {e}")
            return None

    def get_all_reports(self, limit: int = 50) -> List[Dict[str, Any]]:
        """모든 CI 리포트 조회"""
        try:
            reports = []

            # JSON 파일들을 날짜순으로 정렬
            json_files = sorted(
                self.reports_dir.glob("*.json"),
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )

            for file_path in json_files[:limit]:
                report = self._load_report_file(file_path)
                if report:
                    report['file_name'] = file_path.name
                    reports.append(report)

            logger.info(f"총 {len(reports)}개의 CI 리포트 로드됨")
            return reports

        except Exception as e:
            logger.error(f"리포트 조회 오류: {e}")
            return []

    def get_latest_report(self) -> Optional[Dict[str, Any]]:
        """최신 CI 리포트 조회"""
        try:
            reports = self.get_all_reports(limit=1)
            return reports[0] if reports else None
        except Exception as e:
            logger.error(f"최신 리포트 조회 오류: {e}")
            return None

    def get_failed_reports(self, days: int = 7) -> List[Dict[str, Any]]:
        """실패한 빌드 리포트 조회"""
        try:
            all_reports = self.get_all_reports()
            cutoff_date = datetime.now() - timedelta(days=days)

            failed_reports = []
            for report in all_reports:
                try:
                    report_date = datetime.fromisoformat(report.get('timestamp', '').replace('Z', '+00:00'))
                    if report.get('status') == 'failed' and report_date >= cutoff_date:
                        failed_reports.append(report)
                except ValueError:
                    continue

            logger.info(f"지난 {days}일 동안 {len(failed_reports)}개의 실패한 빌드 발견")
            return failed_reports

        except Exception as e:
            logger.error(f"실패 리포트 조회 오류: {e}")
            return []

    def get_performance_stats(self, days: int = 30) -> Dict[str, Any]:
        """CI 성능 통계 계산"""
        try:
            all_reports = self.get_all_reports()
            cutoff_date = datetime.now() - timedelta(days=days)

            recent_reports = []
            for report in all_reports:
                try:
                    report_date = datetime.fromisoformat(report.get('timestamp', '').replace('Z', '+00:00'))
                    if report_date >= cutoff_date:
                        recent_reports.append(report)
                except ValueError:
                    continue

            if not recent_reports:
                return self._empty_stats()

            total_builds = len(recent_reports)
            successful_builds = len([r for r in recent_reports if r.get('status') == 'success'])
            failed_builds = total_builds - successful_builds

            # 평균 실행 시간 계산
            execution_times = [r.get('execution_time', 0) for r in recent_reports if r.get('execution_time')]
            avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0

            # 평균 테스트 커버리지 계산
            coverages = [r.get('coverage', {}).get('percentage', 0) for r in recent_reports]
            avg_coverage = sum(coverages) / len(coverages) if coverages else 0

            # 최근 실행 날짜
            latest_timestamp = max([r.get('timestamp', '') for r in recent_reports]) if recent_reports else ''

            return {
                'period_days': days,
                'total_builds': total_builds,
                'successful_builds': successful_builds,
                'failed_builds': failed_builds,
                'success_rate': round((successful_builds / total_builds) * 100, 1) if total_builds > 0 else 0,
                'failure_rate': round((failed_builds / total_builds) * 100, 1) if total_builds > 0 else 0,
                'avg_execution_time': round(avg_execution_time, 1),
                'avg_coverage': round(avg_coverage, 1),
                'latest_execution': latest_timestamp,
                'calculated_at': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"성능 통계 계산 오류: {e}")
            return self._empty_stats()

    def _empty_stats(self) -> Dict[str, Any]:
        """빈 통계 반환"""
        return {
            'period_days': 30,
            'total_builds': 0,
            'successful_builds': 0,
            'failed_builds': 0,
            'success_rate': 0,
            'failure_rate': 0,
            'avg_execution_time': 0,
            'avg_coverage': 0,
            'latest_execution': '',
            'calculated_at': datetime.now().isoformat()
        }

    def get_failed_tests_summary(self, days: int = 7) -> List[Dict[str, Any]]:
        """실패한 테스트 요약"""
        try:
            failed_reports = self.get_failed_reports(days)

            test_failures = {}
            for report in failed_reports:
                failed_tests = report.get('failed_tests', [])
                for test in failed_tests:
                    test_name = test.get('name', 'unknown')
                    if test_name not in test_failures:
                        test_failures[test_name] = {
                            'name': test_name,
                            'count': 0,
                            'latest_error': '',
                            'file': test.get('file', ''),
                            'builds': []
                        }

                    test_failures[test_name]['count'] += 1
                    test_failures[test_name]['latest_error'] = test.get('error', '')
                    test_failures[test_name]['builds'].append(report.get('id', ''))

            # 실패 횟수순으로 정렬
            sorted_failures = sorted(
                test_failures.values(),
                key=lambda x: x['count'],
                reverse=True
            )

            logger.info(f"지난 {days}일 동안 {len(sorted_failures)}개의 고유 테스트 실패 발견")
            return sorted_failures

        except Exception as e:
            logger.error(f"실패 테스트 요약 오류: {e}")
            return []

    def report_to_markdown(self, report: Dict[str, Any]) -> str:
        """리포트를 마크다운 형식으로 변환"""
        try:
            md_content = f"""# CI/CD 빌드 리포트 - {report.get('id', 'Unknown')}

## 📊 기본 정보
- **빌드 ID**: {report.get('id', 'N/A')}
- **날짜**: {report.get('date', 'N/A')}
- **상태**: {'✅ 성공' if report.get('status') == 'success' else '❌ 실패'}
- **실행 시간**: {report.get('execution_time', 0)}초
- **브랜치**: {report.get('build_info', {}).get('branch', 'N/A')}
- **커밋**: {report.get('build_info', {}).get('commit', 'N/A')}

## 🧪 테스트 결과
- **전체 테스트**: {report.get('test_results', {}).get('total', 0)}개
- **성공**: {report.get('test_results', {}).get('passed', 0)}개
- **실패**: {report.get('test_results', {}).get('failed', 0)}개
- **스킵**: {report.get('test_results', {}).get('skipped', 0)}개

## 📈 커버리지
- **커버리지**: {report.get('coverage', {}).get('percentage', 0)}%
- **커버된 라인**: {report.get('coverage', {}).get('lines_covered', 0)}줄
- **전체 라인**: {report.get('coverage', {}).get('lines_total', 0)}줄

"""

            # 스테이지 정보 추가
            stages = report.get('stages', [])
            if stages:
                md_content += "## ⚙️ 빌드 스테이지\n"
                for stage in stages:
                    status_emoji = '✅' if stage.get('status') == 'success' else '❌'
                    md_content += f"- **{stage.get('name')}**: {status_emoji} ({stage.get('duration', 0)}초)\n"
                md_content += "\n"

            # 실패한 테스트 정보 추가
            failed_tests = report.get('failed_tests', [])
            if failed_tests:
                md_content += "## ❌ 실패한 테스트\n"
                for test in failed_tests:
                    md_content += f"### {test.get('name', 'Unknown')}\n"
                    md_content += f"- **파일**: {test.get('file', 'N/A')}\n"
                    md_content += f"- **라인**: {test.get('line', 'N/A')}\n"
                    md_content += f"- **오류**: {test.get('error', 'N/A')}\n\n"

            return md_content

        except Exception as e:
            logger.error(f"마크다운 변환 오류: {e}")
            return f"# 리포트 변환 오류\n\n{str(e)}"


# CI 리포트 매니저 인스턴스
ci_manager = CIReportManager()


@router.get("/reports")
async def get_ci_reports(
    limit: int = Query(50, description="조회할 리포트 수", ge=1, le=100),
    status: Optional[str] = Query(None, description="상태 필터 (success/failed)")
) -> List[Dict[str, Any]]:
    """
    CI 리포트 목록 조회

    Args:
        limit: 조회할 리포트 수 (기본: 50, 최대: 100)
        status: 상태 필터 (success/failed)

    Returns:
        List[Dict]: CI 리포트 목록
    """
    try:
        reports = ci_manager.get_all_reports(limit=limit)

        # 상태 필터 적용
        if status:
            reports = [r for r in reports if r.get('status') == status]

        return reports
    except Exception as e:
        logger.error(f"CI 리포트 조회 API 오류: {e}")
        raise HTTPException(status_code=500, detail="CI 리포트 조회 실패")


@router.get("/reports/latest")
async def get_latest_ci_report() -> Dict[str, Any]:
    """최신 CI 리포트 조회"""
    try:
        report = ci_manager.get_latest_report()
        if not report:
            raise HTTPException(status_code=404, detail="CI 리포트를 찾을 수 없습니다")
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"최신 CI 리포트 조회 API 오류: {e}")
        raise HTTPException(status_code=500, detail="최신 CI 리포트 조회 실패")


@router.get("/reports/failed")
async def get_failed_ci_reports(
    days: int = Query(7, description="조회 기간 (일)", ge=1, le=90)
) -> List[Dict[str, Any]]:
    """실패한 CI 빌드 리포트 조회"""
    try:
        reports = ci_manager.get_failed_reports(days=days)
        return reports
    except Exception as e:
        logger.error(f"실패 CI 리포트 조회 API 오류: {e}")
        raise HTTPException(status_code=500, detail="실패 CI 리포트 조회 실패")


@router.get("/stats")
async def get_ci_performance_stats(
    days: int = Query(30, description="통계 기간 (일)", ge=1, le=365)
) -> Dict[str, Any]:
    """CI 성능 통계 조회"""
    try:
        stats = ci_manager.get_performance_stats(days=days)
        return stats
    except Exception as e:
        logger.error(f"CI 통계 조회 API 오류: {e}")
        raise HTTPException(status_code=500, detail="CI 통계 조회 실패")


@router.get("/failed-tests")
async def get_failed_tests_summary(
    days: int = Query(7, description="조회 기간 (일)", ge=1, le=90)
) -> List[Dict[str, Any]]:
    """실패한 테스트 요약 조회"""
    try:
        summary = ci_manager.get_failed_tests_summary(days=days)
        return summary
    except Exception as e:
        logger.error(f"실패 테스트 요약 API 오류: {e}")
        raise HTTPException(status_code=500, detail="실패 테스트 요약 조회 실패")


@router.get("/reports/{report_id}")
async def get_ci_report_by_id(report_id: str) -> Dict[str, Any]:
    """특정 CI 리포트 조회"""
    try:
        all_reports = ci_manager.get_all_reports()

        # 리포트 ID로 검색
        for report in all_reports:
            if report.get('id') == report_id:
                return report

        raise HTTPException(status_code=404, detail=f"리포트 ID '{report_id}'를 찾을 수 없습니다")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CI 리포트 상세 조회 API 오류: {e}")
        raise HTTPException(status_code=500, detail="CI 리포트 상세 조회 실패")


@router.get("/reports/{report_id}/markdown")
async def get_ci_report_markdown(report_id: str) -> PlainTextResponse:
    """CI 리포트를 마크다운 형식으로 조회"""
    try:
        all_reports = ci_manager.get_all_reports()

        # 리포트 ID로 검색
        for report in all_reports:
            if report.get('id') == report_id:
                markdown_content = ci_manager.report_to_markdown(report)
                return PlainTextResponse(
                    content=markdown_content,
                    media_type="text/markdown; charset=utf-8"
                )

        raise HTTPException(status_code=404, detail=f"리포트 ID '{report_id}'를 찾을 수 없습니다")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CI 리포트 마크다운 조회 API 오류: {e}")
        raise HTTPException(status_code=500, detail="CI 리포트 마크다운 조회 실패")


@router.get("/health")
async def get_ci_api_health() -> Dict[str, Any]:
    """CI API 상태 확인"""
    try:
        # 리포트 디렉토리 확인
        reports_exist = ci_manager.reports_dir.exists()
        report_count = len(list(ci_manager.reports_dir.glob("*.json"))) if reports_exist else 0

        # 최신 리포트 확인
        latest_report = ci_manager.get_latest_report()

        return {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'message': 'CI 리포트 API가 정상 작동 중입니다',
            'details': {
                'reports_directory': str(ci_manager.reports_dir),
                'reports_directory_exists': reports_exist,
                'total_reports': report_count,
                'latest_report_id': latest_report.get('id') if latest_report else None,
                'latest_report_status': latest_report.get('status') if latest_report else None
            }
        }
    except Exception as e:
        logger.error(f"CI API 헬스체크 오류: {e}")
        raise HTTPException(status_code=503, detail=f"CI 리포트 서비스 이용 불가: {str(e)}")


def get_ci_router() -> APIRouter:
    """CI 리포트 라우터 반환"""
    return router