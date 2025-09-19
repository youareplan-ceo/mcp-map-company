/**
 * 환경 변수 설정
 * 개발/운영 환경별 API 엔드포인트 및 설정 관리
 */

export const ENV = {
  // API 서버 설정
  API_BASE_URL: process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api/v1',
  WS_URL: process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws',
  
  // 외부 서비스 API 키
  TRADINGVIEW_API_KEY: process.env.REACT_APP_TRADINGVIEW_API_KEY || '',
  
  // 앱 설정
  APP_NAME: 'StockPilot AI',
  APP_VERSION: process.env.REACT_APP_VERSION || '1.0.0',
  
  // 개발 모드 확인
  IS_DEV: process.env.NODE_ENV === 'development',
  IS_PROD: process.env.NODE_ENV === 'production',
  
  // 로그 레벨
  LOG_LEVEL: process.env.REACT_APP_LOG_LEVEL || (process.env.NODE_ENV === 'development' ? 'debug' : 'info'),
  
  // 한국 시장 설정
  MARKET_TIMEZONE: 'Asia/Seoul',
  MARKET_OPEN_TIME: '09:00',
  MARKET_CLOSE_TIME: '15:30',
  
  // 캐시 설정 (밀리초)
  CACHE_TIMES: {
    STOCK_SEARCH: 30 * 1000, // 30초
    PRICE_DATA: 5 * 1000,    // 5초
    NEWS_DATA: 5 * 60 * 1000, // 5분
    MARKET_STATUS: 60 * 1000, // 1분
    DASHBOARD_SUMMARY: 60 * 1000, // 1분
    AI_SIGNALS: 30 * 1000, // 30초
  },
  
  // API 요청 제한
  API_LIMITS: {
    MAX_SEARCH_RESULTS: 50,
    MAX_WATCHLIST_SIZE: 100,
    MAX_NEWS_ITEMS: 100,
    MAX_SIGNALS_PER_PAGE: 50,
  }
};