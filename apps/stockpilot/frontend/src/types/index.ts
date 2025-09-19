/**
 * StockPilot AI 전체 타입 정의
 * 한국 주식시장에 특화된 데이터 타입들
 */

// 기본 공통 타입
export interface BaseResponse<T = any> {
  success: boolean;
  data: T;
  message?: string;
  error?: string;
}

// 투자 시그널 타입
export enum InvestmentSignal {
  STRONG_BUY = 'STRONG_BUY',    // 강력 매수
  BUY = 'BUY',                  // 매수
  HOLD = 'HOLD',                // 관망/보유
  SELL = 'SELL',                // 매도
  STRONG_SELL = 'STRONG_SELL'   // 강력 매도
}

// 신뢰도 레벨
export enum ConfidenceLevel {
  VERY_LOW = 'VERY_LOW',        // 매우 낮음
  LOW = 'LOW',                  // 낮음
  MEDIUM = 'MEDIUM',            // 보통
  HIGH = 'HIGH',                // 높음
  VERY_HIGH = 'VERY_HIGH'       // 매우 높음
}

// 시장 구분
export enum Market {
  KOSPI = 'KOSPI',              // 코스피
  KOSDAQ = 'KOSDAQ',            // 코스닥
  KONEX = 'KONEX'               // 코넥스
}

// 주식 기본 정보
export interface StockInfo {
  symbol: string;               // 종목 코드 (6자리)
  name: string;                 // 종목명 (한글)
  englishName?: string;         // 영문명
  market: Market;               // 상장 시장
  sector: string;               // 섹터
  industry: string;             // 업종
  marketCap: number;            // 시가총액
  listedShares: number;         // 상장주식수
  website?: string;             // 홈페이지
}

// 주가 정보
export interface StockPrice {
  symbol: string;               // 종목 코드
  currentPrice: number;         // 현재가
  change: number;               // 전일 대비
  changeRate: number;           // 등락률 (%)
  volume: number;               // 거래량
  tradingValue: number;         // 거래대금
  openPrice: number;            // 시가
  highPrice: number;            // 고가
  lowPrice: number;             // 저가
  previousClose: number;        // 전일 종가
  updatedAt: string;            // 업데이트 시간
}

// AI 분석 결과
export interface AIAnalysis {
  symbol: string;               // 종목 코드
  signal: InvestmentSignal;     // 투자 시그널
  confidence: number;           // 신뢰도 (0-100)
  confidenceLevel: ConfidenceLevel; // 신뢰도 레벨
  targetPrice: number;          // 목표가
  currentPrice: number;         // 현재가
  expectedReturn: number;       // 기대수익률 (%)
  riskLevel: number;            // 위험도 (1-10)
  timeHorizon: string;          // 투자기간 ('단기', '중기', '장기')
  analysisType: string[];       // 분석 방법 ('기술적분석', '기본분석', '감성분석' 등)
  keyFactors: string[];         // 주요 요인들
  reasoning: string;            // 분석 근거
  generatedAt: string;          // 분석 생성 시간
  validUntil: string;           // 분석 유효 시간
}

// 뉴스 감정 타입
export enum SentimentType {
  POSITIVE = 'POSITIVE',
  NEGATIVE = 'NEGATIVE', 
  NEUTRAL = 'NEUTRAL'
}

// 뉴스 감성 분석
export interface NewsSentiment {
  id: string;                   // 뉴스 ID
  title: string;                // 제목
  summary: string;              // 요약
  url: string;                  // 원문 URL
  source: string;               // 뉴스 소스
  publishedAt: string;          // 발행 시간
  sentiment: number;            // 감정 점수 (-1.0 ~ 1.0)
  sentimentLabel: SentimentType; // 감정 라벨
  impact: number;               // 주가 영향도 (0-100)
  keywords: string[];           // 핵심 키워드
  mentionedStocks: string[];    // 언급된 종목들
}

// 포트폴리오 종목
export interface PortfolioStock {
  symbol: string;               // 종목 코드
  name: string;                 // 종목명
  quantity: number;             // 보유 수량
  averagePrice: number;         // 평균 매수가
  currentPrice: number;         // 현재가
  totalCost: number;            // 총 매수금액
  currentValue: number;         // 현재 평가금액
  unrealizedPL: number;         // 평가손익
  unrealizedPLRate: number;     // 평가손익률 (%)
  weight: number;               // 포트폴리오 비중 (%)
  addedAt: string;              // 편입 일시
}

