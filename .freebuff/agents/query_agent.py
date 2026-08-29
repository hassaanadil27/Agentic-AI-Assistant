"""Track A natural-language Query Agent with a visible tool loop."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from agents.llm_provider import DemoProvider, LLMProvider, extract_json_object
from tools.query_tools import aggregate_projects, filter_projects, get_project
from tools.ranking_tools import rank_funding_candidates

# ---------------------------------------------------------------------------
# Status synonym table
# Maps common plain-English words to the exact status values in the dataset.
# Order matters: longer / more-specific phrases should come first so that
# "not started" is matched before "started".
# ---------------------------------------------------------------------------
STATUS_SYNONYMS: dict[str, str] = {
    "not started": "Not Started",
    "unstarted": "Not Started",
    "pending": "Not Started",
    "upcoming": "Not Started",
    "not begun": "Not Started",
    "in progress": "In Progress",
    "in-progress": "In Progress",
    "ongoing": "In Progress",
    "underway": "In Progress",
    "running": "In Progress",
    "active": "In Progress",
    "started": "In Progress",
    "completed": "Completed",
    "complete": "Completed",
    "done": "Completed",
    "finished": "Completed",
    "delivered": "Completed",
    "closed": "Completed",
}

try:
    from tools.query_tools import group_projects
except ImportError:  # Backward compatibility for partially updated deployments.
    def group_projects(
        group_by: str,
        operation: str = "count",
        district: str | None = None,
        category: str | None = None,
        status: str | None = None,
        phase: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        from tools.data_loader import get_dataframe

        if group_by not in {"district", "category", "status", "phase"}:
            raise ValueError("group_by must be district, category, status, or phase")
        df = get_dataframe()
        for column, value in {"district": district, "category": category, "status": status, "phase": phase}.items():
            if value:
                df = df[df[column].astype(str).str.casefold() == value.casefold()]
        if operation == "count":
            grouped = df.groupby(group_by).size().rename("value").reset_index()
        elif operation == "total_cost":
            grouped = df.groupby(group_by)["cost_m"].sum().rename("value").reset_index()
        elif operation == "average_cost":
            grouped = df.groupby(group_by)["cost_m"].mean().rename("value").reset_index()
        else:
            raise ValueError("operation must be count, total_cost, or average_cost")
        return grouped.sort_values("value", ascending=False).head(min(limit, 50)).to_dict("records")


@dataclass
class QueryAnswer:
    answer: str
    trace: list[str] = field(default_factory=list)


class QueryAgent:
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self.tools = {"filter_projects": filter_projects, "aggregate_projects": aggregate_projects, "group_projects": group_projects, "get_project": get_project}

    def ask(self, question: str, history: list[dict] | None = None) -> QueryAnswer:
        trace = [f"PLAN: interpret question and choose dataset tools — {question}"]
        # Treat portfolio-priority questions as a first-class intent in both
        # demo and live modes. Otherwise vague wording such as "which project"
        # can fall through to the default unfiltered count.
        if self._asks_which_project_to_start(question):
            return self._rank_start_candidates(trace)
        if isinstance(self.provider, DemoProvider):
            return self._deterministic(question, trace)
        tool_help = (
            "filter_projects(district,category,status,phase,min_cost,max_cost,has_contractor,has_xen,global_ids,limit,sort_by,descending); "
            "aggregate_projects(operation,district,category,status,phase,min_cost,max_cost,has_contractor,has_xen), "
            "operations: count,total_cost,average_cost,median_cost,min_cost,max_cost,average_progress; "
            "group_projects(group_by,operation,district,category,status,phase,limit) for ranked grouped results; "
            "get_project(global_id)."
        )
        messages = [{"role": "user", "content": question}]
        for step in range(6):
            try:
                response = self.provider.complete(
                    "You are the Track A BSDI Query Agent. Use tools before answering any numerical/project question. "
                    "Return exactly one JSON object: {\"action\":\"call_tool\",\"tool\":name,\"arguments\":{...}} "
                    "or {\"action\":\"final_answer\",\"content\":answer}. Cite filters, counts and IDs from tool results; "
                    "never invent data. "
                    "Dataset vocabulary: water means category PHE. "
                    "Status synonyms — always map to these exact values: "
                    "pending/unstarted/upcoming/not-started → 'Not Started'; "
                    "done/finished/complete/completed/delivered/closed → 'Completed'; "
                    "ongoing/active/underway/running/in-progress → 'In Progress'. "
                    "For 'most expensive', sort_by=cost_m and descending=true. "
                    "For 'which district/category has most', use group_projects. "
                    "Always give a friendly natural-language final_answer, not raw JSON or debug text. "
                    "Available tools: " + tool_help,
                    messages,
                )
            except Exception as exc:
                trace.append(f"OBSERVE: live planner unavailable ({exc}); switching to deterministic planner")
                return self._deterministic(question, trace)
            action = extract_json_object(response.text)
            if not action:
                messages.append({"role": "user", "content": "Return valid JSON only and call a tool first."}); continue
            if action.get("action") == "call_tool" and action.get("tool") in self.tools:
                name = action["tool"]
                arguments = self._sanitize_arguments(name, action.get("arguments", {}), question)
                trace.append(f"ACT: {name}({json.dumps(arguments, default=str)})")
                try: result = self.tools[name](**arguments)
                except Exception as exc: result = {"error": str(exc)}
                data = result.model_dump() if hasattr(result, "model_dump") else result
                trace.append(f"OBSERVE: {json.dumps(data, default=str)[:1200]}")
                messages.extend([{"role": "assistant", "content": response.text}, {"role": "user", "content": "TOOL RESULT: " + json.dumps(data, default=str)}])
            elif action.get("action") == "final_answer":
                trace.append("STOP: grounded answer produced")
                return QueryAnswer(str(action.get("content", "No answer returned.")), trace)
            else:
                messages.append({"role": "user", "content": "Return a valid call_tool or final_answer JSON object."})
        trace.append("OBSERVE: live planner did not complete; switching to deterministic planner")
        return self._deterministic(question, trace)

    @staticmethod
    def _asks_which_project_to_start(question: str) -> bool:
        q = question.casefold()
        project_reference = re.search(r"\b(project|scheme|initiative)s?\b", q)
        priority_language = any(
            phrase in q
            for phrase in (
                "start first",
                "begin first",
                "prioritize first",
                "prioritise first",
                "highest priority",
                "top priority",
                "should we start",
                "should be started",
            )
        )
        return bool(project_reference and priority_language)

    @staticmethod
    def _rank_start_candidates(trace: list[str]) -> QueryAnswer:
        args = {"budget_cap_m": 2000.0}
        trace.append(f"ACT: rank_funding_candidates({json.dumps(args)})")
        ranked = rank_funding_candidates(**args)
        trace.append(f"OBSERVE: {len(ranked)} Not Started projects ranked")
        if not ranked:
            trace.append("STOP: no eligible Not Started projects found")
            return QueryAnswer("There are no Not Started projects eligible for prioritization.", trace)

        winner = ranked[0]
        trace.append("STOP: deterministic grounded priority recommendation produced")
        return QueryAnswer(
            f"Start **{winner.global_id}** first: {winner.description} "
            f"({winner.district}, {winner.category}; PKR {winner.cost_m:,.2f}M). "
            f"It is the highest-ranked Not Started project with an overall score of "
            f"{winner.final_score:.2f}/100 (finance {winner.finance_score:.2f}, delivery "
            f"{winner.delivery_score:.2f}, equity {winner.equity_score:.2f}).",
            trace,
        )

    def _deterministic(self, question: str, trace: list[str]) -> QueryAnswer:
        """Grounded fallback for API outages; covers the assignment's required queries."""
        from tools.data_loader import get_dataframe
        q = question.casefold()

        # Keep ordinary conversation out of the data-query fallback. Without
        # this guard, any greeting was incorrectly answered with the row count.
        if re.search(r"\b(hi|hello|hey|salam|assalam)\b", q) or any(
            phrase in q for phrase in ("your name", "who are you", "what can you do")
        ):
            trace.append("STOP: conversational introduction produced")
            return QueryAnswer(
                "Hi! I’m the BSDI Project AI Agent. I can compare project allocations, "
                "budgets, sectors, districts, statuses, delivery risks, and individual projects.",
                trace,
            )

        df = get_dataframe()
        categories = {str(v).casefold(): str(v) for v in df["category"].dropna().unique()}
        categories["water"] = "PHE"
        districts = {str(v).casefold(): str(v) for v in df["district"].dropna().unique()}
        statuses = {str(v).casefold(): str(v) for v in df["status"].dropna().unique()}
        category = next((v for k, v in categories.items() if k in q), None)
        district = next((v for k, v in districts.items() if k in q), None)

        # --- Status resolution: synonym table first, then exact dataset values ---
        status: str | None = None
        for synonym, canonical in STATUS_SYNONYMS.items():
            if synonym in q:
                status = canonical
                break
        if status is None:
            status = next((v for k, v in statuses.items() if k in q), None)

        filters = {k: v for k, v in {"district": district, "category": category, "status": status}.items() if v}

        id_match = re.search(r"[A-Z]{2,5}-\d{4}-P\d", question, re.I)
        if id_match:
            args = {"global_id": id_match.group(0)}; trace.append(f"ACT: get_project({json.dumps(args)})")
            result = get_project(**args); data = result.model_dump() if result else None
            trace.extend([f"OBSERVE: {json.dumps(data, default=str)}", "STOP: deterministic grounded answer produced"])
            return QueryAnswer(json.dumps(data, indent=2, default=str) if data else "No project matched that Global ID.", trace)
        asks_for_top = any(term in q for term in ("most", "highest", "largest", "top"))
        asks_for_money = any(term in q for term in ("allocation", "budget", "cost", "funding", "value"))
        group_dimension = (
            "category" if any(term in q for term in ("sector", "category"))
            else "district" if "district" in q
            else None
        )
        if group_dimension and asks_for_top:
            operation = "total_cost" if asks_for_money else "count"
            args = {"group_by": group_dimension, "operation": operation, "category": category, "status": status, "limit": 5}
            args = {k: v for k, v in args.items() if v is not None}; trace.append(f"ACT: group_projects({json.dumps(args)})")
            result = group_projects(**args); trace.extend([f"OBSERVE: {json.dumps(result)}", "STOP: deterministic grounded answer produced"])
            label = "sectors" if group_dimension == "category" else "districts"
            if operation == "total_cost":
                summary = "; ".join(f"{r[group_dimension]}: PKR {r['value']:,.2f}M" for r in result)
            else:
                summary = "; ".join(f"{r[group_dimension]}: {int(r['value'])} projects" for r in result)
            return QueryAnswer(f"Highest ranked {label}: {summary}", trace)
        if "most expensive" in q:
            number = int((re.search(r"\b(\d+)\b", q) or [None, "5"])[1])
            args = {**filters, "limit": number, "sort_by": "cost_m", "descending": True}
            trace.append(f"ACT: filter_projects({json.dumps(args)})"); result = filter_projects(**args)
            data = result.model_dump(); trace.extend([f"OBSERVE: {json.dumps(data, default=str)[:2000]}", "STOP: deterministic grounded answer produced"])
            return QueryAnswer("Most expensive matches:\n" + "\n".join(f"- {p.global_id}: {p.description} — PKR {p.cost_m:.2f}M" for p in result.projects), trace)
        operation = "total_cost" if any(term in q for term in ("total budget", "total cost", "budget of")) else "count"
        args = {"operation": operation, **filters}; trace.append(f"ACT: aggregate_projects({json.dumps(args)})")
        result = aggregate_projects(**args); data = result.model_dump()
        trace.extend([f"OBSERVE: {json.dumps(data)}", "STOP: deterministic grounded answer produced"])

        # Build a friendly natural-language answer instead of raw internal debug text.
        filter_parts = []
        if status:
            filter_parts.append(f"**{status}**")
        if category:
            filter_parts.append(f"in category **{category}**")
        if district:
            filter_parts.append(f"in district **{district}**")
        filter_clause = " ".join(filter_parts) if filter_parts else "in the portfolio"

        if operation == "count":
            count_val = int(result.value) if result.value is not None else 0
            return QueryAnswer(
                f"There are **{count_val:,}** {filter_clause} project(s).",
                trace,
            )
        else:
            return QueryAnswer(
                f"The total budget for {filter_clause} projects is **PKR {result.value:,.2f} million** "
                f"(PKR millions; {result.count:,} project(s)).",
                trace,
            )

    @staticmethod
    def _sanitize_arguments(tool_name: str, arguments: dict, question: str) -> dict:
        """Remove fabricated/default filters that would silently corrupt results."""
        clean = {key: value for key, value in arguments.items() if value not in (None, "", [], {})}
        q = question.casefold()
        if tool_name in {"aggregate_projects", "filter_projects"}:
            if not any(word in q for word in ("contractor", "assigned")): clean.pop("has_contractor", None)
            if "xen" not in q and "engineer" not in q: clean.pop("has_xen", None)
            if not any(word in q for word in ("cost", "budget", "expensive", "cheap", "under", "over", "between")):
                clean.pop("min_cost", None); clean.pop("max_cost", None)
            # A zero bound filled in as a schema default is almost never an intended filter.
            if clean.get("min_cost") == 0: clean.pop("min_cost")
            if clean.get("max_cost") == 0: clean.pop("max_cost")
        return clean
