"""
Tool 2: filter_projects
Tool 3: aggregate_projects
Tool 9: get_project

Generic query tools shared by every agent. These are the only way any
agent touches row-level data -- there is no path from an agent to the
raw DataFrame or the Excel file itself.
"""
from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from tools.data_loader import get_dataframe
from models.schemas import ProjectRecord, FilterResult, AggregateResult

MAX_ROWS_RETURNED = 50  # hard cap so we never dump thousands of rows into a prompt


def _row_to_record(row: pd.Series) -> ProjectRecord:
    return ProjectRecord(
        global_id=str(row.get("global_id") or ""),
        district=str(row.get("district") or ""),
        phase=str(row.get("phase") or ""),
        category=str(row.get("category") or ""),
        description=str(row.get("description") or ""),
        executing_agency=(None if pd.isna(row.get("executing_agency")) else str(row.get("executing_agency"))),
        cost_m=(float(row["cost_m"]) if pd.notna(row.get("cost_m")) else 0.0),
        contractor_raw=(None if pd.isna(row.get("contractor_raw")) else str(row.get("contractor_raw"))),
        contractor_normalized=(None if pd.isna(row.get("contractor_normalized")) else str(row.get("contractor_normalized"))),
        nits=(None if pd.isna(row.get("nits")) else str(row.get("nits"))),
        progress_pct=(float(row["progress_pct"]) if pd.notna(row.get("progress_pct")) else 0.0),
        status=str(row.get("status") or ""),
        work_started=(None if pd.isna(row.get("work_started")) else str(row.get("work_started"))),
        xen_name=(None if pd.isna(row.get("xen_name")) else str(row.get("xen_name"))),
        xen_contact_raw=(None if pd.isna(row.get("xen_contact_raw")) else str(row.get("xen_contact_raw"))),
        xen_contact_normalized=(None if pd.isna(row.get("xen_contact_normalized")) else str(row.get("xen_contact_normalized"))),
        has_contractor=bool(row.get("has_contractor", False)),
        has_xen=bool(row.get("has_xen", False)),
        has_work_started=bool(row.get("has_work_started", False)),
    )


def _apply_filters(
    df: pd.DataFrame,
    district: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    phase: Optional[str] = None,
    min_cost: Optional[float] = None,
    max_cost: Optional[float] = None,
    has_contractor: Optional[bool] = None,
    has_xen: Optional[bool] = None,
    global_ids: Optional[list[str]] = None,
) -> pd.DataFrame:
    out = df
    if district:
        out = out[out["district"].str.casefold() == district.casefold()]
    if category:
        out = out[out["category"].str.casefold() == category.casefold()]
    if status:
        out = out[out["status"].str.casefold() == status.casefold()]
    if phase:
        out = out[out["phase"].str.casefold() == phase.casefold()]
    if min_cost is not None:
        out = out[out["cost_m"] >= min_cost]
    if max_cost is not None:
        out = out[out["cost_m"] <= max_cost]
    if has_contractor is not None:
        out = out[out["has_contractor"] == has_contractor]
    if has_xen is not None:
        out = out[out["has_xen"] == has_xen]
    if global_ids:
        out = out[out["global_id"].isin(global_ids)]
    return out