// 포트폴리오 전체 정보
export interface Portfolio {
  id: string;                   // 포트폴리오 ID
  name: string;                 // 포트폴리오 명
  totalInvestment: number;      // 총 투자금액
  currentValue: number;         // 현재 평가금액
  totalPL: number;              // 총 평가손익
  totalPLRate: number;          // 총 평가손익률 (%)
  cashBalance: number;          // 현금 잔고
  stocks: PortfolioStock[];     // 보유 종목들
  lastUpdated: string;          // 최종 업데이트 시간
  createdAt: string;            // 생성 시간
}

// 투자 시그널 목록 아이템
export interface InvestmentSignalItem {
  id: string;                   // 시그널 ID
  symbol: string;               // 종목 코드
  name: string;                 // 종목명
  signal: InvestmentSignal;     // 시그널
  confidence: number;           // 신뢰도
  currentPrice: number;         // 현재가
  targetPrice: number;          // 목표가
  expectedReturn: number;       // 기대수익률
  riskLevel: number;            // 위험도
  market: Market;               // 시장
  sector: string;               // 섹터
  reasoning: string;            // 간략한 근거
  generatedAt: string;          // 생성 시간
  isActive: boolean;            // 활성 상태
}

// 차트 데이터 포인트
export interface ChartDataPoint {
  timestamp: string | number;   // 시간
  open: number;                 // 시가
  high: number;                 // 고가
  low: number;                  // 저가
  close: number;                // 종가
  volume: number;               // 거래량
}

// 기술적 지표
export interface TechnicalIndicators {
  symbol: string;               // 종목 코드
  rsi: number;                  // RSI
  macd: {                       // MACD
    macd: number;
    signal: number;
    histogram: number;
  };
  movingAverages: {             // 이동평균선들
    ma5: number;
    ma20: number;
    ma60: number;
    ma120: number;
  };
  bollinger: {                  // 볼린저 밴드
    upper: number;
    middle: number;
    lower: number;
  };
  stochastic: {                 // 스토캐스틱
    k: number;
    d: number;
  };
  volume: {                     // 거래량 지표
    average: number;
    ratio: number;
  };
  calculatedAt: string;         // 계산 시간
}

// 시장 상태
export interface MarketStatus {
  isOpen: boolean;              // 장 개장 여부
  currentTime: string;          // 현재 시간
  openTime: string;             // 장 시작 시간
  closeTime: string;            // 장 마감 시간
  timeToOpen?: number;          // 장 시작까지 남은 시간 (분)
  timeToClose?: number;         // 장 마감까지 남은 시간 (분)
  session: 'PRE_MARKET' | 'REGULAR' | 'POST_MARKET' | 'CLOSED'; // 장 세션
  nextTradingDay: string;       // 다음 거래일
  holiday?: string;             // 휴장 사유 (휴장시)
}

// API 에러
export interface APIError {
  code: string;                 // 에러 코드
  message: string;              // 에러 메시지
  details?: any;                // 에러 세부사항
  timestamp: string;            // 발생 시간
}

// 검색 결과
export interface StockSearchResult {
  symbol: string;               // 종목 코드
  name: string;                 // 종목명
  market: Market;               // 시장
  sector: string;               // 섹터
  currentPrice?: number;        // 현재가
  changeRate?: number;          // 등락률
  matchScore: number;           // 매치 점수 (검색 관련도)
}

// WebSocket 메시지
export interface WebSocketMessage {
  type: 'PRICE_UPDATE' | 'ANALYSIS_UPDATE' | 'MARKET_STATUS' | 'NEWS_UPDATE' | 'SYSTEM_STATUS' | 'USAGE_STATS' | 'BATCH_STATUS';
  timestamp: string;
  data: any;
}

// 실시간 주가 업데이트
export interface RealTimePriceUpdate {
  symbol: string;
  currentPrice: number;
  change: number;
  changeRate: number;
  volume: number;
  timestamp: string;
}

// 차트 설정
export interface ChartConfig {
  interval: '1m' | '5m' | '15m' | '1h' | '1d' | '1w' | '1M';
  period: number;               // 조회 기간
  indicators: string[];         // 표시할 지표들
  theme: 'light' | 'dark';      // 차트 테마
}

