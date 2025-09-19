import os
import duckdb
import pandas as pd
import altair as alt
import streamlit as st
import requests

API = "http://localhost:8088"
DB_PATH = os.getenv("SP_DB_PATH", "data/stock_signals.duckdb")

st.set_page_config(page_title="StockPilot Signals", layout="wide")
st.title("📈 StockPilot — Latest Signals")

# --- DB 연결 보장 ---
if not os.path.exists(DB_PATH):
    st.error(f"DB가 없습니다: {DB_PATH}")
    st.stop()
con = duckdb.connect(DB_PATH)

# --- 태그 테이블 보장 ---
con.execute("""
CREATE TABLE IF NOT EXISTS tags(
  ticker     VARCHAR PRIMARY KEY,
  status     VARCHAR,
  note       VARCHAR,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")

# --- 사이드바 컨트롤 ---
with st.sidebar:
    st.header("🔎 Filters")
    limit = st.slider("Limit", 10, 500, 100, step=10)
    min_rsi = st.number_input("Min RSI", value=0.0, step=1.0)
    max_rsi = st.number_input("Max RSI", value=100.0, step=1.0)
    min_atr = st.number_input("Min ATR%", value=0.0, step=0.1)
    max_atr = st.number_input("Max ATR%", value=100.0, step=0.1)
    sig_multi = st.multiselect("Signal", ["BUY","WATCH","TAKE_PROFIT","SELL"], default=[])

    tag_filter = st.selectbox("Tag 필터", ["(전체)","관심","관망","제외"], index=0)

# --- API에서 최신 시그널 가져오기 ---
try:
    params={"limit": limit, "min_rsi": min_rsi, "max_rsi": max_rsi, "min_atr": min_atr, "max_atr": max_atr}
    for sgl in sig_multi:
        params.setdefault("signal", []).append(sgl)
    r = requests.get(f"{API}/signals/latest", params=params, timeout=5)
    data = r.json()
except Exception as e:
    st.error(f"API 오류: {e}")
    st.stop()

run_id = data.get("run_id")
signals = pd.DataFrame(data.get("signals", []))
if signals.empty:
    st.info("신호가 없습니다. 배치를 먼저 실행하세요.")
    st.stop()

# --- 태그 조인 ---
tags_df = con.execute("SELECT * FROM tags").fetchdf()
if tags_df.empty:
    tags_df = pd.DataFrame(columns=["ticker","status","note","updated_at"])

merged = signals.merge(tags_df[["ticker","status","note"]], on="ticker", how="left")

# --- 태그 필터 적용 ---
if tag_filter != "(전체)":
    merged = merged[merged["status"] == tag_filter]

# --- 상단 메트릭 ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("표시 종목 수", len(merged))
col2.metric("평균 RSI14", f"{merged['rsi14'].mean():.1f}" if not merged.empty else "-")
col3.metric("평균 ATR%", f"{merged['atr_pct'].mean():.2f}" if not merged.empty else "-")
col4.metric("평균 종가", f"{merged['last_close'].mean():.2f}" if not merged.empty else "-")

# --- 목록 테이블 ---
st.subheader("📄 종목 목록")
st.dataframe(
    merged.sort_values(["status","signal","rsi14","last_close"], ascending=[True,True,False,False]),
    width="stretch"   # Streamlit 경고 대응(use_container_width → width)
)

# --- 산점도 ---
st.subheader("📈 RSI vs ATR% (버블=AvgVol20)")
chart_df = merged.dropna(subset=["rsi14","atr_pct"]).copy()
if not chart_df.empty:
    chart_df["avg_vol20"] = chart_df["avg_vol20"].fillna(0)
    scat = (
        alt.Chart(chart_df)
        .mark_circle()
        .encode(
            x=alt.X("rsi14:Q", title="RSI14"),
            y=alt.Y("atr_pct:Q", title="ATR %"),
            size=alt.Size("avg_vol20:Q", title="Avg Vol(20)"),
            color=alt.Color("signal:N", title="Signal"),
            tooltip=["ticker","last_close","rsi14","atr_pct","avg_vol20","signal","status","note"]
        )
        .interactive()
    )
    st.altair_chart(scat, use_container_width=True)
else:
    st.info("차트를 그릴 데이터가 부족합니다.")

# --- 상세 & 태깅 UI ---
st.subheader("🔍 종목 상세 & 태깅")
tick = st.selectbox("티커 선택", merged["ticker"].tolist())
row = merged[merged["ticker"] == tick].iloc[0]

# 숫자 포맷 안전 처리
fmt = lambda v, f: "-" if pd.isna(v) else f.format(v)
last_close_str = fmt(row.get("last_close"), "{:.2f}")
rsi_str        = fmt(row.get("rsi14"), "{:.2f}")
atr_str        = fmt(row.get("atr_pct"), "{:.2f}")
fast_str       = "-" if pd.isna(row.get("fast")) else str(int(row.get("fast")))
slow_str       = "-" if pd.isna(row.get("slow")) else str(int(row.get("slow")))
avgvol_str     = "-" if pd.isna(row.get("avg_vol20")) else str(int(row.get("avg_vol20")))

st.markdown(
    f"""
**{tick}**
- 종가: `{last_close_str}`  |  RSI14: `{rsi_str}`  |  ATR%: `{atr_str}`
- Fast/Slow: `{fast_str}/{slow_str}`  |  AvgVol20: `{avgvol_str}`
- Signal: `{row.get('signal')}`
- 현재 태그: `{row.get('status') if pd.notna(row.get('status')) else '-'}`
- 메모: `{row.get('note') if pd.notna(row.get('note')) else ''}`
"""
)

st.divider()
st.markdown("### 🏷️ 태그/메모 저장")

colA, colB = st.columns([1,2])
with colA:
    new_status = st.selectbox("태그", ["관심","관망","제외"], index=0)
with colB:
    new_note = st.text_input("메모", value=row.get("note") if pd.notna(row.get("note")) else "")

btn1, btn2 = st.columns([1,1])
saved_msg = st.empty()

def upsert_tag(ticker: str, status: str, note: str):
    con.execute("""
    MERGE INTO tags AS t
    USING (SELECT ? AS ticker, ? AS status, ? AS note) AS s
    ON t.ticker = s.ticker
    WHEN MATCHED THEN
      UPDATE SET status=s.status, note=s.note, updated_at=CURRENT_TIMESTAMP
    WHEN NOT MATCHED THEN
      INSERT (ticker, status, note, updated_at)
      VALUES (s.ticker, s.status, s.note, CURRENT_TIMESTAMP);
    """, [ticker, status, note])

def delete_tag(ticker: str):
    con.execute("DELETE FROM tags WHERE ticker = ?", [ticker])

with btn1:
    if st.button("💾 저장"):
        upsert_tag(tick, new_status, new_note)
        saved_msg.success(f"{tick} 저장 완료 ({new_status})")
        st.experimental_rerun()

with btn2:
    if st.button("🗑️ 태그 삭제"):
        delete_tag(tick)
        saved_msg.info(f"{tick} 태그 삭제 완료")
        st.experimental_rerun()

st.caption("※ 태그는 종목 단위로 저장됩니다(런 무관). 필터에서 '관심/관망/제외'로 뷰를 좁힐 수 있습니다.")
