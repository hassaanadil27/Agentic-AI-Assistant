"""
Generates transcripts/run_0{1,2,3}.md from REAL executions of the system
against the actual dataset (never fabricated). Run this any time after
configuring an API key to regenerate transcripts using live LLM reasoning;
by default (no key) it runs in Demo Mode, which still executes 100% real
tool calls and data analysis.

Usage:
    python generate_transcripts.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
load_dotenv()

from agents.llm_provider import get_provider
from agents.coordinator_agent import CoordinatorAgent
from tools.data_loader import load_projects

OUT_DIR = Path(__file__).resolve().parent / "transcripts"
OUT_DIR.mkdir(exist_ok=True)


def render_transcript(run_number: int, budget_cap_m: float, mode_label: str) -> str:
    provider, is_demo = get_provider()
    meta = load_projects(force_reload=True)
    coordinator = CoordinatorAgent(provider, is_demo)
    final_report, activity_log, specialist_reports = coordinator.run_review(budget_cap_m=budget_cap_m)

    lines = []
    lines.append(f"# Run {run_number:02d} — {mode_label}")
    lines.append("")
    lines.append(f"**Mode:** {'Demo Mode (deterministic, rule-based reasoning over real tool results)' if is_demo else f'Live LLM mode (Grok model: {provider.model_name})'}")
    lines.append(f"**Funding envelope:** PKR {budget_cap_m:,.0f}M")
    lines.append(f"**Dataset:** {meta.total_projects} projects, PKR {meta.total_portfolio_m:,.1f}M total portfolio, {meta.districts} districts")
    lines.append("")
    lines.append("## Agent Plan & Tool Calls (Agent Activity Panel)")
    lines.append("")
    lines.append("```text")
    lines.extend(activity_log)
    lines.append("```")
    lines.append("")
    lines.append("## Final Output")
    lines.append("")
    lines.append("### Executive Summary")
    lines.append(final_report.executive_summary)
    lines.append("")
    lines.append("### Budget Summary")
    lines.append(f"- Budget Available: PKR {final_report.budget_available_m:,.1f}M")
    lines.append(f"- Recommended: PKR {final_report.total_recommended_m:,.2f}M")
    lines.append(f"- Remaining: PKR {final_report.remaining_budget_m:,.2f}M")
    lines.append(f"- Projects Selected: {len(final_report.recommended_projects)}")
    lines.append("")
    lines.append("### Top 10 Recommended Projects")
    lines.append("")
    lines.append("| Rank | Global ID | Project | District | Category | Cost (M) | Score |")
    lines.append("|---|---|---|---|---|---:|---:|")
    for i, r in enumerate(final_report.recommended_projects[:10], start=1):
        desc = r.description[:45].replace("|", "-")
        lines.append(f"| {i} | {r.global_id} | {desc} | {r.district} | {r.category} | {r.cost_m:.1f} | {r.score:.1f} |")
    lines.append("")
    lines.append(f"*(+ {max(0, len(final_report.recommended_projects) - 10)} more projects in the full run — see CSV export in the app)*")
    lines.append("")
    lines.append("### Sample Finance Finding")
    if final_report.finance_findings:
        f = final_report.finance_findings[0]
        lines.append(f"**[{f.severity.upper()}] {f.title}**  \n{f.explanation}")
    lines.append("")
    lines.append("### Sample Delivery Finding")
    if final_report.delivery_findings:
        f = final_report.delivery_findings[0]
        lines.append(f"**[{f.severity.upper()}] {f.title}**  \n{f.explanation}")
    lines.append("")
    lines.append("### Sample Equity Finding")
    if final_report.equity_findings:
        f = final_report.equity_findings[0]
        lines.append(f"**[{f.severity.upper()}] {f.title}**  \n{f.explanation}")
    lines.append("")
    lines.append("### Conflicts & Trade-offs (sample)")
    for c in final_report.conflicts[:3]:
        lines.append(f"- **Issue:** {c.issue}")
        lines.append(f"  - Finance: {c.finance_position}")
        lines.append(f"  - Delivery: {c.delivery_position}")
        lines.append(f"  - Equity: {c.equity_position}")
        lines.append(f"  - **Resolution:** {c.coordinator_resolution}")
    lines.append("")
    lines.append("### Data Quality Warnings")
    for w in final_report.data_quality_warnings[:8]:
        lines.append(f"- {w}")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    runs = [
        (1, 2000.0, "Standard PKR 2B Funding Round"),
        (2, 1000.0, "Reduced PKR 1B Funding Round (stress-tests budget constraint)"),
        (3, 3000.0, "Expanded PKR 3B Funding Round"),
    ]
    for run_number, cap, label in runs:
        content = render_transcript(run_number, cap, label)
        out_path = OUT_DIR / f"run_{run_number:02d}.md"
        out_path.write_text(content, encoding="utf-8")
        print(f"Wrote {out_path}")
