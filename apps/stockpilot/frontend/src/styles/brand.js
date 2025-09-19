/**
 * 유아플랜 브랜드 토큰 - 토스 스타일 모바일 최적화
 */

export const BRAND_TOKENS = {
  // 로고 및 이미지
  logo: {
    path: '/brand/logo.png',
    alt: 'YouArePlan StockPilot AI'
  },
  
  // 파비콘 및 아이콘
  icons: {
    favicon: '/favicon.png',
    appleTouchIcon: '/apple-touch-icon.png',
    ogImage: '/og-image.png'
  },
  
  // 컬러 시스템 (토스 스타일)
  colors: {
    primary: {
      50: '#eff6ff',
      100: '#dbeafe', 
      500: '#3b82f6',
      600: '#2563eb',
      700: '#1d4ed8',
      900: '#1e3a8a'
    },
    gray: {
      50: '#f9fafb',
      100: '#f3f4f6',
      200: '#e5e7eb',
      500: '#6b7280',
      700: '#374151',
      900: '#111827'
    },
    background: '#ffffff',
    surface: '#f9fafb'
  },
  
  // 타이포그래피 (모바일 최적화)
  typography: {
    fontFamily: {
      sans: ['Pretendard', 'system-ui', '-apple-system', 'sans-serif']
    },
    fontSize: {
      xs: '12px',
      sm: '14px', 
      base: '16px',
      lg: '18px',
      xl: '20px',
      '2xl': '24px',
      '3xl': '30px'
    },
    fontWeight: {
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700
    }
  },
  
  // 스페이싱 (토스 스타일)
  spacing: {
    xs: '4px',
    sm: '8px',
    md: '16px',
    lg: '24px',
    xl: '32px',
    '2xl': '48px'
  },
  
  // 보더 반경
  borderRadius: {
    sm: '4px',
    md: '8px',
    lg: '12px',
    xl: '16px',
    full: '9999px'
  },
  
  // 그림자 (토스 스타일)
  shadow: {
    sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
    md: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
    lg: '0 10px 15px -3px rgb(0 0 0 / 0.1)',
    card: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -1px rgb(0 0 0 / 0.06)'
  },
  
  // 애니메이션
  transition: {
    default: '0.15s ease',
    fast: '0.1s ease',
    slow: '0.3s ease'
  }
};

export default BRAND_TOKENS;