// 사용자 설정
export interface UserSettings {
  theme: 'light' | 'dark' | 'auto';
  language: 'ko' | 'en';
  defaultMarket: Market;
  refreshInterval: number;      // 새로고침 간격 (초)
  notifications: {
    priceAlerts: boolean;
    signalAlerts: boolean;
    newsAlerts: boolean;
    emailNotifications: boolean;
  };
  displaySettings: {
    showChangeInPercent: boolean;
    showVolume: boolean;
    compactView: boolean;
  };
}

// 페이지네이션
export interface Pagination {
  page: number;                 // 현재 페이지
  limit: number;                // 페이지당 항목 수
  total: number;                // 전체 항목 수
  totalPages: number;           // 전체 페이지 수
  hasNext: boolean;             // 다음 페이지 존재 여부
  hasPrev: boolean;             // 이전 페이지 존재 여부
}

// API 응답 래퍼
export interface PaginatedResponse<T> extends BaseResponse<T[]> {
  pagination: Pagination;
}

// 날짜 범위
export interface DateRange {
  startDate: string;            // 시작 날짜
  endDate: string;              // 종료 날짜
}

// 정렬 옵션
export interface SortOption {
  field: string;                // 정렬 필드
  direction: 'asc' | 'desc';    // 정렬 방향
}

// 필터 옵션
export interface FilterOptions {
  markets?: Market[];           // 시장 필터
  sectors?: string[];           // 섹터 필터
  signals?: InvestmentSignal[]; // 시그널 필터
  confidenceMin?: number;       // 최소 신뢰도
  priceRange?: {                // 가격 범위
    min: number;
    max: number;
  };
  marketCapRange?: {            // 시가총액 범위
    min: number;
    max: number;
  };
}

// 시스템 헬스체크 관련 타입들
export enum ServiceStatus {
  ONLINE = 'online',
  OFFLINE = 'offline',
  DEGRADED = 'degraded',
  UNKNOWN = 'unknown'
}

export enum OverallStatus {
  OPERATIONAL = 'operational',
  DEGRADED = 'degraded', 
  CRITICAL = 'critical',
  UNKNOWN = 'unknown'
}

export interface ServiceHealthDetail {
  status: ServiceStatus;
  last_check: string;
  response_time_ms?: number;
  details?: any;
  error_message?: string;
}

export interface ServiceStatusResponse {
  overall_status: OverallStatus;
  services: {
    [serviceName: string]: ServiceStatus;
  };
  last_updated: string;
  health_check_available: boolean;
  detailed_check_url?: string;
  system_info?: any;
}

export interface ComprehensiveHealthResponse {
  overall_status: OverallStatus;
  last_updated: string;
  services: {
    [serviceName: string]: ServiceHealthDetail;
  };
  system_metrics?: {
    memory_usage_percent: number;
    cpu_usage_percent: number;
    disk_usage_percent: number;
    uptime_seconds: number;
  };
}

// 사용량 추적 관련 타입들
export interface UsageRecord {
  timestamp: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost: number;
  task_type: string;
  endpoint: string;
  status_code: number;
  error_code?: string;
  error_message?: string;
  response_time_ms?: number;
  user_id?: string;
  request_id?: string;
}

export interface DailyUsage {
  date: string;
  total_requests: number;
  total_tokens: number;
  total_cost: number;
  model_usage: { [model: string]: number };
  cost_by_model: { [model: string]: number };
  endpoint_usage: { [endpoint: string]: number };
  error_breakdown: { [errorCode: string]: number };
  success_requests: number;
  failed_requests: number;
  avg_response_time_ms: number;
  success_rate_percent: number;
  cost_usage_percent: number;
}

export interface UsageStatsResponse {
  daily_usage: { [date: string]: DailyUsage };
  monthly_usage: { [month: string]: number };
  current_limits: {
    daily_limit: number;
    monthly_limit: number;
    alert_threshold: number;
  };
  summary: {
    total_days_tracked: number;
    total_cost_to_date: number;
    total_requests_to_date: number;
    avg_daily_cost: number;
    avg_success_rate: number;
  };
}

// 배치 작업 관련 타입들
export enum JobStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  SUCCESS = 'success',
  FAILED = 'failed',
  SKIPPED = 'skipped',
  CANCELLED = 'cancelled'
}

