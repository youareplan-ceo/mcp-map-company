async function fetchReco(kind="recommendations"){
  const r = await fetch(`http://127.0.0.1:8099/api/v1/stock/`+kind+`?exchange=NASDAQ&limit=5`);
  if(!r.ok) return {items:[]};
  return await r.json();
}
function renderList(title, items){
  if(!items || !items.length){
    return `<div style="padding:12px;border:1px solid #ddd;border-radius:8px;min-width:260px">
      <h3 style="margin:0 0 8px">${title}</h3>
      <div style="color:#777">현재 추천 없음</div>
    </div>`;
  }
  return `<div style="padding:12px;border:1px solid #ddd;border-radius:8px;min-width:260px">
    <h3 style="margin:0 0 8px">${title}</h3>
    <ul style="margin:0;padding-left:18px">
      ${items.map(x=>`<li><b>${x.symbol}</b> · score=${x.score?.toFixed?.(2)??'-'}<br><span style="font-size:12px;color:#555">${(x.why||[]).join(' · ')}</span></li>`).join('')}
    </ul></div>`;
}
async function renderReco(){
  const root = document.getElementById('reco-root');
  if(!root) return;
  try{
    const reco = await fetchReco("recommendations");
    const warn = {items: []}; // 다음 배치에서 /stock/warnings 등으로 분리 가능
    root.innerHTML = `<div style="display:flex;gap:16px;flex-wrap:wrap">
      ${renderList('오늘의 추천(Top 5)', reco.items)}
      ${renderList('경고(Top 5)', warn.items)}
    </div>`;
  }catch(e){
    root.innerHTML = `<div style="color:#d00">추천 영역 오류: ${e.message}</div>`;
  }
}
document.addEventListener('DOMContentLoaded', renderReco);
