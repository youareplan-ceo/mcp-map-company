import json
from pathlib import Path
import pandas as pd
import streamlit as st
from apps._ui import layout, section, table

APPLICANTS = Path("db/policy_applicants.json")
NOTICES    = Path("db/policy_notices.json")
MATCHES    = Path("db/policy_matches.json")

def _load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8") or "[]")
    except Exception:
        return []

with layout("🗂️ 정책자금 매칭 • MCP", subtitle="신청자/요건/매칭", right_badge="BETA", brand="PolicyPilot"):
    tabs = st.tabs(["📋 신청자", "🧩 매칭", "📰 공고", "🧾 로그"])

    # 📋 신청자
    with tabs[0]:
        section("신청자 목록")
        df = pd.DataFrame(_load(APPLICANTS))
        table(df)

    # 🧩 매칭
    with tabs[1]:
        section("매칭 결과(스텁)")
        df = pd.DataFrame(_load(MATCHES))
        if not df.empty:
            # 신청자 정보 join 예시(표시 편의)
            apps = pd.DataFrame(_load(APPLICANTS))
            if not apps.empty:
                df = df.merge(apps[["id","name","region"]], left_on="applicant_id", right_on="id", how="left")
                df = df.drop(columns=["id"])
        table(df)

    # 📰 공고
    with tabs[2]:
        section("최근 공고(샘플)")
        df = pd.DataFrame(_load(NOTICES))
        table(df)

    # 🧾 로그
    with tabs[3]:
        section("최근 실행 로그")
        logs = sorted(Path("logs").glob("*.log"))
        if logs:
            latest = logs[-1]
            st.caption(f"최근 로그: {latest.name}")
            st.code(latest.read_text(encoding="utf-8")[-8000:], language="bash")
        else:
            st.info("logs 디렉토리에 로그가 아직 없습니다.")
