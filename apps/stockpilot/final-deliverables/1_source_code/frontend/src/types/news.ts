/**
 * 뉴스 관련 타입 정의
 * StockPilot AI 뉴스 분석 시스템의 타입 정의
 */

// 뉴스 감정 분석 결과 타입
export type NewsSentiment = 'positive' | 'negative' | 'neutral';

// 뉴스 감정 분석 상수 (실제 값 사용)
export const NEWS_SENTIMENT = {
  POSITIVE: 'positive' as const,
  NEGATIVE: 'negative' as const,
  NEUTRAL: 'neutral' as const,
} as const;

// 뉴스 카테고리 타입
export type NewsCategory = 'market' | 'economy' | 'corporate' | 'policy' | 'international';

// 뉴스 카테고리 상수
export const NEWS_CATEGORY = {
  MARKET: 'market' as const,
  ECONOMY: 'economy' as const,
  CORPORATE: 'corporate' as const,
  POLICY: 'policy' as const,
  INTERNATIONAL: 'international' as const,
} as const;

// 뉴스 필터 인터페이스
export interface NewsFilters {
  category?: NewsCategory;
  sentiment?: NewsSentiment;
  period: '1h' | '6h' | '1d' | '3d' | '1w';
  source?: string;
}

// 관련 주식 정보
export interface RelatedStock {
  symbol: string;
  name: string;
  impact?: number; // 해당 뉴스가 주식에 미치는 영향도
}

// 뉴스 아이템 인터페이스
export interface NewsItem {
  id: string;
  title: string;
  summary: string;
  content?: string;
  url: string;
  imageUrl?: string;
  source: string;
  author?: string;
  publishedAt: string;
  sentiment: NewsSentiment;
  sentimentScore: number; // -1.0 ~ 1.0
  confidence: number; // 0.0 ~ 1.0
  category: NewsCategory;
  tags?: string[];
  impactScore?: number; // 시장 영향도 점수
  relatedStocks?: RelatedStock[];
  viewCount?: number;
  likes?: number;
}

// 뉴스 요약 통계
export interface NewsSummary {
  totalNews: number;
  positiveNews: number;
  negativeNews: number;
  neutralNews: number;
  averageSentiment: number;
  topCategories: Array<{
    category: NewsCategory;
    count: number;
  }>;
  period: string;
  lastUpdated: string;
}

// 트렌딩 키워드
export interface TrendingKeyword {
  word: string;
  count: number;
  sentiment: NewsSentiment;
  trend: 'up' | 'down' | 'stable';
  relatedNews?: NewsItem[];
}

// 뉴스 검색 결과
export interface NewsSearchResult {
  items: NewsItem[];
  totalCount: number;
  page: number;
  limit: number;
  hasMore: boolean;
}

// 뉴스 API 응답 타입들
export interface NewsResponse {
  data: NewsItem[];
  total: number;
  page: number;
  limit: number;
}

export interface NewsSummaryResponse {
  data: NewsSummary;
}

export interface TrendingKeywordsResponse {
  data: TrendingKeyword[];
}

// 기존 types/index.ts와의 호환성을 위한 별칭
export type NewsArticle = NewsItem;

// 기본값 제공
export const defaultNewsFilters: NewsFilters = {
  period: '1d',
};

export const defaultNewsSummary: NewsSummary = {
  totalNews: 0,
  positiveNews: 0,
  negativeNews: 0,
  neutralNews: 0,
  averageSentiment: 0,
  topCategories: [],
  period: '1d',
  lastUpdated: new Date().toISOString(),
};