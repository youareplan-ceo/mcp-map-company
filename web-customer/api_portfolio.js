(function(){
  const API_BASE = 'https://mcp-map-company.onrender.com';
  const API_KEY  = '<<PUT_YOUR_KEY>>'; // TODO: 실제 키

  function uid(){
    let u = localStorage.getItem('sp_uid');
    if(!u){
      u = 'sp_' + Math.random().toString(36).slice(2);
      localStorage.setItem('sp_uid', u);
    }
    return u;
  }

  async function apiGet(){
    const res = await fetch(API_BASE + '/api/v1/portfolio?userId=' + encodeURIComponent(uid()), {
      headers: {'x-stockpilot-key': API_KEY}
    });
    if(!res.ok) throw new Error('GET failed');
    return await res.json();
  }

  async function apiPut(payload){
    const res = await fetch(API_BASE + '/api/v1/portfolio', {
      method:'PUT',
      headers:{
        'content-type':'application/json',
        'x-stockpilot-key': API_KEY
      },
      body: JSON.stringify({ userId: uid(), ...payload })
    });
    if(!res.ok) throw new Error('PUT failed');
    return await res.json();
  }

  // 전역 노출 (기존 로컬스토리지 코드 대체에 사용)
  window.StockPilotAPI = { apiGet, apiPut, uid };
})();
// optional: allow overriding API key via localStorage 'sp_api_key'
(function(){
  try{
    const k = localStorage.getItem('sp_api_key');
    if (k && typeof k === 'string' && k.length > 5) {
      // api_portfolio.js 내부의 API_KEY 변수가 함수 스코프라면 window에 노출
      if (!window.StockPilotAPIKey) window.StockPilotAPIKey = k;
    }
  }catch(e){}
})();
