import React from 'react';
import { Box, Typography, Card, Stack } from '@mui/material';

const History: React.FC = () => {
  const records = [
    { date: '2024-01-15', stock: '삼성전자', type: '매수', quantity: 10, price: '70,000원', profit: null },
    { date: '2024-01-20', stock: '애플', type: '매수', quantity: 5, price: '$175', profit: null },
    { date: '2024-02-01', stock: '삼성전자', type: '매도', quantity: 5, price: '75,000원', profit: '+25,000원' },
    { date: '2024-02-10', stock: '테슬라', type: '매수', quantity: 3, price: '$220', profit: null },
    { date: '2024-02-15', stock: '애플', type: '매도', quantity: 2, price: '$185', profit: '+$20' },
  ];

  return (
    <Box sx={{ 
      minHeight: '100vh',
      backgroundColor: '#F7F8FA',
      p: 3
    }}>
      {/* 누적 수익 */}
      <Card sx={{ 
        bgcolor: '#FFFFFF',
        borderRadius: '12px',
        p: 4,
        textAlign: 'center',
        mb: 3,
        boxShadow: 'none'
      }}>
        <Typography sx={{ 
          fontSize: '16px',
          color: '#666666',
          mb: 2
        }}>
          누적 수익
        </Typography>
        <Typography sx={{ 
          fontSize: '36px',
          fontWeight: 700,
          color: '#00C853',
          mb: 3
        }}>
          +387,000원
        </Typography>
        <Typography sx={{ 
          fontSize: '18px',
          fontWeight: 600,
          color: '#00C853'
        }}>
          +12.5%
        </Typography>
      </Card>

      {/* 거래 기록 */}
      <Stack spacing={2}>
        {records.map((record, index) => (
          <Card key={index} sx={{
            bgcolor: '#FFFFFF',
            borderRadius: '12px',
            p: 3,
            boxShadow: 'none'
          }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Box>
                <Typography sx={{ 
                  fontSize: '14px',
                  color: '#666666',
                  mb: 0.5
                }}>
                  {new Date(record.date).toLocaleDateString('ko-KR', {
                    month: 'long',
                    day: 'numeric'
                  })}
                </Typography>
                <Typography sx={{ 
                  fontSize: '18px',
                  fontWeight: 700,
                  color: '#1A1A1A',
                  mb: 0.5
                }}>
                  {record.stock}
                </Typography>
                <Typography sx={{ 
                  fontSize: '14px',
                  color: '#666666'
                }}>
                  {record.type} {record.quantity}주 × {record.price}
                </Typography>
              </Box>
              <Box sx={{ textAlign: 'right' }}>
                {record.profit ? (
                  <Typography sx={{ 
                    fontSize: '16px',
                    fontWeight: 600,
                    color: record.profit.includes('+') ? '#00C853' : '#FF5252'
                  }}>
                    {record.profit}
                  </Typography>
                ) : (
                  <Typography sx={{ 
                    fontSize: '14px',
                    color: '#666666'
                  }}>
                    {record.type} 완료
                  </Typography>
                )}
              </Box>
            </Box>
          </Card>
        ))}
      </Stack>
    </Box>
  );
};

export default History;