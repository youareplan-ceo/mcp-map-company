/**
 * StockPilot AI 유틸리티 함수들
 * 한국 주식시장에 특화된 공통 함수들
 */

import { format, parseISO, isToday, isYesterday } from 'date-fns';
import { ko } from 'date-fns/locale';
import numeral from 'numeral';
import {
  InvestmentSignal,
  ConfidenceLevel,
  Market
} from '../types';

/**
 * 숫자 포맷팅 유틸리티
 */
export class NumberUtils {
  /**
   * 한국 원화 포맷팅
   * @param value 숫자 값
   * @param showUnit 단위 표시 여부
   * @returns 포맷된 문자열
   */
  static formatKRW(value: number, showUnit: boolean = true): string {
    if (value === 0) return showUnit ? '0원' : '0';
    
    const absValue = Math.abs(value);
    const isNegative = value < 0;
    const prefix = isNegative ? '-' : '';
    
    if (absValue >= 1_000_000_000_000) {
      // 조 단위
      const formatted = numeral(absValue / 1_000_000_000_000).format('0,0.00');
      return `${prefix}${formatted}${showUnit ? '조원' : '조'}`;
    } else if (absValue >= 100_000_000) {
      // 억 단위
      const formatted = numeral(absValue / 100_000_000).format('0,0.0');
      return `${prefix}${formatted}${showUnit ? '억원' : '억'}`;
    } else if (absValue >= 10_000) {
      // 만 단위
      const formatted = numeral(absValue / 10_000).format('0,0.0');
      return `${prefix}${formatted}${showUnit ? '만원' : '만'}`;
    } else {
      // 원 단위
      const formatted = numeral(absValue).format('0,0');
      return `${prefix}${formatted}${showUnit ? '원' : ''}`;
    }
  }

  /**
   * 백분율 포맷팅
   * @param value 소수로 표현된 비율 (0.05 = 5%)
   * @param decimals 소수점 자리수
   * @returns 포맷된 백분율 문자열
   */
  static formatPercent(value: number, decimals: number = 2): string {
    if (value === 0) return '0.00%';
    
    const formatted = numeral(value / 100).format(`0,0.${'0'.repeat(decimals)}%`);
    return value > 0 ? `+${formatted}` : formatted;
  }

  /**
   * 주가 포맷팅
   * @param price 주가
   * @returns 포맷된 주가 문자열
   */
  static formatPrice(price: number): string {
    if (price >= 10000) {
      return numeral(price).format('0,0');
    } else if (price >= 1000) {
      return numeral(price).format('0,0');
    } else {
      return numeral(price).format('0,0.00');
    }
  }

  /**
   * 거래량 포맷팅
   * @param volume 거래량
   * @returns 포맷된 거래량 문자열
   */
  static formatVolume(volume: number): string {
    if (volume >= 100_000_000) {
      return numeral(volume / 100_000_000).format('0,0.0') + '억';
    } else if (volume >= 10_000) {
      return numeral(volume / 10_000).format('0,0.0') + '만';
    } else {
      return numeral(volume).format('0,0');
    }
  }

  /**
   * 시가총액 포맷팅
   * @param marketCap 시가총액
   * @returns 포맷된 시가총액 문자열
   */
  static formatMarketCap(marketCap: number): string {
    if (marketCap >= 1_000_000_000_000) {
      return numeral(marketCap / 1_000_000_000_000).format('0,0.0') + '조';
    } else if (marketCap >= 100_000_000) {
      return numeral(marketCap / 100_000_000).format('0,0') + '억';
    } else {
      return this.formatKRW(marketCap, false);
    }
  }

  /**
   * 압축된 숫자 표시 (K, M, B 등)
   * @param value 숫자 값
   * @returns 압축된 숫자 문자열
   */
  static formatCompact(value: number): string {
    if (Math.abs(value) >= 1_000_000_000) {
      return numeral(value / 1_000_000_000).format('0.0a');
    } else if (Math.abs(value) >= 1_000_000) {
      return numeral(value / 1_000_000).format('0.0a');
    } else if (Math.abs(value) >= 1_000) {
      return numeral(value / 1_000).format('0.0a');
    } else {
      return numeral(value).format('0,0');
    }
  }

