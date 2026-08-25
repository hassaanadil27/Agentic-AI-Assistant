"""Track C - Multi-Agent Review Board Page."""
import logging
from pathlib import Path
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from agents.llm_provider import get_provider
from models.messages import FinalReport, AgentReport
from orchestration.state import load_latest_run
from ui.api_client import get_portfolio, run_review
from ui.styles import APP_CSS

_env_path = Path(__file__).resolve().parent.parent / ".env"
if not (_env_path.exists() and "x-rapidapi-key" in _env_path.read_text(encoding="utf-8").casefold()):
    load_dotenv(_env_path)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

st.markdown(APP_CSS, unsafe_allow_html=True)

def init_state():
    if "review_result" not in st.session_state:
        saved_review = load_latest_run()
        if saved_review:
            report = FinalReport.model_validate(saved_review["final_report"])
            specialists = {name: AgentReport.model_validate(value) for name, value in saved_review.get("specialist_reports", {}).items()}
            st.session_state.review_result = (report, saved_review.get("activity_log", []), specialists, "saved run")


def render_activity(lines: list[str]) -> None:
    """Show execution timeline."""
    rows = []
    for number, raw in enumerate(lines, 1):
        agent, message = "System", raw
        if raw.startswith("[") and "]" in raw:
            agent, message = raw[1:].split("]", 1)
            message = message.strip()
        prefix, separator, detail = message.partition(":")
        stage = prefix if separator and prefix in {"PLAN", "ACT", "OBSERVE", "REASON", "STOP"} else "Update"
        description = detail.strip() if stage != "Update" else message
        description = description.replace("_", " ")
        rows.append({"Step": number, "Agent": agent, "Stage": stage.title(), "Details": description})
    if rows:
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


init_state()
provider, is_demo = get_provider()
provider_label = {
    "HuggingFaceProvider": "Hugging Face",
    "RapidAPIProvider": "RapidAPI",
    "GrokProvider": "Grok",
}.get(provider.__class__.__name__, "Demo")

# Header
st.markdown(
    '<div class="hero"><h1>📋 Multi-Agent Review Board</h1><p>Finance, delivery, and equity specialists collaboratively prioritize projects within a budget envelope.</p></div>',
    unsafe_allow_html=True
)

if is_demo:
    st.info("🟠 Demo Mode Active - Limited functionality")
else:
    st.caption(f"🔌 Connected to {provider_label} · {provider.model_name}")

# Portfolio Overview
st.markdown("### 📊 Portfolio Overview")

with st.spinner("Loading portfolio data…"):
    meta, district_rows, category_rows = get_portfolio()

col1, col2, col3, col4 = st.columns(4)
col1.metric("📦 Total Projects", f"{meta.total_projects:,}", "")
col2.metric("💰 Portfolio Value", f"PKR {meta.total_portfolio_m:,.0f}M", "")
col3.metric("🗺️ Districts", meta.districts, "")
col4.metric("📂 Categories", meta.categories, "")

st.divider()

# Portfolio Analysis Tabs
tab1, tab2 = st.tabs(["📈 Breakdown by Location & Category", "🔍 Data Quality Report"])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Budget by District (Top 15)**")
        districts_df = pd.DataFrame(district_rows).sort_values("total_budget_m", ascending=False).head(15)
        st.bar_chart(districts_df.set_index("district")["total_budget_m"])
    
    with col2:
        st.markdown("**Budget by Category**")
        categories_df = pd.DataFrame(category_rows).sort_values("total_budget_m", ascending=False)
        st.bar_chart(categories_df.set_index("category")["total_budget_m"])

