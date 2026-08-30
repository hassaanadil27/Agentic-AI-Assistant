"""FastAPI backend for the BSDI multi-agent review application."""
from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agents.audit_agent import AuditAgent
from agents.coordinator_agent import CoordinatorAgent
from agents.llm_provider import DemoProvider, get_provider
from agents.query_agent import QueryAgent
from orchestration.state import save_audit_state, save_run_log
from tools.data_loader import load_projects
from tools.data_quality_tools import get_data_quality_report
from tools.finance_tools import category_statistics, district_statistics


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    history: list[dict] = Field(default_factory=list)


class AuditRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=4000)


class ReviewRequest(BaseModel):
    budget_cap_m: float = Field(default=2000.0, gt=0, le=1_000_000)


@asynccontextmanager
async def lifespan(_: FastAPI):
    load_projects()
    yield


app = FastAPI(title="BSDI Project AI API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/portfolio")
def portfolio() -> dict:
    return {
        "metadata": load_projects().model_dump(),
        "district_statistics": [item.model_dump() for item in district_statistics()],
        "category_statistics": [item.model_dump() for item in category_statistics()],
    }


@app.get("/api/data-quality")
def data_quality() -> dict:
    return get_data_quality_report().model_dump()


@app.post("/api/query")
def query(payload: QueryRequest) -> dict:
    try:
        provider, is_demo = get_provider()
        result = QueryAgent(provider).ask(payload.question, payload.history)
        return {**result.model_dump(), "is_demo": is_demo}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Query failed: {exc}") from exc


@app.post("/api/audit")
def audit(payload: AuditRequest) -> dict:
    try:
        provider, _ = get_provider()
        result = AuditAgent(provider).run(payload.goal)
        save_audit_state(payload.goal, result)
        return asdict(result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Audit failed: {exc}") from exc


@app.post("/api/review")
def review(payload: ReviewRequest) -> dict:
    try:
        provider, is_demo = get_provider()
        try:
            report, activity, specialists = CoordinatorAgent(provider, is_demo).run_review(payload.budget_cap_m)
        except Exception:
            report, activity, specialists = CoordinatorAgent(DemoProvider(), True).run_review(payload.budget_cap_m)
        path = save_run_log(report, activity, specialists)
        return {
            "report": report.model_dump(),
            "activity": activity,
            "specialists": {name: value.model_dump() for name, value in specialists.items()},
            "log_path": str(path),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Review failed: {exc}") from exc
