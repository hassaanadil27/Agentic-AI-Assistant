"""Track B autonomous Audit Agent."""
from __future__ import annotations

import json
from dataclasses import dataclass

from agents.llm_provider import LLMProvider, extract_json_object
from tools.audit_tools import AUDIT_CHECKS
from tools.data_loader import load_projects


@dataclass
class AuditResult:
    plan: list[str]
    findings: list[dict]
    report: str
    trace: list[str]


class AuditAgent:
    def __init__(self, provider: LLMProvider): self.provider = provider

    def run(self, goal: str) -> AuditResult:
        meta = load_projects()
        names = list(AUDIT_CHECKS)
        try:
            planning = self.provider.complete(
                "You are the Track B autonomous Audit Agent. Given a goal and dataset summary, choose at least four "
                "distinct checks. Return JSON only: {\"checks\":[names],\"rationale\":\"...\"}. Available checks: " + ", ".join(names),
                [{"role": "user", "content": f"Goal: {goal}\nDataset: {meta.model_dump_json()}"}],
            )
            parsed = extract_json_object(planning.text) or {}
        except Exception:
            parsed = {}
        plan = [name for name in parsed.get("checks", []) if name in AUDIT_CHECKS]
        if len(plan) < 4: plan = names
        trace = ["PLAN: " + ", ".join(plan)]
        findings = []
        for name in plan:
            trace.append(f"ACT: {name}()")
            finding = AUDIT_CHECKS[name]()
            findings.append(finding)
            trace.append(f"OBSERVE: {name} found {finding['count']} issue(s)")
        try:
            synthesis = self.provider.complete(
                "You are a government portfolio audit specialist. Produce a prioritized, actionable report grounded "
                "only in the supplied check results. Include counts, example Global IDs, severity and recommended action. "
                "All costs are PKR millions; never use a dollar sign. Do not invent values.",
                [{"role": "user", "content": json.dumps(findings, default=str)}],
            )
            report = synthesis.text
        except Exception:
            ranked = sorted(findings, key=lambda item: item["count"], reverse=True)
            report = "## Prioritized portfolio audit\n\n" + "\n\n".join(
                f"### {index}. {item['check'].replace('_', ' ').title()}\n"
                f"**Issues found:** {item['count']}\n\n"
                f"Examples: {', '.join(str(row.get('global_id') or row.get('subject')) for row in item['examples'][:5]) or 'None'}.\n\n"
                "**Action:** Validate the flagged records and assign an accountable owner before funding or continuation."
                for index, item in enumerate(ranked, 1)
            )
        trace.extend(["REASON: compared issue counts, financial exposure and accountability risk", "STOP: prioritized audit report produced"])
        return AuditResult(plan, findings, report, trace)
