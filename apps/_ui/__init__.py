from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import streamlit as st
import pandas as pd

def set_page(title: str, icon: str="🛰️"):
    st.set_page_config(page_title=title, page_icon=icon, layout="wide")

def header(title: str, subtitle: str=None, right_badge: str=None):
    c1, c2 = st.columns([0.8, 0.2])
    with c1:
        st.markdown(f"### {title}")
        if subtitle:
            st.caption(subtitle)
    with c2:
        if right_badge:
            st.markdown(
                f"<div style='text-align:right; padding-top:8px;'>"
                f"<span style='background:#222; padding:6px 10px; border-radius:8px;'>{right_badge}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
    st.markdown("---")

def sidebar(brand="MCP Map", tips=None):
    with st.sidebar:
        st.markdown(f"## {brand}")
        st.caption("유아플랜 • MCP Control Tower")
        if tips:
            with st.expander("💡 Tips"):
                for t in tips:
                    st.write(f"- {t}")
        st.markdown(
            "<div style='opacity:.6; font-size:12px;'>"
            f"Last loaded: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            "</div>",
            unsafe_allow_html=True
        )

def table(df: pd.DataFrame, height: int=420):
    if df is None or len(df) == 0:
        st.info("표시할 데이터가 없습니다.")
        return
    st.dataframe(df, height=height, width='stretch')

def section(title: str, desc: str=None):
    st.markdown(f"#### {title}")
    if desc:
        st.caption(desc)   # ✅ 들여쓰기 고침

def footer():
    st.markdown("---")
    st.caption("© YouAPlan • MCP Map — built for 회장님")

@contextmanager
def layout(title: str, subtitle: str=None, right_badge: str=None, brand: str="MCP Map"):
    set_page(title)
    header(title, subtitle, right_badge)
    sidebar(brand=brand, tips=[
        "좌측 상단 ⟳ 로 새로고침",
        "데이터 갱신: bin/flow …",
        "문제시 logs/ 확인"
    ])
    try:
        yield
    finally:
        footer()
