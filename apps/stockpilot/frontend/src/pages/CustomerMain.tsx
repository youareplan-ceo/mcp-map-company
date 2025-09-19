/**
 * StockPilot 고객용 메인 화면 - 토스 스타일 UI
 * 일반 사용자를 위한 주식 검색, AI 추천, 실시간 정보 제공
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  TextField,
  InputAdornment,
  Chip,
  Button,
  Avatar,
  IconButton,
  Divider,
  LinearProgress,
  Stack,
  Grid,
  Fab
} from '@mui/material';
import {
  Search as SearchIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Notifications as NotificationsIcon,
  AccountCircle as ProfileIcon,
  Star as StarIcon,
  ArrowForward as ArrowIcon,
  Add as AddIcon,
  QueryStats as AnalysisIcon,
  Lightbulb as AIIcon,
  NewReleases as NewsIcon
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
  textSecondary: '#757575',
  divider: '#e0e0e0'
};

interface StockInfo {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  aiScore?: number;
}

interface AIRecommendation {
  id: string;
  title: string;
  description: string;
  confidence: number;
  type: 'buy' | 'sell' | 'hold';
  stocks: string[];
}

export const CustomerMain: React.FC = () => {
  // 상태 관리
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<StockInfo[]>([]);
  const [trendingStocks, setTrendingStocks] = useState<StockInfo[]>([]);
  const [aiRecommendations, setAIRecommendations] = useState<AIRecommendation[]>([]);
  const [loading, setLoading] = useState(false);
  const [userName, setUserName] = useState('투자자님');

  // 컴포넌트 마운트 시 데이터 로드
  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      // 인기 종목 데이터 로드
      const trendingResponse = await fetch('/api/v1/stocks/trending');
      if (trendingResponse.ok) {
        const trendingData = await trendingResponse.json();
        setTrendingStocks(trendingData.stocks || []);
      }

      // AI 추천 데이터 로드
      const aiResponse = await fetch('/api/v1/ai/recommendations');
      if (aiResponse.ok) {
        const aiData = await aiResponse.json();
        setAIRecommendations(aiData.recommendations || []);
      }
    } catch (error) {
      console.error('데이터 로드 실패:', error);
    }
    setLoading(false);
  };

  // 주식 검색 처리
  const handleSearch = async (query: string) => {
    if (!query.trim()) {
      setSearchResults([]);
      return;
    }

    try {
      const response = await fetch(`/api/v1/stocks/search?q=${encodeURIComponent(query)}`);
      if (response.ok) {
        const data = await response.json();
        setSearchResults(data.results || []);
      }
    } catch (error) {
      console.error('검색 실패:', error);
    }
  };

  // 종목 선택 처리
  const handleSelectStock = (stock: StockInfo) => {
    console.log('선택된 종목:', stock);
    // 상세 분석 페이지로 이동
  };

  // 가격 변화 색상 반환
  const getPriceColor = (change: number) => {
    if (change > 0) return tossColors.success;
    if (change < 0) return tossColors.danger;
    return tossColors.textSecondary;
  };

  // AI 추천 타입별 색상
  const getRecommendationColor = (type: string) => {
    switch (type) {
      case 'buy': return tossColors.success;
      case 'sell': return tossColors.danger;
      default: return tossColors.warning;
    }
  };

  return (
    <Box sx={{ 
      minHeight: '100vh',
      backgroundColor: tossColors.background,
      pb: 8 // 하단 네비게이션 공간
    }}>
      {/* 상단 헤더 */}
      <Box sx={{
        bgcolor: tossColors.cardBg,
        borderRadius: '0 0 16px 16px',
        p: 2,
        mb: 2,
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
      }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Avatar sx={{ bgcolor: tossColors.primary, width: 32, height: 32 }}>
              <AIIcon fontSize="small" />
            </Avatar>
            <Typography variant="h6" sx={{ color: tossColors.textPrimary, fontWeight: 600 }}>
              StockPilot
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <IconButton size="small">
              <NotificationsIcon />
            </IconButton>
            <IconButton size="small">
              <ProfileIcon />
            </IconButton>
          </Box>
        </Box>

        {/* 환영 메시지 */}
        <Typography variant="body1" sx={{ color: tossColors.textPrimary, mb: 1 }}>
          안녕하세요, {userName} 👋
        </Typography>
        <Typography variant="body2" sx={{ color: tossColors.textSecondary }}>
          오늘도 똑똑한 투자하세요
        </Typography>

        {/* 검색 바 */}
        <TextField
          fullWidth
          placeholder="종목명이나 코드를 검색하세요"
          value={searchQuery}
          onChange={(e) => {
            setSearchQuery(e.target.value);
            handleSearch(e.target.value);
          }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon color="action" />
              </InputAdornment>
            )
          }}
          sx={{
            mt: 2,
            '& .MuiOutlinedInput-root': {
              borderRadius: 3,
              bgcolor: '#f5f5f5',
              '& fieldset': {
                borderColor: 'transparent'
              },
              '&:hover fieldset': {
                borderColor: tossColors.primary
              }
            }
          }}
        />

        {/* 검색 결과 */}
        {searchResults.length > 0 && (
          <Box sx={{ mt: 2, maxHeight: 200, overflow: 'auto' }}>
            {searchResults.map((stock) => (
              <Card
                key={stock.symbol}
                sx={{
                  mb: 1,
                  cursor: 'pointer',
                  '&:hover': {
                    bgcolor: '#f0f7ff'
                  }
                }}
                onClick={() => handleSelectStock(stock)}
              >
                <CardContent sx={{ py: 1.5 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Box>
                      <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                        {stock.name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {stock.symbol}
                      </Typography>
                    </Box>
                    <Box sx={{ textAlign: 'right' }}>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {stock.price?.toLocaleString()}원
                      </Typography>
                      <Typography
                        variant="caption"
                        sx={{ color: getPriceColor(stock.change || 0) }}
                      >
                        {stock.change > 0 ? '+' : ''}{stock.changePercent?.toFixed(2)}%
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            ))}
          </Box>
        )}
      </Box>

      <Container maxWidth="sm" sx={{ px: { xs: 1, sm: 2 } }}>
        {loading && <LinearProgress sx={{ mb: 2 }} />}

        {/* 빠른 액션 버튼들 */}
        <Grid container spacing={{ xs: 1.5, sm: 2 }} sx={{ mb: { xs: 2.5, sm: 3 } }}>
          <Grid item xs={4}>
            <Button
              fullWidth
              variant="outlined"
              startIcon={<AnalysisIcon />}
              sx={{
                py: 1.5,
                borderRadius: 3,
                borderColor: tossColors.divider,
                color: tossColors.textPrimary,
                '&:hover': {
                  bgcolor: '#f0f7ff',
                  borderColor: tossColors.primary
                }
              }}
            >
              종목분석
            </Button>
          </Grid>
          <Grid item xs={4}>
            <Button
              fullWidth
              variant="outlined"
              startIcon={<AIIcon />}
              sx={{
                py: 1.5,
                borderRadius: 3,
                borderColor: tossColors.divider,
                color: tossColors.textPrimary,
                '&:hover': {
                  bgcolor: '#f0f7ff',
                  borderColor: tossColors.primary
                }
              }}
            >
              AI 추천
            </Button>
          </Grid>
          <Grid item xs={4}>
            <Button
              fullWidth
              variant="outlined"
              startIcon={<NewsIcon />}
              sx={{
                py: 1.5,
                borderRadius: 3,
                borderColor: tossColors.divider,
                color: tossColors.textPrimary,
                '&:hover': {
                  bgcolor: '#f0f7ff',
                  borderColor: tossColors.primary
                }
              }}
            >
              시장뉴스
            </Button>
          </Grid>
        </Grid>

        {/* 인기 종목 섹션 */}
        <Card sx={{ mb: 3, borderRadius: 3, boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                🔥 실시간 인기 종목
              </Typography>
              <Button size="small" endIcon={<ArrowIcon />}>
                더보기
              </Button>
            </Box>
            
            <Stack spacing={2}>
              {trendingStocks.slice(0, 5).map((stock, index) => (
                <Box key={stock.symbol}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Box
                      sx={{
                        width: 24,
                        height: 24,
                        borderRadius: '50%',
                        bgcolor: index < 3 ? tossColors.primary : tossColors.divider,
                        color: 'white',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '12px',
                        fontWeight: 'bold'
                      }}
                    >
                      {index + 1}
                    </Box>
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                        {stock.name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {stock.symbol}
                      </Typography>
                    </Box>
                    <Box sx={{ textAlign: 'right' }}>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {stock.price?.toLocaleString()}원
                      </Typography>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        {(stock.change || 0) >= 0 ? (
                          <TrendingUpIcon sx={{ fontSize: 14, color: tossColors.success }} />
                        ) : (
                          <TrendingDownIcon sx={{ fontSize: 14, color: tossColors.danger }} />
                        )}
                        <Typography
                          variant="caption"
                          sx={{ color: getPriceColor(stock.change || 0) }}
                        >
                          {stock.changePercent?.toFixed(2)}%
                        </Typography>
                      </Box>
                    </Box>
                  </Box>
                  {index < trendingStocks.slice(0, 5).length - 1 && (
                    <Divider sx={{ mt: 2 }} />
                  )}
                </Box>
              ))}
            </Stack>
          </CardContent>
        </Card>

        {/* AI 투자 추천 섹션 */}
        <Card sx={{ mb: 3, borderRadius: 3, boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                🤖 AI 투자 추천
              </Typography>
              <Chip 
                label="NEW" 
                size="small" 
                color="primary" 
                sx={{ fontSize: '10px', height: '20px' }}
              />
            </Box>

            <Stack spacing={2}>
              {aiRecommendations.slice(0, 3).map((rec) => (
                <Card 
                  key={rec.id}
                  sx={{
                    bgcolor: '#f8fffe',
                    border: `1px solid ${getRecommendationColor(rec.type)}20`,
                    borderRadius: 2,
                    cursor: 'pointer',
                    '&:hover': {
                      bgcolor: '#f0fff4'
                    }
                  }}
                >
                  <CardContent sx={{ py: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 600, flex: 1 }}>
                        {rec.title}
                      </Typography>
                      <Chip
                        label={rec.type.toUpperCase()}
                        size="small"
                        sx={{
                          bgcolor: getRecommendationColor(rec.type),
                          color: 'white',
                          fontSize: '10px',
                          height: '22px'
                        }}
                      />
                    </Box>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      {rec.description}
                    </Typography>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        {Array.from({ length: 5 }).map((_, i) => (
                          <StarIcon
                            key={i}
                            sx={{
                              fontSize: 14,
                              color: i < Math.round(rec.confidence * 5) ? '#ffc107' : '#e0e0e0'
                            }}
                          />
                        ))}
                      </Box>
                      <Typography variant="caption" color="text.secondary">
                        신뢰도 {(rec.confidence * 100).toFixed(0)}%
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              ))}
            </Stack>

            <Button
              fullWidth
              variant="contained"
              sx={{
                mt: 2,
                py: 1.5,
                borderRadius: 3,
                bgcolor: tossColors.primary,
                '&:hover': {
                  bgcolor: tossColors.secondary
                }
              }}
            >
              모든 AI 추천 보기
            </Button>
          </CardContent>
        </Card>

        {/* 시장 현황 요약 */}
        <Card sx={{ mb: 3, borderRadius: 3, boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
          <CardContent>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
              📊 오늘의 시장 현황
            </Typography>
            
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <Box sx={{ textAlign: 'center', p: 1 }}>
                  <Typography variant="caption" color="text.secondary">KOSPI</Typography>
                  <Typography variant="h6" sx={{ fontWeight: 600, color: tossColors.success }}>
                    2,456.78
                  </Typography>
                  <Typography variant="caption" sx={{ color: tossColors.success }}>
                    +15.34 (+0.63%)
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={6}>
                <Box sx={{ textAlign: 'center', p: 1 }}>
                  <Typography variant="caption" color="text.secondary">KOSDAQ</Typography>
                  <Typography variant="h6" sx={{ fontWeight: 600, color: tossColors.danger }}>
                    745.12
                  </Typography>
                  <Typography variant="caption" sx={{ color: tossColors.danger }}>
                    -3.45 (-0.46%)
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      </Container>

      {/* 플로팅 액션 버튼 */}
      <Fab
        color="primary"
        sx={{
          position: 'fixed',
          bottom: 80,
          right: 16,
          bgcolor: tossColors.primary,
          '&:hover': {
            bgcolor: tossColors.secondary
          }
        }}
      >
        <AddIcon />
      </Fab>

      {/* 오프라인 워터마크 (개발 모드) */}
      {process.env.REACT_APP_OFFLINE_MODE === 'true' && (
        <Box
          sx={{
            position: 'fixed',
            top: 16,
            right: 16,
            bgcolor: 'rgba(255, 193, 7, 0.9)',
            color: '#e65100',
            px: 2,
            py: 1,
            borderRadius: 2,
            fontSize: '12px',
            fontWeight: 'bold',
            zIndex: 9999,
            animation: 'pulse 2s infinite'
          }}
        >
          OFFLINE PREVIEW
        </Box>
      )}

    </Box>
  );
};

export default CustomerMain;