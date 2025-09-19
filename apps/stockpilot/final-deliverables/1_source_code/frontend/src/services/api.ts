/**
 * StockPilot AI API 서비스 레이어
 * 백엔드 API와의 통신을 담당하는 중앙화된 서비스
 */

import axios, { AxiosResponse, AxiosError } from 'axios';
import { toast } from 'react-toastify';
import {
  BaseResponse,
  PaginatedResponse,
  StockInfo,
  StockPrice,
  AIAnalysis,
  Portfolio,
  InvestmentSignalItem,
  ChartDataPoint,
  TechnicalIndicators,
  MarketStatus,
  StockSearchResult,
  FilterOptions,
  SortOption,
  DateRange,
  Pagination
} from '../types';
import { NewsItem, NewsFilters, NewsSummary, TrendingKeyword, NewsSentiment } from '../types/news';
import { 
  PortfolioSummary, 
  Holding, 
  Recommendation, 
  PerformanceHistory, 
  AddHoldingRequest, 
  UpdateHoldingRequest 
} from '../types/portfolio';

import { ENV } from '../env';

// API 기본 설정

// Axios 인스턴스 생성
const apiClient = axios.create({
  baseURL: ENV.API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
});

// 요청 인터셉터 - 인증 토큰 자동 추가
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // 요청 로깅 (개발 환경)
    if (process.env.NODE_ENV === 'development') {
      console.log(`🚀 API Request: ${config.method?.toUpperCase()} ${config.url}`, config.data);
    }
    
    return config;
  },
  (error) => {
    console.error('❌ API Request Error:', error);
    return Promise.reject(error);
  }
);

// 응답 인터셉터 - 에러 처리
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    // 응답 로깅 (개발 환경)
    if (process.env.NODE_ENV === 'development') {
      console.log(`✅ API Response: ${response.config.url}`, response.data);
    }
    
    return response;
  },
  (error: AxiosError) => {
    console.error('❌ API Response Error:', error);
    
    // 공통 에러 처리
    if (error.response?.status === 401) {
      // 인증 실패 - 토큰 삭제 및 로그인 페이지로 리다이렉트
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
      toast.error('인증이 만료되었습니다. 다시 로그인해주세요.');
    } else if (error.response?.status === 403) {
      toast.error('접근 권한이 없습니다.');
    } else if ((error.response?.status ?? 0) >= 500) {
      toast.error('서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
    } else if (error.code === 'NETWORK_ERROR') {
      toast.error('네트워크 오류가 발생했습니다. 연결을 확인해주세요.');
    }
    
    return Promise.reject(error);
  }
);

/**
 * 주식 관련 API 서비스
 */
export class StockService {
  // 종목 검색
  static async searchStocks(
    query: string, 
    limit: number = 20
  ): Promise<StockSearchResult[]> {
    const response = await apiClient.get<BaseResponse<StockSearchResult[]>>(
      '/stocks/search', 
      { params: { q: query, limit } }
    );
    return response.data.data;
  }

  // 종목 정보 조회
  static async getStockInfo(symbol: string): Promise<StockInfo> {
    const response = await apiClient.get<BaseResponse<StockInfo>>(`/stocks/${symbol}/info`);
    return response.data.data;
  }

  // 실시간 주가 조회
  static async getStockPrice(symbol: string): Promise<StockPrice> {
    const response = await apiClient.get<BaseResponse<StockPrice>>(`/stocks/${symbol}/price`);
    return response.data.data;
  }

  // 다중 종목 주가 조회
  static async getMultipleStockPrices(symbols: string[]): Promise<StockPrice[]> {
    const response = await apiClient.post<BaseResponse<StockPrice[]>>(
      '/stocks/prices', 
      { symbols }
    );
    return response.data.data;
  }

  // AI 분석 결과 조회
  static async getAIAnalysis(symbol: string): Promise<AIAnalysis> {
    const response = await apiClient.get<BaseResponse<AIAnalysis>>(`/stocks/${symbol}/analysis`);
    return response.data.data;
  }

