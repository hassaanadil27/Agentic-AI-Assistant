"""Independent checks exposed to the Track B Audit Agent."""
from __future__ import annotations

from tools.data_loader import get_dataframe
from tools.delivery_tools import find_delivery_risks
from tools.equity_tools import find_equity_risks
from tools.finance_tools import find_cost_outliers


def in_progress_missing_start(limit: int = 25) -> dict:
    rows = [r.model_dump() for r in find_delivery_risks(limit_per_type=limit) if r.risk_type == "in_progress_no_start_date"]
    return {"check": "in_progress_missing_start", "count": len(rows), "examples": rows[:limit]}


def high_cost_missing_contractor(limit: int = 25) -> dict:
    df = get_dataframe()
    threshold = float(df["cost_m"].quantile(.9))
    matches = df[(df["cost_m"] >= threshold) & (~df["has_contractor"])]
    fields = ["global_id", "district", "category", "cost_m", "status"]
    return {"check": "high_cost_missing_contractor", "threshold_m": threshold, "count": len(matches), "examples": matches[fields].head(limit).to_dict("records")}


def districts_high_not_started_share(limit: int = 25) -> dict:
    rows = [r.model_dump() for r in find_equity_risks() if r.risk_type == "district_not_started_share"]
    return {"check": "districts_high_not_started_share", "count": len(rows), "examples": rows[:limit]}


def category_cost_outliers(limit: int = 25) -> dict:
    rows = [r.model_dump() for r in find_cost_outliers()]
    return {"check": "category_cost_outliers", "count": len(rows), "examples": rows[:limit]}


def in_progress_without_tender(limit: int = 25) -> dict:
    rows = [r.model_dump() for r in find_delivery_risks(limit_per_type=limit) if r.risk_type == "nits_status_mismatch"]
    return {"check": "in_progress_without_tender", "count": len(rows), "examples": rows[:limit]}


AUDIT_CHECKS = {
    "in_progress_missing_start": in_progress_missing_start,
    "high_cost_missing_contractor": high_cost_missing_contractor,
    "districts_high_not_started_share": districts_high_not_started_share,
    "category_cost_outliers": category_cost_outliers,
    "in_progress_without_tender": in_progress_without_tender,
}
