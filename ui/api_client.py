"""Typed client used by Streamlit to call the FastAPI backend."""
from __future__ import annotations

import os
import requests

from agents.audit_agent import AuditResult
from models.messages import AgentReport, FinalReport
from models.schemas import DataQualityReport, DatasetMetadata

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")


def _request(method: str, path: str, **kwargs) -> dict:
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
        raise RuntimeError(detail or f"Cannot reach the API at {API_URL}. Start it with: python -m uvicorn api:app --reload") from exc


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
