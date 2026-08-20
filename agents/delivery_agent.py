from __future__ import annotations

from collections import Counter

from agents.base_agent import BaseAgent, ToolSpec
from models.messages import AgentReport, AgentFinding, Evidence
from tools.delivery_tools import find_delivery_risks
from tools.query_tools import aggregate_projects, filter_projects


class DeliveryAgent(BaseAgent):
    """
    Why this agent exists: a financially attractive project is worthless if
    it can't actually be delivered. This agent looks for stalled work,
    missing accountability (no XEN), and procurement inconsistencies --
    signals that a project is NOT ready to receive funding yet, even if
    its cost profile looks fine.
    """
    agent_name = "Delivery Agent"

    def _register_tools(self) -> None:
        self.tools = {
            "find_delivery_risks": ToolSpec(
                "find_delivery_risks", find_delivery_risks,
                "Run delivery/accountability risk checks across the portfolio.", {}),
            "aggregate_projects": ToolSpec(
                "aggregate_projects", aggregate_projects,
                "Aggregate count/cost/progress with optional filters.",
                {"operation": "count|total_cost|average_cost", "status": "str (optional)"}),
            "filter_projects": ToolSpec(
                "filter_projects", filter_projects,
                "Return matching project rows (capped).",
                {"status": "str (optional)", "has_xen": "bool (optional)",
                 "has_contractor": "bool (optional)", "limit": "int (optional)"}),
        }

    def system_prompt(self) -> str:
        return (
            "You are the Delivery Agent on a government infrastructure project review board. "
            "Your job is to find delivery and accountability risk: stalled projects, missing "
            "Work Started dates, missing XEN (responsible engineer), procurement (NITs) "
            "inconsistencies, and broken pipeline states. You must call tools to get real data -- "
            "never estimate a number yourself."
        )

    def run_demo_plan(self, task: str) -> AgentReport:
        self.activity.log(self.agent_name, "PLAN: (1) run full delivery risk sweep (2) group by risk type "
                                            "(3) assess overall procurement readiness for Not Started projects.")

        risks = self._call_tool("find_delivery_risks", {})
        not_started_with_nits = self._call_tool("aggregate_projects", {"operation": "count", "status": "Not Started"})
        nits_ready = self._call_tool("filter_projects", {"status": "Not Started", "limit": 1})

        by_type: dict[str, list] = {}
        for r in risks:
            by_type.setdefault(r.risk_type, []).append(r)

        findings: list[AgentFinding] = []
        severity_map = {
            "in_progress_no_start_date": "high",
            "missing_xen": "medium",
            "missing_contractor": "medium",
            "nits_status_mismatch": "high",
            "stalled_high_cost": "high",
            "in_progress_low_progress": "medium",
        }
        titles = {
            "in_progress_no_start_date": "In-Progress projects with no recorded start date",
            "missing_xen": "Projects with no accountable engineer (XEN) on record",
            "missing_contractor": "Active projects with no contractor recorded",
            "nits_status_mismatch": "Work apparently underway without a tender (NITs mismatch)",
            "stalled_high_cost": "High-cost Not Started projects (top decile) sitting idle",
            "in_progress_low_progress": "In-Progress projects with under 10% recorded progress",
        }

        for risk_type, items in by_type.items():
            findings.append(AgentFinding(
                agent_name=self.agent_name,
                finding_id=f"del-{risk_type}",
                title=f"{titles.get(risk_type, risk_type)} ({len(items)} found)",
                severity=severity_map.get(risk_type, "medium"),
                explanation=items[0].detail + f" This pattern was found in {len(items)} project(s) portfolio-wide.",
                affected_projects=[i.global_id for i in items[:10]],
                evidence=[Evidence(global_id=i.global_id, field="risk_detail", value=i.detail, source_tool="find_delivery_risks") for i in items[:5]],
                recommendation="Resolve before funding: assign accountability / confirm tender status / verify start dates.",
            ))

        # Which Not Started projects have flagged risks (missing_xen most relevant pre-start)
        risky_not_started_ids = {i.global_id for i in by_type.get("missing_xen", [])}

        summary = (
            f"Delivery review complete. {len(risks)} total risk instances found across "
            f"{len(by_type)} distinct risk categories: {', '.join(by_type.keys())}. "
            f"{len(risky_not_started_ids)} 'Not Started' projects already show an accountability gap "
            f"(no XEN) before work has even begun."
        )

        return AgentReport(
            agent_name=self.agent_name,
            summary=summary,
            findings=findings,
            data_quality_notes=[
                "Missing 'Work Started' dates and missing 'XEN Name' are common in this dataset; "
                "treated as genuine gaps, not assumed to be zero-risk.",
            ],
            tool_calls=self.tool_log,
        )
