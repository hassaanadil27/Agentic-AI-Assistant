"""
Loads Projects.xlsx and produces a cleaned, type-safe pandas DataFrame.

This is the ONLY place raw Excel bytes are touched. Every tool downstream
operates on the DataFrame this module returns, never on the file directly.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from data_processing.normalizer import (
    normalize_contractor,
    normalize_agency,
    normalize_phone,
    safe_float,
)

logger = logging.getLogger(__name__)

EXPECTED_COLUMNS = [
    "#", "Global ID", "District", "Phase", "Category", "Description",
    "Executing Agency", "Cost (M)", "TSE", "Contractor", "NITs",
    "Progress %", "Status", "Work Started", "XEN Name", "XEN Contact",
]

VALID_STATUSES = {"Completed", "In Progress", "NITs Issued", "Not Started"}

# Column name -> internal snake_case name
COLUMN_MAP = {
    "#": "row_num",
    "Global ID": "global_id",
    "District": "district",
    "Phase": "phase",
    "Category": "category",
    "Description": "description",
    "Executing Agency": "executing_agency_raw",
    "Cost (M)": "cost_m_raw",
    "TSE": "tse",
    "Contractor": "contractor_raw",
    "NITs": "nits",
    "Progress %": "progress_pct_raw",
    "Status": "status",
    "Work Started": "work_started",
    "XEN Name": "xen_name",
    "XEN Contact": "xen_contact_raw",
}


class LoadResult:
    def __init__(self, df: pd.DataFrame, warnings: list[str]):
        self.df = df
        self.warnings = warnings


def load_and_clean_projects(path: str | Path, header_row_zero_indexed: int = 3) -> LoadResult:
    """
    Load Projects.xlsx, skip the 3-row banner, clean and normalize fields.

    Parameters
    ----------
    path: path to the .xlsx file
    header_row_zero_indexed: pandas `header=` index of the real header row
        (row 4 in the spreadsheet -> index 3). Exposed as a parameter, not
        hardcoded logic buried elsewhere, so it's easy to explain/adjust.

    Returns
    -------
    LoadResult with the cleaned DataFrame and a list of human-readable
    warnings encountered while loading (used in the data-quality report
    and shown in the UI).
    """
    warnings: list[str] = []
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found at {path}")

    raw = pd.read_excel(path, sheet_name="Projects List", header=header_row_zero_indexed)

    missing_cols = [c for c in EXPECTED_COLUMNS if c not in raw.columns]
    if missing_cols:
        warnings.append(
            f"Expected columns not found and will be treated as missing: {missing_cols}"
        )

    # Drop fully-empty rows (banner artifacts / trailing blank rows)
    before = len(raw)
    raw = raw.dropna(how="all")
    dropped = before - len(raw)
    if dropped:
        warnings.append(f"Dropped {dropped} fully-empty row(s).")

    df = raw.rename(columns=COLUMN_MAP).copy()

    # --- Numeric cleaning -------------------------------------------------
    df["cost_m"] = df.get("cost_m_raw").apply(safe_float)
    invalid_cost = df["cost_m"].isna().sum()
    if invalid_cost:
        warnings.append(f"{invalid_cost} row(s) had an unparseable Cost (M) value; kept as missing (NaN), not zero.")

    df["progress_pct"] = df.get("progress_pct_raw").apply(safe_float)
    invalid_progress = df["progress_pct"].isna().sum()
    if invalid_progress:
        warnings.append(f"{invalid_progress} row(s) had an unparseable Progress % value; kept as missing (NaN).")

    # --- Status normalization (trim only -- do not invent new categories) -
    df["status"] = df["status"].astype("string").str.strip()
    bad_status_mask = ~df["status"].isin(VALID_STATUSES) & df["status"].notna()
    if bad_status_mask.any():
        bad_vals = df.loc[bad_status_mask, "status"].unique().tolist()
        warnings.append(f"Unexpected Status values encountered (left as-is): {bad_vals}")

    # --- Text field trims ---------------------------------------------------
    for col in ["district", "phase", "category", "description", "global_id", "nits", "xen_name"]:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

    # --- Contractor normalization -------------------------------------------
    df["contractor_raw"] = df["contractor_raw"].astype("string")
    df["contractor_normalized"] = df["contractor_raw"].apply(normalize_contractor)
    df["has_contractor"] = df["contractor_normalized"].notna() & (df["contractor_normalized"].str.len() > 0)

    # --- Executing agency normalization -------------------------------------
    df["executing_agency_raw"] = df["executing_agency_raw"].astype("string")
    df["executing_agency"] = df["executing_agency_raw"].apply(normalize_agency)

    # --- XEN / accountability -----------------------------------------------
    df["has_xen"] = df["xen_name"].notna() & (df["xen_name"].str.len() > 0)

    # --- Phone normalization -------------------------------------------------
    phone_results = df["xen_contact_raw"].apply(normalize_phone)
    df["xen_contact_normalized"] = phone_results.apply(lambda t: t[0])
    df["xen_contact_needs_review"] = phone_results.apply(lambda t: t[1])

    # --- Work started ---------------------------------------------------------
    df["has_work_started"] = df["work_started"].notna()

    # --- Duplicate Global ID check ---------------------------------------------
    dup_mask = df["global_id"].duplicated(keep=False) & df["global_id"].notna()
    if dup_mask.any():
        dup_ids = sorted(df.loc[dup_mask, "global_id"].unique().tolist())
        warnings.append(f"{len(dup_ids)} duplicate Global ID value(s) found: {dup_ids[:10]}{'...' if len(dup_ids) > 10 else ''}")

    logger.info("Loaded %d project rows from %s", len(df), path)
    return LoadResult(df=df, warnings=warnings)