def filter_projects(
    district: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    phase: Optional[str] = None,
    min_cost: Optional[float] = None,
    max_cost: Optional[float] = None,
    has_contractor: Optional[bool] = None,
    has_xen: Optional[bool] = None,
    global_ids: Optional[list[str]] = None,
    limit: int = 20,
    sort_by: Optional[str] = None,
    descending: bool = False,
) -> FilterResult:
    """
    Tool 2. Returns matching project rows (capped at MAX_ROWS_RETURNED)
    plus the true match count, so the caller knows if results were truncated.
    """
    df = get_dataframe()
    filtered = _apply_filters(
        df, district, category, status, phase, min_cost, max_cost,
        has_contractor, has_xen, global_ids,
    )
    true_count = len(filtered)
    allowed_sort_columns = {"cost_m", "progress_pct", "global_id", "district", "category", "status"}
    if sort_by:
        if sort_by not in allowed_sort_columns:
            raise ValueError(f"Unsupported sort column {sort_by!r}. Valid: {sorted(allowed_sort_columns)}")
        filtered = filtered.sort_values(sort_by, ascending=not descending)
    capped_limit = min(limit, MAX_ROWS_RETURNED)
    subset = filtered.head(capped_limit)

    records = [_row_to_record(row) for _, row in subset.iterrows()]

    filters_applied = {
        k: v for k, v in dict(
            district=district, category=category, status=status, phase=phase,
            min_cost=min_cost, max_cost=max_cost, has_contractor=has_contractor,
            has_xen=has_xen, global_ids=global_ids,
        ).items() if v is not None
    }

    return FilterResult(
        count=true_count,
        truncated=true_count > capped_limit,
        projects=records,
        filters_applied=filters_applied,
    )


def group_projects(
    group_by: str,
    operation: str = "count",
    district: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    phase: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """Group filtered projects and return ranked counts or budget totals."""
    allowed_groups = {"district", "category", "status", "phase"}
    if group_by not in allowed_groups:
        raise ValueError(f"Unsupported group_by {group_by!r}. Valid: {sorted(allowed_groups)}")
    df = _apply_filters(get_dataframe(), district=district, category=category, status=status, phase=phase)
    if operation == "count":
        result = df.groupby(group_by).size().rename("value").reset_index()
    elif operation == "total_cost":
        result = df.groupby(group_by)["cost_m"].sum().rename("value").reset_index()
    elif operation == "average_cost":
        result = df.groupby(group_by)["cost_m"].mean().rename("value").reset_index()
    else:
        raise ValueError("operation must be count, total_cost, or average_cost")
    return result.sort_values("value", ascending=False).head(min(limit, 50)).to_dict("records")


def aggregate_projects(
    operation: str,
    district: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    phase: Optional[str] = None,
    min_cost: Optional[float] = None,
    max_cost: Optional[float] = None,
    has_contractor: Optional[bool] = None,
    has_xen: Optional[bool] = None,
) -> AggregateResult:
    """
    Tool 3. Supported operations: count, total_cost, average_cost, median_cost,
    min_cost, max_cost, total_progress, average_progress.
    """
    df = get_dataframe()
    filtered = _apply_filters(
        df, district, category, status, phase, min_cost, max_cost,
        has_contractor, has_xen,
    )

    ops = {
        "count": lambda d: float(len(d)),
        "total_cost": lambda d: float(d["cost_m"].sum(skipna=True)),
        "average_cost": lambda d: float(d["cost_m"].mean(skipna=True)) if len(d) else None,
        "median_cost": lambda d: float(d["cost_m"].median(skipna=True)) if len(d) else None,
        "min_cost": lambda d: float(d["cost_m"].min(skipna=True)) if len(d) else None,
        "max_cost": lambda d: float(d["cost_m"].max(skipna=True)) if len(d) else None,
        "total_progress": lambda d: float(d["progress_pct"].sum(skipna=True)),
        "average_progress": lambda d: float(d["progress_pct"].mean(skipna=True)) if len(d) else None,
    }

    if operation not in ops:
        raise ValueError(f"Unsupported operation '{operation}'. Valid: {list(ops.keys())}")

    value = ops[operation](filtered)
    if value is not None:
        value = round(value, 4)

    filters_applied = {
        k: v for k, v in dict(
            district=district, category=category, status=status, phase=phase,
            min_cost=min_cost, max_cost=max_cost, has_contractor=has_contractor,
            has_xen=has_xen,
        ).items() if v is not None
    }

    return AggregateResult(
        operation=operation,
        value=value,
        count=len(filtered),
        filters_applied=filters_applied,
    )


def get_project(global_id: str) -> Optional[ProjectRecord]:
    """Tool 9. Return the complete normalized record for one Global ID, or None."""
    df = get_dataframe()
    match = df[df["global_id"].str.casefold() == global_id.casefold()]
    if match.empty:
        return None
    return _row_to_record(match.iloc[0])
