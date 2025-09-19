/**
 * 자산 증식 코치 - 모바일 하단 네비게이션
 * 3개 화면만: 홈 / 포트폴리오 / 기록
 * 모바일 전용, 극도의 심플함
 */

import React from 'react';
import {
  BottomNavigation,
  BottomNavigationAction,
  Paper
} from '@mui/material';
import {
  Home as HomeIcon,
  AccountBalanceWallet as PortfolioIcon,
  History as HistoryIcon
} from '@mui/icons-material';

// 자산 증식 코치 색상
const coachColors = {
  primary: '#4B8BF5',     // 토스 블루
  background: '#FFFFFF',  // 흰색 배경
  textSecondary: '#666666' // 회색 텍스트
};

interface MobileBottomNavProps {
  value: number;
  onChange: (newValue: number) => void;
}

export const MobileBottomNav: React.FC<MobileBottomNavProps> = ({
  value,
  onChange
}) => {
  return (
    <Paper 
      sx={{ 
        position: 'fixed', 
        bottom: 0, 
        left: 0, 
        right: 0,
        zIndex: 1000,
        borderTop: '1px solid #F0F0F0',
        borderRadius: '12px 12px 0 0',
        boxShadow: '0 -2px 12px rgba(0,0,0,0.08)'
      }} 
      elevation={0}
    >
      <BottomNavigation
        value={value}
        onChange={(event, newValue) => onChange(newValue)}
        sx={{
          height: 70,
          borderRadius: '12px 12px 0 0',
          '& .MuiBottomNavigationAction-root': {
            color: coachColors.textSecondary,
            fontSize: '14px',
            fontWeight: 500,
            minWidth: 'auto',
            padding: '8px 12px 10px',
            '&.Mui-selected': {
              color: coachColors.primary,
              fontSize: '14px',
              fontWeight: 600
            },
            '& .MuiSvgIcon-root': {
              fontSize: '24px',
              mb: 0.5
            }
          }
        }}
      >
        <BottomNavigationAction 
          label="🏠" 
          icon={<HomeIcon />}
        />
        <BottomNavigationAction 
          label="💼" 
          icon={<PortfolioIcon />}
        />
        <BottomNavigationAction 
          label="📋" 
          icon={<HistoryIcon />}
        />
      </BottomNavigation>
    </Paper>
  );
};

export default MobileBottomNav;