  // 차트 데이터 조회
  static async getChartData(
    symbol: string, 
    interval: string = '1d', 
    period: number = 30
  ): Promise<ChartDataPoint[]> {
    const response = await apiClient.get<BaseResponse<ChartDataPoint[]>>(
      `/stocks/${symbol}/chart`,
      { params: { interval, period } }
    );
    return response.data.data;
  }

  // 기술적 지표 조회
  static async getTechnicalIndicators(symbol: string): Promise<TechnicalIndicators> {
    const response = await apiClient.get<BaseResponse<TechnicalIndicators>>(
      `/stocks/${symbol}/indicators`
    );
    return response.data.data;
  }

  // 종목별 뉴스 및 감성분석 (뉴스 아이템 반환으로 변경)
  static async getStockNews(
    symbol: string, 
    limit: number = 10
  ): Promise<NewsItem[]> {
    const response = await apiClient.get<BaseResponse<NewsItem[]>>(
      `/stocks/${symbol}/news`,
      { params: { limit } }
    );
    return response.data.data;
  }
}

/**
 * 투자 시그널 관련 API 서비스
 */
export class SignalService {
  // 투자 시그널 목록 조회 (페이지네이션 및 필터링)
  static async getSignals(
    page: number = 1,
    limit: number = 20,
    filters?: FilterOptions,
    sort?: SortOption
  ): Promise<PaginatedResponse<InvestmentSignalItem>> {
    const params = {
      page,
      limit,
      ...filters,
      ...(sort && { sortBy: sort.field, sortOrder: sort.direction })
    };

    const response = await apiClient.get<PaginatedResponse<InvestmentSignalItem>>(
      '/signals',
      { params }
    );
    return response.data;
  }

  // 특정 시그널 상세 조회
  static async getSignalDetail(signalId: string): Promise<InvestmentSignalItem> {
    const response = await apiClient.get<BaseResponse<InvestmentSignalItem>>(
      `/signals/${signalId}`
    );
    return response.data.data;
  }

  // 시그널 통계 조회
  static async getSignalStats(period?: string): Promise<any> {
    const response = await apiClient.get<BaseResponse<any>>(
      '/signals/stats',
      { params: { period } }
    );
    return response.data.data;
  }

  // 알림 설정 조회
  static async getAlertSettings(): Promise<any[]> {
    const response = await apiClient.get<BaseResponse<any[]>>('/signals/alerts');
    return response.data.data;
  }

  // 관심종목 토글
  static async toggleWatchlist(symbol: string, action: 'add' | 'remove'): Promise<void> {
    await apiClient.post<BaseResponse<void>>('/signals/watchlist', { symbol, action });
  }

  // 알림 생성
  static async createAlert(alert: any): Promise<any> {
    const response = await apiClient.post<BaseResponse<any>>('/signals/alerts', alert);
    return response.data.data;
  }
}

/**
 * 포트폴리오 관련 API 서비스
 */
export class PortfolioService {
  // 포트폴리오 목록 조회
  static async getPortfolios(): Promise<Portfolio[]> {
    const response = await apiClient.get<BaseResponse<Portfolio[]>>('/portfolio');
    return response.data.data;
  }

  // 포트폴리오 상세 조회
  static async getPortfolio(portfolioId: string): Promise<Portfolio> {
    const response = await apiClient.get<BaseResponse<Portfolio>>(`/portfolio/${portfolioId}`);
    return response.data.data;
  }

  // 포트폴리오 요약 정보 조회
  static async getPortfolioSummary(portfolioId?: string): Promise<PortfolioSummary> {
    const url = portfolioId ? `/portfolio/${portfolioId}/summary` : '/portfolio/summary';
    const response = await apiClient.get<BaseResponse<PortfolioSummary>>(url);
    return response.data.data;
  }

  // 포트폴리오 보유 종목 조회
  static async getHoldings(portfolioId?: string): Promise<Holding[]> {
    const url = portfolioId ? `/portfolio/${portfolioId}/holdings` : '/portfolio/holdings';
    const response = await apiClient.get<BaseResponse<Holding[]>>(url);
    return response.data.data;
  }

