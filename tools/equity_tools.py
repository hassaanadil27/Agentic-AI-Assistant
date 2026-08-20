"""
Tool 8: find_equity_risks

Used by the Equity Agent. All claims are strictly comparative/statistical
(share of budget, share of projects) -- the tool never characterizes a
district's socioeconomic status, only what's measurable in the dataset.
"""
from __future__ import annotations

from models.schemas import EquityRisk
from tools.finance_tools import district_statistics, category_statistics


def find_equity_risks(
    concentration_threshold_pct: float = 8.0,
    low_allocation_threshold_pct: float = 1.0,
    not_started_share_threshold_pct: float = 60.0,
) -> list[EquityRisk]:
    """
    Runs comparative checks across districts and categories:

      - district_budget_concentration : a single district holds a large
        share of total portfolio budget (possible over-concentration)
      - district_low_allocation       : a district holds a very small share
        of total budget relative to the 39-district average
      - district_not_started_share    : a district has a very high share of
        its OWN budget still Not Started (execution lag, not poverty)
      - category_concentration        : a single category dominates total
        portfolio budget
    """
    risks: list[EquityRisk] = []

    d_stats = district_statistics()
    c_stats = category_statistics()

    total_budget = sum(d.total_budget_m for d in d_stats)
    n_districts = len(d_stats)
    fair_share_pct = 100.0 / n_districts if n_districts else 0.0

    for d in d_stats:
        if d.pct_of_portfolio_budget >= concentration_threshold_pct:
            risks.append(EquityRisk(
                risk_type="district_budget_concentration",
                subject=d.district,
                detail=(
                    f"{d.district} holds {d.pct_of_portfolio_budget:.2f}% of total portfolio "
                    f"budget ({d.total_budget_m:.1f}M), versus an equal-share benchmark of "
                    f"{fair_share_pct:.2f}% across {n_districts} districts."
                ),
                metric_value=d.pct_of_portfolio_budget,
            ))
        if d.pct_of_portfolio_budget <= low_allocation_threshold_pct:
            risks.append(EquityRisk(
                risk_type="district_low_allocation",
                subject=d.district,
                detail=(
                    f"{d.district} holds only {d.pct_of_portfolio_budget:.2f}% of total portfolio "
                    f"budget, well below the equal-share benchmark of {fair_share_pct:.2f}%."
                ),
                metric_value=d.pct_of_portfolio_budget,
            ))
        if d.pct_not_started_by_count >= not_started_share_threshold_pct and d.project_count >= 5:
            risks.append(EquityRisk(
                risk_type="district_not_started_share",
                subject=d.district,
                detail=(
                    f"{d.pct_not_started_by_count:.1f}% of {d.district}'s {d.project_count} projects "
                    f"are still 'Not Started' ({d.not_started_count} projects, "
                    f"{d.not_started_budget_m:.1f}M budget)."
                ),
                metric_value=d.pct_not_started_by_count,
            ))

    total_cat_budget = sum(c.total_budget_m for c in c_stats)
    for c in c_stats:
        share = 100 * c.total_budget_m / total_cat_budget if total_cat_budget else 0.0
        if share >= 30.0:
            risks.append(EquityRisk(
                risk_type="category_concentration",
                subject=c.category,
                detail=(
                    f"Category '{c.category}' accounts for {share:.2f}% of total portfolio budget "
                    f"({c.total_budget_m:.1f}M of {total_cat_budget:.1f}M)."
                ),
                metric_value=round(share, 2),
            ))

    return risks
