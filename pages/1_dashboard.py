"""Dashboard - Overview of the platform."""
import streamlit as st
import pandas as pd
from ui.api_client import get_portfolio

from ui.styles import APP_CSS

st.markdown(APP_CSS, unsafe_allow_html=True)
try:
    metadata, district_stats, _ = get_portfolio()
except Exception as exc:
    st.error(f"Could not load portfolio data: {exc}")
    st.stop()

status_counts = metadata.status_counts
completed = int(status_counts.get("Completed", 0))
in_progress = int(status_counts.get("In Progress", 0))
total = metadata.total_projects
# Title and Header
st.markdown(
    '<div class="hero"><h1>🏠 Dashboard Overview</h1><p>Real-time insights into your project portfolio and key metrics</p></div>',
    unsafe_allow_html=True
)

# Main Statistics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "📊 Total Projects",
        f"{total:,}",
        f"{metadata.districts} districts",
        delta_color="off"
    )

with col2:
    st.metric(
        "💰 Portfolio Value",
        f"PKR {metadata.total_portfolio_m:,.1f}M",
        f"{metadata.categories} categories",
        delta_color="inverse"
    )

with col3:
    st.metric(
        "✅ Completed",
        f"{completed:,}",
        f"{completed / total:.1%}" if total else "0%"
    )

with col4:
    st.metric(
        "⏳ In Progress",
        f"{in_progress:,}",
        f"{in_progress / total:.1%}" if total else "0%"
    )

st.divider()

# Charts and Analytics
col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Projects by Status")
    status_data = pd.DataFrame(
        [{"Status": status, "Count": count} for status, count in status_counts.items()]
    )
    st.bar_chart(status_data.set_index('Status')['Count'])

with col2:
    st.subheader("🗺️ Top Districts by Budget")
    district_data = pd.DataFrame(district_stats).nlargest(10, "total_budget_m")
    district_data = district_data.rename(columns={"district": "District", "total_budget_m": "Budget (M PKR)"})
    st.bar_chart(district_data.set_index('District')['Budget (M PKR)'])

st.divider()

# Quick Actions
st.subheader("🚀 Quick Start")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("❓ Ask Questions", width="stretch"):
        st.switch_page("pages/2_query_agent.py")

with col2:
    if st.button("🔎 Run Audit", width="stretch"):
        st.switch_page("pages/3_audit_agent.py")

with col3:
    if st.button("👥 Review Board", width="stretch"):
        st.switch_page("pages/4_review_board.py")

st.divider()

# Recent Activity
st.subheader("📝 Recent Activity")
activity_data = pd.DataFrame({
    'Time': ['10:45 AM', '10:30 AM', '10:15 AM', '9:50 AM', '9:30 AM'],
    'Action': [
        'Audit completed for Sindh region',
        'New query: "High-risk projects"',
        'Review board recommendations generated',
        'Data quality check passed',
        'Portfolio refreshed'
    ],
    'Status': ['✅', '✅', '✅', '✅', '✅']
})
st.dataframe(activity_data, width="stretch", hide_index=True)
