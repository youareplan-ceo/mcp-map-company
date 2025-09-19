/**
 * 사용량 통계 위젯 컴포넌트
 * OpenAI API 사용량 및 비용 모니터링
 */

import React, { useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Grid,
  Box,
  CircularProgress,
  LinearProgress,
  Chip,
  Tooltip,
  IconButton,
  Alert,
  Tab,
  Tabs,
  List,
  ListItem,
  ListItemText,
  Divider
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  TrendingUp as TrendingUpIcon,
  AttachMoney as AttachMoneyIcon,
  Speed as SpeedIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { format, parseISO } from 'date-fns';
import { ko } from 'date-fns/locale';
import numeral from 'numeral';

import { API } from '../../services/api';
import { UsageStatsResponse, DailyUsage } from '../../types';

interface UsageStatsWidgetProps {
  refreshInterval?: number;
  compact?: boolean;
  days?: number;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index, ...other }) => {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`usage-tabpanel-${index}`}
      aria-labelledby={`usage-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 1 }}>
          {children}
        </Box>
      )}
    </div>
  );
};

export const UsageStatsWidget: React.FC<UsageStatsWidgetProps> = ({
  refreshInterval = 60000, // 1분 기본값
  compact = false,
  days = 7
}) => {
  const [isManualRefreshing, setIsManualRefreshing] = useState(false);
  const [tabValue, setTabValue] = useState(0);

  // 사용량 통계 조회 쿼리
  const { 
    data: usageData, 
    isLoading, 
    error, 
    refetch,
    dataUpdatedAt 
  } = useQuery({
    queryKey: ['usage-stats', days],
    queryFn: () => API.Usage.getUsageStats(days),
    refetchInterval: refreshInterval,
    staleTime: 30000, // 30초 후 stale
    retry: 2
  });

  // 수동 새로고침
  const handleManualRefresh = async () => {
    setIsManualRefreshing(true);
    await refetch();
    setIsManualRefreshing(false);
  };

  // 탭 변경 핸들러
  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  // 비용 사용률 색상 결정
  const getCostUsageColor = (percentage: number): 'success' | 'warning' | 'error' => {
    if (percentage >= 90) return 'error';
    if (percentage >= 80) return 'warning';
    return 'success';
  };

  // 로딩 중이거나 에러 시 표시
  if (isLoading && !usageData) {
    return (
      <Card>
        <CardContent>
          <Box display="flex" alignItems="center" justifyContent="center" minHeight={100}>
            <CircularProgress size={24} />
            <Typography variant="body2" sx={{ ml: 2 }}>
              사용량 통계 로딩 중...
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  if (error && !usageData) {
    return (
      <Card>
        <CardContent>
          <Alert severity="error" sx={{ mb: 2 }}>
            사용량 통계를 불러올 수 없습니다.
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

  const stats = usageData as UsageStatsResponse;
  
  // 오늘 사용량 데이터
  const today = format(new Date(), 'yyyy-MM-dd');
  const todayUsage = stats?.daily_usage?.[today] || {
    date: today,
    total_requests: 0,
    total_tokens: 0,
    total_cost: 0,
    success_requests: 0,
    failed_requests: 0,
    cost_usage_percent: 0,
    success_rate_percent: 0,
    avg_response_time_ms: 0,
    model_usage: {},
    cost_by_model: {},
    endpoint_usage: {},
    error_breakdown: {}
  } as DailyUsage;

  // 컴팩트 모드
  if (compact) {
    return (
      <Card>
        <CardContent sx={{ p: 2 }}>
          <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
            <Typography variant="subtitle2">
              AI 사용량
            </Typography>
            <IconButton 
              size="small" 
              onClick={handleManualRefresh} 
              disabled={isManualRefreshing || isLoading}
            >
              <RefreshIcon fontSize="small" />
            </IconButton>
          </Box>

          <Grid container spacing={2}>
            <Grid item xs={6}>
              <Box textAlign="center">
                <Typography variant="h6" color={getCostUsageColor(todayUsage.cost_usage_percent)}>
                  ${numeral(todayUsage.total_cost).format('0.00')}
                </Typography>
                <Typography variant="caption" color="textSecondary">
                  오늘 비용 ({todayUsage.cost_usage_percent.toFixed(1)}%)
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={6}>
              <Box textAlign="center">
                <Typography variant="h6">
                  {numeral(todayUsage.total_requests).format('0,0')}
                </Typography>
                <Typography variant="caption" color="textSecondary">
                  총 요청수
                </Typography>
              </Box>
            </Grid>
          </Grid>

          <Box mt={2}>
            <LinearProgress
              variant="determinate"
              value={todayUsage.cost_usage_percent}
              color={getCostUsageColor(todayUsage.cost_usage_percent)}
              sx={{ height: 6, borderRadius: 1 }}
            />
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
            AI 사용량 통계
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

        {/* 탭 */}
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={handleTabChange} aria-label="usage stats tabs">
            <Tab label="오늘 사용량" />
            <Tab label="주간 요약" />
            <Tab label="모델별 분석" />
          </Tabs>
        </Box>

        {/* 오늘 사용량 탭 */}
        <TabPanel value={tabValue} index={0}>
          <Grid container spacing={3}>
            {/* 주요 지표들 */}
            <Grid item xs={12} md={6}>
              <Box mb={3}>
                <Typography variant="subtitle2" gutterBottom>
                  비용 사용량
                </Typography>
                <Box display="flex" alignItems="center" mb={1}>
                  <AttachMoneyIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="h5">
                    ${numeral(todayUsage.total_cost).format('0.00')}
                  </Typography>
                  <Box ml={2}>
                    <Chip
                      label={`${todayUsage.cost_usage_percent.toFixed(1)}% 사용됨`}
                      color={getCostUsageColor(todayUsage.cost_usage_percent)}
                      size="small"
                    />
                  </Box>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={todayUsage.cost_usage_percent}
                  color={getCostUsageColor(todayUsage.cost_usage_percent)}
                  sx={{ height: 8, borderRadius: 1 }}
                />
                <Typography variant="caption" color="textSecondary">
                  일일 한도: ${numeral(stats?.current_limits?.daily_limit || 0).format('0.00')}
                </Typography>
              </Box>
            </Grid>

            <Grid item xs={12} md={6}>
              <Box mb={3}>
                <Typography variant="subtitle2" gutterBottom>
                  요청 통계
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Box textAlign="center" p={2} bgcolor="success.50" borderRadius={1}>
                      <CheckCircleIcon color="success" />
                      <Typography variant="h6" color="success.main">
                        {numeral(todayUsage.success_requests).format('0,0')}
                      </Typography>
                      <Typography variant="caption">성공</Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={6}>
                    <Box textAlign="center" p={2} bgcolor="error.50" borderRadius={1}>
                      <ErrorIcon color="error" />
                      <Typography variant="h6" color="error.main">
                        {numeral(todayUsage.failed_requests).format('0,0')}
                      </Typography>
                      <Typography variant="caption">실패</Typography>
                    </Box>
                  </Grid>
                </Grid>
              </Box>
            </Grid>

            {/* 성능 지표 */}
            <Grid item xs={12}>
              <Typography variant="subtitle2" gutterBottom>
                성능 지표
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} md={3}>
                  <Box display="flex" alignItems="center">
                    <SpeedIcon color="action" sx={{ mr: 1 }} />
                    <Box>
                      <Typography variant="body2" fontWeight="bold">
                        {todayUsage.success_rate_percent.toFixed(1)}%
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        성공률
                      </Typography>
                    </Box>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Box display="flex" alignItems="center">
                    <TrendingUpIcon color="action" sx={{ mr: 1 }} />
                    <Box>
                      <Typography variant="body2" fontWeight="bold">
                        {numeral(todayUsage.avg_response_time_ms).format('0,0')}ms
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        평균 응답시간
                      </Typography>
                    </Box>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Box display="flex" alignItems="center">
                    <AttachMoneyIcon color="action" sx={{ mr: 1 }} />
                    <Box>
                      <Typography variant="body2" fontWeight="bold">
                        {numeral(todayUsage.total_tokens).format('0,0')}
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        총 토큰수
                      </Typography>
                    </Box>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Box display="flex" alignItems="center">
                    <TrendingUpIcon color="action" sx={{ mr: 1 }} />
                    <Box>
                      <Typography variant="body2" fontWeight="bold">
                        {numeral(todayUsage.total_requests).format('0,0')}
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        총 요청수
                      </Typography>
                    </Box>
                  </Box>
                </Grid>
              </Grid>
            </Grid>
          </Grid>
        </TabPanel>

        {/* 주간 요약 탭 */}
        <TabPanel value={tabValue} index={1}>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <Typography variant="subtitle2" gutterBottom>
                최근 {days}일 요약
              </Typography>
              <List dense>
                <ListItem>
                  <ListItemText
                    primary={`총 비용: $${numeral(stats?.summary?.total_cost_to_date || 0).format('0.00')}`}
                    secondary={`평균 일일 비용: $${numeral(stats?.summary?.avg_daily_cost || 0).format('0.00')}`}
                  />
                </ListItem>
                <Divider />
                <ListItem>
                  <ListItemText
                    primary={`총 요청수: ${numeral(stats?.summary?.total_requests_to_date || 0).format('0,0')}`}
                    secondary={`평균 성공률: ${(stats?.summary?.avg_success_rate || 0).toFixed(1)}%`}
                  />
                </ListItem>
                <Divider />
                <ListItem>
                  <ListItemText
                    primary={`추적 일수: ${stats?.summary?.total_days_tracked || 0}일`}
                    secondary="데이터 수집 기간"
                  />
                </ListItem>
              </List>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="subtitle2" gutterBottom>
                한도 설정
              </Typography>
              <List dense>
                <ListItem>
                  <ListItemText
                    primary={`일일 한도: $${numeral(stats?.current_limits?.daily_limit || 0).format('0.00')}`}
                    secondary="하루 최대 사용 가능 금액"
                  />
                </ListItem>
                <Divider />
                <ListItem>
                  <ListItemText
                    primary={`월간 한도: $${numeral(stats?.current_limits?.monthly_limit || 0).format('0.00')}`}
                    secondary="한 달 최대 사용 가능 금액"
                  />
                </ListItem>
                <Divider />
                <ListItem>
                  <ListItemText
                    primary={`알림 임계치: ${((stats?.current_limits?.alert_threshold || 0) * 100).toFixed(0)}%`}
                    secondary="경고 알림이 발송되는 사용률"
                  />
                </ListItem>
              </List>
            </Grid>
          </Grid>
        </TabPanel>

        {/* 모델별 분석 탭 */}
        <TabPanel value={tabValue} index={2}>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <Typography variant="subtitle2" gutterBottom>
                모델별 사용량 (오늘)
              </Typography>
              <List dense>
                {Object.entries(todayUsage.model_usage || {}).map(([model, count]) => (
                  <Box key={model}>
                    <ListItem>
                      <ListItemText
                        primary={`${model}: ${numeral(count).format('0,0')}회`}
                        secondary={`비용: $${numeral(todayUsage.cost_by_model?.[model] || 0).format('0.00')}`}
                      />
                    </ListItem>
                    <Divider />
                  </Box>
                ))}
              </List>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="subtitle2" gutterBottom>
                엔드포인트별 사용량 (오늘)
              </Typography>
              <List dense>
                {Object.entries(todayUsage.endpoint_usage || {}).slice(0, 5).map(([endpoint, count]) => (
                  <Box key={endpoint}>
                    <ListItem>
                      <ListItemText
                        primary={`${endpoint.replace('/api/v1/', '')}`}
                        secondary={`${numeral(count).format('0,0')}회 호출`}
                      />
                    </ListItem>
                    <Divider />
                  </Box>
                ))}
              </List>
            </Grid>
          </Grid>
        </TabPanel>
      </CardContent>
    </Card>
  );
};