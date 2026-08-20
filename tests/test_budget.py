import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.data_loader import load_projects
from tools.ranking_tools import rank_funding_candidates, select_within_budget


def setup_module(module):
    load_projects(force_reload=True)


def test_selection_never_exceeds_budget_cap():
    ranked = rank_funding_candidates()
    for cap in [500.0, 1000.0, 2000.0, 5000.0]:
        selected = select_within_budget(ranked, budget_cap_m=cap)
        total = sum(c.cost_m for c in selected)
        assert total <= cap, f"Selected total {total} exceeded cap {cap}"


def test_selection_only_includes_not_started_projects():
    from tools.data_loader import get_dataframe
    df = get_dataframe()
    not_started_ids = set(df[df["status"] == "Not Started"]["global_id"])

    ranked = rank_funding_candidates()
    selected = select_within_budget(ranked, budget_cap_m=2000.0)
    for c in selected:
        assert c.global_id in not_started_ids


def test_ranking_produces_documented_score_range():
    ranked = rank_funding_candidates()
    for c in ranked[:50]:
        assert 0.0 <= c.finance_score <= 100.0
        assert 0.0 <= c.delivery_score <= 100.0
        assert 0.0 <= c.equity_score <= 100.0
        assert 0.0 <= c.final_score <= 100.0


def test_selection_is_deterministic_given_same_data():
    ranked1 = rank_funding_candidates()
    ranked2 = rank_funding_candidates()
    sel1 = select_within_budget(ranked1, budget_cap_m=2000.0)
    sel2 = select_within_budget(ranked2, budget_cap_m=2000.0)
    assert [c.global_id for c in sel1] == [c.global_id for c in sel2]
