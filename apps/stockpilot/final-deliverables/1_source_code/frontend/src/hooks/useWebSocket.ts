/**
 * StockPilot AI WebSocket 클라이언트 훅
 * 실시간 데이터 스트리밍 및 자동 재연결 지원
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import websocketSchemas from '../schemas/websocket-schemas.json';

// WebSocket 연결 상태
export enum WebSocketState {
  CONNECTING = 'CONNECTING',
  CONNECTED = 'CONNECTED', 
  DISCONNECTED = 'DISCONNECTED',
  ERROR = 'ERROR',
  RECONNECTING = 'RECONNECTING'
}

// WebSocket 메시지 타입들
export interface WSMessage {
  type: string;
  payload?: any;
  timestamp: string;
  schema_version?: string;
}

export interface ConnectionMessage extends WSMessage {
  type: 'connection';
  status: 'connected' | 'disconnected';
  client_id: string;
  market: 'US';
  services: {
    stock_data: boolean;
    currency_exchange: boolean;
    news_analysis: boolean;
    ai_signals: boolean;
  };
  available_channels: string[];
}

export interface USStocksMessage extends WSMessage {
  type: 'us_stocks';
  payload: {
    stocks: Array<{
      symbol: string;
      company_name: string;
      current_price: number;
      change: number;
      change_percent: number;
      volume: number;
      market_cap?: number;
      market_state: string;
      timestamp: string;
    }>;
    market: 'US';
    count: number;
  };
}

export interface ExchangeRatesMessage extends WSMessage {
  type: 'exchange_rates';
  payload: {
    rates: Array<{
      pair: string;
      rate: number;
      change_percent?: number;
      timestamp: string;
    }>;
    base_currency: 'USD';
  };
}

export interface MarketStatusMessage extends WSMessage {
  type: 'market_status';
  payload: {
    markets: Array<{
      market_code: 'US';
      market_name: string;
      status: 'OPEN' | 'CLOSED' | 'PRE_MARKET' | 'AFTER_HOURS';
      timezone: 'US/Eastern';
      open_time: string;
      close_time: string;
      current_time: string;
      timestamp: string;
    }>;
  };
}

export interface AISignalsMessage extends WSMessage {
  type: 'ai_signals';
  payload: {
    signals: Array<{
      id: string;
      symbol: string;
      company_name: string;
      signal_type: 'BUY' | 'SELL' | 'HOLD';
      confidence: number;
      strength: 'HIGH' | 'MEDIUM' | 'LOW';
      current_price: number;
      target_price?: number;
      expected_return?: number;
      risk_level: 'HIGH' | 'MEDIUM' | 'LOW';
      reasoning: string;
      technical_score: number;
      fundamental_score: number;
      sentiment_score: number;
      created_at: string;
      market_state: string;
    }>;
    market: 'US';
    count: number;
  };
}

export interface USNewsMessage extends WSMessage {
  type: 'us_news';
  payload: {
    news: Array<{
      id: string;
      title: string;
      summary: string;
      sentiment: 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL';
      sentiment_score: number;
      impact_score: number;
      source: string;
      published_at?: string;
      url?: string;
    }>;
    market: 'US';
    count: number;
  };
}

// WebSocket 설정
interface WebSocketConfig {
  url: string;
  protocols?: string | string[];
  reconnectInterval: number;
  maxReconnectAttempts: number;
  pingInterval: number;
  enableSchemaValidation: boolean;
}

// 기본 설정
const defaultConfig: WebSocketConfig = {
  url: 'ws://localhost:8765/ws',
  protocols: ['stockpilot-v1'],
  reconnectInterval: 3000,
  maxReconnectAttempts: 10,
  pingInterval: 30000,
  enableSchemaValidation: true
};

// 메시지 핸들러 타입
export type MessageHandler<T = WSMessage> = (message: T) => void;

export interface UseWebSocketOptions {
  config?: Partial<WebSocketConfig>;
  onConnection?: MessageHandler<ConnectionMessage>;
  onUSStocks?: MessageHandler<USStocksMessage>;
  onExchangeRates?: MessageHandler<ExchangeRatesMessage>;
  onMarketStatus?: MessageHandler<MarketStatusMessage>;
  onAISignals?: MessageHandler<AISignalsMessage>;
  onUSNews?: MessageHandler<USNewsMessage>;
  onError?: (error: Error) => void;
  autoConnect?: boolean;
  channels?: string[];
}

export interface UseWebSocketReturn {
  connectionState: WebSocketState;
  isConnected: boolean;
  lastMessage: WSMessage | null;
  sendMessage: (message: any) => boolean;
  subscribe: (channels: string[]) => void;
  unsubscribe: (channels: string[]) => void;
  connect: () => void;
  disconnect: () => void;
  reconnect: () => void;
  connectionInfo: {
    clientId?: string;
    connectedAt?: Date;
    reconnectAttempts: number;
    availableChannels: string[];
    subscribedChannels: string[];
  };
}

/**
 * StockPilot WebSocket 훅
 * 실시간 데이터 스트리밍을 위한 WebSocket 연결 관리
 */
