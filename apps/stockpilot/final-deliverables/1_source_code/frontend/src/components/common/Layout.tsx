/**
 * StockPilot AI 메인 레이아웃 컴포넌트
 * 네비게이션, 사이드바, 헤더를 포함한 전체 레이아웃
 */

import React, { useState } from 'react';
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  List,
  Typography,
  Divider,
  IconButton,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Badge,
  Chip,
  useTheme,
  useMediaQuery,
  Avatar
} from '@mui/material';
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  TrendingUp as TrendingUpIcon,
  AccountBalance as PortfolioIcon,
  Notifications as NotificationsIcon,
  Settings as SettingsIcon,
  Help as HelpIcon,
  ExitToApp as LogoutIcon,
  Timeline as SignalsIcon,
  Article as NewsIcon,
  AccountCircle as ProfileIcon
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { DateUtils, MarketUtils } from '../../utils';
import MarketStatusChip from './MarketStatusChip';

const drawerWidth = 240;

interface LayoutProps {
  children: React.ReactNode;
}

interface NavigationItem {
  id: string;
  label: string;
  icon: React.ReactElement;
  path: string;
  badge?: number;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const theme = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const [mobileOpen, setMobileOpen] = useState(false);

  // 네비게이션 메뉴 아이템들
  const navigationItems: NavigationItem[] = [
    {
      id: 'dashboard',
      label: '대시보드',
      icon: <DashboardIcon />,
      path: '/dashboard'
    },
    {
      id: 'analysis',
      label: '종목 분석',
      icon: <TrendingUpIcon />,
      path: '/analysis'
    },
    {
      id: 'signals',
      label: 'AI 시그널',
      icon: <SignalsIcon />,
      path: '/signals',
      badge: 5 // 예시: 새로운 시그널 개수
    },
    {
      id: 'portfolio',
      label: '포트폴리오',
      icon: <PortfolioIcon />,
      path: '/portfolio'
    },
    {
      id: 'news',
      label: '뉴스 분석',
      icon: <NewsIcon />,
      path: '/news'
    }
  ];

  // 하단 메뉴 아이템들
  const bottomNavigationItems: NavigationItem[] = [
    {
      id: 'settings',
      label: '설정',
      icon: <SettingsIcon />,
      path: '/settings'
    },
    {
      id: 'help',
      label: '도움말',
      icon: <HelpIcon />,
      path: '/help'
    }
  ];

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleNavigation = (path: string) => {
    navigate(path);
    if (isMobile) {
      setMobileOpen(false);
    }
  };

  const handleLogout = () => {
    // 로그아웃 로직 구현
    localStorage.removeItem('auth_token');
    navigate('/login');
  };

