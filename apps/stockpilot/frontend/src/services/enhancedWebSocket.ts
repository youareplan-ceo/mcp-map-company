/**
 * 강화된 WebSocket 서비스
 * 재연결 백오프, ping/pong, 큐 관리, 이벤트 처리
 */

import { EventEmitter } from 'events';

// WebSocket 이벤트 타입 정의
export interface WebSocketEvents {
  // 시스템 이벤트
  'system:status': (data: SystemStatusUpdate) => void;
  'system:usage': (data: UsageUpdate) => void;
  
  // 시장 데이터 이벤트  
  'price:update': (data: PriceUpdate) => void;
  'signal:update': (data: SignalUpdate) => void;
  'news:update': (data: NewsUpdate) => void;
  'market:status': (data: MarketStatusUpdate) => void;
  
  // 연결 이벤트
  'connected': () => void;
  'disconnected': (reason: string) => void;
  'reconnecting': (attempt: number) => void;
  'error': (error: Error) => void;
}

// 데이터 타입 정의
export interface SystemStatusUpdate {
  overall_status: string;
  services: Record<string, string>;
  timestamp: string;
}

export interface UsageUpdate {
  daily_cost: number;
  requests_count: number;
  usage_percent: number;
  timestamp: string;
}

export interface PriceUpdate {
  symbol: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  timestamp: string;
}

export interface SignalUpdate {
  id: string;
  symbol: string;
  signal: 'BUY' | 'SELL' | 'HOLD';
  strength: 'HIGH' | 'MEDIUM' | 'LOW';
  confidence: number;
  timestamp: string;
}

export interface NewsUpdate {
  id: string;
  title: string;
  content: string;
  sentiment: 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL';
  impact_score: number;
  timestamp: string;
}

export interface MarketStatusUpdate {
  market: string;
  status: 'OPEN' | 'CLOSED' | 'PRE_MARKET' | 'AFTER_HOURS';
  next_open: string;
  next_close: string;
  timestamp: string;
}

// 재연결 설정
interface ReconnectConfig {
  maxAttempts: number;
  initialDelay: number;
  maxDelay: number;
  backoffFactor: number;
}

// 큐 설정
interface QueueConfig {
  maxSize: number;
  dropPolicy: 'oldest' | 'newest' | 'reject';
}

// WebSocket 설정
interface WebSocketConfig {
  url: string;
  protocols?: string[];
  reconnect: ReconnectConfig;
  queue: QueueConfig;
  pingInterval: number;
  pongTimeout: number;
}

export class EnhancedWebSocketService {
  private static instance: EnhancedWebSocketService;
  private ws: WebSocket | null = null;
  private eventEmitter = new EventEmitter();
  private config: WebSocketConfig;
  
  // 재연결 관련
  private reconnectAttempts = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private isManualClose = false;
  
  // Ping/Pong 관련
  private pingTimer: NodeJS.Timeout | null = null;
  private pongTimer: NodeJS.Timeout | null = null;
  private lastPongTime = 0;
  
  // 메시지 큐
  private messageQueue: string[] = [];
  private isConnected = false;

  private constructor() {
    this.config = {
      url: 'ws://localhost:8000/ws',
      protocols: ['stockpilot-v1'],
      reconnect: {
        maxAttempts: 10,
        initialDelay: 1000,
        maxDelay: 30000,
        backoffFactor: 1.5,
      },
      queue: {
        maxSize: 100,
        dropPolicy: 'oldest',
      },
      pingInterval: 30000, // 30초
      pongTimeout: 5000,   // 5초
    };
  }

  public static getInstance(): EnhancedWebSocketService {
    if (!EnhancedWebSocketService.instance) {
      EnhancedWebSocketService.instance = new EnhancedWebSocketService();
    }
    return EnhancedWebSocketService.instance;
  }

  /**
   * WebSocket 연결 시작
   */
  public connect(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('🔌 WebSocket이 이미 연결되어 있습니다.');
      return;
    }

