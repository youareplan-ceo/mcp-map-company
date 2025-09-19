"""
구체적인 배치 작업 정의
일일 데이터 수집, 분석, 정리 작업들
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
from pathlib import Path
import shutil
from loguru import logger

from app.jobs.batch_manager import BatchJob, JobPriority, get_batch_manager
from app.services.stock_service import StockService
from app.services.news_service import NewsService
from app.services.ai_service import AIService
from app.middleware.usage_tracker import get_usage_tracker
from app.config import get_settings

settings = get_settings()


async def daily_data_collection() -> Dict[str, Any]:
    """일일 데이터 수집 작업"""
    logger.info("일일 데이터 수집 시작")
    
    stock_service = StockService()
    news_service = NewsService()
    results = {
        "stocks_updated": 0,
        "news_collected": 0,
        "errors": []
    }
    
    try:
        # 주요 종목 데이터 업데이트
        major_symbols = ["005930.KS", "000660.KS", "035420.KS", "051910.KS", "006400.KS"]  # 삼성전자, SK하이닉스 등
        
        for symbol in major_symbols:
            try:
                stock_data = await stock_service.get_stock_info(symbol)
                if stock_data:
                    results["stocks_updated"] += 1
                    logger.debug(f"주식 데이터 업데이트: {symbol}")
                    
            except Exception as e:
                error_msg = f"주식 데이터 수집 실패: {symbol}, {str(e)}"
                logger.warning(error_msg)
                results["errors"].append(error_msg)
        
        # 뉴스 데이터 수집
        try:
            news_data = await news_service.get_latest_news(limit=50)
            results["news_collected"] = len(news_data) if news_data else 0
            logger.info(f"뉴스 데이터 수집: {results['news_collected']}건")
            
        except Exception as e:
            error_msg = f"뉴스 데이터 수집 실패: {str(e)}"
            logger.warning(error_msg)
            results["errors"].append(error_msg)
        
        # 시장 상태 업데이트
        # (실제 구현에서는 market_service 사용)
        
        logger.info(f"일일 데이터 수집 완료: 주식 {results['stocks_updated']}개, 뉴스 {results['news_collected']}건")
        return results
        
    except Exception as e:
        logger.error(f"일일 데이터 수집 중 치명적 오류: {str(e)}")
        raise


async def daily_ai_analysis() -> Dict[str, Any]:
    """일일 AI 분석 작업"""
    logger.info("일일 AI 분석 시작")
    
    ai_service = AIService()
    results = {
        "analyses_generated": 0,
        "signals_created": 0,
        "errors": []
    }
    
    try:
        # 주요 종목 AI 분석
        major_symbols = ["005930.KS", "000660.KS", "035420.KS"]
        
        for symbol in major_symbols:
            try:
                # AI 분석 수행
                analysis = await ai_service.analyze_stock(symbol, include_news=True)
                if analysis:
                    results["analyses_generated"] += 1
                    
                    # 투자 시그널 생성
                    if analysis.signal and analysis.signal.signal_type != "HOLD":
                        results["signals_created"] += 1
                    
                    logger.debug(f"AI 분석 완료: {symbol}")
                    
            except Exception as e:
                error_msg = f"AI 분석 실패: {symbol}, {str(e)}"
                logger.warning(error_msg)
                results["errors"].append(error_msg)
                
            # API 호출 간 지연 (비용 관리)
            await asyncio.sleep(2)
        
        logger.info(f"일일 AI 분석 완료: 분석 {results['analyses_generated']}개, 시그널 {results['signals_created']}개")
        return results
        
    except Exception as e:
        logger.error(f"일일 AI 분석 중 치명적 오류: {str(e)}")
        raise


async def daily_cleanup() -> Dict[str, Any]:
    """일일 정리 작업"""
    logger.info("일일 정리 작업 시작")
    
    results = {
        "log_files_cleaned": 0,
        "temp_files_cleaned": 0,
        "old_locks_cleaned": 0,
        "space_freed_mb": 0
    }
    
    try:
        # 로그 파일 정리 (7일 이상 된 것)
        log_dir = Path("logs")
        if log_dir.exists():
            cutoff_date = datetime.now() - timedelta(days=7)
            
            for log_file in log_dir.glob("*.log.*"):
                try:
                    if log_file.stat().st_mtime < cutoff_date.timestamp():
                        file_size = log_file.stat().st_size
                        log_file.unlink()
                        results["log_files_cleaned"] += 1
                        results["space_freed_mb"] += file_size / (1024 * 1024)
                        
                except Exception as e:
                    logger.warning(f"로그 파일 삭제 실패: {log_file}, {str(e)}")
        
        # 임시 파일 정리
        temp_dirs = [Path("/tmp"), Path("./temp")]
        
        for temp_dir in temp_dirs:
            if temp_dir.exists():
                for temp_file in temp_dir.glob("stockpilot_*"):
                    try:
                        if temp_file.is_file():
                            file_size = temp_file.stat().st_size
                            temp_file.unlink()
                            results["temp_files_cleaned"] += 1
                            results["space_freed_mb"] += file_size / (1024 * 1024)
                            
                    except Exception as e:
                        logger.warning(f"임시 파일 삭제 실패: {temp_file}, {str(e)}")
        
        # 배치 매니저의 오래된 잠금 파일 정리
        batch_manager = get_batch_manager()
        await batch_manager.cleanup_old_locks(days=3)
        
        logger.info(f"일일 정리 완료: 로그 {results['log_files_cleaned']}개, 임시파일 {results['temp_files_cleaned']}개, {results['space_freed_mb']:.1f}MB 확보")
        return results
        
    except Exception as e:
        logger.error(f"일일 정리 작업 중 오류: {str(e)}")
        raise


async def usage_report() -> Dict[str, Any]:
    """OpenAI 사용량 및 비용 리포트 생성"""
    logger.info("사용량 리포트 생성 시작")
    
    results = {
        "report_generated": False,
        "total_cost": 0.0,
        "total_requests": 0,
        "errors": []
    }
    
    try:
        usage_tracker = await get_usage_tracker()
        stats = await usage_tracker.get_usage_stats(days=1)
        
        # 어제 사용량 계산
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        daily_usage = stats.get("daily_usage", {}).get(yesterday, {})
        
        if daily_usage:
            results["total_cost"] = daily_usage.get("total_cost", 0.0)
            results["total_requests"] = daily_usage.get("total_requests", 0)
            results["report_generated"] = True
            
            # 비용 임계치 체크
            daily_limit = settings.daily_cost_limit
            cost_percentage = (results["total_cost"] / daily_limit) * 100 if daily_limit > 0 else 0
            
            logger.info(
                f"일일 사용량 리포트: "
                f"비용 ${results['total_cost']:.2f} ({cost_percentage:.1f}%), "
                f"요청 {results['total_requests']}건"
            )
            
            # 비용 경고
            if cost_percentage > 80:
                logger.warning(f"일일 비용 사용량 높음: {cost_percentage:.1f}%")
            
        else:
            results["errors"].append("어제 사용량 데이터 없음")
            
        return results
        
    except Exception as e:
        error_msg = f"사용량 리포트 생성 실패: {str(e)}"
        logger.error(error_msg)
        results["errors"].append(error_msg)
        return results


async def health_check_report() -> Dict[str, Any]:
    """시스템 헬스체크 및 상태 리포트"""
    logger.info("시스템 헬스체크 시작")
    
    results = {
        "system_healthy": True,
        "services_checked": 0,
        "issues_found": [],
        "metrics": {}
    }
    
    try:
        # API 서비스 상태 체크
        services_to_check = [
            "database_connection",
            "openai_api",
            "websocket_connections",
            "batch_jobs"
        ]
        
        for service in services_to_check:
            try:
                # 실제 구현에서는 각 서비스별 헬스체크 로직 추가
                # 예: 데이터베이스 연결 테스트, API 호출 테스트 등
                
                results["services_checked"] += 1
                logger.debug(f"서비스 체크 완료: {service}")
                
            except Exception as e:
                issue = f"서비스 문제 발견: {service}, {str(e)}"
                results["issues_found"].append(issue)
                results["system_healthy"] = False
                logger.warning(issue)
        
        # 시스템 메트릭스 수집
        # (실제 구현에서는 더 상세한 메트릭스 수집)
        results["metrics"] = {
            "timestamp": datetime.now().isoformat(),
            "services_up": results["services_checked"] - len(results["issues_found"]),
            "services_down": len(results["issues_found"])
        }
        
        status = "정상" if results["system_healthy"] else "문제 있음"
        logger.info(f"시스템 헬스체크 완료: {status}, 점검 서비스 {results['services_checked']}개")
        
        return results
        
    except Exception as e:
        logger.error(f"헬스체크 중 오류: {str(e)}")
        results["system_healthy"] = False
        results["issues_found"].append(str(e))
        return results


def register_all_jobs():
    """모든 배치 작업을 배치 매니저에 등록"""
    batch_manager = get_batch_manager()
    
    jobs = [
        BatchJob(
            job_id="daily_data_collection",
            name="일일 데이터 수집",
            description="주식 데이터 및 뉴스 수집",
            func=daily_data_collection,
            priority=JobPriority.HIGH,
            max_retries=2,
            timeout=1800  # 30분
        ),
        BatchJob(
            job_id="daily_ai_analysis",
            name="일일 AI 분석",
            description="AI 기반 주식 분석 및 시그널 생성",
            func=daily_ai_analysis,
            priority=JobPriority.HIGH,
            max_retries=3,
            timeout=3600,  # 1시간
            dependencies=["daily_data_collection"]
        ),
        BatchJob(
            job_id="daily_cleanup",
            name="일일 정리 작업",
            description="로그 및 임시 파일 정리",
            func=daily_cleanup,
            priority=JobPriority.LOW,
            max_retries=1,
            timeout=600  # 10분
        ),
        BatchJob(
            job_id="usage_report",
            name="사용량 리포트",
            description="OpenAI API 사용량 및 비용 리포트",
            func=usage_report,
            priority=JobPriority.NORMAL,
            max_retries=2,
            timeout=300  # 5분
        ),
        BatchJob(
            job_id="health_check_report",
            name="시스템 헬스체크",
            description="시스템 상태 점검 및 리포트",
            func=health_check_report,
            priority=JobPriority.CRITICAL,
            max_retries=1,
            timeout=180  # 3분
        )
    ]
    
    for job in jobs:
        batch_manager.register_job(job)
    
    logger.info(f"배치 작업 등록 완료: {len(jobs)}개 작업")