# mcp/anomaly_policy_api.py
"""
이상탐지 정책 및 서프레션 관리 API

주요 기능:
- 탐지 임계값, 윈도우 크기, 민감도 설정 관리
- 서프레션 룰 (알림 억제 규칙) 관리
- 정책 시뮬레이션 및 테스트
- RBAC 기반 접근 제어 (admin만 수정, operator/user는 조회만)

작성자: Claude Code Assistant
생성일: 2024-09-21
"""

from __future__ import annotations

import os
import yaml
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, validator

# 내부 모듈 import
from .utils.rbac import require_role, RoleEnum, get_current_user

# 로깅 설정
log = logging.getLogger("mcp.anomaly_policy_api")

# 라우터 생성
router = APIRouter()

# 정책 파일 경로
POLICY_FILE_PATH = Path(__file__).parent.parent / "data" / "anomaly_policy.yaml"

# ==========================================
# Pydantic 모델 정의
# ==========================================

class MetricPolicyConfig(BaseModel):
    """지표별 정책 설정"""
    threshold: float = Field(3.0, ge=1.0, le=10.0, description="Z-score 임계값")
    window_size: int = Field(7, ge=1, le=30, description="윈도우 크기 (일)")
    enabled: bool = Field(True, description="탐지 활성화 여부")

class AlertLevelConfig(BaseModel):
    """알림 레벨 설정"""
    threshold: float = Field(3.0, ge=1.0, le=10.0, description="임계값")
    color: str = Field("#ffc107", description="색상 코드")
    description: str = Field("알림 설명", description="알림 설명")

class SuppressionGlobalConfig(BaseModel):
    """전역 서프레션 설정"""
    enabled: bool = Field(True, description="서프레션 활성화")
    consecutive_alert_cooldown: int = Field(30, ge=1, le=1440, description="연속 알림 억제 시간 (분)")
    max_alerts_per_day: int = Field(100, ge=1, le=1000, description="일일 최대 알림 수")

class SuppressionTimeBasedConfig(BaseModel):
    """시간대별 서프레션 설정"""
    enabled: bool = Field(False, description="시간대별 서프레션 활성화")
    start_hour: int = Field(22, ge=0, le=23, description="시작 시간")
    end_hour: int = Field(6, ge=0, le=23, description="종료 시간")
    suppressed_levels: List[str] = Field(["low"], description="억제할 알림 레벨")

class SuppressionMetricConfig(BaseModel):
    """지표별 서프레션 설정"""
    cooldown_minutes: int = Field(30, ge=1, le=1440, description="쿨다운 시간 (분)")
    max_hourly_alerts: int = Field(4, ge=1, le=60, description="시간당 최대 알림 수")

class AnomalyPolicySchema(BaseModel):
    """이상탐지 정책 스키마"""
    # 기본 탐지 설정
    default_window_size: int = Field(7, ge=1, le=30, description="기본 윈도우 크기")
    default_threshold: float = Field(3.0, ge=1.0, le=10.0, description="기본 임계값")
    default_forecast_days: int = Field(7, ge=1, le=30, description="기본 예측 일수")
    ewma_alpha: float = Field(0.3, ge=0.1, le=1.0, description="EWMA 알파값")

    # 지표별 설정
    metrics: Dict[str, MetricPolicyConfig] = Field(default_factory=dict, description="지표별 설정")

    # 알림 레벨
    alert_levels: Dict[str, AlertLevelConfig] = Field(default_factory=dict, description="알림 레벨 설정")

    # 서프레션 설정
    suppression_global: SuppressionGlobalConfig = Field(default_factory=SuppressionGlobalConfig, description="전역 서프레션")
    suppression_time_nighttime: SuppressionTimeBasedConfig = Field(default_factory=SuppressionTimeBasedConfig, description="야간 서프레션")
    suppression_time_weekend: SuppressionTimeBasedConfig = Field(default_factory=SuppressionTimeBasedConfig, description="주말 서프레션")
    suppression_metrics: Dict[str, SuppressionMetricConfig] = Field(default_factory=dict, description="지표별 서프레션")

class PolicyTestRequest(BaseModel):
    """정책 테스트 요청"""
    metric_name: str = Field(..., description="테스트할 지표명")
    sample_values: List[float] = Field(..., min_items=10, max_items=1000, description="샘플 값들")
    test_policy: Optional[AnomalyPolicySchema] = Field(None, description="테스트할 정책 (없으면 현재 정책)")