  // 사이드바 내용
  const drawer = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* 로고 */}
      <Toolbar>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Avatar sx={{ bgcolor: 'primary.main', width: 32, height: 32 }}>
            SP
          </Avatar>
          <Typography variant="h6" noWrap component="div" sx={{ fontWeight: 'bold' }}>
            StockPilot AI
          </Typography>
        </Box>
      </Toolbar>
      
      <Divider />

      {/* 시장 상태 표시 */}
      <Box sx={{ p: 2 }}>
        <MarketStatusChip />
      </Box>

      <Divider />

      {/* 메인 네비게이션 */}
      <List sx={{ flexGrow: 1, pt: 1 }}>
        {navigationItems.map((item) => (
          <ListItem key={item.id} disablePadding>
            <ListItemButton
              selected={location.pathname.startsWith(item.path)}
              onClick={() => handleNavigation(item.path)}
              sx={{
                mx: 1,
                borderRadius: 1,
                '&.Mui-selected': {
                  backgroundColor: theme.palette.primary.main + '20',
                  '& .MuiListItemIcon-root': {
                    color: theme.palette.primary.main,
                  },
                  '& .MuiListItemText-primary': {
                    color: theme.palette.primary.main,
                    fontWeight: 600,
                  }
                }
              }}
            >
              <ListItemIcon>
                {item.badge ? (
                  <Badge badgeContent={item.badge} color="error">
                    {item.icon}
                  </Badge>
                ) : (
                  item.icon
                )}
              </ListItemIcon>
              <ListItemText 
                primary={item.label}
                primaryTypographyProps={{
                  fontSize: '0.9rem'
                }}
              />
            </ListItemButton>
          </ListItem>
        ))}
      </List>

      <Divider />

      {/* 하단 메뉴 */}
      <List>
        {bottomNavigationItems.map((item) => (
          <ListItem key={item.id} disablePadding>
            <ListItemButton
              selected={location.pathname === item.path}
              onClick={() => handleNavigation(item.path)}
              sx={{ mx: 1, borderRadius: 1 }}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText 
                primary={item.label}
                primaryTypographyProps={{
                  fontSize: '0.9rem'
                }}
              />
            </ListItemButton>
          </ListItem>
        ))}
        
        {/* 로그아웃 버튼 */}
        <ListItem disablePadding>
          <ListItemButton
            onClick={handleLogout}
            sx={{ mx: 1, borderRadius: 1 }}
          >
            <ListItemIcon>
              <LogoutIcon />
            </ListItemIcon>
            <ListItemText 
              primary="로그아웃"
              primaryTypographyProps={{
                fontSize: '0.9rem'
              }}
            />
          </ListItemButton>
        </ListItem>
      </List>

      {/* 버전 정보 */}
      <Box sx={{ p: 2, textAlign: 'center' }}>
        <Typography variant="caption" color="text.secondary">
          v1.0.0
        </Typography>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex' }}>
      {/* 앱바 */}
      <AppBar
        position="fixed"
        sx={{
          width: { md: `calc(100% - ${drawerWidth}px)` },
          ml: { md: `${drawerWidth}px` },
          bgcolor: 'background.paper',
          color: 'text.primary',
          borderBottom: '1px solid',
          borderColor: 'divider',
          boxShadow: 0
        }}
      >
        <Toolbar>
          {/* 모바일 메뉴 버튼 */}
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { md: 'none' } }}
          >
            <MenuIcon />
          </IconButton>

          {/* 현재 시간 */}
          <Typography variant="body2" sx={{ mr: 'auto' }}>
            {DateUtils.formatMarketTime(new Date())}
          </Typography>

          {/* 헤더 우측 액션들 */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {/* 알림 */}
            <IconButton size="large" color="inherit">
              <Badge badgeContent={3} color="error">
                <NotificationsIcon />
              </Badge>
            </IconButton>

            {/* 프로필 */}
            <IconButton size="large" color="inherit">
              <ProfileIcon />
            </IconButton>
          </Box>
        </Toolbar>
      </AppBar>

      {/* 사이드바 */}
      <Box
        component="nav"
        sx={{ width: { md: drawerWidth }, flexShrink: { md: 0 } }}
        aria-label="mailbox folders"
      >
        {/* 모바일용 임시 드로어 */}
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true, // 모바일 성능 향상
          }}
          sx={{
            display: { xs: 'block', md: 'none' },
            '& .MuiDrawer-paper': { 
              boxSizing: 'border-box', 
              width: drawerWidth 
            },
          }}
        >
          {drawer}
        </Drawer>
        
        {/* 데스크톱용 고정 드로어 */}
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', md: 'block' },
            '& .MuiDrawer-paper': { 
              boxSizing: 'border-box', 
              width: drawerWidth,
              borderRight: '1px solid',
              borderColor: 'divider'
            },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      {/* 메인 컨텐츠 */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          width: { md: `calc(100% - ${drawerWidth}px)` },
          backgroundColor: 'grey.50',
          minHeight: '100vh'
        }}
      >
        <Toolbar />
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      </Box>
    </Box>
  );
};

export default Layout;