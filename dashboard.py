import os, requests, pandas as pd, streamlit as st

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8099")
USER_ID  = os.getenv("USER_ID", "default")

st.set_page_config(page_title="StockPilot Dashboard", layout="wide")
st.title("📊 StockPilot Dashboard")

# --- 상단 컨트롤 ---
col0, col1, col2, col3 = st.columns([1,1,1,2])
with col0: user_id = st.text_input("User ID", value=USER_ID)
with col1: api_base = st.text_input("API Base", value=API_BASE)
with col2:
    if st.button("🔄 새로고침"):
        st.experimental_rerun()

# --- helpers ---
def get_json(path):
    url = f"{api_base}{path}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)

def post_json(path, payload):
    url = f"{api_base}{path}"
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)

# --- 섹션: Holdings ---
st.subheader("🧺 Holdings (보유 종목)")
hold_json, err = get_json(f"/api/v1/portfolio/holdings?user_id={user_id}")
if err:
    st.error(f"Holdings 불러오기 오류: {err}")
else:
    items = hold_json.get("items", [])
    if items:
        st.dataframe(pd.DataFrame(items))
    else:
        st.info("보유 종목이 없습니다. 아래 입력으로 추가해보세요.")

with st.expander("➕ 보유 추가/갱신 (Upsert)"):
    c1, c2, c3, c4 = st.columns(4)
    with c1: sym = st.text_input("티커", value="NVDA")
    with c2: sh = st.number_input("수량", value=5.0, min_value=0.0)
    with c3: cost = st.number_input("평단", value=120.0, min_value=0.0)
    with c4:
        if st.button("저장"):
            res, err = post_json("/api/v1/portfolio/upsert",
                                 {"user_id": user_id, "symbol": sym, "shares": sh, "avg_cost": cost})
            if err: st.error(f"저장 실패: {err}")
            else: st.success(f"저장 완료: {res}")

# --- 섹션: Recommendations ---
st.subheader("🤖 Recommendations (추천)")
reco_json, err = get_json(f"/api/v1/stock/recommendations?user_id={user_id}")
if err:
    st.error(f"추천 불러오기 오류: {err}")
else:
    meta = reco_json.get("meta", {})
    st.caption(f"임계치 → recommend:{meta.get('recommend_threshold')} / add_more:{meta.get('add_more_threshold')} / warn:{meta.get('warn_threshold')}")

    cols = st.columns(2)
    existing = (reco_json.get("recommendations", {}) or {}).get("existing", [])
    new = (reco_json.get("recommendations", {}) or {}).get("new", [])

    with cols[0]:
        st.markdown("**보유 종목에 대한 제안 (existing)**")
        if existing:
            st.dataframe(pd.DataFrame(existing))
        else:
            st.info("보유 종목 관련 제안 없음")

    with cols[1]:
        st.markdown("**신규 종목 제안 (new)**")
        if new:
            st.dataframe(pd.DataFrame(new))
        else:
            st.info("신규 제안 없음")

# ─────────────────────────────────────────────────────────────────────────────
# Alerts
st.subheader("🔔 Alerts (알림)")
alerts_json, err = get_json(f"/api/v1/alerts/list?user_id={user_id}")
if err:
    st.error(f"알림 불러오기 오류: {err}")
else:
    alerts = alerts_json.get("alerts", [])
    if alerts:
        df_alerts = pd.DataFrame(alerts)
        # 최신순 정렬
        if "created_at" in df_alerts.columns:
            df_alerts = df_alerts.sort_values("created_at", ascending=False)
        st.dataframe(df_alerts, use_container_width=True)
    else:
        st.info("알림이 없습니다.")

st.caption("※ 임계치/가중치는 백엔드 환경변수(RECOMMEND_THRESHOLD, ADD_MORE_THRESHOLD, "
           "WARN_THRESHOLD, RECO_W_TREND/RSI/MOM)로 제어합니다.")
