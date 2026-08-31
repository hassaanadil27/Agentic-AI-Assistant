"""Portfolio overview and interactive scheme explorer."""
from __future__ import annotations

from pathlib import Path
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

_env = Path(__file__).resolve().parent.parent / ".env"
if _env.exists():
    load_dotenv(_env, override=True)

from tools.data_loader import get_dataframe
from ui.api_client import get_portfolio
from ui.charts import render_district_bar, render_sector_treemap, render_status_donut
from ui.components import render_empty_state, render_footer, render_header, render_section, render_sidebar_info, render_stat
from ui.pdf_reports import portfolio_report_pdf
from ui.styles import APP_CSS

st.set_page_config(page_title="Portfolio Explorer · BALOCHISTAN SPECIAL DEVELOPMENT INITIATIVE AI Agent", page_icon="📊", layout="wide")
st.markdown(APP_CSS, unsafe_allow_html=True)
render_sidebar_info()
render_header("Portfolio overview", "See where funding sits, how delivery is progressing, and locate any scheme with precise multi-criteria filters.", "Direct dataset access", "blue")

try:
    metadata, district_rows, _ = get_portfolio()
    portfolio = get_dataframe()
except Exception as exc:
    st.error("Portfolio data is currently unavailable.")
    with st.expander("Technical details"):
        st.code(str(exc))
    st.stop()

total = metadata.total_projects
completed = int(metadata.status_counts.get("Completed", 0))
not_started = int(metadata.status_counts.get("Not Started", 0))
cards = st.columns(4)
values = [
    ("Total schemes", f"{total:,}", f"Across {metadata.districts} districts", "All records", "blue"),
    ("Portfolio value", f"PKR {metadata.total_portfolio_m / 1000:,.1f}B", f"Average PKR {metadata.total_portfolio_m / max(total, 1):,.1f}M", "Allocation", "blue"),
    ("Completed", f"{completed:,}", f"{completed / max(total, 1):.1%} delivery rate", "Delivered", "green"),
    ("Not started", f"{not_started:,}", f"{not_started / max(total, 1):.1%} of schemes", "Pipeline", "amber"),
]
for column, metric in zip(cards, values):
    with column:
        render_stat(*metric)

overview_tab, explorer_tab, quality_tab = st.tabs(["Portfolio picture", "Scheme explorer", "Data notes"])

with overview_tab:
    render_section("Portfolio picture", "Hover over any chart for exact values. Chart menus allow image downloads.")
    left, right = st.columns([.9, 1.1])
    chart_config = {"displaylogo": False, "responsive": True}
    with left:
        st.plotly_chart(render_status_donut(metadata.status_counts), width="stretch", config=chart_config)
    with right:
        st.plotly_chart(render_district_bar(pd.DataFrame(district_rows), top_n=12), width="stretch", config=chart_config)
    st.plotly_chart(render_sector_treemap(portfolio), width="stretch", config=chart_config)

