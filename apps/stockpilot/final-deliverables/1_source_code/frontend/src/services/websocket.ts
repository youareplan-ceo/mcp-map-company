/**
 * StockPilot AI WebSocket 서비스
 * 실시간 데이터 업데이트를 위한 WebSocket 연결 관리
 */

import { io, Socket } from 'socket.io-client';
import { ENV } from '../env';
import {
  WebSocketMessage,
  RealTimePriceUpdate,
  MarketStatus,
  AIAnalysis,
  NewsSentiment,
  SystemStatusUpdate,
  UsageStatsUpdate,
  BatchStatusUpdate
} from '../types';

/**
 * WebSocket 이벤트 타입 정의
 */
export interface WebSocketEvents {
  // 주가 관련
  'price_update': (data: RealTimePriceUpdate) => void;
  'price_subscribe': (symbols: string[]) => void;
  'price_unsubscribe': (symbols: string[]) => void;

  // AI 분석 관련
  'analysis_update': (data: AIAnalysis) => void;
  'analysis_subscribe': (symbol: string) => void;

  // 시장 상태 관련
  'market_status': (data: MarketStatus) => void;

  // 뉴스 관련
  'news_update': (data: NewsSentiment) => void;

  // 시스템 모니터링 관련
  'system_status_update': (data: SystemStatusUpdate) => void;
  'usage_stats_update': (data: UsageStatsUpdate) => void;
  'batch_status_update': (data: BatchStatusUpdate) => void;

  // 연결 상태 관련
  'connect': () => void;
  'disconnect': () => void;
  'reconnect': () => void;
  'error': (error: any) => void;
}

/**
 * WebSocket 서비스 클래스
 */
export class WebSocketService {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // 1초
  private subscribedSymbols = new Set<string>();
  private eventListeners = new Map<string, Set<Function>>();

  constructor() {
    this.connect();
  }

  /**
   * WebSocket 서버 연결
   */
  private connect(): void {
    this.socket = io(ENV.WS_URL, {
      transports: ['websocket', 'polling'],
      timeout: 20000,
      autoConnect: true,
      reconnection: true,
      reconnectionAttempts: this.maxReconnectAttempts,
      reconnectionDelay: this.reconnectDelay,
    });

    this.setupEventListeners();
  }

  /**
   * 기본 이벤트 리스너 설정
   */
  private setupEventListeners(): void {
    if (!this.socket) return;

    // 연결 성공
    this.socket.on('connect', () => {
      console.log('✅ WebSocket 연결 성공');
      this.reconnectAttempts = 0;
      
      // 이전에 구독했던 심볼들 다시 구독
      if (this.subscribedSymbols.size > 0) {
        this.subscribePrices(Array.from(this.subscribedSymbols));
      }

      if (process.env.NODE_ENV === 'development') {
        console.log('✅ 실시간 데이터 연결됨');
      }
    });

    // 연결 끊김
    this.socket.on('disconnect', (reason) => {
      console.warn('🔌 WebSocket 연결 끊김:', reason);
      
      if (reason === 'io server disconnect') {
        // 서버에서 연결을 끊은 경우
        console.warn('🔌 서버 연결이 끊어졌습니다.');
      }
    });

    // 재연결 시도
    this.socket.on('reconnect', (attemptNumber) => {
      console.log(`🔄 WebSocket 재연결 성공 (시도 ${attemptNumber}회)`);
      console.log('✅ 실시간 데이터 연결 복구됨');
    });

    // 재연결 실패
    this.socket.on('reconnect_failed', () => {
      console.error('❌ WebSocket 재연결 실패');
      console.error('❌ 실시간 데이터 연결을 복구할 수 없습니다.');
    });

    // 연결 오류
    this.socket.on('connect_error', (error) => {
      console.error('❌ WebSocket 연결 오류:', error);
      this.reconnectAttempts++;
      
      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        console.error('❌ 실시간 데이터 서버에 연결할 수 없습니다.');
      }
    });

    // 실시간 주가 업데이트
    this.socket.on('price_update', (data: RealTimePriceUpdate) => {
      this.emitToListeners('price_update', data);
    });

    // AI 분석 업데이트
    this.socket.on('analysis_update', (data: AIAnalysis) => {
      this.emitToListeners('analysis_update', data);
    });

    // 시장 상태 업데이트
    this.socket.on('market_status', (data: MarketStatus) => {
      this.emitToListeners('market_status', data);
    });

    // 뉴스 업데이트
    this.socket.on('news_update', (data: NewsSentiment) => {
      this.emitToListeners('news_update', data);
    });

    // 시스템 상태 업데이트
    this.socket.on('system_status_update', (data: SystemStatusUpdate) => {
      this.emitToListeners('system_status_update', data);
    });

    // 사용량 통계 업데이트
    this.socket.on('usage_stats_update', (data: UsageStatsUpdate) => {
      this.emitToListeners('usage_stats_update', data);
    });

    // 배치 상태 업데이트
    this.socket.on('batch_status_update', (data: BatchStatusUpdate) => {
      this.emitToListeners('batch_status_update', data);
    });

