/**
 * 알림 설정 화면 - 매수/매도 타이밍 알림
 * 카카오뱅크/토스 스타일의 사용자 친화적 UI
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Card,
  CardContent,
  Typography,
  Switch,
  Button,
  Grid,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Alert,
  Paper,
  IconButton,
  Slider,
  FormControlLabel,
  Badge
} from '@mui/material';
import {
  Notifications as NotificationsIcon,
  NotificationImportant as NotificationImportantIcon,
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Settings as SettingsIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Timeline as TimelineIcon,
  VolumeUp as VolumeUpIcon,
  Phone as PhoneIcon,
  Email as EmailIcon
} from '@mui/icons-material';

// 알림 설정 타입 정의
interface AlertRule {
  id: string;
  symbol: string;
  name: string;
  type: 'price_target' | 'price_change' | 'volume_spike' | 'ai_signal';
  condition: 'above' | 'below' | 'change_percent';
  value: number;
  enabled: boolean;
  created_at: string;
}

interface NotificationSettings {
  push_enabled: boolean;
  email_enabled: boolean;
  sms_enabled: boolean;
  ai_signal_enabled: boolean;
  market_hours_only: boolean;
  quiet_hours_start: string;
  quiet_hours_end: string;
}

interface NewRuleState {
  symbol: string;
  name: string;
  type: 'price_target' | 'price_change' | 'volume_spike' | 'ai_signal';
  condition: 'above' | 'below' | 'change_percent';
  value: number;
}

// 투자 의사결정 중심 색상 스킴
const investmentColors = {
  profit: '#1976d2',      // 수익/기회는 파란색
  loss: '#d32f2f',        // 손실/위험은 빨간색
  neutral: '#757575',      // 중립은 회색
  warning: '#ff9800',      // 경고는 주황색
  success: '#388e3c',      // 성공은 녹색
  background: '#f8fafc',
  cardBackground: '#ffffff'
};

export const AlertSettings: React.FC = () => {
  const [alertRules, setAlertRules] = useState<AlertRule[]>([]);
  const [notificationSettings, setNotificationSettings] = useState<NotificationSettings>({
    push_enabled: true,
    email_enabled: false,
    sms_enabled: false,
    ai_signal_enabled: true,
    market_hours_only: false,
    quiet_hours_start: '22:00',
    quiet_hours_end: '08:00'
  });
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<AlertRule | null>(null);
  const [newRule, setNewRule] = useState<NewRuleState>({
    symbol: '',
    name: '',
    type: 'price_target',
    condition: 'above',
    value: 0
  });

  // 기본 알림 규칙들 (데모 데이터)
  useEffect(() => {
    setAlertRules([
      {
        id: '1',
        symbol: 'AAPL',
        name: 'Apple Inc.',
        type: 'price_target',
        condition: 'above',
        value: 240,
        enabled: true,
        created_at: '2024-01-15'
      },
      {
        id: '2',
        symbol: '005930.KS',
        name: '삼성전자',
        type: 'price_change',
        condition: 'change_percent',
        value: 5,
        enabled: true,
        created_at: '2024-01-14'
      },
      {
        id: '3',
        symbol: 'TSLA',
        name: 'Tesla Inc.',
        type: 'ai_signal',
        condition: 'above',
        value: 80,
        enabled: false,
        created_at: '2024-01-13'
      }
    ]);
  }, []);

  // 알림 규칙 추가
  const handleAddRule = () => {
    if (newRule.symbol && newRule.name && newRule.value > 0) {
      const rule: AlertRule = {
        id: Date.now().toString(),
        symbol: newRule.symbol,
        name: newRule.name,
        type: newRule.type,
        condition: newRule.condition,
        value: newRule.value,
        enabled: true,
        created_at: new Date().toISOString().substring(0, 10)
      };
      setAlertRules([...alertRules, rule]);
      setNewRule({
        symbol: '',
        name: '',
        type: 'price_target',
        condition: 'above',
        value: 0
      });
      setAddDialogOpen(false);
    }
  };

  // 알림 규칙 삭제
  const handleDeleteRule = (id: string) => {
    setAlertRules(alertRules.filter(rule => rule.id !== id));
  };

  // 알림 규칙 토글
  const handleToggleRule = (id: string) => {
    setAlertRules(alertRules.map(rule => 
      rule.id === id ? { ...rule, enabled: !rule.enabled } : rule
    ));
  };

  // 알림 설정 업데이트
  const handleSettingsChange = (setting: keyof NotificationSettings, value: boolean | string) => {
    setNotificationSettings({
      ...notificationSettings,
      [setting]: value
    });
  };

  // 알림 타입별 아이콘
  const getAlertIcon = (type: string) => {
    switch (type) {
      case 'price_target': return <TrendingUpIcon />;
      case 'price_change': return <TimelineIcon />;
      case 'volume_spike': return <VolumeUpIcon />;
      case 'ai_signal': return <NotificationImportantIcon />;
      default: return <NotificationsIcon />;
    }
  };

  // 알림 타입 한글 변환
  const getAlertTypeText = (type: string) => {
    switch (type) {
      case 'price_target': return '목표가 도달';
      case 'price_change': return '가격 변동';
      case 'volume_spike': return '거래량 급증';
      case 'ai_signal': return 'AI 신호';
      default: return type;
    }
  };

  // 조건 텍스트
  const getConditionText = (rule: AlertRule) => {
    switch (rule.type) {
      case 'price_target':
        return `${rule.condition === 'above' ? '이상' : '이하'} $${rule.value}`;
      case 'price_change':
        return `${rule.value}% 이상 변동`;
      case 'volume_spike':
        return `${rule.value}배 이상 급증`;
      case 'ai_signal':
        return `신뢰도 ${rule.value}% 이상`;
      default:
        return `${rule.value}`;
    }
  };

  return (
    <Container maxWidth="lg" sx={{ py: 3 }}>
      {/* 헤더 */}
      <Box mb={3}>
        <Typography variant="h4" fontWeight={700} color={investmentColors.neutral} gutterBottom>
          알림 설정
        </Typography>
        <Typography variant="body1" color="text.secondary">
          매수/매도 타이밍과 주요 이벤트 알림을 설정하세요
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {/* 알림 설정 */}
        <Grid item xs={12} md={4}>
          <Card sx={{ borderRadius: 3, boxShadow: '0 2px 12px rgba(0,0,0,0.08)', mb: 3 }}>
            <CardContent sx={{ p: 3 }}>
              <Box display="flex" alignItems="center" gap={2} mb={3}>
                <SettingsIcon sx={{ color: investmentColors.profit }} />
                <Typography variant="h6" fontWeight={600}>
                  알림 설정
                </Typography>
              </Box>

              <List sx={{ p: 0 }}>
                <ListItem sx={{ px: 0 }}>
                  <ListItemText
                    primary="푸시 알림"
                    secondary="앱 알림을 받습니다"
                  />
                  <ListItemSecondaryAction>
                    <Switch
                      checked={notificationSettings.push_enabled}
                      onChange={(e) => handleSettingsChange('push_enabled', e.target.checked)}
                      color="primary"
                    />
                  </ListItemSecondaryAction>
                </ListItem>

                <ListItem sx={{ px: 0 }}>
                  <ListItemText
                    primary="이메일 알림"
                    secondary="이메일로 알림을 받습니다"
                  />
                  <ListItemSecondaryAction>
                    <Switch
                      checked={notificationSettings.email_enabled}
                      onChange={(e) => handleSettingsChange('email_enabled', e.target.checked)}
                      color="primary"
                    />
                  </ListItemSecondaryAction>
                </ListItem>

                <ListItem sx={{ px: 0 }}>
                  <ListItemText
                    primary="SMS 알림"
                    secondary="문자로 중요 알림을 받습니다"
                  />
                  <ListItemSecondaryAction>
                    <Switch
                      checked={notificationSettings.sms_enabled}
                      onChange={(e) => handleSettingsChange('sms_enabled', e.target.checked)}
                      color="primary"
                    />
                  </ListItemSecondaryAction>
                </ListItem>

                <Divider sx={{ my: 2 }} />

                <ListItem sx={{ px: 0 }}>
                  <ListItemText
                    primary="AI 신호 알림"
                    secondary="AI 매매 신호를 즉시 받습니다"
                  />
                  <ListItemSecondaryAction>
                    <Switch
                      checked={notificationSettings.ai_signal_enabled}
                      onChange={(e) => handleSettingsChange('ai_signal_enabled', e.target.checked)}
                      color="primary"
                    />
                  </ListItemSecondaryAction>
                </ListItem>

                <ListItem sx={{ px: 0 }}>
                  <ListItemText
                    primary="장중에만 알림"
                    secondary="장 운영시간에만 알림을 받습니다"
                  />
                  <ListItemSecondaryAction>
                    <Switch
                      checked={notificationSettings.market_hours_only}
                      onChange={(e) => handleSettingsChange('market_hours_only', e.target.checked)}
                      color="primary"
                    />
                  </ListItemSecondaryAction>
                </ListItem>
              </List>
            </CardContent>
          </Card>

          {/* 방해 금지 시간 */}
          <Card sx={{ borderRadius: 3, boxShadow: '0 2px 12px rgba(0,0,0,0.08)' }}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="h6" fontWeight={600} mb={3}>
                🌙 방해 금지 시간
              </Typography>
              
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    label="시작 시간"
                    type="time"
                    value={notificationSettings.quiet_hours_start}
                    onChange={(e) => handleSettingsChange('quiet_hours_start', e.target.value)}
                    InputLabelProps={{ shrink: true }}
                  />
                </Grid>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    label="종료 시간"
                    type="time"
                    value={notificationSettings.quiet_hours_end}
                    onChange={(e) => handleSettingsChange('quiet_hours_end', e.target.value)}
                    InputLabelProps={{ shrink: true }}
                  />
                </Grid>
              </Grid>

              <Typography variant="body2" color="text.secondary" mt={2}>
                설정된 시간 동안은 긴급 알림만 받습니다
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* 알림 규칙 목록 */}
        <Grid item xs={12} md={8}>
          <Card sx={{ borderRadius: 3, boxShadow: '0 2px 12px rgba(0,0,0,0.08)' }}>
            <CardContent sx={{ p: 3 }}>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
                <Box display="flex" alignItems="center" gap={2}>
                  <NotificationsIcon sx={{ color: investmentColors.profit }} />
                  <Typography variant="h6" fontWeight={600}>
                    알림 규칙
                  </Typography>
                  <Badge badgeContent={alertRules.filter(r => r.enabled).length} color="primary">
                    <Chip label="활성" size="small" />
                  </Badge>
                </Box>
                <Button
                  startIcon={<AddIcon />}
                  variant="contained"
                  onClick={() => setAddDialogOpen(true)}
                  sx={{
                    bgcolor: investmentColors.profit,
                    '&:hover': { bgcolor: '#1565c0' }
                  }}
                >
                  규칙 추가
                </Button>
              </Box>

              {alertRules.length > 0 ? (
                <List sx={{ p: 0 }}>
                  {alertRules.map((rule, index) => (
                    <React.Fragment key={rule.id}>
                      <ListItem
                        sx={{
                          px: 0,
                          py: 2,
                          opacity: rule.enabled ? 1 : 0.6
                        }}
                      >
                        <Box display="flex" alignItems="center" gap={2} mr={2}>
                          {getAlertIcon(rule.type)}
                          <Switch
                            checked={rule.enabled}
                            onChange={() => handleToggleRule(rule.id)}
                            color="primary"
                            size="small"
                          />
                        </Box>
                        
                        <ListItemText
                          primary={
                            <Box display="flex" alignItems="center" gap={1}>
                              <Typography variant="subtitle1" fontWeight={600}>
                                {rule.name}
                              </Typography>
                              <Chip
                                label={getAlertTypeText(rule.type)}
                                size="small"
                                color="primary"
                                variant="outlined"
                              />
                            </Box>
                          }
                          secondary={
                            <Box>
                              <Typography variant="body2" color="text.secondary">
                                {rule.symbol} - {getConditionText(rule)}
                              </Typography>
                              <Typography variant="caption" color="text.disabled">
                                생성일: {rule.created_at}
                              </Typography>
                            </Box>
                          }
                        />

                        <Box display="flex" gap={1}>
                          <IconButton
                            size="small"
                            onClick={() => {
                              setEditingRule(rule);
                              setNewRule({
                                symbol: rule.symbol,
                                name: rule.name,
                                type: rule.type,
                                condition: rule.condition,
                                value: rule.value
                              });
                              setAddDialogOpen(true);
                            }}
                          >
                            <EditIcon fontSize="small" />
                          </IconButton>
                          <IconButton
                            size="small"
                            onClick={() => handleDeleteRule(rule.id)}
                            sx={{ color: investmentColors.loss }}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Box>
                      </ListItem>
                      {index < alertRules.length - 1 && <Divider />}
                    </React.Fragment>
                  ))}
                </List>
              ) : (
                <Alert severity="info" sx={{ borderRadius: 2 }}>
                  설정된 알림 규칙이 없습니다. 새로운 규칙을 추가해보세요.
                </Alert>
              )}
            </CardContent>
          </Card>

          {/* 최근 알림 */}
          <Card sx={{ mt: 3, borderRadius: 3, boxShadow: '0 2px 12px rgba(0,0,0,0.08)' }}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="h6" fontWeight={600} mb={3}>
                📬 최근 알림
              </Typography>
              
              <List sx={{ p: 0 }}>
                <ListItem sx={{ px: 0 }}>
                  <ListItemText
                    primary="Apple Inc. 목표가 도달"
                    secondary="AAPL이 $240.00을 돌파했습니다 • 2시간 전"
                  />
                  <Chip label="매수 신호" color="success" size="small" />
                </ListItem>
                
                <Divider />
                
                <ListItem sx={{ px: 0 }}>
                  <ListItemText
                    primary="삼성전자 급등 알림"
                    secondary="005930이 5% 이상 상승했습니다 • 4시간 전"
                  />
                  <Chip label="급등" color="warning" size="small" />
                </ListItem>
                
                <Divider />
                
                <ListItem sx={{ px: 0 }}>
                  <ListItemText
                    primary="AI 매수 신호"
                    secondary="Tesla Inc.에 대한 강력한 매수 신호가 발생했습니다 • 1일 전"
                  />
                  <Chip label="AI 신호" color="primary" size="small" />
                </ListItem>
              </List>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* 알림 규칙 추가/편집 다이얼로그 */}
      <Dialog
        open={addDialogOpen}
        onClose={() => {
          setAddDialogOpen(false);
          setEditingRule(null);
        }}
        maxWidth="sm"
        fullWidth
        PaperProps={{ sx: { borderRadius: 3 } }}
      >
        <DialogTitle>
          {editingRule ? '알림 규칙 편집' : '새 알림 규칙 추가'}
        </DialogTitle>
        
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={6}>
              <TextField
                fullWidth
                label="종목 코드"
                value={newRule.symbol}
                onChange={(e) => setNewRule({ ...newRule, symbol: e.target.value })}
                placeholder="AAPL, 005930 등"
              />
            </Grid>
            <Grid item xs={6}>
              <TextField
                fullWidth
                label="종목명"
                value={newRule.name}
                onChange={(e) => setNewRule({ ...newRule, name: e.target.value })}
                placeholder="Apple Inc."
              />
            </Grid>
            
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>알림 타입</InputLabel>
                <Select
                  value={newRule.type}
                  onChange={(e) => setNewRule({ ...newRule, type: e.target.value as any })}
                  label="알림 타입"
                >
                  <MenuItem value="price_target">목표가 도달</MenuItem>
                  <MenuItem value="price_change">가격 변동</MenuItem>
                  <MenuItem value="volume_spike">거래량 급증</MenuItem>
                  <MenuItem value="ai_signal">AI 신호</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            {newRule.type === 'price_target' && (
              <Grid item xs={12}>
                <FormControl fullWidth sx={{ mb: 2 }}>
                  <InputLabel>조건</InputLabel>
                  <Select
                    value={newRule.condition}
                    onChange={(e) => setNewRule({ ...newRule, condition: e.target.value as any })}
                    label="조건"
                  >
                    <MenuItem value="above">이상</MenuItem>
                    <MenuItem value="below">이하</MenuItem>
                  </Select>
                </FormControl>
                <TextField
                  fullWidth
                  label="목표 가격 ($)"
                  type="number"
                  value={newRule.value}
                  onChange={(e) => setNewRule({ ...newRule, value: Number(e.target.value) })}
                />
              </Grid>
            )}

            {newRule.type === 'price_change' && (
              <Grid item xs={12}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  가격 변동률 (%)
                </Typography>
                <Slider
                  value={newRule.value}
                  onChange={(e, value) => setNewRule({ ...newRule, value: value as number })}
                  valueLabelDisplay="auto"
                  min={1}
                  max={20}
                  marks={[
                    { value: 1, label: '1%' },
                    { value: 5, label: '5%' },
                    { value: 10, label: '10%' },
                    { value: 20, label: '20%' }
                  ]}
                />
              </Grid>
            )}

            {newRule.type === 'volume_spike' && (
              <Grid item xs={12}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  거래량 배수
                </Typography>
                <Slider
                  value={newRule.value}
                  onChange={(e, value) => setNewRule({ ...newRule, value: value as number })}
                  valueLabelDisplay="auto"
                  min={2}
                  max={10}
                  step={0.5}
                  marks={[
                    { value: 2, label: '2배' },
                    { value: 5, label: '5배' },
                    { value: 10, label: '10배' }
                  ]}
                />
              </Grid>
            )}

            {newRule.type === 'ai_signal' && (
              <Grid item xs={12}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  최소 신뢰도 (%)
                </Typography>
                <Slider
                  value={newRule.value}
                  onChange={(e, value) => setNewRule({ ...newRule, value: value as number })}
                  valueLabelDisplay="auto"
                  min={50}
                  max={95}
                  step={5}
                  marks={[
                    { value: 50, label: '50%' },
                    { value: 70, label: '70%' },
                    { value: 85, label: '85%' },
                    { value: 95, label: '95%' }
                  ]}
                />
              </Grid>
            )}
          </Grid>
        </DialogContent>

        <DialogActions sx={{ p: 3 }}>
          <Button
            onClick={() => {
              setAddDialogOpen(false);
              setEditingRule(null);
            }}
          >
            취소
          </Button>
          <Button
            variant="contained"
            onClick={handleAddRule}
            disabled={!newRule.symbol || !newRule.name || newRule.value <= 0}
            sx={{
              bgcolor: investmentColors.profit,
              '&:hover': { bgcolor: '#1565c0' }
            }}
          >
            {editingRule ? '수정' : '추가'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default AlertSettings;