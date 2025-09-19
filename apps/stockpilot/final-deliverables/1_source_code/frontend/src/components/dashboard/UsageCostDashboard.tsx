/**
 * OpenAI 사용량 및 비용 추적 대시보드
 * 실시간 비용 모니터링 및 80% 임계치 경고 시스템
 */

import React, { useState } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  LinearProgress,
  Alert,
  Chip,
  IconButton,
  Tooltip,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  TrendingUp as TrendingUpIcon,
  AttachMoney as AttachMoneyIcon,
  Speed as SpeedIcon,
  Assessment as AssessmentIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { API } from '../../services/api';
import { UsageStats, DailyUsage, ModelUsage, defaultUsageStats, UsageLimits } from '../../types/api';


interface Props {
  refreshInterval?: number;
}

// 안전한 타입 변환 유틸리티 함수
const ensureUsageStats = (data: unknown): UsageStats => {
  if (!data || typeof data !== 'object') {
    return defaultUsageStats;
  }
  return data as UsageStats;
};

const ensureDailyUsage = (data: unknown): DailyUsage | null => {
  if (!data || typeof data !== 'object') {
    return null;
  }
  return data as DailyUsage;
};

export const UsageCostDashboard: React.FC<Props> = ({
  refreshInterval = 60000, // 1분마다 갱신
}) => {
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  // 사용량 데이터 조회
  // React Query v3 호환 시그니처 사용 - 매개변수 없는 함수로 래핑
  const {
    data: rawData,
    isLoading,
    error,
    refetch,
    isFetching,
  } = useQuery(
    ['usage-stats'],
    () => API.Usage.getUsageStats(),
    {
      refetchInterval: refreshInterval,
      refetchIntervalInBackground: true,
    }
  );

  // 안전한 타입 변환
  const usageData = ensureUsageStats(rawData);

  // 수동 새로고침 핸들러
  const handleRefresh = () => {
    refetch();
    setLastRefreshed(new Date());
  };

  // 오늘 사용량 데이터 추출 (안전한 접근)
  const todayUsageData = usageData?.daily_usage ? Object.values(usageData.daily_usage)[0] : undefined;
  const todayUsage = ensureDailyUsage(todayUsageData);

  // 비용 사용률 계산 (안전한 접근)
  const costUsagePercent = todayUsage?.cost_usage_percent ?? 0;
  const currentLimits: UsageLimits = usageData?.current_limits ?? defaultUsageStats.current_limits;
  const alertThreshold = currentLimits.alert_threshold;
  const isNearLimit = costUsagePercent >= alertThreshold * 100;
  const isOverLimit = costUsagePercent >= 100;

  // 진행률 바 색상 결정
  const getProgressColor = (percent: number) => {
    if (percent >= 100) return 'error';
    if (percent >= 80) return 'warning';
    return 'success';
  };

  // 숫자 포맷팅 함수
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('ko-KR', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('ko-KR').format(num);
  };

  const formatPercent = (percent: number) => {
    return `${percent.toFixed(1)}%`;
  };

  if (isLoading && !usageData) {
    return (
      <Card>
        <CardContent>
          <Box display="flex" justifyContent="center" alignItems="center" minHeight={200}>
            <CircularProgress />
            <Typography variant="body2" sx={{ ml: 2 }}>
              사용량 데이터를 불러오는 중...
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
            사용량 데이터를 불러올 수 없습니다. 잠시 후 다시 시도해주세요.
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Grid container spacing={3}>
      {/* 헤더 섹션 */}
      <Grid item xs={12}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6" fontWeight={600}>
            OpenAI 사용량 및 비용 모니터링
          </Typography>
          <Box display="flex" alignItems="center">
            <Typography variant="caption" color="text.secondary" sx={{ mr: 1 }}>
              마지막 업데이트: {lastRefreshed.toLocaleTimeString()}
            </Typography>
            <Tooltip title="새로고침">
              <IconButton onClick={handleRefresh} disabled={isFetching} size="small">
                <RefreshIcon />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>
      </Grid>

      {/* 경고 알림 */}
      {isOverLimit && (
        <Grid item xs={12}>
          <Alert severity="error" icon={<WarningIcon />}>
            ⚠️ 일일 비용 한도를 초과했습니다! 추가 사용이 제한될 수 있습니다.
          </Alert>
        </Grid>
      )}
      {isNearLimit && !isOverLimit && (
        <Grid item xs={12}>
          <Alert severity="warning" icon={<WarningIcon />}>
            ⚠️ 일일 비용 한도의 80%에 도달했습니다. 사용량을 주의해주세요.
          </Alert>
        </Grid>
      )}

      {usageData && todayUsage && (
        <>
          {/* 메인 지표 카드들 */}
          <Grid item xs={12} sm={6} lg={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" mb={1}>
                  <AttachMoneyIcon color="primary" />
                  <Typography variant="subtitle2" fontWeight={600} sx={{ ml: 1 }}>
                    오늘 비용
                  </Typography>
                </Box>
                <Typography variant="h4" fontWeight={700} color="primary">
                  {formatCurrency(todayUsage?.total_cost ?? 0)}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  한도: {formatCurrency(currentLimits.daily_limit)}
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={Math.min(costUsagePercent, 100)}
                  color={getProgressColor(costUsagePercent)}
                  sx={{ mt: 1, height: 8, borderRadius: 1 }}
                />
                <Typography variant="caption" color="text.secondary">
                  {formatPercent(costUsagePercent)} 사용
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} lg={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" mb={1}>
                  <TrendingUpIcon color="success" />
                  <Typography variant="subtitle2" fontWeight={600} sx={{ ml: 1 }}>
                    요청 수
                  </Typography>
                </Box>
                <Typography variant="h4" fontWeight={700} color="success.main">
                  {formatNumber(todayUsage?.total_requests ?? 0)}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  성공: {formatNumber(todayUsage?.success_requests ?? 0)} ({formatPercent(todayUsage?.success_rate_percent ?? 0)})
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} lg={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" mb={1}>
                  <AssessmentIcon color="info" />
                  <Typography variant="subtitle2" fontWeight={600} sx={{ ml: 1 }}>
                    토큰 사용량
                  </Typography>
                </Box>
                <Typography variant="h4" fontWeight={700} color="info.main">
                  {formatNumber(todayUsage?.total_tokens ?? 0)}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  토큰
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} lg={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" mb={1}>
                  <SpeedIcon color="warning" />
                  <Typography variant="subtitle2" fontWeight={600} sx={{ ml: 1 }}>
                    평균 응답시간
                  </Typography>
                </Box>
                <Typography variant="h4" fontWeight={700} color="warning.main">
                  {(todayUsage?.avg_response_time_ms ?? 0).toFixed(0)}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  밀리초
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          {/* 모델별 사용량 표 */}
          {todayUsage?.model_usage && Object.keys(todayUsage.model_usage).length > 0 && (
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" fontWeight={600} mb={2}>
                    모델별 사용량 통계
                  </Typography>
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell><strong>모델</strong></TableCell>
                          <TableCell align="right"><strong>요청 수</strong></TableCell>
                          <TableCell align="right"><strong>토큰</strong></TableCell>
                          <TableCell align="right"><strong>비용</strong></TableCell>
                          <TableCell align="right"><strong>비용 비율</strong></TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {todayUsage?.model_usage && Object.entries(todayUsage.model_usage).map(([model, usage]) => (
                          <TableRow key={model}>
                            <TableCell>
                              <Chip 
                                label={model} 
                                size="small" 
                                variant="outlined"
                                color={model.includes('gpt-4') ? 'primary' : 'default'}
                              />
                            </TableCell>
                            <TableCell align="right">
                              {formatNumber((usage as ModelUsage)?.requests ?? 0)}
                            </TableCell>
                            <TableCell align="right">
                              {formatNumber((usage as ModelUsage)?.tokens ?? 0)}
                            </TableCell>
                            <TableCell align="right">
                              {formatCurrency((usage as ModelUsage)?.cost ?? 0)}
                            </TableCell>
                            <TableCell align="right">
                              {formatPercent((((usage as ModelUsage)?.cost ?? 0) / (todayUsage?.total_cost ?? 1)) * 100)}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </CardContent>
              </Card>
            </Grid>
          )}

          {/* 요약 통계 */}
          <Grid item xs={12}>
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Typography variant="subtitle2" fontWeight={600} mb={2}>
                전체 사용량 요약
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={6} sm={3}>
                  <Typography variant="caption" color="text.secondary">
                    총 누적 비용
                  </Typography>
                  <Typography variant="h6" fontWeight={600}>
                    {formatCurrency(usageData?.summary?.total_cost_to_date ?? 0)}
                  </Typography>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Typography variant="caption" color="text.secondary">
                    총 요청 수
                  </Typography>
                  <Typography variant="h6" fontWeight={600}>
                    {formatNumber(usageData?.summary?.total_requests_to_date ?? 0)}
                  </Typography>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Typography variant="caption" color="text.secondary">
                    일평균 비용
                  </Typography>
                  <Typography variant="h6" fontWeight={600}>
                    {formatCurrency(usageData?.summary?.avg_daily_cost ?? 0)}
                  </Typography>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Typography variant="caption" color="text.secondary">
                    평균 성공률
                  </Typography>
                  <Typography variant="h6" fontWeight={600}>
                    {formatPercent(usageData?.summary?.avg_success_rate ?? 0)}
                  </Typography>
                </Grid>
              </Grid>
            </Paper>
          </Grid>
        </>
      )}
    </Grid>
  );
};