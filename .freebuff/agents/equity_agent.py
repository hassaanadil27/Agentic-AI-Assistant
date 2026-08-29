from __future__ import annotations

from agents.base_agent import BaseAgent, ToolSpec
from models.messages import AgentReport, AgentFinding, Evidence
from tools.equity_tools import find_equity_risks
from tools.finance_tools import district_statistics, category_statistics


class EquityAgent(BaseAgent):
    """
    Why this agent exists: without an explicit check, funding tends to
    flow to already-large districts/categories simply because they have
    more candidate projects. This agent surfaces measurable concentration
    and under-allocation so the Coordinator can weigh fairness alongside
    cost and delivery readiness. All claims here are strictly about
    measured budget/project shares -- never about a district's poverty or
    need beyond what the dataset can support.
    """
    agent_name = "Equity Agent"

    def _register_tools(self) -> None:
        self.tools = {
            "find_equity_risks": ToolSpec(
                "find_equity_risks", find_equity_risks,
                "Run comparative district/category concentration checks.", {}),
            "district_statistics": ToolSpec(
                "district_statistics", lambda: district_statistics(),
                "Per-district budget and Not-Started statistics.", {}),
            "category_statistics": ToolSpec(
                "category_statistics", lambda: category_statistics(),
                "Per-category budget and Not-Started statistics.", {}),
        }

    def system_prompt(self) -> str:
        return (
            "You are the Equity Agent on a government infrastructure project review board. "
            "Your job is to check whether districts and categories are treated fairly in terms "
            "of measurable budget and project-count shares -- concentration in a few districts, "
            "categories neglected in some areas, districts with almost no allocated budget. "
            "Only make claims that are directly supported by computed statistics -- never "
            "characterize a district's poverty or social need beyond what the data shows."
        )

    def run_demo_plan(self, task: str) -> AgentReport:
        self.activity.log(self.agent_name, "PLAN: (1) district budget shares (2) category concentration "
                                            "(3) districts with high Not-Started share (execution lag) "
                                            "(4) under-allocated districts.")

        risks = self._call_tool("find_equity_risks", {})
        d_stats = self._call_tool("district_statistics", {})

        by_type: dict[str, list] = {}
        for r in risks:
            by_type.setdefault(r.risk_type, []).append(r)

        findings: list[AgentFinding] = []
        titles = {
            "district_budget_concentration": "Districts holding a disproportionately large share of total budget",
            "district_low_allocation": "Districts holding a very small share of total portfolio budget",
            "district_not_started_share": "Districts where a large share of their own budget is still Not Started",
            "category_concentration": "Categories dominating the total portfolio budget",
        }
        severity_map = {
            "district_budget_concentration": "medium",
            "district_low_allocation": "high",
            "district_not_started_share": "medium",
            "category_concentration": "low",
        }

        for risk_type, items in by_type.items():
            findings.append(AgentFinding(
                agent_name=self.agent_name,
                finding_id=f"eq-{risk_type}",
                title=f"{titles.get(risk_type, risk_type)} ({len(items)} found)",
                severity=severity_map.get(risk_type, "medium"),
                explanation="; ".join(i.detail for i in items[:5]),
                affected_projects=[],
                evidence=[Evidence(field=risk_type, value=i.metric_value, source_tool="find_equity_risks") for i in items[:5]],
                recommendation="Favor under-allocated districts, holding cost and delivery-readiness constant, when ranking candidates.",
            ))

        under_allocated = sorted(d_stats, key=lambda d: d.pct_of_portfolio_budget)[:5]

        summary = (
            f"Equity review complete. {len(risks)} comparative concentration/allocation signals found "
            f"across {len(by_type)} risk categories. Most under-allocated districts by budget share: "
            + ", ".join(f"{d.district} ({d.pct_of_portfolio_budget:.2f}%)" for d in under_allocated) + "."
        )

        return AgentReport(
            agent_name=self.agent_name,
            summary=summary,
            findings=findings,
            data_quality_notes=[
                "Equity findings are based purely on measured budget/project-count shares within this "
                "dataset; they do not represent an independent poverty or needs assessment.",
            ],
            tool_calls=self.tool_log,
        )
