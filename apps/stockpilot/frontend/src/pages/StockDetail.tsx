/**
 * 종목 상세 분석 화면 - 토스 스타일 UI
 * 개별 종목의 상세 정보, 차트, AI 분석 결과 표시
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  Chip,
  Button,
  IconButton,
  Divider,
  LinearProgress,
  Stack,
  Grid,
  Tab,
  Tabs,
  Avatar,
  Alert,
  Skeleton
} from '@mui/material';
import {
  ArrowBack as BackIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon,
  Share as ShareIcon,
  Notifications as NotifyIcon,
  Timeline as ChartIcon,
  Psychology as AIIcon,
  Article as NewsIcon,
  Assessment as AnalysisIcon
} from '@mui/icons-material';

// 토스 스타일 색상 팔레트
const tossColors = {
  primary: '#1976d2',
  secondary: '#0d47a1',
  success: '#2e7d32',
  danger: '#d32f2f',
  warning: '#ed6c02',
  background: '#f8f9fa',
  cardBg: '#ffffff',
  textPrimary: '#212121',
  textSecondary: '#757575'
};

interface StockDetail {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  marketCap: number;
  per: number;
  pbr: number;
  dividend: number;
  high52w: number;
  low52w: number;
}

interface AIAnalysis {
  score: number;
  recommendation: 'buy' | 'sell' | 'hold';
  confidence: number;
  factors: {
    technical: number;
    fundamental: number;
    sentiment: number;
  };
  summary: string;
  risks: string[];
  opportunities: string[];
}

interface NewsItem {
  id: string;
  title: string;
  summary: string;
  sentiment: 'positive' | 'negative' | 'neutral';
  publishedAt: string;
  source: string;
}

export const StockDetail: React.FC<{ symbol: string }> = ({ symbol = "005930" }) => {
  // 상태 관리
  const [stockDetail, setStockDetail] = useState<StockDetail | null>(null);
  const [aiAnalysis, setAIAnalysis] = useState<AIAnalysis | null>(null);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState(0);
  const [isFavorite, setIsFavorite] = useState(false);

  // 컴포넌트 마운트 시 데이터 로드
  useEffect(() => {
    loadStockData();
  }, [symbol]);

  const loadStockData = async () => {
    setLoading(true);
    try {
      // 종목 상세 정보 로드
      const stockResponse = await fetch(`/api/v1/stocks/${symbol}`);
      if (stockResponse.ok) {
        const stockData = await stockResponse.json();
        setStockDetail(stockData);
      }

      // AI 분석 결과 로드
      const aiResponse = await fetch(`/api/v1/ai/analysis/${symbol}`);
      if (aiResponse.ok) {
        const aiData = await aiResponse.json();
        setAIAnalysis(aiData);
      }

      // 관련 뉴스 로드
      const newsResponse = await fetch(`/api/v1/news/${symbol}`);
      if (newsResponse.ok) {
        const newsData = await newsResponse.json();
        setNews(newsData.articles || []);
      }
    } catch (error) {
      console.error('데이터 로드 실패:', error);
    }
    setLoading(false);
  };

  // 가격 변화 색상
  const getPriceColor = (change: number) => {
    if (change > 0) return tossColors.success;
    if (change < 0) return tossColors.danger;
    return tossColors.textSecondary;
  };

  // AI 추천 색상
  const getRecommendationColor = (rec: string) => {
    switch (rec) {
      case 'buy': return tossColors.success;
      case 'sell': return tossColors.danger;
      default: return tossColors.warning;
    }
  };

  // 관심종목 토글
  const toggleFavorite = () => {
    setIsFavorite(!isFavorite);
    // API 호출하여 관심종목 추가/제거
  };

  if (loading) {
    return (
      <Box sx={{ minHeight: '100vh', bgcolor: tossColors.background }}>
        <Container maxWidth="sm" sx={{ pt: 2 }}>
          <Skeleton variant="rectangular" height={200} sx={{ mb: 2, borderRadius: 2 }} />
          <Skeleton variant="rectangular" height={150} sx={{ mb: 2, borderRadius: 2 }} />
          <Skeleton variant="rectangular" height={300} sx={{ borderRadius: 2 }} />
        </Container>
      </Box>
    );
  }

  if (!stockDetail) {
    return (
      <Box sx={{ minHeight: '100vh', bgcolor: tossColors.background, p: 2 }}>
        <Alert severity="error">종목 정보를 불러올 수 없습니다.</Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ 
      minHeight: '100vh',
      bgcolor: tossColors.background,
      pb: 8
    }}>
      {/* 상단 헤더 */}
      <Box sx={{
        bgcolor: tossColors.cardBg,
        p: 2,
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        position: 'sticky',
        top: 0,
        zIndex: 100
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <IconButton onClick={() => window.history.back()}>
              <BackIcon />
            </IconButton>
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                {stockDetail.name}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {stockDetail.symbol}
              </Typography>
            </Box>
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <IconButton onClick={toggleFavorite}>
              {isFavorite ? (
                <StarIcon sx={{ color: '#ffc107' }} />
              ) : (
                <StarBorderIcon />
              )}
            </IconButton>
            <IconButton>
              <ShareIcon />
            </IconButton>
            <IconButton>
              <NotifyIcon />
            </IconButton>
          </Box>
        </Box>
      </Box>

      <Container maxWidth="sm" sx={{ px: { xs: 1, sm: 2 } }}>
        {/* 주가 정보 카드 */}
        <Card sx={{ mt: 2, mb: 3, borderRadius: 3, boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
          <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
              <Typography variant="h4" sx={{ fontWeight: 'bold', color: tossColors.textPrimary }}>
                {stockDetail.price.toLocaleString()}원
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {stockDetail.change >= 0 ? (
                  <TrendingUpIcon sx={{ color: tossColors.success }} />
                ) : (
                  <TrendingDownIcon sx={{ color: tossColors.danger }} />
                )}
                <Typography
                  variant="h6"
                  sx={{ color: getPriceColor(stockDetail.change), fontWeight: 600 }}
                >
                  {stockDetail.change > 0 ? '+' : ''}{stockDetail.change.toLocaleString()}
                  ({stockDetail.changePercent.toFixed(2)}%)
                </Typography>
              </Box>
            </Box>

            <LinearProgress
              variant="determinate"
              value={((stockDetail.price - stockDetail.low52w) / (stockDetail.high52w - stockDetail.low52w)) * 100}
              sx={{
                height: 8,
                borderRadius: 4,
                bgcolor: '#e0e0e0',
                mb: 1,
                '& .MuiLinearProgress-bar': {
                  bgcolor: stockDetail.change >= 0 ? tossColors.success : tossColors.danger,
                  borderRadius: 4
                }
              }}
            />
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="caption" color="text.secondary">
                52주 최저: {stockDetail.low52w.toLocaleString()}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                52주 최고: {stockDetail.high52w.toLocaleString()}
              </Typography>
            </Box>
          </CardContent>
        </Card>

        {/* AI 분석 카드 */}
        {aiAnalysis && (
          <Card sx={{ mb: 3, borderRadius: 3, boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <AIIcon sx={{ color: tossColors.primary }} />
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    AI 투자 분석
                  </Typography>
                </Box>
                <Chip
                  label={aiAnalysis.recommendation.toUpperCase()}
                  sx={{
                    bgcolor: getRecommendationColor(aiAnalysis.recommendation),
                    color: 'white',
                    fontWeight: 600
                  }}
                />
              </Box>

              {/* AI 점수 */}
              <Box sx={{ mb: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="body2">AI 투자 점수</Typography>
                  <Typography variant="h6" sx={{ fontWeight: 600, color: tossColors.primary }}>
                    {aiAnalysis.score}/100
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={aiAnalysis.score}
                  sx={{
                    height: 8,
                    borderRadius: 4,
                    '& .MuiLinearProgress-bar': {
                      bgcolor: aiAnalysis.score >= 70 ? tossColors.success : 
                               aiAnalysis.score >= 40 ? tossColors.warning : tossColors.danger
                    }
                  }}
                />
              </Box>

              {/* 분석 요소들 */}
              <Grid container spacing={2} sx={{ mb: 2 }}>
                <Grid item xs={4}>
                  <Box sx={{ textAlign: 'center' }}>
                    <Typography variant="caption" color="text.secondary">기술적</Typography>
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                      {aiAnalysis.factors.technical}
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={4}>
                  <Box sx={{ textAlign: 'center' }}>
                    <Typography variant="caption" color="text.secondary">기본적</Typography>
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                      {aiAnalysis.factors.fundamental}
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={4}>
                  <Box sx={{ textAlign: 'center' }}>
                    <Typography variant="caption" color="text.secondary">감성</Typography>
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                      {aiAnalysis.factors.sentiment}
                    </Typography>
                  </Box>
                </Grid>
              </Grid>

              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {aiAnalysis.summary}
              </Typography>

              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button
                  variant="contained"
                  fullWidth
                  sx={{ borderRadius: 2 }}
                  color={aiAnalysis.recommendation === 'buy' ? 'success' : 'primary'}
                >
                  상세 분석 보기
                </Button>
              </Box>
            </CardContent>
          </Card>
        )}

        {/* 탭 네비게이션 */}
        <Card sx={{ mb: 2, borderRadius: 3 }}>
          <Tabs
            value={activeTab}
            onChange={(_, newValue) => setActiveTab(newValue)}
            variant="fullWidth"
            sx={{
              '& .MuiTab-root': {
                minHeight: 48,
                fontSize: '14px',
                fontWeight: 600
              }
            }}
          >
            <Tab icon={<ChartIcon />} label="차트" />
            <Tab icon={<AnalysisIcon />} label="재무" />
            <Tab icon={<NewsIcon />} label="뉴스" />
          </Tabs>
        </Card>

        {/* 탭 컨텐츠 */}
        {activeTab === 0 && (
          <Card sx={{ mb: 3, borderRadius: 3 }}>
            <CardContent>
              <Box sx={{ 
                height: 300, 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                bgcolor: '#f5f5f5',
                borderRadius: 2
              }}>
                <Typography color="text.secondary">
                  실시간 차트 영역
                </Typography>
              </Box>
            </CardContent>
          </Card>
        )}

        {activeTab === 1 && (
          <Card sx={{ mb: 3, borderRadius: 3 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                주요 재무지표
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Box sx={{ textAlign: 'center', p: 2, bgcolor: '#f8f9fa', borderRadius: 2 }}>
                    <Typography variant="caption" color="text.secondary">PER</Typography>
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                      {stockDetail.per}배
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6}>
                  <Box sx={{ textAlign: 'center', p: 2, bgcolor: '#f8f9fa', borderRadius: 2 }}>
                    <Typography variant="caption" color="text.secondary">PBR</Typography>
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                      {stockDetail.pbr}배
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6}>
                  <Box sx={{ textAlign: 'center', p: 2, bgcolor: '#f8f9fa', borderRadius: 2 }}>
                    <Typography variant="caption" color="text.secondary">시가총액</Typography>
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                      {Math.round(stockDetail.marketCap / 1000000)}조원
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6}>
                  <Box sx={{ textAlign: 'center', p: 2, bgcolor: '#f8f9fa', borderRadius: 2 }}>
                    <Typography variant="caption" color="text.secondary">배당수익률</Typography>
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                      {stockDetail.dividend}%
                    </Typography>
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        )}

        {activeTab === 2 && (
          <Stack spacing={2}>
            {news.map((item) => (
              <Card key={item.id} sx={{ borderRadius: 3 }}>
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 600, flex: 1, mr: 1 }}>
                      {item.title}
                    </Typography>
                    <Chip
                      label={item.sentiment}
                      size="small"
                      color={
                        item.sentiment === 'positive' ? 'success' : 
                        item.sentiment === 'negative' ? 'error' : 'default'
                      }
                    />
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    {item.summary}
                  </Typography>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="caption" color="text.secondary">
                      {item.source}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {new Date(item.publishedAt).toLocaleDateString()}
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            ))}
          </Stack>
        )}
      </Container>
    </Box>
  );
};

export default StockDetail;