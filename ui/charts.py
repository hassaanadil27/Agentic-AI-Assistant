"""Question-aware, serializable Plotly chart generation."""
from __future__ import annotations

import re
from datetime import datetime, timezone

import pandas as pd
import plotly.express as px

from tools.data_loader import get_dataframe

CHART_WORDS = {"chart", "graph", "plot", "visualize", "visualise", "distribution", "compare", "comparison", "percentage", "trend"}


def should_chart(question: str) -> bool:
    words = set(re.findall(r"[a-z]+", question.casefold()))
    return bool(words & CHART_WORDS)


def create_chart_spec(question: str, chart_type: str | None = None) -> dict:
    q = question.casefold()
    df = get_dataframe()
    if "district" in q:
        data = df.groupby("district", as_index=False).agg(value=("cost_m", "sum"), projects=("global_id", "count")).nlargest(15, "value")
        x, y, title, x_label, y_label = "district", "value", "Portfolio budget by district", "District", "Budget (PKR M)"
    elif "status" in q or "progress" in q:
        data = df.groupby("status", as_index=False).agg(value=("global_id", "count"))
        x, y, title, x_label, y_label = "status", "value", "Projects by delivery status", "Status", "Projects"
    else:
        data = df.groupby("category", as_index=False).agg(value=("cost_m", "sum"), projects=("global_id", "count")).sort_values("value", ascending=False)
        x, y, title, x_label, y_label = "category", "value", "Portfolio budget by category", "Category", "Budget (PKR M)"

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


def render_figure(spec: dict, chart_type: str | None = None):
    data = pd.DataFrame(spec["data"])
    kind = chart_type or spec.get("type", "bar")
    common = dict(data_frame=data, title=spec["title"], template="plotly_white")
    if kind == "pie":
        fig = px.pie(**common, names=spec["x"], values=spec["y"], hole=0.35)
    elif kind == "line":
        fig = px.line(**common, x=spec["x"], y=spec["y"], markers=True)
    elif kind == "scatter":
        fig = px.scatter(**common, x=spec["x"], y=spec["y"])
    elif kind == "histogram":
        fig = px.histogram(**common, x=spec["y"])
    else:
        fig = px.bar(**common, x=spec["x"], y=spec["y"], color=spec["y"], color_continuous_scale="Teal")
    fig.update_layout(margin=dict(l=20, r=20, t=60, b=20), coloraxis_showscale=False, height=430)
    fig.update_xaxes(title=spec["x_label"])
    fig.update_yaxes(title=spec["y_label"])
    return fig
