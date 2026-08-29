"""Autonomous portfolio risk-audit workspace."""
from __future__ import annotations

from dataclasses import asdict
from datetime import date
from pathlib import Path
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

_env = Path(__file__).resolve().parent.parent / ".env"
if _env.exists():
    load_dotenv(_env, override=True)

from agents.audit_agent import AuditResult
from orchestration.state import load_audit_state
from ui.api_client import get_quality, run_audit
from ui.components import render_empty_state, render_footer, render_header, render_section, render_sidebar_info, render_stat, render_trace
from ui.styles import APP_CSS

st.set_page_config(page_title="Risk Audit · BSDI", page_icon="🛡️", layout="wide")
st.markdown(APP_CSS, unsafe_allow_html=True)
render_sidebar_info()
render_header("Risk and governance audit", "Set an audit objective, let the agent choose independent checks, and review each flag with counts and source-record examples.", "Python-verified scan", "amber")

if "audit_result" not in st.session_state:
    saved = load_audit_state()
    st.session_state.audit_result = AuditResult(**saved["result"]) if saved and isinstance(saved.get("result"), dict) else None
    st.session_state.audit_goal = saved.get("goal", "") if saved else ""

try:
    quality = get_quality()
    total_rows = max(quality.total_rows, 1)
    quality_cols = st.columns(4)
    quality_metrics = [
        ("Portfolio records", f"{quality.total_rows:,}", "Rows included in the scan", "Scope", "blue"),
        ("Missing contractor", f"{quality.missing_contractor / total_rows:.1%}", f"{quality.missing_contractor:,} affected records", "Accountability", "amber"),
        ("Missing XEN", f"{quality.missing_xen / total_rows:.1%}", f"{quality.missing_xen:,} affected records", "Ownership", "amber"),
        ("Missing start date", f"{quality.missing_work_started / total_rows:.1%}", f"{quality.missing_work_started:,} affected records", "Schedule", "red"),
    ]
    for column, metric in zip(quality_cols, quality_metrics):
        with column:
            render_stat(*metric)
except Exception as exc:
    st.warning(f"Data-quality indicators could not be loaded: {exc}")

render_section("Define the audit", "Use the default objective for a broad governance review, or describe a specific risk focus.")
with st.container(border=True):
    input_col, action_col = st.columns([3.2, 1])
    with input_col:
        goal = st.text_area(
            "Audit objective",
            value=st.session_state.audit_goal or "Find projects most at risk of failure, delay, or weak accountability.",
            height=100,
            help="The objective guides check selection; every selected check still runs deterministically in Python.",
        )
        st.caption("Checks available: missing start dates, contractor gaps, tender/status mismatches, district pipeline concentration, and category cost outliers.")
    with action_col:
        st.write("")
        run_clicked = st.button("Run portfolio audit", type="primary", width="stretch")
        if st.session_state.audit_result and st.button("Clear results", width="stretch"):
            st.session_state.audit_result = None
            st.rerun()

if run_clicked:
    if not goal.strip():
        st.warning("Enter an audit objective before starting the scan.")
    else:
        with st.spinner("Planning checks and scanning the portfolio…"):
            try:
                st.session_state.audit_result = run_audit(goal.strip())
                st.session_state.audit_goal = goal.strip()
                st.toast("Audit complete", icon="✅")
            except Exception as exc:
                st.error("The audit could not be completed.")
                with st.expander("Technical details"):
                    st.code(str(exc))

result = st.session_state.audit_result
if not result:
    render_empty_state("△", "Ready to scan", "Run the audit to generate a prioritized report, detailed findings, and a visible execution trace.")
else:
    total_flags = sum(int(item.get("count", 0)) for item in result.findings)
    checks_with_flags = sum(1 for item in result.findings if int(item.get("count", 0)) > 0)
    examples = sum(len(item.get("examples", [])) for item in result.findings)
    result_cols = st.columns(3)
    for column, metric in zip(result_cols, [
        ("Issues flagged", f"{total_flags:,}", "Counts may overlap across checks", "Review", "red" if total_flags else "green"),
        ("Checks completed", str(len(result.plan)), f"{checks_with_flags} returned findings", "Complete", "green"),
        ("Source examples", f"{examples:,}", "Records included for verification", "Evidence", "blue"),
    ]):
        with column:
            render_stat(*metric)

    report_tab, findings_tab, process_tab = st.tabs(["Prioritized report", "Finding details", "Audit process"])
    with report_tab:
        render_section("Audit conclusion", "A synthesized view of the independent checks, ordered for action.")
        st.markdown(result.report)
        st.download_button("Download audit report", result.report.encode("utf-8"), f"bsdi_audit_{date.today().isoformat()}.md", "text/markdown")

    with findings_tab:
        render_section("Check-by-check evidence", "Counts are complete; example rows are intentionally capped for readability.")
        export_rows: list[dict] = []
        for index, finding in enumerate(sorted(result.findings, key=lambda item: int(item.get("count", 0)), reverse=True), 1):
            check = str(finding.get("check", "audit_check"))
            label = check.replace("_", " ").title()
            count = int(finding.get("count", 0))
            icon = "🔴" if count >= total_rows * .1 else "🟠" if count else "🟢"
            with st.expander(f"{icon} {label} · {count:,} issue(s)", expanded=index <= 2):
                if finding.get("threshold_m") is not None:
                    st.caption(f"Computed threshold: PKR {float(finding['threshold_m']):,.2f} million")
                example_rows = finding.get("examples", [])
                if example_rows:
                    frame = pd.DataFrame(example_rows)
                    st.dataframe(frame, width="stretch", hide_index=True)
                    for row in example_rows:
                        export_rows.append({"check": check, **row})
                else:
                    st.success("No records were flagged by this check.")
        if export_rows:
            st.download_button("Download evidence examples", pd.DataFrame(export_rows).to_csv(index=False).encode("utf-8"), "bsdi_audit_evidence.csv", "text/csv")

    with process_tab:
        render_section("Agent execution trace", "This is the public plan and tool activity, not private model reasoning.")
        render_trace(result.trace)
        with st.expander("Structured result"):
            st.json(asdict(result))

render_footer()
