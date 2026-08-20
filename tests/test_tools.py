import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.data_loader import load_projects, get_dataframe
from tools.query_tools import filter_projects, aggregate_projects, get_project
from tools.finance_tools import district_statistics, category_statistics, find_cost_outliers
from tools.delivery_tools import find_delivery_risks
from tools.equity_tools import find_equity_risks
from data_processing.normalizer import normalize_contractor, normalize_phone, normalize_agency, safe_float


def setup_module(module):
    load_projects(force_reload=True)


# --- numeric cleaning ---------------------------------------------------

def test_safe_float_valid():
    assert safe_float("12.5") == 12.5
    assert safe_float(7) == 7.0


def test_safe_float_invalid_returns_none_not_zero():
    assert safe_float("N/A") is None
    assert safe_float(None) is None


def test_cost_and_progress_are_numeric():
    df = get_dataframe()
    assert df["cost_m"].dtype.kind == "f"
    assert df["progress_pct"].dtype.kind == "f"


# --- filtering -----------------------------------------------------------

def test_filter_by_district_and_status():
    result = filter_projects(district="Awaran", status="Completed", limit=10)
    assert result.count >= 0
    for p in result.projects:
        assert p.district.lower() == "awaran"
        assert p.status.lower() == "completed"


def test_filter_by_category():
    result = filter_projects(category="Health", limit=5)
    for p in result.projects:
        assert p.category.lower() == "health"


def test_filter_truncation_flag():
    result = filter_projects(limit=5)  # no filters -> should truncate against full dataset
    assert result.truncated is True
    assert len(result.projects) == 5


# --- aggregation -----------------------------------------------------------

def test_aggregate_count_matches_filter_count():
    f = filter_projects(status="Not Started", limit=1)
    a = aggregate_projects(operation="count", status="Not Started")
    assert a.count == f.count


def test_aggregate_total_cost_not_started_matches_manual_sum():
    df = get_dataframe()
    manual_total = float(df[df["status"] == "Not Started"]["cost_m"].sum())
    a = aggregate_projects(operation="total_cost", status="Not Started")
    assert abs(a.value - manual_total) < 0.01


def test_aggregate_invalid_operation_raises():
    try:
        aggregate_projects(operation="not_a_real_op")
        assert False, "expected ValueError"
    except ValueError:
        pass


# --- get_project ----------------------------------------------------------

def test_get_project_found():
    df = get_dataframe()
    some_id = df.iloc[0]["global_id"]
    project = get_project(some_id)
    assert project is not None
    assert project.global_id == some_id


def test_get_project_not_found_returns_none():
    assert get_project("DOES-NOT-EXIST-99") is None


# --- district / category stats --------------------------------------------

def test_district_statistics_sums_to_total_budget():
    df = get_dataframe()
    stats = district_statistics()
    total = sum(s.total_budget_m for s in stats)
    assert abs(total - float(df["cost_m"].sum())) < 1.0


def test_category_statistics_nonempty():
    stats = category_statistics()
    assert len(stats) > 0
    assert all(s.project_count > 0 for s in stats)


# --- outliers ---------------------------------------------------------------

def test_cost_outliers_are_actually_above_fence():
    outliers = find_cost_outliers()
    for o in outliers:
        assert o.cost_m > o.category_q3_m


# --- delivery / equity risks --------------------------------------------------

def test_delivery_risks_reference_real_ids():
    df = get_dataframe()
    valid_ids = set(df["global_id"])
    risks = find_delivery_risks()
    assert len(risks) > 0
    assert all(r.global_id in valid_ids for r in risks[:20])


def test_equity_risks_have_positive_metric_values():
    risks = find_equity_risks()
    assert all(r.metric_value >= 0 for r in risks)


# --- normalizer unit tests -----------------------------------------------------

def test_normalize_contractor_removes_duplicated_ms_prefix():
    raw = 'M/S M/s Shahwani & Sons'
    result = normalize_contractor(raw)
    assert result.count("M/S") == 1


def test_normalize_contractor_strips_quotes():
    raw = '"M/S Firm Name'
    result = normalize_contractor(raw)
    assert '"' not in result


def test_normalize_agency_variants_map_to_canonical():
    assert normalize_agency("LGRD") == normalize_agency("Local Govt")
    assert normalize_agency("PHE") == normalize_agency("PHED")


def test_normalize_agency_unknown_passthrough():
    assert normalize_agency("Some Unmapped Agency") == "Some Unmapped Agency"


def test_normalize_phone_scientific_notation():
    normalized, needs_review = normalize_phone("9.23328E+11")
    assert needs_review is False
    assert normalized.startswith("+92")


def test_normalize_phone_leading_zero():
    normalized, needs_review = normalize_phone("0333-3773307")
    assert needs_review is False
    assert normalized == "+92-333-3773307"


def test_normalize_phone_ten_digit_no_prefix():
    normalized, needs_review = normalize_phone("3345417779")
    assert needs_review is False
    assert normalized.startswith("+92-334")


def test_normalize_phone_garbage_flagged_for_review():
    normalized, needs_review = normalize_phone("abc123")
    assert needs_review is True
