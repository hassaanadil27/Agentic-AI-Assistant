"""Track B - Autonomous Audit Agent Page."""
import logging
from pathlib import Path
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from agents.llm_provider import get_provider
from agents.audit_agent import AuditResult
from orchestration.state import load_audit_state
from ui.api_client import run_audit
from ui.styles import APP_CSS

_env_path = Path(__file__).resolve().parent.parent / ".env"
if not (_env_path.exists() and "x-rapidapi-key" in _env_path.read_text(encoding="utf-8").casefold()):
    load_dotenv(_env_path)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

st.markdown(APP_CSS, unsafe_allow_html=True)

def init_state():
    if "audit_result" not in st.session_state:
        saved_audit = load_audit_state()
        if saved_audit and isinstance(saved_audit.get("result"), dict):
            st.session_state.audit_result = AuditResult(**saved_audit["result"])
            st.session_state.audit_goal = saved_audit.get("goal", "")


def friendly_name(value: str) -> str:
    return str(value).replace("_", " ").strip().title()


def render_activity(lines: list[str]) -> None:
    """Show execution logs as timeline."""
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


AUDIT_EXPLANATIONS = {
    "in_progress_missing_start": "Projects marked In Progress without a recorded work-start date.",
    "high_cost_missing_contractor": "High-cost projects missing contractor information.",
    "districts_high_not_started_share": "Districts with unusually high share of unstarted projects.",
    "category_cost_outliers": "Projects with unusual costs compared to similar projects.",
    "in_progress_without_tender": "In-Progress projects without tender information.",
}

init_state()
provider, is_demo = get_provider()
provider_label = {
    "HuggingFaceProvider": "Hugging Face",
    "RapidAPIProvider": "RapidAPI",
    "GrokProvider": "Grok",
}.get(provider.__class__.__name__, "Demo")

# Header
st.markdown(
    '<div class="hero"><h1>🔐 Autonomous Audit Agent</h1><p>Define an audit goal and let the agent create its own check plan, execute independently, and identify risks.</p></div>',
    unsafe_allow_html=True
)

if is_demo:
    st.info("🟠 Demo Mode Active - Limited functionality")
else:
    st.caption(f"🔌 Connected to {provider_label} · {provider.model_name}")

# Audit Input Section
st.markdown("### 📝 Define Your Audit")
col1, col2 = st.columns([3, 1])

with col1:
    audit_goal = st.text_area(
        "Audit Goal",
        value=st.session_state.get("audit_goal", "Find projects most at risk of failure or mismanagement."),
        height=100,
        placeholder="Enter your audit objective..."
    )

with col2:
    run_button = st.button("🚀 Run Audit", type="primary", width="stretch")

if run_button:
    if audit_goal:
        with st.spinner("🔍 Audit Agent is analyzing…"):
            try:
                st.session_state.audit_result = run_audit(audit_goal)
                st.session_state.audit_goal = audit_goal
                st.rerun()
            except Exception as exc:
                st.error(f"❌ Audit failed: {exc}")
    else:
        st.warning("Please enter an audit goal")

# Display Results
if "audit_result" in st.session_state:
    result = st.session_state.audit_result
    
    st.divider()
    
    # Audit Plan
    st.markdown("### 📋 Audit Plan")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Checks", len(result.plan), "")
    col2.metric("Status", "✅ Complete", "")
    col3.metric("Findings", len(result.findings), "")
    
    with st.expander("View Full Plan", expanded=False):
        for index, check in enumerate(result.plan, 1):
            st.markdown(f"**{index}. {friendly_name(check)}**")
            st.caption(AUDIT_EXPLANATIONS.get(check, "A portfolio risk check."))
    
    st.divider()
    
    # Audit Report
    st.markdown("### 📊 Audit Report")
    st.markdown(result.report)
    
    st.divider()
    
    # Detailed Findings
    st.markdown("### 🔎 Detailed Findings")
    
    tabs = st.tabs([f"Finding {i+1}" for i in range(len(result.findings))])
    
    for tab, finding in zip(tabs, result.findings):
        with tab:
            check = finding.get("check", "audit_check")
            count = int(finding.get("count", 0))
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Check Type", friendly_name(check), "")
            col2.metric("Records Flagged", f"{count:,}", "")
            if "threshold_m" in finding:
                col3.metric("Threshold", f"PKR {finding['threshold_m']:,.1f}M", "")
            
            st.info(AUDIT_EXPLANATIONS.get(check, "Portfolio risk check"))
            
            examples = finding.get("examples", [])
            if examples:
                st.markdown("**Examples Requiring Attention**")
                df = pd.DataFrame(examples)
                st.dataframe(df, width="stretch", hide_index=True)
            else:
                st.success("✅ No flagged examples for this check")
    
    st.divider()
    
    # Process Details
    with st.expander("📋 Audit Process Details"):
        st.caption("Technical steps the audit agent performed")
        render_activity(result.trace)
    
    # Export Options
    st.markdown("### 💾 Export Results")
    col1, col2 = st.columns(2)
    
    with col1:
        report_text = f"AUDIT REPORT\n\nGoal: {st.session_state.get('audit_goal')}\n\n{result.report}"
        st.download_button(
            "📄 Download Report",
            report_text,
            "audit_report.txt",
            "text/plain",
            width="stretch"
        )
    
    with col2:
        findings_df = pd.DataFrame(result.findings)
        st.download_button(
            "📊 Download Findings CSV",
            findings_df.to_csv(index=False),
            "audit_findings.csv",
            "text/csv",
            width="stretch"
        )
else:
    st.info("👆 Enter an audit goal and click 'Run Audit' to begin")