with explorer_tab:
    render_section("Find and compare schemes", "Filters update immediately. Search accepts scheme title, Global ID, or district.")

    max_cost = float(portfolio["cost_m"].max(skipna=True) or 0)
    defaults = {
        "explorer_search": "", "explorer_sector": "All sectors", "explorer_district": "All districts",
        "explorer_status": "All statuses", "explorer_cost": (0.0, max_cost),
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)

    with st.container(border=True):
        top = st.columns([1.5, 1, 1])
        with top[0]:
            st.text_input("Search schemes", placeholder="Try ‘water’, ‘Kech’, or a Global ID", key="explorer_search")
        with top[1]:
            st.selectbox("Sector", ["All sectors", *sorted(portfolio["category"].dropna().unique())], key="explorer_sector")
        with top[2]:
            st.selectbox("District", ["All districts", *sorted(portfolio["district"].dropna().unique())], key="explorer_district")
        bottom = st.columns([1, 2.3, .7])
        with bottom[0]:
            st.selectbox("Delivery status", ["All statuses", *sorted(portfolio["status"].dropna().unique())], key="explorer_status")
        with bottom[1]:
            st.slider("Scheme cost · PKR millions", 0.0, max_cost, key="explorer_cost", step=max(1.0, round(max_cost / 500, 1)))
        with bottom[2]:
            st.write("")
            st.write("")
            if st.button("Reset filters", width="stretch"):
                for key, value in defaults.items():
                    st.session_state[key] = value
                st.rerun()

    filtered = portfolio.copy()
    query = st.session_state.explorer_search.strip()
    if query:
        needle = query.casefold()
        match = pd.Series(False, index=filtered.index)
        for field in ("description", "global_id", "district"):
            match |= filtered[field].astype(str).str.casefold().str.contains(needle, regex=False, na=False)
        filtered = filtered[match]
    mappings = [("explorer_sector", "category", "All sectors"), ("explorer_district", "district", "All districts"), ("explorer_status", "status", "All statuses")]
    for state_key, field, all_label in mappings:
        selection = st.session_state[state_key]
        if selection != all_label:
            filtered = filtered[filtered[field] == selection]
    low, high = st.session_state.explorer_cost
    cost_mask = filtered["cost_m"].between(low, high)
    if low == 0 and high == max_cost:
        cost_mask |= filtered["cost_m"].isna()
    filtered = filtered[cost_mask]

    if filtered.empty:
        render_empty_state("⌕", "No matching schemes", "Try a broader search term or reset one of the filters.")
    else:
        summary = st.columns(3)
        with summary[0]:
            render_stat("Matching schemes", f"{len(filtered):,}", f"{len(filtered) / max(total, 1):.1%} of portfolio")
        with summary[1]:
            render_stat("Combined value", f"PKR {filtered['cost_m'].sum(skipna=True):,.1f}M", "Valid recorded costs")
        with summary[2]:
            avg_progress = filtered["progress_pct"].mean(skipna=True)
            render_stat("Average progress", f"{avg_progress:.1f}%" if pd.notna(avg_progress) else "Not available", "Across matching records")

        display = filtered[["global_id", "description", "category", "district", "cost_m", "status", "progress_pct"]].copy()
        display.columns = ["Scheme ID", "Scheme", "Sector", "District", "Cost", "Status", "Progress"]
        st.dataframe(
            display,
            width="stretch",
            height=500,
            hide_index=True,
            column_config={
                "Scheme ID": st.column_config.TextColumn(width="small"),
                "Scheme": st.column_config.TextColumn(width="large"),
                "Cost": st.column_config.NumberColumn("Cost · PKR M", format="%.2f"),
                "Progress": st.column_config.ProgressColumn("Progress", min_value=0, max_value=100, format="%.1f%%"),
            },
        )
        export_columns = st.columns(2)
        with export_columns[0]:
            st.download_button("Download filtered table", display.to_csv(index=False).encode("utf-8"), "bsdi_filtered_schemes.csv", "text/csv", width="stretch")
        with export_columns[1]:
            st.download_button("Download portfolio PDF", portfolio_report_pdf(display.to_dict(orient="records"), float(filtered["cost_m"].sum(skipna=True))), "bsdi_portfolio_report.pdf", "application/pdf", type="primary", width="stretch")

with quality_tab:
    render_section("How to read this data", "The portfolio is intentionally preserved as reported; uncertainty is surfaced rather than silently repaired.")
    if metadata.load_warnings:
        for warning in metadata.load_warnings:
            st.warning(warning)
    else:
        st.success("The workbook loaded successfully with no dataset-level warnings.")
    st.markdown(
        """
        - Monetary values are displayed in **PKR millions**.
        - Missing costs or progress values remain missing; they are not converted to zero.
        - Agency variants use an explicit mapping, and ambiguous phone formats are flagged for review.
        - Use the dedicated **Risk Audit** workspace for completeness and accountability checks.
        """
    )

render_footer()
