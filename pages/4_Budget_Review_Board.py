"""Multi-agent, budget-constrained project review workspace."""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

_env = Path(__file__).resolve().parent.parent / ".env"
if _env.exists():
    load_dotenv(_env, override=True)

from models.messages import AgentReport, FinalReport
from orchestration.state import load_latest_run
from ui.api_client import run_review
from ui.charts import render_allocation_waterfall
import ui.charts as portfolio_charts
from ui.components import render_empty_state, render_footer, render_header, render_section, render_sidebar_info, render_stat, render_trace, render_track_card
from ui.pdf_reports import review_report_pdf
from ui.styles import APP_CSS

st.set_page_config(page_title="Budget Review Board · BSDI", page_icon="👥", layout="wide")
st.markdown(APP_CSS, unsafe_allow_html=True)
render_sidebar_info()
render_header("Budget review board", "Finance, Delivery, and Equity specialists assess the same pipeline, then a Coordinator resolves trade-offs and enforces the funding ceiling.", "Three specialist agents", "blue")

if "review_result" not in st.session_state:
    saved = load_latest_run()
    if saved:
        report = FinalReport.model_validate(saved["final_report"])
        specialists = {name: AgentReport.model_validate(value) for name, value in saved.get("specialist_reports", {}).items()}
        st.session_state.review_result = (report, saved.get("activity_log", []), specialists, "Saved run")
    else:
        st.session_state.review_result = None

with st.expander("How recommendations are produced"):
    explainer = st.columns(4)
    steps = [
        ("01", "Finance", "Assesses affordability, cost exposure, and value within the envelope."),
        ("02", "Delivery", "Checks tender, ownership, contractor, and implementation readiness."),
        ("03", "Equity", "Measures geographic and sector allocation without inferring unmet need."),
        ("04", "Coordinator", "Combines 35/35/30 scores, resolves conflicts, and applies hard limits."),
    ]
    for column, (number, title, copy) in zip(explainer, steps):
        with column:
            st.caption(number)
            st.markdown(f"**{title}**")
            st.caption(copy)

render_section("Set the funding envelope", "Only eligible Not Started schemes can be selected; Python prevents any recommendation from exceeding this cap.")
with st.container(border=True):
    budget_col, action_col = st.columns([3, 1])
    with budget_col:
        budget = st.slider("Available budget · PKR millions", 100.0, 20_000.0, 2_000.0, 100.0, help="PKR 2,000 million equals PKR 2 billion.")
        spent_hint = f"PKR {budget / 1000:,.1f} billion maximum · district and sector concentration controls also apply"
        st.caption(spent_hint)
    with action_col:
        st.write("")
        run_clicked = st.button("Run review board", type="primary", width="stretch")
        if st.session_state.review_result and st.button("Clear results", width="stretch"):
            st.session_state.review_result = None
            st.rerun()

if run_clicked:
    with st.spinner("Specialists are reviewing the pipeline and the Coordinator is building a shortlist…"):
        try:
            report, activity, specialists, log_path = run_review(float(budget))
            st.session_state.review_result = (report, activity, specialists, log_path)
            st.toast("Review complete", icon="✅")
        except Exception as exc:
            st.error("The review board could not complete this run.")
            with st.expander("Technical details"):
                st.code(str(exc))

result = st.session_state.review_result
if not result:
    render_empty_state("◎", "Ready to deliberate", "Choose a funding envelope and run the board to see a ranked, budget-safe shortlist with specialist evidence.")
