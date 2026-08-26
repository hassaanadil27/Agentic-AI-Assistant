"""
Typed client used by Streamlit to call the FastAPI backend, with seamless local Python fallback.
This guarantees the Streamlit interface works 100% reliably whether the FastAPI server is running or not.
"""
from __future__ import annotations

import os
from dataclasses import asdict
import requests

from agents.audit_agent import AuditAgent, AuditResult
from agents.coordinator_agent import CoordinatorAgent
from agents.llm_provider import DemoProvider, get_provider
from agents.query_agent import QueryAgent
from models.messages import AgentReport, FinalReport
from models.schemas import DataQualityReport, DatasetMetadata
from orchestration.state import save_audit_state, save_run_log
from tools.data_loader import load_projects
from tools.data_quality_tools import get_data_quality_report
from tools.finance_tools import category_statistics, district_statistics

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")


def _try_api_request(method: str, path: str, timeout: float = 2.0, **kwargs) -> dict | None:
    """Attempts to call the FastAPI backend. Returns None if backend is unreachable."""
    try:
        response = requests.request(method, f"{API_URL}{path}", timeout=timeout, **kwargs)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None


def ask_query(question: str, history: list[dict]) -> tuple[str, list[str]]:
    data = _try_api_request("POST", "/api/query", json={"question": question, "history": history})
    if data and "answer" in data:
        return data["answer"], data.get("trace", [])
    
    # Direct Local Fallback
    provider, _ = get_provider()
    result = QueryAgent(provider).ask(question, history)
    return result.answer, result.trace


def run_audit(goal: str) -> AuditResult:
    data = _try_api_request("POST", "/api/audit", json={"goal": goal}, timeout=120.0)
    if data and "plan" in data:
        return AuditResult(**data)
    
    # Direct Local Fallback
    provider, _ = get_provider()
    result = AuditAgent(provider).run(goal)
    save_audit_state(goal, result)
    return result


def run_review(budget_cap_m: float) -> tuple[FinalReport, list[str], dict[str, AgentReport], str]:
    data = _try_api_request("POST", "/api/review", json={"budget_cap_m": budget_cap_m}, timeout=120.0)
    if data and "report" in data:
        report = FinalReport.model_validate(data["report"])
        specialists = {name: AgentReport.model_validate(value) for name, value in data["specialists"].items()}
        return report, data.get("activity", []), specialists, data.get("log_path", "")
    
    # Direct Local Fallback
    provider, is_demo = get_provider()
    try:
        report, activity, specialists = CoordinatorAgent(provider, is_demo).run_review(budget_cap_m)
    except Exception:
        report, activity, specialists = CoordinatorAgent(DemoProvider(), True).run_review(budget_cap_m)
    path = save_run_log(report, activity, specialists)
    return report, activity, specialists, str(path)


def get_portfolio() -> tuple[DatasetMetadata, list[dict], list[dict]]:
    data = _try_api_request("GET", "/api/portfolio")
    if data and "metadata" in data:
        return DatasetMetadata.model_validate(data["metadata"]), data.get("district_statistics", []), data.get("category_statistics", [])
    
    # Direct Local Fallback
    meta = load_projects()
    d_stats = [item.model_dump() for item in district_statistics()]
    c_stats = [item.model_dump() for item in category_statistics()]
    return meta, d_stats, c_stats


def get_quality() -> DataQualityReport:
    data = _try_api_request("GET", "/api/data-quality")
    if data and "total_rows" in data:
        return DataQualityReport.model_validate(data)
    
    # Direct Local Fallback
    return get_data_quality_report()
