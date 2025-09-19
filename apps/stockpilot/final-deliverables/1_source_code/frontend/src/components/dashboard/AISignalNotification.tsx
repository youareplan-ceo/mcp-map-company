/**
 * AI 투자 시그널 실시간 알림 컴포넌트
 * WebSocket을 통한 실시간 시그널 표시
 */

import React, { useState, useCallback, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Chip,
  IconButton,
  Tooltip,
  Alert,
  Fade,
  Card,
  CardContent,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  Divider,
  Badge,
  CircularProgress
} from '@mui/material';
import {
  TrendingUp as BuyIcon,
  TrendingDown as SellIcon,
  Remove as HoldIcon,
  Psychology as AIIcon,
  Close as CloseIcon,
  Visibility as ViewIcon,
  NotificationsActive as NotificationIcon,
  Timeline as AnalysisIcon,
  Assessment as AssessmentIcon
} from '@mui/icons-material';
import { 
  useWebSocket, 
  AISignalsMessage,
  WebSocketState 
} from '../../hooks/useWebSocket';

// AI 시그널 데이터 타입
interface AISignal {
  id: string;
  symbol: string;
  company_name: string;
  signal_type: 'BUY' | 'SELL' | 'HOLD';
  confidence: number;
  strength: 'HIGH' | 'MEDIUM' | 'LOW';
  current_price: number;
  target_price?: number;
  expected_return?: number;
  risk_level: 'HIGH' | 'MEDIUM' | 'LOW';
  reasoning: string;
  technical_score: number;
  fundamental_score: number;
  sentiment_score: number;
  created_at: string;
  market_state: string;
}

