"""
Lightweight run-state / logging persistence.

We deliberately use a custom, explicit agent loop (see agents/base_agent.py
and agents/coordinator_agent.py) rather than a heavier framework like
LangGraph. For a system with exactly 4 agents and a fixed, well-understood
control flow (Coordinator -> 3 specialists -> Coordinator), a custom loop
is easier to read, easier to explain line-by-line in a viva, and has zero
extra dependencies -- while still genuinely implementing
plan -> act -> observe -> reason -> ... -> stop with a real stopping
condition (MAX_LOOP_STEPS in LLM mode; a fixed, documented plan in Demo
Mode). This file adds simple JSON persistence of each run for
auditability (Section 19: "Store tool calls in a structured log").
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from models.messages import FinalReport, AgentReport

RUN_LOGS_DIR = Path(__file__).resolve().parent.parent / "run_logs"


def save_run_log(final_report: FinalReport, activity_log: list[str], specialist_reports: dict[str, AgentReport]) -> Path:
    RUN_LOGS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = RUN_LOGS_DIR / f"run_{timestamp}.json"

    payload = {
        "timestamp": timestamp,
        "activity_log": activity_log,
        "final_report": final_report.model_dump(),
        "specialist_reports": {name: report.model_dump() for name, report in specialist_reports.items()},
    }
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return out_path
