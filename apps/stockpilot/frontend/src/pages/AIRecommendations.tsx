/**
 * AI 추천 화면 - 수익률 예상, 투자 근거, 리스크 레벨
 * 카카오뱅크/토스 스타일의 사용자 친화적 UI
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Card,
  CardContent,
  Typography,
  Chip,
  Button,
  Grid,
  LinearProgress,
  Avatar,
  Divider,
  Alert,
  Paper,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  CircularProgress
} from '@mui/material';
import {
  Psychology as PsychologyIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Security as SecurityIcon,
  ShowChart as ShowChartIcon,
  Info as InfoIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';

// AI 추천 데이터 타입
interface AIRecommendation {
  symbol: string;
  company_name: string;
  current_price: number;
  recommendation: 'buy' | 'sell' | 'hold';
  confidence_score: number;
  target_price: number;
  stop_loss: number;
  analysis_summary: string;
  risk_level: 'low' | 'medium' | 'high';
  investment_horizon: string;
  key_factors?: string[];
  timestamp: string;
}

// 시장 심리 데이터 타입
interface MarketSentiment {
  overall_sentiment: string;
  sentiment_score: number;
  recommendation: string;
  market_indices_count: number;
}

// 토스 스타일 색상
const tossColors = {
  primary: '#3182f6',
  secondary: '#0f172a',
  success: '#00d9a5',
  warning: '#ff6b35',
  danger: '#f85149',
  background: '#f8fafc',
  cardBackground: '#ffffff'
};

export const AIRecommendations: React.FC = () => {
  const [recommendations, setRecommendations] = useState<AIRecommendation[]>([]);
  const [marketSentiment, setMarketSentiment] = useState<MarketSentiment | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedRecommendation, setSelectedRecommendation] = useState<AIRecommendation | null>(null);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);

  // AI 추천 데이터 로드
  const loadRecommendations = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/v1/ai/recommendations?limit=5');
      const data = await response.json();
      
      if (data.success) {
        setRecommendations(data.data || []);
      }
    } catch (error) {
      console.error('AI 추천 데이터 로드 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  // 시장 심리 데이터 로드
  const loadMarketSentiment = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/ai/market-sentiment');
      const data = await response.json();
      
      if (data.success) {
        setMarketSentiment(data.data);
      }
    } catch (error) {
      console.error('시장 심리 데이터 로드 실패:', error);
    }
  };

  useEffect(() => {
    loadRecommendations();
    loadMarketSentiment();
  }, []);

  // 추천 레벨에 따른 색상
  const getRecommendationColor = (recommendation: string) => {
    switch (recommendation) {
      case 'buy': return tossColors.success;
      case 'sell': return tossColors.danger;
      default: return tossColors.warning;
    }
  };

  // 리스크 레벨에 따른 아이콘
  const getRiskIcon = (riskLevel: string) => {
    switch (riskLevel) {
      case 'low': return <CheckCircleIcon sx={{ color: tossColors.success }} />;
      case 'medium': return <WarningIcon sx={{ color: tossColors.warning }} />;
      case 'high': return <ErrorIcon sx={{ color: tossColors.danger }} />;
      default: return <InfoIcon />;
    }
  };

  // 수익률 계산
  const calculatePotentialReturn = (currentPrice: number, targetPrice: number) => {
    return ((targetPrice - currentPrice) / currentPrice * 100).toFixed(1);
  };

  // 상세 정보 다이얼로그 열기
  const openDetailDialog = (recommendation: AIRecommendation) => {
    setSelectedRecommendation(recommendation);
    setDetailDialogOpen(true);
  };

  return (
    <Container maxWidth="lg" sx={{ py: 3 }}>
      {/* 헤더 */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4" fontWeight={700} color={tossColors.secondary} gutterBottom>
            AI 투자 추천
          </Typography>
          <Typography variant="body1" color="text.secondary">
            AI가 분석한 오늘의 투자 추천 종목을 확인하세요
          </Typography>
        </Box>
        <IconButton
          onClick={() => {
            loadRecommendations();
            loadMarketSentiment();
          }}
          disabled={loading}
          sx={{
            bgcolor: tossColors.primary,
            color: 'white',
            '&:hover': { bgcolor: '#2563eb' }
          }}
        >
          <RefreshIcon />
        </IconButton>
      </Box>

      {/* 시장 심리 카드 */}
      {marketSentiment && (
        <Card sx={{ mb: 3, borderRadius: 3, boxShadow: '0 2px 12px rgba(0,0,0,0.08)' }}>
          <CardContent sx={{ p: 3 }}>
            <Box display="flex" alignItems="center" gap={2} mb={2}>
              <PsychologyIcon sx={{ color: tossColors.primary, fontSize: 32 }} />
              <Box>
                <Typography variant="h6" fontWeight={600}>
                  오늘의 시장 심리
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  주요 지수 {marketSentiment.market_indices_count}개 분석 기준
                </Typography>
              </Box>
            </Box>

            <Box display="flex" alignItems="center" gap={3}>
              <Box flex={1}>
                <Typography variant="h5" fontWeight={700} color={tossColors.primary} gutterBottom>
                  {marketSentiment.overall_sentiment}
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={marketSentiment.sentiment_score}
                  sx={{
                    height: 8,
                    borderRadius: 4,
                    backgroundColor: '#e2e8f0',
                    '& .MuiLinearProgress-bar': {
                      backgroundColor: marketSentiment.sentiment_score >= 60 
                        ? tossColors.success 
                        : marketSentiment.sentiment_score >= 40 
                        ? tossColors.warning 
                        : tossColors.danger
                    }
                  }}
                />
                <Typography variant="body2" color="text.secondary" mt={1}>
                  심리 지수: {marketSentiment.sentiment_score}점
                </Typography>
              </Box>
              <Chip
                label={marketSentiment.recommendation}
                sx={{
                  bgcolor: marketSentiment.sentiment_score >= 60 
                    ? tossColors.success 
                    : marketSentiment.sentiment_score >= 40 
                    ? tossColors.warning 
                    : tossColors.danger,
                  color: 'white',
                  fontWeight: 600,
                  px: 2,
                  py: 1
                }}
              />
            </Box>
          </CardContent>
        </Card>
      )}

      {/* AI 추천 목록 */}
      <Typography variant="h5" fontWeight={600} mb={3}>
        🎯 오늘의 AI 추천 종목
      </Typography>

      {loading ? (
        <Box display="flex" justifyContent="center" py={6}>
          <CircularProgress />
        </Box>
      ) : recommendations.length > 0 ? (
        <Grid container spacing={3}>
          {recommendations.map((recommendation, index) => (
            <Grid item xs={12} md={6} key={recommendation.symbol}>
              <Card
                sx={{
                  borderRadius: 3,
                  boxShadow: '0 2px 12px rgba(0,0,0,0.08)',
                  cursor: 'pointer',
                  transition: 'transform 0.2s, box-shadow 0.2s',
                  '&:hover': {
                    transform: 'translateY(-2px)',
                    boxShadow: '0 4px 20px rgba(0,0,0,0.12)'
                  }
                }}
                onClick={() => openDetailDialog(recommendation)}
              >
                <CardContent sx={{ p: 3 }}>
                  {/* 헤더 */}
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                    <Box display="flex" alignItems="center" gap={2}>
                      <Avatar
                        sx={{
                          bgcolor: tossColors.primary,
                          width: 48,
                          height: 48,
                          fontSize: '0.9rem',
                          fontWeight: 600
                        }}
                      >
                        {recommendation.symbol.slice(0, 2)}
                      </Avatar>
                      <Box>
                        <Typography variant="h6" fontWeight={600}>
                          {recommendation.company_name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {recommendation.symbol}
                        </Typography>
                      </Box>
                    </Box>
                    <Chip
                      label={recommendation.recommendation.toUpperCase()}
                      sx={{
                        bgcolor: getRecommendationColor(recommendation.recommendation),
                        color: 'white',
                        fontWeight: 600
                      }}
                    />
                  </Box>

                  {/* 가격 정보 */}
                  <Grid container spacing={2} mb={2}>
                    <Grid item xs={6}>
                      <Typography variant="body2" color="text.secondary">
                        현재가
                      </Typography>
                      <Typography variant="h6" fontWeight={600}>
                        ${recommendation.current_price.toFixed(2)}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="body2" color="text.secondary">
                        목표가
                      </Typography>
                      <Typography variant="h6" fontWeight={600} color={tossColors.primary}>
                        ${recommendation.target_price.toFixed(2)}
                      </Typography>
                    </Grid>
                  </Grid>

                  {/* 수익률 예상 */}
                  <Box mb={2}>
                    <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                      <Typography variant="body2" color="text.secondary">
                        예상 수익률
                      </Typography>
                      <Typography variant="h6" fontWeight={600} color={tossColors.success}>
                        +{calculatePotentialReturn(recommendation.current_price, recommendation.target_price)}%
                      </Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={Math.min(recommendation.confidence_score, 100)}
                      sx={{
                        height: 6,
                        borderRadius: 3,
                        backgroundColor: '#e2e8f0',
                        '& .MuiLinearProgress-bar': {
                          backgroundColor: tossColors.success
                        }
                      }}
                    />
                    <Typography variant="caption" color="text.secondary">
                      AI 신뢰도: {recommendation.confidence_score}%
                    </Typography>
                  </Box>

                  {/* 리스크 레벨 */}
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                    <Box display="flex" alignItems="center" gap={1}>
                      {getRiskIcon(recommendation.risk_level)}
                      <Typography variant="body2">
                        리스크: {recommendation.risk_level.toUpperCase()}
                      </Typography>
                    </Box>
                    <Typography variant="body2" color="text.secondary">
                      {recommendation.investment_horizon} 투자
                    </Typography>
                  </Box>

                  {/* 분석 요약 */}
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden'
                    }}
                  >
                    {recommendation.analysis_summary}
                  </Typography>

                  <Divider sx={{ my: 2 }} />

                  <Button
                    fullWidth
                    variant="outlined"
                    sx={{
                      borderColor: tossColors.primary,
                      color: tossColors.primary,
                      '&:hover': {
                        borderColor: '#2563eb',
                        backgroundColor: '#f1f5f9'
                      }
                    }}
                  >
                    상세 분석 보기
                  </Button>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      ) : (
        <Alert severity="info" sx={{ borderRadius: 2 }}>
          현재 AI 추천 데이터를 불러오는 중입니다. 잠시 후 다시 시도해주세요.
        </Alert>
      )}

      {/* 상세 정보 다이얼로그 */}
      <Dialog
        open={detailDialogOpen}
        onClose={() => setDetailDialogOpen(false)}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: { borderRadius: 3 }
        }}
      >
        {selectedRecommendation && (
          <>
            <DialogTitle sx={{ pb: 1 }}>
              <Box display="flex" alignItems="center" gap={2}>
                <Avatar
                  sx={{
                    bgcolor: tossColors.primary,
                    width: 56,
                    height: 56
                  }}
                >
                  {selectedRecommendation.symbol.slice(0, 2)}
                </Avatar>
                <Box>
                  <Typography variant="h5" fontWeight={600}>
                    {selectedRecommendation.company_name}
                  </Typography>
                  <Typography variant="body1" color="text.secondary">
                    {selectedRecommendation.symbol}
                  </Typography>
                </Box>
                <Box ml="auto">
                  <Chip
                    label={selectedRecommendation.recommendation.toUpperCase()}
                    sx={{
                      bgcolor: getRecommendationColor(selectedRecommendation.recommendation),
                      color: 'white',
                      fontWeight: 600,
                      fontSize: '1rem',
                      px: 2,
                      py: 1
                    }}
                  />
                </Box>
              </Box>
            </DialogTitle>

            <DialogContent>
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Paper sx={{ p: 3, borderRadius: 2, bgcolor: '#f8fafc' }}>
                    <Typography variant="h6" fontWeight={600} mb={2}>
                      💰 가격 정보
                    </Typography>
                    <Box mb={2}>
                      <Typography variant="body2" color="text.secondary">
                        현재가
                      </Typography>
                      <Typography variant="h4" fontWeight={700}>
                        ${selectedRecommendation.current_price.toFixed(2)}
                      </Typography>
                    </Box>
                    <Box mb={2}>
                      <Typography variant="body2" color="text.secondary">
                        목표가
                      </Typography>
                      <Typography variant="h5" fontWeight={600} color={tossColors.primary}>
                        ${selectedRecommendation.target_price.toFixed(2)}
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        손절가
                      </Typography>
                      <Typography variant="h6" fontWeight={600} color={tossColors.danger}>
                        ${selectedRecommendation.stop_loss.toFixed(2)}
                      </Typography>
                    </Box>
                  </Paper>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Paper sx={{ p: 3, borderRadius: 2, bgcolor: '#f8fafc' }}>
                    <Typography variant="h6" fontWeight={600} mb={2}>
                      📊 투자 지표
                    </Typography>
                    <Box mb={2}>
                      <Typography variant="body2" color="text.secondary">
                        예상 수익률
                      </Typography>
                      <Typography variant="h4" fontWeight={700} color={tossColors.success}>
                        +{calculatePotentialReturn(selectedRecommendation.current_price, selectedRecommendation.target_price)}%
                      </Typography>
                    </Box>
                    <Box mb={2}>
                      <Typography variant="body2" color="text.secondary">
                        AI 신뢰도
                      </Typography>
                      <Typography variant="h5" fontWeight={600}>
                        {selectedRecommendation.confidence_score}%
                      </Typography>
                    </Box>
                    <Box display="flex" alignItems="center" gap={1}>
                      {getRiskIcon(selectedRecommendation.risk_level)}
                      <Typography variant="body1">
                        리스크: {selectedRecommendation.risk_level.toUpperCase()}
                      </Typography>
                    </Box>
                  </Paper>
                </Grid>

                <Grid item xs={12}>
                  <Typography variant="h6" fontWeight={600} mb={2}>
                    🔍 AI 분석 요약
                  </Typography>
                  <Typography variant="body1" paragraph>
                    {selectedRecommendation.analysis_summary}
                  </Typography>
                </Grid>

                {selectedRecommendation.key_factors && selectedRecommendation.key_factors.length > 0 && (
                  <Grid item xs={12}>
                    <Typography variant="h6" fontWeight={600} mb={2}>
                      📈 주요 투자 포인트
                    </Typography>
                    <List>
                      {selectedRecommendation.key_factors.map((factor, index) => (
                        <ListItem key={index}>
                          <ListItemIcon>
                            <CheckCircleIcon sx={{ color: tossColors.success }} />
                          </ListItemIcon>
                          <ListItemText primary={factor} />
                        </ListItem>
                      ))}
                    </List>
                  </Grid>
                )}
              </Grid>
            </DialogContent>

            <DialogActions sx={{ p: 3 }}>
              <Button
                onClick={() => setDetailDialogOpen(false)}
                variant="outlined"
                sx={{ mr: 1 }}
              >
                닫기
              </Button>
              <Button
                variant="contained"
                sx={{
                  bgcolor: tossColors.primary,
                  '&:hover': { bgcolor: '#2563eb' }
                }}
              >
                관심종목 추가
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Container>
  );
};

export default AIRecommendations;