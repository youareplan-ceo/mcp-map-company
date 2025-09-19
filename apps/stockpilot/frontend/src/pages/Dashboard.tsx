/**
 * StockPilot AI 메인 대시보드 페이지
 * AI 투자 시그널, 시장 현황, 포트폴리오 요약 등을 표시
 */

import React, { useState, useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Paper,
  Chip,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Avatar,
  Divider,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Timeline as TimelineIcon,
  AccountBalance as PortfolioIcon,
  Article as NewsIcon,
  Refresh as RefreshIcon,
  MoreVert as MoreIcon,
  ArrowForward as ArrowForwardIcon
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell
} from 'recharts';

import StockSearchBar from '../components/common/StockSearchBar';
import { SystemStatusWidget } from '../components/monitoring/SystemStatusWidget';
import { UsageStatsWidget } from '../components/monitoring/UsageStatsWidget';
import { BatchStatusWidget } from '../components/monitoring/BatchStatusWidget';
import { USMarketOverview } from '../components/dashboard/USMarketOverview';
import { AISignalNotification } from '../components/dashboard/AISignalNotification';
import { MarketStatusIndicator } from '../components/common/MarketStatusIndicator';
import { 
  DashboardService, 
  SignalService, 
  PortfolioService, 
  NewsService,
  MarketService 
} from '../services/api';
import { 
  NumberUtils, 
  DateUtils, 
  SignalUtils, 
  MarketUtils 
} from '../utils';
import {
  InvestmentSignal,
  InvestmentSignalItem
} from '../types';
import { NewsItem } from '../types/news';
import { formatCurrency, formatPercent, US_MARKET, DEFAULT_MARKET, US_SAMPLE_STOCKS } from '../config/marketConfig';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [selectedTimeRange, setSelectedTimeRange] = useState('1D');

  // 대시보드 요약 데이터 조회
  const { data: dashboardSummary, isLoading: summaryLoading } = useQuery({
    queryKey: ['dashboardSummary'],
    queryFn: () => DashboardService.getDashboardSummary(),
    refetchInterval: 60000 // 1분마다 갱신
  });

  // 최신 AI 시그널 조회
  const { data: latestSignals, isLoading: signalsLoading } = useQuery({
    queryKey: ['latestSignals'],
    queryFn: () => SignalService.getSignals(1, 5),
    refetchInterval: 300000 // 5분마다 갱신
  });

  // 인기 종목 조회
  const { data: trendingStocks } = useQuery({
    queryKey: ['trendingStocks'],
    queryFn: () => DashboardService.getTrendingStocks(8),
    refetchInterval: 180000 // 3분마다 갱신
  });

  // 포트폴리오 요약 조회
  const { data: portfolios } = useQuery({
    queryKey: ['portfolios'],
    queryFn: () => PortfolioService.getPortfolios()
  });

  // 주요 뉴스 조회
  const { data: topNews } = useQuery({
    queryKey: ['topNews'],
    queryFn: () => DashboardService.getTopNews(6),
    refetchInterval: 600000 // 10분마다 갱신
  });

  // 시장 지수 조회
  const { data: marketIndices } = useQuery({
    queryKey: ['marketIndices'],
    queryFn: () => MarketService.getMarketIndices(),
    refetchInterval: 60000 // 1분마다 갱신
  });

  // 통계 카드 데이터
  const getStatsCards = () => [
    {
      title: 'AI 시그널',
      value: latestSignals?.data?.length || 0,
      suffix: '개',
      change: 5,
      changeLabel: '오늘',
      icon: <TimelineIcon />,
      color: 'primary',
      action: () => navigate('/signals')
    },
    {
      title: '관심 종목',
      value: dashboardSummary?.watchlistCount || 12,
      suffix: '종목',
      change: 2,
      changeLabel: '추가됨',
      icon: <TrendingUpIcon />,
      color: 'success',
      action: () => navigate('/watchlist')
    },
    {
      title: '포트폴리오',
      value: portfolios?.length || 1,
      suffix: '개',
      change: 0,
      changeLabel: '변화없음',
      icon: <PortfolioIcon />,
      color: 'info',
      action: () => navigate('/portfolio')
    },
    {
      title: '오늘 뉴스',
      value: topNews?.length || 0,
      suffix: '건',
      change: 8,
      changeLabel: '업데이트',
      icon: <NewsIcon />,
      color: 'warning',
      action: () => navigate('/news')
    }
  ];

  // 시그널 분포 데이터 (파이 차트용)
  const getSignalDistribution = () => {
    if (!latestSignals?.data) return [];

    const signalCounts = latestSignals.data.reduce((acc, signal) => {
      acc[signal.signal] = (acc[signal.signal] || 0) + 1;
      return acc;
    }, {} as Record<InvestmentSignal, number>);

    return Object.entries(signalCounts).map(([signal, count]) => ({
      name: SignalUtils.getSignalLabel(signal as InvestmentSignal),
      value: count,
      color: SignalUtils.getSignalColor(signal as InvestmentSignal)
    }));
  };

  // 시장 지수 차트 데이터
  const getMarketChartData = () => {
    return marketIndices?.history?.slice(-20)?.map((item: any, index: number) => ({
      time: index + 1,
      kospi: item.kospi || 2400,
      kosdaq: item.kosdaq || 800
    })) || [];
  };

  const COLORS = ['#d32f2f', '#f57c00', '#757575', '#1976d2', '#303f9f'];

  return (
    <Box>
      {/* 페이지 헤더 */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom fontWeight={700}>
          투자 대시보드
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          AI 기반 투자 시그널과 시장 현황을 한눈에 확인하세요
        </Typography>

        {/* 종목 검색 */}
        <Box sx={{ maxWidth: 600 }}>
          <StockSearchBar
            placeholder="종목명 또는 코드를 검색하여 분석 시작"
            size="medium"
          />
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* 통계 카드들 */}
        {getStatsCards().map((card, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card
              sx={{
                cursor: 'pointer',
                transition: 'all 0.2s ease-in-out',
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: 4
                }
              }}
              onClick={card.action}
            >
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Avatar
                    sx={{
                      bgcolor: `${card.color}.main`,
                      width: 48,
                      height: 48,
                      mr: 2
                    }}
                  >
                    {card.icon}
                  </Avatar>
                  <Box>
                    <Typography variant="h4" fontWeight={700}>
                      {card.value}
                      <Typography
                        component="span"
                        variant="h6"
                        color="text.secondary"
                        sx={{ ml: 0.5 }}
                      >
                        {card.suffix}
                      </Typography>
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {card.title}
                    </Typography>
                  </Box>
                </Box>
                
                {card.change !== 0 && (
                  <Chip
                    label={`${card.change > 0 ? '+' : ''}${card.change} ${card.changeLabel}`}
                    size="small"
                    color={card.change > 0 ? 'success' : 'default'}
                    variant="outlined"
                  />
                )}
              </CardContent>
            </Card>
          </Grid>
        ))}

        {/* 시장 지수 차트 */}
        <Grid item xs={12} lg={8}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Typography variant="h6" fontWeight={600}>
                  시장 지수 현황
                </Typography>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  {['1D', '1W', '1M'].map((range) => (
                    <Button
                      key={range}
                      size="small"
                      variant={selectedTimeRange === range ? 'contained' : 'outlined'}
                      onClick={() => setSelectedTimeRange(range)}
                    >
                      {range}
                    </Button>
                  ))}
                  <IconButton size="small">
                    <RefreshIcon />
                  </IconButton>
                </Box>
              </Box>

              <Box sx={{ height: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={getMarketChartData()}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="time" axisLine={false} tickLine={false} />
                    <YAxis axisLine={false} tickLine={false} />
                    <RechartsTooltip
                      contentStyle={{
                        backgroundColor: '#fff',
                        border: '1px solid #e0e0e0',
                        borderRadius: '8px'
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="kospi"
                      stroke="#1976d2"
                      strokeWidth={2}
                      dot={false}
                      name="코스피"
                    />
                    <Line
                      type="monotone"
                      dataKey="kosdaq"
                      stroke="#388e3c"
                      strokeWidth={2}
                      dot={false}
                      name="코스닥"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* 미국 시장 개요 */}
        <Grid item xs={12} lg={4}>
          <USMarketOverview />
        </Grid>
        
        {/* AI 투자 시그널 - 실시간 알림 */}
        <Grid item xs={12} md={6}>
          <AISignalNotification />
        </Grid>

        {/* AI 시그널 분포 */}
        <Grid item xs={12} lg={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" fontWeight={600} gutterBottom>
                AI 시그널 분포
              </Typography>
              
              <Box sx={{ height: 250, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={getSignalDistribution()}
                      cx="50%"
                      cy="50%"
                      innerRadius={40}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {getSignalDistribution().map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <RechartsTooltip />
                  </PieChart>
                </ResponsiveContainer>
              </Box>

              {/* 범례 */}
              <Box sx={{ mt: 2 }}>
                {getSignalDistribution().map((item, index) => (
                  <Box key={index} sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
                    <Box
                      sx={{
                        width: 12,
                        height: 12,
                        borderRadius: 1,
                        bgcolor: item.color,
                        mr: 1
                      }}
                    />
                    <Typography variant="body2">
                      {item.name}: {item.value}건
                    </Typography>
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* 최신 AI 시그널 */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" fontWeight={600}>
                  최신 AI 시그널
                </Typography>
                <Button
                  endIcon={<ArrowForwardIcon />}
                  onClick={() => navigate('/signals')}
                >
                  전체보기
                </Button>
              </Box>

              <List disablePadding>
                {latestSignals?.data?.slice(0, 4).map((signal: InvestmentSignalItem, index) => (
                  <React.Fragment key={signal.id}>
                    <ListItem
                      sx={{
                        cursor: 'pointer',
                        borderRadius: 1,
                        '&:hover': { bgcolor: 'action.hover' }
                      }}
                      onClick={() => navigate(`/analysis/${signal.symbol}`)}
                    >
                      <ListItemAvatar>
                        <Avatar
                          sx={{
                            bgcolor: SignalUtils.getSignalColor(signal.signal) + '20',
                            color: SignalUtils.getSignalColor(signal.signal),
                            width: 40,
                            height: 40
                          }}
                        >
                          {signal.signal === InvestmentSignal.BUY || 
                           signal.signal === InvestmentSignal.STRONG_BUY ? (
                            <TrendingUpIcon />
                          ) : (
                            <TrendingDownIcon />
                          )}
                        </Avatar>
                      </ListItemAvatar>
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="subtitle2" fontWeight={600}>
                              {signal.name}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              ({signal.symbol})
                            </Typography>
                            <Chip
                              label={SignalUtils.getSignalLabel(signal.signal)}
                              size="small"
                              sx={{
                                bgcolor: SignalUtils.getSignalColor(signal.signal) + '20',
                                color: SignalUtils.getSignalColor(signal.signal),
                                fontWeight: 600
                              }}
                            />
                          </Box>
                        }
                        secondary={
                          <Box sx={{ mt: 0.5 }}>
                            <Typography variant="body2" color="text.secondary">
                              신뢰도: {signal.confidence}% | 기대수익률: {NumberUtils.formatPercent(signal.expectedReturn)}
                            </Typography>
                          </Box>
                        }
                      />
                    </ListItem>
                    {index < 3 && <Divider />}
                  </React.Fragment>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* 주요 뉴스 */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" fontWeight={600}>
                  주요 뉴스
                </Typography>
                <Button
                  endIcon={<ArrowForwardIcon />}
                  onClick={() => navigate('/news')}
                >
                  전체보기
                </Button>
              </Box>

              <List disablePadding>
                {topNews?.slice(0, 4).map((news: NewsItem, index: number) => (
                  <React.Fragment key={news.id}>
                    <ListItem
                      sx={{
                        cursor: 'pointer',
                        borderRadius: 1,
                        '&:hover': { bgcolor: 'action.hover' },
                        alignItems: 'flex-start',
                        py: 2
                      }}
                      onClick={() => window.open(news.url, '_blank')}
                    >
                      <ListItemText
                        primary={
                          <Typography 
                            variant="subtitle2" 
                            fontWeight={600}
                            sx={{
                              display: '-webkit-box',
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: 'vertical',
                              overflow: 'hidden',
                              mb: 0.5
                            }}
                          >
                            {news.title}
                          </Typography>
                        }
                        secondary={
                          <Box>
                            <Typography 
                              variant="body2" 
                              color="text.secondary"
                              sx={{
                                display: '-webkit-box',
                                WebkitLineClamp: 2,
                                WebkitBoxOrient: 'vertical',
                                overflow: 'hidden',
                                mb: 1
                              }}
                            >
                              {news.summary}
                            </Typography>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Chip
                                label={news.sentiment === 'positive' ? '긍정' : news.sentiment === 'negative' ? '부정' : '중립'}
                                size="small"
                                color={
                                  news.sentiment === 'positive' ? 'success' :
                                  news.sentiment === 'negative' ? 'error' : 'default'
                                }
                                variant="outlined"
                              />
                              <Typography variant="caption" color="text.secondary">
                                {news.source} • {DateUtils.formatRelative(news.publishedAt)}
                              </Typography>
                            </Box>
                          </Box>
                        }
                      />
                    </ListItem>
                    {index < 3 && <Divider />}
                  </React.Fragment>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* 시스템 모니터링 섹션 */}
        <Grid item xs={12}>
          <Typography variant="h5" fontWeight={600} gutterBottom sx={{ mt: 4, mb: 2 }}>
            시스템 모니터링
          </Typography>
          <Grid container spacing={3}>
            {/* 시스템 상태 */}
            <Grid item xs={12} lg={4}>
              <SystemStatusWidget compact={false} />
            </Grid>
            
            {/* 사용량 통계 */}
            <Grid item xs={12} lg={4}>
              <UsageStatsWidget compact={false} />
            </Grid>
            
            {/* 배치 상태 */}
            <Grid item xs={12} lg={4}>
              <BatchStatusWidget compact={false} />
            </Grid>
          </Grid>
        </Grid>

        {/* 인기 종목 */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" fontWeight={600} gutterBottom>
                오늘의 인기 종목
              </Typography>
              
              <Grid container spacing={2}>
                {trendingStocks?.slice(0, 8).map((stock: any, index: number) => (
                  <Grid item xs={6} sm={4} md={3} lg={1.5} key={index}>
                    <Paper
                      sx={{
                        p: 2,
                        cursor: 'pointer',
                        transition: 'all 0.2s ease-in-out',
                        '&:hover': {
                          transform: 'translateY(-2px)',
                          boxShadow: 2
                        }
                      }}
                      onClick={() => navigate(`/analysis/${stock.symbol}`)}
                    >
                      <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                        {stock.name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary" display="block">
                        {stock.symbol}
                      </Typography>
                      <Typography variant="h6" fontWeight={700} sx={{ mt: 1 }}>
                        {NumberUtils.formatPrice(stock.price)}원
                      </Typography>
                      <Typography
                        variant="body2"
                        sx={{
                          color: MarketUtils.getPriceChangeColor(stock.changeRate),
                          fontWeight: 600
                        }}
                      >
                        {MarketUtils.formatChangeRate(stock.changeRate)}
                      </Typography>
                    </Paper>
                  </Grid>
                ))}
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;