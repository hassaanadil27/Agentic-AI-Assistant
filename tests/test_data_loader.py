import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.data_loader import load_projects
from data_processing.cleaner import load_and_clean_projects

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "Projects.xlsx"


def test_excel_loads_and_finds_sheet():
    result = load_and_clean_projects(DATA_PATH)
    assert len(result.df) > 0


def test_header_row_is_correct():
    result = load_and_clean_projects(DATA_PATH)
    expected = {"global_id", "district", "category", "cost_m", "status", "progress_pct"}
    assert expected.issubset(set(result.df.columns))


def test_no_fully_empty_rows_remain():
    result = load_and_clean_projects(DATA_PATH)
    assert result.df.dropna(how="all").shape[0] == result.df.shape[0]


def test_metadata_matches_expected_scale():
    meta = load_projects(force_reload=True)
    # Sanity bounds rather than hardcoded exact numbers -- the assignment
    # explicitly forbids hardcoding assignment statistics into the app,
    # but a test asserting the loaded scale is reasonable is legitimate.
    assert 3500 <= meta.total_projects <= 4500
    assert 30 <= meta.districts <= 45
    assert meta.total_portfolio_m > 0
    assert sum(meta.status_counts.values()) == meta.total_projects
