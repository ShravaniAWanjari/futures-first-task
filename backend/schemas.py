"""
Module: schemas.py
Purpose: Standardized Pydantic interfaces for the orchestration pipeline.
Responsibilities: Ensures data predictability, type safety, and API readiness.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

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
    error: Optional[str] = None
    timing_ms: float = 0.0

class ClassificationTrace(BaseModel):
    query_type: str
    reasoning: str
    recommended_tools: List[str]
    confidence: float

class QueryTrace(BaseModel):
    request_id: str
    dataset: str
    classification: ClassificationTrace
    tool_executions: List[Any] = Field(default_factory=list)
    total_timing_ms: float = 0.0

class QueryResponse(BaseModel):
    request_id: str
    answer_context: str
    sources: List[str]
    trace: QueryTrace
    overall_confidence: float
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)

class QueryRequest(BaseModel):
    query: str
    dataset: str
    request_id: Optional[str] = None
