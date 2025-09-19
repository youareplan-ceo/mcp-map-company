import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  Grid,
  Switch,
  FormControlLabel,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Chip,
  IconButton,
  Slider,
  Avatar,
  Paper,
  Tab,
  Tabs,
} from '@mui/material';
import {
  Settings as SettingsIcon,
  Person,
  Security,
  Palette,
  Language,
  Notifications,
  AccountBalance,
  TrendingUp,
  Info,
  Logout,
  Edit,
  Save,
  Refresh,
  DarkMode,
  LightMode,
  VolumeUp,
  DeviceHub,
  CloudSync,
  Assessment,
} from '@mui/icons-material';

// 투자 의사결정 중심 색상 스킴
const investmentColors = {
  profit: '#1976d2',      // 수익/기회는 파란색
  loss: '#d32f2f',        // 손실/위험은 빨간색
  neutral: '#757575',      // 중립은 회색
  warning: '#ff9800',      // 경고는 주황색
  success: '#388e3c',      // 성공은 녹색
};

// 사용자 정보 인터페이스
interface UserProfile {
  name: string;
  email: string;
  phone: string;
  investmentExperience: 'beginner' | 'intermediate' | 'advanced';
  riskTolerance: 1 | 2 | 3 | 4 | 5;
  investmentGoals: string[];
  preferredMarkets: string[];
}

// 앱 설정 인터페이스
interface AppSettings {
  theme: 'light' | 'dark' | 'auto';
  language: 'ko' | 'en';
  currency: 'KRW' | 'USD';
  dateFormat: 'YYYY-MM-DD' | 'MM/DD/YYYY' | 'DD/MM/YYYY';
  timeFormat: '24h' | '12h';
  autoSync: boolean;
  offlineMode: boolean;
  dataRefreshInterval: 1 | 5 | 10 | 30;
}

// 거래 설정 인터페이스
interface TradingSettings {
  defaultOrderType: 'market' | 'limit';
  confirmBeforeTrade: boolean;
  maxDailyLoss: number;
  autoStopLoss: boolean;
  stopLossPercentage: number;
  takeProfitPercentage: number;
  riskManagementEnabled: boolean;
}

const Settings: React.FC = () => {
  const [selectedTab, setSelectedTab] = useState(0);
  const [userProfile, setUserProfile] = useState<UserProfile>({
    name: '김투자',
    email: 'investor@stockpilot.ai',
    phone: '010-1234-5678',
    investmentExperience: 'intermediate',
    riskTolerance: 3,
    investmentGoals: ['장기투자', '배당수익'],
    preferredMarkets: ['미국주식', '한국주식'],
  });

  const [appSettings, setAppSettings] = useState<AppSettings>({
    theme: 'light',
    language: 'ko',
    currency: 'KRW',
    dateFormat: 'YYYY-MM-DD',
    timeFormat: '24h',
    autoSync: true,
    offlineMode: false,
    dataRefreshInterval: 5,
  });

  const [tradingSettings, setTradingSettings] = useState<TradingSettings>({
    defaultOrderType: 'limit',
    confirmBeforeTrade: true,
    maxDailyLoss: 100000,
    autoStopLoss: true,
    stopLossPercentage: 5,
    takeProfitPercentage: 15,
    riskManagementEnabled: true,
  });

  const [editingProfile, setEditingProfile] = useState(false);
  const [showLogoutDialog, setShowLogoutDialog] = useState(false);

  // 프로필 업데이트
  const handleProfileUpdate = (field: keyof UserProfile, value: any) => {
    setUserProfile(prev => ({ ...prev, [field]: value }));
  };

  // 앱 설정 업데이트
  const handleAppSettingsUpdate = (field: keyof AppSettings, value: any) => {
    setAppSettings(prev => ({ ...prev, [field]: value }));
  };

  // 거래 설정 업데이트
  const handleTradingSettingsUpdate = (field: keyof TradingSettings, value: any) => {
    setTradingSettings(prev => ({ ...prev, [field]: value }));
  };

  // 위험 허용도 레벨 텍스트
  const getRiskToleranceText = (level: number) => {
    switch (level) {
      case 1: return '매우 보수적';
      case 2: return '보수적';
      case 3: return '중립적';
      case 4: return '적극적';
      case 5: return '매우 적극적';
      default: return '중립적';
    }
  };

  // 투자 경험 텍스트
  const getExperienceText = (level: string) => {
    switch (level) {
      case 'beginner': return '초급 (1년 미만)';
      case 'intermediate': return '중급 (1-5년)';
      case 'advanced': return '고급 (5년 이상)';
      default: return '중급';
    }
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 2, mb: 2 }}>
      {/* 페이지 헤더 */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 'bold' }}>
          ⚙️ 설정
        </Typography>
        <Typography variant="subtitle1" color="textSecondary">
          개인화된 투자 환경을 설정하고 관리하세요
        </Typography>
      </Box>

      {/* 탭 메뉴 */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={selectedTab} onChange={(e, newValue) => setSelectedTab(newValue)}>
          <Tab label="프로필" icon={<Person />} />
          <Tab label="앱 설정" icon={<SettingsIcon />} />
          <Tab label="거래 설정" icon={<TrendingUp />} />
          <Tab label="보안" icon={<Security />} />
        </Tabs>
      </Box>

      {/* 탭 1: 프로필 */}
      {selectedTab === 0 && (
        <Grid container spacing={3}>
          {/* 기본 정보 */}
          <Grid item xs={12} md={6}>
            <Card sx={{ boxShadow: 3 }}>
              <CardContent sx={{ p: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                  <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center' }}>
                    <Person sx={{ mr: 1, color: investmentColors.profit }} />
                    기본 정보
                  </Typography>
                  <IconButton onClick={() => setEditingProfile(!editingProfile)}>
                    {editingProfile ? <Save /> : <Edit />}
                  </IconButton>
                </Box>

                <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                  <Avatar 
                    sx={{ 
                      width: 80, 
                      height: 80, 
                      mr: 3, 
                      bgcolor: investmentColors.profit,
                      fontSize: '2rem'
                    }}
                  >
                    {userProfile.name.charAt(0)}
                  </Avatar>
                  <Box>
                    <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                      {userProfile.name}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      {getExperienceText(userProfile.investmentExperience)}
                    </Typography>
                    <Chip 
                      label={`위험도 ${userProfile.riskTolerance}`}
                      size="small"
                      sx={{ 
                        mt: 1,
                        bgcolor: userProfile.riskTolerance <= 2 ? investmentColors.success : 
                               userProfile.riskTolerance === 3 ? investmentColors.warning : investmentColors.loss,
                        color: 'white'
                      }}
                    />
                  </Box>
                </Box>

                <Grid container spacing={2}>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="이름"
                      value={userProfile.name}
                      onChange={(e) => handleProfileUpdate('name', e.target.value)}
                      disabled={!editingProfile}
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="이메일"
                      value={userProfile.email}
                      onChange={(e) => handleProfileUpdate('email', e.target.value)}
                      disabled={!editingProfile}
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="전화번호"
                      value={userProfile.phone}
                      onChange={(e) => handleProfileUpdate('phone', e.target.value)}
                      disabled={!editingProfile}
                    />
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>

          {/* 투자 프로필 */}
          <Grid item xs={12} md={6}>
            <Card sx={{ boxShadow: 3 }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                  <Assessment sx={{ mr: 1, color: investmentColors.profit }} />
                  투자 프로필
                </Typography>

                <Box sx={{ mb: 3 }}>
                  <FormControl fullWidth sx={{ mb: 2 }}>
                    <InputLabel>투자 경험</InputLabel>
                    <Select
                      value={userProfile.investmentExperience}
                      label="투자 경험"
                      onChange={(e) => handleProfileUpdate('investmentExperience', e.target.value)}
                      disabled={!editingProfile}
                    >
                      <MenuItem value="beginner">초급 (1년 미만)</MenuItem>
                      <MenuItem value="intermediate">중급 (1-5년)</MenuItem>
                      <MenuItem value="advanced">고급 (5년 이상)</MenuItem>
                    </Select>
                  </FormControl>

                  <Typography variant="body2" gutterBottom>
                    위험 허용도: {getRiskToleranceText(userProfile.riskTolerance)}
                  </Typography>
                  <Slider
                    value={userProfile.riskTolerance}
                    onChange={(e, value) => handleProfileUpdate('riskTolerance', value)}
                    min={1}
                    max={5}
                    step={1}
                    marks={[
                      { value: 1, label: '보수적' },
                      { value: 3, label: '중립' },
                      { value: 5, label: '적극적' },
                    ]}
                    disabled={!editingProfile}
                  />
                </Box>

                <Divider sx={{ my: 2 }} />

                <Typography variant="subtitle2" gutterBottom>
                  투자 목표
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                  {userProfile.investmentGoals.map((goal) => (
                    <Chip key={goal} label={goal} size="small" color="primary" />
                  ))}
                </Box>

                <Typography variant="subtitle2" gutterBottom>
                  관심 시장
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {userProfile.preferredMarkets.map((market) => (
                    <Chip key={market} label={market} size="small" variant="outlined" />
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* 탭 2: 앱 설정 */}
      {selectedTab === 1 && (
        <Grid container spacing={3}>
          {/* 화면 설정 */}
          <Grid item xs={12} md={6}>
            <Card sx={{ boxShadow: 3 }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                  <Palette sx={{ mr: 1, color: investmentColors.profit }} />
                  화면 설정
                </Typography>

                <List sx={{ p: 0 }}>
                  <ListItem sx={{ px: 0 }}>
                    <ListItemText 
                      primary="테마" 
                      secondary="앱의 색상 테마를 설정합니다"
                    />
                    <FormControl size="small">
                      <Select
                        value={appSettings.theme}
                        onChange={(e) => handleAppSettingsUpdate('theme', e.target.value)}
                      >
                        <MenuItem value="light">
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            <LightMode sx={{ mr: 1 }} />
                            밝은 테마
                          </Box>
                        </MenuItem>
                        <MenuItem value="dark">
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            <DarkMode sx={{ mr: 1 }} />
                            어두운 테마
                          </Box>
                        </MenuItem>
                        <MenuItem value="auto">자동</MenuItem>
                      </Select>
                    </FormControl>
                  </ListItem>

                  <ListItem sx={{ px: 0 }}>
                    <ListItemText 
                      primary="언어" 
                      secondary="앱 인터페이스 언어를 설정합니다"
                    />
                    <FormControl size="small">
                      <Select
                        value={appSettings.language}
                        onChange={(e) => handleAppSettingsUpdate('language', e.target.value)}
                      >
                        <MenuItem value="ko">한국어</MenuItem>
                        <MenuItem value="en">English</MenuItem>
                      </Select>
                    </FormControl>
                  </ListItem>

                  <ListItem sx={{ px: 0 }}>
                    <ListItemText 
                      primary="통화" 
                      secondary="가격 표시 통화를 설정합니다"
                    />
                    <FormControl size="small">
                      <Select
                        value={appSettings.currency}
                        onChange={(e) => handleAppSettingsUpdate('currency', e.target.value)}
                      >
                        <MenuItem value="KRW">원화 (₩)</MenuItem>
                        <MenuItem value="USD">달러 ($)</MenuItem>
                      </Select>
                    </FormControl>
                  </ListItem>
                </List>
              </CardContent>
            </Card>
          </Grid>

          {/* 데이터 설정 */}
          <Grid item xs={12} md={6}>
            <Card sx={{ boxShadow: 3 }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                  <CloudSync sx={{ mr: 1, color: investmentColors.profit }} />
                  데이터 설정
                </Typography>

                <List sx={{ p: 0 }}>
                  <ListItem sx={{ px: 0 }}>
                    <ListItemText
                      primary="자동 동기화"
                      secondary="데이터를 자동으로 동기화합니다"
                    />
                    <ListItemSecondaryAction>
                      <Switch
                        checked={appSettings.autoSync}
                        onChange={(e) => handleAppSettingsUpdate('autoSync', e.target.checked)}
                      />
                    </ListItemSecondaryAction>
                  </ListItem>

                  <ListItem sx={{ px: 0 }}>
                    <ListItemText
                      primary="오프라인 모드"
                      secondary="데이터 사용량을 줄입니다"
                    />
                    <ListItemSecondaryAction>
                      <Switch
                        checked={appSettings.offlineMode}
                        onChange={(e) => handleAppSettingsUpdate('offlineMode', e.target.checked)}
                      />
                    </ListItemSecondaryAction>
                  </ListItem>

                  <ListItem sx={{ px: 0 }}>
                    <ListItemText 
                      primary="데이터 새로고침 간격" 
                      secondary={`${appSettings.dataRefreshInterval}분마다`}
                    />
                    <FormControl size="small">
                      <Select
                        value={appSettings.dataRefreshInterval}
                        onChange={(e) => handleAppSettingsUpdate('dataRefreshInterval', e.target.value)}
                      >
                        <MenuItem value={1}>1분</MenuItem>
                        <MenuItem value={5}>5분</MenuItem>
                        <MenuItem value={10}>10분</MenuItem>
                        <MenuItem value={30}>30분</MenuItem>
                      </Select>
                    </FormControl>
                  </ListItem>
                </List>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* 탭 3: 거래 설정 */}
      {selectedTab === 2 && (
        <Grid container spacing={3}>
          {/* 기본 거래 설정 */}
          <Grid item xs={12} md={6}>
            <Card sx={{ boxShadow: 3 }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                  <TrendingUp sx={{ mr: 1, color: investmentColors.profit }} />
                  기본 거래 설정
                </Typography>

                <List sx={{ p: 0 }}>
                  <ListItem sx={{ px: 0 }}>
                    <ListItemText
                      primary="기본 주문 유형"
                      secondary="새 주문의 기본 타입을 설정합니다"
                    />
                    <FormControl size="small">
                      <Select
                        value={tradingSettings.defaultOrderType}
                        onChange={(e) => handleTradingSettingsUpdate('defaultOrderType', e.target.value)}
                      >
                        <MenuItem value="market">시장가</MenuItem>
                        <MenuItem value="limit">지정가</MenuItem>
                      </Select>
                    </FormControl>
                  </ListItem>

                  <ListItem sx={{ px: 0 }}>
                    <ListItemText
                      primary="거래 확인"
                      secondary="거래 실행 전 확인 메시지를 표시합니다"
                    />
                    <ListItemSecondaryAction>
                      <Switch
                        checked={tradingSettings.confirmBeforeTrade}
                        onChange={(e) => handleTradingSettingsUpdate('confirmBeforeTrade', e.target.checked)}
                      />
                    </ListItemSecondaryAction>
                  </ListItem>

                  <ListItem sx={{ px: 0, flexDirection: 'column', alignItems: 'flex-start' }}>
                    <ListItemText
                      primary="일일 최대 손실액"
                      secondary={`₩${tradingSettings.maxDailyLoss.toLocaleString()}`}
                      sx={{ mb: 2 }}
                    />
                    <TextField
                      type="number"
                      size="small"
                      value={tradingSettings.maxDailyLoss}
                      onChange={(e) => handleTradingSettingsUpdate('maxDailyLoss', parseInt(e.target.value))}
                      InputProps={{
                        startAdornment: <Box sx={{ mr: 1 }}>₩</Box>,
                      }}
                    />
                  </ListItem>
                </List>
              </CardContent>
            </Card>
          </Grid>

          {/* 위험 관리 */}
          <Grid item xs={12} md={6}>
            <Card sx={{ boxShadow: 3 }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                  <Security sx={{ mr: 1, color: investmentColors.loss }} />
                  위험 관리
                </Typography>

                <List sx={{ p: 0 }}>
                  <ListItem sx={{ px: 0 }}>
                    <ListItemText
                      primary="위험 관리 시스템"
                      secondary="자동 위험 관리 기능을 활성화합니다"
                    />
                    <ListItemSecondaryAction>
                      <Switch
                        checked={tradingSettings.riskManagementEnabled}
                        onChange={(e) => handleTradingSettingsUpdate('riskManagementEnabled', e.target.checked)}
                      />
                    </ListItemSecondaryAction>
                  </ListItem>

                  <ListItem sx={{ px: 0 }}>
                    <ListItemText
                      primary="자동 손절매"
                      secondary="설정된 손실률 도달 시 자동 매도"
                    />
                    <ListItemSecondaryAction>
                      <Switch
                        checked={tradingSettings.autoStopLoss}
                        onChange={(e) => handleTradingSettingsUpdate('autoStopLoss', e.target.checked)}
                      />
                    </ListItemSecondaryAction>
                  </ListItem>

                  <ListItem sx={{ px: 0, flexDirection: 'column', alignItems: 'flex-start' }}>
                    <ListItemText
                      primary="손절매 비율"
                      secondary={`${tradingSettings.stopLossPercentage}% 하락 시`}
                      sx={{ mb: 2 }}
                    />
                    <Slider
                      value={tradingSettings.stopLossPercentage}
                      onChange={(e, value) => handleTradingSettingsUpdate('stopLossPercentage', value)}
                      min={1}
                      max={20}
                      step={1}
                      marks={[
                        { value: 5, label: '5%' },
                        { value: 10, label: '10%' },
                        { value: 15, label: '15%' },
                      ]}
                      disabled={!tradingSettings.autoStopLoss}
                      sx={{ width: '100%' }}
                    />
                  </ListItem>

                  <ListItem sx={{ px: 0, flexDirection: 'column', alignItems: 'flex-start' }}>
                    <ListItemText
                      primary="익절매 비율"
                      secondary={`${tradingSettings.takeProfitPercentage}% 수익 시`}
                      sx={{ mb: 2 }}
                    />
                    <Slider
                      value={tradingSettings.takeProfitPercentage}
                      onChange={(e, value) => handleTradingSettingsUpdate('takeProfitPercentage', value)}
                      min={5}
                      max={50}
                      step={5}
                      marks={[
                        { value: 10, label: '10%' },
                        { value: 20, label: '20%' },
                        { value: 30, label: '30%' },
                      ]}
                      sx={{ width: '100%' }}
                    />
                  </ListItem>
                </List>
              </CardContent>
            </Card>
          </Grid>

          {/* 위험 관리 가이드 */}
          <Grid item xs={12}>
            <Alert severity="info" sx={{ borderRadius: 2 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                📊 위험 관리 팁
              </Typography>
              <Typography variant="body2">
                • 손절매는 투자 원금의 1-2% 이내로 설정하는 것이 권장됩니다<br/>
                • 익절매는 위험:수익 비율을 1:2 이상으로 설정하세요<br/>
                • 일일 최대 손실액을 전체 투자금의 5% 이내로 제한하세요
              </Typography>
            </Alert>
          </Grid>
        </Grid>
      )}

      {/* 탭 4: 보안 */}
      {selectedTab === 3 && (
        <Grid container spacing={3}>
          {/* 계정 보안 */}
          <Grid item xs={12} md={6}>
            <Card sx={{ boxShadow: 3 }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                  <Security sx={{ mr: 1, color: investmentColors.loss }} />
                  계정 보안
                </Typography>

                <List sx={{ p: 0 }}>
                  <ListItem sx={{ px: 0 }}>
                    <ListItemText
                      primary="비밀번호 변경"
                      secondary="정기적으로 비밀번호를 변경하세요"
                    />
                    <Button variant="outlined" size="small">
                      변경
                    </Button>
                  </ListItem>

                  <ListItem sx={{ px: 0 }}>
                    <ListItemText
                      primary="2단계 인증"
                      secondary="추가 보안을 위한 2FA를 설정하세요"
                    />
                    <Button variant="outlined" size="small" color="success">
                      활성화
                    </Button>
                  </ListItem>

                  <ListItem sx={{ px: 0 }}>
                    <ListItemText
                      primary="로그인 기록"
                      secondary="최근 로그인 내역을 확인하세요"
                    />
                    <Button variant="text" size="small">
                      보기
                    </Button>
                  </ListItem>
                </List>
              </CardContent>
            </Card>
          </Grid>

          {/* 데이터 관리 */}
          <Grid item xs={12} md={6}>
            <Card sx={{ boxShadow: 3 }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                  <DeviceHub sx={{ mr: 1, color: investmentColors.neutral }} />
                  데이터 관리
                </Typography>

                <List sx={{ p: 0 }}>
                  <ListItem sx={{ px: 0 }}>
                    <ListItemText
                      primary="데이터 백업"
                      secondary="투자 데이터를 안전하게 백업합니다"
                    />
                    <Button variant="outlined" size="small" startIcon={<CloudSync />}>
                      백업
                    </Button>
                  </ListItem>

                  <ListItem sx={{ px: 0 }}>
                    <ListItemText
                      primary="데이터 복원"
                      secondary="백업된 데이터를 복원합니다"
                    />
                    <Button variant="outlined" size="small" startIcon={<Refresh />}>
                      복원
                    </Button>
                  </ListItem>

                  <ListItem sx={{ px: 0 }}>
                    <ListItemText
                      primary="계정 삭제"
                      secondary="모든 데이터를 영구적으로 삭제합니다"
                    />
                    <Button variant="outlined" size="small" color="error">
                      삭제
                    </Button>
                  </ListItem>
                </List>
              </CardContent>
            </Card>
          </Grid>

          {/* 로그아웃 */}
          <Grid item xs={12}>
            <Paper sx={{ p: 3, textAlign: 'center', bgcolor: 'grey.50' }}>
              <Typography variant="h6" gutterBottom>
                세션 관리
              </Typography>
              <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
                보안을 위해 사용하지 않을 때는 로그아웃하세요
              </Typography>
              <Button
                variant="contained"
                color="error"
                startIcon={<Logout />}
                onClick={() => setShowLogoutDialog(true)}
              >
                로그아웃
              </Button>
            </Paper>
          </Grid>
        </Grid>
      )}

      {/* 로그아웃 확인 다이얼로그 */}
      <Dialog open={showLogoutDialog} onClose={() => setShowLogoutDialog(false)}>
        <DialogTitle>로그아웃 확인</DialogTitle>
        <DialogContent>
          <Typography>
            정말로 로그아웃하시겠습니까? 진행 중인 작업이 저장되지 않을 수 있습니다.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowLogoutDialog(false)}>
            취소
          </Button>
          <Button color="error" variant="contained">
            로그아웃
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default Settings;