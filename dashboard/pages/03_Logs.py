import streamlit as st, pandas as pd, datetime, random
st.set_page_config(page_title="MCP Admin — Logs", layout="wide")
st.title("🪵 Logs (demo)")
levels = ["INFO","WARN","ERROR"]
rows = [
    {"time": (datetime.datetime.now()-datetime.timedelta(minutes=i)).strftime("%H:%M:%S"),
     "level": random.choice(levels), "message": f"Demo log #{i:03d}"}
    for i in range(1,51)
]
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
st.info("Connect to real run logs in subsequent task.")
