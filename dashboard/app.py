import streamlit as st
import datetime

st.set_page_config(page_title="MCP Admin Dashboard", layout="wide")

st.title("📊 MCP Admin Dashboard (Sprint-2 Scaffold)")
st.markdown("이 화면은 Sprint-2용 **대시보드 뼈대**입니다. 기능은 추후 연결됩니다.")

col1, col2 = st.columns(2)
with col1:
    st.metric("Health", "OK ✅")
    st.metric("Active Branch", "sprint2/dashboard-scaffold")
with col2:
    st.write("Generated at:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

st.info("추가 패널(로그, 지표, 알림)은 Sprint-2 후속 단계에서 연결 예정.")
