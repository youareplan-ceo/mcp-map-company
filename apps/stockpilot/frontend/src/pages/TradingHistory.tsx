/**
 * 자산 증식 코치 - 기록 화면
 * 실행한 거래 리스트
 * - 날짜 + 종목 + 수익/손실
 * - 누적 수익 표시
 * 극도의 심플함으로 "자산 증식"에만 집중
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  Stack
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown
} from '@mui/icons-material';

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

// 거래 기록 타입
interface TradeRecord {
  id: string;
  date: string;           // 거래 날짜
  stockName: string;      // 종목명
  type: 'buy' | 'sell';   // 매수/매도
  quantity: number;       // 수량
  price: number;          // 가격
  profit: number;         // 수익/손실
}

export const TradingHistory: React.FC = () => {
  const [tradeRecords, setTradeRecords] = useState<TradeRecord[]>([]);
  const [totalProfit, setTotalProfit] = useState(0);
  const [loading, setLoading] = useState(false);

  // 데이터 로드
  useEffect(() => {
    loadTradeHistory();
  }, []);

  // 거래 내역 로드
  const loadTradeHistory = async () => {
    setLoading(true);
    try {
      // 모의 거래 내역 데이터
      const mockData: TradeRecord[] = [
        {
          id: 'trade-1',
          date: '2024-01-15',
          stockName: '애플',
          type: 'buy',
          quantity: 10,
          price: 150.00,
          profit: 0
        },
        {
          id: 'trade-2',
          date: '2024-01-20',
          stockName: '구글',
          type: 'buy',
          quantity: 5,
          price: 2400.00,
          profit: 0
        },
        {
          id: 'trade-3',
          date: '2024-02-01',
          stockName: '애플',
          type: 'sell',
          quantity: 5,
          price: 175.50,
          profit: 127500 // (175.50 - 150.00) * 5
        },
        {
          id: 'trade-4',
          date: '2024-02-10',
          stockName: '테슬라',
          type: 'buy',
          quantity: 8,
          price: 800.00,
          profit: 0
        },
        {
          id: 'trade-5',
          date: '2024-02-15',
          stockName: '마이크로소프트',
          type: 'buy',
          quantity: 12,
          price: 300.00,
          profit: 0
        },
        {
          id: 'trade-6',
          date: '2024-02-28',
          stockName: '테슬라',
          type: 'sell',
          quantity: 3,
          price: 720.00,
          profit: -240000 // (720.00 - 800.00) * 3
        },
        {
          id: 'trade-7',
          date: '2024-03-05',
          stockName: '구글',
          type: 'sell',
          quantity: 2,
          price: 2650.00,
          profit: 500000 // (2650.00 - 2400.00) * 2
        }
      ];

      setTradeRecords(mockData);
      
      // 누적 수익 계산
      const total = mockData.reduce((sum, record) => sum + record.profit, 0);
      setTotalProfit(total);

    } catch (error) {
      console.error('거래 내역 로드 실패:', error);
    }
    setLoading(false);
  };

  // 수익/손실 색상 결정
  const getProfitColor = (profit: number) => {
    return profit > 0 ? coachColors.profit : profit < 0 ? coachColors.loss : coachColors.textSecondary;
  };

  // 거래 타입 텍스트
  const getTradeTypeText = (type: 'buy' | 'sell') => {
    return type === 'buy' ? '매수' : '매도';
  };

  // 거래 타입 색상
  const getTradeTypeColor = (type: 'buy' | 'sell') => {
    return type === 'buy' ? coachColors.primary : coachColors.loss;
  };

  return (
    <Box sx={{ 
      minHeight: '100vh',
      backgroundColor: coachColors.background,
      pb: { xs: 9, sm: 4 },
      p: 3
    }}>
      {/* 상단: 누적 수익 표시 */}
      <Card sx={{ 
        bgcolor: coachColors.cardBg,
        borderRadius: '12px',
        mb: 3,
        p: 3,
        textAlign: 'center',
        boxShadow: 'none'
      }}>
        <Typography 
          sx={{ 
            fontSize: '14px',
            color: coachColors.textSecondary,
            mb: 1
          }}
        >
          누적 수익
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1 }}>
          {totalProfit >= 0 ? 
            <TrendingUp sx={{ fontSize: 24, color: coachColors.profit }} /> :
            <TrendingDown sx={{ fontSize: 24, color: coachColors.loss }} />
          }
          <Typography 
            sx={{ 
              fontSize: '32px',
              fontWeight: 700,
              color: getProfitColor(totalProfit)
            }}
          >
            {totalProfit > 0 ? '+' : ''}{totalProfit.toLocaleString()}원
          </Typography>
        </Box>
      </Card>

      {/* 거래 기록 리스트 */}
      <Stack spacing={2}>
        {tradeRecords.map((record) => (
          <Card 
            key={record.id}
            sx={{
              bgcolor: coachColors.cardBg,
              borderRadius: '12px',
              p: 3,
              boxShadow: 'none'
            }}
          >
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              {/* 좌측: 날짜 + 종목 + 거래타입 */}
              <Box>
                <Typography 
                  sx={{ 
                    fontSize: '14px',
                    color: coachColors.textSecondary,
                    mb: 0.5
                  }}
                >
                  {new Date(record.date).toLocaleDateString('ko-KR', {
                    month: 'long',
                    day: 'numeric'
                  })}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                  <Typography 
                    sx={{ 
                      fontSize: '16px',
                      fontWeight: 700,
                      color: coachColors.text
                    }}
                  >
                    {record.stockName}
                  </Typography>
                  <Typography 
                    sx={{ 
                      fontSize: '14px',
                      fontWeight: 600,
                      color: getTradeTypeColor(record.type),
                      px: 1,
                      py: 0.5,
                      bgcolor: record.type === 'buy' ? 'rgba(75, 139, 245, 0.1)' : 'rgba(255, 82, 82, 0.1)',
                      borderRadius: '6px'
                    }}
                  >
                    {getTradeTypeText(record.type)}
                  </Typography>
                </Box>
                <Typography 
                  sx={{ 
                    fontSize: '14px',
                    color: coachColors.textSecondary
                  }}
                >
                  {record.quantity}주 × ${record.price.toFixed(2)}
                </Typography>
              </Box>
              
              {/* 우측: 수익/손실 */}
              <Box sx={{ textAlign: 'right' }}>
                {record.profit !== 0 && (
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 0.5 }}>
                    {record.profit >= 0 ? 
                      <TrendingUp sx={{ fontSize: 16, color: coachColors.profit }} /> :
                      <TrendingDown sx={{ fontSize: 16, color: coachColors.loss }} />
                    }
                    <Typography 
                      sx={{ 
                        fontSize: '16px',
                        fontWeight: 600,
                        color: getProfitColor(record.profit)
                      }}
                    >
                      {record.profit > 0 ? '+' : ''}{record.profit.toLocaleString()}원
                    </Typography>
                  </Box>
                )}
                {record.profit === 0 && (
                  <Typography 
                    sx={{ 
                      fontSize: '14px',
                      color: coachColors.textSecondary
                    }}
                  >
                    매수 완료
                  </Typography>
                )}
              </Box>
            </Box>
          </Card>
        ))}
      </Stack>

      {/* 빈 공간 */}
      {tradeRecords.length === 0 && (
        <Box sx={{ 
          textAlign: 'center', 
          py: 8,
          color: coachColors.textSecondary 
        }}>
          <Typography sx={{ fontSize: '16px' }}>
            아직 거래 기록이 없습니다
          </Typography>
          <Typography sx={{ fontSize: '14px', mt: 1 }}>
            포트폴리오에서 매수/매도 기록을 추가해보세요
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default TradingHistory;