  // 포트폴리오 추천 조회
  static async getRecommendations(portfolioId?: string): Promise<Recommendation[]> {
    const url = portfolioId ? `/portfolio/${portfolioId}/recommendations` : '/portfolio/recommendations';
    const response = await apiClient.get<BaseResponse<Recommendation[]>>(url);
    return response.data.data;
  }

  // 포트폴리오 성과 이력 조회
  static async getPerformanceHistory(
    days: number = 30,
    portfolioId?: string
  ): Promise<PerformanceHistory> {
    const url = portfolioId ? `/portfolio/${portfolioId}/performance` : '/portfolio/performance';
    const response = await apiClient.get<BaseResponse<PerformanceHistory>>(
      url,
      { params: { days } }
    );
    return response.data.data;
  }

  // 종목 추가
  static async addHolding(
    symbol: string,
    quantity: number,
    averagePrice: number,
    portfolioId?: string
  ): Promise<Holding> {
    const url = portfolioId ? `/portfolio/${portfolioId}/holdings` : '/portfolio/holdings';
    const payload: AddHoldingRequest = {
      symbol,
      quantity,
      averagePrice,
    };
    const response = await apiClient.post<BaseResponse<Holding>>(url, payload);
    return response.data.data;
  }

  // 종목 수정
  static async updateHolding(
    id: string,
    quantity: number,
    averagePrice: number,
    portfolioId?: string
  ): Promise<Holding> {
    const url = portfolioId 
      ? `/portfolio/${portfolioId}/holdings/${id}` 
      : `/portfolio/holdings/${id}`;
    const payload: UpdateHoldingRequest = {
      quantity,
      averagePrice,
    };
    const response = await apiClient.put<BaseResponse<Holding>>(url, payload);
    return response.data.data;
  }

  // 종목 삭제
  static async deleteHolding(
    id: string,
    portfolioId?: string
  ): Promise<void> {
    const url = portfolioId 
      ? `/portfolio/${portfolioId}/holdings/${id}` 
      : `/portfolio/holdings/${id}`;
    await apiClient.delete(url);
  }

  // 포트폴리오 생성
  static async createPortfolio(name: string): Promise<Portfolio> {
    const response = await apiClient.post<BaseResponse<Portfolio>>('/portfolio', { name });
    return response.data.data;
  }

  // 종목 추가 (기존 호환성)
  static async addStockToPortfolio(
    portfolioId: string,
    symbol: string,
    quantity: number,
    price: number
  ): Promise<Portfolio> {
    const response = await apiClient.post<BaseResponse<Portfolio>>(
      `/portfolio/${portfolioId}/stocks`,
      { symbol, quantity, price }
    );
    return response.data.data;
  }

  // 종목 제거 (기존 호환성)
  static async removeStockFromPortfolio(
    portfolioId: string,
    symbol: string
  ): Promise<Portfolio> {
    const response = await apiClient.delete<BaseResponse<Portfolio>>(
      `/portfolio/${portfolioId}/stocks/${symbol}`
    );
    return response.data.data;
  }

  // 포트폴리오 성과 분석 (기존 호환성)
  static async getPortfolioPerformance(
    portfolioId: string,
    dateRange?: DateRange
  ): Promise<any> {
    const response = await apiClient.get<BaseResponse<any>>(
      `/portfolio/${portfolioId}/performance`,
      { params: dateRange }
    );
    return response.data.data;
  }
}

/**
 * 뉴스 관련 API 서비스
 */
export class NewsService {
  // 전체 뉴스 조회 (뉴스 필터 사용)
  static async getNews(
    filters: NewsFilters
  ): Promise<NewsItem[]> {
    const response = await apiClient.get<BaseResponse<NewsItem[]>>(
      '/news',
      { params: filters }
    );
    return response.data.data;
  }

  // 뉴스 감성분석 통계
  static async getNewsSentimentStats(dateRange?: DateRange): Promise<any> {
    const response = await apiClient.get<BaseResponse<any>>(
      '/news/sentiment/stats',
      { params: dateRange }
    );
    return response.data.data;
  }

