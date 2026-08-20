"""Track A natural-language Query Agent with a visible tool loop."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from agents.llm_provider import LLMProvider, extract_json_object
from tools.query_tools import aggregate_projects, filter_projects, get_project, group_projects


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
                    "never invent data. Dataset vocabulary: water means category PHE. For 'most expensive', sort_by=cost_m and descending=true. "
                    "For 'which district/category has most', use group_projects. Available tools: " + tool_help,
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
            elif action.get("action") == "final_answer" and any(line.startswith("ACT:") for line in trace):
                trace.append("STOP: grounded answer produced")
                return QueryAnswer(str(action.get("content", "No answer returned.")), trace)
            else:
                messages.append({"role": "user", "content": "You must call at least one valid tool before final_answer."})
        trace.append("OBSERVE: live planner did not complete; switching to deterministic planner")
        return self._deterministic(question, trace)

    def _deterministic(self, question: str, trace: list[str]) -> QueryAnswer:
        """Grounded fallback for API outages; covers the assignment's required queries."""
        from tools.data_loader import get_dataframe
        q = question.casefold()
        df = get_dataframe()
        categories = {str(v).casefold(): str(v) for v in df["category"].dropna().unique()}
        categories["water"] = "PHE"
        districts = {str(v).casefold(): str(v) for v in df["district"].dropna().unique()}
        statuses = {str(v).casefold(): str(v) for v in df["status"].dropna().unique()}
        category = next((v for k, v in categories.items() if k in q), None)
        district = next((v for k, v in districts.items() if k in q), None)
        status = next((v for k, v in statuses.items() if k in q), None)
        filters = {k: v for k, v in {"district": district, "category": category, "status": status}.items() if v}

        id_match = re.search(r"[A-Z]{2,5}-\d{4}-P\d", question, re.I)
        if id_match:
            args = {"global_id": id_match.group(0)}; trace.append(f"ACT: get_project({json.dumps(args)})")
            result = get_project(**args); data = result.model_dump() if result else None
            trace.extend([f"OBSERVE: {json.dumps(data, default=str)}", "STOP: deterministic grounded answer produced"])
            return QueryAnswer(json.dumps(data, indent=2, default=str) if data else "No project matched that Global ID.", trace)
        if "which district" in q and ("most" in q or "highest" in q):
            args = {"group_by": "district", "operation": "count", "category": category, "status": status, "limit": 5}
            args = {k: v for k, v in args.items() if v is not None}; trace.append(f"ACT: group_projects({json.dumps(args)})")
            result = group_projects(**args); trace.extend([f"OBSERVE: {json.dumps(result)}", "STOP: deterministic grounded answer produced"])
            return QueryAnswer("Highest ranked districts: " + "; ".join(f"{r['district']}: {int(r['value'])} projects" for r in result), trace)
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
        label = "PKR millions" if operation == "total_cost" else "projects"
        return QueryAnswer(f"Result: {result.value:,.2f} {label}. Filters: {result.filters_applied or 'none'}. Matching rows: {result.count}.", trace)

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
