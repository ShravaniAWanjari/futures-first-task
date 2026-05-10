"""
Module: schemas.py
Purpose: Standardized Pydantic interfaces for the orchestration pipeline.
Responsibilities: Ensures data predictability, type safety, and API readiness.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Generic, TypeVar

T = TypeVar("T")

class ErrorDetail(BaseModel):
    type: str
    message: str

class APIResponse(BaseModel, Generic[T]):
    success: bool
    request_id: str
    data: Optional[T] = None
    error: Optional[ErrorDetail] = None
    api_version: str = "1.0"

class ValidationResult(BaseModel):
    valid: bool
    severity: str = "INFO"
    message: str
    action: str = "accept"

class SQLTrace(BaseModel):
    tool: str = "query_structured_data"
    success: bool
    query_used: str
    error: Optional[str] = None
    timing_ms: float = 0.0
    table_references: List[str] = Field(default_factory=list)

class RetrievalResult(BaseModel):
    chunk_id: str
    source_file: str
    page_number: int
    section_title: str
    snippet_text: str
    similarity_score: float
    confidence: float

class RetrievalTrace(BaseModel):
    tool: str = "search_documents"
    success: bool
    n_results: int
    rejected_chunks: int = 0
    retrieval_scores: List[float] = Field(default_factory=list)
    average_confidence: float = 0.0
    error: Optional[str] = None
    timing_ms: float = 0.0

class IntentTrace(BaseModel):
    mode: str
    domain: str
    metric: Optional[str] = None
    dimension: Optional[str] = None
    entities: List[str] = Field(default_factory=list)
    confidence: float

class RoutingPlan(BaseModel):
    primary_route: str
    target_tables: List[str] = Field(default_factory=list)
    target_collections: List[str] = Field(default_factory=list)
    retrieval_strategy: str

class ClassificationTrace(BaseModel):
    query_type: str
    reasoning: str
    recommended_tools: List[str]
    confidence: float
    intent: Optional[IntentTrace] = None
    routing_plan: Optional[RoutingPlan] = None
    # Phase 7+: Conversational support fields
    conversational_response: Optional[str] = None
    conversational_action: Optional[str] = None
    follow_up_detected: Optional[bool] = None
    resolved_query: Optional[str] = None
    operational_domain: Optional[str] = None

class QueryTrace(BaseModel):
    request_id: str
    dataset: str
    classification: ClassificationTrace
    tool_executions: List[Any] = Field(default_factory=list)
    total_timing_ms: float = 0.0

class QueryResponse(BaseModel):
    request_id: str
    answer_context: str
    raw_reasoning: Optional[str] = None
    sources: List[str]
    trace: QueryTrace
    overall_confidence: float
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    # Analytical Presentation Pass
    structured_data: Optional[Dict[str, Any]] = None
    session_title: Optional[str] = None

class QueryRequest(BaseModel):
    query: str
    dataset: str
    request_id: Optional[str] = None

class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    context: Optional[str] = None
    sources: Optional[str] = None
    trace: Optional[str] = None
    structured_data: Optional[str] = None
    timestamp: str

class SessionResponse(BaseModel):
    id: str
    title: str
    workspace: str
    created_at: str
    updated_at: str
    messages: List[MessageResponse] = Field(default_factory=list)

class SuggestionResponse(BaseModel):
    suggestions: List[str]
