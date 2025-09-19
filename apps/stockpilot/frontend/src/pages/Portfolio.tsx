import React from 'react';
import { Box, Typography, Card, Button, Stack } from '@mui/material';

const Portfolio: React.FC = () => {
  const stocks = [
    { name: '삼성전자', shares: 10, price: '70,000원', profit: '+15%', color: '#00C853' },
    { name: '애플', shares: 5, price: '$175', profit: '+8%', color: '#00C853' },
    { name: '테슬라', shares: 3, price: '$220', profit: '-5%', color: '#FF5252' },
    { name: '구글', shares: 2, price: '$2,650', profit: '+12%', color: '#00C853' },
  ];

  return (
    <Box sx={{ 
      minHeight: '100vh',
      backgroundColor: '#F7F8FA',
      p: 3
    }}>
      {/* 상단 버튼 */}
      <Card sx={{ 
        bgcolor: '#FFFFFF',
        borderRadius: '12px',
        p: 3,
        mb: 3,
        boxShadow: 'none'
      }}>
        <Stack direction="row" spacing={2} justifyContent="center">
          <Button sx={{
            bgcolor: '#4B8BF5',
            color: 'white',
            borderRadius: '12px',
            px: 4,
            py: 1.5,
            fontSize: '16px',
            fontWeight: 600,
            '&:hover': { bgcolor: '#3A7BE8' }
          }}>
            매수 기록
          </Button>
          <Button sx={{
            bgcolor: '#FF5252',
            color: 'white',
            borderRadius: '12px',
            px: 4,
            py: 1.5,
            fontSize: '16px',
            fontWeight: 600,
            '&:hover': { bgcolor: '#E13B3E' }
          }}>
            매도 기록
          </Button>
        </Stack>
      </Card>

      {/* 종목 카드들 */}
      <Stack spacing={2}>
        {stocks.map((stock, index) => (
          <Card key={index} sx={{
            bgcolor: '#FFFFFF',
            borderRadius: '12px',
            p: 3,
            boxShadow: 'none',
            cursor: 'pointer',
            '&:hover': { transform: 'translateY(-2px)', transition: 'all 0.2s' }
          }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Box>
                <Typography sx={{ 
                  fontSize: '18px',
                  fontWeight: 700,
                  color: '#1A1A1A',
                  mb: 0.5
                }}>
                  {stock.name}
                </Typography>
                <Typography sx={{ 
                  fontSize: '14px',
                  color: '#666666'
                }}>
                  {stock.shares}주 보유
                </Typography>
              </Box>
              <Box sx={{ textAlign: 'right' }}>
                <Typography sx={{ 
                  fontSize: '16px',
                  fontWeight: 600,
                  color: '#1A1A1A',
                  mb: 0.5
                }}>
                  {stock.price}
                </Typography>
                <Typography sx={{ 
                  fontSize: '14px',
                  fontWeight: 600,
                  color: stock.color
                }}>
                  {stock.profit}
                </Typography>
              </Box>
            </Box>
          </Card>
        ))}
      </Stack>
    </Box>
  );
};

export default Portfolio;