  // 뉴스 요약 통계 조회
  static async getNewsSummary(filters: NewsFilters): Promise<NewsSummary> {
    const response = await apiClient.get<BaseResponse<NewsSummary>>(
      '/news/summary',
      { params: filters }
    );
    return response.data.data;
  }

  // 트렌딩 키워드 조회
  static async getTrendingKeywords(filters: NewsFilters): Promise<TrendingKeyword[]> {
    const response = await apiClient.get<BaseResponse<TrendingKeyword[]>>(
      '/news/trending-keywords',
      { params: filters }
    );
    return response.data.data;
  }

  // 시장 영향도 높은 뉴스 조회
  static async getImpactfulNews(filters: NewsFilters): Promise<NewsItem[]> {
    const response = await apiClient.get<BaseResponse<NewsItem[]>>(
      '/news/impactful',
      { params: filters }
    );
    return response.data.data;
  }
}

/**
 * 시장 관련 API 서비스
 */
export class MarketService {
  // 시장 상태 조회
  static async getMarketStatus(): Promise<MarketStatus> {
    const response = await apiClient.get<BaseResponse<MarketStatus>>('/market/status');
    return response.data.data;
  }

  // 시장 지수 조회 (KOSPI, KOSDAQ 등)
  static async getMarketIndices(): Promise<any> {
    const response = await apiClient.get<BaseResponse<any>>('/market/indices');
    return response.data.data;
  }

  // 시장 통계 조회
  static async getMarketStats(): Promise<any> {
    const response = await apiClient.get<BaseResponse<any>>('/market/stats');
    return response.data.data;
  }
}

/**
 * 대시보드 관련 API 서비스
 */
export class DashboardService {
  // 대시보드 요약 정보 조회
  static async getDashboardSummary(): Promise<any> {
    const response = await apiClient.get<BaseResponse<any>>('/dashboard/summary');
    return response.data.data;
  }

  // 인기 종목 조회
  static async getTrendingStocks(limit: number = 10): Promise<any> {
    const response = await apiClient.get<BaseResponse<any>>(
      '/dashboard/trending',
      { params: { limit } }
    );
    return response.data.data;
  }

  // 주요 뉴스 조회
  static async getTopNews(limit: number = 5): Promise<NewsItem[]> {
    const response = await apiClient.get<BaseResponse<NewsItem[]>>(
      '/dashboard/news',
      { params: { limit } }
    );
    return response.data.data;
  }
}

/**
 * 헬스체크 관련 API 서비스 - 시스템 상태 모니터링
 */
export class HealthService {
  // 기본 헬스체크 
  static async getHealthCheck(): Promise<any> {
    const response = await apiClient.get<BaseResponse<any>>('/health');
    return response.data;
  }

  // 서비스 상태 요약 (대시보드용)
  static async getServiceStatus(): Promise<any> {
    const response = await apiClient.get<BaseResponse<any>>('/status');
    return response.data;
  }

  // 종합 헬스체크 (상세)
  static async getComprehensiveHealth(): Promise<any> {
    const response = await apiClient.get<BaseResponse<any>>('/health/comprehensive');
    return response.data;
  }

  // 데이터베이스 상태
  static async getDatabaseHealth(): Promise<any> {
    const response = await apiClient.get<BaseResponse<any>>('/health/database');
    return response.data;
  }

  // OpenAI API 상태
  static async getOpenAIHealth(): Promise<any> {
    const response = await apiClient.get<BaseResponse<any>>('/health/openai');
    return response.data;
  }

  // Redis 상태
  static async getRedisHealth(): Promise<any> {
    const response = await apiClient.get<BaseResponse<any>>('/health/redis');
    return response.data;
  }

  // 외부 API 상태
  static async getExternalAPIsHealth(): Promise<any> {
    const response = await apiClient.get<BaseResponse<any>>('/health/external-apis');
    return response.data;
  }
}

/**
 * 사용량 추적 관련 API 서비스 - OpenAI 비용/사용량 모니터링
 */
