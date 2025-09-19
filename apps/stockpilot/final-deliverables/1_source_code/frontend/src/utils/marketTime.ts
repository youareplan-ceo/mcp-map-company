/**
 * 미국 시장 시간 정확도 개선 유틸리티
 * EST/EDT 자동 전환 및 휴장일 캘린더 처리
 */

// 미국 시장 상태 타입
export type MarketStatus = 'OPEN' | 'CLOSED' | 'PRE_MARKET' | 'AFTER_HOURS';

// 미국 시장 세션 정보
export interface MarketSession {
  status: MarketStatus;
  currentTime: Date;
  nextOpen: Date | null;
  nextClose: Date | null;
  timezone: string;
  isDST: boolean; // 서머타임 여부
}

// 미국 휴장일 목록 (2024-2025)
const US_MARKET_HOLIDAYS: Record<string, string[]> = {
  '2024': [
    '2024-01-01', // New Year's Day
    '2024-01-15', // Martin Luther King Jr. Day
    '2024-02-19', // Presidents' Day
    '2024-03-29', // Good Friday
    '2024-05-27', // Memorial Day
    '2024-06-19', // Juneteenth
    '2024-07-04', // Independence Day
    '2024-09-02', // Labor Day
    '2024-11-28', // Thanksgiving
    '2024-12-25'  // Christmas
  ],
  '2025': [
    '2025-01-01', // New Year's Day
    '2025-01-20', // Martin Luther King Jr. Day
    '2025-02-17', // Presidents' Day
    '2025-04-18', // Good Friday
    '2025-05-26', // Memorial Day
    '2025-06-19', // Juneteenth
    '2025-07-04', // Independence Day
    '2025-09-01', // Labor Day
    '2025-11-27', // Thanksgiving
    '2025-12-25'  // Christmas
  ]
};

// 서머타임 시작/종료 날짜 계산
const getDSTDates = (year: number): { start: Date; end: Date } => {
  // 서머타임 시작: 3월 둘째 주 일요일
  const march = new Date(year, 2, 1); // 3월 1일
  const firstSunday = new Date(march);
  firstSunday.setDate(1 + (7 - march.getDay()) % 7);
  const secondSunday = new Date(firstSunday);
  secondSunday.setDate(firstSunday.getDate() + 7);
  
  // 서머타임 종료: 11월 첫째 주 일요일
  const november = new Date(year, 10, 1); // 11월 1일
  const novFirstSunday = new Date(november);
  novFirstSunday.setDate(1 + (7 - november.getDay()) % 7);
  
  return {
    start: secondSunday,
    end: novFirstSunday
  };
};

/**
 * 주어진 날짜가 서머타임 기간인지 확인
 */
export const isDaylightSavingTime = (date: Date): boolean => {
  const year = date.getFullYear();
  const { start, end } = getDSTDates(year);
  
  return date >= start && date < end;
};

/**
 * 현재 동부시간 기준 시간 가져오기
 */
export const getEasternTime = (date: Date = new Date()): Date => {
  const utc = new Date(date.getTime() + date.getTimezoneOffset() * 60000);
  const isDST = isDaylightSavingTime(date);
  const offset = isDST ? -4 : -5; // EDT: -4, EST: -5
  
  return new Date(utc.getTime() + offset * 3600000);
};

/**
 * 주어진 날짜가 미국 시장 휴장일인지 확인
 */
export const isMarketHoliday = (date: Date): boolean => {
  const year = date.getFullYear().toString();
  const dateString = date.toISOString().split('T')[0];
  
  if (!dateString) return false;
  
  const holidays = US_MARKET_HOLIDAYS[year] || [];
  return holidays.includes(dateString);
};

/**
 * 주어진 날짜가 주말인지 확인
 */
export const isWeekend = (date: Date): boolean => {
  const dayOfWeek = date.getDay();
  return dayOfWeek === 0 || dayOfWeek === 6; // 일요일(0) 또는 토요일(6)
};

/**
 * 시장 개장/폐장 시간 계산 (동부시간 기준)
 */
export const getMarketHours = (date: Date): { open: Date; close: Date } => {
  const easternDate = getEasternTime(date);
  
  // 정규 시간: 9:30 AM - 4:00 PM ET
  const open = new Date(easternDate);
  open.setHours(9, 30, 0, 0);
  
  const close = new Date(easternDate);
  close.setHours(16, 0, 0, 0);
  
  return { open, close };
};

/**
 * 다음 영업일 찾기
 */
export const getNextTradingDay = (date: Date): Date => {
  let nextDay = new Date(date);
  nextDay.setDate(nextDay.getDate() + 1);
  
  // 주말이나 휴장일이 아닌 날짜 찾기
  while (isWeekend(nextDay) || isMarketHoliday(nextDay)) {
    nextDay.setDate(nextDay.getDate() + 1);
  }
  
  return nextDay;
};

/**
 * 현재 미국 시장 상태 및 세션 정보 계산
 */