    // 일반적인 메시지 처리
    this.socket.on('message', (message: WebSocketMessage) => {
      console.log('📨 WebSocket 메시지:', message);
      this.handleMessage(message);
    });
  }

  /**
   * WebSocket 메시지 처리
   */
  private handleMessage(message: WebSocketMessage): void {
    switch (message.type) {
      case 'PRICE_UPDATE':
        this.emitToListeners('price_update', message.data);
        break;
      case 'ANALYSIS_UPDATE':
        this.emitToListeners('analysis_update', message.data);
        break;
      case 'MARKET_STATUS':
        this.emitToListeners('market_status', message.data);
        break;
      case 'NEWS_UPDATE':
        this.emitToListeners('news_update', message.data);
        break;
      case 'SYSTEM_STATUS':
        this.emitToListeners('system_status_update', message);
        break;
      case 'USAGE_STATS':
        this.emitToListeners('usage_stats_update', message);
        break;
      case 'BATCH_STATUS':
        this.emitToListeners('batch_status_update', message);
        break;
      default:
        console.warn('알 수 없는 WebSocket 메시지 타입:', message.type);
    }
  }

  /**
   * 이벤트 리스너들에게 데이터 전파
   */
  private emitToListeners(event: string, data: any): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.forEach(listener => {
        try {
          listener(data);
        } catch (error) {
          console.error(`이벤트 리스너 실행 오류 (${event}):`, error);
        }
      });
    }
  }

  /**
   * 이벤트 리스너 등록
   */
  public on<K extends keyof WebSocketEvents>(
    event: K,
    listener: WebSocketEvents[K]
  ): void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, new Set());
    }
    
    this.eventListeners.get(event)!.add(listener);
  }

  /**
   * 이벤트 리스너 해제
   */
  public off<K extends keyof WebSocketEvents>(
    event: K,
    listener: WebSocketEvents[K]
  ): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.delete(listener);
      if (listeners.size === 0) {
        this.eventListeners.delete(event);
      }
    }
  }

  /**
   * 주가 실시간 구독
   */
  public subscribePrices(symbols: string[]): void {
    if (!this.socket?.connected) {
      console.warn('WebSocket이 연결되지 않음. 구독 대기 중...');
      symbols.forEach(symbol => this.subscribedSymbols.add(symbol));
      return;
    }

    console.log('📊 주가 구독:', symbols);
    this.socket.emit('price_subscribe', symbols);
    symbols.forEach(symbol => this.subscribedSymbols.add(symbol));
  }

  /**
   * 주가 실시간 구독 해제
   */
  public unsubscribePrices(symbols: string[]): void {
    if (!this.socket?.connected) {
      console.warn('WebSocket이 연결되지 않음');
      return;
    }

    console.log('📊 주가 구독 해제:', symbols);
    this.socket.emit('price_unsubscribe', symbols);
    symbols.forEach(symbol => this.subscribedSymbols.delete(symbol));
  }

  /**
   * AI 분석 구독
   */
  public subscribeAnalysis(symbol: string): void {
    if (!this.socket?.connected) {
      console.warn('WebSocket이 연결되지 않음');
      return;
    }

    console.log('🤖 AI 분석 구독:', symbol);
    this.socket.emit('analysis_subscribe', symbol);
  }

  /**
   * 연결 상태 확인
   */
  public isConnected(): boolean {
    return this.socket?.connected || false;
  }

  /**
   * 구독 중인 심볼 목록 반환
   */
  public getSubscribedSymbols(): string[] {
    return Array.from(this.subscribedSymbols);
  }

  /**
   * WebSocket 연결 해제
   */
  public disconnect(): void {
    if (this.socket) {
      console.log('🔌 WebSocket 연결 해제');
      this.socket.disconnect();
      this.socket = null;
      this.subscribedSymbols.clear();
      this.eventListeners.clear();
    }
  }

  /**
   * 메시지 직접 전송
   */
  public emit(event: string, data: any): void {
    if (this.socket?.connected) {
      this.socket.emit(event, data);
    } else {
      console.warn('WebSocket이 연결되지 않아 메시지를 전송할 수 없습니다:', event);
    }
  }

  /**
   * 연결 강제 재시작
   */
  public reconnect(): void {
    console.log('🔄 WebSocket 연결 재시작');
    this.disconnect();
    setTimeout(() => {
      this.connect();
    }, 1000);
  }
}

// 싱글톤 인스턴스
export const webSocketService = new WebSocketService();

// React Hook으로 사용할 수 있는 함수들
export const useWebSocket = () => {
  return {
    service: webSocketService,
    isConnected: webSocketService.isConnected(),
    subscribePrices: webSocketService.subscribePrices.bind(webSocketService),
    unsubscribePrices: webSocketService.unsubscribePrices.bind(webSocketService),
    subscribeAnalysis: webSocketService.subscribeAnalysis.bind(webSocketService),
    on: webSocketService.on.bind(webSocketService),
    off: webSocketService.off.bind(webSocketService),
    reconnect: webSocketService.reconnect.bind(webSocketService),
  };
};

export default webSocketService;