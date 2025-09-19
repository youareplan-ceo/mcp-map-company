// StockPilot AI 브랜드 테마 시스템
// 작성자: StockPilot Team
// 용도: 일관된 브랜딩과 디자인 시스템

export const colors = {
  // 브랜드 메인 컬러 (그라데이션 베이스)
  brand: {
    primary: '#667eea',      // 메인 브랜드 컬러 (퍼플 블루)
    secondary: '#764ba2',    // 세컨더리 브랜드 컬러 (딥 퍼플)
    gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    gradientHover: 'linear-gradient(135deg, #5a67d8 0%, #6b46c1 100%)',
    light: '#e0e7ff',        // 브랜드 라이트
    lighter: '#f0f4ff',      // 브랜드 더 라이트
    dark: '#4c51bf',         // 브랜드 다크
  },

  // 금융/투자 관련 컬러
  financial: {
    profit: '#10b981',       // 수익/상승 (에메랄드 그린)
    loss: '#ef4444',         // 손실/하락 (레드)
    warning: '#f59e0b',      // 주의/경고 (앰버)
    neutral: '#6b7280',      // 중립/보합 (그레이)
    profitBg: '#ecfdf5',     // 수익 배경
    lossBg: '#fef2f2',       // 손실 배경
    warningBg: '#fffbeb',    // 경고 배경
  },

  // 시스템 컬러
  system: {
    success: '#10b981',      // 성공
    error: '#ef4444',        // 에러
    warning: '#f59e0b',      // 경고
    info: '#3b82f6',         // 정보
    
    successBg: '#ecfdf5',    // 성공 배경
    errorBg: '#fef2f2',      // 에러 배경
    warningBg: '#fffbeb',    // 경고 배경
    infoBg: '#eff6ff',       // 정보 배경
  },

  // 그레이스케일
  gray: {
    50: '#f9fafb',
    100: '#f3f4f6',
    200: '#e5e7eb',
    300: '#d1d5db',
    400: '#9ca3af',
    500: '#6b7280',
    600: '#4b5563',
    700: '#374151',
    800: '#1f2937',
    900: '#111827',
  },

  // 배경 컬러
  background: {
    primary: '#ffffff',      // 메인 배경
    secondary: '#f9fafb',    // 보조 배경
    tertiary: '#f3f4f6',     // 3차 배경
    card: '#ffffff',         // 카드 배경
    overlay: 'rgba(0, 0, 0, 0.5)', // 오버레이
    modal: 'rgba(0, 0, 0, 0.75)',  // 모달 배경
  },

  // 텍스트 컬러
  text: {
    primary: '#111827',      // 메인 텍스트
    secondary: '#374151',    // 보조 텍스트
    tertiary: '#6b7280',     // 3차 텍스트
    disabled: '#9ca3af',     // 비활성 텍스트
    inverse: '#ffffff',      // 역색 텍스트
    brand: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', // 브랜드 텍스트
  },

  // 보더 컬러
  border: {
    light: '#f3f4f6',       // 라이트 보더
    default: '#e5e7eb',     // 기본 보더
    medium: '#d1d5db',      // 미디움 보더
    dark: '#9ca3af',        // 다크 보더
    brand: '#667eea',       // 브랜드 보더
  },

  // 다크 테마 (향후 확장용)
  dark: {
    background: {
      primary: '#111827',
      secondary: '#1f2937',
      tertiary: '#374151',
      card: '#1f2937',
    },
    text: {
      primary: '#f9fafb',
      secondary: '#e5e7eb',
      tertiary: '#9ca3af',
    },
    border: {
      light: '#374151',
      default: '#4b5563',
      medium: '#6b7280',
    }
  }
};

