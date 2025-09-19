/**
 * 자산 증식 코치 - 메인 애플리케이션
 * 3개 화면만: 홈 / 포트폴리오 / 기록
 * 극도의 심플함으로 "자산 증식"에만 집중
 */

import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { Box } from '@mui/material';

// 자산 증식 코치 3개 화면
import Home from './pages/Home';                    // 홈 (자산 현황)
import Portfolio from './pages/Portfolio';          // 포트폴리오 (보유 종목)
import History from './pages/History';              // 기록 (실행 히스토리)

// 모바일 네비게이션
import MobileBottomNav from './components/MobileBottomNav';

// React Query 클라이언트 설정
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5분
    },
  },
});

// 자산 증식 코치 테마
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#4B8BF5', // 토스 블루
    },
    secondary: {
      main: '#00C853', // 수익 녹색
    },
    error: {
      main: '#FF5252', // 손실 빨강
    },
    background: {
      default: '#F7F8FA', // 토스 그레이
      paper: '#FFFFFF',   // 흰색 카드
    },
    text: {
      primary: '#1A1A1A',
      secondary: '#666666',
    },
  },
  typography: {
    fontFamily: [
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      '"Noto Sans KR"',
      'sans-serif',
    ].join(','),
    h4: {
      fontWeight: 700,
      fontSize: '32px', // 금액 표시용
    },
    h6: {
      fontWeight: 600,
      fontSize: '16px', // 일반 텍스트
    },
  },
  shape: {
    borderRadius: 12, // 토스 스타일 radius
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: 'none', // 그림자 제거 (깔끔하게)
          border: 'none',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
          borderRadius: 12,
        },
      },
    },
  },
});

// 네비게이션 컨트롤러
const NavigationController: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  
  // 현재 경로에 따른 네비게이션 값 설정
  const getCurrentNavValue = (): number => {
    switch (location.pathname) {
      case '/': return 0;           // 홈
      case '/portfolio': return 1;  // 포트폴리오 
      case '/history': return 2;    // 기록
      default: return 0;
    }
  };

  const handleNavChange = (newValue: number) => {
    switch (newValue) {
      case 0: navigate('/'); break;          // 홈
      case 1: navigate('/portfolio'); break; // 포트폴리오
      case 2: navigate('/history'); break;   // 기록
    }
  };

  return (
    <MobileBottomNav
      value={getCurrentNavValue()}
      onChange={handleNavChange}
    />
  );
};

const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Router>
          <Box 
            sx={{ 
              flexGrow: 1,
              backgroundColor: 'background.default',
              minHeight: '100vh',
              pb: { xs: 9, sm: 0 } // 모바일 하단 네비게이션 공간
            }}
          >
            {/* 자산 증식 코치 3개 화면만 */}
            <Routes>
              <Route path="/" element={<Home />} />           {/* 홈 (자산 현황) */}
              <Route path="/portfolio" element={<Portfolio />} />  {/* 포트폴리오 (보유 종목) */}
              <Route path="/history" element={<History />} />      {/* 기록 (실행 히스토리) */}
              
              {/* 기본 라우팅 */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
            
            {/* 모바일 하단 네비게이션 (3개 화면만) */}
            <NavigationController />
          </Box>
        </Router>
      </ThemeProvider>
    </QueryClientProvider>
  );
};

export default App;