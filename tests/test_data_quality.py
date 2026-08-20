import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.data_loader import load_projects, get_dataframe
from tools.data_quality_tools import get_data_quality_report


def setup_module(module):
    load_projects(force_reload=True)


def test_missing_counts_match_dataframe():
    df = get_dataframe()
    report = get_data_quality_report()
    assert report.missing_contractor == int((~df["has_contractor"]).sum())
    assert report.missing_xen == int((~df["has_xen"]).sum())
    assert report.missing_work_started == int((~df["has_work_started"]).sum())


def test_report_totals_are_positive_and_bounded():
    df = get_dataframe()
    report = get_data_quality_report()
    assert 0 <= report.missing_contractor <= len(df)
    assert 0 <= report.missing_xen <= len(df)
    assert report.total_rows == len(df)


def test_agency_variant_groups_present():
    report = get_data_quality_report()
    assert "Local Government" in report.agency_variant_groups
    assert "Public Health Engineering" in report.agency_variant_groups


def test_duplicate_detection_runs_without_error():
    report = get_data_quality_report()
    assert isinstance(report.duplicate_global_ids, list)
