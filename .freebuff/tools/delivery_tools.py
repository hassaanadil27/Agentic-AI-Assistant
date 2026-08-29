"""
Tool 7: find_delivery_risks

Used primarily by the Delivery Agent to autonomously discover pipeline /
accountability problems, mirroring the "red flags" listed in the
assignment brief (Track B/C).
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from tools.data_loader import get_dataframe
from models.schemas import DeliveryRisk


def find_delivery_risks(limit_per_type: int = 25) -> list[DeliveryRisk]:
    """
    Runs several independent, documented checks and returns offending rows.
    Each check corresponds to a real-world delivery/accountability concern:

      - in_progress_no_start_date : Status=In Progress but Work Started missing
      - in_progress_low_progress  : Status=In Progress but Progress% very low
      - missing_xen               : no responsible engineer on record
      - missing_contractor        : no contractor on record (any status but Not Started)
      - nits_status_mismatch      : NITs=No but Status=In Progress (work without a tender?)
      - stalled_high_cost         : Not Started AND high cost (top decile) -- capital idle
    """
    df = get_dataframe()
    risks: list[DeliveryRisk] = []

    def add(rows: pd.DataFrame, risk_type: str, detail_fn):
        for _, row in rows.head(limit_per_type).iterrows():
            risks.append(
                DeliveryRisk(
                    global_id=str(row["global_id"]),
                    risk_type=risk_type,
                    detail=detail_fn(row),
                    status=str(row["status"]),
                    progress_pct=float(row["progress_pct"]) if pd.notna(row["progress_pct"]) else 0.0,
                )
            )

    # 1. In Progress with no Work Started date
    r1 = df[(df["status"] == "In Progress") & (~df["has_work_started"])]
    add(r1, "in_progress_no_start_date",
        lambda row: "Status is 'In Progress' but no Work Started date is recorded.")

    # 2. In Progress with very low progress (<10%)
    r2 = df[(df["status"] == "In Progress") & (df["progress_pct"] < 10)]
    add(r2, "in_progress_low_progress",
        lambda row: f"Status is 'In Progress' but Progress is only {row['progress_pct']:.0f}%.")

    # 3. Missing XEN (accountability gap) -- flagged across any active status
    r3 = df[(~df["has_xen"]) & (df["status"] != "Completed")]
    add(r3, "missing_xen",
        lambda row: f"No XEN (responsible engineer) recorded; Status='{row['status']}'.")

    # 4. Missing contractor on a project that is not simply 'Not Started'
    r4 = df[(~df["has_contractor"]) & (df["status"].isin(["In Progress", "NITs Issued"]))]
    add(r4, "missing_contractor",
        lambda row: f"No contractor recorded despite Status='{row['status']}'.")

    # 5. NITs = No but Status = In Progress (work underway without a tender?)
    r5 = df[(df["nits"].str.casefold() == "no") & (df["status"] == "In Progress")]
    add(r5, "nits_status_mismatch",
        lambda row: "NITs (tender) marked 'No' but Status is 'In Progress' -- work may be underway without a formal tender.")

    # 6. Not Started + high cost (top decile of overall cost distribution)
    cost_90th = df["cost_m"].quantile(0.90)
    r6 = df[(df["status"] == "Not Started") & (df["cost_m"] >= cost_90th)]
    add(r6, "stalled_high_cost",
        lambda row: f"Not Started with cost {row['cost_m']:.2f}M, in the top decile of all project costs (>= {cost_90th:.2f}M).")

    return risks
