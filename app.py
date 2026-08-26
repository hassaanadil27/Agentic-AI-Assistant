"""BSDI Project AI Agent - multipage Streamlit application."""
from __future__ import annotations

import logging
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from ui.api_client import get_portfolio
from ui.styles import APP_CSS

_env_path = Path(__file__).resolve().parent / ".env"
if not (_env_path.exists() and "x-rapidapi-key" in _env_path.read_text(encoding="utf-8").casefold()):
    load_dotenv(_env_path)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

st.set_page_config(
    page_title="BSDI Command Center",
    page_icon=":material/monitoring:",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(APP_CSS, unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div class="brand">BSDI Command Center</div>', unsafe_allow_html=True)
    st.markdown('<div class="nav-label">Portfolio intelligence</div>', unsafe_allow_html=True)
    st.caption("Live oversight and agent-assisted review")

st.markdown(
    '<div class="hero"><h1>Portfolio Command Center</h1>'
    '<p>Monitor delivery, investigate risk, and coordinate evidence-based project decisions from one operational workspace.</p></div>',
    unsafe_allow_html=True,
)

try:
    metadata, _, _ = get_portfolio()
except Exception as exc:
    st.error(f"Portfolio service unavailable: {exc}")
    st.info("The interface is ready, but live metrics require the FastAPI service.")
    st.stop()

status_counts = metadata.status_counts
total = metadata.total_projects
completed = int(status_counts.get("Completed", 0))
in_progress = int(status_counts.get("In Progress", 0))

st.markdown('<div class="section-kicker">Portfolio at a glance</div>', unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total projects", f"{total:,}", f"{metadata.districts} districts", delta_color="off")
col2.metric(
    "Portfolio value",
    f"PKR {metadata.total_portfolio_m:,.1f}M",
    f"{metadata.categories} categories",
    delta_color="off",
)
col3.metric("Completed", f"{completed:,}", f"{completed / total:.1%}" if total else "0%")
col4.metric("In progress", f"{in_progress:,}", f"{in_progress / total:.1%}" if total else "0%")

st.markdown('<div class="section-kicker">Operational workspaces</div>', unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)

with col1:
    with st.container(border=True):
        st.markdown("#### Portfolio dashboard")
        st.caption("Compare status, budgets, and district performance.")
        st.page_link("pages/1_dashboard.py", label="Open dashboard", icon=":material/analytics:", width="stretch")

with col2:
    with st.container(border=True):
        st.markdown("#### Query agent")
        st.caption("Ask questions and trace every supporting data step.")
        st.page_link("pages/2_query_agent.py", label="Start analysis", icon=":material/search:", width="stretch")

with col3:
    with st.container(border=True):
        st.markdown("#### Audit agent")
        st.caption("Surface delivery, finance, and data-quality risks.")
        st.page_link("pages/3_audit_agent.py", label="Run audit", icon=":material/policy:", width="stretch")

with col4:
    with st.container(border=True):
        st.markdown("#### Review board")
        st.caption("Prioritize investments with specialist agent evidence.")
        st.page_link("pages/4_review_board.py", label="Open board", icon=":material/groups:", width="stretch")

st.markdown('<div class="section-kicker">System status</div>', unsafe_allow_html=True)
status_col, data_col, model_col = st.columns(3)
status_col.success("Portfolio API connected", icon=":material/check_circle:")
data_col.info(f"{total:,} project records loaded", icon=":material/database:")
model_col.warning("Agent responses follow the configured provider", icon=":material/smart_toy:")
