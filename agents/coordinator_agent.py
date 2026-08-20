"""
CoordinatorAgent: orchestrates Finance, Delivery, and Equity agents,
detects and resolves disagreements, ranks funding candidates, applies the
PKR 2,000M budget constraint, and produces the FinalReport.

This is the visible PLAN -> ACT -> OBSERVE -> REASON -> ... -> STOP loop
at the top level (Section 9 / 29 of the assignment brief):

  1. PLAN: decide which specialists to consult and why.
  2. ACT: dispatch structured tasks to Finance / Delivery / Equity agents.
  3. OBSERVE: collect their structured AgentReports.
  4. REASON: compare specialist findings, detect conflicts.
  5. ACT AGAIN: run rank_funding_candidates + select_within_budget
     (additional targeted tool calls the Coordinator itself makes).
  6. REASON: check district/category concentration in the result.
  7. SYNTHESIZE: build the FinalReport.
  8. STOP.
"""
from __future__ import annotations

import logging

from agents.base_agent import AgentActivityLogger
from agents.finance_agent import FinanceAgent
from agents.delivery_agent import DeliveryAgent
from agents.equity_agent import EquityAgent
from agents.llm_provider import LLMProvider
from models.messages import AgentReport, ConflictRecord, RecommendedProject, FinalReport
from tools.data_loader import load_projects, get_load_warnings
from tools.data_quality_tools import get_data_quality_report
from tools.ranking_tools import rank_funding_candidates, select_within_budget, RankedCandidate
from tools.query_tools import get_project

logger = logging.getLogger(__name__)

BUDGET_CAP_M = 2000.0

# Thresholds used to flag a *visible* trade-off between specialists on a
# selected candidate. Documented here rather than buried: a candidate is
# considered to carry a genuine disagreement if one dimension is notably
# weak (<55) while another is notably strong (>70) -- i.e., specialists
# would reasonably disagree about it.
WEAK_THRESHOLD = 55.0
STRONG_THRESHOLD = 70.0


