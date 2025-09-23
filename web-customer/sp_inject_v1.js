(function(){
  /* ===== 공통 유틸 ===== */
  function nfUSD(n){ try { return new Intl.NumberFormat('en-US',{minimumFractionDigits:2, maximumFractionDigits:2}).format(n);}catch(e){return String(n)}}
  function sanitizeUSD(s){ if(s==null) return 0; let v=String(s).replace(/[, ]/g,'').replace(/[^0-9.]/g,''); const p=v.split('.'); if(p.length>2){ v=p.shift()+'.'+p.join(''); } return v?parseFloat(v):0; }
  function sanitizeInt(s){ const v=String(s||'').replace(/[^\d]/g,''); return v?parseInt(v,10):0; }
  function forceTypes(){
    document.querySelectorAll('#cash-krw,#cash-usd,input.cost').forEach(el=>el.setAttribute('type','text'));
    document.getElementById('cash-krw')?.setAttribute('inputmode','numeric');
    document.getElementById('cash-usd')?.setAttribute('inputmode','decimal');
    document.querySelectorAll('input.cost').forEach(el=>el.setAttribute('inputmode','decimal'));
  }

  /* ===== 현금 드로어 ===== */
  function hookCash(){
    const krw=document.getElementById('cash-krw');
    const usd=document.getElementById('cash-usd');
    if(!krw||!usd) return;

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

  /* ===== 보유 종목 호환 저장 ===== */
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

  /* ===== 보유 종목 드로어 ===== */
  function hookHoldings(){
    const drawer=document.getElementById('drawer-holdings');
    const tbodySel='#holdings-table tbody';

    function attachCostFormat(tb){
      tb.querySelectorAll('input.cost').forEach(inp=>{
        inp.setAttribute('type','text'); inp.setAttribute('inputmode','decimal');
        inp.addEventListener('focus', ()=>{ const n=sanitizeUSD(inp.value); inp.value=n? String(n):''; });
        inp.addEventListener('blur',  ()=>{ const n=sanitizeUSD(inp.value); inp.value=n? nfUSD(n):''; });
      });
    }
    function load(){
      const tb=document.querySelector(tbodySel); if(!tb) return;
      // 기존 행 유지, 값만 포맷 훅 연결
      attachCostFormat(tb);
    }

    if(drawer){
      const obs=new MutationObserver(()=>{ if(getComputedStyle(drawer).right==='0px'){ forceTypes(); load(); } });
      obs.observe(drawer,{attributes:true, attributeFilter:['class','style']});
    }

    // 저장 버튼 자동 인식 (id 없고 텍스트가 '저장'이어도 작동)
    document.addEventListener('click',(e)=>{
      const btn=e.target?.closest('button'); if(!btn) return;
      if(!btn.closest('#drawer-holdings')) return;
      if(btn.id==='holdings-save' || /저장/.test(btn.textContent||'')){
        try{
          const rows=[...document.querySelectorAll(tbodySel+' tr')];
          const out=[];
          rows.forEach(tr=>{
            const s=tr.querySelector('.sym')?.value?.trim().toUpperCase();
            const q=parseFloat((tr.querySelector('.qty')?.value||'').toString().replace(/,/g,''))||0;
            const c=sanitizeUSD(tr.querySelector('.cost')?.value||'');
            if(s && q>0 && c>0) out.push({symbol:s, qty:q, cost:c});
          });
          writeHoldingsCompat(out);
          if(typeof window.refreshOverview==='function') window.refreshOverview();
          else if(typeof window.refreshHomeData==='function') window.refreshHomeData();
        }catch(err){ console.warn('holdings save failed', err); }
      }
    }, true);
  }

  document.addEventListener('DOMContentLoaded', function(){
    forceTypes();
    hookCash();
    hookHoldings();
  });
})();
