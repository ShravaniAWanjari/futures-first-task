import logging
import uuid
import time
import os
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request, Body, Path, Query as FastQuery
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.schemas import (
    QueryRequest, QueryResponse, APIResponse, ErrorDetail, 
    SessionResponse, SuggestionResponse
)
from backend.system_health import get_system_health
from backend.config import Config
from backend.api.services.query_service import QueryService
from backend.api.services.session_service import SessionService
from backend.api import session_manager

# --- API Models ---

class SessionCreate(BaseModel):
    workspace: str = Field(default="vistastream", description="The initial environment for this session.")

class SessionUpdate(BaseModel):
    title: str

class ChatQuery(BaseModel):
    query: str
    session_id: str
    workspace: Optional[str] = None
    image: Optional[str] = None

# --- App Initialization ---

app = FastAPI(
    title="FuturesFirst Orchestration API",
    description="Refined backend service layer for secure multi-source orchestration.",
    version="1.1.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Structured Logging
logging.basicConfig(level=Config.LOG_LEVEL)
logger = logging.getLogger("api")

@app.on_event("startup")
def startup_event():
    logger.info("Initializing API Service (v1.1)...")
    session_manager.init_sessions_db()
    health = get_system_health()
    logger.info(f"System Health on Startup: {health['overall_status'].upper()}")

# --- Global Exception Handler ---

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", "UNKNOWN")
    logger.error(f"Unhandled Exception [REQ:{req_id}]: {str(exc)}", exc_info=True)
    
    status_code = 500
    if isinstance(exc, HTTPException):
        status_code = exc.status_code
        message = exc.detail
    else:
        message = "An unexpected internal error occurred."
        
    return JSONResponse(
        status_code=status_code,
        content=APIResponse(
            success=False,
            request_id=req_id,
            error=ErrorDetail(type=exc.__class__.__name__, message=str(message))
        ).model_dump()
    )

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    req_id = str(uuid.uuid4())[:8]
    request.state.request_id = req_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = req_id
    return response

# --- Query Endpoints ---

@app.post("/query", response_model=APIResponse[QueryResponse])
def handle_query(request: Request, chat_req: ChatQuery):
    req_id = request.state.request_id
    workspace = chat_req.workspace or "vistastream"
    
    result = QueryService.execute_query(
        query=chat_req.query,
        session_id=chat_req.session_id,
        workspace=workspace,
        request_id=req_id,
        image=chat_req.image
    )
    
    return APIResponse(
        success=True,
        request_id=req_id,
        data=result
    )

@app.get("/suggestions", response_model=APIResponse[SuggestionResponse])
def get_suggestions(request: Request, workspace: str = FastQuery("vistastream")):
    req_id = request.state.request_id
    suggestions = QueryService.get_dynamic_suggestions(workspace)
    return APIResponse(
        success=True,
        request_id=req_id,
        data=SuggestionResponse(suggestions=suggestions)
    )

# --- Session Management Endpoints ---

@app.get("/sessions", response_model=APIResponse[List[Dict[str, Any]]])
def get_all_sessions(request: Request, workspace: Optional[str] = FastQuery(None)):
    req_id = request.state.request_id
    sessions = SessionService.list_sessions(workspace)
    return APIResponse(success=True, request_id=req_id, data=sessions)

@app.post("/sessions", response_model=APIResponse[Dict[str, str]])
def create_new_session(request: Request, data: SessionCreate):
    req_id = request.state.request_id
    result = SessionService.create_session(workspace=data.workspace)
    return APIResponse(success=True, request_id=req_id, data=result)

@app.get("/sessions/{session_id}", response_model=APIResponse[SessionResponse])
def get_session_details(request: Request, session_id: str = Path(...)):
    req_id = request.state.request_id
    session = SessionService.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return APIResponse(success=True, request_id=req_id, data=session)

@app.delete("/sessions/{session_id}", response_model=APIResponse[Dict[str, str]])
def delete_chat_session(request: Request, session_id: str = Path(...)):
    req_id = request.state.request_id
    SessionService.delete_session(session_id)
    return APIResponse(success=True, request_id=req_id, data={"status": "deleted"})

@app.patch("/sessions/{session_id}", response_model=APIResponse[Dict[str, str]])
def update_chat_title(request: Request, session_id: str = Path(...), data: SessionUpdate = Body(...)):
    req_id = request.state.request_id
    SessionService.rename_session(session_id, data.title)
    return APIResponse(success=True, request_id=req_id, data={"status": "updated"})

# --- Operational Endpoints ---

@app.get("/health", response_model=APIResponse[Dict[str, Any]])
def health_check(request: Request, dataset: str = FastQuery("vistastream")):
    req_id = request.state.request_id
    health = get_system_health(dataset)
    return APIResponse(success=True, request_id=req_id, data=health)

@app.get("/verification", response_model=APIResponse[Dict[str, str]])
def verification_report(request: Request):
    req_id = request.state.request_id
    report_path = os.path.join(Config.BASE_DIR, "docs", "reports", "verification_report.txt")
    if not os.path.exists(report_path):
         return APIResponse(success=False, request_id=req_id, error=ErrorDetail(type="FileNotFound", message="Report not found."))
    
    with open(report_path, "r", encoding="utf-8") as f:
        return APIResponse(success=True, request_id=req_id, data={"report": f.read()})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
