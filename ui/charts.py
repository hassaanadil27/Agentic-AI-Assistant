"""
Executive Visualizations and Plotly Chart Generation.
Consistent with Balochistan Development Intelligence Platform civic-tech design system.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from tools.data_loader import get_dataframe

CHART_WORDS = {
    "chart", "graph", "plot", "visualize", "visualise", "distribution",
    "compare", "comparison", "percentage", "trend", "share", "proportion",
}

# Executive Color Sequences
EXECUTIVE_PALETTE = ["#0D9488", "#0F766E", "#0F172A", "#1E293B", "#D97706", "#2563EB", "#7C3AED", "#DB2777"]
STATUS_COLORS = {
    "Completed": "#10B981",
    "In Progress": "#0EA5E9",
    "Not Started": "#94A3B8",
    "NITs Issued": "#F59E0B",
}


def should_chart(question: str) -> bool:
    words = set(re.findall(r"[a-z]+", question.casefold()))
    return bool(words & CHART_WORDS)


def create_chart_spec(question: str, chart_type: str | None = None) -> dict:
    q = question.casefold()
    df = get_dataframe()
    if "district" in q:
        data = (
            df.groupby("district", as_index=False)
            .agg(value=("cost_m", "sum"), projects=("global_id", "count"))
            .nlargest(15, "value")
        )
        x, y, title, x_label, y_label = "district", "value", "Portfolio Allocation by District (Top 15)", "District", "Allocation (PKR millions)"
    elif "status" in q or "progress" in q:
        data = df.groupby("status", as_index=False).agg(value=("global_id", "count"))
        x, y, title, x_label, y_label = "status", "value", "Project Count by Delivery Status", "Status", "Number of Projects"
    else:
        data = (
            df.groupby("category", as_index=False)
            .agg(value=("cost_m", "sum"), projects=("global_id", "count"))
            .sort_values("value", ascending=False)
        )
        x, y, title, x_label, y_label = "category", "value", "Portfolio Allocation by Sector", "Sector", "Allocation (PKR millions)"

    inferred = "pie" if any(word in q for word in ("percentage", "proportion", "share", "pie")) else "bar"
    selected = chart_type or inferred
    return {
        "id": f"chart-{int(datetime.now(timezone.utc).timestamp() * 1000)}",
        "question": question,
        "title": title,
        "type": selected,
        "x": x,
        "y": y,
        "x_label": x_label,
        "y_label": y_label,
        "data": data.to_dict(orient="records"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def render_figure(spec: dict, chart_type: str | None = None) -> go.Figure:
    data = pd.DataFrame(spec["data"])
    kind = chart_type or spec.get("type", "bar")

    common = dict(
        data_frame=data,
        title=spec["title"],
        template="plotly_white",
        color_discrete_sequence=EXECUTIVE_PALETTE,
    )

    if kind == "pie":
        fig = px.pie(**common, names=spec["x"], values=spec["y"], hole=0.45)
        fig.update_traces(textposition="inside", textinfo="percent+label")
    elif kind == "line":
        fig = px.line(**common, x=spec["x"], y=spec["y"], markers=True)
    elif kind == "scatter":
        fig = px.scatter(**common, x=spec["x"], y=spec["y"])
    elif kind == "histogram":
        fig = px.histogram(**common, x=spec["y"])
    else:
        fig = px.bar(**common, x=spec["x"], y=spec["y"])
        fig.update_traces(marker=dict(line=dict(width=0)))

    fig.update_layout(
        font=dict(family="Inter, sans-serif", color="#334155"),
        title=dict(font=dict(family="Inter, sans-serif", size=14, color="#0F172A")),
        margin=dict(l=20, r=20, t=50, b=20),
        height=380,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
    )
    fig.update_xaxes(showgrid=False, title=dict(text=spec.get("x_label"), font=dict(size=12, color="#64748B")))
    fig.update_yaxes(showgrid=True, gridcolor="#F1F5F9", title=dict(text=spec.get("y_label"), font=dict(size=12, color="#64748B")))
    return fig


def render_status_donut(status_counts: dict[str, int]) -> go.Figure:
    """Renders a polished executive donut chart for project status breakdown."""
    labels = list(status_counts.keys())
    values = list(status_counts.values())
    colors = [STATUS_COLORS.get(label, "#64748B") for label in labels]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.55,
                marker=dict(colors=colors, line=dict(color="#FFFFFF", width=2)),
                textinfo="label+percent",
                hoverinfo="label+value+percent",
                insidetextorientation="horizontal",
            )
        ]
    )
    fig.update_layout(
        title=dict(text="Project Delivery Status Distribution", font=dict(family="Inter, sans-serif", size=14, color="#0F172A")),
        template="plotly_white",
        font=dict(family="Inter, sans-serif", color="#334155"),
        margin=dict(l=10, r=10, t=45, b=10),
        height=320,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
        paper_bgcolor="#FFFFFF",
    )
    return fig


def render_sector_treemap(df: pd.DataFrame) -> go.Figure:
    """Renders an interactive treemap of portfolio allocation by category."""
    cat_summary = (
        df.groupby("category", as_index=False)
        .agg(cost_m=("cost_m", "sum"), count=("global_id", "count"))
        .sort_values("cost_m", ascending=False)
    )

    fig = px.treemap(
        cat_summary,
        path=["category"],
        values="cost_m",
        title="Portfolio Allocation by Sector (PKR millions)",
        color="cost_m",
        color_continuous_scale=["#CCFBF1", "#0D9488", "#0F766E", "#0F172A"],
        hover_data={"count": True, "cost_m": ":,.1f"},
    )
    fig.update_layout(
        font=dict(family="Inter, sans-serif"),
        margin=dict(l=10, r=10, t=45, b=10),
        height=340,
        coloraxis_showscale=False,
        paper_bgcolor="#FFFFFF",
    )
    return fig


def render_district_bar(district_df: pd.DataFrame, top_n: int = 12) -> go.Figure:
    """Renders a clean horizontal bar chart for top districts by budget."""
    top_districts = district_df.nlargest(top_n, "total_budget_m").sort_values("total_budget_m", ascending=True)

    fig = go.Figure(
        go.Bar(
            x=top_districts["total_budget_m"],
            y=top_districts["district"],
            orientation="h",
            marker=dict(color="#0D9488", line=dict(width=0)),
            hovertemplate="<b>%{y}</b><br>Budget: PKR %{x:,.1f} million<extra></extra>",
        )
    )
    fig.update_layout(
        title=dict(text=f"Top {top_n} Districts by Allocation (PKR millions)", font=dict(family="Inter, sans-serif", size=14, color="#0F172A")),
        template="plotly_white",
        font=dict(family="Inter, sans-serif", color="#334155"),
        margin=dict(l=10, r=20, t=45, b=10),
        height=340,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#F1F5F9", title=dict(text="Allocation (PKR millions)", font=dict(size=11, color="#64748B")))
    fig.update_yaxes(showgrid=False)
    return fig


def render_allocation_waterfall(budget_available_m: float, total_recommended_m: float, remaining_m: float) -> go.Figure:
    """Renders a clean budget waterfall chart for review board consensus."""
    fig = go.Figure(
        go.Waterfall(
            name="Funding Allocation",
            orientation="v",
            measure=["absolute", "relative", "total"],
            x=["Total Budget Envelope", "Allocated to Projects", "Remaining Reserve"],
            textposition="outside",
            text=[f"PKR {budget_available_m:,.1f}M", f"-PKR {total_recommended_m:,.1f}M", f"PKR {remaining_m:,.1f}M"],
            y=[budget_available_m, -total_recommended_m, remaining_m],
            connector={"line": {"color": "#CBD5E1"}},
            decreasing={"marker": {"color": "#0D9488"}},
            increasing={"marker": {"color": "#2563EB"}},
            totals={"marker": {"color": "#0F172A"}},
        )
    )
    fig.update_layout(
        title=dict(text="Budget Envelope Allocation Breakdown", font=dict(family="Inter, sans-serif", size=14, color="#0F172A")),
        template="plotly_white",
        font=dict(family="Inter, sans-serif", color="#334155"),
        margin=dict(l=20, r=20, t=45, b=20),
        height=320,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
    )
    fig.update_yaxes(showgrid=True, gridcolor="#F1F5F9", title=dict(text="PKR millions", font=dict(size=11, color="#64748B")))
    return fig