  /**
   * 숫자 포맷팅 (소수점 자리수 지정)
   * @param value 숫자 값
   * @param decimals 소수점 자리수
   * @returns 포맷된 숫자 문자열
   */
  static formatNumber(value: number, decimals: number = 2): string {
    return numeral(value).format(`0,0.${'0'.repeat(decimals)}`);
  }
}

/**
 * 날짜/시간 포맷팅 유틸리티
 */
export class DateUtils {
  /**
   * 한국 날짜 포맷팅
   * @param date 날짜 문자열 또는 Date 객체
   * @param formatStr 포맷 문자열
   * @returns 포맷된 날짜 문자열
   */
  static formatKorean(date: string | Date, formatStr: string = 'yyyy.MM.dd'): string {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    return format(dateObj, formatStr, { locale: ko });
  }

  /**
   * 상대 시간 표시
   * @param date 날짜
   * @returns 상대 시간 문자열
   */
  static formatRelative(date: string | Date): string {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    
    if (isToday(dateObj)) {
      return format(dateObj, 'HH:mm');
    } else if (isYesterday(dateObj)) {
      return '어제 ' + format(dateObj, 'HH:mm');
    } else {
      return format(dateObj, 'MM.dd', { locale: ko });
    }
  }

  /**
   * 상대 시간 표시 (formatRelative의 별칭)
   * @param date 날짜
   * @returns 상대 시간 문자열
   */
  static formatRelativeTime(date: string | Date): string {
    return this.formatRelative(date);
  }

  /**
   * 시장 시간 포맷팅
   * @param date 날짜
   * @returns 시장 시간 형식
   */
  static formatMarketTime(date: string | Date): string {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    return format(dateObj, 'HH:mm:ss');
  }

  /**
   * 거래일 여부 확인 (주말 제외, 공휴일은 별도 처리 필요)
   * @param date 날짜
   * @returns 거래일 여부
   */
  static isTradingDay(date: Date = new Date()): boolean {
    const day = date.getDay();
    return day !== 0 && day !== 6; // 일요일(0), 토요일(6) 제외
  }

  /**
   * 현재 시간이 장 시간인지 확인
   * @returns 장 시간 여부
   */
  static isMarketHours(): boolean {
    const now = new Date();
    const hours = now.getHours();
    const minutes = now.getMinutes();
    const currentTime = hours * 60 + minutes;
    
    // 오전 9시부터 오후 3시 30분까지
    const marketOpen = 9 * 60;         // 09:00
    const marketClose = 15 * 60 + 30;  // 15:30
    
    return this.isTradingDay(now) && currentTime >= marketOpen && currentTime <= marketClose;
  }

  /**
   * 장 마감까지 남은 시간 계산
   * @returns 남은 분 수 (장 마감 후면 음수)
   */
  static minutesToMarketClose(): number {
    const now = new Date();
    const marketClose = new Date();
    marketClose.setHours(15, 30, 0, 0);
    
    return Math.floor((marketClose.getTime() - now.getTime()) / (1000 * 60));
  }
}

/**
 * 투자 시그널 관련 유틸리티
 */
export class SignalUtils {
  /**
   * 시그널 한글 라벨 반환
   * @param signal 투자 시그널
   * @returns 한글 라벨
   */
  static getSignalLabel(signal: InvestmentSignal): string {
    const labels = {
      [InvestmentSignal.STRONG_BUY]: '강력 매수',
      [InvestmentSignal.BUY]: '매수',
      [InvestmentSignal.HOLD]: '관망',
      [InvestmentSignal.SELL]: '매도',
      [InvestmentSignal.STRONG_SELL]: '강력 매도'
    };
    return labels[signal] || '알 수 없음';
  }

