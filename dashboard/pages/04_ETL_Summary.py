import streamlit as st
import pathlib, json, datetime

st.set_page_config(page_title="MCP Admin — ETL Summary", layout="wide")
st.title("📊 ETL Summary")
st.caption("자동 생성된 ETL 결과 요약")

root = pathlib.Path(__file__).resolve().parents[2]
last_run = root / "data" / "etl" / "last_run.json"

if last_run.exists():
    try:
        meta = json.loads(last_run.read_text())
        st.json(meta)
        ts = meta.get("generated_at", "unknown")
        holdings_rows = meta.get("holdings_rows", 0)
        tables = meta.get("tables", [])
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Last ETL", ts)
        col2.metric("Holdings Rows", holdings_rows)
        col3.metric("Tables", len(tables))
        
        if ts != "unknown":
            st.success(f"✅ ETL 실행 완료: {ts}")
            
    except Exception as e:
        st.error(f"요약 읽기 실패: {e}")
else:
    st.warning("`data/etl/last_run.json` 이 없습니다. code4에서 `make etl-all` 실행 후 확인하세요.")
    
    with st.expander("ETL 실행 가이드"):
        st.code("""
# ETL 전체 실행
make etl-all

# 개별 단계
make db-init      # DB 초기화
make db-ingest    # 데이터 수집
make db-health    # 상태 확인
make etl-summary  # 요약 생성
        """)
