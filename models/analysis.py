"""Validated contracts for project-aware analytical questions and results."""
from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class AnalysisFilter(BaseModel):
    column: str
    operator: Literal["eq", "ne", "gt", "gte", "lt", "lte", "contains", "in"] = "eq"
    value: Any


class AnalysisPlan(BaseModel):
    intent: Literal["overview", "schema", "aggregate", "group", "records", "distribution", "correlation", "lookup", "project_info", "clarify"]
    operation: Literal["count", "distinct_count", "sum", "mean", "median", "mode", "min", "max", "std", "percentage", "list", "correlation"] = "count"
    target_column: str | None = None
    secondary_column: str | None = None
    group_by: list[str] = Field(default_factory=list)
    filters: list[AnalysisFilter] = Field(default_factory=list)
    sort: Literal["ascending", "descending", "none"] = "none"
    limit: int = Field(default=10, ge=1, le=100)
    chart: Literal["bar", "line", "pie", "scatter", "histogram", "none"] = "none"
    clarification: str | None = None


class AnalysisEvidence(BaseModel):
    dataset: str
    rows_available: int
    rows_analyzed: int
    columns: list[str]
    filters: list[dict[str, Any]]
    operation: str
    missing_values_excluded: int = 0


class AnalysisResult(BaseModel):
    success: bool
    intent: str
    answer: str
    evidence: AnalysisEvidence | None = None
    table: list[dict[str, Any]] = Field(default_factory=list)
    chart: dict[str, Any] | None = None
    plan: AnalysisPlan | None = None
    validation: str = "not_run"
    error: str | None = None
