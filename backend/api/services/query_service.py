import uuid
import time
import logging
import json
from typing import List, Optional
from backend.orchestration.orchestrator import orchestrate_query
from backend.schemas import QueryRequest, QueryResponse
from backend.api import session_manager
from backend.api.services.response_synthesizer import synthesize_response, generate_session_title

logger = logging.getLogger("api")


def _build_rich_raw_reasoning(response: QueryResponse, fallback_context: str) -> str:
    """
    Build a richer debug-style reasoning block so the right sidebar
    consistently shows route decisions and retrieval evidence.
    """
    trace = response.trace
    if not trace:
        return fallback_context

    classification = trace.classification
    route = getattr(classification, "query_type", "unknown")
    confidence = getattr(classification, "confidence", 0.0)
    reason = getattr(classification, "reasoning", "")
    intent = getattr(classification, "intent", None)
    routing_plan = getattr(classification, "routing_plan", None)

    parts: List[str] = []
    parts.append("=== ORCHESTRATION REASONING ===")
    parts.append(f"Route: {route} (confidence: {confidence:.2f})")
    if reason:
        parts.append(f"Classifier rationale: {reason}")

    if intent:
        try:
            parts.append("Intent: " + json.dumps(intent, ensure_ascii=True))
        except Exception:
            parts.append(f"Intent: {intent}")

    if routing_plan:
        try:
            parts.append("Routing plan: " + json.dumps(routing_plan, ensure_ascii=True))
        except Exception:
            parts.append(f"Routing plan: {routing_plan}")

    for i, tool in enumerate(trace.tool_executions or [], 1):
        tool_name = getattr(tool, "tool", "unknown")
        success = getattr(tool, "success", False)
        timing_ms = getattr(tool, "timing_ms", None)
        parts.append(f"[Tool {i}] {tool_name} | success={success} | latency={timing_ms}ms")
        if tool_name == "search_documents":
            parts.append(
                "  retrieval: n_results="
                f"{getattr(tool, 'n_results', 0)}, avg_confidence={getattr(tool, 'average_confidence', 0.0):.2f}, "
                f"rejected_chunks={getattr(tool, 'rejected_chunks', 0)}"
            )
        if tool_name == "query_structured_data":
            query_used = getattr(tool, "query_used", None)
            if query_used:
                parts.append(f"  sql: {query_used}")
            tables = getattr(tool, "table_references", None) or []
            if tables:
                parts.append(f"  tables: {', '.join(tables)}")

    if fallback_context:
        parts.append("")
        parts.append(fallback_context)

    return "\n".join(parts)

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
        
        # 4. Capture clean orchestration output for synthesis
        # Keep synthesis input free of debug/routing metadata.
        synthesis_input_context = response.answer_context
        raw_context = _build_rich_raw_reasoning(response, response.answer_context)
        
        # 4. Synthesize Response — transform raw output into management-grade narrative
        synthesized_context, structured_data = synthesize_response(
            answer_context=synthesis_input_context,
            sources=response.sources,
            confidence=response.overall_confidence,
            history=history,
            original_query=query
        )
        response.answer_context = synthesized_context
        response.raw_reasoning = raw_context
        response.structured_data = structured_data
        
        # 5. Persist Assistant Response
        session_manager.add_message(
            session_id=session_id,
            role="assistant",
            content=synthesized_context,
            context=raw_context,  # preserve raw for source panel
            sources=",".join(response.sources),
            trace=response.trace.model_dump_json() if response.trace else None,
            structured_data=json.dumps(structured_data) if structured_data else None
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
                "Which NeonPlay titles had the highest completion rates this month?",
                "What common themes appear in viewer feedback for recent originals?",
                "Which genres are driving the strongest repeat viewing behavior?",
                "How did the latest content releases perform across regions?",
                "Which shows are showing early signs of audience drop-off, and why?"
            ]
