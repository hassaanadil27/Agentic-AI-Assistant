"""Balochistan Special Development Initiative AI Agent landing page."""
from __future__ import annotations

from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

_env = Path(__file__).resolve().parent / ".env"
if _env.exists():
    load_dotenv(_env, override=True)

from ui.api_client import get_portfolio
from ui.components import render_footer, render_header, render_section, render_sidebar_info, render_stat, render_workflow_card
from ui.styles import APP_CSS

st.set_page_config(page_title="BALOCHISTAN SPECIAL DEVELOPMENT INITIATIVE AI Agent", page_icon="🏛️", layout="wide", initial_sidebar_state="expanded")
st.markdown(APP_CSS, unsafe_allow_html=True)
render_sidebar_info()

try:
    metadata, _, _ = get_portfolio()
except Exception as exc:
    st.error("The portfolio could not be loaded. Confirm that the backend or local dataset is available.")
    with st.expander("Technical details"):
        st.code(str(exc))
    st.stop()

total = metadata.total_projects
completed = int(metadata.status_counts.get("Completed", 0))
in_progress = int(metadata.status_counts.get("In Progress", 0))
not_started = int(metadata.status_counts.get("Not Started", 0))

render_header(
    "BALOCHISTAN SPECIAL DEVELOPMENT INITIATIVE AI Agent",
    "A single evidence-led workspace to explore the development portfolio, investigate delivery risk, and make defensible funding decisions.",
    "Portfolio ready",
    "green",
)

cols = st.columns(4)
metrics = [
    ("Total schemes", f"{total:,}", f"{metadata.districts} districts · {metadata.categories} sectors", "Portfolio", "blue"),
    ("Portfolio value", f"PKR {metadata.total_portfolio_m / 1000:,.1f}B", f"PKR {metadata.total_portfolio_m:,.0f} million", "Allocation", "blue"),
    ("Completed", f"{completed:,}", f"{completed / max(total, 1):.1%} of all schemes", "Delivered", "green"),
    ("Needs action", f"{not_started:,}", f"Plus {in_progress:,} schemes in progress", "Not started", "amber"),
]
for column, values in zip(cols, metrics):
    with column:
        render_stat(*values)

render_section("Choose your workflow", "Start with the question you need to answer; each workspace stays grounded in the same portfolio data.")
cards = [
    ("▦", "Explore the portfolio", "Filter schemes, compare delivery status, and inspect district or sector allocation.", "pages/1_Overview_and_Explorer.py", "Open explorer"),
    ("✦", "Ask the AI assistant", "Use plain language for exact counts, costs, comparisons, and ranked project questions.", "pages/2_AI_Assistant.py", "Start a conversation"),
    ("△", "Run a risk audit", "Scan for missing accountability fields, tender mismatches, delivery gaps, and cost outliers.", "pages/3_Risk_Audit.py", "Open risk audit"),
    ("◎", "Allocate a budget", "Have Finance, Delivery, and Equity specialists build a budget-safe funding shortlist.", "pages/4_Budget_Review_Board.py", "Open review board"),
]
row_a = st.columns(2)
row_b = st.columns(2)
for column, (icon, title, copy, path, label) in zip([*row_a, *row_b], cards):
    with column:
        render_workflow_card(icon, title, copy)
        st.page_link(path, label=f"{label}  →", width="stretch")
        st.write("")

render_section("Built for explainable decisions", "The model assists with planning and narrative; source-of-truth operations remain deterministic.")
explain_cols = st.columns(3)
explainers = [
    ("01", "Calculated, not guessed", "Counts, sums, rankings, and budget limits are executed in Python against the Excel portfolio."),
    ("02", "Traceable evidence", "Agent findings retain source tools, affected project IDs, and a public action trace."),
    ("03", "Works without an API", "Offline demo mode still runs the real tools and dataset using a deterministic investigation plan."),
]
for column, (number, title, copy) in zip(explain_cols, explainers):
    with column:
        with st.container(border=True):
            st.caption(number)
            st.markdown(f"**{title}**")
            st.caption(copy)

render_footer()
