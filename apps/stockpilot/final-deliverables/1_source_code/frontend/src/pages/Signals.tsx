/**
 * AI 투자 시그널 페이지
 * 실시간 AI 분석 결과와 투자 추천 시그널 제공
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  Chip,
  Button,
  ButtonGroup,
  TextField,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Tab,
  Tabs,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  LinearProgress
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Timeline as TimelineIcon,
  Refresh as RefreshIcon,
  FilterList as FilterIcon,
  Info as InfoIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon,
  Notifications as NotificationsIcon,
  Settings as SettingsIcon
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { SignalService } from '../services/api';
import { InvestmentSignal, SignalStrength, Market, MarketType, InvestmentSignalItem, SignalAlert } from '../types';
import { SignalUtils, NumberUtils, DateUtils, MarketUtils } from '../utils';
import { webSocketService } from '../services/websocket';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
  <div hidden={value !== index} style={{ paddingTop: 16 }}>
    {value === index && children}
  </div>
);

interface SignalFilters {
  signal?: InvestmentSignal;
  market?: MarketType;
  strength?: SignalStrength;
  period: '1d' | '3d' | '1w' | '1m';
}

const Signals: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [filters, setFilters] = useState<SignalFilters>({ period: '1d' });
  const [selectedSignal, setSelectedSignal] = useState<InvestmentSignalItem | null>(null);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [watchlist, setWatchlist] = useState<Set<string>>(new Set());

  const queryClient = useQueryClient();

  // AI 시그널 목록 조회
  const { data: signalsData, isLoading, refetch } = useQuery({
    queryKey: ['aiSignals', filters, page, rowsPerPage],
    queryFn: () => SignalService.getSignals(
      page + 1, // API는 1-based pagination
      rowsPerPage,
      {
        markets: filters.market ? [filters.market as any] : undefined,
        signals: filters.signal ? [filters.signal] : undefined,
        confidenceMin: filters.strength === SignalStrength.STRONG ? 80 : 
                      filters.strength === SignalStrength.MODERATE ? 50 : 
                      filters.strength === SignalStrength.WEAK ? 20 : undefined
      }
    ),
    refetchInterval: 30000 // 30초마다 갱신
  });

  // 시그널 통계 데이터
  const { data: signalStats } = useQuery({
    queryKey: ['signalStats', filters.period],
    queryFn: () => SignalService.getSignalStats(filters.period),
    refetchInterval: 60000
  });

  // 알림 설정 조회
  const { data: alertSettings = [] } = useQuery({
    queryKey: ['signalAlerts'],
    queryFn: () => SignalService.getAlertSettings()
  });

  // 시그널 즐겨찾기 뮤테이션
  const toggleWatchlistMutation = useMutation({
    mutationFn: ({ symbol, action }: { symbol: string; action: 'add' | 'remove' }) =>
      SignalService.toggleWatchlist(symbol, action),
    onSuccess: (_, variables) => {
      const newWatchlist = new Set(watchlist);
      if (variables.action === 'add') {
        newWatchlist.add(variables.symbol);
      } else {
        newWatchlist.delete(variables.symbol);
      }
      setWatchlist(newWatchlist);
    }
  });

  // 알림 생성 뮤테이션
  const createAlertMutation = useMutation({
    mutationFn: (alert: Omit<SignalAlert, 'id' | 'createdAt'>) =>
      SignalService.createAlert(alert),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['signalAlerts'] });
    }
  });

  // WebSocket 연결 및 실시간 시그널 업데이트
  useEffect(() => {
    // 시그널 업데이트 구독
    const handleSignalUpdate = (data: any) => {
      queryClient.invalidateQueries({ queryKey: ['aiSignals'] });
      queryClient.invalidateQueries({ queryKey: ['signalStats'] });
    };

    webSocketService.on('analysis_update', handleSignalUpdate);

    return () => {
      webSocketService.off('analysis_update', handleSignalUpdate);
    };
  }, [queryClient]);

  // 시그널 통계 카드 데이터
  const statsCards = [
    {
      title: '총 시그널',
      value: signalStats?.totalSignals || 0,
      change: signalStats?.totalChange || 0,
      icon: <TimelineIcon />
    },
    {
      title: '매수 시그널',
      value: signalStats?.buySignals || 0,
      change: signalStats?.buyChange || 0,
      icon: <TrendingUpIcon />,
      color: 'success.main'
    },
    {
      title: '매도 시그널',
      value: signalStats?.sellSignals || 0,
      change: signalStats?.sellChange || 0,
      icon: <TrendingDownIcon />,
      color: 'error.main'
    },
    {
      title: '평균 신뢰도',
      value: signalStats?.averageConfidence ? `${NumberUtils.formatPercent(signalStats.averageConfidence)}%` : '-',
      change: signalStats?.confidenceChange || 0,
      icon: <StarIcon />
    }
  ];

  const handleFilterChange = (key: keyof SignalFilters, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPage(0);
  };

  const handleSignalDetail = (signal: InvestmentSignalItem) => {
    setSelectedSignal(signal);
    setDetailDialogOpen(true);
  };

  const handleToggleWatchlist = (symbol: string) => {
    const action = watchlist.has(symbol) ? 'remove' : 'add';
    toggleWatchlistMutation.mutate({ symbol, action });
  };

  return (
    <Box>
      {/* 헤더 */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" component="h1" fontWeight="bold">
          AI 투자 시그널
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={() => refetch()}
          >
            새로고침
          </Button>
          <Button
            variant="outlined"
            startIcon={<SettingsIcon />}
          >
            알림 설정
          </Button>
        </Box>
      </Box>

      {/* 통계 카드들 */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {statsCards.map((card, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box>
                    <Typography color="text.secondary" variant="body2" sx={{ mb: 1 }}>
                      {card.title}
                    </Typography>
                    <Typography variant="h5" fontWeight="bold">
                      {card.value}
                    </Typography>
                    {card.change !== 0 && (
                      <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                        {card.change > 0 ? (
                          <TrendingUpIcon sx={{ fontSize: 16, color: 'success.main', mr: 0.5 }} />
                        ) : (
                          <TrendingDownIcon sx={{ fontSize: 16, color: 'error.main', mr: 0.5 }} />
                        )}
                        <Typography
                          variant="body2"
                          sx={{
                            color: card.change > 0 ? 'success.main' : 'error.main',
                            fontWeight: 500
                          }}
                        >
                          {Math.abs(card.change)}
                        </Typography>
                      </Box>
                    )}
                  </Box>
                  <Box sx={{ color: card.color || 'primary.main' }}>
                    {card.icon}
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* 필터 및 탭 */}
      <Paper sx={{ mb: 3 }}>
        {/* 필터 바 */}
        <Box sx={{ p: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
          <Grid container spacing={2} alignItems="center">
            <Grid item>
              <TextField
                select
                size="small"
                label="시그널 타입"
                value={filters.signal || ''}
                onChange={(e) => handleFilterChange('signal', e.target.value || undefined)}
                sx={{ minWidth: 120 }}
              >
                <MenuItem value="">전체</MenuItem>
                <MenuItem value={InvestmentSignal.STRONG_BUY}>강력 매수</MenuItem>
                <MenuItem value={InvestmentSignal.BUY}>매수</MenuItem>
                <MenuItem value={InvestmentSignal.HOLD}>보유</MenuItem>
                <MenuItem value={InvestmentSignal.SELL}>매도</MenuItem>
                <MenuItem value={InvestmentSignal.STRONG_SELL}>강력 매도</MenuItem>
              </TextField>
            </Grid>
            <Grid item>
              <TextField
                select
                size="small"
                label="시장"
                value={filters.market || ''}
                onChange={(e) => handleFilterChange('market', e.target.value || undefined)}
                sx={{ minWidth: 100 }}
              >
                <MenuItem value="">전체</MenuItem>
                <MenuItem value={Market.KOSPI}>KOSPI</MenuItem>
                <MenuItem value={Market.KOSDAQ}>KOSDAQ</MenuItem>
                <MenuItem value={Market.KONEX}>KONEX</MenuItem>
              </TextField>
            </Grid>
            <Grid item>
              <TextField
                select
                size="small"
                label="신뢰도"
                value={filters.strength || ''}
                onChange={(e) => handleFilterChange('strength', e.target.value || undefined)}
                sx={{ minWidth: 100 }}
              >
                <MenuItem value="">전체</MenuItem>
                <MenuItem value={SignalStrength.STRONG}>높음</MenuItem>
                <MenuItem value={SignalStrength.MODERATE}>보통</MenuItem>
                <MenuItem value={SignalStrength.WEAK}>낮음</MenuItem>
              </TextField>
            </Grid>
            <Grid item>
              <ButtonGroup size="small">
                {(['1d', '3d', '1w', '1m'] as const).map((period) => (
                  <Button
                    key={period}
                    variant={filters.period === period ? 'contained' : 'outlined'}
                    onClick={() => handleFilterChange('period', period)}
                  >
                    {period === '1d' ? '1일' : period === '3d' ? '3일' : period === '1w' ? '1주' : '1개월'}
                  </Button>
                ))}
              </ButtonGroup>
            </Grid>
          </Grid>
        </Box>

        {/* 탭 */}
        <Tabs
          value={tabValue}
          onChange={(_, newValue) => setTabValue(newValue)}
          indicatorColor="primary"
          textColor="primary"
        >
          <Tab label="전체 시그널" />
          <Tab label="관심 종목" />
          <Tab label="알림 내역" />
        </Tabs>

        {/* 전체 시그널 탭 */}
        <TabPanel value={tabValue} index={0}>
          {isLoading ? (
            <LinearProgress />
          ) : (
            <>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>종목</TableCell>
                      <TableCell align="center">시그널</TableCell>
                      <TableCell align="center">신뢰도</TableCell>
                      <TableCell align="right">현재가</TableCell>
                      <TableCell align="right">목표가</TableCell>
                      <TableCell align="right">기대수익률</TableCell>
                      <TableCell align="center">생성시간</TableCell>
                      <TableCell align="center">액션</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {signalsData?.data.map((signal: any) => (
                      <TableRow key={signal.id} hover>
                        <TableCell>
                          <Box>
                            <Typography variant="subtitle2" fontWeight={600}>
                              {signal.name}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {signal.symbol} • {MarketUtils.getMarketLabel(signal.market)}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell align="center">
                          <Chip
                            label={SignalUtils.getSignalLabel(signal.signal)}
                            color={SignalUtils.getSignalColor(signal.signal) as any}
                            size="small"
                            sx={{ fontWeight: 600 }}
                          />
                        </TableCell>
                        <TableCell align="center">
                          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <Typography variant="body2" fontWeight={500}>
                              {NumberUtils.formatPercent(signal.confidence)}%
                            </Typography>
                            {signal.confidence > 80 && (
                              <StarIcon sx={{ fontSize: 16, color: 'warning.main', ml: 0.5 }} />
                            )}
                          </Box>
                        </TableCell>
                        <TableCell align="right">
                          {NumberUtils.formatPrice(signal.currentPrice)}원
                        </TableCell>
                        <TableCell align="right">
                          {signal.targetPrice ? `${NumberUtils.formatPrice(signal.targetPrice)}원` : '-'}
                        </TableCell>
                        <TableCell align="right">
                          {signal.expectedReturn ? (
                            <Typography
                              sx={{
                                color: MarketUtils.getPriceChangeColor(signal.expectedReturn),
                                fontWeight: 500
                              }}
                            >
                              {NumberUtils.formatPercent(signal.expectedReturn)}%
                            </Typography>
                          ) : '-'}
                        </TableCell>
                        <TableCell align="center">
                          <Typography variant="body2">
                            {DateUtils.formatRelativeTime(new Date(signal.generatedAt))}
                          </Typography>
                        </TableCell>
                        <TableCell align="center">
                          <IconButton
                            size="small"
                            onClick={() => handleToggleWatchlist(signal.symbol)}
                            color={watchlist.has(signal.symbol) ? 'primary' : 'default'}
                          >
                            {watchlist.has(signal.symbol) ? <StarIcon /> : <StarBorderIcon />}
                          </IconButton>
                          <IconButton
                            size="small"
                            onClick={() => handleSignalDetail(signal)}
                          >
                            <InfoIcon />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
              
              <TablePagination
                component="div"
                count={signalsData?.pagination?.total || 0}
                page={page}
                onPageChange={(_, newPage) => setPage(newPage)}
                rowsPerPage={rowsPerPage}
                onRowsPerPageChange={(e) => {
                  setRowsPerPage(parseInt(e.target.value, 10));
                  setPage(0);
                }}
                rowsPerPageOptions={[10, 25, 50, 100]}
                labelRowsPerPage="페이지당 행 수:"
                labelDisplayedRows={({ from, to, count }) => `${from}-${to} / 총 ${count}개`}
              />
            </>
          )}
        </TabPanel>

        {/* 관심 종목 탭 */}
        <TabPanel value={tabValue} index={1}>
          <Box sx={{ p: 2 }}>
            {watchlist.size > 0 ? (
              <Typography variant="body2">
                관심 종목: {Array.from(watchlist).join(', ')}
              </Typography>
            ) : (
              <Alert severity="info">
                관심 종목이 없습니다. 시그널 목록에서 별표를 클릭하여 관심 종목을 추가하세요.
              </Alert>
            )}
          </Box>
        </TabPanel>

        {/* 알림 내역 탭 */}
        <TabPanel value={tabValue} index={2}>
          <Box>
            {alertSettings.length > 0 ? (
              <List>
                {alertSettings.map((alert, index) => (
                  <React.Fragment key={alert.id}>
                    <ListItem>
                      <ListItemIcon>
                        <NotificationsIcon color="primary" />
                      </ListItemIcon>
                      <ListItemText
                        primary={`${alert.symbol} - ${SignalUtils.getSignalLabel(alert.signal)} 시그널`}
                        secondary={`신뢰도 ${alert.minConfidence}% 이상 • 생성: ${new Date(alert.createdAt).toLocaleString()}`}
                      />
                    </ListItem>
                    {index < alertSettings.length - 1 && <Divider />}
                  </React.Fragment>
                ))}
              </List>
            ) : (
              <Alert severity="info" sx={{ m: 2 }}>
                설정된 알림이 없습니다.
              </Alert>
            )}
          </Box>
        </TabPanel>
      </Paper>

      {/* 시그널 상세 다이얼로그 */}
      <Dialog
        open={detailDialogOpen}
        onClose={() => setDetailDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {selectedSignal && (
            <Box>
              <Typography variant="h6">
                {selectedSignal.name} ({selectedSignal.symbol})
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
                <Chip
                  label={SignalUtils.getSignalLabel(selectedSignal.signal)}
                  color={SignalUtils.getSignalColor(selectedSignal.signal) as any}
                  size="small"
                />
                <Typography variant="body2" color="text.secondary">
                  신뢰도: {NumberUtils.formatPercent(selectedSignal.confidence)}%
                </Typography>
              </Box>
            </Box>
          )}
        </DialogTitle>
        <DialogContent>
          {selectedSignal && (
            <Box>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>
                AI 분석 요약
              </Typography>
              <Typography variant="body2" sx={{ mb: 2 }}>
                {selectedSignal.reasoning || '분석 내용이 없습니다.'}
              </Typography>
              
              <Grid container spacing={2} sx={{ mb: 2 }}>
                <Grid item xs={6}>
                  <Paper sx={{ p: 2 }}>
                    <Typography variant="caption" color="text.secondary">
                      현재가
                    </Typography>
                    <Typography variant="h6">
                      {NumberUtils.formatPrice(selectedSignal.currentPrice)}원
                    </Typography>
                  </Paper>
                </Grid>
                <Grid item xs={6}>
                  <Paper sx={{ p: 2 }}>
                    <Typography variant="caption" color="text.secondary">
                      목표가
                    </Typography>
                    <Typography variant="h6">
                      {selectedSignal.targetPrice ? `${NumberUtils.formatPrice(selectedSignal.targetPrice)}원` : '-'}
                    </Typography>
                  </Paper>
                </Grid>
              </Grid>

              <Typography variant="caption" color="text.secondary">
                생성 시간: {new Date(selectedSignal.generatedAt).toLocaleString()}
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailDialogOpen(false)}>
            닫기
          </Button>
          {selectedSignal && (
            <Button
              variant="contained"
              onClick={() => handleToggleWatchlist(selectedSignal.symbol)}
            >
              {watchlist.has(selectedSignal.symbol) ? '관심종목 제거' : '관심종목 추가'}
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Signals;