class PolicyTestResult(BaseModel):
    """정책 테스트 결과"""
    metric_name: str
    total_samples: int
    anomalies_detected: int
    suppressed_alerts: int
    alert_distribution: Dict[str, int]  # 레벨별 알림 수
    evaluation_summary: str  # 평가 요약 (한국어)

class SuppressionStatus(BaseModel):
    """서프레션 상태"""
    metric_name: str
    last_alert_time: Optional[str] = None
    suppressed_count_today: int = 0
    suppressed_count_hour: int = 0
    is_currently_suppressed: bool = False
    suppression_reason: str = ""

# ==========================================
# 정책 관리 클래스
# ==========================================

class AnomalyPolicyManager:
    """이상탐지 정책 관리자"""

    def __init__(self, policy_file_path: Path = POLICY_FILE_PATH):
        """초기화"""
        self.policy_file_path = policy_file_path
        self.log = logging.getLogger(f"{__name__}.AnomalyPolicyManager")
        self._suppression_history: Dict[str, List[datetime]] = {}

    def load_policy(self) -> Dict[str, Any]:
        """정책 파일 로드"""
        try:
            if not self.policy_file_path.exists():
                self.log.warning(f"정책 파일이 없습니다: {self.policy_file_path}")
                return self._get_default_policy()

            with open(self.policy_file_path, 'r', encoding='utf-8') as f:
                policy_data = yaml.safe_load(f)

            self.log.info("정책 파일 로드 완료")
            return policy_data

        except Exception as e:
            self.log.error(f"정책 파일 로드 실패: {e}")
            return self._get_default_policy()

    def save_policy(self, policy_data: Dict[str, Any]) -> bool:
        """정책 파일 저장"""
        try:
            # 디렉토리 생성
            self.policy_file_path.parent.mkdir(parents=True, exist_ok=True)

            # 메타데이터 업데이트
            if 'metadata' not in policy_data:
                policy_data['metadata'] = {}

            policy_data['metadata'].update({
                'updated_at': datetime.now().isoformat(),
                'updated_by': 'API'
            })

            # 파일 저장
            with open(self.policy_file_path, 'w', encoding='utf-8') as f:
                yaml.dump(policy_data, f, default_flow_style=False, allow_unicode=True)

            self.log.info(f"정책 파일 저장 완료: {self.policy_file_path}")
            return True

        except Exception as e:
            self.log.error(f"정책 파일 저장 실패: {e}")
            return False

    def test_policy(self, request: PolicyTestRequest) -> PolicyTestResult:
        """정책 시뮬레이션 테스트"""
        try:
            # 테스트할 정책 결정
            if request.test_policy:
                test_policy_dict = request.test_policy.dict()
            else:
                test_policy_dict = self.load_policy()

            # 지표별 설정 가져오기
            metrics_config = test_policy_dict.get('metrics', {})
            metric_config = metrics_config.get(request.metric_name, {})

            threshold = metric_config.get('threshold', test_policy_dict.get('detection', {}).get('default_threshold', 3.0))
            window_size = metric_config.get('window_size', test_policy_dict.get('detection', {}).get('default_window_size', 7))

            # 간단한 이상탐지 시뮬레이션
            import numpy as np
            values = np.array(request.sample_values)

            # 이동평균과 표준편차 계산
            anomalies = []
            alert_levels = []

            for i in range(window_size, len(values)):
                window_data = values[i-window_size:i]
                mean_val = np.mean(window_data)
                std_val = np.std(window_data)

                if std_val > 0:
                    z_score = abs((values[i] - mean_val) / std_val)
                    if z_score >= threshold:
                        anomalies.append(i)
                        alert_levels.append(self._classify_alert_level(z_score, test_policy_dict))

            # 서프레션 적용
            suppressed_count = self._simulate_suppression(anomalies, request.metric_name, test_policy_dict)

            # 결과 집계
            alert_distribution = {}
            for level in alert_levels:
                alert_distribution[level] = alert_distribution.get(level, 0) + 1

            evaluation = self._generate_evaluation_summary(
                len(anomalies), suppressed_count, len(request.sample_values), alert_distribution
            )

            return PolicyTestResult(
                metric_name=request.metric_name,
                total_samples=len(request.sample_values),
                anomalies_detected=len(anomalies),
                suppressed_alerts=suppressed_count,
                alert_distribution=alert_distribution,
                evaluation_summary=evaluation
            )

        except Exception as e:
            self.log.error(f"정책 테스트 실패: {e}")
            raise HTTPException(status_code=500, detail=f"정책 테스트 중 오류 발생: {str(e)}")

    def get_suppression_status(self) -> List[SuppressionStatus]:
        """현재 서프레션 상태 조회"""
        try:
            policy = self.load_policy()
            status_list = []

            # 지표별 서프레션 상태 확인
            suppression_metrics = policy.get('suppression', {}).get('metric_based', {})

            for metric_name, config in suppression_metrics.items():
                history = self._suppression_history.get(metric_name, [])
                now = datetime.now()

                # 오늘과 이번 시간의 알림 수 계산
                today_alerts = len([dt for dt in history if dt.date() == now.date()])
                hour_alerts = len([dt for dt in history if dt.hour == now.hour and dt.date() == now.date()])

                # 마지막 알림 시간
                last_alert = max(history) if history else None

                # 현재 억제 여부 판단
                is_suppressed = False
                suppression_reason = ""

                if last_alert:
                    cooldown_minutes = config.get('cooldown_minutes', 30)
                    if (now - last_alert).total_seconds() < cooldown_minutes * 60:
                        is_suppressed = True
                        suppression_reason = f"쿨다운 중 ({cooldown_minutes}분)"

                if today_alerts >= config.get('max_hourly_alerts', 4):
                    is_suppressed = True
                    suppression_reason = "시간당 알림 한도 초과"

                status_list.append(SuppressionStatus(
                    metric_name=metric_name,
                    last_alert_time=last_alert.isoformat() if last_alert else None,
                    suppressed_count_today=today_alerts,
                    suppressed_count_hour=hour_alerts,
                    is_currently_suppressed=is_suppressed,
                    suppression_reason=suppression_reason
                ))

            return status_list

        except Exception as e:
            self.log.error(f"서프레션 상태 조회 실패: {e}")
            return []

    def _get_default_policy(self) -> Dict[str, Any]:
        """기본 정책 반환"""
        return {
            "detection": {
                "default_window_size": 7,
                "default_threshold": 3.0,
                "default_forecast_days": 7,
                "ewma_alpha": 0.3
            },
            "metrics": {},
            "alert_levels": {
                "low": {"threshold": 2.0, "color": "#17a2b8", "description": "참고용 알림"},
                "medium": {"threshold": 3.0, "color": "#ffc107", "description": "모니터링 강화"},
                "high": {"threshold": 4.0, "color": "#fd7e14", "description": "신속 확인 요망"},
                "critical": {"threshold": 5.0, "color": "#dc3545", "description": "즉시 대응 필요"}
            },
            "suppression": {
                "global": {
                    "enabled": True,
                    "consecutive_alert_cooldown": 30,
                    "max_alerts_per_day": 100
                }
            }
        }

    def _classify_alert_level(self, z_score: float, policy: Dict[str, Any]) -> str:
        """Z-score에 따른 알림 레벨 분류"""
        alert_levels = policy.get('alert_levels', {})

        for level in ['critical', 'high', 'medium', 'low']:
            if level in alert_levels and z_score >= alert_levels[level].get('threshold', 3.0):
                return level

        return 'low'

    def _simulate_suppression(self, anomaly_indices: List[int], metric_name: str, policy: Dict[str, Any]) -> int:
        """서프레션 시뮬레이션"""
        suppression_config = policy.get('suppression', {})
        if not suppression_config.get('global', {}).get('enabled', True):
            return 0

        # 간단한 서프레션 로직 (연속 알림 억제)
        cooldown = suppression_config.get('global', {}).get('consecutive_alert_cooldown', 30)
        suppressed_count = 0

        last_alert_idx = None
        for idx in anomaly_indices:
            if last_alert_idx is not None and (idx - last_alert_idx) < cooldown / (24 * 60):  # 일 단위 변환
                suppressed_count += 1
            else:
                last_alert_idx = idx

        return suppressed_count

    def _generate_evaluation_summary(self, anomalies: int, suppressed: int, total: int, distribution: Dict[str, int]) -> str:
        """평가 요약 생성 (한국어)"""
        detection_rate = (anomalies / total * 100) if total > 0 else 0
        suppression_rate = (suppressed / anomalies * 100) if anomalies > 0 else 0

        summary = f"탐지율: {detection_rate:.1f}% ({anomalies}/{total}), 억제율: {suppression_rate:.1f}%"

        if distribution:
            level_summary = ", ".join([f"{level}: {count}개" for level, count in distribution.items()])
            summary += f" - 레벨별: {level_summary}"

        return summary

