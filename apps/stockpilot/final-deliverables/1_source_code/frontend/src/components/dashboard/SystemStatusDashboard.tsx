/**
 * 실시간 시스템 상태 대시보드
 * /api/v1/status API 응답을 실시간으로 표시하는 메인 대시보드
 */

import React, { useState } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  IconButton,
  CircularProgress,
  Alert,
  Tooltip,
  Paper,
  Divider,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Circle as CircleIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { API } from '../../services/api';
import { SystemStatus, ServiceStatus, isServiceStatus, defaultSystemStatus } from '../../types/api';


// 서비스 상태별 색상 및 아이콘 매핑
const getStatusColor = (status: string) => {
  switch (status) {
    case 'online':
    case 'operational':
      return 'success';
    case 'degraded':
      return 'warning';
    case 'offline':
    case 'outage':
      return 'error';
    case 'unknown':
      return 'default';
    default:
      return 'default';
  }
};

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'online':
    case 'operational':
      return <CheckCircleIcon color="success" />;
    case 'degraded':
      return <WarningIcon color="warning" />;
    case 'offline':
    case 'outage':
      return <ErrorIcon color="error" />;
    case 'unknown':
      return <CircleIcon color="disabled" />;
    default:
      return <CircleIcon color="disabled" />;
  }
};

const getStatusText = (status: string) => {
  switch (status) {
    case 'online':
    case 'operational':
      return '정상';
    case 'degraded':
      return '성능 저하';
    case 'offline':
    case 'outage':
      return '오프라인';
    case 'unknown':
      return '상태 불명';
    default:
      return '상태 불명';
  }
};

// 서비스 이름 한국어 매핑
const getServiceName = (serviceKey: string) => {
  const serviceNames: { [key: string]: string } = {
    api: 'API 서버',
    database: '데이터베이스',
    ai_engine: 'AI 엔진',
    websocket: 'WebSocket',
    batch_system: '배치 시스템',
    usage_tracking: '사용량 추적',
    external_apis: '외부 API',
  };
  return serviceNames[serviceKey] || serviceKey;
};

interface Props {
  refreshInterval?: number;
}

// 안전한 타입 변환 유틸리티 함수
const ensureSystemStatus = (data: unknown): SystemStatus => {
  if (!data || typeof data !== 'object') {
    return defaultSystemStatus;
  }
  return data as SystemStatus;
};

