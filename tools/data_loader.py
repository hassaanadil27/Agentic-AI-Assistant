"""
Tool 1: load_projects

Loads and caches the cleaned dataset for the whole process. All other
tools call get_dataframe() to access the SAME cleaned data rather than
re-reading the Excel file, keeping results consistent within one run.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from data_processing.cleaner import load_and_clean_projects
from models.schemas import DatasetMetadata

_CACHE: dict[str, object] = {"df": None, "warnings": None, "path": None}

DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "Projects.xlsx"


def load_projects(path: Optional[str] = None, force_reload: bool = False) -> DatasetMetadata:
    """
    Load (or return cached) project data and return dataset-level metadata.
    This is the tool the agents call at the start of a run.
    """
    target_path = Path(path) if path else DEFAULT_DATA_PATH

    if _CACHE["df"] is None or force_reload or _CACHE["path"] != str(target_path):
        result = load_and_clean_projects(target_path)
        _CACHE["df"] = result.df
        _CACHE["warnings"] = result.warnings
        _CACHE["path"] = str(target_path)

    df: pd.DataFrame = _CACHE["df"]  # type: ignore

    status_counts = df["status"].value_counts(dropna=False).to_dict()
    status_counts = {str(k): int(v) for k, v in status_counts.items()}

    return DatasetMetadata(
        total_projects=len(df),
        total_portfolio_m=round(float(df["cost_m"].sum(skipna=True)), 2),
        districts=int(df["district"].nunique(dropna=True)),
        categories=int(df["category"].nunique(dropna=True)),
        status_counts=status_counts,
        load_warnings=list(_CACHE["warnings"]),  # type: ignore
    )


def get_dataframe(path: Optional[str] = None) -> pd.DataFrame:
    """Internal accessor used by other tool modules. Ensures data is loaded."""
    if _CACHE["df"] is None:
        load_projects(path)
    return _CACHE["df"]  # type: ignore


def get_load_warnings() -> list[str]:
    if _CACHE["warnings"] is None:
        load_projects()
    return list(_CACHE["warnings"])  # type: ignore
