"""BSDI Project AI Agent — Multi-page Streamlit application."""
from __future__ import annotations

import logging
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

from ui.styles import APP_CSS

_env_path = Path(__file__).resolve().parent / ".env"
# RapidAPI's copied Python example is not dotenv syntax. The provider can
# safely extract its key, while normal key=value files still use dotenv.
if not (_env_path.exists() and "x-rapidapi-key" in _env_path.read_text(encoding="utf-8").casefold()):
    load_dotenv(_env_path)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

st.set_page_config(
    page_title="BSDI Project AI Agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(APP_CSS, unsafe_allow_html=True)


# Main Content
with st.sidebar:
    st.markdown('<div class="brand">🏢 BSDI AI Platform</div>', unsafe_allow_html=True)
    st.divider()
    st.caption("📍 Home")

st.markdown(
    '<div class="hero"><h1>📊 Welcome to BSDI AI Agent</h1><p>An intelligent platform for portfolio analysis, audit, and decision support</p></div>',
    unsafe_allow_html=True
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Projects", "2,847", "+142")
col2.metric("Budget", "PKR 850M", "+12.5%")
col3.metric("Completed", "1,243", "43.6%")
col4.metric("In Progress", "1,341", "47.1%")

st.divider()

st.markdown("### 🚀 Quick Start")

col1, col2, col3, col4 = st.columns(4)

with col1:
    with st.container(border=True):
        st.markdown("#### 🏠 Dashboard")
        st.caption("View portfolio overview and key metrics")
        st.page_link("pages/1_dashboard.py", label="Open Dashboard", icon="🏠", width="stretch")

with col2:
    with st.container(border=True):
        st.markdown("#### 🔍 Query Agent")
        st.caption("Ask natural-language questions about your projects")
        st.page_link("pages/2_query_agent.py", label="Open Query Agent", icon="🔍", width="stretch")

with col3:
    with st.container(border=True):
        st.markdown("#### 🔐 Audit Agent")
        st.caption("Run autonomous audits to find portfolio risks")
        st.page_link("pages/3_audit_agent.py", label="Open Audit Agent", icon="🔐", width="stretch")

with col4:
    with st.container(border=True):
        st.markdown("#### 📋 Review Board")
        st.caption("Multi-agent project prioritization system")
        st.page_link("pages/4_review_board.py", label="Open Review Board", icon="📋", width="stretch")

st.divider()

st.markdown("### 📚 Features")

feature1, feature2, feature3 = st.columns(3)

with feature1:
    st.markdown("**🤖 AI-Powered Analysis**")
    st.caption("Advanced agents provide intelligent insights into your portfolio")

with feature2:
    st.markdown("**📊 Beautiful Visualizations**")
    st.caption("Interactive charts and comprehensive data views")

with feature3:
    st.markdown("**🔐 Comprehensive Audits**")
    st.caption("Automated risk detection and compliance checking")

st.divider()

st.markdown("### 📖 How It Works")

with st.expander("🔍 Query Agent - Ask Natural Questions"):
    st.markdown("""
    The Query Agent lets you ask free-form questions about your project portfolio:
    - **Natural Language**: Ask in your own words
    - **Verified Evidence**: Every answer is backed by data
    - **Visual Insights**: Generate charts automatically
    - **Citation Trail**: See exactly how the answer was derived
    """)

with st.expander("🔐 Audit Agent - Autonomous Risk Detection"):
    st.markdown("""
    Define an audit goal and let the agent create its own verification plan:
    - **Goal-Driven**: You set the audit objective
    - **Independent Execution**: Agent creates and runs checks
    - **Risk Ranking**: Findings are prioritized by importance
    - **Detailed Reports**: Comprehensive audit documentation
    """)

with st.expander("📋 Review Board - Multi-Agent Prioritization"):
    st.markdown("""
    Let finance, delivery, and equity specialists work together:
    - **Budget Envelope**: Set your available funding
    - **Multi-Specialist**: Finance, delivery, and equity agents
    - **Collaborative**: All agents reach consensus
    - **Project Ranking**: Get prioritized recommendations
    """)
