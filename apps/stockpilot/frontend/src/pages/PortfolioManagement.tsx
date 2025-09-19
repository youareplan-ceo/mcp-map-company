/**
 * 자산 증식 코치 - 포트폴리오 화면
 * 상단: [매수 기록] [매도 기록] 버튼
 * 종목 카드 (토스 스타일):
 * - 종목명 + 보유수량
 * - 현재가 + 수익률
 * - 평가금액 + 수익금액
 * 클릭시: 매수/매도 기록 입력
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Stack,
  Button
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  Add as AddIcon
} from '@mui/icons-material';
import { TradeRecordPopup } from '../components/TradeRecordPopup';

// 자산 증식 코치 색상
const coachColors = {
  background: '#F7F8FA',  // 토스 그레이
  cardBg: '#FFFFFF',      // 흰색 카드
  profit: '#00C853',      // 수익 녹색
  loss: '#FF5252',        // 손실 빨강
  primary: '#4B8BF5',     // 토스 블루
  text: '#1A1A1A',        // 검정 텍스트
  textSecondary: '#666666' // 회색 텍스트
};

// 간단한 종목 데이터 타입
interface StockItem {
  symbol: string;         // 종목 코드
  name: string;           // 종목명
  shares: number;         // 보유수량
  currentPrice: number;   // 현재가
  profitRate: number;     // 수익률
  totalValue: number;     // 평가금액
  totalProfit: number;    // 수익금액
}

export const PortfolioManagement: React.FC = () => {
  const [stockItems, setStockItems] = useState<StockItem[]>([]);
  const [loading, setLoading] = useState(false);
  
  // 거래 기록 팝업 상태
  const [tradePopupOpen, setTradePopupOpen] = useState(false);
  const [selectedStock, setSelectedStock] = useState<{name: string; symbol: string} | null>(null);
  const [tradeType, setTradeType] = useState<'buy' | 'sell'>('buy');

  // 데이터 로드
  useEffect(() => {
    loadStockData();
  }, []);

  // 간단한 종목 데이터 로드
  const loadStockData = async () => {
    setLoading(true);
    try {
      // 모의 종목 데이터
      const mockData: StockItem[] = [
        {
          symbol: 'AAPL',
          name: '애플',
          shares: 10,
          currentPrice: 175.50,
          profitRate: 17.0,
          totalValue: 1755000,
          totalProfit: 255000
        },
        {
          symbol: 'GOOGL',
          name: '구글',
          shares: 5,
          currentPrice: 2650.00,
          profitRate: 10.4,
          totalValue: 1325000,
          totalProfit: 125000
        },
        {
          symbol: 'TSLA',
          name: '테슬라',
          shares: 8,
          currentPrice: 720.00,
          profitRate: -10.0,
          totalValue: 576000,
          totalProfit: -64000
        },
        {
          symbol: 'MSFT',
          name: '마이크로소프트',
          shares: 12,
          currentPrice: 330.00,
          profitRate: 10.0,
          totalValue: 396000,
          totalProfit: 36000
        },
        {
          symbol: 'AMZN',
          name: '아마존',
          shares: 3,
          currentPrice: 2980.00,
          profitRate: -6.9,
          totalValue: 894000,
          totalProfit: -66000
        }
      ];

      setStockItems(mockData);

    } catch (error) {
      console.error('종목 데이터 로드 실패:', error);
    }
    setLoading(false);
  };

  // 수익률에 따른 색상 결정
  const getProfitColor = (profitRate: number) => {
    return profitRate > 0 ? coachColors.profit : coachColors.loss;
  };

  // 거래 기록 팝업 열기
  const handleOpenTradePopup = (type: 'buy' | 'sell', stockName?: string, stockSymbol?: string) => {
    setTradeType(type);
    if (stockName && stockSymbol) {
      setSelectedStock({ name: stockName, symbol: stockSymbol });
    }
    setTradePopupOpen(true);
  };

  // 거래 기록 팝업 닫기
  const handleCloseTradePopup = () => {
    setTradePopupOpen(false);
    setSelectedStock(null);
  };

  return (
    <Box sx={{ 
      minHeight: '100vh',
      backgroundColor: coachColors.background,
      pb: { xs: 9, sm: 4 },
      p: 3
    }}>
      {/* 상단: [매수 기록] [매도 기록] 버튼 */}
      <Card sx={{ 
        bgcolor: coachColors.cardBg,
        borderRadius: '12px',
        mb: 3,
        p: 3,
        boxShadow: 'none'
      }}>
        <Stack direction="row" spacing={2} justifyContent="center">
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => handleOpenTradePopup('buy')}
            sx={{
              bgcolor: coachColors.primary,
              color: 'white',
              fontWeight: 600,
              borderRadius: '12px',
              px: 4,
              py: 2,
              fontSize: '16px',
              '&:hover': {
                bgcolor: '#3A7BE8'
              }
            }}
          >
            매수 기록
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => handleOpenTradePopup('sell')}
            sx={{
              bgcolor: coachColors.loss,
              color: 'white',
              fontWeight: 600,
              borderRadius: '12px',
              px: 4,
              py: 2,
              fontSize: '16px',
              '&:hover': {
                bgcolor: '#E13B3E'
              }
            }}
          >
            매도 기록
          </Button>
        </Stack>
      </Card>

      {/* 종목 카드 (토스 스타일) */}
      <Stack spacing={2}>
        {stockItems.map((stock) => (
          <Card 
            key={stock.symbol}
            sx={{
              bgcolor: coachColors.cardBg,
              borderRadius: '12px',
              p: 3,
              boxShadow: 'none',
              cursor: 'pointer',
              '&:hover': {
                transform: 'translateY(-2px)',
                transition: 'transform 0.2s ease-in-out'
              }
            }}
            onClick={() => handleOpenTradePopup('buy', stock.name, stock.symbol)}
          >
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              {/* 좌측: 종목명 + 보유수량 */}
              <Box>
                <Typography 
                  sx={{ 
                    fontSize: '16px',
                    fontWeight: 700,
                    color: coachColors.text,
                    mb: 0.5
                  }}
                >
                  {stock.name}
                </Typography>
                <Typography 
                  sx={{ 
                    fontSize: '14px',
                    color: coachColors.textSecondary
                  }}
                >
                  {stock.shares}주 보유
                </Typography>
              </Box>
              
              {/* 우측: 현재가 + 수익률 */}
              <Box sx={{ textAlign: 'right' }}>
                <Typography 
                  sx={{ 
                    fontSize: '16px',
                    fontWeight: 600,
                    color: coachColors.text,
                    mb: 0.5
                  }}
                >
                  ${stock.currentPrice.toFixed(2)}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 0.5 }}>
                  {stock.profitRate >= 0 ? 
                    <TrendingUp sx={{ fontSize: 16, color: coachColors.profit }} /> :
                    <TrendingDown sx={{ fontSize: 16, color: coachColors.loss }} />
                  }
                  <Typography 
                    sx={{ 
                      fontSize: '14px',
                      fontWeight: 600,
                      color: getProfitColor(stock.profitRate)
                    }}
                  >
                    {stock.profitRate > 0 ? '+' : ''}{stock.profitRate.toFixed(1)}%
                  </Typography>
                </Box>
              </Box>
            </Box>
            
            {/* 하단: 평가금액 + 수익금액 */}
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 2, pt: 2, borderTop: '1px solid #F0F0F0' }}>
              <Box>
                <Typography 
                  sx={{ 
                    fontSize: '14px',
                    color: coachColors.textSecondary,
                    mb: 0.5
                  }}
                >
                  평가금액
                </Typography>
                <Typography 
                  sx={{ 
                    fontSize: '16px',
                    fontWeight: 600,
                    color: coachColors.text
                  }}
                >
                  {stock.totalValue.toLocaleString()}원
                </Typography>
              </Box>
              
              <Box sx={{ textAlign: 'right' }}>
                <Typography 
                  sx={{ 
                    fontSize: '14px',
                    color: coachColors.textSecondary,
                    mb: 0.5
                  }}
                >
                  수익금액
                </Typography>
                <Typography 
                  sx={{ 
                    fontSize: '16px',
                    fontWeight: 600,
                    color: getProfitColor(stock.totalProfit)
                  }}
                >
                  {stock.totalProfit > 0 ? '+' : ''}{stock.totalProfit.toLocaleString()}원
                </Typography>
              </Box>
            </Box>
          </Card>
        ))}
      </Stack>

      {/* 거래 기록 입력 팝업 */}
      <TradeRecordPopup
        open={tradePopupOpen}
        onClose={handleCloseTradePopup}
        stockName={selectedStock?.name}
        stockSymbol={selectedStock?.symbol}
      />
    </Box>
  );
};

export default PortfolioManagement;