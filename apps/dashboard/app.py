import os, json
import duckdb
import streamlit as st
from pathlib import Path
from datetime import datetime

DB_PATH = "duckdb/stocks.db"
SUMMARY_JSON = Path("db/stocks_summary.json")

st.set_page_config(page_title="StockPilot Dashboard", layout="wide")

st.title("🛰️ StockPilot • MCP Map Dashboard")

# --- DB 연결 ---
con = None
if Path(DB_PATH).exists():
    try:
        con = duckdb.connect(DB_PATH, read_only=True)
    except Exception as e:
        st.error(f"DuckDB 연결 실패: {e}")

# --- 탭 구성 ---
tabs = st.tabs(["📊 요약", "🧭 시그널", "📰 뉴스", "🧾 로그"])

# 📊 요약 탭
with tabs[0]:
    st.subheader("종목별 요약 (시그널 × 뉴스Top)")
    if SUMMARY_JSON.exists():
        try:
            data = json.loads(SUMMARY_JSON.read_text(encoding="utf-8") or "[]")
        except Exception as e:
            st.error(f"요약 JSON 로드 실패: {e}")
            data = []
        if data:
            # 심볼 필터
            symbols = sorted(list({r.get("symbol") for r in data if r.get("symbol")}))
            sym = st.selectbox("심볼", ["(전체)"] + symbols)
            rows = data if sym == "(전체)" else [r for r in data if r.get("symbol")==sym]
            st.write(rows)
        else:
            st.info("요약 파일이 비어 있습니다. 플로우 실행 후 확인하세요.")
    else:
        st.info("요약 파일이 없습니다. 먼저 플로우를 실행해 주세요.")

# 🧭 시그널 탭
with tabs[1]:
    st.subheader("최근 시그널 (DuckDB)")
    if con:
        try:
            q = """
            SELECT symbol, ts, decision, close, rationale
            FROM signals
            ORDER BY ts DESC
            LIMIT 200
            """
            df = con.execute(q).df()
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.info("signals 테이블이 아직 없습니다. 플로우를 먼저 실행하세요.")
            st.caption(f"오류: {e}")
    else:
        st.info("DuckDB가 아직 없습니다.")

# 📰 뉴스 탭
with tabs[2]:
    st.subheader("최근 뉴스 (DuckDB)")
    if con:
        try:
            q = """
            SELECT symbol, ts, score, source, title, url
            FROM news
            ORDER BY ts DESC
            LIMIT 200
            """
            df = con.execute(q).df()
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.info("news 테이블이 아직 없습니다. news_daily 플로우 실행 후 확인하세요.")
            st.caption(f"오류: {e}")
    else:
        st.info("DuckDB가 아직 없습니다.")

# 🧾 로그 탭
with tabs[3]:
    st.subheader("최근 실행 로그")
    logs_dir = Path("logs")
    if logs_dir.exists():
        files = sorted(logs_dir.glob("*.log"))
        if not files:
            st.info("로그 파일이 없습니다.")
        else:
            latest = files[-1]
            st.caption(f"최근 로그: {latest.name}")
            try:
                st.code(latest.read_text(encoding="utf-8")[-8000:], language="bash")
            except Exception as e:
                st.error(f"로그 로드 실패: {e}")
    else:
        st.info("logs 디렉토리가 없습니다.")
