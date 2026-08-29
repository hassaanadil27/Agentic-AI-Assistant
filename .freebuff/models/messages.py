"""
Structured message schemas used for ALL inter-agent communication.

Why this file exists (viva note):
Every specialist agent returns one of these Pydantic objects instead of
free-form text. This is what makes the "multi-agent communication" real
and auditable rather than just several different prompts glued together.
The Coordinator only ever reads structured fields (agent_name, findings,
recommended_projects, evidence, ...) -- it never has to re-parse prose.
"""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class ToolCallLog(BaseModel):
    """A single record of a tool invocation, used for the traceability log."""
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    timestamp: str
    result_summary: str


class Evidence(BaseModel):
    """A concrete, dataset-grounded fact backing up a claim."""
    global_id: Optional[str] = None
    field: str
    value: Any
    source_tool: str


class AgentFinding(BaseModel):
    """One discrete observation made by a specialist agent."""
    agent_name: str
    finding_id: str
    title: str
    severity: str  # "low" | "medium" | "high"
    explanation: str
    affected_projects: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    recommendation: str = ""


class AgentReport(BaseModel):
    """The full structured output a specialist agent hands to the Coordinator."""
    agent_name: str
    summary: str
    findings: list[AgentFinding] = Field(default_factory=list)
    recommended_projects: list[str] = Field(default_factory=list)
    rejected_projects: list[str] = Field(default_factory=list)
    data_quality_notes: list[str] = Field(default_factory=list)
    tool_calls: list[ToolCallLog] = Field(default_factory=list)


class ConflictRecord(BaseModel):
    """A visible disagreement between two or more specialists that the
    Coordinator had to resolve. This directly satisfies the assignment's
    'visible disagreement / trade-off' requirement."""
    issue: str
    global_id: Optional[str] = None
    finance_position: Optional[str] = None
    delivery_position: Optional[str] = None
    equity_position: Optional[str] = None
    coordinator_resolution: str


class RecommendedProject(BaseModel):
    """One project in the Coordinator's final funding shortlist."""
    global_id: str
    description: str
    district: str
    category: str
    cost_m: float
    score: float
    finance_assessment: str
    delivery_assessment: str
    equity_assessment: str
    reason_selected: str


class FinalReport(BaseModel):
    """The Coordinator's complete, human-readable output."""
    executive_summary: str
    recommended_projects: list[RecommendedProject]
    total_recommended_m: float
    budget_available_m: float
    remaining_budget_m: float
    finance_findings: list[AgentFinding]
    delivery_findings: list[AgentFinding]
    equity_findings: list[AgentFinding]
    conflicts: list[ConflictRecord]
    data_quality_warnings: list[str]
