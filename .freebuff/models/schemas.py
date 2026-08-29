"""
Schemas describing tool inputs/outputs and dataset-level structures.
Kept separate from messages.py (agent<->agent communication) for clarity.
"""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class ProjectRecord(BaseModel):
    """One normalized project row, safe to hand to an LLM (small, structured)."""
    global_id: str
    district: str
    phase: str
    category: str
    description: str
    executing_agency: Optional[str] = None
    cost_m: float
    contractor_raw: Optional[str] = None
    contractor_normalized: Optional[str] = None
    nits: Optional[str] = None
    progress_pct: float
    status: str
    work_started: Optional[str] = None
    xen_name: Optional[str] = None
    xen_contact_raw: Optional[str] = None
    xen_contact_normalized: Optional[str] = None
    has_contractor: bool = False
    has_xen: bool = False
    has_work_started: bool = False


class DatasetMetadata(BaseModel):
    total_projects: int
    total_portfolio_m: float
    districts: int
    categories: int
    status_counts: dict[str, int]
    load_warnings: list[str] = Field(default_factory=list)


class FilterResult(BaseModel):
    count: int
    truncated: bool
    projects: list[ProjectRecord]
    filters_applied: dict[str, Any]


class AggregateResult(BaseModel):
    operation: str
    value: Optional[float]
    count: int
    filters_applied: dict[str, Any]


class DistrictStat(BaseModel):
    district: str
    project_count: int
    total_budget_m: float
    avg_cost_m: float
    not_started_count: int
    not_started_budget_m: float
    pct_not_started_by_count: float
    pct_of_portfolio_budget: float


class CategoryStat(BaseModel):
    category: str
    project_count: int
    total_budget_m: float
    avg_cost_m: float
    not_started_count: int
    not_started_budget_m: float


class OutlierResult(BaseModel):
    method: str
    global_id: str
    category: str
    cost_m: float
    category_median_m: float
    category_q1_m: float
    category_q3_m: float
    reason: str


class DeliveryRisk(BaseModel):
    global_id: str
    risk_type: str
    detail: str
    status: str
    progress_pct: float


class EquityRisk(BaseModel):
    risk_type: str
    subject: str  # district or category name
    detail: str
    metric_value: float


class DataQualityReport(BaseModel):
    total_rows: int
    missing_contractor: int
    missing_xen: int
    missing_work_started: int
    invalid_cost_count: int
    invalid_progress_count: int
    duplicate_global_ids: list[str]
    agency_variant_groups: dict[str, list[str]]
    contractor_variant_examples: list[dict[str, str]]
    suspicious_phone_examples: list[dict[str, str]]