export const typography = {
  // 폰트 패밀리
  fontFamily: {
    primary: "'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif",
    secondary: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif",
    mono: "'JetBrains Mono', 'Fira Code', 'Monaco', 'Consolas', monospace",
    number: "'JetBrains Mono', 'SF Mono', 'Monaco', 'Consolas', monospace", // 숫자 전용
  },

  // 폰트 크기
  fontSize: {
    xs: '0.75rem',     // 12px
    sm: '0.875rem',    // 14px
    base: '1rem',      // 16px
    lg: '1.125rem',    // 18px
    xl: '1.25rem',     // 20px
    '2xl': '1.5rem',   // 24px
    '3xl': '1.875rem', // 30px
    '4xl': '2.25rem',  // 36px
    '5xl': '3rem',     // 48px
    '6xl': '3.75rem',  // 60px
  },

  // 폰트 웨이트
  fontWeight: {
    light: 300,
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
    extrabold: 800,
  },

  // 라인 하이트
  lineHeight: {
    tight: 1.25,
    snug: 1.375,
    normal: 1.5,
    relaxed: 1.625,
    loose: 2,
  },

  // 레터 스페이싱
  letterSpacing: {
    tighter: '-0.05em',
    tight: '-0.025em',
    normal: '0',
    wide: '0.025em',
    wider: '0.05em',
    widest: '0.1em',
  },
};

export const spacing = {
  // 기본 스페이싱 (rem 단위)
  0: '0',
  1: '0.25rem',    // 4px
  2: '0.5rem',     // 8px
  3: '0.75rem',    // 12px
  4: '1rem',       // 16px
  5: '1.25rem',    // 20px
  6: '1.5rem',     // 24px
  8: '2rem',       // 32px
  10: '2.5rem',    // 40px
  12: '3rem',      // 48px
  16: '4rem',      // 64px
  20: '5rem',      // 80px
  24: '6rem',      // 96px
  32: '8rem',      // 128px
  40: '10rem',     // 160px
  48: '12rem',     // 192px
  56: '14rem',     // 224px
  64: '16rem',     // 256px
};

export const shadows = {
  // 그림자 효과
  none: 'none',
  sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
  default: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
  md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
  lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
  xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
  '2xl': '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
  inner: 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)',
  
  // 브랜드 그림자
  brand: '0 4px 15px rgba(102, 126, 234, 0.3)',
  brandHover: '0 8px 25px rgba(102, 126, 234, 0.4)',
  
  // 금융 관련 그림자
  profit: '0 4px 15px rgba(16, 185, 129, 0.2)',
  loss: '0 4px 15px rgba(239, 68, 68, 0.2)',
};

export const borderRadius = {
  none: '0',
  sm: '0.125rem',    // 2px
  default: '0.25rem', // 4px
  md: '0.375rem',    // 6px
  lg: '0.5rem',      // 8px
  xl: '0.75rem',     // 12px
  '2xl': '1rem',     // 16px
  '3xl': '1.5rem',   // 24px
  full: '9999px',    // 완전한 원형
};

export const zIndex = {
  // Z-index 레벨
  hide: -1,
  auto: 'auto',
  base: 0,
  docked: 10,
  dropdown: 1000,
  sticky: 1100,
  banner: 1200,
  overlay: 1300,
  modal: 1400,
  popover: 1500,
  skipLink: 1600,
  toast: 1700,
  tooltip: 1800,
};

export const breakpoints = {
  // 반응형 브레이크포인트
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
};

export const transitions = {
  // 트랜지션 효과
  default: 'all 0.3s ease',
  fast: 'all 0.15s ease',
  slow: 'all 0.5s ease',
  
  // 전용 트랜지션
  color: 'color 0.3s ease',
  background: 'background-color 0.3s ease',
  border: 'border-color 0.3s ease',
  shadow: 'box-shadow 0.3s ease',
  transform: 'transform 0.3s ease',
  opacity: 'opacity 0.3s ease',
};

export const animations = {
  // 애니메이션 키프레임
  pulse: {
    '0%, 100%': {
      opacity: 1,
    },
    '50%': {
      opacity: 0.5,
    },
  },
  
  bounce: {
    '0%, 100%': {
      transform: 'translateY(-25%)',
      animationTimingFunction: 'cubic-bezier(0.8, 0, 1, 1)',
    },
    '50%': {
      transform: 'translateY(0)',
      animationTimingFunction: 'cubic-bezier(0, 0, 0.2, 1)',
    },
  },
  
  fadeIn: {
    '0%': {
      opacity: 0,
    },
    '100%': {
      opacity: 1,
    },
  },
  
  slideUp: {
    '0%': {
      transform: 'translateY(100%)',
      opacity: 0,
    },
    '100%': {
      transform: 'translateY(0)',
      opacity: 1,
    },
  },
  
  slideDown: {
    '0%': {
      transform: 'translateY(-100%)',
      opacity: 0,
    },
    '100%': {
      transform: 'translateY(0)',
      opacity: 1,
    },
  },
};