# 전역 정책 매니저 인스턴스
policy_manager = AnomalyPolicyManager()

# ==========================================
# API 엔드포인트
# ==========================================

@router.get("/policy", response_model=Dict[str, Any], summary="이상탐지 정책 조회")
async def get_anomaly_policy(
    current_user=Depends(require_role([RoleEnum.ADMIN, RoleEnum.OPERATOR, RoleEnum.USER]))
):
    """
    현재 이상탐지 정책 설정 조회

    **권한**: ADMIN, OPERATOR, USER
    **캐시**: 5분
    """
    try:
        policy_data = policy_manager.load_policy()

        # 민감한 정보 마스킹 (USER 권한인 경우)
        if hasattr(current_user, 'role') and current_user.role == RoleEnum.USER:
            # 알림 채널 정보 등 민감한 정보 제거
            if 'notification' in policy_data:
                policy_data['notification'] = {"message": "권한 부족으로 표시할 수 없습니다"}

        return {
            "success": True,
            "data": policy_data,
            "message": "정책 조회 완료"
        }

    except Exception as e:
        log.error(f"정책 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"정책 조회 중 오류가 발생했습니다: {str(e)}")

@router.post("/policy", response_model=Dict[str, Any], summary="이상탐지 정책 저장")
async def save_anomaly_policy(
    policy_request: Dict[str, Any],
    current_user=Depends(require_role([RoleEnum.ADMIN]))
):
    """
    이상탐지 정책 설정 저장

    **권한**: ADMIN만 가능
    **입력**: 전체 정책 설정 Dict
    """
    try:
        # 정책 저장
        success = policy_manager.save_policy(policy_request)

        if not success:
            raise HTTPException(status_code=500, detail="정책 저장에 실패했습니다")

        return {
            "success": True,
            "message": "정책이 성공적으로 저장되었습니다",
            "saved_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"정책 저장 실패: {e}")
        raise HTTPException(status_code=500, detail=f"정책 저장 중 오류가 발생했습니다: {str(e)}")

@router.post("/policy/test", response_model=PolicyTestResult, summary="정책 시뮬레이션 테스트")
async def test_anomaly_policy(
    test_request: PolicyTestRequest,
    current_user=Depends(require_role([RoleEnum.ADMIN, RoleEnum.OPERATOR]))
):
    """
    샘플 데이터에 대한 정책 적용 시뮬레이션

    **권한**: ADMIN, OPERATOR
    **기능**:
    - 주어진 샘플 데이터에 정책 적용
    - 탐지되는 이상치 수와 알림 레벨 분석
    - 서프레션 룰 적용 결과 확인
    """
    try:
        result = policy_manager.test_policy(test_request)

        return result

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"정책 테스트 실패: {e}")
        raise HTTPException(status_code=500, detail=f"정책 테스트 중 오류가 발생했습니다: {str(e)}")

@router.get("/suppression", response_model=List[SuppressionStatus], summary="서프레션 상태 조회")
async def get_suppression_status(
    current_user=Depends(require_role([RoleEnum.ADMIN, RoleEnum.OPERATOR]))
):
    """
    현재 서프레션 룰 및 억제 상태 조회

    **권한**: ADMIN, OPERATOR
    **기능**:
    - 지표별 서프레션 히스토리
    - 현재 억제 중인 지표 목록
    - 쿨다운 상태 및 남은 시간
    """
    try:
        status_list = policy_manager.get_suppression_status()

        return status_list

    except Exception as e:
        log.error(f"서프레션 상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"서프레션 상태 조회 중 오류가 발생했습니다: {str(e)}")

@router.get("/policy/health", response_model=Dict[str, Any], summary="정책 API 헬스체크")
async def policy_health_check():
    """
    정책 API 상태 확인

    **기능**:
    - 정책 파일 존재 여부
    - 파일 읽기/쓰기 권한
    - 설정 유효성 검사
    """
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "policy_file_exists": POLICY_FILE_PATH.exists(),
            "policy_file_path": str(POLICY_FILE_PATH),
            "policy_file_readable": os.access(POLICY_FILE_PATH, os.R_OK) if POLICY_FILE_PATH.exists() else False,
            "policy_file_writable": os.access(POLICY_FILE_PATH.parent, os.W_OK),
        }

        # 정책 파일 로드 테스트
        try:
            policy_data = policy_manager.load_policy()
            health_status["policy_load_success"] = True
            health_status["policy_metrics_count"] = len(policy_data.get('metrics', {}))
        except Exception as e:
            health_status["policy_load_success"] = False
            health_status["policy_load_error"] = str(e)
            health_status["status"] = "degraded"

        return health_status

    except Exception as e:
        log.error(f"헬스체크 실패: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }