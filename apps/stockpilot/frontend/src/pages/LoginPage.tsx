/**
 * StockPilot 로그인/회원가입 화면 - 토스 스타일 UI
 * 간편하고 직관적인 사용자 인증 시스템
 */

import React, { useState } from 'react';
import {
  Box,
  Container,
  Typography,
  TextField,
  Button,
  Divider,
  Card,
  CardContent,
  InputAdornment,
  IconButton,
  Alert,
  Stack,
  Chip,
  Link
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  Phone as PhoneIcon,
  Email as EmailIcon,
  Lock as LockIcon,
  Google as GoogleIcon,
  Apple as AppleIcon,
  AccountCircle as UserIcon
} from '@mui/icons-material';

// 토스 스타일 색상 팔레트
const tossColors = {
  primary: '#1976d2',
  secondary: '#0d47a1',
  success: '#2e7d32',
  background: '#f8f9fa',
  cardBg: '#ffffff',
  textPrimary: '#212121',
  textSecondary: '#757575',
  kakaoYellow: '#FEE500',
  naverGreen: '#03C75A'
};

interface LoginForm {
  phone: string;
  email: string;
  password: string;
  name: string;
}

export const LoginPage: React.FC = () => {
  // 상태 관리
  const [isSignUp, setIsSignUp] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState<LoginForm>({
    phone: '',
    email: '',
    password: '',
    name: ''
  });
  const [errors, setErrors] = useState<Partial<LoginForm>>({});
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<'phone' | 'verify' | 'complete'>('phone');

  // 폼 데이터 업데이트
  const handleInputChange = (field: keyof LoginForm) => (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    setFormData(prev => ({
      ...prev,
      [field]: event.target.value
    }));
    // 에러 클리어
    if (errors[field]) {
      setErrors(prev => ({
        ...prev,
        [field]: undefined
      }));
    }
  };

  // 폼 검증
  const validateForm = (): boolean => {
    const newErrors: Partial<LoginForm> = {};

    if (!formData.phone) {
      newErrors.phone = '휴대폰 번호를 입력해주세요';
    } else if (!/^010-\d{4}-\d{4}$/.test(formData.phone)) {
      newErrors.phone = '올바른 휴대폰 번호 형식이 아닙니다';
    }

    if (isSignUp) {
      if (!formData.name) {
        newErrors.name = '이름을 입력해주세요';
      }
      if (!formData.email) {
        newErrors.email = '이메일을 입력해주세요';
      } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
        newErrors.email = '올바른 이메일 형식이 아닙니다';
      }
    }

    if (!formData.password) {
      newErrors.password = '비밀번호를 입력해주세요';
    } else if (formData.password.length < 6) {
      newErrors.password = '비밀번호는 6자 이상이어야 합니다';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // 휴대폰 번호 포맷팅
  const formatPhoneNumber = (value: string) => {
    const numbers = value.replace(/\D/g, '');
    if (numbers.length <= 3) return numbers;
    if (numbers.length <= 7) return `${numbers.slice(0, 3)}-${numbers.slice(3)}`;
    return `${numbers.slice(0, 3)}-${numbers.slice(3, 7)}-${numbers.slice(7, 11)}`;
  };

  // 휴대폰 번호 입력 처리
  const handlePhoneChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const formatted = formatPhoneNumber(event.target.value);
    setFormData(prev => ({ ...prev, phone: formatted }));
  };

  // 인증 번호 전송
  const handleSendVerification = async () => {
    if (!validateForm()) return;

    setLoading(true);
    try {
      // API 호출
      const response = await fetch('/api/v1/auth/send-sms', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: formData.phone })
      });

      if (response.ok) {
        setStep('verify');
      } else {
        throw new Error('인증번호 전송에 실패했습니다');
      }
    } catch (error) {
      console.error('SMS 전송 실패:', error);
    }
    setLoading(false);
  };

  // 로그인/회원가입 처리
  const handleAuth = async () => {
    if (!validateForm()) return;

    setLoading(true);
    try {
      const endpoint = isSignUp ? '/api/v1/auth/signup' : '/api/v1/auth/login';
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });

      if (response.ok) {
        const data = await response.json();
        localStorage.setItem('token', data.token);
        // 메인 페이지로 이동
        console.log('인증 성공');
      } else {
        throw new Error(isSignUp ? '회원가입에 실패했습니다' : '로그인에 실패했습니다');
      }
    } catch (error) {
      console.error('인증 실패:', error);
    }
    setLoading(false);
  };

  // 소셜 로그인
  const handleSocialLogin = (provider: string) => {
    console.log(`${provider} 로그인 시도`);
    // 소셜 로그인 구현
  };

  return (
    <Box sx={{
      minHeight: '100vh',
      backgroundColor: tossColors.background,
      display: 'flex',
      alignItems: 'center',
      py: 4
    }}>
      <Container maxWidth="sm">
        <Box sx={{ textAlign: 'center', mb: 4 }}>
          {/* 로고 */}
          <Box sx={{
            width: 80,
            height: 80,
            borderRadius: '20px',
            bgcolor: tossColors.primary,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            mx: 'auto',
            mb: 2,
            boxShadow: '0 4px 12px rgba(25, 118, 210, 0.3)'
          }}>
            <Typography variant="h4" sx={{ color: 'white', fontWeight: 'bold' }}>
              S
            </Typography>
          </Box>
          
          <Typography variant="h4" sx={{ fontWeight: 'bold', color: tossColors.textPrimary, mb: 1 }}>
            StockPilot
          </Typography>
          <Typography variant="body1" color="text.secondary">
            AI와 함께하는 똑똑한 투자
          </Typography>
        </Box>

        <Card sx={{
          borderRadius: '16px',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.1)',
          overflow: 'visible'
        }}>
          <CardContent sx={{ p: 4 }}>
            {/* 탭 선택 */}
            <Box sx={{
              display: 'flex',
              bgcolor: '#f5f5f5',
              borderRadius: '12px',
              p: 0.5,
              mb: 3
            }}>
              <Button
                fullWidth
                onClick={() => setIsSignUp(false)}
                sx={{
                  py: 1.5,
                  borderRadius: '8px',
                  bgcolor: !isSignUp ? 'white' : 'transparent',
                  color: !isSignUp ? tossColors.primary : tossColors.textSecondary,
                  fontWeight: !isSignUp ? 600 : 400,
                  boxShadow: !isSignUp ? '0 2px 8px rgba(0,0,0,0.1)' : 'none',
                  '&:hover': {
                    bgcolor: !isSignUp ? 'white' : 'rgba(0,0,0,0.04)'
                  }
                }}
              >
                로그인
              </Button>
              <Button
                fullWidth
                onClick={() => setIsSignUp(true)}
                sx={{
                  py: 1.5,
                  borderRadius: '8px',
                  bgcolor: isSignUp ? 'white' : 'transparent',
                  color: isSignUp ? tossColors.primary : tossColors.textSecondary,
                  fontWeight: isSignUp ? 600 : 400,
                  boxShadow: isSignUp ? '0 2px 8px rgba(0,0,0,0.1)' : 'none',
                  '&:hover': {
                    bgcolor: isSignUp ? 'white' : 'rgba(0,0,0,0.04)'
                  }
                }}
              >
                회원가입
              </Button>
            </Box>

            <Stack spacing={3}>
              {/* 이름 (회원가입시만) */}
              {isSignUp && (
                <TextField
                  fullWidth
                  placeholder="이름을 입력하세요"
                  value={formData.name}
                  onChange={handleInputChange('name')}
                  error={!!errors.name}
                  helperText={errors.name}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <UserIcon color="action" />
                      </InputAdornment>
                    )
                  }}
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      borderRadius: '12px'
                    }
                  }}
                />
              )}

              {/* 휴대폰 번호 */}
              <TextField
                fullWidth
                placeholder="휴대폰 번호 (010-0000-0000)"
                value={formData.phone}
                onChange={handlePhoneChange}
                error={!!errors.phone}
                helperText={errors.phone}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <PhoneIcon color="action" />
                    </InputAdornment>
                  )
                }}
                sx={{
                  '& .MuiOutlinedInput-root': {
                    borderRadius: '12px'
                  }
                }}
              />

              {/* 이메일 (회원가입시만) */}
              {isSignUp && (
                <TextField
                  fullWidth
                  placeholder="이메일을 입력하세요"
                  value={formData.email}
                  onChange={handleInputChange('email')}
                  error={!!errors.email}
                  helperText={errors.email}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <EmailIcon color="action" />
                      </InputAdornment>
                    )
                  }}
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      borderRadius: '12px'
                    }
                  }}
                />
              )}

              {/* 비밀번호 */}
              <TextField
                fullWidth
                type={showPassword ? 'text' : 'password'}
                placeholder="비밀번호를 입력하세요"
                value={formData.password}
                onChange={handleInputChange('password')}
                error={!!errors.password}
                helperText={errors.password}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <LockIcon color="action" />
                    </InputAdornment>
                  ),
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowPassword(!showPassword)}
                        edge="end"
                      >
                        {showPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  )
                }}
                sx={{
                  '& .MuiOutlinedInput-root': {
                    borderRadius: '12px'
                  }
                }}
              />

              {/* 로그인/회원가입 버튼 */}
              <Button
                fullWidth
                variant="contained"
                onClick={handleAuth}
                disabled={loading}
                sx={{
                  py: 1.5,
                  fontSize: '16px',
                  fontWeight: 600,
                  borderRadius: '12px',
                  bgcolor: tossColors.primary,
                  '&:hover': {
                    bgcolor: tossColors.secondary
                  }
                }}
              >
                {loading ? '처리 중...' : (isSignUp ? '회원가입하기' : '로그인하기')}
              </Button>
            </Stack>

            {/* 또는 구분선 */}
            <Box sx={{ display: 'flex', alignItems: 'center', my: 3 }}>
              <Divider sx={{ flex: 1 }} />
              <Typography variant="body2" color="text.secondary" sx={{ px: 2 }}>
                또는
              </Typography>
              <Divider sx={{ flex: 1 }} />
            </Box>

            {/* 소셜 로그인 */}
            <Stack spacing={2}>
              <Button
                fullWidth
                variant="outlined"
                onClick={() => handleSocialLogin('kakao')}
                sx={{
                  py: 1.5,
                  borderRadius: '12px',
                  bgcolor: tossColors.kakaoYellow,
                  borderColor: tossColors.kakaoYellow,
                  color: '#000',
                  fontWeight: 600,
                  '&:hover': {
                    bgcolor: '#fdd835',
                    borderColor: '#fdd835'
                  }
                }}
              >
                카카오톡으로 시작하기
              </Button>
              
              <Button
                fullWidth
                variant="outlined"
                onClick={() => handleSocialLogin('naver')}
                sx={{
                  py: 1.5,
                  borderRadius: '12px',
                  bgcolor: tossColors.naverGreen,
                  borderColor: tossColors.naverGreen,
                  color: 'white',
                  fontWeight: 600,
                  '&:hover': {
                    bgcolor: '#00b347',
                    borderColor: '#00b347'
                  }
                }}
              >
                네이버로 시작하기
              </Button>

              <Button
                fullWidth
                variant="outlined"
                startIcon={<GoogleIcon />}
                onClick={() => handleSocialLogin('google')}
                sx={{
                  py: 1.5,
                  borderRadius: '12px',
                  borderColor: '#dadce0',
                  color: tossColors.textPrimary,
                  '&:hover': {
                    bgcolor: '#f8f9fa',
                    borderColor: '#dadce0'
                  }
                }}
              >
                Google로 시작하기
              </Button>
            </Stack>

            {/* 하단 링크 */}
            <Box sx={{ textAlign: 'center', mt: 3 }}>
              <Typography variant="body2" color="text.secondary">
                {isSignUp ? '이미 계정이 있으신가요? ' : '아직 계정이 없으신가요? '}
                <Link
                  component="button"
                  variant="body2"
                  onClick={() => setIsSignUp(!isSignUp)}
                  sx={{
                    color: tossColors.primary,
                    textDecoration: 'none',
                    fontWeight: 600,
                    '&:hover': {
                      textDecoration: 'underline'
                    }
                  }}
                >
                  {isSignUp ? '로그인하기' : '회원가입하기'}
                </Link>
              </Typography>
            </Box>

            {/* 이용약관 동의 (회원가입시) */}
            {isSignUp && (
              <Box sx={{ mt: 3 }}>
                <Typography variant="caption" color="text.secondary" sx={{ textAlign: 'center', display: 'block' }}>
                  회원가입 시{' '}
                  <Link href="#" sx={{ color: tossColors.primary, textDecoration: 'none' }}>
                    이용약관
                  </Link>
                  {' '}및{' '}
                  <Link href="#" sx={{ color: tossColors.primary, textDecoration: 'none' }}>
                    개인정보처리방침
                  </Link>
                  에 동의하는 것으로 간주됩니다.
                </Typography>
              </Box>
            )}
          </CardContent>
        </Card>

        {/* 고객센터 안내 */}
        <Box sx={{ textAlign: 'center', mt: 3 }}>
          <Typography variant="body2" color="text.secondary">
            로그인에 문제가 있으신가요?{' '}
            <Link href="#" sx={{ color: tossColors.primary, textDecoration: 'none' }}>
              고객센터
            </Link>
          </Typography>
        </Box>
      </Container>
    </Box>
  );
};

export default LoginPage;