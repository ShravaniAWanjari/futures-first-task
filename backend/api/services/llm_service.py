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
                # Use the flash-latest model identified in the diagnostic list
                self.model = genai.GenerativeModel('gemini-flash-latest')
                logger.info("[llm_service] Gemini 1.5 Flash initialized successfully.")
            except Exception as e:
                logger.error(f"[llm_service] Failed to initialize Gemini: {e}")
                self.enabled = False
        else:
            logger.warning("[llm_service] No GEMINI_API_KEY found. LLM synthesis will be disabled.")

    def generate_title(self, query: str) -> str:
        """Generates a clean, professional title for the session."""
        if not self.enabled:
            return "New Analysis"
        
        try:
            prompt = (
                f"Generate a professional, concise 3-5 word title for a business intelligence report based on this user query: '{query}'. "
                "The title should be high-level and executive (e.g. 'Regional ROI Analysis' or 'Subscriber Growth Trends'). "
                "Do not use punctuation or quotes. Return ONLY the title string."
            )
            response = self.model.generate_content(prompt)
            return response.text.strip().replace('"', '').replace("'", "")
        except Exception:
            return "Operational Analysis"

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
            "You are a Senior Operational Intelligence Analyst at an executive consulting firm. "
            "Your goal is to provide HIGH-IMPACT, MANAGEMENT-GRADE insights based on Grounded Evidence. "
            "\n\nSTRICT FORMATTING RULES:"
            "\n1. STRUCTURE OVER PARAGRAPHS: NEVER write long paragraphs. Always use a heading (### Heading) followed by short body text or a table. Every response must have clear sections."
            "\n2. MANDATORY TABLES: If you see metrics comparing periods, regions, platforms, or devices, you MUST use markdown tables. Syntax: header row, separator row (|---|---|), then data rows. Do NOT put ** markers in table headers."
            "\n   Example:"
            "\n   | Platform | Spend | CPM |"
            "\n   |---|---|---|"
            "\n   | TikTok | $1.6M | $54.99 |"
            "\n   | YouTube | $740K | $79.45 |"
            "\n3. HEADINGS: Use ### for section titles. Do NOT wrap headings in ** markers. Write them as plain ### Heading Text."
            "\n4. BOLD: Use **bold** only for inline metrics, entity names, and key numbers within body text. Never bold an entire heading."
            "\n5. PROFESSIONAL CALLOUTS: For critical strategic observations, write them as a separate paragraph starting with 'Strategic Implication:' in bold. NEVER use 'SO WHAT?' or '> ' blockquote markers."
            "\n6. DIRECT & ACCURATE: Be concise. No fluff. Just provide the intelligence."
            "\n7. GROUNDING: Every metric must be grounded in the provided evidence. Do not hallucinate numbers."
            "\n8. CLEANUP: Correct obvious fragments (e.g. 'YouTub' -> 'YouTube', 'APAC 8PM' -> 'APAC: 8 PM')."
            "\n9. For simple informational queries (like 'what is LATAM'), provide a direct, concise definition or explanation. Do not over-complicate."
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
