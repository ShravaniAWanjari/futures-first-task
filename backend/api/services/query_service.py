import uuid
import time
import logging
from typing import List, Optional
from backend.orchestration.orchestrator import orchestrate_query
from backend.schemas import QueryRequest, QueryResponse
from backend.api import session_manager
from backend.api.services.response_synthesizer import synthesize_response, generate_session_title

logger = logging.getLogger("api")

class QueryService:
    @staticmethod
    def execute_query(query: str, session_id: str, workspace: str, request_id: Optional[str] = None) -> QueryResponse:
        """
        Coordinates orchestration, response synthesis, and message persistence.
        """
        req_id = request_id or str(uuid.uuid4())[:8]
        
        # 1. Create Orchestration Request
        orchestrator_req = QueryRequest(
            query=query,
            dataset=workspace,
            request_id=req_id
        )
        
        # 2. Persist User Message
        session_manager.add_message(
            session_id=session_id,
            role="user",
            content=query
        )
        
        # 3. Fetch History for Context Resolution
        history = session_manager.get_session_messages(session_id)
        
        # 4. Execute Orchestration with Context
        response = orchestrate_query(orchestrator_req, history=history)
        
        # 4. Synthesize Response — transform raw output into management-grade narrative
        raw_context = response.answer_context
        synthesized_context = synthesize_response(
            answer_context=raw_context,
            sources=response.sources,
            confidence=response.overall_confidence,
            history=history,
            original_query=query
        )
        response.answer_context = synthesized_context
        
        # 5. Persist Assistant Response
        session_manager.add_message(
            session_id=session_id,
            role="assistant",
            content=synthesized_context,
            context=raw_context,  # preserve raw for source panel
            sources=",".join(response.sources),
            trace=response.trace.model_dump_json() if response.trace else None
        )
        
        # 6. Auto-generate semantic title for new sessions
        try:
            messages = session_manager.get_session_messages(session_id)
            if messages and len(messages) <= 2:
                # First interaction — generate title
                title = generate_session_title(query)
                session_manager.update_session_title(session_id, title)
                logger.info(f"Session titled: '{title}'")
        except Exception as e:
            logger.warning(f"Title generation failed: {e}")
        
        return response

    @staticmethod
    def get_dynamic_suggestions(workspace: str) -> List[str]:
        """
        Generates adaptive workspace-aware query suggestions.
        """
        if workspace == "vistastream":
            return [
                "What was the subscriber growth in APAC during Q2?",
                "Which marketing platforms had the best ROI in North America?",
                "Are there any localization quality complaints in the recent report?",
                "Summarize the Q3 content roadmap for science-fiction.",
                "Compare ad-spend efficiency between Europe and APAC."
            ]
        else:
            return [
                "Why are there so many warnings in the watch activity data?",
                "What is the current status of subtitle quality improvements?",
                "Summarize the internal notes for Galaxy Burn release.",
                "How does the marketing spend correlate with regional performance?",
                "List the data quality inconsistencies found in the latest upload."
            ]