export const AISignalNotification: React.FC = () => {
  const [signals, setSignals] = useState<AISignal[]>([]);
  const [newSignalAlert, setNewSignalAlert] = useState<AISignal | null>(null);
  const [selectedSignal, setSelectedSignal] = useState<AISignal | null>(null);
  const [signalCount, setSignalCount] = useState(0);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  // AI 시그널 수신 핸들러
  const handleAISignals = useCallback((message: AISignalsMessage) => {
    console.log('🤖 실시간 AI 시그널 수신:', message.payload.signals.length);
    
    const newSignals = message.payload.signals;
    
    // 새로운 시그널이 있으면 알림 표시
    if (newSignals.length > 0 && signals.length > 0) {
      const latestSignal = newSignals[0];
      if (latestSignal) {
        const isNewSignal = !signals.some(s => s.id === latestSignal.id);
        
        if (isNewSignal) {
          setNewSignalAlert(latestSignal);
          // 5초 후 알림 자동 숨김
          setTimeout(() => setNewSignalAlert(null), 5000);
        }
      }
    }
    
    setSignals(newSignals);
    setSignalCount(prev => prev + newSignals.length);
    setLastUpdate(new Date());
  }, [signals]);

  // WebSocket 연결
  const { connectionState, isConnected } = useWebSocket({
    channels: ['ai_signals'],
    onAISignals: handleAISignals,
    autoConnect: true
  });

  // 시그널 타입별 아이콘
  const getSignalIcon = (signalType: string) => {
    switch (signalType) {
      case 'BUY':
        return <BuyIcon color="success" />;
      case 'SELL':
        return <SellIcon color="error" />;
      case 'HOLD':
        return <HoldIcon color="warning" />;
      default:
        return <AIIcon />;
    }
  };

  // 시그널 타입별 색상
  const getSignalColor = (signalType: string) => {
    switch (signalType) {
      case 'BUY':
        return 'success';
      case 'SELL':
        return 'error';
      case 'HOLD':
        return 'warning';
      default:
        return 'primary';
    }
  };

  // 신뢰도 색상
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'success';
    if (confidence >= 0.6) return 'warning';
    return 'error';
  };

  // 위험도 색상
  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'LOW':
        return 'success';
      case 'MEDIUM':
        return 'warning';
      case 'HIGH':
        return 'error';
      default:
        return 'primary';
    }
  };

  // 시그널 상세 보기
  const handleViewSignal = (signal: AISignal) => {
    setSelectedSignal(signal);
  };

  return (
    <>
      {/* 메인 시그널 위젯 */}
      <Paper sx={{ p: 3 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Box display="flex" alignItems="center" gap={1}>
            <AIIcon color="primary" />
            <Typography variant="h6" fontWeight={600}>
              AI 투자 시그널
            </Typography>
            {isConnected && signals.length > 0 && (
              <Badge badgeContent={signals.length} color="primary">
                <Chip label="LIVE" size="small" color="success" />
              </Badge>
            )}
          </Box>
          
          <Box display="flex" alignItems="center" gap={1}>
            {connectionState === WebSocketState.CONNECTING && (
              <CircularProgress size={16} />
            )}
            {lastUpdate && (
              <Typography variant="caption" color="text.secondary">
                마지막 업데이트: {lastUpdate.toLocaleTimeString()}
              </Typography>
            )}
          </Box>
        </Box>

        {/* 연결 상태에 따른 표시 */}
        {!isConnected ? (
          <Alert severity="info">
            AI 시그널 서비스에 연결하는 중입니다...
          </Alert>
        ) : signals.length === 0 ? (
          <Alert severity="info">
            AI 시그널을 생성 중입니다. 잠시만 기다려 주세요.
          </Alert>
        ) : (
          <Box>
            {/* 시그널 목록 */}
            {signals.slice(0, 3).map((signal, index) => (
              <Card 
                key={signal.id} 
                variant="outlined" 
                sx={{ 
                  mb: index < 2 ? 1 : 0,
                  bgcolor: signal.signal_type === 'BUY' ? 'success.light' : 
                           signal.signal_type === 'SELL' ? 'error.light' : 'warning.light',
                  opacity: signal.signal_type === 'BUY' ? 0.1 : 
                           signal.signal_type === 'SELL' ? 0.1 : 0.1,
                  '&:hover': { opacity: 0.15 }
                }}
              >
                <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                  <Box display="flex" justifyContent="space-between" alignItems="start">
                    <Box>
                      <Box display="flex" alignItems="center" gap={1} mb={1}>
                        {getSignalIcon(signal.signal_type)}
                        <Typography variant="subtitle2" fontWeight={600}>
                          {signal.symbol}
                        </Typography>
                        <Chip 
                          label={signal.signal_type}
                          color={getSignalColor(signal.signal_type) as any}
                          size="small"
                        />
                        <Chip 
                          label={`${(signal.confidence * 100).toFixed(0)}%`}
                          color={getConfidenceColor(signal.confidence) as any}
                          size="small"
                          variant="outlined"
                        />
                      </Box>
                      
                      <Typography variant="caption" color="text.secondary" display="block">
                        현재가: ${signal.current_price}
                        {signal.target_price && ` → 목표가: $${signal.target_price}`}
                        {signal.expected_return && 
                          ` (${signal.expected_return > 0 ? '+' : ''}${signal.expected_return.toFixed(1)}%)`
                        }
                      </Typography>
                      
                      <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
                        {signal.reasoning.length > 60 ? 
                          `${signal.reasoning.substring(0, 60)}...` : 
                          signal.reasoning
                        }
                      </Typography>
                    </Box>
                    
                    <Box display="flex" alignItems="center" gap={1}>
                      <Chip 
                        label={signal.risk_level}
                        color={getRiskColor(signal.risk_level) as any}
                        size="small"
                        variant="outlined"
                      />
                      <Tooltip title="상세 보기">
                        <IconButton 
                          size="small" 
                          onClick={() => handleViewSignal(signal)}
                        >
                          <ViewIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            ))}
            
            {signals.length > 3 && (
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                총 {signals.length}개의 시그널이 있습니다.
              </Typography>
            )}
          </Box>
        )}
      </Paper>

      {/* 새 시그널 알림 */}
      {newSignalAlert && (
        <Fade in={!!newSignalAlert}>
          <Alert 
            severity="info"
            sx={{ 
              position: 'fixed',
              top: 80,
              right: 20,
              zIndex: 9999,
              minWidth: 300,
              maxWidth: 400
            }}
            icon={<NotificationIcon />}
            action={
              <IconButton size="small" onClick={() => setNewSignalAlert(null)}>
                <CloseIcon />
              </IconButton>
            }
          >
            <Typography variant="subtitle2" fontWeight={600}>
              새로운 AI 시그널: {newSignalAlert.symbol} {newSignalAlert.signal_type}
            </Typography>
            <Typography variant="caption" display="block">
              신뢰도: {(newSignalAlert.confidence * 100).toFixed(0)}% | 
              위험도: {newSignalAlert.risk_level}
            </Typography>
          </Alert>
        </Fade>
      )}

      {/* 시그널 상세 보기 다이얼로그 */}
      <Dialog 
        open={!!selectedSignal} 
        onClose={() => setSelectedSignal(null)}
        maxWidth="md"
        fullWidth
      >
        {selectedSignal && (
          <>
            <DialogTitle>
              <Box display="flex" alignItems="center" gap={1}>
                {getSignalIcon(selectedSignal.signal_type)}
                <Typography variant="h6">
                  {selectedSignal.symbol} - {selectedSignal.company_name}
                </Typography>
                <Chip 
                  label={selectedSignal.signal_type}
                  color={getSignalColor(selectedSignal.signal_type) as any}
                />
              </Box>
            </DialogTitle>
            
            <DialogContent>
              {/* 기본 정보 */}
              <Box mb={3}>
                <Typography variant="subtitle2" gutterBottom>
                  시그널 정보
                </Typography>
                <Box display="flex" gap={1} mb={2}>
                  <Chip 
                    label={`신뢰도: ${(selectedSignal.confidence * 100).toFixed(0)}%`}
                    color={getConfidenceColor(selectedSignal.confidence) as any}
                  />
                  <Chip 
                    label={`강도: ${selectedSignal.strength}`}
                    variant="outlined"
                  />
                  <Chip 
                    label={`위험도: ${selectedSignal.risk_level}`}
                    color={getRiskColor(selectedSignal.risk_level) as any}
                    variant="outlined"
                  />
                </Box>
                
                <Typography variant="body2" color="text.secondary">
                  생성 시간: {new Date(selectedSignal.created_at).toLocaleString()}
                </Typography>
              </Box>

              {/* 가격 정보 */}
              <Box mb={3}>
                <Typography variant="subtitle2" gutterBottom>
                  가격 정보
                </Typography>
                <Typography variant="body2">
                  현재가: ${selectedSignal.current_price}
                </Typography>
                {selectedSignal.target_price && (
                  <Typography variant="body2">
                    목표가: ${selectedSignal.target_price}
                  </Typography>
                )}
                {selectedSignal.expected_return && (
                  <Typography variant="body2" color={selectedSignal.expected_return > 0 ? 'success.main' : 'error.main'}>
                    예상 수익률: {selectedSignal.expected_return > 0 ? '+' : ''}{selectedSignal.expected_return.toFixed(1)}%
                  </Typography>
                )}
              </Box>

              {/* 분석 점수 */}
              <Box mb={3}>
                <Typography variant="subtitle2" gutterBottom>
                  분석 점수
                </Typography>
                <Box display="flex" gap={2}>
                  <Box textAlign="center">
                    <Typography variant="caption" color="text.secondary">기술적</Typography>
                    <Typography variant="h6" color={selectedSignal.technical_score > 0 ? 'success.main' : 'error.main'}>
                      {selectedSignal.technical_score > 0 ? '+' : ''}{selectedSignal.technical_score.toFixed(2)}
                    </Typography>
                  </Box>
                  <Box textAlign="center">
                    <Typography variant="caption" color="text.secondary">펀더멘털</Typography>
                    <Typography variant="h6" color={selectedSignal.fundamental_score > 0 ? 'success.main' : 'error.main'}>
                      {selectedSignal.fundamental_score > 0 ? '+' : ''}{selectedSignal.fundamental_score.toFixed(2)}
                    </Typography>
                  </Box>
                  <Box textAlign="center">
                    <Typography variant="caption" color="text.secondary">뉴스감성</Typography>
                    <Typography variant="h6" color={selectedSignal.sentiment_score > 0 ? 'success.main' : 'error.main'}>
                      {selectedSignal.sentiment_score > 0 ? '+' : ''}{selectedSignal.sentiment_score.toFixed(2)}
                    </Typography>
                  </Box>
                </Box>
              </Box>

              {/* 분석 근거 */}
              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  AI 분석 근거
                </Typography>
                <Alert severity="info" icon={<AnalysisIcon />}>
                  {selectedSignal.reasoning}
                </Alert>
              </Box>
            </DialogContent>
            
            <DialogActions>
              <Button onClick={() => setSelectedSignal(null)}>
                닫기
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </>
  );
};