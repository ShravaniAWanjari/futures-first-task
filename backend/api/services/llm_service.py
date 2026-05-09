import logging
import google.generativeai as genai
from typing import List, Dict, Any, Optional
from backend.config import Config

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.api_key = Config.GEMINI_API_KEY
        self.enabled = bool(self.api_key)
        
        if self.enabled:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                logger.info("[llm_service] Gemini 1.5 Flash initialized successfully.")
            except Exception as e:
                logger.error(f"[llm_service] Failed to initialize Gemini: {e}")
                self.enabled = False
        else:
            logger.warning("[llm_service] No GEMINI_API_KEY found. LLM synthesis will be disabled.")

    def synthesize_narrative(self, query: str, context: str, history: List[Dict[str, Any]] = None) -> Optional[str]:
        """
        Synthesizes a professional BI narrative from grounded context.
        """
        if not self.enabled:
            return None

        history = history or []
        
        # Phase 11: Detect simple informational/definition queries
        is_informational = any(query.lower().startswith(p) for p in ["what is", "who is", "define", "what does", "meaning of"])
        
        # Build prompt
        system_prompt = (
            "You are a Senior Operational Intelligence Analyst. "
            "Your goal is to provide DIRECT, ACCURATE, and CONCISE answers based on Grounded Evidence. "
            "\n\nCRITICAL DIRECTIVES:"
            "\n1. NO CORPORATE FLUFF: Do not use phrases like 'Analysis suggests', 'The data indicates', or 'It is recommended' unless specifically asked for an analysis. Just answer the question."
            "\n2. DIRECT ANSWERS FIRST: If the user asks a simple question (e.g., 'What regions are covered?'), provide a direct list or statement immediately. Do not wrap it in a 'STRATEGIC SUMMARY' if a simple list is sufficient."
            "\n3. ONLY use provided Grounded Evidence for data. If the evidence is empty or missing the specific answer, say so clearly."
            "\n4. DEFINITIONS: For 'What is' queries, provide a one-sentence definition first, then relate it to the evidence."
            "\n5. STYLE: Data-driven and professional. Use bolding for metrics and entities. NO EMOJIS."
            "\n6. FORMATTING: Use markdown headers (##) only for complex, multi-part reports. For simple questions, plain text or bullet points are preferred."
            "\n7. CLEANUP: Correct obvious fragments (e.g. 'YouTub' -> 'YouTube')."
        )

        chat_history = []
        for msg in history[-5:]: # Last 5 messages for context
            role = "user" if msg['role'] == 'user' else "model"
            chat_history.append({"role": role, "parts": [msg['content']]})

        prompt = (
            f"USER QUERY: {query}\n\n"
            f"GROUNDED EVIDENCE:\n{context}\n\n"
            "Analyze the evidence and provide a synthesized narrative response."
        )

        try:
            # Start chat with history
            chat = self.model.start_chat(history=chat_history)
            response = chat.send_message(f"{system_prompt}\n\n{prompt}")
            
            if response and response.text:
                return response.text.strip()
            return None
        except Exception as e:
            logger.error(f"[llm_service] Synthesis failed: {e}")
            return None

# Singleton instance
llm_service = LLMService()
