/**
 * 내 포트폴리오 화면 - 보유 종목, 수익률, 손익 현황
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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tabs,
  Tab,
  CircularProgress
} from '@mui/material';
import {
  AccountBalance as AccountBalanceIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  PieChart as PieChartIcon,
  Add as AddIcon,
  Remove as RemoveIcon,
  Refresh as RefreshIcon,
  Timeline as TimelineIcon,
  Assessment as AssessmentIcon
} from '@mui/icons-material';

// 포트폴리오 데이터 타입
interface PortfolioHolding {
  symbol: string;
  name: string;
  quantity: number;
  avg_price: number;
  current_price: number;
  pnl: number;
  pnl_percent: number;
  market_value: number;
  weight: number;
}

interface PortfolioSummary {
  total_value: number;
  total_pnl: number;
  total_pnl_percent: number;
  total_cost: number;
  holdings: PortfolioHolding[];
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

export const MyPortfolio: React.FC = () => {
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState(0);

  // 포트폴리오 데이터 로드
  const loadPortfolioData = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/v1/portfolio');
      const data = await response.json();
      
      if (data.success || data.portfolio) {
        // 포트폴리오 데이터 가공
        const holdings = (data.portfolio || []).map((holding: any, index: number) => ({
          ...holding,
          market_value: holding.quantity * holding.current_price,
          weight: 0 // 나중에 계산
        }));

        const totalValue = data.total_value || holdings.reduce((sum: number, h: any) => sum + h.market_value, 0);
        
        // 비중 계산
        holdings.forEach((holding: any) => {
          holding.weight = (holding.market_value / totalValue) * 100;
        });

        setPortfolio({
          total_value: totalValue,
          total_pnl: data.total_pnl || 0,
          total_pnl_percent: data.total_pnl_percent || 0,
          total_cost: totalValue - (data.total_pnl || 0),
          holdings: holdings
        });
      }
    } catch (error) {
      console.error('포트폴리오 데이터 로드 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPortfolioData();
  }, []);

  // 가격 변동 색상
  const getPnLColor = (pnl: number) => {
    if (pnl > 0) return tossColors.success;
    if (pnl < 0) return tossColors.danger;
    return tossColors.secondary;
  };

  // 숫자 포맷팅
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(value);
  };

  // 퍼센트 포맷팅
  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  return (
    <Container maxWidth="lg" sx={{ py: 3 }}>
      {/* 헤더 */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4" fontWeight={700} color={tossColors.secondary} gutterBottom>
            내 포트폴리오
          </Typography>
          <Typography variant="body1" color="text.secondary">
            보유 종목과 수익률을 한눈에 확인하세요
          </Typography>
        </Box>
        <IconButton
          onClick={loadPortfolioData}
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

      {loading ? (
        <Box display="flex" justifyContent="center" py={6}>
          <CircularProgress />
        </Box>
      ) : portfolio ? (
        <>
          {/* 포트폴리오 요약 */}
          <Grid container spacing={3} mb={4}>
            <Grid item xs={12} md={4}>
              <Card sx={{ borderRadius: 3, boxShadow: '0 2px 12px rgba(0,0,0,0.08)', height: '100%' }}>
                <CardContent sx={{ p: 3, textAlign: 'center' }}>
                  <AccountBalanceIcon sx={{ fontSize: 48, color: tossColors.primary, mb: 2 }} />
                  <Typography variant="h6" fontWeight={600} color="text.secondary" gutterBottom>
                    총 자산
                  </Typography>
                  <Typography variant="h3" fontWeight={700} color={tossColors.secondary}>
                    {formatCurrency(portfolio.total_value)}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" mt={1}>
                    총 투자금: {formatCurrency(portfolio.total_cost)}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={4}>
              <Card sx={{ borderRadius: 3, boxShadow: '0 2px 12px rgba(0,0,0,0.08)', height: '100%' }}>
                <CardContent sx={{ p: 3, textAlign: 'center' }}>
                  {portfolio.total_pnl >= 0 ? (
                    <TrendingUpIcon sx={{ fontSize: 48, color: tossColors.success, mb: 2 }} />
                  ) : (
                    <TrendingDownIcon sx={{ fontSize: 48, color: tossColors.danger, mb: 2 }} />
                  )}
                  <Typography variant="h6" fontWeight={600} color="text.secondary" gutterBottom>
                    총 손익
                  </Typography>
                  <Typography 
                    variant="h3" 
                    fontWeight={700} 
                    color={getPnLColor(portfolio.total_pnl)}
                  >
                    {formatCurrency(portfolio.total_pnl)}
                  </Typography>
                  <Typography 
                    variant="h6" 
                    fontWeight={600}
                    color={getPnLColor(portfolio.total_pnl)}
                    mt={1}
                  >
                    {formatPercent(portfolio.total_pnl_percent)}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={4}>
              <Card sx={{ borderRadius: 3, boxShadow: '0 2px 12px rgba(0,0,0,0.08)', height: '100%' }}>
                <CardContent sx={{ p: 3, textAlign: 'center' }}>
                  <PieChartIcon sx={{ fontSize: 48, color: tossColors.warning, mb: 2 }} />
                  <Typography variant="h6" fontWeight={600} color="text.secondary" gutterBottom>
                    보유 종목 수
                  </Typography>
                  <Typography variant="h3" fontWeight={700} color={tossColors.secondary}>
                    {portfolio.holdings.length}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" mt={1}>
                    개 종목 보유 중
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* 탭 네비게이션 */}
          <Paper sx={{ mb: 3, borderRadius: 3 }}>
            <Tabs
              value={activeTab}
              onChange={(e, newValue) => setActiveTab(newValue)}
              sx={{ px: 2 }}
            >
              <Tab label="보유 종목" />
              <Tab label="자산 구성" />
              <Tab label="수익률 분석" />
            </Tabs>
          </Paper>

          {/* 보유 종목 테이블 */}
          {activeTab === 0 && (
            <Card sx={{ borderRadius: 3, boxShadow: '0 2px 12px rgba(0,0,0,0.08)' }}>
              <CardContent sx={{ p: 0 }}>
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 600 }}>종목</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 600 }}>보유량</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 600 }}>평균단가</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 600 }}>현재가</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 600 }}>평가금액</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 600 }}>손익</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 600 }}>수익률</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {portfolio.holdings.map((holding) => (
                        <TableRow 
                          key={holding.symbol}
                          sx={{ '&:hover': { backgroundColor: '#f8fafc' } }}
                        >
                          <TableCell>
                            <Box display="flex" alignItems="center" gap={2}>
                              <Avatar
                                sx={{
                                  bgcolor: tossColors.primary,
                                  width: 36,
                                  height: 36,
                                  fontSize: '0.8rem'
                                }}
                              >
                                {holding.symbol.slice(0, 2)}
                              </Avatar>
                              <Box>
                                <Typography variant="subtitle2" fontWeight={600}>
                                  {holding.name}
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                  {holding.symbol}
                                </Typography>
                              </Box>
                            </Box>
                          </TableCell>
                          <TableCell align="right">
                            {holding.quantity.toLocaleString()}
                          </TableCell>
                          <TableCell align="right">
                            {formatCurrency(holding.avg_price)}
                          </TableCell>
                          <TableCell align="right">
                            {formatCurrency(holding.current_price)}
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            {formatCurrency(holding.market_value)}
                          </TableCell>
                          <TableCell 
                            align="right" 
                            sx={{ 
                              color: getPnLColor(holding.pnl),
                              fontWeight: 600
                            }}
                          >
                            {formatCurrency(holding.pnl)}
                          </TableCell>
                          <TableCell 
                            align="right"
                            sx={{ 
                              color: getPnLColor(holding.pnl_percent),
                              fontWeight: 600
                            }}
                          >
                            {formatPercent(holding.pnl_percent)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          )}

          {/* 자산 구성 */}
          {activeTab === 1 && (
            <Card sx={{ borderRadius: 3, boxShadow: '0 2px 12px rgba(0,0,0,0.08)' }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" fontWeight={600} mb={3}>
                  포트폴리오 구성 비중
                </Typography>
                {portfolio.holdings.map((holding, index) => (
                  <Box key={holding.symbol} mb={3}>
                    <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                      <Box display="flex" alignItems="center" gap={2}>
                        <Avatar
                          sx={{
                            bgcolor: `hsl(${index * 40}, 70%, 50%)`,
                            width: 32,
                            height: 32,
                            fontSize: '0.7rem'
                          }}
                        >
                          {holding.symbol.slice(0, 2)}
                        </Avatar>
                        <Typography variant="subtitle1" fontWeight={600}>
                          {holding.name}
                        </Typography>
                      </Box>
                      <Typography variant="body1" fontWeight={600}>
                        {holding.weight.toFixed(1)}%
                      </Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={holding.weight}
                      sx={{
                        height: 8,
                        borderRadius: 4,
                        backgroundColor: '#e2e8f0',
                        '& .MuiLinearProgress-bar': {
                          backgroundColor: `hsl(${index * 40}, 70%, 50%)`
                        }
                      }}
                    />
                    <Box display="flex" justifyContent="space-between" mt={1}>
                      <Typography variant="caption" color="text.secondary">
                        {formatCurrency(holding.market_value)}
                      </Typography>
                      <Typography 
                        variant="caption" 
                        color={getPnLColor(holding.pnl_percent)}
                        fontWeight={600}
                      >
                        {formatPercent(holding.pnl_percent)}
                      </Typography>
                    </Box>
                  </Box>
                ))}
              </CardContent>
            </Card>
          )}

          {/* 수익률 분석 */}
          {activeTab === 2 && (
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Card sx={{ borderRadius: 3, boxShadow: '0 2px 12px rgba(0,0,0,0.08)', height: '100%' }}>
                  <CardContent sx={{ p: 3 }}>
                    <Typography variant="h6" fontWeight={600} mb={3}>
                      📊 수익률 현황
                    </Typography>
                    <Box mb={3}>
                      <Typography variant="body2" color="text.secondary" mb={1}>
                        전체 수익률
                      </Typography>
                      <Typography 
                        variant="h4" 
                        fontWeight={700} 
                        color={getPnLColor(portfolio.total_pnl_percent)}
                      >
                        {formatPercent(portfolio.total_pnl_percent)}
                      </Typography>
                      <LinearProgress
                        variant="determinate"
                        value={Math.min(Math.abs(portfolio.total_pnl_percent), 100)}
                        sx={{
                          mt: 2,
                          height: 8,
                          borderRadius: 4,
                          backgroundColor: '#e2e8f0',
                          '& .MuiLinearProgress-bar': {
                            backgroundColor: getPnLColor(portfolio.total_pnl_percent)
                          }
                        }}
                      />
                    </Box>
                    
                    <Divider sx={{ my: 3 }} />
                    
                    <Box>
                      <Typography variant="body2" color="text.secondary" mb={2}>
                        종목별 기여도 (수익률 기준)
                      </Typography>
                      {portfolio.holdings
                        .sort((a, b) => b.pnl - a.pnl)
                        .slice(0, 3)
                        .map((holding, index) => (
                          <Box key={holding.symbol} display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                            <Box display="flex" alignItems="center" gap={1}>
                              <Box
                                sx={{
                                  width: 12,
                                  height: 12,
                                  borderRadius: '50%',
                                  bgcolor: index === 0 ? tossColors.success : index === 1 ? tossColors.warning : tossColors.primary
                                }}
                              />
                              <Typography variant="body2">
                                {holding.name}
                              </Typography>
                            </Box>
                            <Typography 
                              variant="body2" 
                              fontWeight={600}
                              color={getPnLColor(holding.pnl_percent)}
                            >
                              {formatPercent(holding.pnl_percent)}
                            </Typography>
                          </Box>
                        ))}
                    </Box>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={6}>
                <Card sx={{ borderRadius: 3, boxShadow: '0 2px 12px rgba(0,0,0,0.08)', height: '100%' }}>
                  <CardContent sx={{ p: 3 }}>
                    <Typography variant="h6" fontWeight={600} mb={3}>
                      💡 포트폴리오 인사이트
                    </Typography>
                    
                    <Alert 
                      severity={portfolio.total_pnl >= 0 ? "success" : "error"} 
                      sx={{ mb: 2, borderRadius: 2 }}
                    >
                      <Typography variant="body2">
                        {portfolio.total_pnl >= 0 ? 
                          `현재 포트폴리오가 ${formatPercent(portfolio.total_pnl_percent)} 수익을 기록하고 있습니다.` :
                          `현재 포트폴리오가 ${formatPercent(Math.abs(portfolio.total_pnl_percent))} 손실을 기록하고 있습니다.`
                        }
                      </Typography>
                    </Alert>

                    <Box mb={2}>
                      <Typography variant="subtitle2" fontWeight={600} mb={1}>
                        🏆 최고 수익 종목
                      </Typography>
                      {portfolio.holdings.length > 0 && (
                        <Box>
                          {(() => {
                            const bestPerformer = portfolio.holdings.reduce((prev, current) => 
                              (prev.pnl_percent > current.pnl_percent) ? prev : current
                            );
                            return (
                              <Typography variant="body2" color="text.secondary">
                                {bestPerformer.name}: <span style={{ color: getPnLColor(bestPerformer.pnl_percent) }}>
                                  {formatPercent(bestPerformer.pnl_percent)}
                                </span>
                              </Typography>
                            );
                          })()}
                        </Box>
                      )}
                    </Box>

                    <Box mb={2}>
                      <Typography variant="subtitle2" fontWeight={600} mb={1}>
                        📊 포트폴리오 특성
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        • 보유 종목 수: {portfolio.holdings.length}개<br/>
                        • 최대 비중 종목: {portfolio.holdings.length > 0 ? 
                          portfolio.holdings.reduce((prev, current) => 
                            (prev.weight > current.weight) ? prev : current
                          ).name : '-'}<br/>
                        • 총 투자금: {formatCurrency(portfolio.total_cost)}
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          )}
        </>
      ) : (
        <Alert severity="info" sx={{ borderRadius: 2 }}>
          포트폴리오 데이터를 불러오는 중입니다. 잠시 후 다시 시도해주세요.
        </Alert>
      )}
    </Container>
  );
};

export default MyPortfolio;