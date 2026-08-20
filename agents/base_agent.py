"""
BaseAgent: implements the generic PLAN -> ACT -> OBSERVE -> REASON -> ... -> STOP
loop shared by every specialist agent.

Two execution modes:
  1. LLM mode (Grok): the model is given a system prompt describing
     its role and available tools, and drives the loop itself by emitting
     JSON actions (call_tool / final_answer). Python executes each tool call.
  2. Demo mode: no LLM is called. Each agent instead runs its own fixed,
     documented investigation PLAN (still calling the exact same real
     tools against the real dataset, still building the loop's
     observe/reason/next-action structure) and synthesizes findings with
     rule-based text generation. This satisfies the assignment's explicit
     requirement to support a no-API-key demo mode without ever
     fabricating dataset numbers.

Every tool call -- in EITHER mode -- is logged to `self.tool_log` as a
ToolCallLog, which feeds the Transparency requirement (Section 19) and the
UI's "Agent Activity Panel".
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from models.messages import AgentReport, ToolCallLog
from agents.llm_provider import LLMProvider, extract_json_object

logger = logging.getLogger(__name__)

MAX_LOOP_STEPS = 6


class ToolSpec:
    """Describes one callable tool exposed to the LLM: name, docstring-style
    description, and a JSON-schema-ish argument description (kept simple
    on purpose so it's easy to explain and easy for smaller open models to
    follow)."""

    def __init__(self, name: str, func: Callable[..., Any], description: str, arg_schema: dict):
        self.name = name
        self.func = func
        self.description = description
        self.arg_schema = arg_schema

    def to_prompt_block(self) -> str:
        return f"- {self.name}({json.dumps(self.arg_schema)}): {self.description}"


class AgentActivityLogger:
    """Collects human-readable activity lines for the UI's Agent Activity Panel.
    Deliberately high-level (plans, tool calls, results, decisions) -- never
    raw model chain-of-thought (Section 17: 'Never expose private
    chain-of-thought')."""

    def __init__(self):
        self.lines: list[str] = []

    def log(self, agent_name: str, message: str):
        line = f"[{agent_name}] {message}"
        self.lines.append(line)
        logger.info(line)


class BaseAgent:
    agent_name: str = "BaseAgent"

    def __init__(self, provider: LLMProvider, is_demo: bool, activity: AgentActivityLogger):
        self.provider = provider
        self.is_demo = is_demo
        self.activity = activity
        self.tools: dict[str, ToolSpec] = {}
        self.tool_log: list[ToolCallLog] = []
        self._register_tools()

    # -- to be implemented by subclasses ------------------------------------
    def _register_tools(self) -> None:
        raise NotImplementedError

    def system_prompt(self) -> str:
        raise NotImplementedError

    def run_demo_plan(self, task: str) -> AgentReport:
        """Deterministic fallback investigation, used in Demo Mode."""
        raise NotImplementedError

    # -- shared machinery -----------------------------------------------------
    def _call_tool(self, name: str, arguments: dict) -> Any:
        if name not in self.tools:
            raise ValueError(f"Unknown tool '{name}'. Available: {list(self.tools)}")
        spec = self.tools[name]
        self.activity.log(self.agent_name, f"Calling {name}({arguments})")
        result = spec.func(**arguments)
        summary = self._summarize_result(result)
        self.activity.log(self.agent_name, f"{name} -> {summary}")
        self.tool_log.append(ToolCallLog(
            tool_name=name,
            arguments=arguments,
            timestamp=datetime.now(timezone.utc).isoformat(),
            result_summary=summary,
        ))
        return result

    @staticmethod
    def _summarize_result(result: Any) -> str:
        if isinstance(result, list):
            return f"{len(result)} item(s) returned"
        if hasattr(result, "count"):
            try:
                return f"count={result.count}"
            except Exception:  # noqa: BLE001
                pass
        return str(result)[:160]

    def _tools_prompt_block(self) -> str:
        return "\n".join(spec.to_prompt_block() for spec in self.tools.values())

    def run(self, task: str) -> AgentReport:
        self.activity.log(self.agent_name, f"Received task: {task}")
        if self.is_demo:
            return self.run_demo_plan(task)
        return self._run_llm_loop(task)

    def _run_llm_loop(self, task: str) -> AgentReport:
        """Genuine PLAN -> ACT -> OBSERVE -> REASON loop driven by the LLM."""
        system = self.system_prompt() + "\n\nAvailable tools:\n" + self._tools_prompt_block() + (
            "\n\nRespond with EXACTLY one JSON object per turn, no prose outside it:\n"
            '  {"action": "call_tool", "tool": "<tool_name>", "arguments": {...}}\n'
            "or, once you have enough evidence:\n"
            '  {"action": "final_answer", "report": {'
            '"summary": "...", '
            '"findings": [{"finding_id": "...", "title": "...", "severity": "low|medium|high", '
            '"explanation": "...", "affected_projects": ["..."], "recommendation": "..."}], '
            '"recommended_projects": ["..."], "rejected_projects": ["..."], '
            '"data_quality_notes": ["..."]'
            "}}\n"
            "Every numeric claim in your findings MUST come from a tool result you already observed. "
            "Never invent a Global ID, cost, or statistic."
        )
        messages: list[dict] = [{"role": "user", "content": f"Task: {task}"}]

        for step in range(MAX_LOOP_STEPS):
            self.activity.log(self.agent_name, f"Reasoning step {step + 1}/{MAX_LOOP_STEPS}...")
            response = self.provider.complete(system, messages)
            action = extract_json_object(response.text)

            if action is None:
                messages.append({"role": "assistant", "content": response.text})
                messages.append({"role": "user", "content": "Your last reply was not valid JSON. Reply with exactly one JSON object as instructed."})
                continue

            if action.get("action") == "call_tool":
                tool_name = action.get("tool", "")
                args = action.get("arguments", {}) or {}
                try:
                    result = self._call_tool(tool_name, args)
                    result_json = self._to_jsonable(result)
                except Exception as exc:  # noqa: BLE001
                    result_json = {"error": str(exc)}
                    self.activity.log(self.agent_name, f"Tool call failed: {exc}")
                messages.append({"role": "assistant", "content": json.dumps(action)})
                messages.append({"role": "user", "content": f"Tool result: {json.dumps(result_json)[:4000]}"})
                continue

            if action.get("action") == "final_answer":
                self.activity.log(self.agent_name, "Synthesizing final report.")
                return self._build_report_from_llm(action.get("report", {}))

            # Unknown action shape
            messages.append({"role": "assistant", "content": response.text})
            messages.append({"role": "user", "content": "Unrecognized action. Use 'call_tool' or 'final_answer'."})

        self.activity.log(self.agent_name, "Reached max reasoning steps; synthesizing with evidence gathered so far.")
        return AgentReport(
            agent_name=self.agent_name,
            summary="Reached maximum reasoning steps before a final synthesis was produced.",
            tool_calls=self.tool_log,
        )

    def _build_report_from_llm(self, report_dict: dict) -> AgentReport:
        from models.messages import AgentFinding
        findings = []
        for f in report_dict.get("findings", []):
            try:
                findings.append(AgentFinding(agent_name=self.agent_name, **{
                    "finding_id": f.get("finding_id", "f"),
                    "title": f.get("title", ""),
                    "severity": f.get("severity", "medium"),
                    "explanation": f.get("explanation", ""),
                    "affected_projects": f.get("affected_projects", []),
                    "recommendation": f.get("recommendation", ""),
                }))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping malformed finding: %s", exc)
        return AgentReport(
            agent_name=self.agent_name,
            summary=report_dict.get("summary", ""),
            findings=findings,
            recommended_projects=report_dict.get("recommended_projects", []),
            rejected_projects=report_dict.get("rejected_projects", []),
            data_quality_notes=report_dict.get("data_quality_notes", []),
            tool_calls=self.tool_log,
        )

    @staticmethod
    def _to_jsonable(obj: Any) -> Any:
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if isinstance(obj, list):
            return [BaseAgent._to_jsonable(o) for o in obj]
        return obj