export const useWebSocket = (options: UseWebSocketOptions = {}): UseWebSocketReturn => {
  // 설정 병합
  const config = { ...defaultConfig, ...options.config };
  
  // 상태 관리
  const [connectionState, setConnectionState] = useState<WebSocketState>(WebSocketState.DISCONNECTED);
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null);
  const [connectionInfo, setConnectionInfo] = useState({
    clientId: undefined as string | undefined,
    connectedAt: undefined as Date | undefined,
    reconnectAttempts: 0,
    availableChannels: [] as string[],
    subscribedChannels: [] as string[]
  });

  // WebSocket 레퍼런스
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  
  // 스키마 검증
  const validateMessage = useCallback((message: WSMessage): boolean => {
    if (!config.enableSchemaValidation) return true;
    
    try {
      const schemas = websocketSchemas.schemas as any;
      const messageSchema = schemas[message.type];
      
      if (!messageSchema) {
        console.warn(`[WebSocket] 알 수 없는 메시지 타입: ${message.type}`);
        return false;
      }
      
      // 스키마 버전 확인
      const messageSchemaVersion = message.schema_version || '1.0';
      const expectedSchemaVersion = messageSchema.version;
      
      if (messageSchemaVersion !== expectedSchemaVersion) {
        console.warn(`[WebSocket] 스키마 버전 불일치: ${messageSchemaVersion} (예상: ${expectedSchemaVersion})`);
        // 하위 호환성을 위해 메시지는 처리하지만 경고만 출력
      }
      
      return true;
    } catch (error) {
      console.error('[WebSocket] 스키마 검증 오류:', error);
      return false;
    }
  }, [config.enableSchemaValidation]);

  // 메시지 처리
  const handleMessage = useCallback((message: WSMessage) => {
    // 스키마 검증
    if (!validateMessage(message)) {
      return;
    }
    
    setLastMessage(message);
    
    // 타입별 핸들러 호출
    switch (message.type) {
      case 'connection':
        const connMsg = message as ConnectionMessage;
        setConnectionInfo(prev => ({
          ...prev,
          clientId: connMsg.client_id,
          connectedAt: new Date(),
          availableChannels: connMsg.available_channels || []
        }));
        options.onConnection?.(connMsg);
        break;
        
      case 'us_stocks':
        options.onUSStocks?.(message as USStocksMessage);
        break;
        
      case 'exchange_rates':
        options.onExchangeRates?.(message as ExchangeRatesMessage);
        break;
        
      case 'market_status':
        options.onMarketStatus?.(message as MarketStatusMessage);
        break;
        
      case 'ai_signals':
        options.onAISignals?.(message as AISignalsMessage);
        break;
        
      case 'us_news':
        options.onUSNews?.(message as USNewsMessage);
        break;
        
      case 'subscribed':
        // 구독 성공 처리
        const events = (message as any).events || [];
        setConnectionInfo(prev => ({
          ...prev,
          subscribedChannels: Array.from(new Set([...prev.subscribedChannels, ...events]))
        }));
        console.log(`[WebSocket] 구독 완료: ${events.join(', ')}`);
        break;
        
      case 'unsubscribed':
        // 구독 해제 처리
        const unsubEvents = (message as any).events || [];
        setConnectionInfo(prev => ({
          ...prev,
          subscribedChannels: prev.subscribedChannels.filter(ch => !unsubEvents.includes(ch))
        }));
        console.log(`[WebSocket] 구독 해제: ${unsubEvents.join(', ')}`);
        break;
        
      case 'pong':
        // Pong 응답 처리 (조용히)
        break;
        
      case 'error':
        console.error('[WebSocket] 서버 에러:', message);
        options.onError?.(new Error((message as any).message || 'Unknown server error'));
        break;
        
      default:
        console.warn(`[WebSocket] 처리되지 않은 메시지 타입: ${message.type}`, message);
    }
  }, [validateMessage, options]);

  // Ping 전송
  const sendPing = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
        type: 'ping',
        timestamp: new Date().toISOString()
      }));
    }
  }, []);

  // 메시지 전송
  const sendMessage = useCallback((message: any): boolean => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      try {
        ws.current.send(JSON.stringify({
          ...message,
          timestamp: new Date().toISOString(),
          schema_version: '1.0'
        }));
        return true;
      } catch (error) {
        console.error('[WebSocket] 메시지 전송 실패:', error);
        options.onError?.(error as Error);
        return false;
      }
    }
    console.warn('[WebSocket] 연결되지 않은 상태에서 메시지 전송 시도');
    return false;
  }, [options]);

  // 채널 구독
  const subscribe = useCallback((channels: string[]) => {
    sendMessage({
      type: 'subscribe',
      events: channels
    });
  }, [sendMessage]);

  // 채널 구독 해제
  const unsubscribe = useCallback((channels: string[]) => {
    sendMessage({
      type: 'unsubscribe',
      events: channels
    });
  }, [sendMessage]);

  // 재연결 로직
  const scheduleReconnect = useCallback(() => {
    if (connectionInfo.reconnectAttempts >= config.maxReconnectAttempts) {
      console.error('[WebSocket] 최대 재연결 시도 횟수 초과');
      setConnectionState(WebSocketState.ERROR);
      return;
    }

    setConnectionState(WebSocketState.RECONNECTING);
    setConnectionInfo(prev => ({
      ...prev,
      reconnectAttempts: prev.reconnectAttempts + 1
    }));

    reconnectTimeoutRef.current = setTimeout(() => {
      console.log(`[WebSocket] 재연결 시도 ${connectionInfo.reconnectAttempts + 1}/${config.maxReconnectAttempts}`);
      connect();
    }, config.reconnectInterval);
  }, [connectionInfo.reconnectAttempts, config.maxReconnectAttempts, config.reconnectInterval]);

  // WebSocket 연결
  const connect = useCallback(() => {
    // 기존 연결이 있으면 정리
    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }

    // 재연결 타이머 정리
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    try {
      setConnectionState(WebSocketState.CONNECTING);
      console.log(`[WebSocket] 연결 시도: ${config.url}`);
      
      ws.current = new WebSocket(config.url, config.protocols);
      
      ws.current.onopen = () => {
        console.log('[WebSocket] 연결 성공');
        setConnectionState(WebSocketState.CONNECTED);
        setConnectionInfo(prev => ({
          ...prev,
          reconnectAttempts: 0,
          connectedAt: new Date()
        }));
        
        // Ping 시작
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
        }
        pingIntervalRef.current = setInterval(sendPing, config.pingInterval);
        
        // 자동 채널 구독
        if (options.channels && options.channels.length > 0) {
          setTimeout(() => subscribe(options.channels!), 100);
        }
      };
      
      ws.current.onmessage = (event) => {
        try {
          const message: WSMessage = JSON.parse(event.data);
          handleMessage(message);
        } catch (error) {
          console.error('[WebSocket] 메시지 파싱 오류:', error, event.data);
          options.onError?.(new Error('Message parsing failed'));
        }
      };
      
      ws.current.onclose = (event) => {
        console.log(`[WebSocket] 연결 종료: ${event.code} - ${event.reason}`);
        setConnectionState(WebSocketState.DISCONNECTED);
        
        // Ping 정리
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }
        
        // 비정상 종료인 경우 재연결 시도
        if (event.code !== 1000 && connectionInfo.reconnectAttempts < config.maxReconnectAttempts) {
          scheduleReconnect();
        }
      };
      
      ws.current.onerror = (error) => {
        console.error('[WebSocket] 연결 오류:', error);
        setConnectionState(WebSocketState.ERROR);
        options.onError?.(new Error('WebSocket connection error'));
      };
      
    } catch (error) {
      console.error('[WebSocket] 연결 생성 실패:', error);
      setConnectionState(WebSocketState.ERROR);
      options.onError?.(error as Error);
    }
  }, [config, options, connectionInfo.reconnectAttempts, sendPing, subscribe, handleMessage, scheduleReconnect]);

  // WebSocket 연결 해제
  const disconnect = useCallback(() => {
    console.log('[WebSocket] 연결 해제');
    
    // 재연결 타이머 정리
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    // Ping 정리
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    
    // WebSocket 정리
    if (ws.current) {
      ws.current.close(1000, 'Client disconnected');
      ws.current = null;
    }
    
    setConnectionState(WebSocketState.DISCONNECTED);
    setConnectionInfo(prev => ({
      ...prev,
      reconnectAttempts: 0,
      subscribedChannels: []
    }));
  }, []);

  // 재연결
  const reconnect = useCallback(() => {
    setConnectionInfo(prev => ({
      ...prev,
      reconnectAttempts: 0
    }));
    disconnect();
    setTimeout(connect, 100);
  }, [connect, disconnect]);

  // 자동 연결
  useEffect(() => {
    if (options.autoConnect !== false) {
      connect();
    }
    
    // 클린업
    return () => {
      disconnect();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    connectionState,
    isConnected: connectionState === WebSocketState.CONNECTED,
    lastMessage,
    sendMessage,
    subscribe,
    unsubscribe,
    connect,
    disconnect,
    reconnect,
    connectionInfo
  };
};