export interface JobExecution {
  job_id: string;
  job_name: string;
  status: JobStatus;
  start_time?: string;
  end_time?: string;
  duration?: number;
  error_message?: string;
  retry_count: number;
  result?: any;
  // 확장된 메트릭스
  execution_id: string;
  items_processed?: number;
  throughput_per_second?: number;
  memory_peak_mb?: number;
  cpu_usage_percent?: number;
  warnings: string[];
  progress_percentage?: number;
}

export interface BatchJob {
  job_id: string;
  name: string;
  description: string;
  priority: string;
  enabled: boolean;
  max_retries: number;
  timeout: number;
  dependencies: string[];
  last_status: JobStatus;
  last_run?: string;
}

export interface ExecutionStatsResponse {
  total: number;
  success: number;
  failed: number;
  success_rate: number;
  avg_duration_seconds: number;
  avg_throughput_per_second: number;
  avg_memory_peak_mb: number;
  avg_cpu_usage_percent: number;
  stats: {
    by_status: { [status: string]: number };
    by_job: any;
  };
}

export interface LockStatus {
  job_id: string;
  lock_exists: boolean;
  lock_age_hours?: number;
  is_expired: boolean;
}

// WebSocket 실시간 업데이트 타입 확장
export interface SystemStatusUpdate {
  type: 'SYSTEM_STATUS';
  timestamp: string;
  data: ServiceStatusResponse;
}

export interface UsageStatsUpdate {
  type: 'USAGE_STATS';
  timestamp: string;
  data: {
    daily_cost: number;
    daily_requests: number;
    cost_usage_percent: number;
    alerts?: any[];
  };
}

export interface BatchStatusUpdate {
  type: 'BATCH_STATUS';
  timestamp: string;
  data: {
    running_jobs: string[];
    recent_failures: number;
    execution_update?: JobExecution;
  };
}

export enum NewsCategory {
  MARKET = 'MARKET',
  COMPANY = 'COMPANY',
  ECONOMY = 'ECONOMY',
  POLITICS = 'POLITICS',
  TECHNOLOGY = 'TECHNOLOGY'
}

export interface NewsArticle {
  id: string;
  title: string;
  content?: string;
  summary: string;
  url: string;
  source: string;
  publishedAt: string;
  sentiment: SentimentType;
  impactScore?: number;
  relatedStocks?: { symbol: string; name: string }[];
  keywords?: string[];
}

// 시장 타입 별칭 (Market와 동일하지만 다른 용도)
export type MarketType = Market;

// 시그널 강도
export enum SignalStrength {
  WEAK = 'WEAK',
  MODERATE = 'MODERATE',
  STRONG = 'STRONG'
}

// AI 시그널
export interface AISignal {
  id: string;
  symbol: string;
  name: string;
  signal: InvestmentSignal;
  strength: SignalStrength;
  confidence: number;
  currentPrice: number;
  targetPrice: number;
  expectedReturn: number;
  reasoning: string;
  generatedAt: string;
  expiresAt: string;
}

// 시그널 알림
export interface SignalAlert {
  id: string;
  symbol: string;
  name: string;
  alertType: 'PRICE' | 'SIGNAL' | 'VOLUME';
  condition: string;
  threshold: number;
  isActive: boolean;
  createdAt: string;
}

// 포트폴리오 보유 종목
export interface PortfolioHolding {
  id: string;
  symbol: string;
  stock: {
    name: string;
    currentPrice: number;
    change: number;
    changeRate: number;
  };
  quantity: number;
  averagePrice: number;
  currentValue: number;
  totalCost: number;
  unrealizedPL: number;
  unrealizedPLRate: number;
  addedAt: string;
}

// 포트폴리오 요약
export interface PortfolioSummary {
  totalValue: number;
  totalCost: number;
  totalPL: number;
  totalPLRate: number;
  todayPL: number;
  todayPLRate: number;
  cashBalance: number;
  assetAllocation: {
    stocks: number;
    cash: number;
  };
}

// 포트폴리오 추천
export interface PortfolioRecommendation {
  type: 'BUY' | 'SELL' | 'REBALANCE';
  symbol: string;
  name: string;
  reasoning: string;
  expectedImpact: number;
  confidence: number;
}