/**
 * 시장 설정 정보
 * 미국 시장 우선, 다중 시장 지원
 */

export interface MarketConfig {
  code: string;
  name: string;
  currency: string;
  timezone: string;
  openTime: string;
  closeTime: string;
  locale: string;
  tickerFormat: RegExp;
  isPrimary: boolean;
}

// 미국 시장 설정 (우선)
export const US_MARKET: MarketConfig = {
  code: 'US',
  name: '미국 시장',
  currency: 'USD',
  timezone: 'US/Eastern',
  openTime: '09:30',
  closeTime: '16:00',
  locale: 'en-US',
  tickerFormat: /^[A-Z]{1,5}$/,  // AAPL, MSFT, GOOGL 등
  isPrimary: true,
};

// 한국 시장 설정 (2차 지원)
export const KR_MARKET: MarketConfig = {
  code: 'KR',
  name: '한국 시장',
  currency: 'KRW',
  timezone: 'Asia/Seoul',
  openTime: '09:00',
  closeTime: '15:30',
  locale: 'ko-KR',
  tickerFormat: /^\d{6}$/,  // 005930 등
  isPrimary: false,
};

// 전체 지원 시장
export const SUPPORTED_MARKETS: MarketConfig[] = [
  US_MARKET,
  KR_MARKET,
];

// 기본 시장 설정 (미국 우선)
export const DEFAULT_MARKET = US_MARKET;

// 환경 변수에서 설정 값 가져오기
export const getMarketConfig = () => {
  const defaultMarket = process.env.REACT_APP_DEFAULT_MARKET || 'US';
  const defaultCurrency = process.env.REACT_APP_DEFAULT_CURRENCY || 'USD';
  const defaultTimezone = process.env.REACT_APP_DEFAULT_TIMEZONE || 'US/Eastern';
  
  return {
    defaultMarket,
    defaultCurrency,
    defaultTimezone,
    markets: SUPPORTED_MARKETS,
  };
};

// 시장 코드로 설정 조회
export const getMarketByCode = (marketCode: string): MarketConfig => {
  return SUPPORTED_MARKETS.find(market => market.code === marketCode) || DEFAULT_MARKET;
};

// 티커 심볼로 시장 추측
export const detectMarketFromTicker = (ticker: string): MarketConfig => {
  // 미국 시장 패턴 우선 체크
  if (US_MARKET.tickerFormat.test(ticker)) {
    return US_MARKET;
  }
  
  // 한국 시장 패턴 체크
  if (KR_MARKET.tickerFormat.test(ticker)) {
    return KR_MARKET;
  }
  
  // 기본적으로 미국 시장 반환
  return US_MARKET;
};

// 통화 포맷팅 함수
export const formatCurrency = (
  amount: number, 
  currency: string = DEFAULT_MARKET.currency,
  locale: string = DEFAULT_MARKET.locale
): string => {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: currency,
  }).format(amount);
};

// 퍼센트 포맷팅 함수
export const formatPercent = (
  value: number,
  locale: string = DEFAULT_MARKET.locale
): string => {
  return new Intl.NumberFormat(locale, {
    style: 'percent',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value / 100);
};

// 시장 상태 타입
export type MarketStatus = 'OPEN' | 'CLOSED' | 'PRE_MARKET' | 'AFTER_HOURS';

// 시장 시간 확인 함수
export const getMarketStatus = (marketConfig: MarketConfig = DEFAULT_MARKET): MarketStatus => {
  const now = new Date();
  const marketTime = new Intl.DateTimeFormat('en-CA', {
    timeZone: marketConfig.timezone,
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
  }).format(now);

  const [currentHour, currentMinute] = marketTime.split(':').map(Number);
  const currentTimeMinutes = (currentHour || 0) * 60 + (currentMinute || 0);
  
  const [openHour, openMinute] = marketConfig.openTime.split(':').map(Number);
  const openTimeMinutes = (openHour || 0) * 60 + (openMinute || 0);
  
  const [closeHour, closeMinute] = marketConfig.closeTime.split(':').map(Number);
  const closeTimeMinutes = (closeHour || 0) * 60 + (closeMinute || 0);

  // 주말 체크
  const dayOfWeek = new Date().getDay();
  if (dayOfWeek === 0 || dayOfWeek === 6) {
    return 'CLOSED';
  }

  if (currentTimeMinutes >= openTimeMinutes && currentTimeMinutes < closeTimeMinutes) {
    return 'OPEN';
  } else if (currentTimeMinutes < openTimeMinutes) {
    return 'PRE_MARKET';
  } else {
    return 'AFTER_HOURS';
  }
};

// 미국 주요 주식 예시 데이터
export const US_SAMPLE_STOCKS = [
  { symbol: 'AAPL', name: 'Apple Inc.' },
  { symbol: 'MSFT', name: 'Microsoft Corporation' },
  { symbol: 'GOOGL', name: 'Alphabet Inc.' },
  { symbol: 'AMZN', name: 'Amazon.com Inc.' },
  { symbol: 'TSLA', name: 'Tesla Inc.' },
  { symbol: 'META', name: 'Meta Platforms Inc.' },
  { symbol: 'NVDA', name: 'NVIDIA Corporation' },
  { symbol: 'NFLX', name: 'Netflix Inc.' },
];