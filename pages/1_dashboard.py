"""Portfolio dashboard with live, interactive analytics."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from ui.api_client import get_portfolio
from ui.styles import APP_CSS

st.markdown(APP_CSS, unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div class="brand">Portfolio Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="nav-label">View controls</div>', unsafe_allow_html=True)
    district_limit = st.slider("Districts shown", min_value=5, max_value=20, value=10, step=5)
    st.caption("Charts update immediately from the loaded portfolio.")

try:
    metadata, district_stats, category_stats = get_portfolio()
except Exception as exc:
    st.error(f"Could not load portfolio data: {exc}")
    st.stop()

status_counts = metadata.status_counts
total = metadata.total_projects
completed = int(status_counts.get("Completed", 0))
in_progress = int(status_counts.get("In Progress", 0))

st.markdown(
    '<div class="hero"><h1>Portfolio Dashboard</h1>'
    '<p>Live delivery and investment signals across the complete BSDI project portfolio.</p></div>',
    unsafe_allow_html=True,
)

st.markdown('<div class="section-kicker">Key indicators</div>', unsafe_allow_html=True)
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

status_data = pd.DataFrame(
    [{"Status": status, "Projects": int(count)} for status, count in status_counts.items()]
).sort_values("Projects", ascending=False)
district_data = pd.DataFrame(district_stats).nlargest(district_limit, "total_budget_m")
district_data = district_data.rename(
    columns={"district": "District", "total_budget_m": "Budget (M PKR)", "project_count": "Projects"}
)

chart_theme = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {"color": "#dfe2de", "size": 12},
    "margin": {"l": 12, "r": 12, "t": 48, "b": 12},
    "hoverlabel": {"bgcolor": "#20231f", "font_color": "#f4f5f2"},
}

left, right = st.columns([.92, 1.35])
with left:
    status_figure = px.pie(
        status_data,
        names="Status",
        values="Projects",
        hole=.67,
        title="Project status mix",
        color_discrete_sequence=["#f6c945", "#64c987", "#6f8fae", "#d37b6f", "#9d84b7"],
    )
    status_figure.update_traces(
        textinfo="percent",
        hovertemplate="<b>%{label}</b><br>%{value:,} projects<br>%{percent}<extra></extra>",
    )
    status_figure.add_annotation(
        text=f"<b>{total:,}</b><br><span style='font-size:11px'>projects</span>",
        showarrow=False,
        font={"color": "#f4f5f2", "size": 18},
    )
    status_figure.update_layout(**chart_theme, legend={"orientation": "h", "y": -.08})
    st.plotly_chart(status_figure, width="stretch", config={"displaylogo": False, "responsive": True})

with right:
    district_figure = px.bar(
        district_data.sort_values("Budget (M PKR)"),
        x="Budget (M PKR)",
        y="District",
        orientation="h",
        title=f"Top {district_limit} districts by portfolio value",
        color="Budget (M PKR)",
        color_continuous_scale=[[0, "#5f542b"], [1, "#f6c945"]],
        custom_data=["Projects"] if "Projects" in district_data.columns else None,
    )
    hover = "<b>%{y}</b><br>PKR %{x:,.1f}M"
    if "Projects" in district_data.columns:
        hover += "<br>%{customdata[0]:,} projects"
    district_figure.update_traces(hovertemplate=hover + "<extra></extra>")
    district_figure.update_layout(**chart_theme, coloraxis_showscale=False)
    district_figure.update_xaxes(title="Budget (million PKR)", gridcolor="#292d2a")
    district_figure.update_yaxes(title=None)
    st.plotly_chart(district_figure, width="stretch", config={"displaylogo": False, "responsive": True})

st.markdown('<div class="section-kicker">Category allocation</div>', unsafe_allow_html=True)
category_data = pd.DataFrame(category_stats)
if not category_data.empty and "total_budget_m" in category_data:
    category_data = category_data.rename(
        columns={"category": "Category", "total_budget_m": "Budget (M PKR)", "project_count": "Projects"}
    ).sort_values("Budget (M PKR)", ascending=False)
    category_figure = px.bar(
        category_data,
        x="Category",
        y="Budget (M PKR)",
        title="Investment by project category",
        color_discrete_sequence=["#f6c945"],
        custom_data=["Projects"] if "Projects" in category_data.columns else None,
    )
    category_figure.update_traces(
        hovertemplate="<b>%{x}</b><br>PKR %{y:,.1f}M<extra></extra>",
        marker_line_width=0,
    )
    category_figure.update_layout(**chart_theme)
    category_figure.update_yaxes(title="Budget (million PKR)", gridcolor="#292d2a")
    category_figure.update_xaxes(title=None)
    st.plotly_chart(category_figure, width="stretch", config={"displaylogo": False, "responsive": True})

with st.expander("View exact status totals"):
    status_table = status_data.copy()
    status_table["Share"] = status_table["Projects"].div(total).fillna(0).map(lambda value: f"{value:.1%}")
    st.dataframe(status_table, width="stretch", hide_index=True)

st.markdown('<div class="section-kicker">Continue analysis</div>', unsafe_allow_html=True)
query_col, audit_col, review_col = st.columns(3)
if query_col.button("Ask the query agent", icon=":material/search:", width="stretch"):
    st.switch_page("pages/2_query_agent.py")
if audit_col.button("Run a portfolio audit", icon=":material/policy:", width="stretch"):
    st.switch_page("pages/3_audit_agent.py")
if review_col.button("Open the review board", icon=":material/groups:", width="stretch"):
    st.switch_page("pages/4_review_board.py")
