/**
 * 시스템 상태 위젯 컴포넌트
 * 대시보드에 표시되는 시스템 전체 상태 모니터링
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Grid,
  Chip,
  Box,
  CircularProgress,
  Tooltip,
  IconButton,
  Alert,
  LinearProgress
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon,
  Info as InfoIcon
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import { ko } from 'date-fns/locale';

import { API } from '../../services/api';
import {
  ServiceStatusResponse,
  ServiceStatus,
  OverallStatus
} from '../../types';

interface SystemStatusWidgetProps {
  refreshInterval?: number;  // 새로고침 간격 (밀리초)
  compact?: boolean;        // 컴팩트 모드
}

// 상태별 색상 및 아이콘 매핑
const getStatusConfig = (status: ServiceStatus | OverallStatus) => {
  switch (status) {
    case ServiceStatus.ONLINE:
    case OverallStatus.OPERATIONAL:
      return { 
        color: 'success' as const, 
        icon: <CheckCircleIcon />, 
        label: '정상' 
      };
    case ServiceStatus.DEGRADED:
    case OverallStatus.DEGRADED:
      return { 
        color: 'warning' as const, 
        icon: <WarningIcon />, 
        label: '저하됨' 
      };
    case ServiceStatus.OFFLINE:
    case OverallStatus.CRITICAL:
      return { 
        color: 'error' as const, 
        icon: <ErrorIcon />, 
        label: '오프라인' 
      };
    default:
      return { 
        color: 'default' as const, 
        icon: <InfoIcon />, 
        label: '알 수 없음' 
      };
  }
};

// 서비스별 한글 이름 매핑
const getServiceDisplayName = (serviceName: string): string => {
  const serviceNames: Record<string, string> = {
    'api': 'API 서버',
    'database': '데이터베이스',
    'ai_engine': 'AI 엔진',
    'websocket': 'WebSocket',
    'batch_system': '배치 시스템',
    'usage_tracking': '사용량 추적',
    'external_apis': '외부 API'
  };
  return serviceNames[serviceName] || serviceName;
};

export const SystemStatusWidget: React.FC<SystemStatusWidgetProps> = ({
  refreshInterval = 30000, // 30초 기본값
  compact = false
}) => {
  const [isManualRefreshing, setIsManualRefreshing] = useState(false);

  // 시스템 상태 조회 쿼리
  const { 
    data: statusData, 
    isLoading, 
    error, 
    refetch,
    dataUpdatedAt 
  } = useQuery({
    queryKey: ['system-status'],
    queryFn: API.Health.getServiceStatus,
    refetchInterval: refreshInterval,
    staleTime: 15000, // 15초 후 stale
    retry: 3
  });

  // 수동 새로고침
  const handleManualRefresh = async () => {
    setIsManualRefreshing(true);
    await refetch();
    setIsManualRefreshing(false);
  };

  // 로딩 중이거나 에러 시 표시
  if (isLoading && !statusData) {
    return (
      <Card>
        <CardContent>
          <Box display="flex" alignItems="center" justifyContent="center" minHeight={100}>
            <CircularProgress size={24} />
            <Typography variant="body2" sx={{ ml: 2 }}>
              시스템 상태 확인 중...
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  if (error && !statusData) {
    return (
      <Card>
        <CardContent>
          <Alert severity="error" sx={{ mb: 2 }}>
            시스템 상태를 불러올 수 없습니다.
          </Alert>
          <Box display="flex" justifyContent="center">
            <IconButton onClick={handleManualRefresh} disabled={isManualRefreshing}>
              <RefreshIcon />
            </IconButton>
          </Box>
        </CardContent>
      </Card>
    );
  }

  const statusInfo = statusData as ServiceStatusResponse;
  const overallConfig = getStatusConfig(statusInfo?.overall_status);

  // 컴팩트 모드
  if (compact) {
    return (
      <Card>
        <CardContent sx={{ p: 2 }}>
          <Box display="flex" alignItems="center" justifyContent="space-between">
            <Box display="flex" alignItems="center">
              <Chip
                icon={overallConfig.icon}
                label={`시스템 ${overallConfig.label}`}
                color={overallConfig.color}
                variant="outlined"
                size="small"
              />
              <Typography variant="caption" color="textSecondary" sx={{ ml: 1 }}>
                {format(new Date(dataUpdatedAt), 'HH:mm:ss', { locale: ko })}
              </Typography>
            </Box>
            <IconButton 
              size="small" 
              onClick={handleManualRefresh} 
              disabled={isManualRefreshing || isLoading}
            >
              <RefreshIcon fontSize="small" />
            </IconButton>
          </Box>
        </CardContent>
      </Card>
    );
  }

  // 전체 모드
  return (
    <Card>
      <CardContent>
        {/* 헤더 */}
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6" component="h3">
            시스템 상태
          </Typography>
          <Box display="flex" alignItems="center">
            <Typography variant="caption" color="textSecondary" sx={{ mr: 1 }}>
              마지막 업데이트: {format(new Date(dataUpdatedAt), 'MM/dd HH:mm:ss', { locale: ko })}
            </Typography>
            <IconButton 
              size="small" 
              onClick={handleManualRefresh} 
              disabled={isManualRefreshing || isLoading}
            >
              <RefreshIcon fontSize="small" />
            </IconButton>
          </Box>
        </Box>

        {/* 전체 상태 */}
        <Box mb={3}>
          <Box display="flex" alignItems="center" mb={1}>
            <Chip
              icon={overallConfig.icon}
              label={`전체 상태: ${overallConfig.label}`}
              color={overallConfig.color}
              variant="filled"
            />
          </Box>
          
          {/* 시스템 정보 */}
          {statusInfo?.system_info && (
            <Box mt={2}>
              <Grid container spacing={2}>
                <Grid item xs={6} md={3}>
                  <Typography variant="body2" color="textSecondary">버전</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {statusInfo.system_info.version}
                  </Typography>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Typography variant="body2" color="textSecondary">환경</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {statusInfo.system_info.environment}
                  </Typography>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Typography variant="body2" color="textSecondary">업타임</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {Math.round(statusInfo.system_info.uptime_seconds / 60)}분
                  </Typography>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Typography variant="body2" color="textSecondary">모니터링 서비스</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {statusInfo.system_info.services_monitored}개
                  </Typography>
                </Grid>
              </Grid>
            </Box>
          )}
        </Box>

        {/* 개별 서비스 상태 */}
        <Typography variant="subtitle2" gutterBottom>
          서비스별 상태
        </Typography>
        <Grid container spacing={1}>
          {Object.entries(statusInfo?.services || {}).map(([serviceName, serviceStatus]) => {
            const serviceConfig = getStatusConfig(serviceStatus);
            return (
              <Grid item xs={12} sm={6} md={4} key={serviceName}>
                <Tooltip title={`${getServiceDisplayName(serviceName)}: ${serviceConfig.label}`}>
                  <Box 
                    display="flex" 
                    alignItems="center" 
                    p={1} 
                    border={1} 
                    borderColor="grey.300" 
                    borderRadius={1}
                  >
                    <Box sx={{ color: `${serviceConfig.color}.main` }}>
                      {serviceConfig.icon}
                    </Box>
                    <Typography variant="body2" sx={{ ml: 1, flex: 1 }}>
                      {getServiceDisplayName(serviceName)}
                    </Typography>
                    <Chip
                      label={serviceConfig.label}
                      color={serviceConfig.color}
                      size="small"
                      variant="outlined"
                    />
                  </Box>
                </Tooltip>
              </Grid>
            );
          })}
        </Grid>

        {/* 상세 헬스체크 링크 */}
        {statusInfo?.detailed_check_url && (
          <Box mt={2} textAlign="center">
            <Typography variant="caption" color="textSecondary">
              상세 헬스체크: {statusInfo.detailed_check_url}
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};