/**
 * 개별 종목 분석 페이지
 * AI 분석 결과, 실시간 차트, 뉴스 분석 등을 종합적으로 표시
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Paper,
  Chip,
  Button,
  IconButton,
  Avatar,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Divider,
  Alert,
  Skeleton,
  Tab,
  Tabs,
  CircularProgress,
  LinearProgress
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Add as AddIcon,
  Remove as RemoveIcon,
  Refresh as RefreshIcon,
  Share as ShareIcon,
  Bookmark as BookmarkIcon,
  BookmarkBorder as BookmarkBorderIcon,
  Psychology as AIIcon,
  Timeline as ChartIcon,
  Article as NewsIcon,
  Analytics as TechnicalIcon
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar
} from 'recharts';

import { 
  StockService, 
  PortfolioService, 
  NewsService 
} from '../services/api';
import { useWebSocket } from '../services/websocket';
import {
  StockInfo,
  StockPrice,
  AIAnalysis,
  NewsSentiment,
  ChartDataPoint,
  TechnicalIndicators,
  RealTimePriceUpdate
} from '../types';
import {
  NumberUtils,
  DateUtils,
  SignalUtils,
  MarketUtils,
  StringUtils
} from '../utils';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel({ children, value, index, ...other }: TabPanelProps) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      {...other}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

const StockAnalysis: React.FC = () => {
  const { symbol } = useParams<{ symbol: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { service: wsService, subscribePrices, unsubscribePrices, on, off } = useWebSocket();
  
  const [currentTab, setCurrentTab] = useState(0);
  const [chartInterval, setChartInterval] = useState('1d');
  const [isWatchlisted, setIsWatchlisted] = useState(false);
  const [realtimePrice, setRealtimePrice] = useState<StockPrice | null>(null);

  // 종목 기본 정보 조회
  const { data: stockInfo, isLoading: infoLoading, error: infoError } = useQuery({
    queryKey: ['stockInfo', symbol],
    queryFn: () => StockService.getStockInfo(symbol!),
    enabled: !!symbol,
    staleTime: 300000 // 5분간 캐시 유지
  });

  // 실시간 주가 조회
  const { data: stockPrice, isLoading: priceLoading } = useQuery({
    queryKey: ['stockPrice', symbol],
    queryFn: () => StockService.getStockPrice(symbol!),
    enabled: !!symbol,
    refetchInterval: 5000, // 5초마다 갱신
    staleTime: 0
  });

  // AI 분석 결과 조회
  const { data: aiAnalysis, isLoading: analysisLoading, refetch: refetchAnalysis } = useQuery({
    queryKey: ['aiAnalysis', symbol],
    queryFn: () => StockService.getAIAnalysis(symbol!),
    enabled: !!symbol,
    staleTime: 300000 // 5분간 캐시 유지
  });

  // 차트 데이터 조회
  const { data: chartData, isLoading: chartLoading } = useQuery({
    queryKey: ['chartData', symbol, chartInterval],
    queryFn: () => StockService.getChartData(symbol!, chartInterval, 100),
    enabled: !!symbol,
    staleTime: 60000 // 1분간 캐시 유지
  });

  // 기술적 지표 조회
  const { data: technicalIndicators } = useQuery({
    queryKey: ['technicalIndicators', symbol],
    queryFn: () => StockService.getTechnicalIndicators(symbol!),
    enabled: !!symbol,
    staleTime: 300000
  });

  // 종목 뉴스 조회
  const { data: stockNews } = useQuery({
    queryKey: ['stockNews', symbol],
    queryFn: () => StockService.getStockNews(symbol!, 20),
    enabled: !!symbol,
    staleTime: 180000 // 3분간 캐시 유지
  });

  // 포트폴리오에 종목 추가/제거
  const addToPortfolio = useMutation({
    mutationFn: ({ portfolioId, quantity, price }: any) =>
      PortfolioService.addStockToPortfolio(portfolioId, symbol!, quantity, price),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] });
    }
  });

  // WebSocket 실시간 주가 업데이트 구독
  useEffect(() => {
    if (!symbol) return;

    // 실시간 주가 구독
    subscribePrices([symbol]);

    // 실시간 주가 업데이트 리스너
    const handlePriceUpdate = (data: RealTimePriceUpdate) => {
      if (data.symbol === symbol) {
        setRealtimePrice(prevPrice => ({
          ...prevPrice!,
          currentPrice: data.currentPrice,
          change: data.change,
          changeRate: data.changeRate,
          volume: data.volume,
          updatedAt: data.timestamp
        }));
      }
    };

    on('price_update', handlePriceUpdate);

    return () => {
      unsubscribePrices([symbol]);
      off('price_update', handlePriceUpdate);
    };
  }, [symbol, subscribePrices, unsubscribePrices, on, off]);

  // 탭 변경 핸들러
  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  // 차트 간격 변경 핸들러
  const handleIntervalChange = (interval: string) => {
    setChartInterval(interval);
  };

  // 관심종목 추가/제거
  const toggleWatchlist = () => {
    setIsWatchlisted(!isWatchlisted);
    // 실제 API 호출 구현
  };

  // 현재 주가 (실시간 또는 조회된 주가)
  const currentPrice = realtimePrice || stockPrice;

  // 에러 처리
  if (infoError) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" action={
          <Button color="inherit" size="small" onClick={() => navigate('/dashboard')}>
            대시보드로 돌아가기
          </Button>
        }>
          종목 정보를 불러올 수 없습니다. 종목 코드를 확인해주세요.
        </Alert>
      </Box>
    );
  }

  // 로딩 상태
  if (infoLoading || priceLoading) {
    return (
      <Box sx={{ p: 3 }}>
        <Skeleton variant="rectangular" height={200} sx={{ mb: 2 }} />
        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Skeleton variant="rectangular" height={400} />
          </Grid>
          <Grid item xs={12} md={4}>
            <Skeleton variant="rectangular" height={400} />
          </Grid>
        </Grid>
      </Box>
    );
  }

  return (
    <Box>
      {/* 헤더 */}
      <Box sx={{ mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
          <IconButton onClick={() => navigate('/dashboard')}>
            <ArrowBackIcon />
          </IconButton>
          <Typography variant="h4" fontWeight={700}>
            {stockInfo?.name}
          </Typography>
          <Typography variant="h6" color="text.secondary">
            ({symbol})
          </Typography>
          <Chip
            label={MarketUtils.getMarketLabel(stockInfo?.market!)}
            size="small"
            color="primary"
            variant="outlined"
          />
        </Box>

        {/* 현재 주가 및 액션 버튼들 */}
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 2 }}>
            <Typography variant="h3" fontWeight={700}>
              {currentPrice ? NumberUtils.formatPrice(currentPrice.currentPrice) : '--'}
              <Typography component="span" variant="h5" color="text.secondary" sx={{ ml: 0.5 }}>
                원
              </Typography>
            </Typography>
            
            {currentPrice && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography
                  variant="h6"
                  sx={{
                    color: MarketUtils.getPriceChangeColor(currentPrice.changeRate),
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 0.5
                  }}
                >
                  {currentPrice.changeRate > 0 ? <TrendingUpIcon /> : 
                   currentPrice.changeRate < 0 ? <TrendingDownIcon /> : null}
                  {MarketUtils.formatPriceChange(currentPrice.change)}
                  ({MarketUtils.formatChangeRate(currentPrice.changeRate)})
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  거래량: {NumberUtils.formatVolume(currentPrice.volume)}
                </Typography>
              </Box>
            )}
          </Box>

          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant="outlined"
              startIcon={isWatchlisted ? <BookmarkIcon /> : <BookmarkBorderIcon />}
              onClick={toggleWatchlist}
            >
              {isWatchlisted ? '관심종목 제거' : '관심종목 추가'}
            </Button>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => {/* 포트폴리오 추가 모달 열기 */}}
            >
              포트폴리오에 추가
            </Button>
            <IconButton onClick={() => refetchAnalysis()}>
              <RefreshIcon />
            </IconButton>
            <IconButton>
              <ShareIcon />
            </IconButton>
          </Box>
        </Box>
      </Box>

      {/* 탭 메뉴 */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={currentTab} onChange={handleTabChange}>
          <Tab icon={<AIIcon />} label="AI 분석" />
          <Tab icon={<ChartIcon />} label="차트 분석" />
          <Tab icon={<TechnicalIcon />} label="기술적 지표" />
          <Tab icon={<NewsIcon />} label="뉴스 분석" />
        </Tabs>
      </Box>

      {/* AI 분석 탭 */}
      <TabPanel value={currentTab} index={0}>
        <Grid container spacing={3}>
          {/* AI 분석 결과 카드 */}
          <Grid item xs={12} md={8}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                  <Avatar
                    sx={{
                      bgcolor: aiAnalysis ? SignalUtils.getSignalColor(aiAnalysis.signal) + '20' : 'grey.200',
                      color: aiAnalysis ? SignalUtils.getSignalColor(aiAnalysis.signal) : 'grey.500',
                      width: 56,
                      height: 56
                    }}
                  >
                    <AIIcon fontSize="large" />
                  </Avatar>
                  <Box>
                    <Typography variant="h5" fontWeight={700}>
                      AI 투자 시그널
                    </Typography>
                    {aiAnalysis && (
                      <Typography variant="body2" color="text.secondary">
                        {DateUtils.formatRelative(aiAnalysis.generatedAt)} 생성
                      </Typography>
                    )}
                  </Box>
                </Box>

                {analysisLoading ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                    <CircularProgress />
                  </Box>
                ) : aiAnalysis ? (
                  <>
                    {/* 시그널 및 기본 정보 */}
                    <Grid container spacing={3} sx={{ mb: 3 }}>
                      <Grid item xs={12} sm={6} md={3}>
                        <Box sx={{ textAlign: 'center' }}>
                          <Typography variant="h4" fontWeight={700}
                            sx={{ color: SignalUtils.getSignalColor(aiAnalysis.signal) }}
                          >
                            {SignalUtils.getSignalLabel(aiAnalysis.signal)}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            투자 시그널
                          </Typography>
                        </Box>
                      </Grid>
                      <Grid item xs={12} sm={6} md={3}>
                        <Box sx={{ textAlign: 'center' }}>
                          <Typography variant="h4" fontWeight={700}>
                            {aiAnalysis.confidence}%
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            신뢰도
                          </Typography>
                          <LinearProgress
                            variant="determinate"
                            value={aiAnalysis.confidence}
                            sx={{ mt: 1, borderRadius: 1 }}
                          />
                        </Box>
                      </Grid>
                      <Grid item xs={12} sm={6} md={3}>
                        <Box sx={{ textAlign: 'center' }}>
                          <Typography variant="h4" fontWeight={700}
                            sx={{ color: aiAnalysis.expectedReturn > 0 ? 'success.main' : 'error.main' }}
                          >
                            {NumberUtils.formatPercent(aiAnalysis.expectedReturn)}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            기대수익률
                          </Typography>
                        </Box>
                      </Grid>
                      <Grid item xs={12} sm={6} md={3}>
                        <Box sx={{ textAlign: 'center' }}>
                          <Typography variant="h4" fontWeight={700}>
                            {NumberUtils.formatPrice(aiAnalysis.targetPrice)}원
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            목표가
                          </Typography>
                        </Box>
                      </Grid>
                    </Grid>

                    {/* 분석 근거 */}
                    <Box sx={{ mb: 3 }}>
                      <Typography variant="h6" fontWeight={600} gutterBottom>
                        분석 근거
                      </Typography>
                      <Typography variant="body1" sx={{ lineHeight: 1.8 }}>
                        {aiAnalysis.reasoning}
                      </Typography>
                    </Box>

                    {/* 주요 요인 */}
                    <Box>
                      <Typography variant="h6" fontWeight={600} gutterBottom>
                        주요 고려 요인
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                        {aiAnalysis.keyFactors.map((factor, index) => (
                          <Chip
                            key={index}
                            label={factor}
                            variant="outlined"
                            size="small"
                          />
                        ))}
                      </Box>
                    </Box>
                  </>
                ) : (
                  <Alert severity="info">
                    AI 분석 데이터를 불러오는 중입니다...
                  </Alert>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* 종목 기본 정보 */}
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" fontWeight={600} gutterBottom>
                  종목 정보
                </Typography>
                
                {stockInfo && (
                  <List disablePadding>
                    <ListItem sx={{ px: 0 }}>
                      <ListItemText
                        primary="시가총액"
                        secondary={NumberUtils.formatMarketCap(stockInfo.marketCap)}
                      />
                    </ListItem>
                    <Divider />
                    <ListItem sx={{ px: 0 }}>
                      <ListItemText
                        primary="상장주식수"
                        secondary={NumberUtils.formatCompact(stockInfo.listedShares) + '주'}
                      />
                    </ListItem>
                    <Divider />
                    <ListItem sx={{ px: 0 }}>
                      <ListItemText
                        primary="섹터"
                        secondary={stockInfo.sector}
                      />
                    </ListItem>
                    <Divider />
                    <ListItem sx={{ px: 0 }}>
                      <ListItemText
                        primary="업종"
                        secondary={stockInfo.industry}
                      />
                    </ListItem>
                    <Divider />
                    <ListItem sx={{ px: 0 }}>
                      <ListItemText
                        primary="상장시장"
                        secondary={MarketUtils.getMarketLabel(stockInfo.market)}
                      />
                    </ListItem>
                  </List>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>

      {/* 차트 분석 탭 */}
      <TabPanel value={currentTab} index={1}>
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
              <Typography variant="h6" fontWeight={600}>
                주가 차트
              </Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                {['1d', '5d', '1M', '3M', '1Y'].map((interval) => (
                  <Button
                    key={interval}
                    size="small"
                    variant={chartInterval === interval ? 'contained' : 'outlined'}
                    onClick={() => handleIntervalChange(interval)}
                  >
                    {interval.toUpperCase()}
                  </Button>
                ))}
              </Box>
            </Box>

            <Box sx={{ height: 400 }}>
              {chartLoading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                  <CircularProgress />
                </Box>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData || []}>
                    <defs>
                      <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#1976d2" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#1976d2" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis 
                      dataKey="timestamp" 
                      axisLine={false} 
                      tickLine={false}
                      tick={{ fontSize: 12 }}
                    />
                    <YAxis 
                      axisLine={false} 
                      tickLine={false}
                      tick={{ fontSize: 12 }}
                      domain={['dataMin - 1000', 'dataMax + 1000']}
                    />
                    <RechartsTooltip
                      contentStyle={{
                        backgroundColor: '#fff',
                        border: '1px solid #e0e0e0',
                        borderRadius: '8px'
                      }}
                      formatter={(value: any) => [NumberUtils.formatPrice(value) + '원', '주가']}
                    />
                    <Area
                      type="monotone"
                      dataKey="close"
                      stroke="#1976d2"
                      fillOpacity={1}
                      fill="url(#colorPrice)"
                      strokeWidth={2}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </Box>
          </CardContent>
        </Card>
      </TabPanel>

      {/* 기술적 지표 탭 */}
      <TabPanel value={currentTab} index={2}>
        <Grid container spacing={3}>
          {/* RSI */}
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6" fontWeight={600} gutterBottom>
                  RSI (14)
                </Typography>
                <Typography variant="h4" fontWeight={700}
                  sx={{
                    color: (technicalIndicators?.rsi ?? 0) > 70 ? 'error.main' :
                           (technicalIndicators?.rsi ?? 0) < 30 ? 'success.main' : 'text.primary'
                  }}
                >
                  {technicalIndicators?.rsi?.toFixed(1) || '--'}
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={technicalIndicators?.rsi || 0}
                  sx={{ mt: 2, borderRadius: 1 }}
                />
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                  {(technicalIndicators?.rsi ?? 0) > 70 ? '과매수' :
                   (technicalIndicators?.rsi ?? 0) < 30 ? '과매도' : '중립'}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          {/* MACD */}
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6" fontWeight={600} gutterBottom>
                  MACD
                </Typography>
                <Typography variant="h5" fontWeight={700}>
                  {technicalIndicators?.macd?.macd?.toFixed(2) || '--'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Signal: {technicalIndicators?.macd?.signal?.toFixed(2) || '--'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Histogram: {technicalIndicators?.macd?.histogram?.toFixed(2) || '--'}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          {/* 이동평균선 */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" fontWeight={600} gutterBottom>
                  이동평균선
                </Typography>
                <Grid container spacing={2}>
                  {[
                    { key: 'ma5', label: '5일선', period: 5 },
                    { key: 'ma20', label: '20일선', period: 20 },
                    { key: 'ma60', label: '60일선', period: 60 },
                    { key: 'ma120', label: '120일선', period: 120 }
                  ].map(({ key, label, period }) => (
                    <Grid item xs={6} sm={3} key={key}>
                      <Typography variant="subtitle2" fontWeight={600}>
                        {label}
                      </Typography>
                      <Typography variant="h6">
                        {technicalIndicators?.movingAverages?.[key as keyof typeof technicalIndicators.movingAverages]
                          ? NumberUtils.formatPrice(technicalIndicators.movingAverages[key as keyof typeof technicalIndicators.movingAverages])
                          : '--'}원
                      </Typography>
                    </Grid>
                  ))}
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>

      {/* 뉴스 분석 탭 */}
      <TabPanel value={currentTab} index={3}>
        <Card>
          <CardContent>
            <Typography variant="h6" fontWeight={600} gutterBottom>
              종목 관련 뉴스 및 감성 분석
            </Typography>
            
            <List>
              {stockNews?.map((news: any, index: number) => (
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
                    <ListItemAvatar>
                      <Avatar
                        sx={{
                          bgcolor: news.sentimentLabel === 'POSITIVE' ? 'success.main' :
                                  news.sentimentLabel === 'NEGATIVE' ? 'error.main' : 'grey.400',
                          width: 32,
                          height: 32
                        }}
                      >
                        {news.sentimentLabel === 'POSITIVE' ? <TrendingUpIcon fontSize="small" /> :
                         news.sentimentLabel === 'NEGATIVE' ? <TrendingDownIcon fontSize="small" /> :
                         <NewsIcon fontSize="small" />}
                      </Avatar>
                    </ListItemAvatar>
                    <ListItemText
                      primary={
                        <Typography 
                          variant="subtitle1" 
                          fontWeight={600}
                          sx={{
                            display: '-webkit-box',
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: 'vertical',
                            overflow: 'hidden',
                            mb: 1
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
                              WebkitLineClamp: 3,
                              WebkitBoxOrient: 'vertical',
                              overflow: 'hidden',
                              mb: 1.5
                            }}
                          >
                            {news.summary}
                          </Typography>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                            <Chip
                              label={`감정: ${news.sentimentLabel}`}
                              size="small"
                              color={
                                news.sentimentLabel === 'POSITIVE' ? 'success' :
                                news.sentimentLabel === 'NEGATIVE' ? 'error' : 'default'
                              }
                              variant="outlined"
                            />
                            <Chip
                              label={`영향도: ${news.impact}%`}
                              size="small"
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
                  {index < stockNews.length - 1 && <Divider />}
                </React.Fragment>
              ))}
            </List>
          </CardContent>
        </Card>
      </TabPanel>
    </Box>
  );
};

export default StockAnalysis;