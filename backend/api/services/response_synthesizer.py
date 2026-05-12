"""
Module: response_synthesizer.py
Purpose: Transforms raw orchestration output into management-quality narrative analysis.
Responsibility: bridges retrieval artifacts and executive communication.
"""

import re
import math
import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from backend.api.services.llm_service import llm_service

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Phase 4: Token Safety — Maximum chars per snippet
MAX_SNIPPET_CHARS = 800
MAX_FINDINGS = 5
REDUNDANT_HEADERS = ["prepared by:", "internal only", "draft v", "version:", "maybe final", "neonplay media", "quarterly exec report"]


def _detect_tone(query: str) -> str:
    """Phase 8: Detects desired response tone from query phrasing."""
    q = query.lower()
    if any(kw in q for kw in ["quick", "brief", "concise", "short", "tl;dr", "briefly", "summarize"]):
        return "concise"
    if any(kw in q for kw in ["casual", "simply", "plain english", "easy", "informal"]):
        return "conversational"
    if any(kw in q for kw in ["bullet", "point", "list style"]):
        return "bulleted"
    if any(kw in q for kw in ["executive", "management", "formal", "detailed report", "comprehensive"]):
        return "executive"
    return "standard"


def synthesize_response(answer_context: str, sources: List[str], confidence: float, history: List[Dict[str, Any]] = None, original_query: str = "") -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Takes raw orchestration answer_context and produces a coherent,
    tone-adaptive narrative summary and structured data for rich rendering.
    """
    sections = _split_sections(answer_context)
    history = history or []
    
    # Phase 8: Detect tone
    tone = _detect_tone(original_query)
    
    # 1. Detect if this is an operational domain query
    is_operational = "ingestion_logs" in answer_context or "validation_summaries" in answer_context
    
    # 2. Detect expansion intent
    is_expansion = any(re.search(p, original_query.lower()) for p in [r"provide more", r"what else", r"additional", r"tell me more"])
    is_follow_up = _is_follow_up_prompt(original_query) or is_expansion
    
    last_assistant_msg = ""
    if is_follow_up and history:
        for msg in reversed(history):
            if msg.get('role') == 'assistant':
                last_assistant_msg = msg.get('content', '')
                break

    synthesized_parts = []
    structured_data = _extract_structured_data(answer_context, original_query)

    # Core Content Extraction
    data_found = False
    for section_type, content in sections:
        narrative = None
        if section_type == 'sql':
            narrative = _synthesize_sql_narrative(content, original_query=original_query)
            data_found = True
        elif section_type == 'retrieval':
            narrative = _synthesize_retrieval_narrative(content, is_expansion=is_expansion, tone=tone)
            data_found = True
        elif section_type == 'plain':
            # Small talk and conversational responses pass through directly
            if content.strip():
                narrative = content.strip()
            
        if narrative:
            synthesized_parts.append(narrative)
    
    if not synthesized_parts:
        if is_follow_up:
            return "No additional operational details could be retrieved to expand on the previous answer.", None
        return "The requested information could not be retrieved from current datasets.", None

    narrative_output = "\n\n".join(synthesized_parts)

    # Phase 11: Skip for simple informational "What is" queries
    is_informational = any(original_query.lower().startswith(p) for p in ["what is", "who is", "define", "what does"])
    if tone != "concise" and data_found and not is_informational:
        recommendation = _generate_operational_implication(answer_context, original_query)
        if recommendation:
            synthesized_parts.append(recommendation)
    
    # Phase 14: LLM-Powered Semantic Synthesis (Business Intelligence Narrative)
    if llm_service.enabled:
        llm_narrative = llm_service.synthesize_narrative(
            query=original_query,
            context=answer_context,
            history=history
        )
        if llm_narrative:
            logger.info("[synthesizer] Successfully generated LLM narrative.")
            narrative_output = _format_all_flattened_tables(llm_narrative)
        else:
            logger.warning("[synthesizer] LLM synthesis failed or returned empty. Falling back to deterministic.")
            narrative_output = "\n\n".join(synthesized_parts)
    else:
        narrative_output = "\n\n".join(synthesized_parts)
        
        # Phase 12: Narrative Metric Bolding (Executive Readability) - Only for deterministic
        narrative_output = _format_all_flattened_tables(narrative_output)
        narrative_output = re.sub(r'(\$[\d\.]+M?)', r'**\1**', narrative_output)
        narrative_output = re.sub(r'(\d+(?:\.\d+)?%)', r'**\1**', narrative_output)
        narrative_output = re.sub(r'(\d+(?:\.\d+)?x)', r'**\1**', narrative_output)
    
    # Phase 25: Multi-Pass Data Extraction
    # If no chart was found in the raw context, try extracting from the CLEAN narrative
    if not structured_data or 'chart' not in structured_data:
        logger.info("[synthesizer] No chart found in raw context. Attempting extraction from synthesized narrative.")
        narrative_structured = _extract_structured_data(narrative_output, original_query)
        if narrative_structured and 'chart' in narrative_structured:
            if not structured_data:
                structured_data = narrative_structured
            else:
                structured_data['chart'] = narrative_structured['chart']
                # Sync table if found in narrative but not in raw
                if 'table' in narrative_structured and 'table' not in structured_data:
                    structured_data['table'] = narrative_structured['table']

    # Update structured_data with LLM fallback if still missing
    if llm_service.enabled and (not structured_data or 'chart' not in structured_data):
        chart_intent = any(k in original_query.lower() for k in ["chart", "graph", "plot", "viz", "visualization", "pie", "bar", "line", "summary", "breakdown"])
        if chart_intent or not structured_data:
            logger.info("[synthesizer] Conventional extraction insufficient. Attempting LLM-driven structured extraction.")
            # Use the synthesis narrative for extraction as it's cleaner than raw context
            llm_structured = llm_service.extract_structured_data(original_query, narrative_output)
            if llm_structured and 'chart' in llm_structured:
                if not structured_data:
                    structured_data = llm_structured
                else:
                    structured_data['chart'] = llm_structured['chart']
                
                if 'title' not in structured_data or structured_data['title'] == "Operational Analysis":
                    structured_data['title'] = llm_service.generate_title(original_query)
                structured_data['summary'] = narrative_output[:300] + "..." if len(narrative_output) > 300 else narrative_output

    return narrative_output, structured_data


def _synthesize_sql_narrative(content: str, original_query: str = "") -> Optional[str]:
    """Transforms SQL results into an executive summary."""
    lines = [l.strip() for l in content.split('\n') if l.strip()]
    
    dash_idx = next((i for i, l in enumerate(lines) if re.match(r'^-{3,}', l)), -1)
    header_idx = dash_idx - 1 if dash_idx > 0 else -1
    if header_idx < 0: return None
    
    columns = [c.strip() for c in lines[header_idx].split('|') if c.strip()]
    data_lines = [l for l in lines[dash_idx + 1:] if not l.startswith('...')]
    
    rows = []
    for line in data_lines:
        values = [v.strip() for v in line.split('|')]
        row = {columns[ci]: values[ci] if ci < len(values) else '' for ci in range(len(columns))}
        if any(row.values()): rows.append(row)
    
    if not rows: return None
    
    # PHASE 3: Specialized Operational Summary
    if "ingestion_logs" in content.lower() or "validation_summaries" in content.lower():
        return _synthesize_operational_summary(rows)
    
    metric_cols = [c for c in columns if _is_numeric_col(rows, c)]
    category_cols = [c for c in columns if c not in metric_cols and c.lower() not in ('id', 'pk')]
    
    if metric_cols and category_cols:
        metric, category = metric_cols[0], category_cols[0]
        label, cat_label = _humanize(metric), _humanize(category)
        # Phase 17: Intent-Aware Sorting (Highest vs Lowest)
        is_lowest = any(k in original_query.lower() for k in ["lowest", "least", "bottom", "worst", "min"])
        
        entries = sorted(
            [
                {'cat': r[category], 'val': _parse_num(r[metric])}
                for r in rows
                if _parse_num(r[metric]) is not None and not _is_missing_dimension(r.get(category))
            ],
            key=lambda x: x['val'],
            reverse=not is_lowest # Sort ascending if 'lowest' is requested
        )
        
        if entries:
            top = entries[0]
            total = sum(e['val'] for e in entries)
            
            # Phase 16: Direct Answer Override (Conciseness)
            if any(k in original_query.lower() for k in ["what regions", "list regions", "which regions", "what platforms", "list platforms"]):
                cats = [f"**{e['cat']}**" for e in entries]
                return f"The current dataset covers the following {cat_label.lower()}s: {', '.join(cats)}."

            summary = f"Performance data indicates that **{top['cat']}** leads in {label} at {_fmt(top['val'])}, representing {_pct(top['val'], total)} of total {label} ({_fmt(total)})."
            
    # Final Fallback: provide a high-level count if data exists but didn't match structured patterns
    # Final Fallback: provide a professional observation
    return f"Operational data for **{_humanize(str(list(rows[0].values())[0]))}** has been processed. The results highlight key metrics across the requested dimensions, including {', '.join([_humanize(c) for c in metric_cols[:2]])}."


def _synthesize_operational_summary(rows: List[Dict[str, Any]]) -> str:
    """Specialized synthesis for operational ingestion logs and validation summaries."""
    # Aggregates
    total_warnings = sum(_parse_num(r.get('occurrence', r.get('rejected_count', 0))) for r in rows if r.get('log_level') == 'WARNING' or 'rejected_count' in r)
    total_errors = sum(_parse_num(r.get('occurrence', 0)) for r in rows if r.get('log_level') == 'ERROR')
    
    # Categories / Systems
    table_counts = {}
    for r in rows:
        t = r.get('table_name', r.get('validation_rule', 'Unknown System'))
        table_counts[t] = table_counts.get(t, 0) + _parse_num(r.get('occurrence', r.get('rejected_count', 0)))
    
    sorted_tables = sorted(table_counts.items(), key=lambda x: x[1], reverse=True)
    top_systems = [f"**{_humanize(t)}** ({_fmt(c)} events)" for t, c in sorted_tables[:3]]
    
    # Issue Types
    issue_counts = {}
    for r in rows:
        i = r.get('action_taken', r.get('log_level', 'General Anomaly'))
        issue_counts[i] = issue_counts.get(i, 0) + _parse_num(r.get('occurrence', r.get('rejected_count', 0)))
    
    sorted_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
    top_issues = [f"**{_humanize(i)}**" for i, c in sorted_issues[:3]]
    
    # Implications
    implication = "Immediate cross-reference of ingestion manifests is recommended to resolve tracking gaps and prevent downstream reporting inaccuracies."
    if total_errors > total_warnings:
        implication = "Critical pipeline failures detected. Priority should be given to resolving rejected records to ensure data completeness for regional stakeholders."
    
    # Construct Narrative
    parts = [
        "### Operational Analysis Summary",
        f"**Key Findings**: Pipeline diagnostics identified a total of **{_fmt(total_warnings + total_errors)}** operational events requiring attention, including **{_fmt(total_warnings)} warnings**.",
        f"**Dominant Issue Types**: High concentration of {', '.join(top_issues)} detected.",
        f"**Affected Systems**: Primary impact observed in {', '.join(top_systems)}.",
        f"**Operational Implications**: {implication}"
    ]
    
    return "\n\n".join(parts)


def _synthesize_retrieval_narrative(content: str, is_expansion: bool = False, tone: str = "standard") -> Optional[str]:
    """Transforms raw retrieval chunks into structured, management-grade narrative analysis."""
    results = re.split(r'\[Document Result \d+\]', content)
    results = [r.strip() for r in results if r.strip()]
    
    findings = []
    for res in results:
        # Extract metadata and content
        source_match = re.search(r'Source File:\s*(.*?)\s*\(', res)
        snippet_match = re.search(r'Snippet:(.*)', res, re.DOTALL)
        
        if source_match and snippet_match:
            source = source_match.group(1).strip()
            snippet = snippet_match.group(1).strip()
            
            # Phase 23: Metadata Noise Reduction
            snippet_lower = snippet.lower()
            for header in REDUNDANT_HEADERS:
                if header in snippet_lower[:100]:
                    # Remove the header line
                    lines = snippet.split('\n')
                    snippet = '\n'.join([l for l in lines if header not in l.lower()]).strip()
            
            if not snippet: continue

            # Word-Aware Truncation
            if len(snippet) > MAX_SNIPPET_CHARS:
                # Truncate and back up to last space/sentence
                snippet = snippet[:MAX_SNIPPET_CHARS]
                last_period = snippet.rfind('.')
                if last_period > 300:
                    snippet = snippet[:last_period + 1]
                else:
                    last_space = snippet.rfind(' ')
                    if last_space > 300:
                        snippet = snippet[:last_space] + "..."

            # 1. Technical Artifact Removal
            snippet = re.sub(r'Trace ID:\s*[a-f0-9]{8,}', '', snippet, flags=re.IGNORECASE)
            snippet = re.sub(r'\b[a-f0-9]{32}\b', '', snippet, flags=re.IGNORECASE)
            snippet = snippet.replace('\u200b', '')
            snippet = re.sub(r'#+\s*', '', snippet)
            
            # 2. Fix fragments at start (Only if it's truly a fragment, not a capitalized entity like LATAM)
            snippet = re.sub(r'^[a-z]{1,5}\b\s*', '', snippet)
            
            # 3. Bullet Point Normalization
            # Only match single asterisks used as list delimiters (not ** bold markers)
            snippet = re.sub(r'(?<!\*)\*(?!\*)', '\n- ', snippet)
            snippet = snippet.replace('●', '\n- ').replace('•', '\n- ')
            
            # 4. Header Identification (Formal BI Style)
            snippet = re.sub(r'(\b[A-Z][A-Z\s]{3,}:)', r'\n\n**\1**\n', snippet)
            snippet = re.sub(r'(\b[A-Z][a-z/ ]+[:])', r'\n\n**\1**\n', snippet)
            
            # 5. Sentence cleanup and Word Deduplication
            snippet = re.sub(r'\.([A-Z])', r'. \1', snippet)
            snippet = re.sub(r'\b(\w+)\s+\1\b', r'\1', snippet, flags=re.IGNORECASE)
            
            # Phase 12: Bolden metrics in snippets for better visibility
            snippet = re.sub(r'(\$[\d\.]+M?)', r'**\1**', snippet)
            snippet = re.sub(r'(\d+(?:\.\d+)?%)', r'**\1**', snippet)
            snippet = re.sub(r'(\d+(?:\.\d+)?x)', r'**\1**', snippet)
            
            if len(snippet) > 40 and not _is_fragment(snippet):
                findings.append({
                    "source": source.replace('_', ' ').title(),
                    "finding": snippet.strip()
                })
    
    if not findings: return None
    
    # Deduplication
    unique_findings = []
    seen_content = set()
    for f in findings:
        norm = re.sub(r'\s+', ' ', f['finding']).strip().lower()
        if norm[:100] not in seen_content:
            unique_findings.append(f)
            seen_content.add(norm[:100])
            
    if not unique_findings: return None
    
    # Phase 4: Limit total findings
    unique_findings = unique_findings[:MAX_FINDINGS]
    
    # Construct Narrative based on tone
    idx_start = 2 if is_expansion and len(unique_findings) > 2 else 0
    
    parts = []
    for i, f in enumerate(unique_findings[idx_start:], 1):
        if tone == "concise":
            parts.append(f"- {f['finding'][:200]}")
        else:
            if i == 1:
                parts.append(f"## STRATEGIC INTELLIGENCE SUMMARY\n\n---\n\n{f['finding']}")
            else:
                source_label = f["source"].split(".")[0]
                parts.append(f"## OPERATIONAL CONTEXT: {source_label}\n\n---\n\n{f['finding']}")
            
    return "\n\n".join(parts)


def _generate_operational_implication(context: str, query: str) -> Optional[str]:
    """Adds a layer of synthesized management implication based on the context."""
    ctx_lower = context.lower()
    q_lower = query.lower()
    
    # Localization / Quality theme
    if any(k in ctx_lower for k in ['localization', 'subtitle', 'quality', 'translation']):
        return "## MANAGEMENT RECOMMENDATION\n\n---\n\n**STRATEGIC RISK MITIGATION**: Current operational data indicates a need for enhanced localization QA protocols. It is recommended to implement a pre-release audit cycle to ensure regional content parity and viewer satisfaction before the next major roadmap milestone."
        
    # Spend / Efficiency theme
    if any(k in ctx_lower for k in ['spend', 'efficiency', 'roi', 'cost']):
        return "## MANAGEMENT RECOMMENDATION\n\n---\n\n**CAPITAL OPTIMIZATION**: To maximize acquisition efficiency, leadership should consider re-allocating under-performing display budgets toward high-ROI creator partnerships identified in the APAC and North American performance clusters."
        
    # Data / Warning theme
    if any(k in ctx_lower for k in ['warning', 'inconsistency', 'data quality', 'error']):
        return "## MANAGEMENT RECOMMENDATION\n\n---\n\n**OPERATIONAL INTEGRITY**: Addressing current ingestion anomalies is critical for downstream reporting accuracy. A technical deep-dive into the rejected record sets is advised to stabilize the data pipeline for Q3 reporting."

    # Growth / Performance theme
    if any(k in ctx_lower for k in ['growth', 'subscriber', 'reach', 'performance']):
        return "## MANAGEMENT RECOMMENDATION\n\n---\n\n**GROWTH SUSTAINABILITY**: Sustaining the current subscriber trajectory requires continued investment in the science-fiction and mobile-first content pillars that are currently driving outsized regional engagement."

    return None


def _is_follow_up_prompt(query: str) -> bool:
    q = query.lower().strip()
    return any(re.match(p, q) for p in [
        r"^explain (?:further|more|that|this)$", r"^elaborate\b", r"^why\??$", 
        r"^how so\??$", r"^expand on (?:this|that)$", r"^can you explain more$"
    ])


def _split_sections(context: str) -> List[tuple]:
    sections = []
    parts = re.split(r'(===\s*.*?\s*===)', context)
    current_type = 'plain'
    for part in parts:
        part = part.strip()
        if not part: continue
        header_match = re.match(r'===\s*(.*?)\s*===', part)
        if header_match:
            h = header_match.group(1).upper()
            if 'SQL' in h: current_type = 'sql'
            elif 'SEMANTIC' in h or 'DOCUMENT' in h: current_type = 'retrieval'
            else: current_type = 'plain'
        else:
            sections.append((current_type, part))
            current_type = 'plain'
    return sections


def _is_numeric_col(rows: list, col: str) -> bool:
    if not rows or not col: return False
    # Exclude ID-like columns
    col_lower = col.lower()
    if any(k in col_lower for k in ['id', 'pk', 'uuid', 'session', 'timestamp', 'index']):
        return False
    val = rows[0].get(col)
    parsed = _parse_num(val)
    if parsed is None: return False
    # Heuristic: if it's a very large integer (> 100M) without decimals, it's likely an ID or timestamp
    if isinstance(parsed, float) and parsed > 100_000_000 and parsed == int(parsed):
        return False
    return True

def _parse_num(val: Any) -> Optional[float]:
    if val is None: return None
    if isinstance(val, (int, float)): return float(val)
    s = str(val).strip().replace(',', '').replace('$', '').replace('%', '')
    if not s: return None
    try:
        # Handle suffixes
        if s.upper().endswith('B'): return float(s[:-1]) * 1_000_000_000.0
        if s.upper().endswith('M'): return float(s[:-1]) * 1_000_000.0
        if s.upper().endswith('K'): return float(s[:-1]) * 1_000.0
        return float(s)
    except: return None

def _humanize(col: str) -> str:
    acronyms = {'usd', 'roi', 'apac', 'emea', 'latam', 'kpi'}
    words = col.replace('_', ' ').split()
    return ' '.join(w.upper() if w.lower() in acronyms else w.capitalize() for w in words)

def _fmt(n: float) -> str:
    n = float(n)
    if abs(n) >= 1_000_000: return f"{n / 1_000_000:.1f}M"
    if abs(n) >= 1_000: return f"{n / 1_000:.1f}K"
    return f"{n:.1f}"

def _pct(part: float, total: float) -> str:
    return f"{(part / total) * 100:.0f}%" if total > 0 else "0%"

def _is_fragment(text: str) -> bool:
    return len(text.split()) < 4 or text.lower() in ('controls', 'overview', 'summary')


def _is_missing_dimension(value: Any) -> bool:
    if value is None:
        return True
    return str(value).strip().lower() in ("", "none", "null", "n/a", "undefined")


def generate_session_title(query: str) -> str:
    """
    Generates a concise, management-oriented session title from a user query.
    Uses AI-powered generation if available, otherwise falls back to deterministic patterns.
    """
    if llm_service.enabled:
        ai_title = llm_service.generate_title(query)
        if ai_title and ai_title != "Operational Analysis":
            return ai_title

    query_clean = query.strip().rstrip('?').rstrip('.').strip()
    
    # Pattern matching for common query structures
    patterns = [
        # "What regions/platforms" → "X Coverage"
        (r"(?i)^what\s+regions?\b", "Regional Coverage"),
        (r"(?i)^what\s+platforms?\b", "Platform Coverage"),
        (r"(?i)^what\s+channels?\b", "Channel Coverage"),
        
        # "What is/was the X" → "X Overview"
        (r"(?i)^what\s+(?:is|was|are|were)\s+the\s+(.+?)(?:\s+(?:in|for|during|across)\s+(.+))?$", _what_title),
        (r"(?i)^what\s+(.+)", lambda m: f"{_extract_subject(m.group(1))} Overview"),
        
        # "How does/did X" → "X Performance Review"
        (r"(?i)^how\s+(?:does|did|do)\s+(?:the\s+)?(.+?)(?:\s+(?:compare|correlate|perform))", lambda m: f"{_extract_subject(m.group(1))} Performance Review"),
        (r"(?i)^how\s+(.+)", lambda m: f"{_extract_subject(m.group(1))} Assessment"),
        
        # "Compare X" → "X Comparison"
        (r"(?i)^compare\s+(.+)", lambda m: f"{_extract_subject(m.group(1))} Comparison"),
        
        # "Summarize X" → "X Summary"
        (r"(?i)^summarize\s+(?:the\s+)?(.+)", lambda m: f"{_extract_subject(m.group(1))} Summary"),
        
        # "List X" → "X Overview"
        (r"(?i)^list\s+(?:the\s+)?(.+)", lambda m: f"{_extract_subject(m.group(1))} Overview"),
        
        # "Show/Get X" → "X Report"
        (r"(?i)^(?:show|get|find|retrieve)\s+(?:me\s+)?(?:the\s+)?(.+)", lambda m: f"{_extract_subject(m.group(1))} Report"),
        
        # "Which X" → "X Analysis"
        (r"(?i)^which\s+(.+)", lambda m: f"{_extract_subject(m.group(1))} Analysis"),
    ]
    
    for pattern, handler in patterns:
        match = re.match(pattern, query_clean)
        if match:
            title = handler(match) if callable(handler) else handler
            return _clean_title(title)
    
    # Fallback: extract key terms
    return _clean_title(_fallback_title(query_clean))


def _fallback_title(query: str) -> str:
    """Generates a title from keyword extraction when no pattern matches."""
    key_terms = []
    
    # Extract significant words (skip very short/common ones)
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                  'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                  'should', 'may', 'might', 'shall', 'can', 'and', 'but', 'or', 'if',
                  'of', 'in', 'to', 'for', 'with', 'on', 'at', 'from', 'by', 'about',
                  'that', 'this', 'it', 'they', 'we', 'you', 'me', 'my', 'our', 'your',
                  'there', 'so', 'many', 'much', 'also', 'very', 'just', 'how', 'what',
                  'why', 'when', 'where', 'which', 'who', 'whom', 'its', 'their', 'any'}
    
    for word in query.split():
        cleaned = re.sub(r'[^\w]', '', word)
        if cleaned.lower() not in stop_words and len(cleaned) > 2:
            key_terms.append(cleaned)
    
    if len(key_terms) >= 2:
        return _titleize(' '.join(key_terms[:4])) + ' Review'
    elif key_terms:
        return _titleize(key_terms[0]) + ' Analysis'
    
    return 'Operational Query'

def _what_title(match) -> str:
    subject = match.group(1)
    context = match.group(2) if match.lastindex >= 2 and match.group(2) else None
    subject_clean = _extract_subject(subject)
    if context: return f"{_titleize(context.strip())} {subject_clean} Review"
    return f"{subject_clean} Review"

def _extract_subject(text: str) -> str:
    stop_prefixes = [
        'our', 'the', 'their', 'its', 'my', 'your', 'a', 'an', 'some', 'any',
        'is', 'was', 'are', 'were', 'do', 'does', 'did', 'about', 'of'
    ]
    words = text.strip().split()
    while words and words[0].lower() in stop_prefixes: words.pop(0)
    return _titleize(' '.join(words[:5]))

def _titleize(text: str) -> str:
    acronyms = {'apac', 'emea', 'latam', 'roi', 'q1', 'q2', 'q3', 'q4', 'sql', 'kpi', 'fy'}
    words = text.split()
    result = []
    for w in words:
        if w.lower() in acronyms: result.append(w.upper())
        elif len(w) <= 2 and w.lower() in ('in', 'of', 'to', 'on', 'by', 'at', 'or', 'an', 'a'): result.append(w.lower())
        else: result.append(w.capitalize())
    return ' '.join(result)

def _clean_title(title: str) -> str:
    """Post-processes title for length and clarity."""
    t = title.strip()
    # Remove trailing 'Analysis Analysis' or similar
    t = re.sub(r'( Analysis| Review| Assessment| Investigation)\1+', r'\1', t)
    # Cap length
    if len(t) > 45:
        t = t[:42] + "..."
    return t

def _enhance_title_with_result(title: str, chart_data: Dict[str, Any]) -> str:
    """Refines a generic title (e.g. 'Region Analysis') with the actual winner (e.g. 'APAC Analysis')."""
    labels = chart_data.get('labels', [])
    if not labels: return title
    top_val = str(labels[0])
    
    # Common category names to replace at the start of the title
    categories = ['Region', 'Platform', 'Channel', 'Category', 'System', 'Market', 'Country', 'Month', 'Quarter', 'Campaign']
    
    for cat in categories:
        # Match case-insensitively but preserve structure
        if title.lower().startswith(cat.lower()):
            # Replace the category name with the top value
            # e.g. "Region Had The Highest Spend" -> "APAC Had The Highest Spend"
            pattern = re.compile(re.escape(cat), re.IGNORECASE)
            new_title = pattern.sub(top_val, title, count=1)
            return new_title
            
    # Fallback: if it's an analysis title, prepend the winner
    if any(k in title for k in ["Analysis", "Review", "Summary", "Report"]):
        # Avoid prepending if it's already there
        if top_val.lower() not in title.lower():
            return f"{top_val}: {title}"
            
    return title

def _extract_structured_data(answer_context: str, query: str) -> Optional[Dict[str, Any]]:
    """Analytical Presentation Pass: Extracts structured data for tables and charts."""
    sections = _split_sections(answer_context)
    logger.info(f"[synthesizer] Extracting structured data from {len(sections)} sections")
    
    # Priority: SQL results, then search for markdown tables in any section
    sql_content = None
    table_content = None
    
    for s_type, content in sections:
        if s_type == 'sql':
            sql_content = content
            logger.info("[synthesizer] Found SQL content for extraction")
            break
        # Look for markdown table pattern
        if '|' in content and '---' in content:
            table_content = content
            logger.info("[synthesizer] Found Markdown table content for extraction")
        # Look for flattened table patterns if explicit table/comparison/growth request
        elif any(k in query.lower() for k in ['table', 'comparison', 'summary', 'list', 'breakdown', 'roi', 'growth', 'performance', 'metric']):
            flattened = _extract_flattened_table(content)
            if flattened:
                table_content = flattened
                logger.info("[synthesizer] Found Flattened table content for extraction")
            
    content_to_parse = sql_content or table_content
    if not content_to_parse:
        logger.info("[synthesizer] No table/SQL content found for extraction")
        return None
        
    lines = [l.strip() for l in content_to_parse.split('\n') if l.strip()]
    
    # Find header and dash separator
    dash_idx = -1
    for i, line in enumerate(lines):
        if re.match(r'^[|\s-]{3,}$', line) or (line.startswith('|') and '---' in line) or (re.match(r'^-{3,}$', line)):
            dash_idx = i
            break
            
    if dash_idx <= 0: 
        logger.info("[synthesizer] Could not find table dash separator")
        return None
    
    def _clean_pipe_split(line: str) -> List[str]:
        parts = line.split('|')
        if parts and not parts[0].strip(): parts = parts[1:]
        if parts and not parts[-1].strip(): parts = parts[:-1]
        return [p.strip() for p in parts]

    header_line = lines[dash_idx - 1]
    columns = _clean_pipe_split(header_line)
    # Ensure no empty string columns
    columns = [c if c else f"Column_{i}" for i, c in enumerate(columns)]
    
    data_lines = [l for l in lines[dash_idx + 1:] if not l.startswith('...')]
    
    logger.info(f"[synthesizer] Parsed {len(columns)} columns and {len(data_lines)} potential rows")
    
    rows = []
    for line in data_lines:
        values = _clean_pipe_split(line)
        if len(values) > 0:
            row = {columns[ci]: values[ci] if ci < len(values) else '' for ci in range(len(columns))}
            label_cols = [c for c in columns if c.lower() in ('region', 'platform', 'category', 'channel', 'metric', 'dimension')]
            if label_cols and _is_missing_dimension(row.get(label_cols[0])):
                continue
            
            # Skip if all non-label columns are empty (prevents empty rows in cards/tables)
            non_label_values = [v for k, v in row.items() if k not in label_cols and k.lower() not in ('metric', 'category', 'label', 'column_0')]
            if len(non_label_values) > 0 and not any(v.strip() for v in non_label_values):
                continue
                
            rows.append(row)
            
    if not rows: return None
    
    # 1. Determine Response Type
    res_type = "operational_analysis"
    q_lower = query.lower()
    if any(k in q_lower for k in ["compare", "vs", "difference", "growth", "change"]): res_type = "metric_comparison"
    elif any(k in q_lower for k in ["trend", "over time", "month", "quarter"]): res_type = "trend_analysis"
    elif any(k in q_lower for k in ["breakdown", "contribution", "ratio"]): res_type = "breakdown_analysis"
    elif len(rows) > 5: res_type = "table_response"
    
    # 2. Build Structured Object
    structured = {
        "response_type": res_type,
        "title": generate_session_title(query),
        "table": {
            "columns": columns,
            "rows": rows[:20] 
        }
    }
    
    # Check if narrative already contains a table (to avoid primary table redundancy)
    if "|---" in answer_context:
        # If narrative has a table, and we are not in 'table_response' mode, 
        # we might want to suppress the primary table to avoid double-rendering.
        # But we'll keep it for now and let the chart handle the visual part.
        pass
    
    # 3. Chart Detection
    metric_cols = [c for c in columns if _is_numeric_col(rows, c)]
    category_cols = [c for c in columns if c not in metric_cols and c.lower() not in ('id', 'pk', 'uuid')]
    
    if metric_cols and category_cols:
        # Smart Category Selection
        best_category = category_cols[0]
        
        # Smart Metric Selection: Prefer 'Current' or 'Change' or 'ROI' for charts
        best_metric = metric_cols[0]
        for col in metric_cols:
            if any(k in col.lower() for k in ['current', 'change', 'roi', 'growth', 'spend']):
                best_metric = col
                break
        
        metric = best_metric
        
        max_diversity = 0
        for col in category_cols:
            unique_vals = len(set(str(r.get(col, '')) for r in rows))
            col_lower = col.lower()
            
            # Bonus for relevant keywords
            diversity_score = unique_vals
            if any(k in col_lower for k in ['name', 'table', 'region', 'platform', 'type', 'category']):
                diversity_score += 10
            
            # Penalty for constants
            if unique_vals <= 1 and len(rows) > 1:
                diversity_score = -1
                
            if diversity_score > max_diversity:
                max_diversity = diversity_score
                best_category = col
        
        category = best_category
        
        # Filter out None/empty labels and outliers
        chart_data = []
        for r in rows[:15]:
            label_val = str(r.get(category, ''))
            if label_val.lower() in ('none', 'null', '', 'undefined'):
                continue
            val = _parse_num(r.get(metric))
            if val is not None:
                chart_data.append((label_val, val))
        
        if not chart_data: return structured

        labels = [d[0] for d in chart_data[:10]]
        values = [d[1] for d in chart_data[:10]]
        
        chart_type = "bar"
        if res_type == "trend_analysis": chart_type = "line"
        elif res_type == "breakdown_analysis": chart_type = "pie"
        
        # 4. Multi-Scale Charting (Phase 22: High-Resolution Visualization)
        # If the range of values is too high, split into multiple charts
        non_zero_vals = [v for l, v in chart_data if v > 0]
        if non_zero_vals:
            max_v = max(non_zero_vals)
            min_v = min(non_zero_vals)
            
            # If scale difference is > 100x, split them
            if max_v / min_v > 100:
                logger.info(f"[synthesizer] Scale imbalance detected ({max_v} vs {min_v}). Splitting charts.")
                
                # Group into Key Metrics vs Operational Ratios buckets
                buckets = {}
                for l, v in chart_data:
                    mag = 0
                    if v > 0:
                        mag = int(math.log10(v))
                    
                    # Group into categories: Volume Metrics (e.g. Millions) vs Rates (e.g. Churn, %)
                    bucket_key = "Key Performance Metrics" if mag >= 4 else "Operational Rates & Ratios"
                    if bucket_key not in buckets: buckets[bucket_key] = []
                    buckets[bucket_key].append({"label": l, "value": v})
                
                charts = []
                for b_name, b_data in buckets.items():
                    if not b_data: continue
                    charts.append({
                        "type": chart_type, # Preserve original intent (Bar/Line/Pie)
                        "title": f"{b_name}: {_humanize(metric)} Analysis",
                        "data": b_data
                    })
                structured["charts"] = charts
            else:
                # Standard single chart
                structured["chart"] = {
                    "type": chart_type,
                    "title": f"{_humanize(metric)} by {_humanize(category)}",
                    "data": [{"label": labels[i], "value": values[i]} for i in range(len(labels))]
                }
        
        # If we have charts, and it's a metric comparison, we can skip the primary table 
        if res_type == "metric_comparison" and len(rows) <= 5:
            structured["response_type"] = "chart_only_response"
            
        # Add KPI card if singular metric
        if len(rows) == 1:
            structured["kpi"] = {
                "label": _humanize(metric),
                "value": _fmt(values[0]),
                "context": f"Total for {rows[0][category]}"
            }
            
    return structured

def _extract_flattened_table(text: str) -> Optional[str]:
    """Tries to reconstruct a markdown table from flattened text strings."""
    # Pattern 0: Specific QoQ Multi-Metric Block (Metric Val1 Val2 [Change])
    # Matches: "Avg Weekly Watch Hours 4.8 hrs 5.7 hrs" or "Total Subscribers 41.2M 45.8M +11.1%"
    qoq_pattern = r'([A-Z][A-Za-z\s]{3,45}?(?=\s+\d))\s+([\d\.]+(?:M|hrs|%|min)?)\s+([\d\.]+(?:M|hrs|%|min)?)(?:\s+([\+\-][\d\.]+(?:%|M)?))?'
    qoq_items = re.findall(qoq_pattern, text)
    
    if len(qoq_items) >= 2:
        # Check if we have change values
        has_change = any(m[3] for m in qoq_items)
        header = "| Metric | Q1 FY2026 | Q2 FY2026 |" + (" Change |" if has_change else "")
        sep = "|---|---|---|" + ("---|" if has_change else "")
        rows = []
        for m in qoq_items:
            row = f"| {m[0].strip()} | {m[1]} | {m[2]} |"
            if has_change:
                row += f" **{m[3] if m[3] else 'N/A'}** |"
            rows.append(row)
        return f"{header}\n{sep}\n" + "\n".join(rows)

    # Pattern 0.1: Regional Activity Windows
    # Matches: "APAC 8 PM – 1 AM North America 7 PM – 11 PM"
    window_pattern = r'([A-Z][A-Za-z\s]{1,20})\s+(\d+\s*[AP]M\s*–\s*\d+\s*[AP]M)'
    window_items = re.findall(window_pattern, text)
    if len(window_items) >= 2:
        header = "| Region | Peak Viewing Window |\n|---|---|\n"
        rows = [f"| {m[0].strip()} | {m[1]} |" for m in window_items]
        return header + "\n".join(rows)

    lines = text.split('\n')
    for line in lines:
        # Pattern 1: Multi-column financial matches (Region Spend ROI Conv)
        financial_matches = re.findall(r'([A-Z][a-z\s]+)\s+(\$[\d\.]+M?)\s+([\d\.]+x)\s+([\d\.]+%?)', line)
        if len(financial_matches) >= 2:
            header = "| Region | Marketing Spend | ROI | Conversion |\n|---|---|---|---|\n"
            rows = []
            for m in financial_matches:
                rows.append(f"| {m[0].strip()} | **{m[1]}** | **{m[2]}** | **{m[3]}** |")
            return header + "\n".join(rows)

        # Pattern 2: QoQ Metric matches (Metric Q1 Q2 Change) - Improved
        qoq_matches = re.findall(r'([A-Z][A-Za-z\s]{5,})\s+([\d\.]+(?:M|hrs|%)?)\s+([\d\.]+(?:M|hrs|%)?)\s+([\+\-][\d\.]+(?:%|M)?)', line)
        if len(qoq_matches) >= 2:
            header = "| Performance Metric | Q1 FY2026 | Q2 FY2026 | QoQ Change |\n|---|---|---|---|\n"
            rows = []
            for m in qoq_matches:
                rows.append(f"| {m[0].strip()} | {m[1]} | {m[2]} | **{m[3]}** |")
            return header + "\n".join(rows)

        # Pattern 3: Basic Label-Value pairs (Metric Value)
        matches = re.findall(r'([A-Za-z\s]{3,})\s+([\d\.]+[%xMh]?)\s+', line + " ")
        if len(matches) >= 3:
            header = "| Metric | Current Value |\n|---|---|\n"
            rows = []
            for m in matches:
                label = m[0].strip()
                val = m[1].strip()
                rows.append(f"| {label} | **{val}** |")
            return header + "\n".join(rows)

    return None

def _format_all_flattened_tables(text: str) -> str:
    """Detects and replaces dense metric strings with markdown tables in the final text."""
    # 1. QoQ Metric Replacement (Metric Val1 Val2 [Change])
    # Matches: "Avg Weekly Watch Hours 4.8 hrs 5.7 hrs"
    qoq_pattern = r'([A-Z][A-Za-z\s]{3,45}?(?=\s+\d))\s+([\d\.]+(?:M|hrs|%|min)?)\s+([\d\.]+(?:M|hrs|%|min)?)(?:\s+([\+\-][\d\.]+(?:%|M)?))?'
    qoq_matches = re.findall(qoq_pattern, text)
    
    if len(qoq_matches) >= 2:
        has_change = any(m[3] for m in qoq_matches)
        header = "| Metric | Q1 FY2026 | Q2 FY2026 |" + (" Change |" if has_change else "")
        sep = "|---|---|---|" + ("---|" if has_change else "")
        table_rows = []
        for m in qoq_matches:
            row = f"| {m[0].strip()} | {m[1]} | {m[2]} |"
            if has_change:
                row += f" **{m[3] if m[3] else 'N/A'}** |"
            table_rows.append(row)
        
        table_md = f"\n{header}\n{sep}\n" + "\n".join(table_rows) + "\n"
        
        # Identify the full block of text to replace
        try:
            start_idx = text.find(qoq_matches[0][0])
            last_item = qoq_matches[-1]
            # Construct a search string that represents the end of the block
            search_str = f"{last_item[2]}"
            if last_item[3]: search_str += f" {last_item[3]}"
            end_idx = text.find(search_str, start_idx) + len(search_str)
            
            if start_idx != -1 and end_idx != -1:
                text = text[:start_idx] + table_md + text[end_idx:]
        except Exception:
            pass

    # 2. Regional Activity Windows Replacement
    # Matches: "APAC 8 PM – 1 AM" or "LATAM 8PM - midnight"
    window_pattern = r'([A-Z][A-Za-z\s]{1,20})\s+(\d+\s*[AP]M\s*[–-]\s*(?:\d+\s*[AP]M|midnight))'
    window_matches = re.findall(window_pattern, text)
    if len(window_matches) >= 2:
        header = "| Region | Peak Viewing Window |\n|---|---|\n"
        table_rows = [f"| {m[0].strip()} | {m[1]} |" for m in window_matches]
        table_md = f"\n{header}" + "\n".join(table_rows) + "\n"
        
        try:
            start_idx = text.find(window_matches[0][0])
            last_item = window_matches[-1]
            search_str = f"{last_item[1]}"
            end_idx = text.find(search_str, start_idx) + len(search_str)
            
            if start_idx != -1 and end_idx != -1:
                text = text[:start_idx] + table_md + text[end_idx:]
        except Exception:
            pass

    # 5. Generic Metric List Replacement
    # Matches: "- APAC: 84%" or "- North America: 73%"
    list_pattern = r'^[ \t]*[-*•]\s*([A-Z][A-Za-z\s]+):\s*(\d+(?:\.\d+)?(?:%|M|hrs|min)?)(?=\s|$)'
    list_matches = re.findall(list_pattern, text, re.MULTILINE)
    if len(list_matches) >= 3:
        header = "| Category | Metric Value |\n|---|---|\n"
        table_rows = [f"| {m[0].strip()} | **{m[1]}** |" for m in list_matches]
        table_md = f"\n{header}" + "\n".join(table_rows) + "\n"
        
        # Determine the range of text to replace
        lines = text.split('\n')
        new_lines = []
        in_list = False
        list_added = False
        
        for line in lines:
            if re.match(list_pattern, line):
                if not in_list:
                    in_list = True
                continue
            else:
                if in_list and not list_added:
                    new_lines.append(table_md)
                    list_added = True
                    in_list = False
                new_lines.append(line)
        
        if in_list and not list_added:
            new_lines.append(table_md)
            
        text = '\n'.join(new_lines)

    # 6. Dense Line Metrics (Multiple Label Value pairs on one line)
    # Matches: "Mobile 73% Smart TV 17% Desktop 7% Tablet 3%"
    dense_pattern = r'([A-Z][A-Za-z\s]{2,20})\s+(\d+(?:\.\d+)?(?:%|M|hrs|min)?)(?=\s|$)'
    dense_matches = re.findall(dense_pattern, text)
    if len(dense_matches) >= 3 and "| Category |" not in text:
        header = "| Segment | Contribution |\n|---|---|\n"
        table_rows = [f"| {m[0].strip()} | **{m[1]}** |" for m in dense_matches]
        table_md = f"\n{header}" + "\n".join(table_rows) + "\n"
        
        # Try to replace the line that contains these matches
        first_match = dense_matches[0][0]
        last_match = dense_matches[-1][1]
        
        start_idx = text.find(first_match)
        end_idx = text.find(last_match, start_idx) + len(last_match)
        
        if start_idx != -1 and end_idx != -1:
            # Check if we are already in a table
            if text[max(0, start_idx-5):start_idx].count('|') < 2:
                text = text[:start_idx] + table_md + text[end_idx:]

    # 7. Roadmap / Planned Release Reconstruction
    # Handles: "planned releases title genre target region expected release Galaxy Burn: Frontier Sci-Fi APAC July..."
    if "planned releases" in text.lower() and "| Title |" not in text:
        roadmap_pattern = r'([A-Z][A-Za-z\d\s:]{3,30})\s+([A-Z][a-z\d\-]+)\s+([A-Z]{2,10})\s+([A-Z][a-z]+(?:\s+\d{4})?)'
        roadmap_matches = re.findall(roadmap_pattern, text)
        if len(roadmap_matches) >= 2:
            header = "| Project Title | Genre | Region | Release Window |\n|---|---|---|---|\n"
            table_rows = [f"| {m[0].strip().replace(':', '')} | {m[1]} | {m[2]} | {m[3]} |" for m in roadmap_matches]
            table_md = f"\n{header}" + "\n".join(table_rows) + "\n"
            
            # Find the "planned releases" block and replace it
            try:
                start_marker = re.search(r'planned releases', text, re.IGNORECASE).start()
                last_m = roadmap_matches[-1]
                end_marker = text.find(last_m[3], start_marker) + len(last_m[3])
                if start_marker != -1 and end_marker != -1:
                    text = text[:start_marker] + table_md + text[end_marker:]
            except Exception:
                pass

    # 8. Markdown Table Sanity Check (Fix common AI mistakes)
    # Fix double pipes: "| |" -> "|"
    text = text.replace("| |", "|")
    # Fix missing space after pipes in separators: "|---|---|---| ---|" -> "|---|---|---|---|"
    text = re.sub(r'(\|\s*[-:]+\s*)+\|', lambda m: m.group(0).replace(" ", ""), text)
    # Ensure there is a newline before and after tables
    text = re.sub(r'([^\n])\n(\|.*\|)\n([^\n])', r'\1\n\n\2\n\n\3', text)

    return text
