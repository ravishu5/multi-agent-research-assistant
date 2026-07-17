"""Pydantic models for the research assistant API."""

from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from typing import Any


# --- Enums ---

class JobStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    RESEARCHING = "researching"
    SUMMARIZING = "summarizing"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentRole(str, Enum):
    PLANNER = "planner"
    RESEARCHER = "researcher"
    SUMMARIZER = "summarizer"


# --- Request Models ---

class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=5, max_length=2000, description="The research question or topic")
    depth: str = Field(default="standard", pattern="^(quick|standard|deep)$", description="Research depth")
    max_sources: int = Field(default=5, ge=1, le=20, description="Maximum sources to consult")


class ApprovalRequest(BaseModel):
    approved: bool
    feedback: str | None = Field(default=None, max_length=1000)


# --- Agent State (LangGraph) ---

class ResearchPlan(BaseModel):
    sub_questions: list[str] = []
    search_queries: list[str] = []
    approach: str = ""


class SourceResult(BaseModel):
    query: str
    title: str
    snippet: str
    url: str = ""
    relevance_score: float = 0.0


class AgentTrace(BaseModel):
    agent: AgentRole
    action: str
    input_summary: str = ""
    output_summary: str = ""
    duration_ms: float = 0.0
    token_usage: dict[str, int] = {}
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GraphState(BaseModel):
    """State that flows through the LangGraph workflow."""
    job_id: str = ""
    query: str = ""
    depth: str = "standard"
    max_sources: int = 5

    # Planner output
    plan: ResearchPlan = Field(default_factory=ResearchPlan)

    # Researcher output
    sources: list[SourceResult] = []
    raw_findings: str = ""

    # Summarizer output
    summary: str = ""
    key_points: list[str] = []
    confidence_score: float = 0.0

    # Human-in-the-loop
    needs_approval: bool = False
    approved: bool = False
    approval_feedback: str = ""

    # Observability
    traces: list[AgentTrace] = []
    errors: list[str] = []
    status: JobStatus = JobStatus.PENDING

    # Guardrail flags
    guardrail_results: dict[str, Any] = {}


# --- Response Models ---

class JobSubmitResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: str
    created_at: datetime
    updated_at: datetime
    traces: list[AgentTrace] = []
    errors: list[str] = []


class JobResultResponse(BaseModel):
    job_id: str
    status: JobStatus
    query: str
    plan: ResearchPlan
    sources: list[SourceResult]
    summary: str
    key_points: list[str]
    confidence_score: float
    traces: list[AgentTrace]
    guardrail_results: dict[str, Any]
    created_at: datetime
    completed_at: datetime | None
