const API = (typeof window !== 'undefined' && window.API_BASE) ? window.API_BASE : 'http://127.0.0.1:8099';

function fmt(v, d=2) {
  if (v === null || v === undefined || Number.isNaN(v)) return "-";
  return Number(v).toFixed(d);
}

async function loadData() {
  try {
    document.getElementById('apiBase').textContent = API;

    const [pnl, reco] = await Promise.all([
      fetch(`${API}/api/v1/portfolio/pnl`).then(r => r.json()),
      fetch(`${API}/api/v1/portfolio/reco`).then(r => r.json()),
    ]);

    const s = pnl.summary || {};
    document.getElementById("summary").innerHTML =
      `<h2>총 손익: ${fmt(s.total_profit)} (${fmt(s.total_profit_pct)}%)</h2>
       <div class="meta">총 원가: ${fmt(s.total_cost)} · 평가금액: ${fmt(s.total_value)} · 기준시각: ${s.asof || "-"}</div>`;

    const map = {};
    (pnl.items || []).forEach(it => map[(it.symbol||'').toUpperCase()] = it);

    let html = "";
    (reco.recommendations || []).forEach(r => {
      const sym = (r.symbol || "").toUpperCase();
      const it = map[sym] || {};
      const pct = it.profit_pct;
      const badge =
        r.action === "trim" ? "🟢 보유익절" :
        r.action === "cut"  ? "🔴 위험" :
        r.action === "add"  ? "🟡 추가매수" :
                              "⚪ 보유";

      html += `<div class="card">
        <div class="card-head">
          <h3>${sym}</h3>
          <span class="badge">${badge}</span>
        </div>
        <div class="row">
          <div>수익률: <b class="${(pct||0)>=0?'pos':'neg'}">${fmt(pct)}%</b></div>
          <div>현재가: ${fmt(it.last_price)} · 매입가: ${fmt(it.buy_price)} · 수량: ${fmt(it.quantity,0)}</div>
        </div>
        <div class="why">사유: ${r.reason || "-"}</div>
      </div>`;
    });

    if (!html) html = `<div class="card">표시할 추천이 없습니다.</div>`;
    document.getElementById("cards").innerHTML = html;

  } catch (e) {
    console.error(e);
    document.getElementById("summary").innerHTML = `<p class="error">API 오류: ${e?.message || e}</p>`;
    document.getElementById("cards").innerHTML = "";
  }
}

window.onload = () => {
  loadData();
  setInterval(loadData, 30000);
};
