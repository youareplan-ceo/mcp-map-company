/**
 * 포트폴리오 관련 타입 정의
 * StockPilot AI 포트폴리오 관리 시스템의 타입 정의
 */

// 주식 정보 (포트폴리오용)
export interface StockInfo {
  symbol: string;
  name: string;
  currentPrice: number;
  change: number;
  changeRate: number;
  market?: 'KOSPI' | 'KOSDAQ' | 'KONEX';
  sector?: string;
}

// 포트폴리오 보유 종목
export interface Holding {
  id: string;
  symbol: string;
  stock: StockInfo;
  quantity: number;
  averagePrice: number;
  currentValue: number;
  totalCost: number;
  unrealizedPL: number;
  unrealizedPLRate: number;
  weight: number;
  addedAt: string;
  lastUpdated: string;
}

// 포트폴리오 요약 정보
export interface PortfolioSummary {
  id: string;
  name: string;
  totalValue: number;
  totalCost: number;
  totalPL: number;
  totalPLRate: number;
  totalReturn: number;
  totalReturnRate: number;
  todayPL: number;
  todayPLRate: number;
  todayReturn: number;
  todayReturnRate: number;
  cashBalance: number;
  assetAllocation: {
    stocks: number;
    cash: number;
  };
  holdingsCount: number;
  lastUpdated: string;
}

// 포트폴리오 추천 정보
export interface Recommendation {
  id: string;
  type: 'BUY' | 'SELL' | 'REBALANCE' | 'HOLD';
  symbol: string;
  name: string;
  title: string;
  description: string;
  currentPrice: number;
  targetPrice?: number;
  reasoning: string;
  confidence: number;
  expectedReturn?: number;
  riskLevel: number;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  validUntil: string;
  createdAt: string;
}

// 성과 데이터 포인트
export interface PerformancePoint {
  date: string;
  portfolioValue: number;
  totalReturn: number;
  totalReturnRate: number;
  dayReturn: number;
  dayReturnRate: number;
  benchmarkReturn?: number;
  benchmarkReturnRate?: number;
}

// 포트폴리오 성과 히스토리
export interface PerformanceHistory {
  data: PerformancePoint[];
  summary: {
    totalReturn: number;
    totalReturnRate: number;
    maxDrawdown: number;
    volatility: number;
    sharpeRatio: number;
    benchmarkOutperformance: number;
  };
}

// 종목 추가 요청 데이터
export interface AddHoldingRequest {
  symbol: string;
  quantity: number;
  averagePrice: number;
  note?: string;
}

// 종목 수정 요청 데이터
export interface UpdateHoldingRequest {
  quantity?: number;
  averagePrice?: number;
  note?: string;
}

// 포트폴리오 분석 데이터
export interface PortfolioAnalysis {
  diversification: {
    sectorWeights: Array<{
      sector: string;
      weight: number;
      count: number;
    }>;
    marketWeights: Array<{
      market: string;
      weight: number;
      count: number;
    }>;
    concentration: {
      top5Weight: number;
      top10Weight: number;
      herfindahlIndex: number;
    };
  };
  riskMetrics: {
    beta: number;
    volatility: number;
    valueAtRisk: number;
    maxDrawdown: number;
    correlationWithMarket: number;
  };
  performance: {
    totalReturn: number;
    annualizedReturn: number;
    sharpeRatio: number;
    informationRatio: number;
    alphaReturn: number;
    benchmarkComparison: {
      portfolio: number;
      kospi: number;
      kosdaq: number;
    };
  };
}

// 포트폴리오 리밸런싱 제안
export interface RebalancingSuggestion {
  id: string;
  type: 'SECTOR_REBALANCE' | 'RISK_ADJUSTMENT' | 'OPPORTUNITY_BASED';
  title: string;
  description: string;
  actions: Array<{
    action: 'BUY' | 'SELL' | 'HOLD';
    symbol: string;
    name: string;
    currentWeight: number;
    targetWeight: number;
    quantity: number;
    amount: number;
  }>;
  expectedImpact: {
    riskReduction: number;
    returnImprovement: number;
    costEstimate: number;
  };
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  validUntil: string;
}

// API 응답 타입들
export interface PortfolioSummaryResponse {
  data: PortfolioSummary;
}

export interface HoldingsResponse {
  data: Holding[];
}

export interface RecommendationsResponse {
  data: Recommendation[];
}

export interface PerformanceHistoryResponse {
  data: PerformanceHistory;
}

export interface AddHoldingResponse {
  data: Holding;
}

// 기본값 제공
export const defaultPortfolioSummary: PortfolioSummary = {
  id: '',
  name: '기본 포트폴리오',
  totalValue: 0,
  totalCost: 0,
  totalPL: 0,
  totalPLRate: 0,
  totalReturn: 0,
  totalReturnRate: 0,
  todayPL: 0,
  todayPLRate: 0,
  todayReturn: 0,
  todayReturnRate: 0,
  cashBalance: 0,
  assetAllocation: {
    stocks: 0,
    cash: 100,
  },
  holdingsCount: 0,
  lastUpdated: new Date().toISOString(),
};

// 유틸리티 함수들
export const formatCurrency = (amount: number): string => {
  return new Intl.NumberFormat('ko-KR', {
    style: 'currency',
    currency: 'KRW',
    minimumFractionDigits: 0,
  }).format(amount);
};

export const formatPercent = (rate: number): string => {
  return `${(rate >= 0 ? '+' : '')}${rate.toFixed(2)}%`;
};

export const formatNumber = (num: number): string => {
  return new Intl.NumberFormat('ko-KR').format(num);
};