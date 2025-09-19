// StockPilot AI 한국어 번역 파일
// 작성자: StockPilot Team
// 용도: 한국어 UI 번역 및 현지화

export const ko = {
  // 공통 텍스트
  common: {
    // 기본 액션
    save: '저장',
    cancel: '취소',
    delete: '삭제',
    edit: '편집',
    add: '추가',
    remove: '제거',
    confirm: '확인',
    close: '닫기',
    back: '뒤로',
    next: '다음',
    previous: '이전',
    submit: '제출',
    reset: '초기화',
    search: '검색',
    filter: '필터',
    sort: '정렬',
    refresh: '새로고침',
    download: '다운로드',
    upload: '업로드',
    export: '내보내기',
    import: '가져오기',
    copy: '복사',
    paste: '붙여넣기',
    cut: '잘라내기',
    undo: '실행 취소',
    redo: '다시 실행',
    
    // 상태
    loading: '로딩 중...',
    saving: '저장 중...',
    success: '성공',
    error: '오류',
    warning: '경고',
    info: '정보',
    empty: '데이터가 없습니다',
    noData: '표시할 데이터가 없습니다',
    notFound: '찾을 수 없습니다',
    unauthorized: '권한이 없습니다',
    forbidden: '접근이 금지되었습니다',
    serverError: '서버 오류가 발생했습니다',
    networkError: '네트워크 오류가 발생했습니다',
    
    // 시간 관련
    today: '오늘',
    yesterday: '어제',
    tomorrow: '내일',
    thisWeek: '이번 주',
    thisMonth: '이번 달',
    thisYear: '올해',
    lastWeek: '지난 주',
    lastMonth: '지난 달',
    lastYear: '작년',
    
    // 일반적인 라벨
    name: '이름',
    description: '설명',
    type: '유형',
    category: '카테고리',
    status: '상태',
    date: '날짜',
    time: '시간',
    startDate: '시작 날짜',
    endDate: '종료 날짜',
    amount: '금액',
    price: '가격',
    quantity: '수량',
    total: '총계',
    subtotal: '소계',
    tax: '세금',
    discount: '할인',
    
    // 확인 메시지
    confirmDelete: '정말 삭제하시겠습니까?',
    confirmCancel: '변경사항이 취소됩니다. 계속하시겠습니까?',
    unsavedChanges: '저장되지 않은 변경사항이 있습니다.',
    
    // 단위
    currency: '원',
    percent: '%',
    shares: '주',
    days: '일',
    hours: '시간',
    minutes: '분',
    seconds: '초',
  },

  // 브랜드 및 제품명
  brand: {
    name: '스톡파일럿',
    nameEn: 'StockPilot',
    tagline: 'AI 투자 코파일럿',
    taglineEn: 'AI Investment Copilot',
    description: '인공지능과 함께하는 스마트 투자',
    fullDescription: '데이터 기반 투자 결정을 도와주는 AI 투자 어시스턴트',
  },

  // 네비게이션
  navigation: {
    dashboard: '대시보드',
    portfolio: '포트폴리오',
    analysis: '분석',
    signals: '투자 신호',
    watchlist: '관심 종목',
    news: '뉴스',
    market: '시장',
    settings: '설정',
    profile: '프로필',
    help: '도움말',
    logout: '로그아웃',
    login: '로그인',
    signup: '회원가입',
    
    // 서브 메뉴
    overview: '개요',
    performance: '수익률',
    holdings: '보유 종목',
    transactions: '거래 내역',
    reports: '리포트',
    alerts: '알림',
    tools: '도구',
    
    // 하단 네비게이션 (모바일)
    home: '홈',
    invest: '투자',
    discover: '발견',
    account: '계정',
  },

  // 대시보드
  dashboard: {
    title: '대시보드',
    welcome: '환영합니다',
    goodMorning: '좋은 아침입니다',
    goodAfternoon: '좋은 오후입니다',
    goodEvening: '좋은 저녁입니다',
    
    // 요약 카드
    totalValue: '총 자산',
    totalReturn: '총 수익률',
    todayReturn: '오늘 수익률',
    unrealizedGain: '평가 손익',
    realizedGain: '실현 손익',
    cashBalance: '현금 잔고',
    investedAmount: '투자 금액',
    portfolioValue: '포트폴리오 가치',
    
    // 차트 및 분석
    performanceChart: '수익률 차트',
    assetAllocation: '자산 배분',
    sectorAllocation: '섹터 배분',
    topGainers: '상승률 상위',
    topLosers: '하락률 상위',
    recentTransactions: '최근 거래',
    marketOverview: '시장 개요',
    
    // 추천 및 알림
    aiRecommendations: 'AI 추천',
    signalAlerts: '신호 알림',
    newsHighlights: '주요 뉴스',
    marketUpdates: '시장 소식',
    
    // 퀵 액션
    quickActions: '빠른 작업',
    addTransaction: '거래 추가',
    updatePortfolio: '포트폴리오 업데이트',
    viewAnalysis: '분석 보기',
    checkAlerts: '알림 확인',
  },

  // 포트폴리오
  portfolio: {
    title: '포트폴리오',
    myPortfolio: '내 포트폴리오',
    overview: '포트폴리오 개요',
    performance: '포트폴리오 성과',
    allocation: '자산 배분',
    
    // 보유 종목
    holdings: '보유 종목',
    stockName: '종목명',
    symbol: '종목코드',
    shares: '보유주식수',
    avgPrice: '평균 단가',
    currentPrice: '현재가',
    marketValue: '평가액',
    gain: '손익',
    gainPercent: '손익률',
    weight: '비중',
    
    // 거래
    transactions: '거래 내역',
    buy: '매수',
    sell: '매도',
    dividend: '배당',
    split: '주식분할',
    transactionDate: '거래일',
    transactionType: '거래 유형',
    pricePerShare: '주당 가격',
    totalAmount: '총 금액',
    commission: '수수료',
    
    // 분석
    diversification: '분산 정도',
    riskLevel: '위험 수준',
    correlation: '상관관계',
    volatility: '변동성',
    sharpeRatio: '샤프 비율',
    beta: '베타',
    alpha: '알파',
    
    // 액션
    addHolding: '종목 추가',
    editHolding: '종목 수정',
    removeHolding: '종목 제거',
    recordTransaction: '거래 기록',
    rebalance: '리밸런싱',
    generateReport: '리포트 생성',
  },

  // 투자 분석
  analysis: {
    title: '투자 분석',
    fundamentalAnalysis: '기본 분석',
    technicalAnalysis: '기술적 분석',
    sentimentAnalysis: '감정 분석',
    aiAnalysis: 'AI 분석',
    
    // 기본 분석
    financialRatios: '재무 비율',
    peRatio: 'PER',
    pbRatio: 'PBR',
    roe: 'ROE',
    roa: 'ROA',
    debtRatio: '부채비율',
    currentRatio: '유동비율',
    eps: '주당순이익',
    bps: '주당순자산',
    dividend: '배당',
    dividendYield: '배당수익률',
    
    // 기술적 분석
    priceChart: '주가 차트',
    candlestick: '캔들스틱',
    volume: '거래량',
    movingAverage: '이동평균',
    bollinger: '볼린저 밴드',
    rsi: 'RSI',
    macd: 'MACD',
    stochastic: '스토캐스틱',
    
    // 신호 및 추천
    buySignal: '매수 신호',
    sellSignal: '매도 신호',
    holdSignal: '보유 신호',
    strongBuy: '적극 매수',
    strongSell: '적극 매도',
    recommendation: '투자 의견',
    targetPrice: '목표가',
    stopLoss: '손절가',
    
    // AI 분석
    aiScore: 'AI 점수',
    aiInsights: 'AI 인사이트',
    predictedPrice: '예상 주가',
    confidenceLevel: '신뢰도',
    riskAssessment: '위험 평가',
    opportunityScore: '기회 점수',
  },

  // 시장 데이터
  market: {
    title: '시장',
    marketOverview: '시장 개요',
    indices: '지수',
    sectors: '섹터',
    currencies: '환율',
    commodities: '원자재',
    
    // 주식 시장
    kospi: '코스피',
    kosdaq: '코스닥',
    nasdaq: '나스닥',
    sp500: 'S&P 500',
    dowJones: '다우존스',
    nikkei: '니케이',
    
    // 시장 상태
    marketOpen: '장 개장',
    marketClosed: '장 마감',
    preMarket: '장전 거래',
    afterHours: '시간외 거래',
    marketHours: '거래 시간',
    
    // 가격 정보
    lastPrice: '현재가',
    change: '등락',
    changePercent: '등락률',
    high: '고가',
    low: '저가',
    open: '시가',
    previousClose: '전일 종가',
    volume: '거래량',
    turnover: '거래대금',
    marketCap: '시가총액',
    
    // 순위 및 목록
    topGainers: '상승률 상위',
    topLosers: '하락률 상위',
    mostActive: '거래량 상위',
    newHighs: '신고가',
    newLows: '신저가',
    hotStocks: '인기 종목',
  },

  // 뉴스 및 정보
  news: {
    title: '뉴스',
    latestNews: '최신 뉴스',
    marketNews: '시장 뉴스',
    companyNews: '기업 뉴스',
    economicNews: '경제 뉴스',
    analysisReports: '분석 리포트',
    
    // 뉴스 메타데이터
    source: '출처',
    author: '기자',
    publishedAt: '발행 시간',
    readMore: '더 보기',
    relatedStocks: '관련 종목',
    sentiment: '감정 분석',
    positive: '긍정적',
    negative: '부정적',
    neutral: '중립적',
    
    // 필터
    filterBySource: '출처별 필터',
    filterByDate: '날짜별 필터',
    filterBySector: '섹터별 필터',
    searchNews: '뉴스 검색',
  },

  // 알림 및 신호
  signals: {
    title: '투자 신호',
    alerts: '알림',
    notifications: '알림 목록',
    signalHistory: '신호 내역',
    alertSettings: '알림 설정',
    
    // 신호 유형
    priceAlert: '가격 알림',
    volumeAlert: '거래량 알림',
    newsAlert: '뉴스 알림',
    technicalAlert: '기술적 신호',
    fundamentalAlert: '기본 분석 신호',
    aiAlert: 'AI 신호',
    
    // 알림 설정
    enableAlerts: '알림 활성화',
    alertFrequency: '알림 빈도',
    alertChannels: '알림 방식',
    email: '이메일',
    sms: 'SMS',
    push: '푸시 알림',
    telegram: '텔레그램',
    
    // 신호 상태
    active: '활성',
    triggered: '발생',
    expired: '만료',
    pending: '대기',
    cancelled: '취소',
  },

  // 설정
  settings: {
    title: '설정',
    generalSettings: '일반 설정',
    accountSettings: '계정 설정',
    privacySettings: '개인정보 설정',
    notificationSettings: '알림 설정',
    displaySettings: '화면 설정',
    tradingSettings: '거래 설정',
    
    // 일반 설정
    language: '언어',
    timezone: '시간대',
    currency: '기본 통화',
    dateFormat: '날짜 형식',
    numberFormat: '숫자 형식',
    
    // 화면 설정
    theme: '테마',
    lightMode: '라이트 모드',
    darkMode: '다크 모드',
    systemMode: '시스템 설정',
    fontSize: '글자 크기',
    colorScheme: '색상 테마',
    
    // 개인정보
    personalInfo: '개인정보',
    changePassword: '비밀번호 변경',
    twoFactorAuth: '2단계 인증',
    loginHistory: '로그인 기록',
    dataExport: '데이터 내보내기',
    accountDeletion: '계정 삭제',
    
    // 거래 설정
    defaultOrderType: '기본 주문 유형',
    confirmationRequired: '확인 필요',
    maxOrderAmount: '최대 주문 금액',
    riskTolerance: '위험 허용도',
    investmentStyle: '투자 스타일',
  },

  // 사용자 인증
  auth: {
    // 로그인
    login: '로그인',
    loginTitle: '스톡파일럿에 로그인',
    loginSubtitle: 'AI와 함께하는 스마트 투자를 시작하세요',
    email: '이메일',
    password: '비밀번호',
    rememberMe: '로그인 상태 유지',
    forgotPassword: '비밀번호를 잊으셨나요?',
    loginButton: '로그인',
    
    // 회원가입
    signup: '회원가입',
    signupTitle: '스톡파일럿 계정 만들기',
    signupSubtitle: '무료로 시작하여 AI 투자 도우미를 경험해보세요',
    firstName: '이름',
    lastName: '성',
    confirmPassword: '비밀번호 확인',
    agreeTerms: '이용약관에 동의합니다',
    agreePrivacy: '개인정보처리방침에 동의합니다',
    agreeMarketing: '마케팅 정보 수신에 동의합니다 (선택)',
    signupButton: '계정 만들기',
    
    // 비밀번호 재설정
    resetPassword: '비밀번호 재설정',
    resetPasswordTitle: '비밀번호 재설정',
    resetPasswordSubtitle: '등록된 이메일로 재설정 링크를 보내드립니다',
    sendResetEmail: '재설정 이메일 보내기',
    backToLogin: '로그인으로 돌아가기',
    
    // 오류 메시지
    invalidCredentials: '이메일 또는 비밀번호가 올바르지 않습니다',
    accountNotFound: '계정을 찾을 수 없습니다',
    emailAlreadyExists: '이미 등록된 이메일입니다',
    passwordTooWeak: '비밀번호가 너무 약합니다',
    passwordMismatch: '비밀번호가 일치하지 않습니다',
    termsNotAgreed: '이용약관에 동의해주세요',
    
    // 성공 메시지
    signupSuccess: '계정이 성공적으로 생성되었습니다',
    loginSuccess: '로그인되었습니다',
    resetEmailSent: '비밀번호 재설정 이메일이 발송되었습니다',
    passwordChanged: '비밀번호가 변경되었습니다',
  },

  // CSV 업로드
  csvUpload: {
    title: 'CSV 파일 업로드',
    selectFile: '파일 선택',
    dragAndDrop: '파일을 드래그하여 업로드하거나 클릭하세요',
    supportedFormats: '지원 형식: CSV',
    maxFileSize: '최대 파일 크기: 10MB',
    uploadProgress: '업로드 진행률',
    processing: '파일 처리 중...',
    validating: '데이터 검증 중...',
    importing: '데이터 가져오는 중...',
    
    // 매핑
    columnMapping: '컬럼 매핑',
    mapColumns: 'CSV 컬럼을 필드에 매핑하세요',
    csvColumn: 'CSV 컬럼',
    targetField: '대상 필드',
    preview: '미리보기',
    firstRows: '첫 5행 미리보기',
    
    // 검증
    validation: '데이터 검증',
    validationResults: '검증 결과',
    totalRows: '총 행 수',
    validRows: '유효한 행',
    errorRows: '오류가 있는 행',
    warningRows: '경고가 있는 행',
    
    // 오류
    fileTooBig: '파일이 너무 큽니다',
    invalidFormat: '지원하지 않는 파일 형식입니다',
    emptyFile: '빈 파일입니다',
    invalidData: '잘못된 데이터가 포함되어 있습니다',
    missingColumns: '필수 컬럼이 누락되었습니다',
    duplicateData: '중복 데이터가 있습니다',
    
    // 성공
    uploadSuccess: '파일이 성공적으로 업로드되었습니다',
    importSuccess: '데이터가 성공적으로 가져와졌습니다',
    rowsImported: '{{count}}개 행이 가져와졌습니다',
  },

  // 차트 및 시각화
  charts: {
    // 차트 유형
    lineChart: '선 차트',
    barChart: '막대 차트',
    candlestickChart: '캔들스틱 차트',
    pieChart: '원 차트',
    areaChart: '영역 차트',
    scatterChart: '산점도',
    
    // 시간 범위
    timeRange: '기간',
    oneDay: '1일',
    oneWeek: '1주',
    oneMonth: '1개월',
    threeMonths: '3개월',
    sixMonths: '6개월',
    oneYear: '1년',
    threeYears: '3년',
    fiveYears: '5년',
    allTime: '전체',
    
    // 지표
    indicators: '지표',
    movingAverage: '이동평균',
    ema: '지수이동평균',
    bollinger: '볼린저 밴드',
    rsi: 'RSI',
    macd: 'MACD',
    volume: '거래량',
    
    // 차트 도구
    zoomIn: '확대',
    zoomOut: '축소',
    resetZoom: '확대/축소 초기화',
    fullscreen: '전체화면',
    download: '차트 다운로드',
    share: '차트 공유',
  },

  // 도움말 및 지원
  help: {
    title: '도움말',
    faq: '자주 묻는 질문',
    tutorials: '튜토리얼',
    support: '고객 지원',
    contact: '문의하기',
    documentation: '문서',
    community: '커뮤니티',
    
    // FAQ 카테고리
    gettingStarted: '시작하기',
    portfolio: '포트폴리오',
    trading: '거래',
    technical: '기술적 문제',
    billing: '결제',
    security: '보안',
    
    // 지원
    contactUs: '문의하기',
    sendMessage: '메시지 보내기',
    chatSupport: '채팅 지원',
    emailSupport: '이메일 지원',
    phoneSupport: '전화 지원',
    responseTime: '응답 시간',
    businessHours: '운영 시간',
  },

  // 피드백 및 리뷰
  feedback: {
    title: '피드백',
    rating: '평점',
    review: '리뷰',
    comment: '의견',
    suggestion: '제안',
    bugReport: '버그 신고',
    featureRequest: '기능 요청',
    
    // 만족도
    satisfaction: '만족도',
    veryUnsatisfied: '매우 불만족',
    unsatisfied: '불만족',
    neutral: '보통',
    satisfied: '만족',
    verySatisfied: '매우 만족',
    
    // 메시지
    thankYou: '소중한 의견을 주셔서 감사합니다',
    feedbackSent: '피드백이 전송되었습니다',
    improveService: '더 나은 서비스를 위해 노력하겠습니다',
  },

  // 법적 고지사항
  legal: {
    terms: '이용약관',
    privacy: '개인정보처리방침',
    disclaimer: '면책조항',
    riskWarning: '투자 위험 고지',
    
    // 투자 위험 경고
    investmentRisk: {
      title: '투자 위험 고지',
      warning: '모든 투자에는 손실 위험이 따릅니다',
      description: '과거 성과는 미래 결과를 보장하지 않으며, 투자 결정은 본인의 책임입니다',
      aiDisclaimer: 'AI 분석은 참고용이며, 투자 조언이 아닙니다',
      consultation: '투자 전 전문가와 상담하시기 바랍니다',
    },
  },

  // 날짜 및 시간 형식
  dateTime: {
    // 상대적 시간
    justNow: '방금 전',
    minuteAgo: '1분 전',
    minutesAgo: '{{count}}분 전',
    hourAgo: '1시간 전',
    hoursAgo: '{{count}}시간 전',
    dayAgo: '1일 전',
    daysAgo: '{{count}}일 전',
    weekAgo: '1주 전',
    weeksAgo: '{{count}}주 전',
    monthAgo: '1개월 전',
    monthsAgo: '{{count}}개월 전',
    yearAgo: '1년 전',
    yearsAgo: '{{count}}년 전',
    
    // 요일
    monday: '월요일',
    tuesday: '화요일',
    wednesday: '수요일',
    thursday: '목요일',
    friday: '금요일',
    saturday: '토요일',
    sunday: '일요일',
    
    // 월
    january: '1월',
    february: '2월',
    march: '3월',
    april: '4월',
    may: '5월',
    june: '6월',
    july: '7월',
    august: '8월',
    september: '9월',
    october: '10월',
    november: '11월',
    december: '12월',
  },
};

export default ko;