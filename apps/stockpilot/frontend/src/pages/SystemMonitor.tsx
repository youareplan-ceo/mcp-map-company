/**
 * 시스템 모니터링 메인 페이지
 * 실시간 상태 대시보드 및 비용 추적을 한 곳에 통합
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Grid,
  Typography,
  Tabs,
  Tab,
  Paper,
  Alert,
  Chip,
  Button,
  Switch,
  FormControlLabel,
  Tooltip,
  IconButton,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Settings as SettingsIcon,
  TrendingUp as TrendingUpIcon,
  Assessment as AssessmentIcon,
  Notifications as NotificationsIcon,
  Security as SecurityIcon,
} from '@mui/icons-material';

// 커스텀 컴포넌트 import
import { SystemStatusDashboard } from '../components/dashboard/SystemStatusDashboard';
import { UsageCostDashboard } from '../components/dashboard/UsageCostDashboard';
import { EnhancedWebSocketService } from '../services/enhancedWebSocket';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`monitor-tabpanel-${index}`}
      aria-labelledby={`monitor-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

export const SystemMonitor: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [isRealTimeEnabled, setIsRealTimeEnabled] = useState(true);
  const [wsConnectionStatus, setWsConnectionStatus] = useState<'connected' | 'disconnected' | 'connecting'>('disconnected');
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [alerts, setAlerts] = useState<Array<{id: string, type: 'warning' | 'error' | 'info', message: string}>>([]);

  // WebSocket 서비스 인스턴스
  const [wsService] = useState(() => EnhancedWebSocketService.getInstance());

  useEffect(() => {
    // WebSocket 연결 설정
    if (isRealTimeEnabled) {
      try {
        wsService.connect();
        setWsConnectionStatus('connecting');

        // 연결 이벤트 리스너
        wsService.on('connected', () => {
          setWsConnectionStatus('connected');
          setLastUpdate(new Date());
          
          // 필요한 이벤트 구독
          wsService.subscribeTo([
            'system:status',
            'system:usage',
            'price:update',
            'signal:update'
          ]);
        });

        wsService.on('disconnected', (reason: string) => {
          setWsConnectionStatus('disconnected');
          addAlert('warning', `WebSocket 연결이 끊어졌습니다: ${reason}`);
        });

        wsService.on('reconnecting', (attempt: number) => {
          setWsConnectionStatus('connecting');
          addAlert('info', `재연결 시도 중... (${attempt}회차)`);
        });

        wsService.on('error', (error: Error) => {
          addAlert('error', `WebSocket 오류: ${error.message}`);
        });

        // 시스템 상태 업데이트 처리
        wsService.on('system:status', (data) => {
          setLastUpdate(new Date());
          
          // 시스템 상태에 따른 알림
          if (data.overall_status === 'degraded') {
            addAlert('warning', '일부 서비스에서 성능 저하가 발생하고 있습니다.');
          } else if (data.overall_status === 'outage') {
            addAlert('error', '시스템 장애가 발생했습니다.');
          }
        });

        // 사용량 업데이트 처리
        wsService.on('system:usage', (data) => {
          setLastUpdate(new Date());
          
          // 비용 임계치 경고
          if (data.usage_percent >= 80) {
            addAlert('warning', `일일 사용량이 ${data.usage_percent}%에 도달했습니다.`);
          }
        });

      } catch (error) {
        console.error('WebSocket 설정 실패:', error);
        addAlert('error', 'WebSocket 연결을 설정할 수 없습니다.');
      }
    } else {
      wsService.disconnect();
      setWsConnectionStatus('disconnected');
    }

    return () => {
      if (wsService) {
        wsService.disconnect();
      }
    };
  }, [isRealTimeEnabled, wsService]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleRealTimeToggle = (event: React.ChangeEvent<HTMLInputElement>) => {
    setIsRealTimeEnabled(event.target.checked);
  };

  const addAlert = (type: 'warning' | 'error' | 'info', message: string) => {
    const newAlert = {
      id: Date.now().toString(),
      type,
      message,
    };
    
    setAlerts(prev => [newAlert, ...prev.slice(0, 4)]); // 최대 5개까지만 유지
    
    // 5초 후 자동 제거
    setTimeout(() => {
      setAlerts(prev => prev.filter(alert => alert.id !== newAlert.id));
    }, 5000);
  };

  const handleRefreshAll = () => {
    setLastUpdate(new Date());
    // 모든 컴포넌트에 새로고침 신호를 보낼 수 있음
    window.dispatchEvent(new CustomEvent('refresh-dashboards'));
  };

  const getConnectionStatusColor = () => {
    switch (wsConnectionStatus) {
      case 'connected': return 'success';
      case 'connecting': return 'warning';
      case 'disconnected': return 'error';
      default: return 'default';
    }
  };

  const getConnectionStatusText = () => {
    switch (wsConnectionStatus) {
      case 'connected': return '실시간 연결됨';
      case 'connecting': return '연결 중...';
      case 'disconnected': return '연결 끊어짐';
      default: return '알 수 없음';
    }
  };

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      {/* 헤더 섹션 */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4" fontWeight={600} color="primary">
            시스템 모니터링
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            StockPilot AI 시스템 상태 및 성능 대시보드
          </Typography>
        </Box>
        
        <Box display="flex" alignItems="center" gap={2}>
          {/* 실시간 연결 상태 */}
          <Chip 
            icon={<TrendingUpIcon />}
            label={getConnectionStatusText()}
            color={getConnectionStatusColor() as any}
            variant={wsConnectionStatus === 'connected' ? 'filled' : 'outlined'}
            size="small"
          />
          
          {/* 마지막 업데이트 시간 */}
          <Typography variant="caption" color="text.secondary">
            마지막 업데이트: {lastUpdate.toLocaleTimeString()}
          </Typography>
          
          {/* 실시간 토글 */}
          <FormControlLabel
            control={
              <Switch
                checked={isRealTimeEnabled}
                onChange={handleRealTimeToggle}
                color="primary"
              />
            }
            label="실시간 모드"
          />
          
          {/* 새로고침 버튼 */}
          <Tooltip title="전체 새로고침">
            <IconButton onClick={handleRefreshAll} color="primary">
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          
          {/* 설정 버튼 */}
          <Tooltip title="모니터링 설정">
            <IconButton color="primary">
              <SettingsIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* 알림 영역 */}
      {alerts.length > 0 && (
        <Box mb={3}>
          {alerts.map((alert) => (
            <Alert 
              key={alert.id} 
              severity={alert.type} 
              sx={{ mb: 1 }}
              onClose={() => setAlerts(prev => prev.filter(a => a.id !== alert.id))}
            >
              {alert.message}
            </Alert>
          ))}
        </Box>
      )}

      {/* 탭 네비게이션 */}
      <Paper sx={{ mb: 3 }}>
        <Tabs 
          value={activeTab} 
          onChange={handleTabChange}
          variant="fullWidth"
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab 
            icon={<AssessmentIcon />} 
            label="시스템 상태" 
            iconPosition="start"
            sx={{ minHeight: 64 }}
          />
          <Tab 
            icon={<TrendingUpIcon />} 
            label="사용량 & 비용" 
            iconPosition="start"
            sx={{ minHeight: 64 }}
          />
          <Tab 
            icon={<SecurityIcon />} 
            label="보안 & 성능" 
            iconPosition="start"
            sx={{ minHeight: 64 }}
          />
          <Tab 
            icon={<NotificationsIcon />} 
            label="알림 & 로그" 
            iconPosition="start"
            sx={{ minHeight: 64 }}
          />
        </Tabs>
      </Paper>

      {/* 탭 컨텐츠 */}
      <TabPanel value={activeTab} index={0}>
        <SystemStatusDashboard 
          refreshInterval={isRealTimeEnabled ? 30000 : 0}
        />
      </TabPanel>

      <TabPanel value={activeTab} index={1}>
        <UsageCostDashboard 
          refreshInterval={isRealTimeEnabled ? 60000 : 0}
        />
      </TabPanel>

      <TabPanel value={activeTab} index={2}>
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Paper sx={{ p: 3, textAlign: 'center' }}>
              <SecurityIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
              <Typography variant="h6" mb={1}>
                보안 & 성능 모니터링
              </Typography>
              <Typography variant="body2" color="text.secondary" mb={2}>
                시스템 보안 상태 및 성능 지표를 실시간으로 모니터링합니다.
              </Typography>
              <Button variant="outlined" color="primary">
                상세 보고서 보기
              </Button>
            </Paper>
          </Grid>
        </Grid>
      </TabPanel>

      <TabPanel value={activeTab} index={3}>
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Paper sx={{ p: 3, textAlign: 'center' }}>
              <NotificationsIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
              <Typography variant="h6" mb={1}>
                알림 & 로그 관리
              </Typography>
              <Typography variant="body2" color="text.secondary" mb={2}>
                시스템 알림 설정 및 로그 분석 도구를 제공합니다.
              </Typography>
              <Button variant="outlined" color="primary">
                로그 분석 보기
              </Button>
            </Paper>
          </Grid>
        </Grid>
      </TabPanel>

      {/* 푸터 정보 */}
      <Box 
        mt={4} 
        py={2} 
        textAlign="center" 
        borderTop={1} 
        borderColor="divider"
      >
        <Typography variant="caption" color="text.secondary">
          StockPilot AI 시스템 모니터링 v1.0.0 | 
          WebSocket 연결: {wsConnectionStatus} | 
          실시간 모드: {isRealTimeEnabled ? '활성화' : '비활성화'}
        </Typography>
      </Box>
    </Container>
  );
};