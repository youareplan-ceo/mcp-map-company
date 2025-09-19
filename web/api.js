// API 연결 설정
const API_CONFIG = {
    // 로컬 개발시
    local: 'http://localhost:8000',
    // 배포시 (회장님 서버 주소로 변경 필요)
    production: 'https://api.youareplan.com'
};

// 현재 환경 감지
const API_BASE = window.location.hostname === 'localhost' 
    ? API_CONFIG.local 
    : API_CONFIG.production;

// 주식 데이터 가져오기
async function fetchStockData() {
    try {
        const response = await fetch(`${API_BASE}/api/stocks`);
        if (!response.ok) throw new Error('API 연결 실패');
        return await response.json();
    } catch (error) {
        console.error('주식 데이터 로딩 실패:', error);
        // 연결 실패시 샘플 데이터 반환
        return {
            stocks: [
                { name: '삼성전자', price: '89,500', change: '+2.3%', isUp: true },
                { name: 'SK하이닉스', price: '195,000', change: '+1.8%', isUp: true },
                { name: 'NAVER', price: '245,000', change: '-0.5%', isUp: false }
            ],
            status: 'demo'
        };
    }
}

// 포트폴리오 데이터 가져오기
async function fetchPortfolioData() {
    try {
        const response = await fetch(`${API_BASE}/api/portfolio`);
        if (!response.ok) throw new Error('API 연결 실패');
        return await response.json();
    } catch (error) {
        console.error('포트폴리오 데이터 로딩 실패:', error);
        // 연결 실패시 샘플 데이터 반환
        return {
            holdings: [
                { name: '삼성전자', percentage: 30 },
                { name: 'SK하이닉스', percentage: 25 },
                { name: 'NAVER', percentage: 20 },
                { name: '카카오', percentage: 15 },
                { name: '기타', percentage: 10 }
            ],
            totalValue: '10,000,000',
            todayProfit: '+240,000',
            status: 'demo'
        };
    }
}

// AI 추천 가져오기
async function fetchAIRecommendations() {
    try {
        const response = await fetch(`${API_BASE}/api/ai-recommendations`);
        if (!response.ok) throw new Error('API 연결 실패');
        return await response.json();
    } catch (error) {
        console.error('AI 추천 로딩 실패:', error);
        // 연결 실패시 샘플 데이터 반환
        return {
            recommendations: [
                { name: '삼성전자', signal: '매수', strength: '강함' },
                { name: 'NAVER', signal: '관망', strength: '보통' },
                { name: '카카오', signal: '매수 대기', strength: '강함' }
            ],
            lastUpdate: new Date().toISOString(),
            status: 'demo'
        };
    }
}

// WebSocket 연결 (실시간 업데이트용)
function connectWebSocket() {
    const wsUrl = API_BASE.replace('http', 'ws') + '/ws';
    
    try {
        const ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
            console.log('실시간 연결 성공');
            updateConnectionStatus(true);
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleRealtimeUpdate(data);
        };
        
        ws.onerror = (error) => {
            console.error('WebSocket 에러:', error);
            updateConnectionStatus(false);
        };
        
        ws.onclose = () => {
            console.log('연결 종료, 5초 후 재연결');
            updateConnectionStatus(false);
            setTimeout(connectWebSocket, 5000);
        };
        
        return ws;
    } catch (error) {
        console.error('WebSocket 연결 실패:', error);
        updateConnectionStatus(false);
        return null;
    }
}

// 연결 상태 업데이트
function updateConnectionStatus(isConnected) {
    const statusElements = document.querySelectorAll('.connect-status');
    statusElements.forEach(el => {
        if (isConnected) {
            el.classList.remove('status-offline');
            el.classList.add('status-online');
        } else {
            el.classList.remove('status-online');
            el.classList.add('status-offline');
        }
    });
}

// 실시간 데이터 처리
function handleRealtimeUpdate(data) {
    if (data.type === 'stock_update') {
        updateStockList(data.stocks);
    } else if (data.type === 'portfolio_update') {
        updatePortfolio(data.portfolio);
    } else if (data.type === 'ai_signal') {
        showAISignal(data.signal);
    }
}

// 주식 목록 업데이트
function updateStockList(stocks) {
    // index.html의 renderStocks() 함수 호출
    if (typeof renderStocks === 'function') {
        renderStocks(stocks);
    }
}

// 포트폴리오 업데이트
function updatePortfolio(portfolio) {
    // 차트 업데이트 로직
    console.log('포트폴리오 업데이트:', portfolio);
}

// AI 신호 표시
function showAISignal(signal) {
    // 알림 표시 로직
    console.log('AI 신호:', signal);
}

// 초기화
document.addEventListener('DOMContentLoaded', () => {
    // WebSocket 연결 시도
    connectWebSocket();
    
    // 초기 데이터 로드
    fetchStockData();
    fetchPortfolioData();
    fetchAIRecommendations();
});

// Export for use in index.html
window.API = {
    fetchStockData,
    fetchPortfolioData,
    fetchAIRecommendations,
    connectWebSocket
};