/**
 * 배치 작업 상태 위젯 컴포넌트
 * 배치 작업 실행 상태 및 이력 모니터링
 */

import React, { useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Grid,
  Box,
  CircularProgress,
  Chip,
  Tooltip,
  IconButton,
  Alert,
  Tab,
  Tabs,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  LinearProgress,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  PlayArrow as PlayArrowIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Schedule as ScheduleIcon,
  Speed as SpeedIcon,
  Memory as MemoryIcon,
  Info as InfoIcon,
  LockOpen as LockOpenIcon
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format, formatDistanceToNow, parseISO } from 'date-fns';
import { ko } from 'date-fns/locale';
import { toast } from 'react-toastify';
import numeral from 'numeral';

import { API } from '../../services/api';
import { BatchJob, JobExecution, JobStatus, ExecutionStatsResponse } from '../../types';

interface BatchStatusWidgetProps {
  refreshInterval?: number;
  compact?: boolean;
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
      id={`batch-tabpanel-${index}`}
      aria-labelledby={`batch-tab-${index}`}
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

// 작업 상태별 설정
const getJobStatusConfig = (status: JobStatus) => {
  switch (status) {
    case JobStatus.SUCCESS:
      return { 
        color: 'success' as const, 
        icon: <CheckCircleIcon />, 
        label: '성공' 
      };
    case JobStatus.FAILED:
      return { 
        color: 'error' as const, 
        icon: <ErrorIcon />, 
        label: '실패' 
      };
    case JobStatus.RUNNING:
      return { 
        color: 'info' as const, 
        icon: <CircularProgress size={16} />, 
        label: '실행 중' 
      };
    case JobStatus.PENDING:
      return { 
        color: 'default' as const, 
        icon: <ScheduleIcon />, 
        label: '대기 중' 
      };
    case JobStatus.SKIPPED:
      return { 
        color: 'warning' as const, 
        icon: <WarningIcon />, 
        label: '건너뜀' 
      };
    default:
      return { 
        color: 'default' as const, 
        icon: <InfoIcon />, 
        label: '알 수 없음' 
      };
  }
};

export const BatchStatusWidget: React.FC<BatchStatusWidgetProps> = ({
  refreshInterval = 30000, // 30초 기본값
  compact = false
}) => {
  const [isManualRefreshing, setIsManualRefreshing] = useState(false);
  const [tabValue, setTabValue] = useState(0);
  const [lockReleaseDialog, setLockReleaseDialog] = useState<{
    open: boolean;
    jobId: string;
    jobName: string;
  }>({ open: false, jobId: '', jobName: '' });

  const queryClient = useQueryClient();

  // 배치 작업 목록 조회
  const { data: batchJobs, isLoading: jobsLoading } = useQuery({
    queryKey: ['batch-jobs'],
    queryFn: API.Batch.getBatchJobs,
    refetchInterval: refreshInterval,
    staleTime: 15000,
    retry: 2
  });

  // 최근 실행 이력 조회
  const { data: recentExecutions, isLoading: executionsLoading } = useQuery({
    queryKey: ['batch-executions'],
    queryFn: () => API.Batch.getRecentExecutions(10),
    refetchInterval: refreshInterval,
    staleTime: 15000,
    retry: 2
  });

  // 실행 통계 조회
  const { data: executionStats, isLoading: statsLoading } = useQuery({
    queryKey: ['batch-execution-stats'],
    queryFn: () => API.Batch.getExecutionStats(),
    refetchInterval: refreshInterval * 2, // 1분마다
    staleTime: 30000,
    retry: 2
  });

  // 작업 실행 뮤테이션
  const executeJobMutation = useMutation({
    mutationFn: ({ jobId, force }: { jobId: string; force: boolean }) =>
      API.Batch.executeJob(jobId, force),
    onSuccess: (_, variables) => {
      toast.success(`배치 작업 "${variables.jobId}" 실행이 시작되었습니다.`);
      queryClient.invalidateQueries({ queryKey: ['batch-jobs'] });
      queryClient.invalidateQueries({ queryKey: ['batch-executions'] });
    },
    onError: (error: any) => {
      toast.error(`배치 작업 실행 실패: ${error.message}`);
    }
  });

  // 잠금 해제 뮤테이션
  const releaseLockMutation = useMutation({
    mutationFn: ({ jobId, reason }: { jobId: string; reason: string }) =>
      API.Batch.forceReleaseLock(jobId, reason),
    onSuccess: (_, variables) => {
      toast.success(`잠금이 해제되었습니다: ${variables.jobId}`);
      setLockReleaseDialog({ open: false, jobId: '', jobName: '' });
      queryClient.invalidateQueries({ queryKey: ['batch-jobs'] });
    },
    onError: (error: any) => {
      toast.error(`잠금 해제 실패: ${error.message}`);
    }
  });

  // 수동 새로고침
  const handleManualRefresh = async () => {
    setIsManualRefreshing(true);
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['batch-jobs'] }),
      queryClient.invalidateQueries({ queryKey: ['batch-executions'] }),
      queryClient.invalidateQueries({ queryKey: ['batch-execution-stats'] })
    ]);
    setIsManualRefreshing(false);
  };

  // 탭 변경 핸들러
  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  // 작업 실행 핸들러
  const handleExecuteJob = (jobId: string, force: boolean = false) => {
    executeJobMutation.mutate({ jobId, force });
  };

  // 잠금 해제 다이얼로그 핸들러
  const handleLockReleaseDialog = (jobId: string, jobName: string) => {
    setLockReleaseDialog({ open: true, jobId, jobName });
  };

  const handleReleaseLock = () => {
    if (lockReleaseDialog.jobId) {
      releaseLockMutation.mutate({ 
        jobId: lockReleaseDialog.jobId, 
        reason: '수동 해제' 
      });
    }
  };

  // 로딩 중 표시
  if ((jobsLoading || executionsLoading || statsLoading) && !batchJobs && !recentExecutions && !executionStats) {
    return (
      <Card>
        <CardContent>
          <Box display="flex" alignItems="center" justifyContent="center" minHeight={100}>
            <CircularProgress size={24} />
            <Typography variant="body2" sx={{ ml: 2 }}>
              배치 상태 로딩 중...
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  const jobs = (batchJobs || []) as BatchJob[];
  const executions = (recentExecutions?.executions || []) as JobExecution[];
  const stats = executionStats as ExecutionStatsResponse;

  // 컴팩트 모드
  if (compact) {
    const runningJobs = executions.filter(ex => ex.status === JobStatus.RUNNING);
    const recentFailures = executions.slice(0, 5).filter(ex => ex.status === JobStatus.FAILED);
    
    return (
      <Card>
        <CardContent sx={{ p: 2 }}>
          <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
            <Typography variant="subtitle2">
              배치 작업
            </Typography>
            <IconButton 
              size="small" 
              onClick={handleManualRefresh} 
              disabled={isManualRefreshing}
            >
              <RefreshIcon fontSize="small" />
            </IconButton>
          </Box>

          <Grid container spacing={2}>
            <Grid item xs={6}>
              <Box textAlign="center">
                <Typography variant="h6" color={runningJobs.length > 0 ? 'info.main' : 'text.primary'}>
                  {runningJobs.length}
                </Typography>
                <Typography variant="caption" color="textSecondary">
                  실행 중
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={6}>
              <Box textAlign="center">
                <Typography variant="h6" color={recentFailures.length > 0 ? 'error.main' : 'success.main'}>
                  {recentFailures.length}
                </Typography>
                <Typography variant="caption" color="textSecondary">
                  최근 실패
                </Typography>
              </Box>
            </Grid>
          </Grid>

          {stats && (
            <Box mt={2}>
              <LinearProgress
                variant="determinate"
                value={stats.success_rate}
                color={stats.success_rate >= 90 ? 'success' : stats.success_rate >= 70 ? 'warning' : 'error'}
                sx={{ height: 6, borderRadius: 1 }}
              />
              <Typography variant="caption" color="textSecondary" display="block" textAlign="center" mt={0.5}>
                성공률: {stats.success_rate.toFixed(1)}%
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>
    );
  }

  // 전체 모드
  return (
    <>
      <Card>
        <CardContent>
          {/* 헤더 */}
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6" component="h3">
              배치 작업 상태
            </Typography>
            <IconButton 
              size="small" 
              onClick={handleManualRefresh} 
              disabled={isManualRefreshing}
            >
              <RefreshIcon fontSize="small" />
            </IconButton>
          </Box>

          {/* 탭 */}
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs value={tabValue} onChange={handleTabChange} aria-label="batch status tabs">
              <Tab label="작업 목록" />
              <Tab label="최근 실행" />
              <Tab label="통계" />
            </Tabs>
          </Box>

          {/* 작업 목록 탭 */}
          <TabPanel value={tabValue} index={0}>
            <List>
              {jobs.map((job, index) => {
                const statusConfig = getJobStatusConfig(job.last_status as JobStatus);
                return (
                  <Box key={job.job_id}>
                    <ListItem>
                      <ListItemIcon>
                        <Box sx={{ color: `${statusConfig.color}.main` }}>
                          {statusConfig.icon}
                        </Box>
                      </ListItemIcon>
                      <ListItemText
                        primary={
                          <Box display="flex" alignItems="center" justifyContent="space-between">
                            <Typography variant="body1" fontWeight="medium">
                              {job.name}
                            </Typography>
                            <Box display="flex" alignItems="center" gap={1}>
                              <Chip
                                label={statusConfig.label}
                                color={statusConfig.color}
                                size="small"
                                variant="outlined"
                              />
                              {job.enabled && (
                                <Button
                                  size="small"
                                  startIcon={<PlayArrowIcon />}
                                  onClick={() => handleExecuteJob(job.job_id)}
                                  disabled={job.last_status === JobStatus.RUNNING || executeJobMutation.isPending}
                                >
                                  실행
                                </Button>
                              )}
                              {job.last_status === JobStatus.RUNNING && (
                                <Button
                                  size="small"
                                  startIcon={<LockOpenIcon />}
                                  onClick={() => handleLockReleaseDialog(job.job_id, job.name)}
                                  color="warning"
                                  disabled={releaseLockMutation.isPending}
                                >
                                  잠금해제
                                </Button>
                              )}
                            </Box>
                          </Box>
                        }
                        secondary={
                          <Box>
                            <Typography variant="body2" color="textSecondary">
                              {job.description}
                            </Typography>
                            <Box display="flex" alignItems="center" gap={2} mt={0.5}>
                              <Typography variant="caption">
                                우선순위: {job.priority}
                              </Typography>
                              <Typography variant="caption">
                                재시도: {job.max_retries}회
                              </Typography>
                              <Typography variant="caption">
                                활성화: {job.enabled ? '예' : '아니오'}
                              </Typography>
                              {job.last_run && (
                                <Typography variant="caption">
                                  마지막 실행: {formatDistanceToNow(parseISO(job.last_run), { 
                                    addSuffix: true, 
                                    locale: ko 
                                  })}
                                </Typography>
                              )}
                            </Box>
                          </Box>
                        }
                      />
                    </ListItem>
                    {index < jobs.length - 1 && <Divider />}
                  </Box>
                );
              })}
            </List>
          </TabPanel>

          {/* 최근 실행 탭 */}
          <TabPanel value={tabValue} index={1}>
            <List>
              {executions.map((execution, index) => {
                const statusConfig = getJobStatusConfig(execution.status);
                return (
                  <Box key={execution.execution_id}>
                    <ListItem>
                      <ListItemIcon>
                        <Box sx={{ color: `${statusConfig.color}.main` }}>
                          {statusConfig.icon}
                        </Box>
                      </ListItemIcon>
                      <ListItemText
                        primary={
                          <Box display="flex" alignItems="center" justifyContent="space-between">
                            <Typography variant="body1" fontWeight="medium">
                              {execution.job_name}
                            </Typography>
                            <Chip
                              label={statusConfig.label}
                              color={statusConfig.color}
                              size="small"
                              variant="filled"
                            />
                          </Box>
                        }
                        secondary={
                          <Box>
                            {execution.error_message && (
                              <Typography variant="body2" color="error" gutterBottom>
                                오류: {execution.error_message}
                              </Typography>
                            )}
                            <Grid container spacing={2} sx={{ mt: 0.5 }}>
                              <Grid item xs={12} sm={6}>
                                <Typography variant="caption" color="textSecondary">
                                  시작: {execution.start_time ? format(parseISO(execution.start_time), 'MM/dd HH:mm:ss', { locale: ko }) : '-'}
                                </Typography>
                              </Grid>
                              <Grid item xs={12} sm={6}>
                                <Typography variant="caption" color="textSecondary">
                                  소요시간: {execution.duration ? `${execution.duration.toFixed(1)}초` : '-'}
                                </Typography>
                              </Grid>
                              {execution.items_processed && (
                                <Grid item xs={12} sm={6}>
                                  <Typography variant="caption" color="textSecondary">
                                    처리건수: {numeral(execution.items_processed).format('0,0')}
                                  </Typography>
                                </Grid>
                              )}
                              {execution.memory_peak_mb && (
                                <Grid item xs={12} sm={6}>
                                  <Typography variant="caption" color="textSecondary">
                                    최대메모리: {numeral(execution.memory_peak_mb).format('0.0')}MB
                                  </Typography>
                                </Grid>
                              )}
                            </Grid>
                          </Box>
                        }
                      />
                    </ListItem>
                    {index < executions.length - 1 && <Divider />}
                  </Box>
                );
              })}
            </List>
          </TabPanel>

          {/* 통계 탭 */}
          <TabPanel value={tabValue} index={2}>
            {stats ? (
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" gutterBottom>
                    실행 통계 (최근 7일)
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Box textAlign="center" p={2} bgcolor="success.50" borderRadius={1}>
                        <CheckCircleIcon color="success" />
                        <Typography variant="h6" color="success.main">
                          {stats.success}
                        </Typography>
                        <Typography variant="caption">성공</Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={6}>
                      <Box textAlign="center" p={2} bgcolor="error.50" borderRadius={1}>
                        <ErrorIcon color="error" />
                        <Typography variant="h6" color="error.main">
                          {stats.failed}
                        </Typography>
                        <Typography variant="caption">실패</Typography>
                      </Box>
                    </Grid>
                  </Grid>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" gutterBottom>
                    성능 지표
                  </Typography>
                  <List dense>
                    <ListItem>
                      <ListItemIcon>
                        <SpeedIcon />
                      </ListItemIcon>
                      <ListItemText
                        primary={`성공률: ${stats.success_rate.toFixed(1)}%`}
                        secondary={`총 ${stats.total}회 실행`}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon>
                        <ScheduleIcon />
                      </ListItemIcon>
                      <ListItemText
                        primary={`평균 실행시간: ${stats.avg_duration_seconds.toFixed(1)}초`}
                        secondary="작업별 평균 소요시간"
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon>
                        <MemoryIcon />
                      </ListItemIcon>
                      <ListItemText
                        primary={`평균 메모리: ${stats.avg_memory_peak_mb.toFixed(1)}MB`}
                        secondary="최대 메모리 사용량 평균"
                      />
                    </ListItem>
                  </List>
                </Grid>
              </Grid>
            ) : (
              <Alert severity="info">통계 데이터를 불러오는 중입니다...</Alert>
            )}
          </TabPanel>
        </CardContent>
      </Card>

      {/* 잠금 해제 확인 다이얼로그 */}
      <Dialog open={lockReleaseDialog.open} onClose={() => setLockReleaseDialog({ open: false, jobId: '', jobName: '' })}>
        <DialogTitle>잠금 해제 확인</DialogTitle>
        <DialogContent>
          <Typography>
            "{lockReleaseDialog.jobName}" 작업의 잠금을 강제로 해제하시겠습니까?
          </Typography>
          <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
            실행 중인 작업이 있다면 예상치 못한 문제가 발생할 수 있습니다.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button 
            onClick={() => setLockReleaseDialog({ open: false, jobId: '', jobName: '' })}
            disabled={releaseLockMutation.isPending}
          >
            취소
          </Button>
          <Button 
            onClick={handleReleaseLock} 
            color="warning"
            disabled={releaseLockMutation.isPending}
          >
            {releaseLockMutation.isPending ? '해제 중...' : '잠금 해제'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};