import streamlit as st, datetime
st.set_page_config(page_title="MCP Admin — Overview", layout="wide")
st.title("📊 MCP Admin — Overview")
st.caption("Generated: " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
col1, col2, col3 = st.columns(3)
col1.metric("System", "OK ✅")
col2.metric("Branch", "sprint2/dashboard-panels")
col3.metric("Build", "Scaffold v2")
st.markdown("""---
### Links
- Sprint-2 Dashboard PR: #21
- Sprint-1 #14 Batch-2 PR: #22
""")