export const getCurrentMarketSession = (): MarketSession => {
  const now = new Date();
  const easternNow = getEasternTime(now);
  const isDST = isDaylightSavingTime(now);
  
  // 오늘이 영업일인지 확인
  const isBusinessDay = !isWeekend(easternNow) && !isMarketHoliday(easternNow);
  
  let status: MarketStatus;
  let nextOpen: Date | null = null;
  let nextClose: Date | null = null;
  
  if (isBusinessDay) {
    const { open, close } = getMarketHours(easternNow);
    const currentTime = easternNow.getTime();
    const openTime = open.getTime();
    const closeTime = close.getTime();
    
    // 프리마켓: 4:00 AM - 9:30 AM ET
    const preMarketStart = new Date(easternNow);
    preMarketStart.setHours(4, 0, 0, 0);
    const preMarketTime = preMarketStart.getTime();
    
    // 애프터마켓: 4:00 PM - 8:00 PM ET
    const afterMarketEnd = new Date(easternNow);
    afterMarketEnd.setHours(20, 0, 0, 0);
    const afterMarketTime = afterMarketEnd.getTime();
    
    if (currentTime >= openTime && currentTime < closeTime) {
      // 정규 시간
      status = 'OPEN';
      nextClose = close;
    } else if (currentTime >= preMarketTime && currentTime < openTime) {
      // 프리마켓
      status = 'PRE_MARKET';
      nextOpen = open;
    } else if (currentTime >= closeTime && currentTime < afterMarketTime) {
      // 애프터마켓
      status = 'AFTER_HOURS';
      const nextTradingDay = getNextTradingDay(easternNow);
      const nextTradingOpen = getMarketHours(nextTradingDay).open;
      nextOpen = nextTradingOpen;
    } else {
      // 장외 시간
      status = 'CLOSED';
      const nextTradingDay = getNextTradingDay(easternNow);
      const nextTradingOpen = getMarketHours(nextTradingDay).open;
      nextOpen = nextTradingOpen;
    }
  } else {
    // 주말이나 휴장일
    status = 'CLOSED';
    const nextTradingDay = getNextTradingDay(easternNow);
    const nextTradingOpen = getMarketHours(nextTradingDay).open;
    nextOpen = nextTradingOpen;
  }
  
  return {
    status,
    currentTime: easternNow,
    nextOpen,
    nextClose,
    timezone: isDST ? 'EDT' : 'EST',
    isDST
  };
};

/**
 * 시장 상태를 한국어로 변환
 */
export const getMarketStatusText = (status: MarketStatus, isDST: boolean = false): string => {
  const timezone = isDST ? 'EDT' : 'EST';
  
  switch (status) {
    case 'OPEN':
      return `정규 거래중 (${timezone})`;
    case 'PRE_MARKET':
      return `프리마켓 (${timezone})`;
    case 'AFTER_HOURS':
      return `애프터마켓 (${timezone})`;
    case 'CLOSED':
      return `휴장중 (${timezone})`;
    default:
      return `알 수 없음 (${timezone})`;
  }
};

/**
 * 다음 개장/폐장까지의 남은 시간 계산
 */
export const getTimeUntilNextSession = (session: MarketSession): string => {
  const now = session.currentTime.getTime();
  const target = session.status === 'OPEN' ? session.nextClose : session.nextOpen;
  
  if (!target) return '';
  
  const diff = target.getTime() - now;
  if (diff <= 0) return '';
  
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
  
  if (hours > 0) {
    return `${hours}시간 ${minutes}분`;
  } else {
    return `${minutes}분`;
  }
};

/**
 * 시장 상태 색상 가져오기
 */
export const getMarketStatusColor = (status: MarketStatus): string => {
  switch (status) {
    case 'OPEN':
      return '#4caf50'; // 초록색 - 개장
    case 'PRE_MARKET':
      return '#ff9800'; // 주황색 - 프리마켓
    case 'AFTER_HOURS':
      return '#2196f3'; // 파란색 - 애프터마켓
    case 'CLOSED':
      return '#f44336'; // 빨간색 - 휴장
    default:
      return '#9e9e9e'; // 회색 - 알 수 없음
  }
};

/**
 * 실시간 시장 상태 업데이트를 위한 훅에서 사용할 계산 함수
 */
export const calculateMarketStatus = (): MarketSession => {
  return getCurrentMarketSession();
};

/**
 * 시장 시간 포맷터 (동부시간)
 */
export const formatMarketTime = (date: Date, isDST: boolean = false): string => {
  const timezone = isDST ? 'EDT' : 'EST';
  const easternTime = getEasternTime(date);
  
  const options: Intl.DateTimeFormatOptions = {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZone: 'America/New_York'
  };
  
  return `${easternTime.toLocaleTimeString('en-US', options)} ${timezone}`;
};

/**
 * 시장 개장일 체크 (주말 및 휴장일 제외)
 */
export const isTradingDay = (date: Date = new Date()): boolean => {
  return !isWeekend(date) && !isMarketHoliday(date);
};

/**
 * 시장 개장 시간 체크 (정규 시간만)
 */
export const isMarketOpen = (date: Date = new Date()): boolean => {
  if (!isTradingDay(date)) return false;
  
  const easternTime = getEasternTime(date);
  const { open, close } = getMarketHours(easternTime);
  
  return easternTime >= open && easternTime < close;
};