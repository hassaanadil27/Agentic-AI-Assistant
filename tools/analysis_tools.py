"""Generic, validated pandas analysis over the existing cleaned project dataset."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pandas as pd

from models.analysis import AnalysisEvidence, AnalysisPlan, AnalysisResult
from tools.data_loader import DEFAULT_DATA_PATH, get_dataframe

PUBLIC_COLUMNS = {
    "row_num", "global_id", "district", "phase", "category", "description", "executing_agency",
    "cost_m", "progress_pct", "status", "work_started", "xen_name", "nits",
    "contractor_normalized", "has_contractor", "has_xen", "has_work_started",
}
NUMERIC_COLUMNS = {"cost_m", "progress_pct"}
CATEGORICAL_COLUMNS = PUBLIC_COLUMNS - NUMERIC_COLUMNS
ALIASES = {
    "project": "global_id", "projects": "global_id", "scheme": "global_id", "schemes": "global_id", "record": "row_num", "records": "row_num", "row": "row_num", "rows": "row_num",
    "id": "global_id", "sector": "category", "sectors": "category", "budget": "cost_m",
    "cost": "cost_m", "value": "cost_m", "allocation": "cost_m", "progress": "progress_pct",
    "agency": "executing_agency", "contractor": "contractor_normalized", "tender": "nits",
    "engineer": "xen_name", "xen": "xen_name", "start date": "work_started",
}


def dataset_schema() -> dict[str, Any]:
    df = get_dataframe()
    source = Path(DEFAULT_DATA_PATH)
    columns = []
    for name in sorted(PUBLIC_COLUMNS):
        series = df[name]
        kind = "numeric" if name in NUMERIC_COLUMNS else "boolean" if pd.api.types.is_bool_dtype(series.dtype) else "categorical/text"
        columns.append({
            "name": name,
            "type": kind,
            "non_null": int(series.notna().sum()),
            "missing": int(series.isna().sum()),
            "unique": int(series.nunique(dropna=True)),
            "examples": [str(v) for v in series.dropna().unique()[:5]],
        })
    return {
        "dataset": source.name,
        "path": str(source),
        "rows": len(df),
        "columns": columns,
        "numeric_columns": sorted(NUMERIC_COLUMNS),
        "categorical_columns": sorted(CATEGORICAL_COLUMNS),
        "modified_at": source.stat().st_mtime if source.exists() else None,
    }


def resolve_column(name: str | None) -> str | None:
    if not name:
        return None
    normalized = str(name).strip().casefold().replace(" ", "_")
    normalized = ALIASES.get(normalized, normalized)
    return normalized if normalized in PUBLIC_COLUMNS else None


def _apply_filters(df: pd.DataFrame, plan: AnalysisPlan) -> tuple[pd.DataFrame, list[dict]]:
    out = df
    applied = []
    for condition in plan.filters:
        column = resolve_column(condition.column)
        if not column:
            raise ValueError(f"The field '{condition.column}' does not exist in the project dataset.")
        value, operator = condition.value, condition.operator
        series = out[column]
        if operator in {"gt", "gte", "lt", "lte"} and column not in NUMERIC_COLUMNS:
            raise ValueError(f"The field '{column}' is not numeric and cannot use '{operator}'.")
        if operator == "eq": mask = series.astype(str).str.casefold() == str(value).casefold()
        elif operator == "ne": mask = series.astype(str).str.casefold() != str(value).casefold()
        elif operator == "contains": mask = series.astype(str).str.contains(str(value), case=False, regex=False, na=False)
        elif operator == "in": mask = series.astype(str).str.casefold().isin([str(v).casefold() for v in value])
        elif operator == "gt": mask = pd.to_numeric(series, errors="coerce") > float(value)
        elif operator == "gte": mask = pd.to_numeric(series, errors="coerce") >= float(value)
        elif operator == "lt": mask = pd.to_numeric(series, errors="coerce") < float(value)
        else: mask = pd.to_numeric(series, errors="coerce") <= float(value)
        out = out[mask.fillna(False)]
        applied.append({"column": column, "operator": operator, "value": value})
    return out, applied


def _clean_number(value: Any) -> float | int | None:
    if value is None or pd.isna(value) or not math.isfinite(float(value)):
        return None
    number = float(value)
    return int(number) if number.is_integer() else round(number, 4)


def execute_analysis(plan: AnalysisPlan) -> AnalysisResult:
    df = get_dataframe().copy()
    target = resolve_column(plan.target_column)
    secondary = resolve_column(plan.secondary_column)
    groups = [resolve_column(item) for item in plan.group_by]
    if any(item is None for item in groups):
        return _failure(plan, "I couldn't find one of the requested grouping fields in the project data.")
    try:
        filtered, applied = _apply_filters(df, plan)
    except ValueError as exc:
        return _failure(plan, str(exc))
    if filtered.empty:
        return _failure(plan, "No records in the project data match those conditions.", rows=0)

    if plan.intent == "schema":
        schema = dataset_schema()
        table = schema["columns"]
        return _success(plan, f"The project dataset contains **{schema['rows']:,} records** and **{len(table)} analysis-ready fields**.", table, None, len(df), len(df), [], ["all columns"])
    if plan.intent == "overview":
        value = float(filtered["cost_m"].sum(skipna=True))
        table = [{"Metric": "Projects", "Value": len(filtered)}, {"Metric": "Portfolio value (PKR M)", "Value": round(value, 2)}, {"Metric": "Districts", "Value": int(filtered['district'].nunique())}, {"Metric": "Sectors", "Value": int(filtered['category'].nunique())}]
        return _success(plan, f"The portfolio contains **{len(filtered):,} projects** worth **PKR {value:,.2f} million**, across **{filtered['district'].nunique()} districts** and **{filtered['category'].nunique()} sectors**.", table, None, len(df), len(filtered), applied, ["global_id", "cost_m", "district", "category"])
    if plan.intent == "lookup":
        columns = [c for c in ["global_id", "description", "district", "category", "status", "cost_m", "progress_pct", "executing_agency", "work_started", "contractor_normalized", "xen_name", "nits"] if c in filtered]
        table = filtered[columns].head(plan.limit).where(pd.notna(filtered[columns].head(plan.limit)), None).to_dict("records")
        return _success(plan, f"I found **{len(filtered):,} matching project record(s)**. The table shows up to {plan.limit}.", table, None, len(df), len(filtered), applied, columns)
    if plan.intent == "records":
        if target and target in filtered.columns and plan.sort != "none":
            filtered = filtered.sort_values(target, ascending=plan.sort == "ascending", na_position="last")
        columns = [c for c in ["global_id", "description", "district", "category", "status", "cost_m", "progress_pct"] if c in filtered]
        table = filtered[columns].head(plan.limit).where(pd.notna(filtered[columns].head(plan.limit)), None).to_dict("records")
        if table and target:
            direction = "lowest" if plan.sort == "ascending" else "highest"
            answer = f"**{table[0]['global_id']}** has the **{direction} {target.replace('_', ' ')}** in the requested project set, at **{_format_value(table[0][target], 'mean', target)}**."
            chart = {"type": "bar", "title": f"Projects by {target.replace('_', ' ')}", "x": "global_id", "y": target, "data": table}
        else:
            answer, chart = f"I found **{len(filtered):,} matching project(s)** and displayed the first **{len(table):,}**.", None
        return _success(plan, answer, table, chart, len(df), len(filtered), applied, columns)
    if plan.intent == "correlation":
        if target not in NUMERIC_COLUMNS or secondary not in NUMERIC_COLUMNS:
            return _failure(plan, "Correlation requires two numeric project fields.")
        pair = filtered[[target, secondary]].dropna()
        if len(pair) < 2:
            return _failure(plan, "There are not enough complete records to calculate that correlation.", rows=len(pair))
        value = _clean_number(pair[target].corr(pair[secondary]))
        if value is None:
            return _failure(plan, "I couldn't calculate a finite correlation from the available records.", rows=len(pair))
        chart = {"type": "scatter", "title": f"{target} versus {secondary}", "x": target, "y": secondary, "data": pair.head(500).to_dict("records")}
        return _success(plan, f"The Pearson correlation between **{target}** and **{secondary}** is **{value:.4f}**, based on **{len(pair):,} complete records**.", [{"Metric": "Pearson correlation", "Value": value}], chart, len(df), len(pair), applied, [target, secondary])
    if plan.intent == "distribution":
        if target not in NUMERIC_COLUMNS:
            return _failure(plan, "A distribution requires a numeric field such as cost or progress.")
        series = filtered[target].dropna()
        if series.empty:
            return _failure(plan, "No valid numeric values are available for that distribution.")
        summary = [{"Statistic": name, "Value": _clean_number(value)} for name, value in {"Count": len(series), "Mean": series.mean(), "Median": series.median(), "Minimum": series.min(), "Maximum": series.max(), "Standard deviation": series.std()}.items()]
        chart = {"type": "histogram", "title": f"Distribution of {target.replace('_', ' ')}", "x": target, "y": target, "data": [{target: _clean_number(v)} for v in series.head(2000)]}
        return _success(plan, f"The **{target.replace('_', ' ')}** distribution covers **{len(series):,} valid records**, with a mean of **{_format_value(series.mean(), 'mean', target)}** and median of **{_format_value(series.median(), 'median', target)}**.", summary, chart, len(df), len(series), applied, [target], int(filtered[target].isna().sum()))

    if groups:
        operation = plan.operation
        if operation == "count":
            count_column, count_method = ("row_num", "size") if target == "row_num" else ("global_id", "nunique")
            grouped = filtered.groupby(groups, dropna=False).agg(value=(count_column, count_method), total_cost_m=("cost_m", "sum")).reset_index()
        elif operation == "percentage": grouped = filtered.groupby(groups, dropna=False).size().div(len(filtered)).mul(100).rename("value").reset_index()
        else:
            if target not in NUMERIC_COLUMNS:
                return _failure(plan, f"The operation '{operation}' requires a numeric field such as cost or progress.")
            valid = filtered.dropna(subset=[target])
            methods = {"sum": "sum", "mean": "mean", "median": "median", "min": "min", "max": "max", "std": "std"}
            if operation not in methods:
                return _failure(plan, f"The operation '{operation}' is not supported for grouped analysis.")
            grouped = valid.groupby(groups, dropna=False).agg(value=(target, methods[operation]), record_count=("global_id", "size")).reset_index()
        ascending = plan.sort == "ascending"
        if plan.sort != "none": grouped = grouped.sort_values("value", ascending=ascending)
        grouped = grouped.head(plan.limit)
        table = grouped.where(pd.notna(grouped), None).to_dict("records")
        if not table: return _failure(plan, "The grouped calculation produced no valid values.")
        leader = table[0]
        group_label = " / ".join(str(leader[g]) for g in groups)
        metric_label = _metric_label(operation, target)
        direction = "lowest" if plan.sort == "ascending" else "highest" if plan.sort == "descending" else "first"
        answer = f"**{group_label}** has the **{direction} {metric_label}**, with **{_format_value(leader['value'], operation, target)}**."
        chart_type = plan.chart if plan.chart != "none" else "bar"
        chart = {"type": chart_type, "title": f"{metric_label.title()} by {' and '.join(groups)}", "x": groups[0], "y": "value", "data": table}
        return _success(plan, answer, table, chart, len(df), len(filtered), applied, [*groups, target or "global_id"])

    if plan.operation == "percentage":
        value, missing, used = round(len(filtered) / len(df) * 100, 4), 0, len(df)
    elif plan.operation == "count":
        if target == "row_num": value, missing = len(filtered), 0
        else: value, missing = int(filtered["global_id"].nunique(dropna=True)), int(filtered["global_id"].isna().sum())
        used = len(filtered)
    elif plan.operation == "distinct_count":
        if not target: return _failure(plan, "A valid field is required for a distinct count.")
        value, missing, used = int(filtered[target].nunique(dropna=True)), int(filtered[target].isna().sum()), int(filtered[target].notna().sum())
    elif plan.operation == "list":
        if not target: return _failure(plan, "A valid field is required to list values.")
        if target == "global_id":
            columns = [c for c in ["global_id", "description", "district", "category", "status", "cost_m", "progress_pct"] if c in filtered]
            table = filtered[columns].head(plan.limit).where(pd.notna(filtered[columns].head(plan.limit)), None).to_dict("records")
            return _success(plan, f"I found **{len(filtered):,} matching projects** and displayed the first **{len(table):,}**.", table, None, len(df), len(filtered), applied, columns)
        values = sorted((str(v) for v in filtered[target].dropna().unique()), key=str.casefold)
        table = [{target: value} for value in values[:plan.limit]]
        return _success(plan, f"There are **{len(values):,} distinct {target.replace('_', ' ')} values**. The table lists up to {plan.limit}.", table, None, len(df), len(filtered), applied, [target], int(filtered[target].isna().sum()))
    else:
        if target not in NUMERIC_COLUMNS:
            return _failure(plan, f"The operation '{plan.operation}' requires a numeric field such as cost or progress.")
        series = filtered[target].dropna()
        if series.empty: return _failure(plan, "No valid numeric values are available for that calculation.", rows=0)
        funcs = {"sum": series.sum, "mean": series.mean, "median": series.median, "mode": lambda: series.mode().iloc[0], "min": series.min, "max": series.max, "std": series.std}
        if plan.operation not in funcs: return _failure(plan, f"The operation '{plan.operation}' is not supported.")
        value, missing, used = _clean_number(funcs[plan.operation]()), int(filtered[target].isna().sum()), len(series)
        if value is None: return _failure(plan, "The calculation did not produce a finite result.", rows=used)
    metric = _metric_label(plan.operation, target)
    if plan.operation == "count" and target == "global_id":
        answer = f"There are **{int(value):,} unique projects**, calculated as `COUNT(DISTINCT global_id)` across **{used:,} record(s)**."
    elif plan.operation == "count" and target == "row_num":
        answer = f"There are **{int(value):,} dataset records**, calculated by counting workbook rows after cleaning."
    elif plan.operation == "distinct_count" and target:
        plural = {"category": "sectors", "status": "statuses"}.get(target, target.replace("_", " ") + "s")
        answer = f"There are **{int(value):,} distinct {plural}** in the matching project data, based on **{used:,} record(s)**."
    else:
        answer = f"The **{metric}** is **{_format_value(value, plan.operation, target)}**, calculated from **{used:,} record(s)**."
    result = _success(plan, answer, [{"Metric": metric, "Value": value}], None, len(df), used, applied, [target or "global_id"], missing)
    if result.evidence and plan.operation == "count":
        result.evidence.operation = "count_distinct(global_id)" if target == "global_id" else "count_rows" if target == "row_num" else "count"
    return result


def _metric_label(operation: str, target: str | None) -> str:
    field = {"cost_m": "project cost", "progress_pct": "progress percentage", "global_id": "projects", "row_num": "records"}.get(target, (target or "projects").replace("_", " "))
    count_label = "record count" if target == "row_num" else "project count"
    return {"count": count_label, "distinct_count": f"distinct {field} count", "sum": f"total {field}", "mean": f"average {field}", "median": f"median {field}", "mode": f"mode of {field}", "min": f"minimum {field}", "max": f"maximum {field}", "std": f"standard deviation of {field}", "percentage": "share of projects"}.get(operation, f"{operation} {field}")


def _format_value(value: Any, operation: str, target: str | None) -> str:
    if operation in {"count", "distinct_count"}: return f"{int(value):,}"
    if operation == "percentage": return f"{float(value):,.2f}%"
    if target == "cost_m": return f"PKR {float(value):,.2f} million"
    if target == "progress_pct": return f"{float(value):,.2f}%"
    return f"{int(value):,}" if float(value).is_integer() else f"{float(value):,.4f}"


def _success(plan, answer, table, chart, available, analyzed, filters, columns, missing=0):
    evidence = AnalysisEvidence(dataset=Path(DEFAULT_DATA_PATH).name, rows_available=available, rows_analyzed=analyzed, columns=[c for c in columns if c], filters=filters, operation=plan.operation, missing_values_excluded=missing)
    return AnalysisResult(success=True, intent=plan.intent, answer=answer, evidence=evidence, table=table, chart=chart, plan=plan, validation="passed")


def _failure(plan: AnalysisPlan, message: str, rows: int = 0) -> AnalysisResult:
    return AnalysisResult(success=False, intent=plan.intent, answer=message, plan=plan, validation="failed", error=message)


def rank_attention_projects(limit: int = 5, global_id: str | None = None) -> dict[str, Any]:
    """Rank projects needing attention using transparent observed flags.

    This is not a hidden risk score. It counts actual delivery/accountability
    concerns present in Projects.xlsx, then orders ties by lower progress and
    higher recorded cost. Only fields that exist in the cleaned dataset are used.
    """
    df = get_dataframe().copy()
    flags = pd.DataFrame(index=df.index)
    flags["In progress with no recorded start date"] = (df["status"] == "In Progress") & ~df["has_work_started"]
    flags["In progress with no contractor"] = (df["status"] == "In Progress") & ~df["has_contractor"]
    flags["In progress with no assigned XEN"] = (df["status"] == "In Progress") & ~df["has_xen"]
    flags["Not Started despite tender being issued"] = (df["status"] == "Not Started") & (df["nits"].astype(str).str.casefold() == "yes")
    issue_count = flags.sum(axis=1)
    candidates = df.loc[issue_count > 0, ["global_id", "description", "district", "category", "status", "cost_m", "progress_pct", "has_contractor", "has_xen", "work_started"]].copy()
    candidates["attention_flags"] = issue_count[issue_count > 0].astype(int)
    candidates["reasons"] = [
        [name for name in flags.columns if bool(flags.at[index, name])]
        for index in candidates.index
    ]
    if global_id:
        candidates = candidates[candidates["global_id"].astype(str).str.casefold() == global_id.casefold()]
    candidates = candidates.sort_values(["attention_flags", "progress_pct", "cost_m"], ascending=[False, True, False], na_position="last")
    rows = candidates.head(max(1, min(limit, 20))).where(pd.notna(candidates.head(max(1, min(limit, 20)))), None).to_dict("records")
    return {
        "success": bool(rows),
        "method": "Observed attention-flag count; ties use lower progress then higher cost",
        "candidate_count": len(candidates),
        "rows_analyzed": len(df),
        "columns": ["global_id", "status", "progress_pct", "has_work_started", "has_contractor", "has_xen", "nits", "cost_m"],
        "results": rows,
    }