export const SystemStatusDashboard: React.FC<Props> = ({
  refreshInterval = 30000, // 30초마다 갱신
}) => {
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  // 시스템 상태 데이터 조회
  // React Query v3 호환 시그니처 사용 - 매개변수 없는 함수로 래핑
  const {
    data: rawData,
    isLoading,
    error,
    refetch,
    isFetching,
  } = useQuery(
    ['system-status'],
    () => API.Health.getServiceStatus(),
    {
      refetchInterval: refreshInterval,
      refetchIntervalInBackground: true,
    }
  );

  // 안전한 타입 변환
  const statusData = ensureSystemStatus(rawData);

  // 수동 새로고침 핸들러
  const handleRefresh = () => {
    refetch();
    setLastRefreshed(new Date());
  };

  // 업타임 포맷팅
  const formatUptime = (seconds?: number) => {
    if (!seconds) return 'N/A';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (hours > 0) {
      return `${hours}시간 ${minutes}분`;
    }
    return `${minutes}분`;
  };

  if (isLoading && !statusData) {
    return (
      <Card>
        <CardContent>
          <Box display="flex" justifyContent="center" alignItems="center" minHeight={200}>
            <CircularProgress />
            <Typography variant="body2" sx={{ ml: 2 }}>
              시스템 상태를 확인하는 중...
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent>
          <Alert severity="error">
            시스템 상태를 불러올 수 없습니다. 네트워크 연결을 확인해주세요.
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        {/* 헤더 섹션 */}
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Box display="flex" alignItems="center">
            <Typography variant="h6" fontWeight={600}>
              시스템 상태 모니터링
            </Typography>
            {statusData && (
              <Chip
                icon={getStatusIcon(statusData.overall_status)}
                label={getStatusText(statusData.overall_status)}
                color={getStatusColor(statusData.overall_status) as any}
                size="small"
                sx={{ ml: 2 }}
              />
            )}
          </Box>
          
          <Box display="flex" alignItems="center">
            <Typography variant="caption" color="text.secondary" sx={{ mr: 1 }}>
              마지막 업데이트: {lastRefreshed.toLocaleTimeString()}
            </Typography>
            <Tooltip title="새로고침">
              <IconButton
                onClick={handleRefresh}
                disabled={isFetching}
                size="small"
              >
                <RefreshIcon />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {statusData && (
          <>
            {/* 시스템 정보 섹션 */}
            {statusData.system_info && (
              <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
                <Typography variant="subtitle2" fontWeight={600} mb={1}>
                  시스템 정보
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6} sm={3}>
                    <Typography variant="caption" color="text.secondary">
                      버전
                    </Typography>
                    <Typography variant="body2" fontWeight={500}>
                      {statusData.system_info.version}
                    </Typography>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Typography variant="caption" color="text.secondary">
                      환경
                    </Typography>
                    <Typography variant="body2" fontWeight={500}>
                      {statusData.system_info.environment}
                    </Typography>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Typography variant="caption" color="text.secondary">
                      업타임
                    </Typography>
                    <Typography variant="body2" fontWeight={500}>
                      {formatUptime(statusData.system_info.uptime_seconds)}
                    </Typography>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Typography variant="caption" color="text.secondary">
                      최종 확인
                    </Typography>
                    <Typography variant="body2" fontWeight={500}>
                      {new Date(statusData.last_updated).toLocaleTimeString()}
                    </Typography>
                  </Grid>
                </Grid>
              </Paper>
            )}

            {/* 서비스 상태 그리드 */}
            <Typography variant="subtitle2" fontWeight={600} mb={2}>
              서비스 상태
            </Typography>
            <Grid container spacing={2}>
              {Object.entries(statusData.services).map(([serviceKey, status]: [string, ServiceStatus]) => (
                <Grid item xs={12} sm={6} md={4} lg={3} key={serviceKey}>
                  <Paper
                    variant="outlined"
                    sx={{
                      p: 2,
                      height: '100%',
                      borderColor: status === 'online' ? 'success.main' : 
                                   status === 'degraded' ? 'warning.main' :
                                   status === 'offline' ? 'error.main' : 'grey.300',
                      borderWidth: status === 'online' ? 2 : 1,
                    }}
                  >
                    <Box display="flex" alignItems="center" mb={1}>
                      {getStatusIcon(status)}
                      <Typography variant="subtitle2" fontWeight={600} sx={{ ml: 1 }}>
                        {getServiceName(serviceKey)}
                      </Typography>
                    </Box>
                    
                    <Chip
                      label={getStatusText(status)}
                      color={getStatusColor(status) as 'success' | 'warning' | 'error' | 'default'}
                      size="small"
                      variant={status === 'online' ? 'filled' : 'outlined'}
                    />
                    
                    {/* 추가 상태 정보 표시 (필요시) */}
                    {status === 'degraded' && (
                      <Typography variant="caption" color="warning.main" display="block" mt={1}>
                        ⚠️ 성능이 저하되어 있습니다
                      </Typography>
                    )}
                    {status === 'offline' && (
                      <Typography variant="caption" color="error.main" display="block" mt={1}>
                        🔴 서비스에 연결할 수 없습니다
                      </Typography>
                    )}
                    {status === 'unknown' && (
                      <Typography variant="caption" color="text.secondary" display="block" mt={1}>
                        ❓ 상태를 확인할 수 없습니다
                      </Typography>
                    )}
                  </Paper>
                </Grid>
              ))}
            </Grid>

            {/* 전체 상태 요약 */}
            <Divider sx={{ my: 3 }} />
            <Box display="flex" justifyContent="center">
              <Alert 
                severity={
                  statusData.overall_status === 'operational' ? 'success' :
                  statusData.overall_status === 'degraded' ? 'warning' : 'error'
                }
                sx={{ width: 'fit-content' }}
              >
                <Typography variant="body2">
                  {statusData.overall_status === 'operational' && 
                    '🟢 모든 시스템이 정상적으로 운영되고 있습니다.'}
                  {statusData.overall_status === 'degraded' && 
                    '🟡 일부 서비스에서 성능 저하가 발생하고 있습니다.'}
                  {statusData.overall_status === 'outage' && 
                    '🔴 시스템 장애가 발생했습니다. 복구 작업을 진행하고 있습니다.'}
                </Typography>
              </Alert>
            </Box>
          </>
        )}
      </CardContent>
    </Card>
  );
};