  /**
   * 시그널 색상 반환
   * @param signal 투자 시그널
   * @returns 색상 코드
   */
  static getSignalColor(signal: InvestmentSignal): string {
    const colors = {
      [InvestmentSignal.STRONG_BUY]: '#d32f2f',   // 진한 빨강 (상승)
      [InvestmentSignal.BUY]: '#f57c00',          // 주황 (상승)
      [InvestmentSignal.HOLD]: '#757575',         // 회색 (중립)
      [InvestmentSignal.SELL]: '#1976d2',         // 파랑 (하락)
      [InvestmentSignal.STRONG_SELL]: '#303f9f'   // 진한 파랑 (하락)
    };
    return colors[signal] || '#757575';
  }

  /**
   * 신뢰도 레벨 한글 라벨 반환
   * @param level 신뢰도 레벨
   * @returns 한글 라벨
   */
  static getConfidenceLabel(level: ConfidenceLevel): string {
    const labels = {
      [ConfidenceLevel.VERY_LOW]: '매우 낮음',
      [ConfidenceLevel.LOW]: '낮음',
      [ConfidenceLevel.MEDIUM]: '보통',
      [ConfidenceLevel.HIGH]: '높음',
      [ConfidenceLevel.VERY_HIGH]: '매우 높음'
    };
    return labels[level] || '알 수 없음';
  }

  /**
   * 신뢰도 점수로 레벨 계산
   * @param score 신뢰도 점수 (0-100)
   * @returns 신뢰도 레벨
   */
  static scoreToConfidenceLevel(score: number): ConfidenceLevel {
    if (score >= 80) return ConfidenceLevel.VERY_HIGH;
    if (score >= 65) return ConfidenceLevel.HIGH;
    if (score >= 45) return ConfidenceLevel.MEDIUM;
    if (score >= 25) return ConfidenceLevel.LOW;
    return ConfidenceLevel.VERY_LOW;
  }
}

/**
 * 시장 관련 유틸리티
 */
export class MarketUtils {
  /**
   * 시장 한글 라벨 반환
   * @param market 시장 타입
   * @returns 한글 라벨
   */
  static getMarketLabel(market: Market): string {
    const labels = {
      [Market.KOSPI]: '코스피',
      [Market.KOSDAQ]: '코스닥',
      [Market.KONEX]: '코넥스'
    };
    return labels[market] || '알 수 없음';
  }

  /**
   * 시장별 색상 반환
   * @param market 시장 타입
   * @returns 색상 코드
   */
  static getMarketColor(market: Market): string {
    const colors = {
      [Market.KOSPI]: '#1976d2',      // 파랑
      [Market.KOSDAQ]: '#388e3c',     // 초록
      [Market.KONEX]: '#f57c00'       // 주황
    };
    return colors[market] || '#757575';
  }

  /**
   * 종목 코드 유효성 검사
   * @param symbol 종목 코드
   * @returns 유효 여부
   */
  static isValidSymbol(symbol: string): boolean {
    return /^\d{6}$/.test(symbol);
  }

  /**
   * 등락률에 따른 색상 반환
   * @param changeRate 등락률
   * @returns 색상 코드
   */
  static getPriceChangeColor(changeRate: number): string {
    if (changeRate > 0) return '#d32f2f';      // 빨강 (상승)
    if (changeRate < 0) return '#1976d2';      // 파랑 (하락)
    return '#757575';                          // 회색 (보합)
  }

  /**
   * 등락률 표시 문자열 (+ 또는 - 기호 포함)
   * @param changeRate 등락률
   * @returns 포맷된 등락률 문자열
   */
  static formatChangeRate(changeRate: number): string {
    const formatted = NumberUtils.formatPercent(changeRate);
    if (changeRate > 0 && !formatted.startsWith('+')) {
      return '+' + formatted;
    }
    return formatted;
  }

