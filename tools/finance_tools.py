"""
Tool 4: district_statistics
Tool 5: category_statistics
Tool 6: find_cost_outliers

Primarily used by the Finance Agent (and Equity Agent, for district_statistics).
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from tools.data_loader import get_dataframe
from models.schemas import DistrictStat, CategoryStat, OutlierResult


def district_statistics() -> list[DistrictStat]:
    """Tool 4. Per-district spend / pipeline statistics, computed from the
    live dataset (never hardcoded)."""
    df = get_dataframe()
    total_portfolio = float(df["cost_m"].sum(skipna=True))

    results: list[DistrictStat] = []
    for district, g in df.groupby("district", dropna=True):
        not_started = g[g["status"] == "Not Started"]
        project_count = len(g)
        total_budget = float(g["cost_m"].sum(skipna=True))
        results.append(
            DistrictStat(
                district=str(district),
                project_count=project_count,
                total_budget_m=round(total_budget, 2),
                avg_cost_m=round(float(g["cost_m"].mean(skipna=True)), 2) if project_count else 0.0,
                not_started_count=len(not_started),
                not_started_budget_m=round(float(not_started["cost_m"].sum(skipna=True)), 2),
                pct_not_started_by_count=round(100 * len(not_started) / project_count, 2) if project_count else 0.0,
                pct_of_portfolio_budget=round(100 * total_budget / total_portfolio, 2) if total_portfolio else 0.0,
            )
        )
    results.sort(key=lambda r: r.total_budget_m, reverse=True)
    return results


def category_statistics() -> list[CategoryStat]:
    """Tool 5. Per-category spend / pipeline statistics."""
    df = get_dataframe()

    results: list[CategoryStat] = []
    for category, g in df.groupby("category", dropna=True):
        not_started = g[g["status"] == "Not Started"]
        project_count = len(g)
        results.append(
            CategoryStat(
                category=str(category),
                project_count=project_count,
                total_budget_m=round(float(g["cost_m"].sum(skipna=True)), 2),
                avg_cost_m=round(float(g["cost_m"].mean(skipna=True)), 2) if project_count else 0.0,
                not_started_count=len(not_started),
                not_started_budget_m=round(float(not_started["cost_m"].sum(skipna=True)), 2),
            )
        )
    results.sort(key=lambda r: r.total_budget_m, reverse=True)
    return results


def find_cost_outliers(
    method: str = "iqr",
    iqr_multiplier: float = 1.5,
    min_group_size: int = 5,
    status: Optional[str] = None,
    limit: int = 30,
) -> list[OutlierResult]:
    """
    Tool 6. Find unusually expensive projects USING an IQR method computed
    within each category (so a school isn't compared against a road).
    Categories with fewer than `min_group_size` rows are skipped -- with too
    few points, quartiles aren't a statistically defensible signal, and we
    would rather report nothing than a misleading outlier.
    """
    df = get_dataframe()
    if status:
        df = df[df["status"].str.casefold() == status.casefold()]

    outliers: list[OutlierResult] = []
    for category, g in df.groupby("category", dropna=True):
        costs = g["cost_m"].dropna()
        if len(costs) < min_group_size:
            continue
        q1 = costs.quantile(0.25)
        q3 = costs.quantile(0.75)
        iqr = q3 - q1
        upper_fence = q3 + iqr_multiplier * iqr
        median = costs.median()

        flagged = g[g["cost_m"] > upper_fence]
        for _, row in flagged.iterrows():
            outliers.append(
                OutlierResult(
                    method=f"IQR (k={iqr_multiplier}) within category",
                    global_id=str(row["global_id"]),
                    category=str(category),
                    cost_m=round(float(row["cost_m"]), 2),
                    category_median_m=round(float(median), 2),
                    category_q1_m=round(float(q1), 2),
                    category_q3_m=round(float(q3), 2),
                    reason=(
                        f"Cost {row['cost_m']:.2f}M exceeds the category's upper fence "
                        f"({upper_fence:.2f}M = Q3 {q3:.2f}M + {iqr_multiplier}×IQR {iqr:.2f}M)."
                    ),
                )
            )

    outliers.sort(key=lambda o: o.cost_m, reverse=True)
    return outliers[:limit]
