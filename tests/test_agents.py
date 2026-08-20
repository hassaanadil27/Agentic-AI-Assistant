import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.data_loader import load_projects
from agents.llm_provider import DemoProvider
from agents.base_agent import AgentActivityLogger
from agents.finance_agent import FinanceAgent
from agents.delivery_agent import DeliveryAgent
from agents.equity_agent import EquityAgent
from agents.coordinator_agent import CoordinatorAgent
from models.messages import AgentReport


def setup_module(module):
    load_projects(force_reload=True)


def test_finance_agent_returns_structured_report():
    activity = AgentActivityLogger()
    agent = FinanceAgent(DemoProvider(), True, activity)
    report = agent.run("Assess financial structure.")
    assert isinstance(report, AgentReport)
    assert report.agent_name == "Finance Agent"
    assert len(report.findings) > 0
    assert len(report.tool_calls) > 0


def test_delivery_agent_finds_multiple_risk_classes():
    activity = AgentActivityLogger()
    agent = DeliveryAgent(DemoProvider(), True, activity)
    report = agent.run("Assess delivery risk.")
    assert len(report.findings) >= 3  # multiple distinct risk classes


def test_equity_agent_returns_structured_report():
    activity = AgentActivityLogger()
    agent = EquityAgent(DemoProvider(), True, activity)
    report = agent.run("Assess equity.")
    assert isinstance(report, AgentReport)
    assert report.agent_name == "Equity Agent"


def test_agent_findings_reference_real_project_ids_when_present():
    from tools.data_loader import get_dataframe
    valid_ids = set(get_dataframe()["global_id"])

    activity = AgentActivityLogger()
    agent = DeliveryAgent(DemoProvider(), True, activity)
    report = agent.run("Assess delivery risk.")
    for finding in report.findings:
        for pid in finding.affected_projects:
            assert pid in valid_ids, f"Finding referenced a project ID not in the dataset: {pid}"


def test_coordinator_combines_all_three_specialist_reports():
    provider = DemoProvider()
    coordinator = CoordinatorAgent(provider, True)
    final_report, activity_log, specialist_reports = coordinator.run_review(budget_cap_m=2000.0)

    assert set(specialist_reports.keys()) == {"Finance Agent", "Delivery Agent", "Equity Agent"}
    assert len(final_report.finance_findings) > 0
    assert len(final_report.delivery_findings) > 0
    assert len(final_report.equity_findings) > 0
    # Activity log should show the plan -> act -> observe -> reason structure
    joined = " ".join(activity_log)
    assert "PLAN" in joined and "OBSERVE" in joined and "REASON" in joined and "STOP" in joined


def test_coordinator_produces_visible_conflicts():
    provider = DemoProvider()
    coordinator = CoordinatorAgent(provider, True)
    final_report, _, _ = coordinator.run_review(budget_cap_m=2000.0)
    # Not a hard requirement that conflicts exist for every possible budget,
    # but for the default PKR 2000M run against this dataset we expect at
    # least one genuine trade-off to surface.
    assert len(final_report.conflicts) >= 1
    for c in final_report.conflicts:
        assert c.coordinator_resolution
