from __future__ import annotations

from agents.base_agent import BaseAgent, ToolSpec
from models.messages import AgentReport, AgentFinding, Evidence
from tools.finance_tools import district_statistics, category_statistics, find_cost_outliers
from tools.query_tools import aggregate_projects, filter_projects


class FinanceAgent(BaseAgent):
    """
    Why this agent exists: funding decisions need a grounded view of cost
    structure -- what's expensive, where budget is concentrated, and which
    categories still have a large share of unspent (Not Started) budget.
    This agent NEVER decides who gets funded; it only supplies financial
    evidence for the Coordinator.
    """
    agent_name = "Finance Agent"

    def _register_tools(self) -> None:
        self.tools = {
            "district_statistics": ToolSpec(
                "district_statistics", lambda: district_statistics(),
                "Per-district budget totals and Not-Started shares.", {}),
            "category_statistics": ToolSpec(
                "category_statistics", lambda: category_statistics(),
                "Per-category budget totals and Not-Started shares.", {}),
            "find_cost_outliers": ToolSpec(
                "find_cost_outliers", find_cost_outliers,
                "Find cost outliers using IQR within each category.",
                {"method": "str (optional)", "status": "str (optional)"}),
            "aggregate_projects": ToolSpec(
                "aggregate_projects", aggregate_projects,
                "Aggregate cost/progress with optional filters.",
                {"operation": "count|total_cost|average_cost|median_cost|min_cost|max_cost",
                 "status": "str (optional)", "category": "str (optional)", "district": "str (optional)"}),
            "filter_projects": ToolSpec(
                "filter_projects", filter_projects,
                "Return matching project rows (capped).",
                {"status": "str (optional)", "category": "str (optional)", "district": "str (optional)",
                 "min_cost": "float (optional)", "max_cost": "float (optional)", "limit": "int (optional)"}),
        }

    def system_prompt(self) -> str:
        return (
            "You are the Finance Agent on a government infrastructure project review board. "
            "Your job is to analyze the cost structure of the PMTS Projects portfolio: "
            "budget concentration, cost outliers, cost vs. progress, and whether an extra "
            "PKR 2,000M can be allocated efficiently among 'Not Started' projects. "
            "You must call tools to get real numbers -- never estimate or guess a figure yourself. "
            "Plan your checks, call tools, observe results, and only then write your findings."
        )

    def run_demo_plan(self, task: str) -> AgentReport:
        self.activity.log(self.agent_name, "PLAN: (1) portfolio totals (2) category budget shares "
                                            "(3) cost outliers (4) Not-Started financial exposure by category.")

        total_not_started = self._call_tool("aggregate_projects", {"operation": "total_cost", "status": "Not Started"})
        cat_stats = self._call_tool("category_statistics", {})
        outliers = self._call_tool("find_cost_outliers", {"status": None})

        findings: list[AgentFinding] = []

        # Finding 1: overall Not Started financial exposure
        findings.append(AgentFinding(
            agent_name=self.agent_name,
            finding_id="fin-not-started-exposure",
            title="Total financial exposure of Not Started projects",
            severity="medium",
            explanation=(
                f"Across the portfolio, Not Started projects total {total_not_started.value:.2f}M PKR "
                f"across {total_not_started.count} projects -- this is the pool the PKR 2,000M funding "
                f"decision will be drawn from."
            ),
            affected_projects=[],
            evidence=[Evidence(field="total_cost (Not Started)", value=total_not_started.value, source_tool="aggregate_projects")],
            recommendation="Prioritize categories with high Not-Started budget share and feasible per-project cost.",
        ))

        # Finding 2: category budget concentration among Not Started
        top_categories = sorted(cat_stats, key=lambda c: c.not_started_budget_m, reverse=True)[:3]
        findings.append(AgentFinding(
            agent_name=self.agent_name,
            finding_id="fin-category-concentration",
            title="Categories with the largest Not-Started financial backlog",
            severity="medium",
            explanation=(
                "The largest Not-Started budget backlogs are in: " +
                "; ".join(f"{c.category} ({c.not_started_budget_m:.1f}M across {c.not_started_count} projects)" for c in top_categories)
            ),
            affected_projects=[],
            evidence=[Evidence(field="not_started_budget_m", value=c.not_started_budget_m, source_tool="category_statistics") for c in top_categories],
            recommendation="Weight funding toward categories with large unmet financial backlog, subject to delivery readiness.",
        ))

        # Finding 3: cost outliers
        if outliers:
            top_outliers = outliers[:5]
            findings.append(AgentFinding(
                agent_name=self.agent_name,
                finding_id="fin-cost-outliers",
                title=f"{len(outliers)} project(s) flagged as cost outliers within their category",
                severity="high" if len(outliers) > 20 else "medium",
                explanation=(
                    f"Using an IQR method computed within each category, {len(outliers)} projects have costs "
                    f"well above their category's typical range. Example: {top_outliers[0].global_id} "
                    f"({top_outliers[0].category}) costs {top_outliers[0].cost_m:.1f}M vs. a category median of "
                    f"{top_outliers[0].category_median_m:.1f}M."
                ),
                affected_projects=[o.global_id for o in top_outliers],
                evidence=[Evidence(global_id=o.global_id, field="cost_m", value=o.cost_m, source_tool="find_cost_outliers") for o in top_outliers],
                recommendation="Review outlier projects for cost justification before including them in any funding round.",
            ))

        summary = (
            f"Finance review complete. Not-Started backlog totals {total_not_started.value:.1f}M across "
            f"{total_not_started.count} projects. {len(outliers)} cost outliers identified portfolio-wide. "
            f"Category backlogs are concentrated in {', '.join(c.category for c in top_categories)}."
        )

        return AgentReport(
            agent_name=self.agent_name,
            summary=summary,
            findings=findings,
            data_quality_notes=[],
            tool_calls=self.tool_log,
        )
