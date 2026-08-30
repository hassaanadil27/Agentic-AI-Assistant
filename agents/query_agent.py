"""Project-aware analytical query agent with validated plans and evidence."""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from agents.llm_provider import DemoProvider, LLMProvider, extract_json_object
from agents.answer_formatter import format_professional_answer, validate_professional_answer
from models.analysis import AnalysisFilter, AnalysisPlan, AnalysisResult
from orchestration.query_log import log_query
from tools.analysis_tools import ALIASES, NUMERIC_COLUMNS, PUBLIC_COLUMNS, dataset_schema, execute_analysis, rank_attention_projects
from tools.data_loader import get_dataframe
from tools.ranking_tools import rank_funding_candidates

logger = logging.getLogger(__name__)


@dataclass
class QueryAnswer:
    answer: str
    trace: list[str] = field(default_factory=list)
    evidence: dict[str, Any] | None = None
    table: list[dict[str, Any]] = field(default_factory=list)
    chart: dict[str, Any] | None = None
    intent: str = "unknown"
    plan: dict[str, Any] | None = None
    validation: str = "not_run"

    def model_dump(self) -> dict[str, Any]:
        return self.__dict__.copy()


class QueryAgent:
    """Translate language into a validated plan, execute it, then explain evidence."""

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def ask(self, question: str, history: list[dict] | None = None) -> QueryAnswer:
        question = " ".join(str(question).split()).strip()
        trace = [f"PLAN: understand the analytical request — {question}"]
        if not question:
            return QueryAnswer("Please enter a project-related question.", trace, validation="failed")
        if self._is_greeting(question):
            return QueryAnswer("Hi! I’m the BSDI Project AI Agent. I can analyze counts, budgets, progress, districts, sectors, delivery, quality, rankings, correlations, and records—with evidence.", [*trace, "STOP: capabilities explained"], intent="project_info", validation="passed")
        contextual = self._with_followup_context(question, history or [])
        if re.search(r"\bpending\b", contextual, re.I):
            statuses = sorted(str(v) for v in get_dataframe()["status"].dropna().unique())
            if not any(v.casefold() == "pending" for v in statuses):
                answer = "## Clarification Needed\n\n- The dataset does not contain an explicit **Pending** status.\n- **Available statuses:** " + ", ".join(f"**{v}**" for v in statuses) + "\n\nPlease specify whether **pending** should mean **Not Started**, **In Progress**, or another combination.\n\n## Evidence\n\n- **Dataset:** `Projects.xlsx`\n- **Field Checked:** `status`\n- **Records Analyzed:** {:,}".format(len(get_dataframe()))
                evidence = {"dataset":"Projects.xlsx","rows_available":len(get_dataframe()),"rows_analyzed":len(get_dataframe()),"columns":["status"],"filters":[],"operation":"inspect_status_values","missing_values_excluded":0}
                return QueryAnswer(answer, [*trace,"STOP: ambiguous status requires clarification"], evidence, intent="clarify", validation="needs_clarification")
        if self._asks_attention(contextual):
            return self._attention_answer(contextual, trace)
        if self._asks_priority(contextual):
            return self._priority_answer(contextual, trace)
        if self._asks_project_architecture(contextual):
            return self._project_information(contextual, trace)
        if self._asks_unavailable_health_data(contextual):
            return QueryAnswer("I can't answer that reliably from the available project data. `Projects.xlsx` has current status, progress, cost, tender, contractor, XEN, and work-start information, but it has no deadline/overdue field, blocker log, explicit risk severity, health score, or historical snapshots for improvement trends.", [*trace, "STOP: required project-health fields are unavailable"], {"dataset": "Projects.xlsx", "available_columns": sorted(PUBLIC_COLUMNS)}, intent="insufficient_data", validation="passed")
        local_plan = self._deterministic_plan(contextual)
        if local_plan.intent != "clarify":
            plan = local_plan
            trace.append("REASON: the schema-grounded planner resolved the request without spending an LLM call")
        else:
            plan = None if isinstance(self.provider, DemoProvider) else self._llm_plan(contextual, history or [], trace)
        if plan is not None and not self._plans_semantically_compatible(plan, local_plan):
            trace.append("OBSERVE: rejected an online plan whose metric or fields did not match the question")
            plan = None
        elif plan is not None and local_plan.intent != "clarify":
            # Deterministic ordering/limits make equivalent live plans stable
            # and ensure the first stated result is actually top/bottom as asked.
            plan.sort = local_plan.sort
            plan.limit = local_plan.limit
            if local_plan.chart != "none": plan.chart = local_plan.chart
        if plan is None:
            plan = local_plan
            trace.append("REASON: used the validated local planner")
        if plan.intent == "clarify":
            return QueryAnswer(plan.clarification or "Please clarify the project field or metric.", [*trace, "STOP: clarification required"], intent="clarify", plan=plan.model_dump(), validation="needs_clarification")

        trace.append(f"ACT: execute_analysis({json.dumps(plan.model_dump(), default=str)})")
        result = execute_analysis(plan)
        trace.append(f"OBSERVE: success={result.success}; rows={result.evidence.rows_analyzed if result.evidence else 0}; validation={result.validation}")
        if result.success:
            result.answer = format_professional_answer(result)
            valid, issues = validate_professional_answer(result.answer, result)
            if not valid:
                result.success = False
                result.validation = "failed"
                result.answer = "I could not produce an evidence-complete answer safely. Validation issues: " + "; ".join(issues)
            trace.extend(["REASON: result matches requested metric, fields and filters", "STOP: evidence-grounded answer produced"])
            self._log_request(question, result)
        else:
            trace.append("STOP: no unsupported or unvalidated value returned")
        return self._from_result(result, trace)

    def _llm_plan(self, question: str, history: list[dict], trace: list[str]) -> AnalysisPlan | None:
        schema = dataset_schema()
        columns = [{"name": c["name"], "type": c["type"], "examples": c["examples"]} for c in schema["columns"]]
        system = (
            "You are a project-aware analytical query planner. Return ONE JSON plan, never an answer. "
            "Use only PROJECT_SCHEMA fields; never invent fields, metrics, filters or values. "
            "intent: overview|schema|aggregate|group|records|distribution|correlation|lookup|clarify. "
            "operation: count|distinct_count|sum|mean|median|mode|min|max|std|percentage|list|correlation. "
            "filters: [{column,operator,value}], operator eq|ne|gt|gte|lt|lte|contains|in. "
            "Use category=sector, cost_m=cost/budget/allocation, progress_pct=progress, global_id=projects. "
            "For ranking/comparison set group_by, sort and limit. Ascending=lowest/fewest; descending=highest/most. "
            "Chart bar for groups, histogram for distributions, scatter for correlation, otherwise none. "
            "If ambiguous use intent=clarify and clarification. JSON keys: intent,operation,target_column,secondary_column,group_by,filters,sort,limit,chart,clarification.\n"
            f"PROJECT_SCHEMA={json.dumps(columns, ensure_ascii=False)}"
        )
        messages = [*[m for m in history[-6:] if m.get("role") in {"user", "assistant"}], {"role": "user", "content": question}]
        try:
            payload = extract_json_object(self.provider.complete(system, messages).text)
            if not isinstance(payload, dict):
                raise ValueError("planner returned no JSON object")
            payload = {key: value for key, value in payload.items() if value is not None}
            if isinstance(payload.get("group_by"), str):
                payload["group_by"] = [payload["group_by"]]
            if isinstance(payload.get("sort"), list):
                sort_item = payload["sort"][0] if payload["sort"] else {}
                direction = str(sort_item.get("direction", "none")).casefold() if isinstance(sort_item, dict) else str(sort_item).casefold()
                payload["sort"] = "ascending" if direction in {"asc", "ascending"} else "descending" if direction in {"desc", "descending"} else "none"
            aliases = {"avg": "mean", "average": "mean", "total": "sum"}
            if payload.get("operation") in aliases:
                payload["operation"] = aliases[payload["operation"]]
            plan = AnalysisPlan.model_validate(payload)
            trace.append("REASON: Gemini produced a structured analysis plan")
            return plan
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM planning failed; using validated local planner: %s", exc)
            trace.append("OBSERVE: online planner unavailable; no answer value was accepted")
            return None

    def _deterministic_plan(self, question: str) -> AnalysisPlan:
        q = question.casefold()
        if any(p in q for p in ("what data", "dataset schema", "columns", "fields", "data types", "missing values")):
            return AnalysisPlan(intent="schema", operation="list", limit=100)
        if any(p in q for p in ("portfolio overview", "dataset overview", "summary of the portfolio")):
            return AnalysisPlan(intent="overview")
        match = re.search(r"\b[A-Z]{2,6}-\d{4}-P\d+\b", question, re.I)
        filters = self._infer_filters(q)
        if match:
            filters.append(AnalysisFilter(column="global_id", value=match.group(0).upper()))
            return AnalysisPlan(intent="lookup", operation="list", filters=filters)

        target, group = self._infer_target(q), self._infer_group(q)
        limit_match = re.search(r"\b(?:top|bottom|first|last)\s+(\d+)\b", q)
        limit = min(int(limit_match.group(1)), 100) if limit_match else 50
        sort = "descending" if any(t in q for t in ("highest", "largest", "most", "top", "best")) else "ascending" if any(t in q for t in ("lowest", "lowes", "smallest", "least", "fewest", "bottom", "worst")) else "none"
        operation = self._infer_operation(q, target)
        if any(t in q for t in ("correlation", "correlated", "relationship", "related to", "association")):
            numerics = [c for c in NUMERIC_COLUMNS if c.split("_")[0] in q]
            return AnalysisPlan(intent="correlation", operation="correlation", target_column=numerics[0], secondary_column=numerics[1], filters=filters, chart="scatter") if len(numerics) >= 2 else AnalysisPlan(intent="clarify", clarification="Which two numeric fields should I compare? Available options are project cost and progress percentage.")
        if any(t in q for t in ("distribution", "spread", "histogram")):
            return AnalysisPlan(intent="distribution", operation="list", target_column=target, filters=filters, chart="histogram", limit=100) if target in NUMERIC_COLUMNS else AnalysisPlan(intent="clarify", clarification="Which distribution do you want: project cost or progress percentage?")
        list_request = bool(re.search(r"\b(?:show|list|give me|what are)\s+(?:the\s+)?(?:top\s+\d+\s+|bottom\s+\d+\s+)?(?:projects|schemes)\b", q))
        ranking_request = bool(re.search(r"\b(?:top|bottom)\s+\d+\b", q))
        if (re.search(r"\bwhich\s+(?:one\s+|project\s+|scheme\s+)", q) or ranking_request) and not group and target in NUMERIC_COLUMNS and sort != "none":
            return AnalysisPlan(intent="records", operation="list", target_column=target, filters=filters, sort=sort, limit=limit, chart="bar")
        if list_request:
            return AnalysisPlan(intent="aggregate", operation="list", target_column="global_id", filters=filters, sort=sort, limit=min(limit, 20), chart="none")
        if group:
            if sort == "none": sort = "descending"
            return AnalysisPlan(intent="group", operation=operation, target_column=target, group_by=[group], filters=filters, sort=sort, limit=limit, chart="bar")
        if operation in {"distinct_count", "list"} and target:
            return AnalysisPlan(intent="aggregate", operation=operation, target_column=target, filters=filters, limit=100)
        if operation not in {"count", "percentage"} and target not in NUMERIC_COLUMNS:
            return AnalysisPlan(intent="clarify", clarification="I couldn't find that requested field in the project data. Available numeric fields are project cost and progress percentage.")
        if self._looks_analytical(q):
            return AnalysisPlan(intent="aggregate", operation=operation, target_column=target, filters=filters)
        return AnalysisPlan(intent="clarify", clarification="I couldn't identify the requested project metric. Mention cost, progress, district, sector, status, agency, contractor, or a project ID.")

    @staticmethod
    def _infer_operation(q: str, target: str | None) -> str:
        if any(t in q for t in ("how many", "number of", "count")):
            return "distinct_count" if target and target != "global_id" and any(t in q for t in ("district", "sector", "category", "status", "phase", "agency")) else "count"
        if any(t in q for t in ("average", "mean", "on average")): return "mean"
        if "median" in q or "typical" in q: return "median"
        if "mode" in q or "most common" in q: return "mode"
        if any(t in q for t in ("standard deviation", "std", "variability")): return "std"
        if any(t in q for t in ("percentage", "percent", "share", "proportion", "rate")): return "percentage"
        if any(t in q for t in ("minimum", "min ", "lowest value")): return "min"
        if any(t in q for t in ("maximum", "max ", "highest value")): return "max"
        if any(t in q for t in ("total", "sum", "allocation", "budget")) and target == "cost_m": return "sum"
        if "compare" in q and target in NUMERIC_COLUMNS: return "mean"
        if any(t in q for t in ("list all", "show all", "what are all", "tell me all")): return "list"
        return "count"

    @staticmethod
    def _infer_target(q: str) -> str | None:
        # Metric words take priority over the generic word "project".
        if any(t in q for t in ("budget", "cost", "value", "allocation", "funding", "expensive", "cheapest")): return "cost_m"
        if any(t in q for t in ("progress", "completion percentage")): return "progress_pct"
        for phrase, column in sorted(ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
            if re.search(rf"\b{re.escape(phrase)}\b", q): return column
        for column in PUBLIC_COLUMNS:
            if column in q or column.replace("_", " ") in q: return column
        return "global_id" if any(t in q for t in ("project", "scheme", "record")) else None

    @staticmethod
    def _infer_group(q: str) -> str | None:
        mappings = {"category": ("sector", "category"), "district": ("district",), "status": ("status",), "phase": ("phase",), "executing_agency": ("agency",), "contractor_normalized": ("contractor",)}
        for column, terms in mappings.items():
            if any(re.search(rf"\b(?:by|per|each|which|across)\s+(?:\w+\s+)?{term}s?\b", q) for term in terms): return column
        if any(t in q for t in ("highest", "lowest", "most", "least", "fewest", "top", "bottom", "compare")):
            explicit = next((column for column, terms in mappings.items() if any(re.search(rf"\b{term}s?\b", q) for term in terms)), None)
            if explicit: return explicit
            df = get_dataframe()
            for column in ("status", "category", "district", "phase"):
                mentioned = [str(v) for v in df[column].dropna().unique() if re.search(rf"\b{re.escape(str(v).casefold())}\b", q)]
                if len(mentioned) >= 2: return column
        return None

    @staticmethod
    def _infer_filters(q: str) -> list[AnalysisFilter]:
        df, filters = get_dataframe(), []
        scan_columns = ["status", "category", "district", "phase", "executing_agency"]
        if "tender" in q or "nits" in q or "nit " in q: scan_columns.append("nits")
        for column in scan_columns:
            values = sorted((str(v) for v in df[column].dropna().unique()), key=len, reverse=True)
            matches = [v for v in values if re.search(rf"\b{re.escape(v.casefold())}\b", q)]
            if len(matches) > 1: filters.append(AnalysisFilter(column=column, operator="in", value=matches))
            elif matches: filters.append(AnalysisFilter(column=column, value=matches[0]))
        boolean_terms = {"has_contractor": (("missing contractor", "without contractor", "no contractor"), ("with contractor", "has contractor")), "has_xen": (("missing xen", "without xen", "no xen"), ("with xen", "has xen")), "has_work_started": (("missing start", "without start date", "no start date"), ("work started", "with start date"))}
        for column, (negative, positive) in boolean_terms.items():
            if any(t in q for t in negative): filters.append(AnalysisFilter(column=column, value=False))
            elif any(t in q for t in positive): filters.append(AnalysisFilter(column=column, value=True))
        patterns = [(r"(?:cost|budget|value)\s*(?:is\s*)?(?:over|above|more than|>)\s*(?:pkr\s*)?([\d,.]+)", "cost_m", "gt"), (r"(?:cost|budget|value)\s*(?:is\s*)?(?:under|below|less than|<)\s*(?:pkr\s*)?([\d,.]+)", "cost_m", "lt"), (r"progress\s*(?:is\s*)?(?:over|above|more than|>)\s*([\d,.]+)", "progress_pct", "gt"), (r"progress\s*(?:is\s*)?(?:under|below|less than|<)\s*([\d,.]+)", "progress_pct", "lt"), (r"(?:below|under|less than|<)\s*([\d,.]+)\s*%?\s*progress", "progress_pct", "lt"), (r"(?:above|over|more than|>)\s*([\d,.]+)\s*%?\s*progress", "progress_pct", "gt")]
        for pattern, column, operator in patterns:
            match = re.search(pattern, q)
            if match: filters.append(AnalysisFilter(column=column, operator=operator, value=float(match.group(1).replace(",", ""))))
        return filters

    @staticmethod
    def _with_followup_context(question: str, history: list[dict]) -> str:
        q = question.casefold()
        if len(question.split()) > 8 and not any(t in q for t in ("that", "it", "them", "those", "same", "now", "instead")): return question
        previous = next((str(m.get("content", "")) for m in reversed(history) if m.get("role") == "user" and m.get("content")), "")
        return f"Previous user question: {previous}\nFollow-up: {question}" if previous else question

    @staticmethod
    def _plans_semantically_compatible(candidate: AnalysisPlan, local: AnalysisPlan) -> bool:
        """Reject a valid-looking plan that answers a different measurable question."""
        if local.intent == "clarify":
            selected = [candidate.target_column, candidate.secondary_column, *candidate.group_by, *(item.column for item in candidate.filters)]
            return candidate.intent != "clarify" and all(not item or item in PUBLIC_COLUMNS or item in ALIASES for item in selected)
        if candidate.intent == "clarify": return False
        if local.operation != candidate.operation: return False
        if local.target_column and candidate.target_column != local.target_column: return False
        if local.group_by and candidate.group_by != local.group_by: return False
        local_filters = {(item.column, item.operator, json.dumps(item.value, sort_keys=True, default=str)) for item in local.filters}
        candidate_filters = {(item.column, item.operator, json.dumps(item.value, sort_keys=True, default=str)) for item in candidate.filters}
        return local_filters == candidate_filters

    @staticmethod
    def _format_answer(result: AnalysisResult) -> str:
        evidence = result.evidence
        if not evidence: return result.answer
        lines = ["## Answer", "", result.answer]
        if len(result.table) > 1:
            lines += ["", "## Key findings", ""] + [f"{i}. " + " — ".join(f"{k.replace('_', ' ').title()}: {v}" for k, v in row.items()) for i, row in enumerate(result.table[:5], 1)]
        lines += ["", "## Evidence", "", f"- Dataset: `{evidence.dataset}`", f"- Records analyzed: **{evidence.rows_analyzed:,}** of {evidence.rows_available:,}", f"- Columns: {', '.join(f'`{c}`' for c in evidence.columns)}", f"- Calculation: `{evidence.operation}`"]
        lines.append("- Filters: " + ("; ".join(f"{f['column']} {f['operator']} {f['value']}" for f in evidence.filters) if evidence.filters else "none (entire portfolio)"))
        if evidence.missing_values_excluded: lines.append(f"- Missing numeric values excluded: {evidence.missing_values_excluded:,}")
        return "\n".join(lines)

    @staticmethod
    def _from_result(result: AnalysisResult, trace: list[str]) -> QueryAnswer:
        return QueryAnswer(result.answer, trace, result.evidence.model_dump() if result.evidence else None, result.table, result.chart, result.intent, result.plan.model_dump() if result.plan else None, result.validation)

    @staticmethod
    def _looks_analytical(q: str) -> bool:
        return any(t in q for t in ("project", "scheme", "record", "cost", "budget", "progress", "district", "sector", "category", "status", "phase", "agency", "contractor", "xen", "tender", "allocation"))

    @staticmethod
    def _is_greeting(q: str) -> bool:
        text = q.casefold()
        return bool(re.fullmatch(r"(?:hi|hello|hey|salam|assalam)[!. ]*", text)) or any(p in text for p in ("your name", "who are you", "what can you do"))

    @staticmethod
    def _asks_priority(q: str) -> bool:
        text = q.casefold()
        return bool(re.search(r"\b(project|scheme)s?\b", text) and any(t in text for t in ("start first", "started first", "begin first", "prioritize first", "prioritise first", "highest priority", "top priority", "should we start", "should be started")))

    @staticmethod
    def _asks_attention(q: str) -> bool:
        text = q.casefold().replace("-", " ")
        entity = re.search(r"\b(project|scheme)s?\b", text)
        return bool(entity and any(phrase in text for phrase in ("immediate attention", "needs attention", "need attention", "at risk", "highest risk", "focus on first", "performing worst", "main problems")))

    @staticmethod
    def _asks_unavailable_health_data(q: str) -> bool:
        text = q.casefold()
        return any(phrase in text for phrase in ("overdue", "deadline", "open blocker", "unresolved issue", "improved the most", "healthier", "health score", "critical risk"))

    @staticmethod
    def _attention_answer(question: str, trace: list[str]) -> QueryAnswer:
        text = question.casefold()
        number_match = re.search(r"\b(\d+)\b", text)
        if number_match: limit = min(int(number_match.group(1)), 20)
        elif any(phrase in text for phrase in ("compare", "second", "next project", "next one")): limit = 2
        elif re.search(r"\bprojects\b", text): limit = 5
        else: limit = 1
        id_match = re.search(r"\b[A-Z]{2,6}-\d{4}-P\d+\b", question, re.I)
        global_id = id_match.group(0).upper() if id_match else None
        result = rank_attention_projects(limit, global_id=global_id)
        trace.append(f"ACT: rank_attention_projects({{\"limit\": {limit}, \"global_id\": {json.dumps(global_id)}}})")
        if not result["success"]:
            message = f"I found project **{global_id}**, but it has no supported delivery or accountability warning under the available fields." if global_id else "I couldn't identify a project requiring immediate attention because no supported delivery or accountability warning was found in the available data."
            return QueryAnswer(message, [*trace, "STOP: no attention flags found"], intent="attention_analysis", validation="passed")
        rows = result["results"]
        table = [{"Rank": index, "Project ID": row["global_id"], "Project": row["description"], "Status": row["status"], "Progress": row["progress_pct"], "Cost (PKR M)": row["cost_m"], "Missing Contractor": not row["has_contractor"], "Missing XEN": not row["has_xen"], "Start Date": row["work_started"] or "Not recorded", "Attention flags": row["attention_flags"], "Observed reasons": "; ".join(row["reasons"])} for index, row in enumerate(rows, 1)]
        first = table[0]
        lines = ["## Project Requiring Immediate Attention", "", f"**{first['Project ID']} — {first['Project']}** requires the most immediate review under the available project indicators.", "", "### Why", ""]
        lines.extend(f"{index}. {reason}" for index, reason in enumerate(rows[0]["reasons"], 1))
        lines.extend(["", f"- Current status: **{first['Status']}**", f"- Recorded progress: **{first['Progress']:.0f}%**", f"- Recorded cost: **PKR {first['Cost (PKR M)']:,.2f} million**", f"- Missing contractor: **{'Yes' if first['Missing Contractor'] else 'No'}**", f"- Missing XEN: **{'Yes' if first['Missing XEN'] else 'No'}**", f"- Start date: **{first['Start Date']}**"])
        if len(table) > 1:
            lines.extend(["", "### Other Projects Requiring Attention", ""] + [f"{row['Rank']}. **{row['Project ID']}** — {row['Attention flags']} observed flag(s); {row['Progress']:.0f}% progress." for row in table])
        lines.extend(["", "### Evidence and Method", "", f"- Dataset: `Projects.xlsx`", f"- Projects analyzed: **{result['rows_analyzed']:,}**", f"- Projects with at least one supported flag: **{result['candidate_count']:,}**", "- Fields: `status`, `progress_pct`, `has_work_started`, `has_contractor`, `has_xen`, `nits`, `cost_m`", f"- Ranking method: {result['method']}", "", "### Interpretation", "", "The dataset has no explicit risk, deadline, blocker, or severity score. This ranking therefore uses only observable delivery/accountability warnings and reports the method transparently; it does not invent a risk score."])
        evidence = {"dataset": "Projects.xlsx", "rows_available": result["rows_analyzed"], "rows_analyzed": result["rows_analyzed"], "columns": result["columns"], "filters": [{"column": "attention_flags", "operator": "gt", "value": 0}], "operation": "transparent_attention_ranking", "missing_values_excluded": 0}
        chart = {"type": "bar", "title": "Projects Requiring Attention — Observed Warning Count", "x": "Project ID", "y": "Attention flags", "data": table}
        return QueryAnswer("\n".join(lines), [*trace, "REASON: ranked only observed delivery and accountability flags", "STOP: evidence-grounded attention analysis produced"], evidence, table, chart, intent="attention_analysis", plan={"intent": "project_attention_analysis", "operation": "rank", "fields": result["columns"], "method": result["method"]}, validation="passed")

    @staticmethod
    def _priority_answer(question: str, trace: list[str]) -> QueryAnswer:
        ranked = rank_funding_candidates(budget_cap_m=2000.0)
        trace.append("ACT: rank_funding_candidates({\"budget_cap_m\": 2000.0})")
        if not ranked: return QueryAnswer("No eligible Not Started projects were found.", trace, validation="failed")
        number_match = re.search(r"\b(\d+)\b", question)
        limit = min(int(number_match.group(1)), 20) if number_match else 1
        selected = ranked[:limit]
        table = [{"Rank": index, "Project ID": item.global_id, "Project": item.description, "District": item.district, "Sector": item.category, "Cost (PKR M)": round(item.cost_m, 2), "Priority score": round(item.final_score, 2)} for index, item in enumerate(selected, 1)]
        lines = ["## Answer", "", f"These are the **{len(selected)} highest-ranked eligible Not Started projects** to start first:", ""]
        lines.extend(f"{row['Rank']}. **{row['Project ID']}** — {row['Project']} ({row['District']}, {row['Sector']}); PKR {row['Cost (PKR M)']:,.2f}M; score {row['Priority score']:.2f}/100." for row in table)
        lines.extend(["", "## Evidence", "", f"- Candidates ranked: **{len(ranked):,} eligible Not Started projects**", "- Ranking dimensions: Finance 35%, Delivery 35%, Equity 30%", "- Source: `Projects.xlsx`", "- Calculation: `rank_funding_candidates` with a PKR 2,000M comparison envelope"])
        chart = {"type": "bar", "title": f"Top {len(selected)} Project Priority Scores", "x": "Project ID", "y": "Priority score", "data": table}
        evidence = {"dataset": "Projects.xlsx", "rows_available": len(get_dataframe()), "rows_analyzed": len(ranked), "columns": ["global_id", "status", "cost_m", "district", "category"], "filters": [{"column": "status", "operator": "eq", "value": "Not Started"}], "operation": "rank_funding_candidates", "missing_values_excluded": 0}
        return QueryAnswer("\n".join(lines), [*trace, "STOP: verified top-N priority ranking produced"], evidence, table, chart, intent="ranking", validation="passed")

    @staticmethod
    def _asks_project_architecture(q: str) -> bool:
        return any(t in q.casefold() for t in ("how does the system", "architecture", "backend", "frontend", "which model", "what model", "how is data loaded", "preprocessing", "tools available", "prediction", "accuracy", "precision", "recall", "f1", "roc"))

    @staticmethod
    def _project_information(question: str, trace: list[str]) -> QueryAnswer:
        q = question.casefold()
        if any(term in q for term in ("accuracy", "precision", "recall", "f1", "roc", "prediction")): answer, sources = "This repository does **not** contain a trained predictive model or prediction metrics such as accuracy, precision, recall, F1, or ROC-AUC. It is an analytical and ranking system, so I will not invent model-performance values.", ["agents/query_agent.py", "tools/ranking_tools.py", "models/"]
        elif "model" in q: answer, sources = "The live assistant uses **Google Gemini** through `agents/llm_provider.py`. Numeric results are calculated in Python, not by Gemini.", ["agents/llm_provider.py", ".env configuration"]
        elif "frontend" in q: answer, sources = "The frontend is a multipage **Streamlit** application; the chat page and shared UI live under `pages/` and `ui/`.", ["pages/2_AI_Assistant.py", "ui/components.py", "ui/charts.py"]
        elif any(t in q for t in ("backend", "architecture", "system")): answer, sources = "The project uses Streamlit, an embedded/FastAPI service adapter, agent planning, validated pandas tools, and `Projects.xlsx` as the factual source.", ["api.py", "ui/api_client.py", "agents/query_agent.py", "tools/analysis_tools.py"]
        else: answer, sources = "`Projects.xlsx` is cleaned, cached, and queried through validated analysis tools.", ["data/Projects.xlsx", "data_processing/cleaner.py", "tools/data_loader.py"]
        text = "## Answer\n\n" + answer + "\n\n## Evidence\n\n" + "\n".join(f"- `{s}`" for s in sources)
        return QueryAnswer(text, [*trace, "STOP: project files used as evidence"], {"files": sources}, intent="project_info", validation="passed")

    @staticmethod
    def _log_request(question: str, result: AnalysisResult) -> None:
        payload = {"question": question, "intent": result.intent, "plan": result.plan.model_dump() if result.plan else None, "validation": result.validation, "evidence": result.evidence.model_dump() if result.evidence else None, "result_preview": result.table[:5], "graph": result.chart and {key: result.chart.get(key) for key in ("type", "title", "x", "y")}}
        logger.info("QUERY %s", payload)
        try:
            log_query(payload)
        except OSError:
            logger.warning("Could not write the internal query audit log.")

    @staticmethod
    def _sanitize_arguments(tool_name: str, arguments: dict, question: str) -> dict:
        """Backward-compatible sanitization for callers using the legacy tool API."""
        clean = {key: value for key, value in arguments.items() if value not in (None, "", [], {})}
        q = question.casefold()
        if tool_name in {"aggregate_projects", "filter_projects"}:
            if not any(word in q for word in ("contractor", "assigned")): clean.pop("has_contractor", None)
            if "xen" not in q and "engineer" not in q: clean.pop("has_xen", None)
            if not any(word in q for word in ("cost", "budget", "expensive", "cheap", "under", "over", "between")):
                clean.pop("min_cost", None); clean.pop("max_cost", None)
            if clean.get("min_cost") == 0: clean.pop("min_cost")
            if clean.get("max_cost") == 0: clean.pop("max_cost")
        return clean
