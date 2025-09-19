/**
 * 포트폴리오 관리 페이지
 * 보유 종목, 수익률, 포트폴리오 분석 및 추천 기능
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Tab,
  Tabs,
  Alert,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Assessment as AssessmentIcon,
  PieChart as PieChartIcon,
  Timeline as TimelineIcon,
  Lightbulb as RecommendationIcon
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PortfolioService, StockService } from '../services/api';
import { PortfolioHolding, PortfolioSummary, PortfolioRecommendation } from '../types';
import { Holding, Recommendation, PerformancePoint } from '../types/portfolio';
import { NumberUtils, SignalUtils, MarketUtils } from '../utils';
import { PieChart, Pie, Cell, ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import StockSearchBar from '../components/common/StockSearchBar';
import { MarketStatusIndicator } from '../components/common/MarketStatusIndicator';
import { formatCurrency, formatPercent, US_MARKET, DEFAULT_MARKET, detectMarketFromTicker } from '../config/marketConfig';

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

const Portfolio: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedHolding, setSelectedHolding] = useState<Holding | null>(null);
  const [newHolding, setNewHolding] = useState({
    symbol: '',
    quantity: 0,
    averagePrice: 0
  });

  const queryClient = useQueryClient();

  // 포트폴리오 요약 데이터
  const { data: portfolioSummary } = useQuery({
    queryKey: ['portfolioSummary'],
    queryFn: () => PortfolioService.getPortfolioSummary(),
    refetchInterval: 60000
  });

  // 포트폴리오 보유 종목
  const { data: holdings = [] } = useQuery({
    queryKey: ['portfolioHoldings'],
    queryFn: () => PortfolioService.getHoldings(),
    refetchInterval: 30000
  });

  // 포트폴리오 추천사항
  const { data: recommendations = [] } = useQuery<Recommendation[]>({
    queryKey: ['portfolioRecommendations'],
    queryFn: () => PortfolioService.getRecommendations()
  });

  // 포트폴리오 성과 데이터
  const { data: performanceData } = useQuery({
    queryKey: ['portfolioPerformance'],
    queryFn: () => PortfolioService.getPerformanceHistory(30)
  });

  // 종목 추가 뮤테이션
  const addHoldingMutation = useMutation({
    mutationFn: (holding: { symbol: string; quantity: number; averagePrice: number }) =>
      PortfolioService.addHolding(holding.symbol, holding.quantity, holding.averagePrice),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolioSummary'] });
      queryClient.invalidateQueries({ queryKey: ['portfolioHoldings'] });
      setAddDialogOpen(false);
      setNewHolding({ symbol: '', quantity: 0, averagePrice: 0 });
    }
  });

  // 종목 업데이트 뮤테이션
  const updateHoldingMutation = useMutation({
    mutationFn: (data: { id: string; quantity: number; averagePrice: number }) =>
      PortfolioService.updateHolding(data.id, data.quantity, data.averagePrice),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolioSummary'] });
      queryClient.invalidateQueries({ queryKey: ['portfolioHoldings'] });
      setEditDialogOpen(false);
      setSelectedHolding(null);
    }
  });

  // 종목 삭제 뮤테이션
  const deleteHoldingMutation = useMutation({
    mutationFn: (id: string) => PortfolioService.deleteHolding(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolioSummary'] });
      queryClient.invalidateQueries({ queryKey: ['portfolioHoldings'] });
    }
  });

  // 포트폴리오 요약 카드들
  const summaryCards = [
    {
      title: '총 평가금액',
      value: portfolioSummary ? NumberUtils.formatKRW(portfolioSummary.totalValue) : '-',
      change: portfolioSummary?.totalReturn || 0,
      icon: <AssessmentIcon />
    },
    {
      title: '총 수익률',
      value: portfolioSummary ? `${NumberUtils.formatPercent(portfolioSummary.totalReturnRate)}%` : '-',
      change: portfolioSummary?.totalReturnRate || 0,
      icon: <TrendingUpIcon />
    },
    {
      title: '보유 종목 수',
      value: holdings.length.toString(),
      change: 0,
      icon: <PieChartIcon />
    },
    {
      title: '오늘 수익',
      value: portfolioSummary ? NumberUtils.formatKRW(portfolioSummary.todayReturn) : '-',
      change: portfolioSummary?.todayReturnRate || 0,
      icon: <TimelineIcon />
    }
  ];

  // 포트폴리오 구성 차트 데이터
  const portfolioChartData = holdings.map((holding: Holding) => ({
    name: holding.stock.name,
    value: holding.currentValue,
    percentage: portfolioSummary ? (holding.currentValue / portfolioSummary.totalValue) * 100 : 0
  }));

  const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#8dd1e1', '#d084d0', '#ffb347'];

  const handleAddHolding = () => {
    if (newHolding.symbol && newHolding.quantity > 0 && newHolding.averagePrice > 0) {
      addHoldingMutation.mutate(newHolding);
    }
  };

  const handleUpdateHolding = () => {
    if (selectedHolding) {
      updateHoldingMutation.mutate({
        id: selectedHolding.id,
        quantity: selectedHolding.quantity,
        averagePrice: selectedHolding.averagePrice
      });
    }
  };

  const handleDeleteHolding = (id: string) => {
    deleteHoldingMutation.mutate(id);
  };

  return (
    <Box>
      {/* 헤더 */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" component="h1" fontWeight="bold">
          포트폴리오
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setAddDialogOpen(true)}
        >
          종목 추가
        </Button>
      </Box>

      {/* 요약 카드들 */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {summaryCards.map((card, index) => (
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
                          <TrendingUpIcon sx={{ fontSize: 16, color: 'error.main', mr: 0.5 }} />
                        ) : (
                          <TrendingDownIcon sx={{ fontSize: 16, color: 'primary.main', mr: 0.5 }} />
                        )}
                        <Typography
                          variant="body2"
                          sx={{
                            color: MarketUtils.getPriceChangeColor(card.change),
                            fontWeight: 500
                          }}
                        >
                          {MarketUtils.formatChangeRate(card.change)}
                        </Typography>
                      </Box>
                    )}
                  </Box>
                  <Box sx={{ color: 'primary.main' }}>
                    {card.icon}
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* 탭 네비게이션 */}
      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={tabValue}
          onChange={(_, newValue) => setTabValue(newValue)}
          indicatorColor="primary"
          textColor="primary"
        >
          <Tab label="보유 종목" />
          <Tab label="포트폴리오 분석" />
          <Tab label="AI 추천" />
        </Tabs>

        {/* 보유 종목 탭 */}
        <TabPanel value={tabValue} index={0}>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>종목</TableCell>
                  <TableCell align="right">보유수량</TableCell>
                  <TableCell align="right">평단가</TableCell>
                  <TableCell align="right">현재가</TableCell>
                  <TableCell align="right">평가금액</TableCell>
                  <TableCell align="right">손익</TableCell>
                  <TableCell align="right">수익률</TableCell>
                  <TableCell align="center">액션</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {holdings.map((holding: Holding) => {
                  const returnAmount = holding.currentValue - (holding.quantity * holding.averagePrice);
                  const returnRate = ((holding.stock.currentPrice - holding.averagePrice) / holding.averagePrice) * 100;

                  return (
                    <TableRow key={holding.id}>
                      <TableCell>
                        <Box>
                          <Typography variant="subtitle2" fontWeight={600}>
                            {holding.stock.name}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {holding.stock.symbol}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell align="right">
                        {NumberUtils.formatNumber(holding.quantity)}주
                      </TableCell>
                      <TableCell align="right">
                        {NumberUtils.formatPrice(holding.averagePrice)}원
                      </TableCell>
                      <TableCell align="right">
                        {NumberUtils.formatPrice(holding.stock.currentPrice)}원
                      </TableCell>
                      <TableCell align="right">
                        {NumberUtils.formatKRW(holding.currentValue)}
                      </TableCell>
                      <TableCell align="right">
                        <Typography
                          sx={{
                            color: MarketUtils.getPriceChangeColor(returnAmount),
                            fontWeight: 500
                          }}
                        >
                          {NumberUtils.formatKRW(returnAmount)}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography
                          sx={{
                            color: MarketUtils.getPriceChangeColor(returnRate),
                            fontWeight: 500
                          }}
                        >
                          {NumberUtils.formatPercent(returnRate)}%
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <IconButton
                          size="small"
                          onClick={() => {
                            setSelectedHolding(holding);
                            setEditDialogOpen(true);
                          }}
                        >
                          <EditIcon />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={() => handleDeleteHolding(holding.id)}
                          color="error"
                        >
                          <DeleteIcon />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        </TabPanel>

        {/* 포트폴리오 분석 탭 */}
        <TabPanel value={tabValue} index={1}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" sx={{ mb: 2 }}>
                  포트폴리오 구성
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      dataKey="value"
                      data={portfolioChartData}
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                      fill="#8884d8"
                      label={({ name, percentage }) => `${name} ${percentage.toFixed(1)}%`}
                    >
                      {portfolioChartData.map((_: any, index: number) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value: any) => NumberUtils.formatKRW(value)} />
                  </PieChart>
                </ResponsiveContainer>
              </Paper>
            </Grid>
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" sx={{ mb: 2 }}>
                  수익률 추이 (30일)
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={performanceData?.data || []}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip formatter={(value: any) => `${value}%`} />
                    <Line type="monotone" dataKey="returnRate" stroke="#8884d8" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </Paper>
            </Grid>
          </Grid>
        </TabPanel>

        {/* AI 추천 탭 */}
        <TabPanel value={tabValue} index={2}>
          <Box>
            {recommendations.length > 0 ? (
              <List>
                {recommendations.map((rec: Recommendation, index: number) => (
                  <React.Fragment key={index}>
                    <ListItem sx={{ py: 2 }}>
                      <ListItemIcon>
                        <RecommendationIcon color="primary" />
                      </ListItemIcon>
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="subtitle1" fontWeight={600}>
                              {rec.title}
                            </Typography>
                            <Chip
                              label={rec.type === 'BUY' ? '매수' : rec.type === 'SELL' ? '매도' : '리밸런싱'}
                              color={rec.type === 'BUY' ? 'success' : rec.type === 'SELL' ? 'error' : 'warning'}
                              size="small"
                            />
                          </Box>
                        }
                        secondary={
                          <Box sx={{ mt: 1 }}>
                            <Typography variant="body2" sx={{ mb: 1 }}>
                              {rec.description}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              신뢰도: {NumberUtils.formatPercent(rec.confidence)}% | 
                              생성시간: {new Date(rec.createdAt).toLocaleString()}
                            </Typography>
                          </Box>
                        }
                      />
                    </ListItem>
                    {index < recommendations.length - 1 && <Divider />}
                  </React.Fragment>
                ))}
              </List>
            ) : (
              <Alert severity="info">
                현재 AI 추천사항이 없습니다. 포트폴리오 분석을 통해 새로운 추천을 받아보세요.
              </Alert>
            )}
          </Box>
        </TabPanel>
      </Paper>

      {/* 종목 추가 다이얼로그 */}
      <Dialog open={addDialogOpen} onClose={() => setAddDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>종목 추가</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <StockSearchBar
              placeholder="추가할 종목을 검색하세요"
              onSelect={(stock) => setNewHolding(prev => ({ ...prev, symbol: stock.symbol }))}
              autoNavigate={false}
              fullWidth
            />
            <Grid container spacing={2} sx={{ mt: 2 }}>
              <Grid item xs={6}>
                <TextField
                  fullWidth
                  label="보유수량"
                  type="number"
                  value={newHolding.quantity}
                  onChange={(e) => setNewHolding(prev => ({ ...prev, quantity: Number(e.target.value) }))}
                />
              </Grid>
              <Grid item xs={6}>
                <TextField
                  fullWidth
                  label="평균단가 (원)"
                  type="number"
                  value={newHolding.averagePrice}
                  onChange={(e) => setNewHolding(prev => ({ ...prev, averagePrice: Number(e.target.value) }))}
                />
              </Grid>
            </Grid>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddDialogOpen(false)}>취소</Button>
          <Button onClick={handleAddHolding} variant="contained">
            추가
          </Button>
        </DialogActions>
      </Dialog>

      {/* 종목 수정 다이얼로그 */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>종목 수정</DialogTitle>
        <DialogContent>
          {selectedHolding && (
            <Box sx={{ pt: 2 }}>
              <Typography variant="subtitle1" sx={{ mb: 2 }}>
                {selectedHolding.stock.name} ({selectedHolding.stock.symbol})
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    label="보유수량"
                    type="number"
                    value={selectedHolding.quantity}
                    onChange={(e) => setSelectedHolding(prev => prev ? { ...prev, quantity: Number(e.target.value) } : null)}
                  />
                </Grid>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    label="평균단가 (원)"
                    type="number"
                    value={selectedHolding.averagePrice}
                    onChange={(e) => setSelectedHolding(prev => prev ? { ...prev, averagePrice: Number(e.target.value) } : null)}
                  />
                </Grid>
              </Grid>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>취소</Button>
          <Button onClick={handleUpdateHolding} variant="contained">
            수정
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Portfolio;