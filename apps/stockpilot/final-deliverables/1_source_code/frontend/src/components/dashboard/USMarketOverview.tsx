/**
 * 미국 시장 개요 위젯 - WebSocket 실시간 연동
 * 실시간 미국 주요 지수 및 종목 표시
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  Chip,
  IconButton,
  Tooltip,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  Divider,
  Alert,
  Badge
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Refresh as RefreshIcon,
  AccessTime as TimeIcon,
  AccountBalance as MarketIcon,
  WifiOff as OfflineIcon,
  Wifi as OnlineIcon,
  Warning as WarningIcon
} from '@mui/icons-material';
import { MarketStatusIndicator } from '../common/MarketStatusIndicator';
import { formatCurrency, formatPercent, getMarketStatus, US_MARKET } from '../../config/marketConfig';
import { 
  useWebSocket, 
  WebSocketState,
  USStocksMessage, 
  ExchangeRatesMessage,
  MarketStatusMessage 
} from '../../hooks/useWebSocket';
import { 
  getCurrentMarketSession, 
  getMarketStatusText, 
  getMarketStatusColor,
  formatMarketTime 
} from '../../utils/marketTime';

interface USStockData {
  symbol: string;
  companyName: string;
  currentPrice: number;
  change: number;
  changePercent: number;
  volume: number;
  marketCap?: number;
  marketState: string;
}

interface MarketIndex {
  symbol: string;
  name: string;
  value: number;
  change: number;
  changePercent: number;
}

export const USMarketOverview: React.FC = () => {
  const [majorStocks, setMajorStocks] = useState<USStockData[]>([]);
  const [marketIndices, setMarketIndices] = useState<MarketIndex[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [exchangeRate, setExchangeRate] = useState<number>(1387); // USD/KRW
  const [exchangeRateChange, setExchangeRateChange] = useState<number>(0);
  const [currentMarketStatus, setCurrentMarketStatus] = useState<string>('CLOSED');
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [updateCount, setUpdateCount] = useState(0);

  // WebSocket 연결 핸들러들
  const handleUSStocks = useCallback((message: USStocksMessage) => {
    console.log('📊 실시간 주식 데이터 수신:', message.payload.stocks.length);
    
    // 주식 데이터 업데이트
    const stocksData: USStockData[] = message.payload.stocks.map(stock => ({
      symbol: stock.symbol,
      companyName: stock.company_name,
      currentPrice: stock.current_price,
      change: stock.change,
      changePercent: stock.change_percent,
      volume: stock.volume,
      marketCap: stock.market_cap,
      marketState: stock.market_state
    }));
    
    setMajorStocks(stocksData);
    setLastUpdate(new Date());
    setUpdateCount(prev => prev + 1);
    
    // 첫 번째 데이터 로딩 완료
    if (loading) {
      setLoading(false);
    }
  }, [loading]);

  const handleExchangeRates = useCallback((message: ExchangeRatesMessage) => {
    console.log('💱 실시간 환율 데이터 수신:', message.payload.rates);
    
    const usdKrwRate = message.payload.rates.find(rate => rate.pair === 'USD/KRW');
    if (usdKrwRate) {
      setExchangeRate(usdKrwRate.rate);
      setExchangeRateChange(usdKrwRate.change_percent || 0);
    }
  }, []);

  const handleMarketStatus = useCallback((message: MarketStatusMessage) => {
    console.log('🏢 시장 상태 업데이트:', message.payload.markets);
    
    const usMarket = message.payload.markets.find(market => market.market_code === 'US');
    if (usMarket) {
      setCurrentMarketStatus(usMarket.status);
    }
  }, []);

  const handleConnectionError = useCallback((error: Error) => {
    console.error('WebSocket 연결 오류:', error);
    setConnectionError(error.message);
  }, []);

  // WebSocket 연결
  const { 
    connectionState, 
    isConnected, 
    connectionInfo,
    reconnect 
  } = useWebSocket({
    channels: ['us_stocks', 'exchange_rates', 'market_status'],
    onUSStocks: handleUSStocks,
    onExchangeRates: handleExchangeRates,
    onMarketStatus: handleMarketStatus,
    onError: handleConnectionError,
    autoConnect: true
  });

  // 연결 상태 변경 처리
  useEffect(() => {
    if (connectionState === WebSocketState.CONNECTED) {
      setConnectionError(null);
      console.log('✅ WebSocket 연결 성공');
    } else if (connectionState === WebSocketState.ERROR) {
      setConnectionError('실시간 연결에 문제가 발생했습니다');
    }
  }, [connectionState]);

  // 시장 상태 업데이트
  useEffect(() => {
    const marketSession = getCurrentMarketSession();
    setCurrentMarketStatus(marketSession.status);
  }, []);

  // 수동 새로고침
  const handleManualRefresh = useCallback(() => {
    console.log('🔄 수동 새로고침 요청');
    if (connectionState === WebSocketState.CONNECTED) {
      // WebSocket이 연결된 경우 재연결로 최신 데이터 요청
      setUpdateCount(prev => prev + 1);
    } else {
      // WebSocket이 연결되지 않은 경우 재연결 시도
      reconnect();
    }
  }, [connectionState, reconnect]);

  const getChangeIcon = (change: number) => {
    return change >= 0 ? 
      <TrendingUpIcon color="success" fontSize="small" /> : 
      <TrendingDownIcon color="error" fontSize="small" />;
  };

  const getChangeColor = (change: number) => {
    return change >= 0 ? 'success.main' : 'error.main';
  };

  const formatMarketCap = (marketCap: number) => {
    if (marketCap >= 1e12) {
      return `$${(marketCap / 1e12).toFixed(1)}T`;
    } else if (marketCap >= 1e9) {
      return `$${(marketCap / 1e9).toFixed(0)}B`;
    }
    return `$${(marketCap / 1e6).toFixed(0)}M`;
  };

  // 연결 상태 표시 컴포넌트
  const renderConnectionStatus = () => {
    let statusIcon;
    let statusText;
    let statusColor;

    switch (connectionState) {
      case WebSocketState.CONNECTED:
        statusIcon = <OnlineIcon fontSize="small" />;
        statusText = '실시간 연결됨';
        statusColor = 'success.main';
        break;
      case WebSocketState.CONNECTING:
      case WebSocketState.RECONNECTING:
        statusIcon = <CircularProgress size={16} />;
        statusText = '연결 중...';
        statusColor = 'warning.main';
        break;
      case WebSocketState.ERROR:
        statusIcon = <OfflineIcon fontSize="small" />;
        statusText = '연결 오류';
        statusColor = 'error.main';
        break;
      default:
        statusIcon = <OfflineIcon fontSize="small" />;
        statusText = '연결 끊김';
        statusColor = 'text.disabled';
    }

    return (
      <Tooltip title={`${statusText} | 업데이트: ${updateCount}회`}>
        <Box display="flex" alignItems="center" gap={0.5} sx={{ color: statusColor }}>
          {statusIcon}
          <Typography variant="caption" color="inherit">
            {statusText}
          </Typography>
        </Box>
      </Tooltip>
    );
  };

  if (loading && majorStocks.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <CircularProgress />
        <Typography variant="body2" sx={{ mt: 2 }}>
          실시간 미국 시장 데이터 연결 중...
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
          WebSocket 서버와 연결하고 있습니다.
        </Typography>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 3 }}>
      {/* 연결 오류 알림 */}
      {connectionError && (
        <Alert 
          severity="warning" 
          sx={{ mb: 2 }}
          action={
            <IconButton size="small" onClick={reconnect} color="inherit">
              <RefreshIcon />
            </IconButton>
          }
        >
          {connectionError}
        </Alert>
      )}

      {/* 헤더 */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box display="flex" alignItems="center" gap={1}>
          <MarketIcon color="primary" />
          <Typography variant="h6" fontWeight={600}>
            미국 시장 개요
          </Typography>
          <Chip 
            label={getMarketStatusText(currentMarketStatus as any, getCurrentMarketSession().isDST)}
            size="small"
            sx={{ 
              bgcolor: getMarketStatusColor(currentMarketStatus as any) + '20',
              color: getMarketStatusColor(currentMarketStatus as any),
              fontWeight: 600
            }}
          />
          {isConnected && (
            <Badge badgeContent={updateCount} color="primary" max={999}>
              <Chip label="LIVE" size="small" color="success" />
            </Badge>
          )}
        </Box>
        
        <Box display="flex" alignItems="center" gap={2}>
          {renderConnectionStatus()}
          <Typography variant="caption" color="text.secondary">
            <TimeIcon fontSize="small" sx={{ mr: 0.5 }} />
            {formatMarketTime(lastUpdate, getCurrentMarketSession().isDST)}
          </Typography>
          <Tooltip title="새로고침">
            <IconButton onClick={handleManualRefresh} size="small">
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* 주요 지수 */}
      <Typography variant="subtitle2" fontWeight={600} mb={2}>
        주요 지수
      </Typography>
      <Grid container spacing={2} mb={3}>
        {marketIndices.map((index) => (
          <Grid item xs={4} key={index.symbol}>
            <Card variant="outlined">
              <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                <Typography variant="caption" color="text.secondary">
                  {index.name}
                </Typography>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Typography variant="body1" fontWeight={600}>
                    {index.value.toLocaleString()}
                  </Typography>
                  <Box display="flex" alignItems="center" gap={0.5}>
                    {getChangeIcon(index.change)}
                    <Typography 
                      variant="caption" 
                      color={getChangeColor(index.change)}
                      fontWeight={600}
                    >
                      {index.changePercent > 0 ? '+' : ''}{index.changePercent.toFixed(2)}%
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* 주요 종목 */}
      <Typography variant="subtitle2" fontWeight={600} mb={2}>
        주요 종목 (FAANG+ 기술주)
      </Typography>
      <List dense>
        {majorStocks.map((stock, index) => (
          <React.Fragment key={stock.symbol}>
            <ListItem
              sx={{
                px: 0,
                '&:hover': { bgcolor: 'action.hover', borderRadius: 1 }
              }}
            >
              <ListItemText
                primary={
                  <Box display="flex" alignItems="center" justifyContent="space-between">
                    <Box>
                      <Typography variant="body2" fontWeight={600}>
                        {stock.symbol}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {stock.companyName}
                      </Typography>
                    </Box>
                    
                    <Box textAlign="right">
                      <Typography variant="body2" fontWeight={600}>
                        {formatCurrency(stock.currentPrice)}
                      </Typography>
                      <Box display="flex" alignItems="center" gap={0.5}>
                        {getChangeIcon(stock.change)}
                        <Typography 
                          variant="caption" 
                          color={getChangeColor(stock.change)}
                          fontWeight={600}
                        >
                          {stock.change > 0 ? '+' : ''}{stock.changePercent.toFixed(2)}%
                        </Typography>
                      </Box>
                    </Box>
                  </Box>
                }
                secondary={
                  <Box display="flex" justifyContent="space-between" mt={0.5}>
                    <Typography variant="caption" color="text.secondary">
                      거래량: {(stock.volume / 1000000).toFixed(1)}M
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      시총: {stock.marketCap ? formatMarketCap(stock.marketCap) : 'N/A'}
                    </Typography>
                  </Box>
                }
              />
            </ListItem>
            {index < majorStocks.length - 1 && <Divider />}
          </React.Fragment>
        ))}
      </List>

      {/* 환율 정보 - 실시간 업데이트 */}
      <Box mt={2} pt={2} borderTop="1px solid" borderColor="divider">
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Box display="flex" alignItems="center" gap={1}>
            <Typography variant="caption" color="text.secondary">
              USD/KRW 환율
            </Typography>
            {isConnected && (
              <Chip label="실시간" size="small" color="success" sx={{ height: 16, fontSize: '0.6rem' }} />
            )}
          </Box>
          <Box display="flex" alignItems="center" gap={0.5}>
            <Typography variant="caption" fontWeight={600}>
              ₩{exchangeRate.toLocaleString()}
            </Typography>
            {exchangeRateChange !== 0 && (
              <>
                {getChangeIcon(exchangeRateChange)}
                <Typography 
                  variant="caption" 
                  color={getChangeColor(exchangeRateChange)}
                  fontWeight={600}
                >
                  {exchangeRateChange > 0 ? '+' : ''}{exchangeRateChange.toFixed(2)}%
                </Typography>
              </>
            )}
          </Box>
        </Box>
        <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
          {isConnected ? 
            '* 실시간 환율로 자동 업데이트됩니다' : 
            '* 연결 후 실시간 환율이 적용됩니다'
          }
        </Typography>
        
        {/* 연결 정보 */}
        {connectionInfo.clientId && (
          <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
            클라이언트 ID: {connectionInfo.clientId.slice(-8)} | 
            구독 채널: {connectionInfo.subscribedChannels.length}개
          </Typography>
        )}
      </Box>
    </Paper>
  );
};