with tab2:
    from ui.api_client import get_quality
    quality = get_quality()
    total = max(quality.total_rows, 1)
    
    st.markdown("**Data Completeness Metrics**")
    col1, col2, col3 = st.columns(3)
    col1.metric("Projects Reviewed", f"{quality.total_rows:,}", "")
    col2.metric("Missing Contractor", f"{quality.missing_contractor:,}", f"{quality.missing_contractor/total:.1%}")
    col3.metric("Missing XEN", f"{quality.missing_xen:,}", f"{quality.missing_xen/total:.1%}")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Missing Start Date", f"{quality.missing_work_started:,}", f"{quality.missing_work_started/total:.1%}")
    col2.metric("Invalid Cost", f"{quality.invalid_cost_count:,}", "")
    col3.metric("Invalid Progress", f"{quality.invalid_progress_count:,}", "")
    
    if quality.duplicate_global_ids:
        st.warning(f"⚠️ {len(quality.duplicate_global_ids)} duplicate IDs found")
    else:
        st.success("✅ No duplicate project IDs")

st.divider()

# Review Board Configuration
st.markdown("### 🎯 Run Review Board")

col1, col2 = st.columns([3, 1])

with col1:
    budget = st.slider(
        "Funding Envelope (PKR Million)",
        min_value=100.0,
        max_value=20000.0,
        value=2000.0,
        step=100.0
    )

with col2:
    run_button = st.button("🚀 Run Review", type="primary", width="stretch")

if run_button:
    with st.spinner("👥 Review board specialists are analyzing…"):
        try:
            report, activity, specialists, path = run_review(budget)
            st.session_state.review_result = (report, activity, specialists, path)
            st.rerun()
        except Exception as exc:
            st.error(f"❌ Review failed: {exc}")

# Display Results
if "review_result" in st.session_state:
    report, activity, specialists, path = st.session_state.review_result
    
    st.divider()
    
    st.markdown("### ✅ Review Results")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("✅ Selected Projects", len(report.recommended_projects), "")
    col2.metric("💰 Allocated Budget", f"PKR {report.total_recommended_m:,.1f}M", "")
    col3.metric("💵 Remaining", f"PKR {report.remaining_budget_m:,.1f}M", "")
    
    st.divider()
    
    # Specialist Reports
    st.markdown("### 👥 Specialist Assessments")
    
    specialist_cols = st.columns(3)
    specialist_names = list(specialists.keys())
    
    for col, specialist_name in zip(specialist_cols, specialist_names):
        specialist = specialists[specialist_name]
        with col:
            with st.container(border=True):
                st.markdown(f"**{specialist_name.title()}**")
                st.markdown(f"**Summary:**\n{specialist.summary}")
                st.caption(f"{len(specialist.findings)} findings · {len(specialist.recommended_projects)} candidate projects")
                if specialist.findings:
                    st.markdown(f"**Top finding:** {specialist.findings[0].title}")
    
    st.divider()
    
    # Recommended Projects
    st.markdown("### 📋 Recommended Projects")
    st.caption("Ranked by financial feasibility, delivery readiness, and equity allocation")
    
    rec_raw = pd.DataFrame([r.model_dump() for r in report.recommended_projects])
    rec_display = rec_raw[["global_id", "category", "cost_m", "district", "score"]].head(20)
    rec_display.columns = ["Project ID", "Category", "Cost (M)", "District", "Priority Score"]
    
    st.dataframe(rec_display, width="stretch", hide_index=True)
    
    # Export
    col1, col2 = st.columns(2)
    
    with col1:
        st.download_button(
            "📥 Download Recommendations (CSV)",
            rec_raw.to_csv(index=False),
            "review_recommendations.csv",
            "text/csv",
            width="stretch"
        )
    
    with col2:
        st.download_button(
            "📥 Download Summary (Text)",
            f"REVIEW BOARD RESULTS\n\nBudget: PKR {report.budget_available_m:,.0f}M\nSelected: {len(report.recommended_projects)} projects\nAllocated: PKR {report.total_recommended_m:,.1f}M\n\n{report.executive_summary}",
            "review_summary.txt",
            "text/plain",
            width="stretch"
        )
    
    st.divider()
    
    # Process Details
    with st.expander("📋 Review Process Details"):
        st.caption("How the review board reached its recommendations")
        render_activity(activity)
else:
    st.info("👆 Set a funding budget and click 'Run Review' to see recommendations")