// 컴포넌트별 스타일 템플릿
export const components = {
  // 버튼 스타일
  button: {
    primary: {
      background: colors.brand.gradient,
      color: colors.text.inverse,
      border: 'none',
      borderRadius: borderRadius.lg,
      padding: `${spacing[3]} ${spacing[6]}`,
      fontSize: typography.fontSize.base,
      fontWeight: typography.fontWeight.medium,
      transition: transitions.default,
      boxShadow: shadows.brand,
      
      '&:hover': {
        background: colors.brand.gradientHover,
        boxShadow: shadows.brandHover,
        transform: 'translateY(-1px)',
      },
      
      '&:active': {
        transform: 'translateY(0)',
      },
      
      '&:disabled': {
        opacity: 0.5,
        cursor: 'not-allowed',
        transform: 'none',
      },
    },
    
    secondary: {
      background: colors.background.primary,
      color: colors.brand.primary,
      border: `1px solid ${colors.border.brand}`,
      borderRadius: borderRadius.lg,
      padding: `${spacing[3]} ${spacing[6]}`,
      fontSize: typography.fontSize.base,
      fontWeight: typography.fontWeight.medium,
      transition: transitions.default,
      
      '&:hover': {
        background: colors.brand.lighter,
        borderColor: colors.brand.secondary,
      },
    },
    
    ghost: {
      background: 'transparent',
      color: colors.text.secondary,
      border: 'none',
      borderRadius: borderRadius.lg,
      padding: `${spacing[3]} ${spacing[6]}`,
      fontSize: typography.fontSize.base,
      fontWeight: typography.fontWeight.medium,
      transition: transitions.default,
      
      '&:hover': {
        background: colors.background.secondary,
        color: colors.text.primary,
      },
    },
  },

  // 카드 스타일
  card: {
    default: {
      background: colors.background.card,
      borderRadius: borderRadius.xl,
      padding: spacing[6],
      boxShadow: shadows.default,
      border: `1px solid ${colors.border.light}`,
      transition: transitions.default,
      
      '&:hover': {
        boxShadow: shadows.md,
        transform: 'translateY(-2px)',
      },
    },
    
    elevated: {
      background: colors.background.card,
      borderRadius: borderRadius.xl,
      padding: spacing[6],
      boxShadow: shadows.lg,
      border: 'none',
      transition: transitions.default,
      
      '&:hover': {
        boxShadow: shadows.xl,
        transform: 'translateY(-4px)',
      },
    },
    
    flat: {
      background: colors.background.card,
      borderRadius: borderRadius.xl,
      padding: spacing[6],
      boxShadow: 'none',
      border: `1px solid ${colors.border.default}`,
    },
  },

  // 입력 필드 스타일
  input: {
    default: {
      width: '100%',
      padding: `${spacing[3]} ${spacing[4]}`,
      fontSize: typography.fontSize.base,
      fontFamily: typography.fontFamily.primary,
      border: `1px solid ${colors.border.default}`,
      borderRadius: borderRadius.lg,
      background: colors.background.primary,
      color: colors.text.primary,
      transition: transitions.default,
      
      '&:focus': {
        outline: 'none',
        borderColor: colors.brand.primary,
        boxShadow: `0 0 0 3px ${colors.brand.light}`,
      },
      
      '&::placeholder': {
        color: colors.text.disabled,
      },
      
      '&:disabled': {
        background: colors.background.secondary,
        color: colors.text.disabled,
        cursor: 'not-allowed',
      },
    },
  },
};

// 테마 객체 (전체 내보내기)
const theme = {
  colors,
  typography,
  spacing,
  shadows,
  borderRadius,
  zIndex,
  breakpoints,
  transitions,
  animations,
  components,
};

export default theme;