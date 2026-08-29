"""
Tool 10: rank_funding_candidates

Transparent, documented scoring system used by the Coordinator to rank
'Not Started' projects as candidates for the extra PKR 2,000M.

SCORING METHODOLOGY (documented per assignment Section 12)
------------------------------------------------------------
Final Score (0-100) = 0.35 * FinanceScore + 0.35 * DeliveryScore + 0.30 * EquityScore

Weights (35% Finance / 35% Delivery / 30% Equity) reflect that financial
feasibility and delivery readiness are equally decisive for whether money
spent will actually turn into a finished project, while equity is a real
but slightly softer policy consideration -- it should influence ranking,
not dominate it. Weights are named constants below, not buried magic
numbers, and can be changed in one place.

FinanceScore (0-100):
  - cost_feasibility: rewards lower cost relative to the remaining budget
    envelope (cheaper projects "fit" more easily and let more projects be
    funded) -- linearly scaled, cost==0 -> 100, cost>=cap -> 0.
  - category_need: rewards categories with a high share of their OWN
    budget still Not Started (i.e., funding here clears a real backlog)
    using each category's own not-started share, scaled 0-100.
  Finance = 0.6 * cost_feasibility + 0.4 * category_need

DeliveryScore (0-100), starts at 100 and is PENALIZED for missing
readiness signals (documented, not hidden):
  - -25 if NITs != 'Yes' (no tender issued yet -> less procurement-ready)
  - -20 if no XEN assigned (no accountable engineer on record)
  - -15 if Executing Agency is missing
  Floor at 0.

EquityScore (0-100):
  - Rewards districts with a LOWER existing share of total portfolio
    budget (pct_of_portfolio_budget) -- i.e. currently under-allocated
    districts score higher. Linearly scaled against the observed max
    district share in the dataset.

Missing critical information (no contractor is EXPECTED and normal for
Not Started projects, so it is NOT penalized here -- only NITs/XEN/agency,
which represent genuine readiness gaps even before construction starts).
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from tools.data_loader import get_dataframe
from tools.finance_tools import district_statistics, category_statistics

FINANCE_WEIGHT = 0.35
DELIVERY_WEIGHT = 0.35
EQUITY_WEIGHT = 0.30

NITS_PENALTY = 25
MISSING_XEN_PENALTY = 20
MISSING_AGENCY_PENALTY = 15


class RankedCandidate:
    def __init__(self, global_id: str, district: str, category: str,
                 description: str, cost_m: float, finance_score: float,
                 delivery_score: float, equity_score: float, final_score: float,
                 finance_reason: str, delivery_reason: str, equity_reason: str):
        self.global_id = global_id
        self.district = district
        self.category = category
        self.description = description
        self.cost_m = cost_m
        self.finance_score = finance_score
        self.delivery_score = delivery_score
        self.equity_score = equity_score
        self.final_score = final_score
        self.finance_reason = finance_reason
        self.delivery_reason = delivery_reason
        self.equity_reason = equity_reason

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def rank_funding_candidates(budget_cap_m: float = 2000.0) -> list[RankedCandidate]:
    """Score and rank every 'Not Started' project. Does NOT apply the budget
    constraint itself (that's the Coordinator's job via a greedy knapsack-style
    selection) -- this tool only produces a transparent, ordered candidate list."""
    df = get_dataframe()
    candidates = df[df["status"] == "Not Started"].copy()
    if candidates.empty:
        return []

    d_stats = {d.district: d for d in district_statistics()}
    c_stats = {c.category: c for c in category_statistics()}

    max_cost = float(candidates["cost_m"].max(skipna=True)) or 1.0
    max_district_share = max((d.pct_of_portfolio_budget for d in d_stats.values()), default=1.0) or 1.0

    ranked: list[RankedCandidate] = []
    for _, row in candidates.iterrows():
        cost = float(row["cost_m"]) if pd.notna(row["cost_m"]) else 0.0

        # --- Finance score ---
        cost_feasibility = max(0.0, 100.0 * (1 - min(cost, max_cost) / max_cost))
        cat = c_stats.get(row["category"])
        if cat and cat.total_budget_m > 0:
            category_need = 100.0 * (cat.not_started_budget_m / cat.total_budget_m)
        else:
            category_need = 0.0
        finance_score = 0.6 * cost_feasibility + 0.4 * category_need
        finance_reason = (
            f"Cost {cost:.2f}M (feasibility {cost_feasibility:.0f}/100 relative to max Not-Started "
            f"cost {max_cost:.2f}M); category '{row['category']}' has {category_need:.0f}% of its own "
            f"budget still Not Started (need score)."
        )

        # --- Delivery score ---
        delivery_score = 100.0
        penalties = []
        if str(row.get("nits", "")).strip().casefold() != "yes":
            delivery_score -= NITS_PENALTY
            penalties.append(f"-{NITS_PENALTY} (no tender/NITs issued)")
        if not bool(row.get("has_xen", False)):
            delivery_score -= MISSING_XEN_PENALTY
            penalties.append(f"-{MISSING_XEN_PENALTY} (no XEN assigned)")
        if pd.isna(row.get("executing_agency")):
            delivery_score -= MISSING_AGENCY_PENALTY
            penalties.append(f"-{MISSING_AGENCY_PENALTY} (no executing agency recorded)")
        delivery_score = max(0.0, delivery_score)
        delivery_reason = "Starts at 100; " + (", ".join(penalties) if penalties else "no readiness penalties applied.")

        # --- Equity score ---
        dstat = d_stats.get(row["district"])
        district_share = dstat.pct_of_portfolio_budget if dstat else 0.0
        equity_score = 100.0 * (1 - min(district_share, max_district_share) / max_district_share)
        equity_reason = (
            f"District '{row['district']}' currently holds {district_share:.2f}% of total portfolio "
            f"budget (max observed district share: {max_district_share:.2f}%); lower share -> higher equity score."
        )

        final_score = (
            FINANCE_WEIGHT * finance_score
            + DELIVERY_WEIGHT * delivery_score
            + EQUITY_WEIGHT * equity_score
        )

        ranked.append(RankedCandidate(
            global_id=str(row["global_id"]),
            district=str(row["district"]),
            category=str(row["category"]),
            description=str(row["description"]),
            cost_m=round(cost, 2),
            finance_score=round(finance_score, 2),
            delivery_score=round(delivery_score, 2),
            equity_score=round(equity_score, 2),
            final_score=round(final_score, 2),
            finance_reason=finance_reason,
            delivery_reason=delivery_reason,
            equity_reason=equity_reason,
        ))

    ranked.sort(key=lambda r: r.final_score, reverse=True)
    return ranked


def select_within_budget(
    ranked: list[RankedCandidate],
    budget_cap_m: float = 2000.0,
    max_district_share_of_fund: float = 0.35,
    max_category_share_of_fund: float = 0.45,
) -> list[RankedCandidate]:
    """
    Greedy selection down the ranked list, skipping any candidate that would:
      (a) exceed the total budget cap, or
      (b) push a single district's share of the *newly allocated* funds
          above max_district_share_of_fund, or
      (c) push a single category's share of the *newly allocated* funds
          above max_category_share_of_fund.

    (b) and (c) directly implement the assignment's requirement to control
    district/category concentration in the final recommendation.
    """
    selected: list[RankedCandidate] = []
    spent = 0.0
    district_spend: dict[str, float] = {}
    category_spend: dict[str, float] = {}

    for cand in ranked:
        if spent + cand.cost_m > budget_cap_m:
            continue

        projected_total = spent + cand.cost_m
        projected_district = district_spend.get(cand.district, 0.0) + cand.cost_m
        projected_category = category_spend.get(cand.category, 0.0) + cand.cost_m

        if projected_total > 0 and (projected_district / projected_total) > max_district_share_of_fund and projected_total > 200:
            continue
        if projected_total > 0 and (projected_category / projected_total) > max_category_share_of_fund and projected_total > 200:
            continue

        selected.append(cand)
        spent += cand.cost_m
        district_spend[cand.district] = district_spend.get(cand.district, 0.0) + cand.cost_m
        category_spend[cand.category] = category_spend.get(cand.category, 0.0) + cand.cost_m

    return selected