else:
    report, activity, specialists, source_label = result
    allocation_rate = report.total_recommended_m / max(report.budget_available_m, 1)
    cards = st.columns(4)
    summaries = [
        ("Funding envelope", f"PKR {report.budget_available_m:,.0f}M", "Hard ceiling", "Budget", "blue"),
        ("Recommended", f"{len(report.recommended_projects):,}", "Eligible Not Started schemes", "Selected", "green"),
        ("Allocated", f"PKR {report.total_recommended_m:,.1f}M", f"{allocation_rate:.1%} utilization", "Committed", "blue"),
        ("Remaining", f"PKR {report.remaining_budget_m:,.1f}M", "Unallocated buffer", "Available", "green"),
    ]
    for column, summary in zip(cards, summaries):
        with column:
            render_stat(*summary)
    recommended_rows = [item.model_dump() for item in report.recommended_projects]

    render_section("Review tracks and current work", "Each specialist reviews the same eligible pipeline from a different decision perspective.")
    track_columns = st.columns(4)
    track_details = [
        ("Finance track", "Tests affordability and financial value.", "Scored project costs and budget exposure.", "blue"),
        ("Delivery track", "Tests whether schemes are ready to execute.", "Checked tenders, ownership, contractors, and dates.", "teal"),
        ("Equity track", "Compares geographic and sector distribution.", "Measured allocation balance across districts and sectors.", "amber"),
        ("Coordinator track", "Combines evidence and enforces decision rules.", "Resolved trade-offs and produced the budget-safe shortlist.", "green"),
    ]
    for column, details in zip(track_columns, track_details):
        with column:
            render_track_card(details[0], details[1], details[2], status="Complete", tone=details[3])

    summary_tab, shortlist_tab, specialists_tab, process_tab = st.tabs(["Decision summary", "Funding shortlist", "Specialist evidence", "Process and conflicts"])

    with summary_tab:
        render_section("Coordinator recommendation", "The consolidated result after specialist review and budget enforcement.")
        with st.container(border=True):
            st.markdown(report.executive_summary)
        chart_left, note_right = st.columns([1.4, .8])
        with chart_left:
            st.plotly_chart(render_allocation_waterfall(report.budget_available_m, report.total_recommended_m, report.remaining_budget_m), width="stretch", config={"displaylogo": False})
            if specialists and hasattr(portfolio_charts, "render_specialist_activity"):
                specialist_activity = [
                    {
                        "Track": name.replace(" Agent", ""),
                        "Findings": len(specialist.findings),
                        "Evidence records": sum(len(finding.evidence) for finding in specialist.findings),
                    }
                    for name, specialist in specialists.items()
                ]
                st.plotly_chart(portfolio_charts.render_specialist_activity(specialist_activity), width="stretch", config={"displaylogo": False})
        with note_right:
            st.markdown("#### Decision guardrails")
            st.markdown(
                """
                - Finance and Delivery each contribute **35%** of the final score.
                - Equity contributes **30%**.
                - The shortlist cannot exceed the funding envelope.
                - District and sector concentration limits reduce over-allocation.
                - Missing readiness fields reduce Delivery scores.
                """
            )
            st.caption(f"Result source: {source_label or 'current local run'}")

    with shortlist_tab:
        render_section("Ranked funding shortlist", "Each recommendation includes the specialist assessments and the Coordinator's selection rationale.")
        if recommended_rows:
            table = pd.DataFrame(recommended_rows)
            display = table[["global_id", "description", "district", "category", "cost_m", "score"]].copy()
            display.columns = ["Scheme ID", "Scheme", "District", "Sector", "Cost", "Score"]
            st.dataframe(
                display,
                width="stretch",
                height=480,
                hide_index=True,
                column_config={
                    "Scheme": st.column_config.TextColumn(width="large"),
                    "Cost": st.column_config.NumberColumn("Cost · PKR M", format="%.2f"),
                    "Score": st.column_config.ProgressColumn("Priority score", min_value=0, max_value=100, format="%.1f"),
                },
            )
            st.download_button("Download shortlist", display.to_csv(index=False).encode("utf-8"), f"bsdi_shortlist_{date.today().isoformat()}.csv", "text/csv")
            st.markdown("#### Why each scheme was selected")
            for index, item in enumerate(report.recommended_projects[:12], 1):
                with st.expander(f"{index}. {item.global_id} · {item.district} · Score {item.score:.1f}"):
                    st.markdown(f"**{item.description}**")
                    st.markdown(item.reason_selected)
                    cols = st.columns(3)
                    cols[0].info(f"Finance\n\n{item.finance_assessment}")
                    cols[1].info(f"Delivery\n\n{item.delivery_assessment}")
                    cols[2].info(f"Equity\n\n{item.equity_assessment}")
        else:
            render_empty_state("—", "No scheme was selected", "The current envelope and concentration constraints did not produce an eligible shortlist.")

    with specialists_tab:
        render_section("Specialist evidence", "Open each perspective to review findings, affected schemes, recommendations, and source tools.")
        tabs = st.tabs(list(specialists.keys())) if specialists else []
        for tab, (name, specialist) in zip(tabs, specialists.items()):
            with tab:
                st.markdown(specialist.summary)
                if specialist.data_quality_notes:
                    for note in specialist.data_quality_notes:
                        st.warning(note)
                for finding in specialist.findings:
                    severity_icon = {"high": "🔴", "medium": "🟠", "low": "🟢"}.get(finding.severity.casefold(), "●")
                    with st.expander(f"{severity_icon} {finding.title}"):
                        st.markdown(finding.explanation)
                        if finding.recommendation:
                            st.markdown(f"**Recommended action:** {finding.recommendation}")
                        if finding.affected_projects:
                            st.caption("Affected examples: " + ", ".join(finding.affected_projects[:12]))
                        if finding.evidence:
                            st.dataframe(pd.DataFrame([e.model_dump() for e in finding.evidence]), width="stretch", hide_index=True)
                with st.expander("Tool calls"):
                    st.dataframe(pd.DataFrame([call.model_dump() for call in specialist.tool_calls]), width="stretch", hide_index=True)

    with process_tab:
        render_section("Conflicts and trade-offs", "A conflict is surfaced when one score dimension is weak while another is strong.")
        if report.conflicts:
            for conflict in report.conflicts:
                with st.expander(f"⚖ {conflict.global_id or 'Portfolio trade-off'} · {conflict.issue}", expanded=True):
                    positions = st.columns(3)
                    positions[0].markdown(f"**Finance**\n\n{conflict.finance_position or 'No position recorded.'}")
                    positions[1].markdown(f"**Delivery**\n\n{conflict.delivery_position or 'No position recorded.'}")
                    positions[2].markdown(f"**Equity**\n\n{conflict.equity_position or 'No position recorded.'}")
                    st.success(f"Coordinator resolution: {conflict.coordinator_resolution}")
        else:
            st.success("No material score conflicts were detected in this shortlist.")
        if report.data_quality_warnings:
            st.markdown("#### Data-quality cautions")
            for warning in report.data_quality_warnings:
                st.warning(warning)
        with st.expander("Public execution trace"):
            render_trace(activity)

    export = report.model_dump()
    download_columns = st.columns(2)
    with download_columns[0]:
        st.download_button("Download formatted review PDF", review_report_pdf(report, specialists), f"bsdi_review_{date.today().isoformat()}.pdf", "application/pdf", type="primary", width="stretch")
    with download_columns[1]:
        st.download_button("Download structured review data", json.dumps(export, indent=2, ensure_ascii=False).encode("utf-8"), f"bsdi_review_{date.today().isoformat()}.json", "application/json", width="stretch")

render_footer()
