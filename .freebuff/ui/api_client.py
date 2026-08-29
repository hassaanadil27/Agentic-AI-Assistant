"""Service adapter for remote FastAPI or embedded Streamlit execution."""
from __future__ import annotations

import os
from dataclasses import asdict
from urllib.parse import urlparse

import requests

from agents.audit_agent import AuditResult
from models.messages import AgentReport, FinalReport
from models.schemas import DataQualityReport, DatasetMetadata

API_URL = os.getenv("API_URL", "").rstrip("/")


def _uses_embedded_service() -> bool:
    """Streamlit Cloud cannot run the repository's second web process."""
    if not API_URL:
        return True
    return (urlparse(API_URL).hostname or "").casefold() in {"localhost", "127.0.0.1", "::1"}


def _embedded_request(path: str, payload: dict | None = None) -> dict:
    """Run the same application services inside the Streamlit process."""
    payload = payload or {}
    if path == "/api/portfolio":
        from tools.data_loader import load_projects
        from tools.finance_tools import category_statistics, district_statistics

        return {
            "metadata": load_projects().model_dump(),
            "district_statistics": [item.model_dump() for item in district_statistics()],
            "category_statistics": [item.model_dump() for item in category_statistics()],
        }
    if path == "/api/data-quality":
        from tools.data_quality_tools import get_data_quality_report

        return get_data_quality_report().model_dump()
    if path == "/api/query":
        from agents.llm_provider import get_provider
        from agents.query_agent import QueryAgent

        provider, is_demo = get_provider()
        result = QueryAgent(provider).ask(payload["question"], payload.get("history", []))
        return {"answer": result.answer, "trace": result.trace, "is_demo": is_demo}
    if path == "/api/audit":
        from agents.audit_agent import AuditAgent
        from agents.llm_provider import get_provider
        from orchestration.state import save_audit_state

        provider, _ = get_provider()
        result = AuditAgent(provider).run(payload["goal"])
        save_audit_state(payload["goal"], result)
        return asdict(result)
    if path == "/api/review":
        from agents.coordinator_agent import CoordinatorAgent
        from agents.llm_provider import DemoProvider, get_provider
        from orchestration.state import save_run_log

        provider, is_demo = get_provider()
        try:
            report, activity, specialists = CoordinatorAgent(provider, is_demo).run_review(payload["budget_cap_m"])
        except Exception:
            report, activity, specialists = CoordinatorAgent(DemoProvider(), True).run_review(payload["budget_cap_m"])
        path_value = save_run_log(report, activity, specialists)
        return {
            "report": report.model_dump(),
            "activity": activity,
            "specialists": {name: value.model_dump() for name, value in specialists.items()},
            "log_path": str(path_value),
        }
    raise RuntimeError(f"Unsupported embedded service path: {path}")


def _request(method: str, path: str, **kwargs) -> dict:
    if _uses_embedded_service():
        return _embedded_request(path, kwargs.get("json"))
    try:
        response = requests.request(method, f"{API_URL}{path}", timeout=300, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        detail = ""
        if exc.response is not None:
            try:
                detail = exc.response.json().get("detail", "")
            except ValueError:
                detail = exc.response.text
        raise RuntimeError(detail or f"Cannot reach the configured API at {API_URL}.") from exc


def ask_query(question: str, history: list[dict]) -> tuple[str, list[str]]:
    data = _request("POST", "/api/query", json={"question": question, "history": history})
    return data["answer"], data["trace"]


def run_audit(goal: str) -> AuditResult:
    return AuditResult(**_request("POST", "/api/audit", json={"goal": goal}))


def run_review(budget_cap_m: float) -> tuple[FinalReport, list[str], dict[str, AgentReport], str]:
    data = _request("POST", "/api/review", json={"budget_cap_m": budget_cap_m})
    report = FinalReport.model_validate(data["report"])
    specialists = {name: AgentReport.model_validate(value) for name, value in data["specialists"].items()}
    return report, data["activity"], specialists, data["log_path"]


def get_portfolio() -> tuple[DatasetMetadata, list[dict], list[dict]]:
    data = _request("GET", "/api/portfolio")
    return DatasetMetadata.model_validate(data["metadata"]), data["district_statistics"], data["category_statistics"]


def get_quality() -> DataQualityReport:
    return DataQualityReport.model_validate(_request("GET", "/api/data-quality"))
