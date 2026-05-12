import logging
import base64
import io
from typing import List, Dict, Any, Optional
from backend.config import Config

try:
    import google.generativeai as genai
except ImportError:
    genai = None

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.api_key = Config.GEMINI_API_KEY
        self.enabled = bool(self.api_key and genai is not None)
        
        if self.enabled:
            try:
                import os
                genai.configure(api_key=self.api_key)
                # Phase 23: Define Global Executive Persona as System Instruction
                system_instruction = (
                    "You are Iris., a Senior Operational Intelligence Assistant at an executive consulting firm. "
                    "Your goal is to provide HIGH-IMPACT, MANAGEMENT-GRADE insights based on Grounded Evidence. "
                    "\n\nSTRICT OPERATIONAL RULES:"
                    "\n1. NO TECHNICAL META-COMMENTARY: NEVER mention 'retrieved records', 'identified entries', 'searching databases', or describe your technical mechanics. Provide insights directly as a senior human analyst would."
                    "\n2. DATA RECONSTRUCTION: You will receive 'Grounded Evidence' which often contains fragmented or flattened table data (e.g. 'region spend cpm APAC $5M $55'). You MUST identify these patterns and reconstruct them into clean, valid Markdown tables."
                    "\n3. STRUCTURE: Use concise executive sections with ## and ### headings. Keep paragraphs short and analytical."
                    "\n4. MANDATORY TABLES: For any regional, platform, campaign, or temporal comparisons, you MUST use Markdown tables. Omit rows where data is missing."
                    "\n5. BOLDING: Use **bold** for key metrics and entity names within narrative text."
                    "\n6. PROFESSIONAL TONE: Be concise, direct, and authoritative. Avoid fluff or introductory filler (e.g. 'Based on the records...')."
                    "\n7. DO NOT LEAK CONTROL TEXT: Never output internal tags or labels such as 'chart only response', 'response_type', 'thinking', or process notes."
                    "\n8. EVIDENCE-GROUNDED ACTIONS ONLY: Do not invent generic management recommendations. If you include an action or implication, it must be explicitly tied to the metrics in the evidence."
                    "\n9. GREETINGS: Only if the user says 'hi' or 'hello', start with 'Hello there, I am Iris., your Operational Intelligence Assistant.' Otherwise, jump straight to the analysis."
                )
                
                # Use gemini-2.5-flash for the best balance of speed, reasoning, and generous limits
                self.model = genai.GenerativeModel(
                    model_name='gemini-2.5-flash',
                    system_instruction=system_instruction
                )
                logger.info(f"[llm_service] Gemini 2.5 Flash initialized. Key detected: {self.api_key[:4]}...{self.api_key[-4:]}")
            except Exception as e:
                logger.error(f"[llm_service] Failed to initialize Gemini: {e}")
                self.enabled = False
        elif genai is None:
            logger.warning("[llm_service] google-generativeai is not installed. Falling back to deterministic synthesis.")
            self.enabled = False
        else:
            import os
            logger.warning("[llm_service] No GEMINI_API_KEY found. os.environ keys: " + str(list(os.environ.keys())))
            self.enabled = False

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

    def analyze_attachment(self, query: str, file_data: str, history: List[Dict[str, Any]] = None) -> Optional[str]:
        """Multimodal analysis of attachments (Images, PDFs, CSVs) using Gemini."""
        if not self.enabled: return None
        try:
            if file_data.startswith('data:'):
                header, b64_data = file_data.split(',', 1)
                mime_type = header.split(':')[1].split(';')[0]
            else:
                b64_data = file_data
                mime_type = 'image/png' # Default fallback
            file_bytes = base64.b64decode(b64_data)
            
            prompt_text = f"Analyze this attachment and answer the user query: {query}. Provide professional, executive-grade insights."
            parts = [prompt_text, {"mime_type": mime_type, "data": file_bytes}]
            response = self.model.generate_content(parts)
            return response.text.strip() if response else None
        except Exception as e:
            logger.error(f"[llm_service] Attachment analysis failed: {e}")
            return None

    def synthesize_narrative(self, query: str, context: str, history: List[Dict[str, Any]] = None) -> Optional[str]:
        """Synthesizes a professional BI narrative from grounded context."""
        if not self.enabled: return None
        history = history or []
        
        chat_history = []
        for msg in history[-5:]: # Maintain conversational context
            role = "user" if msg['role'] == 'user' else "model"
            chat_history.append({"role": role, "parts": [msg['content']]})
        
        # Enhanced Analysis Instructions
        analysis_prompt = (
            f"USER QUERY: {query}\n\n"
            f"GROUNDED EVIDENCE:\n{context}\n\n"
            "INSTRUCTIONS:\n"
            "1. ANSWER-FIRST STRUCTURE: Start every response with a Level 2 Heading (##) that states the core business conclusion or leading performer.\n"
            "2. EXECUTIVE BI STYLE: Sound like a strategy analyst preparing output for leadership. Short paragraphs, strong metric callouts, no filler.\n"
            "3. RECONSTRUCT FRAGMENTS: The evidence contains fragmented data dumps. Identify and transform these into professional Markdown tables (using | and --- syntax).\n"
            "4. TABULAR DATA MANDATE: Any regional, platform, campaign, or time-based metric comparison MUST be presented as a Markdown table. Do not use plain text lists for metrics.\n"
            "4. REGIONAL CLARITY: Always use full regional names (e.g., 'North America' instead of 'NA', 'Asia Pacific' instead of 'APAC' in titles) to avoid ambiguity with data states like 'Not Available'.\n"
            "5. TABLE HYGIENE: Do not use manual dashed lines or extra decorations inside tables. Use only standard Markdown table syntax.\n"
            "6. INTELLIGENT ATTRIBUTION: If specific drivers are missing, infer cautiously from nearby evidence, but do not fabricate unsupported claims.\n"
            "7. DIRECT ANSWER: Answer the query directly and authoritatively. No filler.\n"
            "8. NO META-COMMENTARY: NEVER mention 'retrieved records', system behavior, or technical mechanics.\n"
            "9. NO CONTROL LABELS: Never output internal labels such as 'chart only response', 'response_type', 'thinking', or other prompt artifacts.\n"
            "10. STRATEGIC IMPLICATION: Only include a '### Strategic Implication' section when the evidence clearly supports an action. The action must reference actual metrics in the response.\n"
            "11. SUMMARIZATION BEHAVIOR: If the user asks to summarize, compress the answer materially. Do not repeat the previous response verbatim."
        )

        try:
            chat = self.model.start_chat(history=chat_history)
            response = chat.send_message(analysis_prompt)
            
            # Phase 24: Robust Safety Handling
            if response and hasattr(response, 'text'):
                try:
                    txt = response.text.strip()
                    if txt:
                        logger.info(f"[llm_service] Synthesis successful for query: {query[:50]}...")
                        return txt
                except Exception as e:
                    # Likely a safety filter block
                    logger.warning(f"[llm_service] Response text inaccessible (safety block?): {e}")
            
            logger.warning("[llm_service] Model returned empty or blocked response.")
            return None
        except Exception as e:
            logger.error(f"[llm_service] Synthesis failed: {e}")
            return None

    def extract_structured_data(self, query: str, context: str) -> Optional[Dict[str, Any]]:
        """
        Attempts to extract a visualization-ready chart object from unstructured evidence
        using Gemini's reasoning capabilities.
        """
        if not self.enabled: return None
        
        try:
            prompt = (
                "You are a Data Extraction Engine. Extract ALL visualization-ready datasets from the evidence provided below. "
                "\n\nRULES:"
                "\n1. Identify every independent dataset suitable for a chart (bar, pie, line). Examples: regional performance, platform shares, spend breakdowns, time trends."
                "\n2. DATA ROUTING: Use 'pie' charts for percentage-based breakdowns or shares of a whole. Use 'bar' charts for discrete performance comparisons. Use 'line' charts for ordered trends or time-series patterns."
                "\n3. Return ONLY a JSON object. No markdown, no triple backticks, no extra text."
                "\n4. JSON Schema:"
                "\n   { \"title\": \"The Main Finding\", \"table\": { \"columns\": [\"Dimension\", \"Metric\"], \"rows\": [{ \"Dimension\": \"A\", \"Metric\": \"123\" }] }, \"charts\": [ { \"type\": \"bar|pie|line\", \"title\": \"Metric by Category\", \"data\": [ { \"label\": \"Category\", \"value\": 123.4 } ] } ] }"
                "\n5. IMPORTANT: THE TOP-LEVEL TITLE must be 'Answer-First'. It should summarize the core conclusion or the highest performing metric found in the data. "
                "NEVER use generic titles like 'Analysis', 'Summary', or 'Data Results'. "
                "Good example: 'Serialized Sci-Fi Dominates Q2 Engagement'. Bad example: 'Q2 Performance Summary'."
                "\n6. In the 'value' field, return ONLY a number (float or int). Strip characters like '%', '$', or 'M'."
                "\n7. When metrics exist, prefer returning a chart suite that includes bar, pie, and line variants when the same dataset supports them."
                "\n8. If no clear chart-ready data exists, return an empty object {}."
                f"\n\nUSER QUERY: {query}"
                f"\n\nGROUNDED EVIDENCE:\n{context}"
            )
            
            response = self.model.generate_content(prompt)
            if response and response.text:
                # Clean the response (sometimes AI adds markdown blocks even when told not to)
                clean_json = response.text.strip().replace('```json', '').replace('```', '').strip()
                return json.loads(clean_json)
            return None
        except Exception as e:
            logger.error(f"[llm_service] Structured data extraction failed: {e}")
            return None

# Singleton instance
llm_service = LLMService()
