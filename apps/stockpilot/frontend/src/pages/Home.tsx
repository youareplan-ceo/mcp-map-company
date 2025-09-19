import React from 'react';
import { Box, Typography, Card } from '@mui/material';

const Home: React.FC = () => {
  return (
    <Box sx={{ 
      minHeight: '100vh',
      backgroundColor: '#F7F8FA',
      p: 3
    }}>
      {/* 내 자산 */}
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
          내 자산
        </Typography>
        <Typography sx={{ 
          fontSize: '36px',
          fontWeight: 700,
          color: '#1A1A1A',
          mb: 3
        }}>
          1.2억원
        </Typography>
        <Typography sx={{ 
          fontSize: '18px',
          fontWeight: 600,
          color: '#00C853'
        }}>
          +2,400만원 (+25%)
        </Typography>
      </Card>

      {/* 상태 */}
      <Card sx={{ 
        bgcolor: '#FFFFFF',
        borderRadius: '12px',
        p: 3,
        textAlign: 'center',
        boxShadow: 'none',
        border: '2px solid #00C853'
      }}>
        <Typography sx={{ 
          fontSize: '16px',
          fontWeight: 600,
          color: '#00C853',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 1
        }}>
          ✅ 포트폴리오 안정
        </Typography>
      </Card>
    </Box>
  );
};

export default Home;