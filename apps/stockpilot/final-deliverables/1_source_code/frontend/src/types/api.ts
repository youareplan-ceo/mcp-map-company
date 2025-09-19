/**
 * StockPilot AI API 응답 타입 정의
 * 백엔드 API와의 타입 안전성을 보장하기 위한 인터페이스
 */

// 기본 서비스 상태 타입
export type ServiceStatus = 'online' | 'degraded' | 'offline' | 'unknown';
export type OverallStatus = 'operational' | 'degraded' | 'outage';

// 시스템 상태 인터페이스
export interface SystemStatus {
  overall_status: OverallStatus;
  services: {
    api: ServiceStatus;
    database: ServiceStatus;
    ai_engine: ServiceStatus;
    websocket: ServiceStatus;
    batch_system: ServiceStatus;
    usage_tracking: ServiceStatus;
    external_apis: ServiceStatus;
  };
  last_updated: string;
  system_info?: {
    version: string;
    environment: string;
    uptime_seconds?: number;
  };
}

// 모델별 사용량 타입
export interface ModelUsage {
  requests: number;
  tokens: number;
  cost: number;
}

// 일별 사용량 데이터
export interface DailyUsage {
  date: string;
  total_requests: number;
  total_tokens: number;
  total_cost: number;
  success_requests: number;
  failed_requests: number;
  cost_usage_percent: number;
  success_rate_percent: number;
  avg_response_time_ms: number;
  model_usage?: {
    [model: string]: ModelUsage;
  };
}

// 사용량 제한 설정
export interface UsageLimits {
  daily_limit: number;
  monthly_limit: number;
  alert_threshold: number;
}

// 사용량 요약 통계
export interface UsageSummary {
  total_days_tracked: number;
  total_cost_to_date: number;
  total_requests_to_date: number;
  avg_daily_cost: number;
  avg_success_rate: number;
}

// 전체 사용량 통계 인터페이스
export interface UsageStats {
  daily_usage: {
    [date: string]: DailyUsage;
  };
  current_limits: UsageLimits;
  summary: UsageSummary;
}

// API 기본 응답 래퍼
export interface BaseResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
  timestamp?: string;
}

// 페이지네이션 응답
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// 주식 정보 기본 타입
export interface StockInfo {
  symbol: string;
  name: string;
  market: string;
  sector?: string;
  industry?: string;
}

// 주식 가격 정보
export interface StockPrice {
  symbol: string;
  current_price: number;
  change: number;
  change_percent: number;
  volume: number;
  market_cap?: number;
  updated_at: string;
}

// AI 분석 결과
export interface AIAnalysis {
  symbol: string;
  analysis_type: 'technical' | 'fundamental' | 'sentiment';
  score: number;
  recommendation: 'BUY' | 'SELL' | 'HOLD';
  confidence: number;
  summary: string;
  factors: string[];
  created_at: string;
}

// 뉴스 감정 분석
export interface NewsSentiment {
  id: string;
  title: string;
  content: string;
  sentiment: 'positive' | 'negative' | 'neutral';
  sentiment_score: number;
  symbols: string[];
  published_at: string;
  source: string;
}

// 투자 신호
export interface InvestmentSignal {
  id: string;
  symbol: string;
  signal_type: 'BUY' | 'SELL' | 'HOLD';
  strength: number;
  confidence: number;
  reasoning: string;
  created_at: string;
  expires_at?: string;
}

// 차트 데이터 포인트
export interface ChartDataPoint {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

// 기술적 지표
export interface TechnicalIndicators {
  rsi?: number;
  macd?: {
    value: number;
    signal: number;
    histogram: number;
  };
  bollinger_bands?: {
    upper: number;
    middle: number;
    lower: number;
  };
  moving_averages?: {
    ma5: number;
    ma20: number;
    ma50: number;
    ma200: number;
  };
}

// 시장 상태
export interface MarketStatus {
  market: string;
  status: 'open' | 'closed' | 'pre_market' | 'after_hours';
  next_open?: string;
  next_close?: string;
  timezone: string;
}

// 포트폴리오 정보
export interface Portfolio {
  id: string;
  name: string;
  total_value: number;
  cash_balance: number;
  holdings: PortfolioHolding[];
  performance: PortfolioPerformance;
}

// 포트폴리오 보유 종목
export interface PortfolioHolding {
  symbol: string;
  quantity: number;
  avg_price: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  weight: number;
}

// 포트폴리오 성과
export interface PortfolioPerformance {
  total_return: number;
  total_return_percent: number;
  daily_return: number;
  daily_return_percent: number;
  sharpe_ratio?: number;
  max_drawdown?: number;
}

// 타입 가드 함수들
export const isServiceStatus = (status: any): status is ServiceStatus => {
  return ['online', 'degraded', 'offline', 'unknown'].includes(status);
};

export const isOverallStatus = (status: any): status is OverallStatus => {
  return ['operational', 'degraded', 'outage'].includes(status);
};

// 기본값 객체들
export const defaultSystemStatus: SystemStatus = {
  overall_status: 'operational',
  services: {
    api: 'online',
    database: 'unknown',
    ai_engine: 'unknown',
    websocket: 'unknown',
    batch_system: 'unknown',
    usage_tracking: 'unknown',
    external_apis: 'unknown',
  },
  last_updated: new Date().toISOString(),
};

export const defaultUsageStats: UsageStats = {
  daily_usage: {},
  current_limits: {
    daily_limit: 100,
    monthly_limit: 3000,
    alert_threshold: 0.8,
  },
  summary: {
    total_days_tracked: 0,
    total_cost_to_date: 0,
    total_requests_to_date: 0,
    avg_daily_cost: 0,
    avg_success_rate: 0,
  },
};