import json

from agents.audit_agent import AuditAgent
from agents.llm_provider import LLMProvider, LLMResponse
from agents.query_agent import QueryAgent
from tools.audit_tools import AUDIT_CHECKS
from tools.query_tools import aggregate_projects, filter_projects, group_projects


class SequenceProvider(LLMProvider):
    def __init__(self, responses): self.responses = iter(responses)
    def complete(self, system_prompt, messages): return LLMResponse(next(self.responses))


class FailingProvider(LLMProvider):
    def complete(self, system_prompt, messages): raise RuntimeError("quota exhausted")


def test_track_a_query_agent_calls_tool_before_answering():
    provider = SequenceProvider([
        json.dumps({"action": "call_tool", "tool": "aggregate_projects", "arguments": {"operation": "total_cost", "status": "Not Started"}}),
        json.dumps({"action": "final_answer", "content": "The grounded total was computed with status=Not Started."}),
    ])
    result = QueryAgent(provider).ask("What is the total budget of Not Started projects?")
    assert any(line.startswith("ACT: aggregate_projects") for line in result.trace)
    assert any(line.startswith("OBSERVE:") for line in result.trace)


def test_track_b_agent_selects_and_executes_four_checks():
    checks = list(AUDIT_CHECKS)[:4]
    provider = SequenceProvider([
        json.dumps({"checks": checks, "rationale": "Cover delivery, finance and equity."}),
        "Prioritized grounded audit report",
    ])
    result = AuditAgent(provider).run("Find portfolio risks")
    assert result.plan == checks
    assert len(result.findings) == 4
    assert all("count" in finding for finding in result.findings)
    assert result.report == "Prioritized grounded audit report"


def test_track_a_four_brief_query_shapes_are_supported():
    water_kech = aggregate_projects("count", district="Kech", category="PHE", status="Completed")
    not_started = aggregate_projects("total_cost", status="Not Started")
    education_by_district = group_projects("district", "count", category="Education", limit=1)
    expensive_health = filter_projects(category="Health", limit=5, sort_by="cost_m", descending=True)
    assert water_kech.value is not None
    assert not_started.value and not_started.value > 0
    assert len(education_by_district) == 1
    assert len(expensive_health.projects) == 5
    costs = [project.cost_m for project in expensive_health.projects]
    assert costs == sorted(costs, reverse=True)


def test_track_a_removes_model_fabricated_default_filters():
    arguments = QueryAgent._sanitize_arguments(
        "aggregate_projects",
        {"operation": "total_cost", "status": "Not Started", "district": "", "min_cost": 0, "max_cost": 0, "has_xen": ""},
        "What is the total budget of all Not Started projects?",
    )
    assert arguments == {"operation": "total_cost", "status": "Not Started"}


def test_tracks_a_and_b_remain_grounded_when_api_is_unavailable():
    query = QueryAgent(FailingProvider()).ask("What is the total budget of all Not Started projects?")
    assert "PKR millions" in query.answer
    assert any(line.startswith("ACT: aggregate_projects") for line in query.trace)
    audit = AuditAgent(FailingProvider()).run("Find portfolio risks")
    assert len(audit.findings) >= 4
    assert "Prioritized portfolio audit" in audit.report
