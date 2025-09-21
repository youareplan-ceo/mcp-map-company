const API = "http://127.0.0.1:8099";

function fmt(v, d=2) {
  if (v === null || v === undefined || Number.isNaN(v)) return "-";
  return Number(v).toFixed(d);
}

async function loadData() {
  try {
    const [pnl, reco] = await Promise.all([
      fetch(`${API}/api/v1/portfolio/pnl`).then(r => r.json()),
      fetch(`${API}/api/v1/portfolio/reco`).then(r => r.json()),
    ]);

    // summary (API 키: total_profit, total_profit_pct)
    const s = pnl.summary || {};
    document.getElementById("summary").innerHTML =
      `<h2>총 손익: ${fmt(s.total_profit)} (${fmt(s.total_profit_pct)}%)</h2>
       <div>총 원가: ${fmt(s.total_cost)} · 평가금액: ${fmt(s.total_value)} · 기준시각: ${s.asof || "-"}</div>`;

    // 종목별 수익률은 PnL.items에 있음 → 심볼로 조인
    const pnlMap = {};
    (pnl.items || []).forEach(it => { pnlMap[(it.symbol||"").toUpperCase()] = it; });

    let html = "";
    (reco.recommendations || []).forEach(r => {
      const sym = (r.symbol || "").toUpperCase();
      const pit = pnlMap[sym] || {};
      const pct = pit.profit_pct;
      const badge =
        r.action === "trim" ? "🟢 익절" :
        r.action === "cut"  ? "🔴 손절" :
        r.action === "add"  ? "🟡 분할매수" :
                              "⚪ 보유";

      html += `<div class="card">
        <h3>${sym} <span style="font-size:0.8em">${badge}</span></h3>
        <p>수익률: <b>${fmt(pct)}%</b></p>
        <p>현재가: ${fmt(pit.last_price)} · 매입가: ${fmt(pit.buy_price)} · 수량: ${fmt(pit.quantity,0)}</p>
        <p style="color:#666">사유: ${r.reason || "-"}</p>
      </div>`;
    });

    if (!html) html = `<div class="card">표시할 추천이 없습니다.</div>`;
    document.getElementById("cards").innerHTML = html;

  } catch (e) {
    console.error(e);
    document.getElementById("summary").innerHTML =
      `<p style="color:red">API 오류: ${e?.message || e}</p>`;
    document.getElementById("cards").innerHTML = "";
  }
}

window.onload = () => {
  loadData();
  setInterval(loadData, 30000); // 30초 자동 갱신
};