    this.isManualClose = false;
    this.createConnection();
  }

  /**
   * WebSocket 연결 해제
   */
  public disconnect(): void {
    this.isManualClose = true;
    this.clearTimers();
    
    if (this.ws) {
      this.ws.close(1000, '수동 연결 해제');
      this.ws = null;
    }
    
    this.isConnected = false;
    this.reconnectAttempts = 0;
  }

  /**
   * 실제 WebSocket 연결 생성
   */
  private createConnection(): void {
    try {
      console.log(`🔌 WebSocket 연결 시도: ${this.config.url}`);
      
      this.ws = new WebSocket(this.config.url, this.config.protocols);
      
      this.ws.onopen = this.handleOpen.bind(this);
      this.ws.onmessage = this.handleMessage.bind(this);
      this.ws.onclose = this.handleClose.bind(this);
      this.ws.onerror = this.handleError.bind(this);
      
    } catch (error) {
      console.error('❌ WebSocket 연결 생성 실패:', error);
      this.scheduleReconnect();
    }
  }

  /**
   * 연결 성공 핸들러
   */
  private handleOpen(event: Event): void {
    console.log('✅ WebSocket 연결 성공');
    
    this.isConnected = true;
    this.reconnectAttempts = 0;
    this.lastPongTime = Date.now();
    
    // 큐에 있는 메시지 전송
    this.flushMessageQueue();
    
    // Ping 타이머 시작
    this.startPingTimer();
    
    // 연결 성공 이벤트 발생
    this.eventEmitter.emit('connected');
  }

  /**
   * 메시지 수신 핸들러
   */
  private handleMessage(event: MessageEvent): void {
    try {
      const data = JSON.parse(event.data);
      
      // Pong 메시지 처리
      if (data.type === 'pong') {
        this.handlePong();
        return;
      }
      
      // 일반 메시지 처리
      this.processMessage(data);
      
    } catch (error) {
      console.error('❌ WebSocket 메시지 파싱 실패:', error);
    }
  }

  /**
   * 연결 종료 핸들러
   */
  private handleClose(event: CloseEvent): void {
    console.log(`🔌 WebSocket 연결 종료: ${event.code} - ${event.reason}`);
    
    this.isConnected = false;
    this.clearTimers();
    
    this.eventEmitter.emit('disconnected', event.reason);
    
    // 수동 종료가 아닌 경우 재연결 시도
    if (!this.isManualClose && event.code !== 1000) {
      this.scheduleReconnect();
    }
  }

  /**
   * 에러 핸들러
   */
  private handleError(event: Event): void {
    console.error('❌ WebSocket 에러:', event);
    this.eventEmitter.emit('error', new Error('WebSocket 연결 에러'));
  }

  /**
   * 재연결 스케줄링
   */
  private scheduleReconnect(): void {
    if (this.isManualClose || this.reconnectAttempts >= this.config.reconnect.maxAttempts) {
      console.log('🚫 재연결 중단 (최대 시도 횟수 초과 또는 수동 종료)');
      return;
    }

    this.reconnectAttempts++;
    
    const delay = Math.min(
      this.config.reconnect.initialDelay * Math.pow(this.config.reconnect.backoffFactor, this.reconnectAttempts - 1),
      this.config.reconnect.maxDelay
    );

    console.log(`🔄 ${delay}ms 후 재연결 시도 (${this.reconnectAttempts}/${this.config.reconnect.maxAttempts})`);
    
    this.eventEmitter.emit('reconnecting', this.reconnectAttempts);
    
    this.reconnectTimer = setTimeout(() => {
      this.createConnection();
    }, delay);
  }

  /**
   * Ping 타이머 시작
   */
  private startPingTimer(): void {
    this.pingTimer = setInterval(() => {
      this.sendPing();
    }, this.config.pingInterval);
  }

  /**
   * Ping 메시지 전송
   */
  private sendPing(): void {
    if (this.isConnected) {
      this.sendMessage({ type: 'ping', timestamp: Date.now() });
      
      // Pong 타임아웃 설정
      this.pongTimer = setTimeout(() => {
        console.warn('⚠️ Pong 응답 타임아웃 - 연결 재시작');
        this.ws?.close(1006, 'Ping timeout');
      }, this.config.pongTimeout);
    }
  }

  /**
   * Pong 응답 처리
   */
  private handlePong(): void {
    this.lastPongTime = Date.now();
    
    if (this.pongTimer) {
      clearTimeout(this.pongTimer);
      this.pongTimer = null;
    }
  }

  /**
   * 메시지 전송
   */
  public sendMessage(message: any): void {
    const messageStr = JSON.stringify(message);
    
    if (this.isConnected && this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(messageStr);
    } else {
      // 큐에 메시지 추가
      this.addToQueue(messageStr);
    }
  }

  /**
   * 메시지 큐에 추가
   */
  private addToQueue(message: string): void {
    if (this.messageQueue.length >= this.config.queue.maxSize) {
      switch (this.config.queue.dropPolicy) {
        case 'oldest':
          this.messageQueue.shift();
          break;
        case 'newest':
          this.messageQueue.pop();
          break;
        case 'reject':
          console.warn('⚠️ 메시지 큐가 가득참 - 메시지 거부');
          return;
      }
    }
    
    this.messageQueue.push(message);
  }

  /**
   * 메시지 큐 비우기
   */
  private flushMessageQueue(): void {
    while (this.messageQueue.length > 0 && this.isConnected) {
      const message = this.messageQueue.shift();
      if (message) {
        this.ws?.send(message);
      }
    }
  }

  /**
   * 메시지 처리
   */
  private processMessage(data: any): void {
    const { type, payload } = data;
    
    switch (type) {
      case 'system:status':
        this.eventEmitter.emit('system:status', payload);
        break;
      case 'system:usage':
        this.eventEmitter.emit('system:usage', payload);
        break;
      case 'price:update':
        this.eventEmitter.emit('price:update', payload);
        break;
      case 'signal:update':
        this.eventEmitter.emit('signal:update', payload);
        break;
      case 'news:update':
        this.eventEmitter.emit('news:update', payload);
        break;
      case 'market:status':
        this.eventEmitter.emit('market:status', payload);
        break;
      default:
        console.warn('⚠️ 알 수 없는 메시지 타입:', type);
    }
  }

  /**
   * 타이머 정리
   */
  private clearTimers(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
    
    if (this.pongTimer) {
      clearTimeout(this.pongTimer);
      this.pongTimer = null;
    }
  }

  /**
   * 이벤트 리스너 등록
   */
  public on<K extends keyof WebSocketEvents>(event: K, listener: WebSocketEvents[K]): void {
    this.eventEmitter.on(event, listener);
  }

  /**
   * 이벤트 리스너 제거
   */
  public off<K extends keyof WebSocketEvents>(event: K, listener: WebSocketEvents[K]): void {
    this.eventEmitter.off(event, listener);
  }

  /**
   * 연결 상태 확인
   */
  public isConnectionOpen(): boolean {
    return this.isConnected && this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * 연결 품질 정보
   */
  public getConnectionInfo() {
    return {
      isConnected: this.isConnected,
      reconnectAttempts: this.reconnectAttempts,
      queueSize: this.messageQueue.length,
      lastPongTime: this.lastPongTime,
      readyState: this.ws?.readyState,
    };
  }

  /**
   * 구독 관리 헬퍼 메서드들
   */
  public subscribeTo(events: (keyof WebSocketEvents)[]): void {
    if (this.isConnected) {
      this.sendMessage({
        type: 'subscribe',
        events: events
      });
    }
  }

  public unsubscribeFrom(events: (keyof WebSocketEvents)[]): void {
    if (this.isConnected) {
      this.sendMessage({
        type: 'unsubscribe',
        events: events
      });
    }
  }
}