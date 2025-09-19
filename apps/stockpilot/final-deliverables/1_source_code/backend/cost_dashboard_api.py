#!/usr/bin/env python3
"""
StockPilot 비용 대시보드 API 서버
실시간 비용 모니터링 및 제어를 위한 REST API
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import uvicorn
import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.cost_dashboard import (
    create_cost_tracker, track_openai_cost,
    CostMetric, BudgetRule, CostCategory, AlertLevel
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI 앱 초기화
app = FastAPI(
    title="StockPilot 비용 대시보드 API",
    description="실시간 비용 모니터링, 예산 관리 및 자동 제어를 위한 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 비용 추적기
cost_tracker = None

# Pydantic 모델들
class CostMetricRequest(BaseModel):
    """비용 메트릭 요청 모델"""
    category: str = Field(..., description="비용 카테고리 (openai_api, data_source, infrastructure, storage, bandwidth)")
    model: str = Field(..., description="모델명 (gpt-4, gpt-3.5-turbo, etc.)")
    channel: str = Field(..., description="채널명 (korean, english, premium, etc.)")
    country: str = Field(..., description="국가 코드 (KR, US, JP, etc.)")
    call_count: int = Field(1, description="API 호출 횟수")
    token_count: int = Field(0, description="토큰 사용량")
    cost_usd: float = Field(..., description="USD 비용")
    response_time_ms: int = Field(0, description="응답 시간 (밀리초)")
    user_id: Optional[str] = Field(None, description="사용자 ID")
    session_id: Optional[str] = Field(None, description="세션 ID")

class BudgetRuleRequest(BaseModel):
    """예산 규칙 요청 모델"""
    name: str = Field(..., description="규칙명")
    category: str = Field(..., description="비용 카테고리")
    model_filter: Optional[str] = Field(None, description="모델 필터")
    channel_filter: Optional[str] = Field(None, description="채널 필터")
    country_filter: Optional[str] = Field(None, description="국가 필터")
    daily_limit_usd: float = Field(100.0, description="일일 한도 (USD)")
    monthly_limit_usd: float = Field(3000.0, description="월별 한도 (USD)")
    alert_threshold_percent: float = Field(80.0, description="알림 임계치 (%)")
    auto_throttle_enabled: bool = Field(True, description="자동 스로틀링 활성화")
    emergency_stop_enabled: bool = Field(True, description="긴급 정지 활성화")

class ThrottleCheckRequest(BaseModel):
    """스로틀링 확인 요청 모델"""
    model: Optional[str] = Field(None, description="모델명")
    channel: Optional[str] = Field(None, description="채널명")
    country: Optional[str] = Field(None, description="국가 코드")

@app.on_event("startup")
async def startup_event():
    """앱 시작 시 초기화"""
    global cost_tracker
    try:
        cost_tracker = await create_cost_tracker()
        logger.info("비용 대시보드 API 서버 시작 완료")
    except Exception as e:
        logger.error(f"비용 추적기 초기화 실패: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """앱 종료 시 정리"""
    global cost_tracker
    if cost_tracker:
        try:
            await cost_tracker.__aexit__(None, None, None)
            logger.info("비용 추적기 종료 완료")
        except Exception as e:
            logger.error(f"비용 추적기 종료 오류: {e}")

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": "StockPilot 비용 대시보드 API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "dashboard": "/dashboard",
            "cost_track": "/cost/track",
            "budget_rules": "/budget/rules",
            "throttle_check": "/throttle/check",
            "alerts": "/alerts",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    try:
        # 비용 추적기 상태 확인
        if cost_tracker is None:
            return {"status": "unhealthy", "reason": "cost_tracker_not_initialized"}
        
        # Redis 연결 확인
        if cost_tracker.redis_client:
            await cost_tracker.redis_client.ping()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "cost_tracker": "healthy",
                "redis": "healthy",
                "database": "healthy"
            }
        }
    except Exception as e:
        logger.error(f"헬스 체크 실패: {e}")
        return {"status": "unhealthy", "error": str(e)}

@app.post("/cost/track")
async def track_cost(request: CostMetricRequest, background_tasks: BackgroundTasks):
    """비용 추적 엔드포인트"""
    try:
        global cost_tracker
        if cost_tracker is None:
            raise HTTPException(status_code=503, detail="비용 추적기가 초기화되지 않음")
        
        # CostMetric 객체 생성
        metric = CostMetric(
            timestamp=datetime.now(),
            category=CostCategory(request.category),
            model=request.model,
            channel=request.channel,
            country=request.country,
            call_count=request.call_count,
            token_count=request.token_count,
            cost_usd=request.cost_usd,
            response_time_ms=request.response_time_ms,
            user_id=request.user_id,
            session_id=request.session_id
        )
        
        # 백그라운드에서 비용 추적 실행
        def track_in_background():
            asyncio.create_task(cost_tracker.track_cost(metric))
        
        background_tasks.add_task(track_in_background)
        
        return {
            "status": "success",
            "message": "비용 추적 요청이 처리되었습니다",
            "metric_id": f"{metric.timestamp.strftime('%Y%m%d_%H%M%S')}_{id(metric)}",
            "timestamp": metric.timestamp.isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"잘못된 요청: {e}")
    except Exception as e:
        logger.error(f"비용 추적 오류: {e}")
        raise HTTPException(status_code=500, detail=f"내부 서버 오류: {e}")

@app.post("/cost/track/openai")
async def track_openai_cost_endpoint(
    model: str = Query(..., description="OpenAI 모델명"),
    channel: str = Query(..., description="채널명"),
    country: str = Query("KR", description="국가 코드"),
    call_count: int = Query(1, description="API 호출 횟수"),
    token_count: int = Query(..., description="토큰 사용량"),
    cost_usd: float = Query(..., description="USD 비용"),
    response_time_ms: int = Query(0, description="응답 시간"),
    user_id: Optional[str] = Query(None, description="사용자 ID"),
    session_id: Optional[str] = Query(None, description="세션 ID"),
    background_tasks: BackgroundTasks = None
):
    """OpenAI API 비용 추적 전용 엔드포인트"""
    try:
        # 백그라운드에서 비용 추적 실행
        def track_in_background():
            asyncio.create_task(track_openai_cost(
                model=model,
                channel=channel,
                country=country,
                call_count=call_count,
                token_count=token_count,
                cost_usd=cost_usd,
                response_time_ms=response_time_ms,
                user_id=user_id,
                session_id=session_id
            ))
        
        background_tasks.add_task(track_in_background)
        
        return {
            "status": "success",
            "message": "OpenAI API 비용 추적이 시작되었습니다",
            "model": model,
            "cost_usd": cost_usd,
            "token_count": token_count,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"OpenAI 비용 추적 오류: {e}")
        raise HTTPException(status_code=500, detail=f"내부 서버 오류: {e}")

@app.get("/dashboard")
async def get_dashboard_data(
    period: str = Query("hourly", description="데이터 주기 (hourly, daily)"),
    limit: int = Query(24, description="데이터 개수 제한")
):
    """비용 대시보드 데이터 조회"""
    try:
        global cost_tracker
        if cost_tracker is None:
            raise HTTPException(status_code=503, detail="비용 추적기가 초기화되지 않음")
        
        dashboard_data = await cost_tracker.get_cost_dashboard_data(period, limit)
        
        return {
            "status": "success",
            "data": dashboard_data,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"대시보드 데이터 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"내부 서버 오류: {e}")

@app.get("/dashboard/stream")
async def stream_dashboard_data():
    """실시간 대시보드 데이터 스트리밍 (Server-Sent Events)"""
    async def generate_data():
        try:
            while True:
                global cost_tracker
                if cost_tracker is not None:
                    dashboard_data = await cost_tracker.get_cost_dashboard_data()
                    
                    # SSE 형식으로 데이터 전송
                    yield f"data: {json.dumps(dashboard_data, ensure_ascii=False)}\n\n"
                
                # 5초마다 업데이트
                await asyncio.sleep(5)
                
        except asyncio.CancelledError:
            logger.info("대시보드 스트리밍 연결 종료")
        except Exception as e:
            logger.error(f"대시보드 스트리밍 오류: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_data(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

@app.get("/throttle/check")
async def check_throttle_status(
    model: Optional[str] = Query(None, description="모델명"),
    channel: Optional[str] = Query(None, description="채널명"),
    country: Optional[str] = Query(None, description="국가 코드")
):
    """스로틀링 상태 확인"""
    try:
        global cost_tracker
        if cost_tracker is None:
            raise HTTPException(status_code=503, detail="비용 추적기가 초기화되지 않음")
        
        is_throttled, reason = await cost_tracker.is_throttled(model, channel, country)
        
        return {
            "status": "success",
            "is_throttled": is_throttled,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
            "request": {
                "model": model,
                "channel": channel,
                "country": country
            }
        }
        
    except Exception as e:
        logger.error(f"스로틀링 상태 확인 오류: {e}")
        raise HTTPException(status_code=500, detail=f"내부 서버 오류: {e}")

@app.post("/throttle/check")
async def check_throttle_status_post(request: ThrottleCheckRequest):
    """스로틀링 상태 확인 (POST)"""
    try:
        global cost_tracker
        if cost_tracker is None:
            raise HTTPException(status_code=503, detail="비용 추적기가 초기화되지 않음")
        
        is_throttled, reason = await cost_tracker.is_throttled(
            request.model, request.channel, request.country
        )
        
        return {
            "status": "success",
            "is_throttled": is_throttled,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
            "request": request.dict()
        }
        
    except Exception as e:
        logger.error(f"스로틀링 상태 확인 오류: {e}")
        raise HTTPException(status_code=500, detail=f"내부 서버 오류: {e}")

@app.get("/budget/rules")
async def get_budget_rules():
    """예산 규칙 목록 조회"""
    try:
        global cost_tracker
        if cost_tracker is None:
            raise HTTPException(status_code=503, detail="비용 추적기가 초기화되지 않음")
        
        rules = {}
        for name, rule in cost_tracker.budget_rules.items():
            rules[name] = {
                "name": rule.name,
                "category": rule.category.value,
                "model_filter": rule.model_filter,
                "channel_filter": rule.channel_filter,
                "country_filter": rule.country_filter,
                "daily_limit_usd": rule.daily_limit_usd,
                "monthly_limit_usd": rule.monthly_limit_usd,
                "alert_threshold_percent": rule.alert_threshold_percent,
                "auto_throttle_enabled": rule.auto_throttle_enabled,
                "emergency_stop_enabled": rule.emergency_stop_enabled
            }
        
        return {
            "status": "success",
            "rules": rules,
            "total_rules": len(rules),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"예산 규칙 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"내부 서버 오류: {e}")

@app.post("/budget/rules")
async def create_budget_rule(request: BudgetRuleRequest):
    """새 예산 규칙 생성"""
    try:
        global cost_tracker
        if cost_tracker is None:
            raise HTTPException(status_code=503, detail="비용 추적기가 초기화되지 않음")
        
        # BudgetRule 객체 생성
        new_rule = BudgetRule(
            name=request.name,
            category=CostCategory(request.category),
            model_filter=request.model_filter,
            channel_filter=request.channel_filter,
            country_filter=request.country_filter,
            daily_limit_usd=request.daily_limit_usd,
            monthly_limit_usd=request.monthly_limit_usd,
            alert_threshold_percent=request.alert_threshold_percent,
            auto_throttle_enabled=request.auto_throttle_enabled,
            emergency_stop_enabled=request.emergency_stop_enabled
        )
        
        # 규칙 추가
        cost_tracker.budget_rules[request.name] = new_rule
        
        return {
            "status": "success",
            "message": f"예산 규칙 '{request.name}'이 생성되었습니다",
            "rule": request.dict(),
            "timestamp": datetime.now().isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"잘못된 요청: {e}")
    except Exception as e:
        logger.error(f"예산 규칙 생성 오류: {e}")
        raise HTTPException(status_code=500, detail=f"내부 서버 오류: {e}")

@app.delete("/budget/rules/{rule_name}")
async def delete_budget_rule(rule_name: str):
    """예산 규칙 삭제"""
    try:
        global cost_tracker
        if cost_tracker is None:
            raise HTTPException(status_code=503, detail="비용 추적기가 초기화되지 않음")
        
        if rule_name not in cost_tracker.budget_rules:
            raise HTTPException(status_code=404, detail=f"예산 규칙 '{rule_name}'을 찾을 수 없음")
        
        del cost_tracker.budget_rules[rule_name]
        
        return {
            "status": "success",
            "message": f"예산 규칙 '{rule_name}'이 삭제되었습니다",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"예산 규칙 삭제 오류: {e}")
        raise HTTPException(status_code=500, detail=f"내부 서버 오류: {e}")

@app.get("/alerts")
async def get_alerts(
    level: Optional[str] = Query(None, description="알림 레벨 필터 (info, warning, critical, emergency)"),
    limit: int = Query(50, description="최대 알림 개수")
):
    """비용 알림 목록 조회"""
    try:
        global cost_tracker
        if cost_tracker is None:
            raise HTTPException(status_code=503, detail="비용 추적기가 초기화되지 않음")
        
        alerts = await cost_tracker._get_active_alerts()
        
        # 레벨 필터 적용
        if level:
            alerts = [alert for alert in alerts if alert["level"] == level]
        
        # 개수 제한 적용
        alerts = alerts[:limit]
        
        return {
            "status": "success",
            "alerts": alerts,
            "total_alerts": len(alerts),
            "filter": {"level": level, "limit": limit},
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"알림 목록 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"내부 서버 오류: {e}")

@app.get("/stats/summary")
async def get_cost_summary():
    """비용 요약 통계"""
    try:
        global cost_tracker
        if cost_tracker is None:
            raise HTTPException(status_code=503, detail="비용 추적기가 초기화되지 않음")
        
        summary = await cost_tracker._get_cost_summary()
        
        return {
            "status": "success",
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"비용 요약 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"내부 서버 오류: {e}")

@app.get("/stats/trends")
async def get_cost_trends(
    period: str = Query("hourly", description="트렌드 주기 (hourly, daily)"),
    limit: int = Query(24, description="데이터 포인트 개수")
):
    """비용 트렌드 데이터"""
    try:
        global cost_tracker
        if cost_tracker is None:
            raise HTTPException(status_code=503, detail="비용 추적기가 초기화되지 않음")
        
        trends = await cost_tracker._get_cost_trends(period, limit)
        
        return {
            "status": "success",
            "trends": trends,
            "period": period,
            "limit": limit,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"비용 트렌드 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"내부 서버 오류: {e}")

@app.get("/stats/breakdown")
async def get_cost_breakdown():
    """비용 세부 분석"""
    try:
        global cost_tracker
        if cost_tracker is None:
            raise HTTPException(status_code=503, detail="비용 추적기가 초기화되지 않음")
        
        breakdown = await cost_tracker._get_cost_breakdown()
        
        return {
            "status": "success",
            "breakdown": breakdown,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"비용 분석 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"내부 서버 오류: {e}")

@app.post("/throttle/override/{rule_name}")
async def override_throttle(rule_name: str, override_duration_hours: int = Query(1, description="해제 지속 시간(시간)")):
    """스로틀링 수동 해제"""
    try:
        global cost_tracker
        if cost_tracker is None:
            raise HTTPException(status_code=503, detail="비용 추적기가 초기화되지 않음")
        
        if rule_name not in cost_tracker.budget_rules:
            raise HTTPException(status_code=404, detail=f"예산 규칙 '{rule_name}'을 찾을 수 없음")
        
        # Redis에서 스로틀링/긴급정지 해제
        throttle_key = f"throttle:{rule_name}"
        stop_key = f"emergency_stop:{rule_name}"
        
        await cost_tracker.redis_client.delete(throttle_key)
        await cost_tracker.redis_client.delete(stop_key)
        
        # 메모리에서도 해제
        if rule_name in cost_tracker.active_throttles:
            del cost_tracker.active_throttles[rule_name]
        
        # 임시 해제 상태 설정
        override_key = f"override:{rule_name}"
        override_data = {
            "overridden_at": datetime.now().isoformat(),
            "duration_hours": override_duration_hours,
            "expires_at": (datetime.now() + timedelta(hours=override_duration_hours)).isoformat()
        }
        
        await cost_tracker.redis_client.hset(override_key, mapping=override_data)
        await cost_tracker.redis_client.expire(override_key, override_duration_hours * 3600)
        
        return {
            "status": "success",
            "message": f"스로틀링이 {override_duration_hours}시간 동안 해제되었습니다",
            "rule_name": rule_name,
            "expires_at": override_data["expires_at"],
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"스로틀링 해제 오류: {e}")
        raise HTTPException(status_code=500, detail=f"내부 서버 오류: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="StockPilot 비용 대시보드 API 서버")
    parser.add_argument("--host", default="0.0.0.0", help="서버 호스트")
    parser.add_argument("--port", type=int, default=8004, help="서버 포트")
    parser.add_argument("--reload", action="store_true", help="개발 모드 (자동 재로드)")
    parser.add_argument("--log-level", default="info", help="로그 레벨")
    
    args = parser.parse_args()
    
    logger.info(f"🔧 StockPilot 비용 대시보드 API 서버 시작 - {args.host}:{args.port}")
    
    uvicorn.run(
        "cost_dashboard_api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
        access_log=True
    )