  /**
   * 가격 변화량 표시
   * @param change 변화량
   * @returns 포맷된 변화량 문자열
   */
  static formatPriceChange(change: number): string {
    const formatted = NumberUtils.formatPrice(Math.abs(change));
    if (change > 0) return `+${formatted}`;
    if (change < 0) return `-${formatted}`;
    return formatted;
  }
}

/**
 * 문자열 유틸리티
 */
export class StringUtils {
  /**
   * 문자열 자르기 (한글 고려)
   * @param str 원본 문자열
   * @param maxLength 최대 길이
   * @param ellipsis 말줄임표 추가 여부
   * @returns 자른 문자열
   */
  static truncate(str: string, maxLength: number, ellipsis: boolean = true): string {
    if (str.length <= maxLength) return str;
    
    const truncated = str.substring(0, maxLength);
    return ellipsis ? truncated + '...' : truncated;
  }

  /**
   * 검색어 하이라이트
   * @param text 원본 텍스트
   * @param query 검색어
   * @returns 하이라이트된 HTML 문자열
   */
  static highlight(text: string, query: string): string {
    if (!query.trim()) return text;
    
    const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`(${escapedQuery})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
  }

  /**
   * 한글 종목명 검색 매칭
   * @param stockName 종목명
   * @param query 검색어
   * @returns 매치 점수 (0-100)
   */
  static matchKoreanStock(stockName: string, query: string): number {
    const name = stockName.toLowerCase();
    const search = query.toLowerCase();
    
    // 완전 일치
    if (name === search) return 100;
    
    // 시작 일치
    if (name.startsWith(search)) return 90;
    
    // 포함 일치
    if (name.includes(search)) return 70;
    
    // 초성 매칭 (간단한 버전)
    const nameChars = name.split('');
    const searchChars = search.split('');
    let matchCount = 0;
    
    for (const char of searchChars) {
      if (nameChars.includes(char)) {
        matchCount++;
      }
    }
    
    return Math.floor((matchCount / searchChars.length) * 50);
  }
}

/**
 * 로컬 스토리지 유틸리티
 */
export class StorageUtils {
  /**
   * 로컬 스토리지에 데이터 저장
   * @param key 키
   * @param value 값
   */
  static set(key: string, value: any): void {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.error('로컬 스토리지 저장 실패:', error);
    }
  }

  /**
   * 로컬 스토리지에서 데이터 조회
   * @param key 키
   * @param defaultValue 기본값
   * @returns 저장된 값 또는 기본값
   */
  static get<T>(key: string, defaultValue: T | null = null): T | null {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue;
    } catch (error) {
      console.error('로컬 스토리지 조회 실패:', error);
      return defaultValue;
    }
  }

  /**
   * 로컬 스토리지에서 데이터 삭제
   * @param key 키
   */
  static remove(key: string): void {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.error('로컬 스토리지 삭제 실패:', error);
    }
  }

  /**
   * 로컬 스토리지 전체 삭제
   */
  static clear(): void {
    try {
      localStorage.clear();
    } catch (error) {
      console.error('로컬 스토리지 초기화 실패:', error);
    }
  }
}

/**
 * URL 파라미터 유틸리티
 */
export class URLUtils {
  /**
   * URL 파라미터를 객체로 변환
   * @param search location.search 문자열
   * @returns 파라미터 객체
   */
  static parseSearchParams(search: string): Record<string, string> {
    const params = new URLSearchParams(search);
    const result: Record<string, string> = {};
    
    params.forEach((value, key) => {
      result[key] = value;
    });
    
    return result;
  }

  /**
   * 객체를 URL 파라미터 문자열로 변환
   * @param params 파라미터 객체
   * @returns URL 파라미터 문자열
   */
  static stringifySearchParams(params: Record<string, any>): string {
    const searchParams = new URLSearchParams();
    
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.set(key, String(value));
      }
    });
    
    return searchParams.toString();
  }
}

// 클래스들은 이미 export 키워드로 내보내짐