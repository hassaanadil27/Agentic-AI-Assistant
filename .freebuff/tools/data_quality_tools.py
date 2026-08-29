"""
Data quality report tool (Section 15 of the assignment).
Surfaces the messiness of the raw file in one structured object, used by
the UI and referenced by agents in their data_quality_notes.
"""
from __future__ import annotations

from tools.data_loader import get_dataframe
from data_processing.normalizer import AGENCY_VARIANT_GROUPS
from models.schemas import DataQualityReport


def get_data_quality_report() -> DataQualityReport:
    df = get_dataframe()

    missing_contractor = int((~df["has_contractor"]).sum())
    missing_xen = int((~df["has_xen"]).sum())
    missing_work_started = int((~df["has_work_started"]).sum())
    invalid_cost = int(df["cost_m"].isna().sum())
    invalid_progress = int(df["progress_pct"].isna().sum())

    dup_mask = df["global_id"].duplicated(keep=False) & df["global_id"].notna()
    duplicate_ids = sorted(df.loc[dup_mask, "global_id"].unique().tolist())

    # Contractor variant examples: raw vs normalized, where they differ
    diff_mask = (
        df["contractor_raw"].notna()
        & df["contractor_normalized"].notna()
        & (df["contractor_raw"].astype(str) != df["contractor_normalized"].astype(str))
    )
    contractor_examples = [
        {"raw": str(r["contractor_raw"]), "normalized": str(r["contractor_normalized"])}
        for _, r in df.loc[diff_mask].head(10).iterrows()
    ]

    phone_examples = [
        {"global_id": str(r["global_id"]), "raw": str(r["xen_contact_raw"])}
        for _, r in df.loc[df["xen_contact_needs_review"] == True].head(10).iterrows()  # noqa: E712
    ]

    return DataQualityReport(
        total_rows=len(df),
        missing_contractor=missing_contractor,
        missing_xen=missing_xen,
        missing_work_started=missing_work_started,
        invalid_cost_count=invalid_cost,
        invalid_progress_count=invalid_progress,
        duplicate_global_ids=duplicate_ids,
        agency_variant_groups=AGENCY_VARIANT_GROUPS,
        contractor_variant_examples=contractor_examples,
        suspicious_phone_examples=phone_examples,
    )
