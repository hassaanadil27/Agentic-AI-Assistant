"""Question-aware, serializable Plotly chart generation."""
from __future__ import annotations

import re
from datetime import datetime, timezone

import pandas as pd
import plotly.express as px

from tools.data_loader import get_dataframe

CHART_WORDS = {"chart", "graph", "plot", "visualize", "visualise", "distribution", "compare", "comparison", "percentage", "trend"}


def should_chart(question: str) -> bool:
    """Every portfolio question has a useful evidence view in the workspace."""
    return bool(question.strip())


def create_chart_spec(question: str, chart_type: str | None = None) -> dict:
    q = question.casefold()
    df = get_dataframe()
    if any(word in q for word in ("contractor", "vendor")):
        data = pd.DataFrame(
            {
                "coverage": ["Contractor recorded", "Contractor missing"],
                "value": [int(df["has_contractor"].sum()), int((~df["has_contractor"]).sum())],
            }
        )
        x, y, title, x_label, y_label = "coverage", "value", "Contractor information coverage", "Coverage", "Projects"
        inferred = "pie"
    elif any(word in q for word in ("start date", "work started", "started date")):
        data = pd.DataFrame(
            {
                "coverage": ["Start date recorded", "Start date missing"],
                "value": [int(df["has_work_started"].sum()), int((~df["has_work_started"]).sum())],
            }
        )
        x, y, title, x_label, y_label = "coverage", "value", "Work-start date completeness", "Coverage", "Projects"
        inferred = "pie"
    elif any(word in q for word in ("agency", "department", "executing")):
        data = (
            df.groupby("executing_agency", as_index=False)
            .agg(value=("cost_m", "sum"), projects=("global_id", "count"))
            .nlargest(12, "value")
        )
        x, y, title, x_label, y_label = "executing_agency", "value", "Portfolio budget by executing agency", "Executing agency", "Budget (PKR M)"
        inferred = "bar"
    elif any(word in q for word in ("progress", "completion rate", "delivery")) and "status" not in q:
        bins = pd.cut(
            df["progress_pct"].fillna(0),
            bins=[-1, 0, 25, 50, 75, 99, 100],
            labels=["Not started", "1-25%", "26-50%", "51-75%", "76-99%", "Complete"],
        )
        data = bins.value_counts(sort=False).rename_axis("progress_band").reset_index(name="value")
        x, y, title, x_label, y_label = "progress_band", "value", "Projects by delivery progress", "Progress", "Projects"
        inferred = "bar"
    elif "district" in q:
        data = df.groupby("district", as_index=False).agg(value=("cost_m", "sum"), projects=("global_id", "count")).nlargest(15, "value")
        x, y, title, x_label, y_label = "district", "value", "Portfolio budget by district", "District", "Budget (PKR M)"
        inferred = "bar"
    elif "status" in q or "progress" in q:
        data = df.groupby("status", as_index=False).agg(value=("global_id", "count"))
        x, y, title, x_label, y_label = "status", "value", "Projects by delivery status", "Status", "Projects"
        inferred = "pie"
    else:
        data = df.groupby("category", as_index=False).agg(value=("cost_m", "sum"), projects=("global_id", "count")).sort_values("value", ascending=False)
        x, y, title, x_label, y_label = "category", "value", "Portfolio budget by category", "Category", "Budget (PKR M)"
        inferred = "bar"

    if any(word in q for word in ("percentage", "proportion", "share", "pie")):
        inferred = "pie"
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


def render_figure(spec: dict, chart_type: str | None = None):
    data = pd.DataFrame(spec["data"])
    kind = chart_type or spec.get("type", "bar")
    common = dict(data_frame=data, title=spec["title"], template="plotly_dark")
    if kind == "pie":
        fig = px.pie(**common, names=spec["x"], values=spec["y"], hole=0.35)
    elif kind == "line":
        fig = px.line(**common, x=spec["x"], y=spec["y"], markers=True)
    elif kind == "scatter":
        fig = px.scatter(**common, x=spec["x"], y=spec["y"])
    elif kind == "histogram":
        fig = px.histogram(**common, x=spec["y"])
    else:
        fig = px.bar(**common, x=spec["x"], y=spec["y"], color=spec["y"], color_continuous_scale=[[0, "#5f542b"], [1, "#f6c945"]])
    fig.update_layout(
        margin=dict(l=16, r=16, t=58, b=16),
        coloraxis_showscale=False,
        height=430,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#dfe2de"),
        hoverlabel=dict(bgcolor="#20231f", font_color="#f4f5f2"),
        legend=dict(orientation="h", y=-0.2),
    )
    fig.update_traces(hovertemplate="<b>%{x}</b><br>%{y:,.1f}<extra></extra>" if kind != "pie" else None)
    fig.update_xaxes(title=spec["x_label"])
    fig.update_yaxes(title=spec["y_label"], gridcolor="#292d2a")
    return fig
