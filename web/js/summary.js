const API = "http://127.0.0.1:8099";
const INTERVAL_MS = 30_000;

async function fetchSummary(exchange){
  const res = await fetch(`${API}/api/v1/stock/signals?exchange=${exchange}&limit=40&batch_size=40`);
  if(!res.ok) throw new Error(`HTTP ${res.status}`);
  const j = await res.json();
  return j.summary || {};
}

function tile(title, s){
  return `
  <div style="padding:12px 16px;border:1px solid #ddd;border-radius:8px;min-width:260px">
    <h3 style="margin:0 0 8px">${title}</h3>
    <div>BUY: <b>${s.buy||0}</b> · SELL: <b>${s.sell||0}</b> · HOLD: <b>${s.hold||0}</b></div>
    <div style="font-size:12px;color:#555;margin-top:6px">rules: ${
      Object.entries(s.reasons||{}).map(([k,v])=>`${k}:${v}`).join(' · ') || '-'
    }</div>
    <div style="font-size:12px;color:#777;margin-top:4px">t=${s.duration_ms||0}ms · mode=${s.mode||''} · batch=${s.batch_size||'-'}</div>
  </div>`;
}

async function renderSummaryOnce(){
  const root = document.getElementById('summary-root');
  const status = document.getElementById('summary-status');
  if(!root || !status) return;
  status.textContent = "갱신중…";
  status.style.color = "#666";
  try{
    const [us, kr] = await Promise.all([fetchSummary('NASDAQ'), fetchSummary('KRX')]);
    root.innerHTML = `
      <div style="display:flex;gap:16px;flex-wrap:wrap">
        ${tile('NASDAQ (40)', us)}
        ${tile('KRX (40)', kr)}
      </div>`;
    status.textContent = `마지막 갱신: ${new Date().toLocaleTimeString()} (자동 30초)`;
    status.style.color = "#0a0";
  }catch(e){
    status.textContent = `에러: ${e.message}`;
    status.style.color = "#d00";
  }
}

function bindControls(){
  const btn = document.getElementById('summary-refresh');
  if(btn){ btn.addEventListener('click', renderSummaryOnce); }
  setInterval(renderSummaryOnce, INTERVAL_MS);
}

document.addEventListener('DOMContentLoaded', () => {
  bindControls();
  renderSummaryOnce();
});
