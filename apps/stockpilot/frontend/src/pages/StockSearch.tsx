/**
 * 종목 검색 화면 - 티커/회사명으로 검색 및 즉시 분석
 * 카카오뱅크/토스 스타일의 사용자 친화적 UI
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  TextField,
  Card,
  CardContent,
  Typography,
  Chip,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Avatar,
  Divider,
  Grid,
  Paper,
  CircularProgress,
  Alert,
  InputAdornment,
  IconButton
} from '@mui/material';
import {
  Search as SearchIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Clear as ClearIcon,
  Analytics as AnalyticsIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon
} from '@mui/icons-material';

// 종목 데이터 타입 정의
interface StockData {
  symbol: string;
  name: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  market_cap?: number;
}

interface AIAnalysis {
  symbol: string;
  recommendation: 'buy' | 'sell' | 'hold';
  confidence_score: number;
  target_price: number;
  analysis_summary: string;
  risk_level: 'low' | 'medium' | 'high';
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

export const StockSearch: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<StockData[]>([]);
  const [selectedStock, setSelectedStock] = useState<StockData | null>(null);
  const [aiAnalysis, setAiAnalysis] = useState<AIAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [watchlist, setWatchlist] = useState<string[]>(['AAPL', '005930.KS']);

  // 인기 종목 (기본 표시)
  const popularStocks = [
    { symbol: 'AAPL', name: 'Apple Inc.', type: '미국주식' },
    { symbol: 'MSFT', name: 'Microsoft Corp.', type: '미국주식' },
    { symbol: 'GOOGL', name: 'Alphabet Inc.', type: '미국주식' },
    { symbol: 'TSLA', name: 'Tesla Inc.', type: '미국주식' },
    { symbol: '005930.KS', name: '삼성전자', type: '한국주식' },
    { symbol: '000660.KS', name: 'SK하이닉스', type: '한국주식' },
    { symbol: '035420.KS', name: 'NAVER', type: '한국주식' },
    { symbol: '035720.KS', name: '카카오', type: '한국주식' }
  ];

  // 종목 검색 API 호출
  const searchStocks = async (query: string) => {
    if (!query.trim()) {
      setSearchResults([]);
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`http://localhost:8000/api/v1/stocks/search/real?q=${encodeURIComponent(query)}`);
      const data = await response.json();
      
      if (data.success) {
        setSearchResults(data.data || []);
      } else {
        setSearchResults([]);
      }
    } catch (error) {
      console.error('종목 검색 실패:', error);
      setSearchResults([]);
    } finally {
      setLoading(false);
    }
  };

  // 종목 상세 정보 조회
  const getStockDetail = async (symbol: string) => {
    try {
      const response = await fetch(`http://localhost:8000/api/v1/stocks/real/${symbol}`);
      const data = await response.json();
      
      if (data.success) {
        setSelectedStock(data.data);
        return data.data;
      }
    } catch (error) {
      console.error('종목 정보 조회 실패:', error);
    }
    return null;
  };

  // AI 분석 수행
  const performAIAnalysis = async (symbol: string) => {
    setAnalyzing(true);
    try {
      const response = await fetch(`http://localhost:8000/api/v1/ai/analyze/${symbol}`);
      const data = await response.json();
      
      if (data.success) {
        setAiAnalysis(data.data);
      } else {
        setAiAnalysis(null);
      }
    } catch (error) {
      console.error('AI 분석 실패:', error);
      setAiAnalysis(null);
    } finally {
      setAnalyzing(false);
    }
  };

  // 종목 선택 및 분석
  const handleSelectStock = async (symbol: string) => {
    const stockData = await getStockDetail(symbol);
    if (stockData) {
      await performAIAnalysis(symbol);
    }
  };

  // 관심종목 토글
  const toggleWatchlist = (symbol: string) => {
    setWatchlist(prev => 
      prev.includes(symbol) 
        ? prev.filter(s => s !== symbol)
        : [...prev, symbol]
    );
  };

  // 검색어 변경 시 검색 실행
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      searchStocks(searchQuery);
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [searchQuery]);

  // 가격 변동 색상 결정
  const getPriceColor = (change: number) => {
    if (change > 0) return tossColors.success;
    if (change < 0) return tossColors.danger;
    return tossColors.secondary;
  };

  // 추천 레벨 색상
  const getRecommendationColor = (recommendation: string) => {
    switch (recommendation) {
      case 'buy': return tossColors.success;
      case 'sell': return tossColors.danger;
      default: return tossColors.warning;
    }
  };

  return (
    <Container maxWidth="lg" sx={{ py: 3 }}>
      {/* 헤더 */}
      <Box mb={3}>
        <Typography variant="h4" fontWeight={700} color={tossColors.secondary} gutterBottom>
          종목 검색
        </Typography>
        <Typography variant="body1" color="text.secondary">
          티커나 회사명으로 검색하고 AI 분석을 받아보세요
        </Typography>
      </Box>

      {/* 검색 박스 */}
      <Card sx={{ mb: 3, borderRadius: 3, boxShadow: '0 2px 12px rgba(0,0,0,0.08)' }}>
        <CardContent sx={{ p: 3 }}>
          <TextField
            fullWidth
            placeholder="AAPL, 삼성전자, 005930 등을 검색해보세요"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon color="action" />
                </InputAdornment>
              ),
              endAdornment: searchQuery && (
                <InputAdornment position="end">
                  <IconButton onClick={() => setSearchQuery('')} edge="end">
                    <ClearIcon />
                  </IconButton>
                </InputAdornment>
              ),
              sx: {
                borderRadius: 2,
                backgroundColor: '#f8fafc',
                '& .MuiOutlinedInput-notchedOutline': {
                  borderColor: 'transparent'
                },
                '&:hover .MuiOutlinedInput-notchedOutline': {
                  borderColor: tossColors.primary
                },
                '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                  borderColor: tossColors.primary
                }
              }
            }}
          />
        </CardContent>
      </Card>

      <Grid container spacing={3}>
        {/* 검색 결과 / 인기 종목 */}
        <Grid item xs={12} md={6}>
          <Card sx={{ borderRadius: 3, boxShadow: '0 2px 12px rgba(0,0,0,0.08)' }}>
            <CardContent sx={{ p: 0 }}>
              <Box sx={{ p: 3, pb: 1 }}>
                <Typography variant="h6" fontWeight={600} gutterBottom>
                  {searchQuery ? '검색 결과' : '인기 종목'}
                </Typography>
              </Box>

              {loading ? (
                <Box display="flex" justifyContent="center" py={4}>
                  <CircularProgress />
                </Box>
              ) : (
                <List sx={{ pt: 0 }}>
                  {(searchQuery ? searchResults : popularStocks).map((stock, index) => (
                    <React.Fragment key={stock.symbol}>
                      <ListItem
                        button
                        onClick={() => handleSelectStock(stock.symbol)}
                        sx={{
                          px: 3,
                          py: 2,
                          '&:hover': {
                            backgroundColor: '#f8fafc'
                          }
                        }}
                      >
                        <ListItemAvatar>
                          <Avatar
                            sx={{
                              bgcolor: tossColors.primary,
                              width: 48,
                              height: 48,
                              fontSize: '0.9rem',
                              fontWeight: 600
                            }}
                          >
                            {stock.symbol.slice(0, 2)}
                          </Avatar>
                        </ListItemAvatar>
                        <ListItemText
                          primary={
                            <Box display="flex" justifyContent="space-between" alignItems="center">
                              <Typography variant="subtitle1" fontWeight={600}>
                                {stock.name}
                              </Typography>
                              <IconButton
                                size="small"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  toggleWatchlist(stock.symbol);
                                }}
                              >
                                {watchlist.includes(stock.symbol) ? (
                                  <StarIcon sx={{ color: tossColors.warning }} />
                                ) : (
                                  <StarBorderIcon />
                                )}
                              </IconButton>
                            </Box>
                          }
                          secondary={
                            <Box>
                              <Typography variant="body2" color="text.secondary">
                                {stock.symbol}
                              </Typography>
                              {'type' in stock && (
                                <Chip
                                  label={stock.type}
                                  size="small"
                                  sx={{
                                    mt: 0.5,
                                    height: 20,
                                    fontSize: '0.7rem',
                                    bgcolor: '#e2e8f0',
                                    color: '#475569'
                                  }}
                                />
                              )}
                            </Box>
                          }
                        />
                      </ListItem>
                      {index < (searchQuery ? searchResults : popularStocks).length - 1 && (
                        <Divider variant="inset" component="li" />
                      )}
                    </React.Fragment>
                  ))}
                </List>
              )}

              {searchQuery && searchResults.length === 0 && !loading && (
                <Box py={4} textAlign="center">
                  <Typography color="text.secondary">
                    검색 결과가 없습니다
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* 선택된 종목 정보 및 AI 분석 */}
        <Grid item xs={12} md={6}>
          {selectedStock ? (
            <Box>
              {/* 종목 정보 카드 */}
              <Card sx={{ mb: 3, borderRadius: 3, boxShadow: '0 2px 12px rgba(0,0,0,0.08)' }}>
                <CardContent sx={{ p: 3 }}>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                    <Typography variant="h6" fontWeight={600}>
                      {selectedStock.name}
                    </Typography>
                    <Chip label={selectedStock.symbol} variant="outlined" />
                  </Box>

                  <Box display="flex" alignItems="center" gap={2} mb={2}>
                    <Typography variant="h4" fontWeight={700}>
                      ${selectedStock.price.toFixed(2)}
                    </Typography>
                    <Box display="flex" alignItems="center" gap={0.5}>
                      {selectedStock.change > 0 ? <TrendingUpIcon /> : <TrendingDownIcon />}
                      <Typography
                        variant="body1"
                        fontWeight={600}
                        color={getPriceColor(selectedStock.change)}
                      >
                        ${selectedStock.change.toFixed(2)} ({selectedStock.change_percent.toFixed(2)}%)
                      </Typography>
                    </Box>
                  </Box>

                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography variant="body2" color="text.secondary">
                        거래량
                      </Typography>
                      <Typography variant="body1" fontWeight={600}>
                        {selectedStock.volume.toLocaleString()}
                      </Typography>
                    </Grid>
                    {selectedStock.market_cap && (
                      <Grid item xs={6}>
                        <Typography variant="body2" color="text.secondary">
                          시가총액
                        </Typography>
                        <Typography variant="body1" fontWeight={600}>
                          ${(selectedStock.market_cap / 1e9).toFixed(1)}B
                        </Typography>
                      </Grid>
                    )}
                  </Grid>
                </CardContent>
              </Card>

              {/* AI 분석 결과 */}
              <Card sx={{ borderRadius: 3, boxShadow: '0 2px 12px rgba(0,0,0,0.08)' }}>
                <CardContent sx={{ p: 3 }}>
                  <Box display="flex" alignItems="center" gap={1} mb={2}>
                    <AnalyticsIcon color="primary" />
                    <Typography variant="h6" fontWeight={600}>
                      AI 분석 결과
                    </Typography>
                  </Box>

                  {analyzing ? (
                    <Box display="flex" justifyContent="center" py={4}>
                      <CircularProgress />
                      <Typography variant="body2" color="text.secondary" ml={2}>
                        AI가 분석 중입니다...
                      </Typography>
                    </Box>
                  ) : aiAnalysis ? (
                    <Box>
                      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                        <Chip
                          label={aiAnalysis.recommendation.toUpperCase()}
                          sx={{
                            bgcolor: getRecommendationColor(aiAnalysis.recommendation),
                            color: 'white',
                            fontWeight: 600,
                            fontSize: '0.9rem'
                          }}
                        />
                        <Typography variant="body2" color="text.secondary">
                          신뢰도: {aiAnalysis.confidence_score}%
                        </Typography>
                      </Box>

                      <Typography variant="body1" paragraph>
                        {aiAnalysis.analysis_summary}
                      </Typography>

                      <Grid container spacing={2}>
                        <Grid item xs={6}>
                          <Typography variant="body2" color="text.secondary">
                            목표 가격
                          </Typography>
                          <Typography variant="h6" fontWeight={600} color={tossColors.primary}>
                            ${aiAnalysis.target_price.toFixed(2)}
                          </Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="body2" color="text.secondary">
                            위험도
                          </Typography>
                          <Chip
                            label={aiAnalysis.risk_level.toUpperCase()}
                            size="small"
                            color={aiAnalysis.risk_level === 'low' ? 'success' : aiAnalysis.risk_level === 'medium' ? 'warning' : 'error'}
                          />
                        </Grid>
                      </Grid>
                    </Box>
                  ) : (
                    <Alert severity="info">
                      종목을 선택하면 AI 분석이 시작됩니다
                    </Alert>
                  )}
                </CardContent>
              </Card>
            </Box>
          ) : (
            <Card sx={{ borderRadius: 3, boxShadow: '0 2px 12px rgba(0,0,0,0.08)' }}>
              <CardContent sx={{ p: 4, textAlign: 'center' }}>
                <SearchIcon sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
                <Typography variant="h6" color="text.secondary" gutterBottom>
                  종목을 선택해주세요
                </Typography>
                <Typography variant="body2" color="text.disabled">
                  왼쪽에서 종목을 선택하면 상세 정보와 AI 분석을 확인할 수 있습니다
                </Typography>
              </CardContent>
            </Card>
          )}
        </Grid>
      </Grid>
    </Container>
  );
};

export default StockSearch;