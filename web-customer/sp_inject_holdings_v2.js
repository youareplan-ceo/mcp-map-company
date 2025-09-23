(function(){
  // ---------- helpers ----------
  function nfUSD(n){ try { return new Intl.NumberFormat('en-US',{minimumFractionDigits:2, maximumFractionDigits:2}).format(n);}catch(e){return String(n)}}
  function sanitizeUSD(s){ if(s==null) return 0; let v=String(s).replace(/[, ]/g,'').replace(/[^0-9.]/g,''); const p=v.split('.'); if(p.length>2){ v=p.shift()+'.'+p.join(''); } return v?parseFloat(v):0; }
  function sanitizeInt(s){ const v=String(s||'').replace(/[^\d]/g,''); return v?parseInt(v,10):0; }

  // ---------- 현금 드로어(변함없음) ----------
  function hookCash(){
    const krw=document.querySelector('#cash-krw');
    const usd=document.querySelector('#cash-usd');
    if(!krw||!usd) return;

    krw.type='text'; krw.setAttribute('inputmode','numeric');
    usd.type='text'; usd.setAttribute('inputmode','decimal');

    const sKRW=localStorage.getItem('cashKRW'); if(sKRW){ const n=sanitizeInt(sKRW); krw.value=n? n.toLocaleString('ko-KR'):''; }
    const sUSD=localStorage.getItem('cashUSD'); if(sUSD){ const n=sanitizeUSD(sUSD); usd.value=n? nfUSD(n):''; }

    krw.addEventListener('blur', ()=>{ const n=sanitizeInt(krw.value); krw.value=n? n.toLocaleString('ko-KR'):''; });
    usd.addEventListener('blur', ()=>{ const n=sanitizeUSD(usd.value); usd.value=n? nfUSD(n):''; });

    const oldClose = window.closeDrawer;
    window.closeDrawer = function(kind){
      if(kind==='cash'){
        const k=sanitizeInt(krw.value), u=sanitizeUSD(usd.value);
        localStorage.setItem('cashKRW', String(k));
        localStorage.setItem('cashUSD', String(u));
        if(typeof window.refreshOverview==='function') window.refreshOverview();
        else if(typeof window.refreshHomeData==='function') window.refreshHomeData();
      }
      return typeof oldClose==='function' ? oldClose.apply(this, arguments) : undefined;
    };
  }

  // ---------- 보유 종목: 테이블 구조만 이용 ----------
  function selectHoldingsRows(){
    // 드로어 영역 추정: 우측 패널 내 테이블 tbody
    const drawer = document.querySelector('#drawer-holdings') || document.querySelector('[id*="drawer"][class*="hold"]') || document;
    const tb = drawer.querySelector('table tbody') || document.querySelector('#holdings-table tbody') || document.querySelector('tbody');
    if(!tb) return [];
    return Array.from(tb.querySelectorAll('tr')).filter(tr=>tr.querySelectorAll('input').length>=3);
  }

  function getRowFields(tr){
    // 1열: 티커, 2열: 수량, 3열: 평균매입가($) 로 가정
    const inputs = Array.from(tr.querySelectorAll('input'));
    const [sym, qty, cost] = inputs;
    return {sym, qty, cost};
  }

  function attachCostFormatting(){
    selectHoldingsRows().forEach(tr=>{
      const {cost} = getRowFields(tr);
      if(!cost) return;
      cost.type='text'; cost.setAttribute('inputmode','decimal');
      cost.addEventListener('focus', ()=>{ const n=sanitizeUSD(cost.value); cost.value=n? String(n):''; });
      cost.addEventListener('blur',  ()=>{ const n=sanitizeUSD(cost.value); cost.value=n? nfUSD(n):''; });
    });
  }

  function readHoldingsCompat(){
    const keys=['portfolioHoldings','portfolio','holdings','portfolio_data'];
    for(const k of keys){
      try{
        const raw=localStorage.getItem(k); if(!raw) continue;
        const j=JSON.parse(raw);
        const arr=Array.isArray(j)? j : (j&&Array.isArray(j.holdings)? j.holdings:null);
        if(arr && arr.length) return arr;
      }catch(e){}
    }
    return [];
  }
  function writeHoldingsCompat(arr){
    localStorage.setItem('portfolioHoldings', JSON.stringify(arr));       // 표준
    localStorage.setItem('portfolio', JSON.stringify({holdings:arr}));    // 호환
    localStorage.setItem('holdings', JSON.stringify(arr));                // 호환
  }

  function saveHoldingsFromUI(){
    const rows = selectHoldingsRows();
    const out = [];
    rows.forEach(tr=>{
      const {sym, qty, cost} = getRowFields(tr);
      const s = sym?.value?.trim().toUpperCase();
      const q = parseFloat((qty?.value||'').toString().replace(/,/g,'')) || 0;
      const c = sanitizeUSD(cost?.value||'');
      if(s && q>0 && c>0) out.push({symbol:s, qty:q, cost:c});
    });
    writeHoldingsCompat(out);
    if(typeof window.refreshOverview==='function') window.refreshOverview();
    else if(typeof window.refreshHomeData==='function') window.refreshHomeData();
    console.debug('[Holdings] saved', out);
    return out.length;
  }

  function hookSaveButton(){
    // 1) 기존 "저장" 버튼 강제 활성화 및 클릭 훅
    document.addEventListener('click', (e)=>{
      const btn = e.target.closest('button');
      if(!btn) return;
      if(!/저장/.test(btn.textContent||'')) return;
      // disabled 방지
      btn.disabled = false;
      // 저장 수행
      setTimeout(saveHoldingsFromUI, 0);
    }, true);

    // 2) 드로어 하단에 "강제 저장" 버튼 없으면 추가 (디버그용)
    const drawer = document.querySelector('#drawer-holdings') || document.body;
    if(drawer && !drawer.querySelector('#sp-force-save')){
      const b=document.createElement('button');
      b.id='sp-force-save';
      b.textContent='강제 저장';
      b.style.cssText='position:fixed;right:28px;bottom:92px;z-index:9999;padding:10px 16px;border-radius:8px;background:#10b981;color:#fff;border:0;box-shadow:0 2px 8px rgba(0,0,0,.15);';
      b.onclick=()=>{ const n=saveHoldingsFromUI(); b.textContent = `저장됨 (${n}종목)`; setTimeout(()=>b.textContent='강제 저장',1500); };
      drawer.appendChild(b);
    }
  }

  // ---------- init ----------
  function init(){
    hookCash();
    attachCostFormatting();
    hookSaveButton();
    // 행 추가/드로어 열림 시에도 포맷 다시 연결
    const mo = new MutationObserver(()=>attachCostFormatting());
    mo.observe(document.body, {subtree:true, childList:true, attributes:true});
  }
  document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', init) : init();
})();