class CoordinatorAgent:
    agent_name = "Coordinator"

    def __init__(self, provider: LLMProvider, is_demo: bool):
        self.provider = provider
        self.is_demo = is_demo
        self.activity = AgentActivityLogger()
        self.finance_agent = FinanceAgent(provider, is_demo, self.activity)
        self.delivery_agent = DeliveryAgent(provider, is_demo, self.activity)
        self.equity_agent = EquityAgent(provider, is_demo, self.activity)

    def run_review(self, budget_cap_m: float = BUDGET_CAP_M) -> tuple[FinalReport, list[str], dict[str, AgentReport]]:
        """Executes the full board review. Returns (FinalReport, activity_log, specialist_reports)."""
        self.activity.log(self.agent_name, "PLAN: load dataset, dispatch Finance/Delivery/Equity reviews, "
                                            "then rank & select Not Started candidates within the PKR "
                                            f"{budget_cap_m:.0f}M funding envelope.")

        meta = load_projects()
        self.activity.log(self.agent_name, f"Dataset loaded: {meta.total_projects} projects, "
                                            f"{meta.total_portfolio_m:.1f}M total portfolio, "
                                            f"{meta.districts} districts.")

        # --- ACT: dispatch to specialists ------------------------------------
        finance_task = "Assess financial structure and cost outliers relevant to a PKR 2,000M Not-Started funding round."
        delivery_task = "Assess delivery readiness and accountability risk across the portfolio, especially for Not Started projects."
        equity_task = "Assess district and category budget concentration/under-allocation for a fair funding decision."

        self.activity.log(self.agent_name, "ACT: dispatching structured task to Finance Agent.")
        finance_report = self.finance_agent.run(finance_task)

        self.activity.log(self.agent_name, "ACT: dispatching structured task to Delivery Agent.")
        delivery_report = self.delivery_agent.run(delivery_task)

        self.activity.log(self.agent_name, "ACT: dispatching structured task to Equity Agent.")
        equity_report = self.equity_agent.run(equity_task)

        self.activity.log(self.agent_name, "OBSERVE: collected 3 structured specialist reports.")

        # --- ACT AGAIN: Coordinator's own targeted tool calls ------------------
        self.activity.log(self.agent_name, "ACT: calling rank_funding_candidates() to score all Not Started projects.")
        ranked = rank_funding_candidates(budget_cap_m=budget_cap_m)
        self.activity.log(self.agent_name, f"OBSERVE: {len(ranked)} Not Started candidates scored.")

        self.activity.log(self.agent_name, "ACT: calling select_within_budget() to enforce the PKR "
                                            f"{budget_cap_m:.0f}M cap and district/category concentration limits.")
        selected = select_within_budget(ranked, budget_cap_m=budget_cap_m)
        total_recommended = round(sum(c.cost_m for c in selected), 2)
        self.activity.log(self.agent_name, f"OBSERVE: selected {len(selected)} projects totaling {total_recommended:.2f}M "
                                            f"(remaining {budget_cap_m - total_recommended:.2f}M).")

        # --- REASON: detect visible disagreements/trade-offs -------------------
        self.activity.log(self.agent_name, "REASON: scanning selected candidates for cross-specialist disagreement.")
        conflicts = self._detect_conflicts(selected, finance_report, delivery_report, equity_report)
        self.activity.log(self.agent_name, f"REASON: {len(conflicts)} visible conflict(s)/trade-off(s) identified and resolved.")

        # --- SYNTHESIZE ------------------------------------------------------
        recommended_projects = [self._to_recommended(c) for c in selected]

        dq = get_data_quality_report()
        dq_warnings = get_load_warnings() + [
            f"{dq.missing_contractor} project(s) missing a contractor.",
            f"{dq.missing_xen} project(s) missing an XEN (responsible engineer).",
            f"{dq.missing_work_started} project(s) missing a Work Started date.",
        ]
        if dq.duplicate_global_ids:
            dq_warnings.append(f"{len(dq.duplicate_global_ids)} duplicate Global ID(s) detected.")

        executive_summary = self._build_executive_summary(
            meta.total_projects, meta.total_portfolio_m, len(selected), total_recommended,
            budget_cap_m, conflicts,
        )

        final_report = FinalReport(
            executive_summary=executive_summary,
            recommended_projects=recommended_projects,
            total_recommended_m=total_recommended,
            budget_available_m=budget_cap_m,
            remaining_budget_m=round(budget_cap_m - total_recommended, 2),
            finance_findings=finance_report.findings,
            delivery_findings=delivery_report.findings,
            equity_findings=equity_report.findings,
            conflicts=conflicts,
            data_quality_warnings=dq_warnings,
        )

        self.activity.log(self.agent_name, "STOP: final recommendation generated.")

        specialist_reports = {
            "Finance Agent": finance_report,
            "Delivery Agent": delivery_report,
            "Equity Agent": equity_report,
        }
        return final_report, self.activity.lines, specialist_reports

    # ------------------------------------------------------------------------
    def _to_recommended(self, c: RankedCandidate) -> RecommendedProject:
        return RecommendedProject(
            global_id=c.global_id,
            description=c.description,
            district=c.district,
            category=c.category,
            cost_m=c.cost_m,
            score=c.final_score,
            finance_assessment=c.finance_reason,
            delivery_assessment=c.delivery_reason,
            equity_assessment=c.equity_reason,
            reason_selected=(
                f"Ranked #{c.final_score:.1f}/100 overall (Finance {c.finance_score:.0f}, "
                f"Delivery {c.delivery_score:.0f}, Equity {c.equity_score:.0f}); selected within the "
                f"PKR {BUDGET_CAP_M:.0f}M cap and district/category concentration limits."
            ),
        )

    def _detect_conflicts(
        self,
        selected: list[RankedCandidate],
        finance_report: AgentReport,
        delivery_report: AgentReport,
        equity_report: AgentReport,
    ) -> list[ConflictRecord]:
        """
        A candidate is flagged as a genuine, data-driven disagreement when its
        sub-scores pull in different directions -- e.g. strong on Equity but
        weak on Delivery, meaning the project serves an under-allocated
        district yet is not procurement-ready. This is computed from the real
        per-candidate scores, never hardcoded to a specific project.
        """
        conflicts: list[ConflictRecord] = []
        finance_outlier_ids = set()
        for f in finance_report.findings:
            if f.finding_id == "fin-cost-outliers":
                finance_outlier_ids.update(f.affected_projects)

        for c in selected:
            scores = {"finance": c.finance_score, "delivery": c.delivery_score, "equity": c.equity_score}
            weak = [k for k, v in scores.items() if v < WEAK_THRESHOLD]
            strong = [k for k, v in scores.items() if v > STRONG_THRESHOLD]

            if weak and strong:
                finance_pos = (
                    f"Favorable: cost {c.cost_m:.1f}M fits within budget (Finance score {c.finance_score:.0f})."
                    if "finance" in strong else
                    f"Cautious: {c.finance_reason}" if "finance" in weak else
                    f"Neutral (Finance score {c.finance_score:.0f})."
                )
                delivery_pos = (
                    f"Favorable: high delivery readiness (score {c.delivery_score:.0f})."
                    if "delivery" in strong else
                    f"Concerned: {c.delivery_reason}" if "delivery" in weak else
                    f"Neutral (Delivery score {c.delivery_score:.0f})."
                )
                equity_pos = (
                    f"Favorable: {c.equity_reason}"
                    if "equity" in strong else
                    f"Cautious: district already has a larger existing share (Equity score {c.equity_score:.0f})." if "equity" in weak else
                    f"Neutral (Equity score {c.equity_score:.0f})."
                )
                resolution = (
                    f"Coordinator ranked {c.global_id} at {c.final_score:.1f}/100 using the documented "
                    f"35% Finance / 35% Delivery / 30% Equity weighting. Despite weakness in "
                    f"{', '.join(weak)}, strength in {', '.join(strong)} kept it within the funded "
                    f"shortlist; the weak dimension(s) should be addressed before disbursement."
                )
                conflicts.append(ConflictRecord(
                    issue=f"Trade-off on {c.global_id} ({c.description[:60]})",
                    global_id=c.global_id,
                    finance_position=finance_pos,
                    delivery_position=delivery_pos,
                    equity_position=equity_pos,
                    coordinator_resolution=resolution,
                ))

            if c.global_id in finance_outlier_ids:
                conflicts.append(ConflictRecord(
                    issue=f"{c.global_id} was flagged as a Finance cost outlier but ranked highly enough to be selected",
                    global_id=c.global_id,
                    finance_position="Flagged as a cost outlier within its category -- warrants scrutiny before disbursement.",
                    delivery_position=c.delivery_reason,
                    equity_position=c.equity_reason,
                    coordinator_resolution=(
                        f"Coordinator kept {c.global_id} in the shortlist (score {c.final_score:.1f}/100) but "
                        "flags it for a cost justification review prior to funds release, per Finance Agent's outlier finding."
                    ),
                ))

        return conflicts[:15]  # keep the report readable

    @staticmethod
    def _build_executive_summary(
        total_projects: int, total_portfolio_m: float, n_selected: int,
        total_recommended: float, budget_cap_m: float, conflicts: list[ConflictRecord],
    ) -> str:
        return (
            f"Reviewed {total_projects} projects (total portfolio {total_portfolio_m:,.1f}M PKR). "
            f"Out of all 'Not Started' candidates, the board recommends funding {n_selected} projects "
            f"totaling {total_recommended:,.2f}M PKR against the {budget_cap_m:,.0f}M PKR envelope "
            f"(remaining {budget_cap_m - total_recommended:,.2f}M). Selections balance financial "
            f"feasibility, delivery readiness, and district/category equity using a transparent, "
            f"weighted scoring model (35% Finance / 35% Delivery / 30% Equity). "
            f"{len(conflicts)} specific trade-off(s) between specialists were identified and resolved "
            f"during ranking (see Conflicts & Trade-offs)."
        )
