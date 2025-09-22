import streamlit as st, pandas as pd, numpy as np, time
st.set_page_config(page_title="MCP Admin — Metrics", layout="wide")
st.title("📈 Metrics (demo)")
x = pd.date_range(end=pd.Timestamp.now(), periods=24, freq="H")
y = np.abs(np.random.randn(24)).cumsum()
df = pd.DataFrame({"time": x, "value": y})
st.line_chart(df.set_index("time"))
st.bar_chart(df.tail(8).set_index("time"))
st.success("Demo metrics plotted. Wire to real data in Sprint-2 next step.")
