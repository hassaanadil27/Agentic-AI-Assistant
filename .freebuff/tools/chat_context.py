"""Build a compact, question-relevant project context for the chat LLM."""
from __future__ import annotations

import json
import re

from tools.data_loader import get_dataframe, load_projects
from tools.finance_tools import category_statistics, district_statistics


def build_chat_context(question: str, max_projects: int = 20) -> str:
    """Return portfolio aggregates plus the rows most relevant to a question."""
    df = get_dataframe().copy()
    metadata = load_projects()
    terms = {
        token.casefold()
        for token in re.findall(r"[A-Za-z0-9_-]+", question)
        if len(token) >= 3
    }

    searchable_columns = ["global_id", "district", "category", "description", "status", "phase"]
    searchable = df[searchable_columns].fillna("").astype(str).agg(" ".join, axis=1).str.casefold()
    scores = searchable.map(lambda text: sum(1 for term in terms if term in text))
    matches = df.loc[scores[scores > 0].sort_values(ascending=False).index].head(max_projects)

    project_columns = [
        "global_id", "description", "district", "category", "phase", "status",
        "cost_m", "progress_pct", "executing_agency", "has_contractor", "has_xen",
        "has_work_started",
    ]
    payload = {
        "portfolio": metadata.model_dump(),
        "district_statistics": [item.model_dump() for item in district_statistics()],
        "category_statistics": [item.model_dump() for item in category_statistics()],
        "matching_projects": matches[project_columns].fillna("").to_dict(orient="records"),
        "matching_projects_note": (
            f"Top {len(matches)} lexical matches from {len(df)} projects; ask for a Global ID "
            "or more specific wording if the intended project is absent."
        ),
    }
    return json.dumps(payload, default=str, ensure_ascii=False)