export class UsageService {
  // 사용량 통계 조회
  static async getUsageStats(days: number = 7): Promise<any> {
    const response = await apiClient.get<BaseResponse<any>>(
      '/usage/stats',
      { params: { days } }
    );
    return response.data.data;
  }

  // 모델별 비용 분석
  static async getCostAnalysis(days: number = 7): Promise<any> {
    const response = await apiClient.get<BaseResponse<any>>(
      '/usage/costs',
      { params: { days } }
    );
    return response.data.data;
  }

  // 비용/에러율 알림 내역
  static async getAlerts(limit: number = 50): Promise<any> {
    const response = await apiClient.get<BaseResponse<any>>(
      '/usage/alerts',
      { params: { limit } }
    );
    return response.data.data;
  }

  // 일일 사용량 초기화 (테스트용)
  static async resetDailyUsage(date?: string): Promise<any> {
    const response = await apiClient.post<BaseResponse<any>>(
      '/usage/reset',
      { date }
    );
    return response.data;
  }
}

/**
 * 배치 작업 관련 API 서비스 - 배치 작업 모니터링 및 관리
 */
export class BatchService {
  // 등록된 배치 작업 목록
  static async getBatchJobs(): Promise<any> {
    const response = await apiClient.get<BaseResponse<any>>('/batch/jobs');
    return response.data.data;
  }

  // 개별 작업 실행
  static async executeJob(jobId: string, force: boolean = false): Promise<any> {
    const response = await apiClient.post<BaseResponse<any>>(
      `/batch/jobs/${jobId}/execute`,
      {},
      { params: { force } }
    );
    return response.data;
  }

  // 작업 상태 조회
  static async getJobStatus(jobId: string): Promise<any> {
    const response = await apiClient.get<BaseResponse<any>>(`/batch/jobs/${jobId}/status`);
    return response.data;
  }

  // 최근 N회 실행 이력 조회
  static async getRecentExecutions(limit: number = 50): Promise<any> {
    const response = await apiClient.get<BaseResponse<any>>(
      '/batch/executions/recent',
      { params: { limit } }
    );
    return response.data;
  }

  // 실행 통계 조회
  static async getExecutionStats(jobId?: string, days: number = 7): Promise<any> {
    const params: any = { days };
    if (jobId) params.job_id = jobId;
    
    const response = await apiClient.get<BaseResponse<any>>(
      '/batch/executions/stats',
      { params }
    );
    return response.data;
  }

  // 작업 잠금 상태 조회
  static async getLockStatus(jobId: string): Promise<any> {
    const response = await apiClient.get<BaseResponse<any>>(`/batch/jobs/${jobId}/lock/status`);
    return response.data;
  }

  // 강제 잠금 해제
  static async forceReleaseLock(jobId: string, reason: string): Promise<any> {
    const response = await apiClient.post<BaseResponse<any>>(
      `/batch/jobs/${jobId}/lock/release`,
      { reason }
    );
    return response.data;
  }

  // 만료된 잠금 파일 조회
  static async getExpiredLocks(maxAgeHours: number = 24): Promise<any> {
    const response = await apiClient.get<BaseResponse<any>>(
      '/batch/locks/expired',
      { params: { max_age_hours: maxAgeHours } }
    );
    return response.data;
  }

  // 만료된 잠금 파일 정리
  static async cleanupExpiredLocks(force: boolean = false, maxAgeHours: number = 24): Promise<any> {
    const response = await apiClient.post<BaseResponse<any>>(
      '/batch/locks/cleanup',
      {},
      { params: { force, max_age_hours: maxAgeHours } }
    );
    return response.data;
  }

  // 배치 시스템 상태
  static async getBatchSystemHealth(): Promise<any> {
    const response = await apiClient.get<BaseResponse<any>>('/batch/health');
    return response.data;
  }
}

// API 서비스들을 하나의 객체로 내보내기
export const API = {
  Stock: StockService,
  Signal: SignalService,
  Portfolio: PortfolioService,
  News: NewsService,
  Market: MarketService,
  Dashboard: DashboardService,
  Health: HealthService,
  Usage: UsageService,
  Batch: BatchService,
};

export default API;