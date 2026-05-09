"""
Module: response_synthesizer.py
Purpose: Transforms raw orchestration output into management-quality narrative analysis.
Responsibility: bridges retrieval artifacts and executive communication.
"""

import re
import logging
import json
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Phase 4: Token Safety — Maximum chars per snippet
MAX_SNIPPET_CHARS = 500
MAX_FINDINGS = 4


def _detect_tone(query: str) -> str:
    """Phase 8: Detects desired response tone from query phrasing."""
    q = query.lower()
    if any(kw in q for kw in ["quick", "brief", "concise", "short", "tl;dr", "briefly"]):
        return "concise"
    if any(kw in q for kw in ["casual", "simply", "plain english", "easy", "informal"]):
        return "conversational"
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
    content_found = False
    for section_type, content in sections:
        narrative = None
        if section_type == 'sql':
            narrative = _synthesize_sql_narrative(content)
        elif section_type == 'retrieval':
            narrative = _synthesize_retrieval_narrative(content, is_expansion=is_expansion, tone=tone)
        elif section_type == 'plain':
            # Small talk and conversational responses pass through directly
            if content.strip():
                narrative = content.strip()
            
        if narrative:
            synthesized_parts.append(narrative)
            content_found = True
    
    if not content_found:
        if is_follow_up:
            return "No additional operational details could be retrieved to expand on the previous answer.", None
        return "The requested information could not be retrieved from current datasets.", None

    # Add Operational Recommendation/Implication
    if tone != "concise":
        recommendation = _generate_operational_implication(answer_context, original_query)
        if recommendation:
            synthesized_parts.append(recommendation)
    
    narrative_output = "\n\n".join(synthesized_parts)
    
    # Update structured_data with narrative components if not already there
    if structured_data:
        structured_data['summary'] = narrative_output[:300] + "..." if len(narrative_output) > 300 else narrative_output
        if 'title' not in structured_data:
            structured_data['title'] = generate_session_title(original_query)

    return narrative_output, structured_data


def _synthesize_sql_narrative(content: str) -> Optional[str]:
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
        entries = sorted([{'cat': r[category], 'val': _parse_num(r[metric])} for r in rows if _parse_num(r[metric]) is not None], key=lambda x: x['val'], reverse=True)
        
        if entries:
            top = entries[0]
            total = sum(e['val'] for e in entries)
            summary = f"Performance data indicates that **{top['cat']}** leads in {label} at {_fmt(top['val'])}, representing {_pct(top['val'], total)} of total {label} ({_fmt(total)})."
            
            if len(entries) >= 2:
                runner = entries[1]
                summary += f" {runner['cat']} follows with {_fmt(runner['val'])}, showing a variance of {_fmt(top['val'] - runner['val'])}."
            
            return summary
            
    # Final Fallback: provide a high-level count if data exists but didn't match structured patterns
    return f"Analysis of the retrieved records identified **{len(rows)} relevant entries**. Dominant categories include **{_humanize(str(list(rows[0].values())[0]))}** and associated operational metrics."


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
            
            # 1. Technical Artifact Removal
            snippet = re.sub(r'Trace ID:\s*[a-f0-9]{8,}', '', snippet, flags=re.IGNORECASE)
            snippet = re.sub(r'\b[a-f0-9]{32}\b', '', snippet, flags=re.IGNORECASE)
            snippet = snippet.replace('\u200b', '')
            snippet = re.sub(r'#+\s*', '', snippet)
            
            # 2. Fix fragments at start
            snippet = re.sub(r'^[a-z]{1,10}\b\s*', '', snippet)
            
            # 3. Bullet Point Normalization
            # Only match single asterisks used as list delimiters (not ** bold markers)
            snippet = re.sub(r'(?<!\*)\*(?!\*)', '\n- ', snippet)
            snippet = snippet.replace('●', '\n- ').replace('•', '\n- ')
            
            # 4. Header Identification
            snippet = re.sub(r'(\b[A-Z][a-z/ ]+[:])', r'\n\n**\1**\n', snippet)
            
            # 5. Sentence cleanup
            snippet = re.sub(r'\.([A-Z])', r'. \1', snippet)
            
            # Phase 4: Token Safety — Truncate oversized snippets
            if len(snippet) > MAX_SNIPPET_CHARS:
                snippet = snippet[:MAX_SNIPPET_CHARS].rsplit('.', 1)[0] + '.'
            
            # Clean up excessive newlines
            snippet = re.sub(r'\n{3,}', '\n\n', snippet)
            
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
                parts.append(f"### Key Findings\n\n{f['finding']}")
            else:
                parts.append(f"### Additional Context ({f['source']})\n\n{f['finding']}")
            
    return "\n\n".join(parts)


def _generate_operational_implication(context: str, query: str) -> Optional[str]:
    """Adds a layer of synthesized management implication based on the context."""
    ctx_lower = context.lower()
    q_lower = query.lower()
    
    # Localization / Quality theme
    if any(k in ctx_lower for k in ['localization', 'subtitle', 'quality', 'translation']):
        return "Internal assessments suggest strengthening localization QA protocols and viewer feedback monitoring before the next major release rollout to mitigate consistency risks."
        
    # Spend / Efficiency theme
    if any(k in ctx_lower for k in ['spend', 'efficiency', 'roi', 'cost']):
        return "Given the observed variance in acquisition efficiency, re-aligning budget towards high-performance regions or channels may optimize overall reach for the upcoming quarter."
        
    # Data / Warning theme
    if any(k in ctx_lower for k in ['warning', 'inconsistency', 'data quality', 'error']):
        return "Addressing these data inconsistencies is a priority for operational transparency. Recommendations include a cross-reference pass with the latest ingestion logs to resolve tracking gaps."

    # Growth / Performance theme
    if any(k in ctx_lower for k in ['growth', 'subscriber', 'reach', 'performance']):
        return "Sustaining this performance trajectory likely requires continued focus on high-engagement content segments identified in these reports."

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
    return len(rows) > 0 and _parse_num(rows[0].get(col, '')) is not None

def _parse_num(val: str) -> Optional[float]:
    if val is None: return None
    s = str(val).replace(',', '').replace('$', '').replace('%', '').strip()
    if not s: return None
    
    multiplier = 1.0
    if s.upper().endswith('K'):
        multiplier = 1_000.0
        s = s[:-1]
    elif s.upper().endswith('M'):
        multiplier = 1_000_000.0
        s = s[:-1]
    elif s.upper().endswith('B'):
        multiplier = 1_000_000_000.0
        s = s[:-1]
        
    try: return float(s) * multiplier
    except: return None

def _humanize(col: str) -> str:
    acronyms = {'usd', 'roi', 'apac', 'emea', 'latam', 'kpi'}
    words = col.replace('_', ' ').split()
    return ' '.join(w.upper() if w.lower() in acronyms else w.capitalize() for w in words)

def _fmt(n: float) -> str:
    if abs(n) >= 1_000_000: return f"{n / 1_000_000:.1f}M"
    if abs(n) >= 1_000: return f"{n / 1_000:.1f}K"
    return f"{n:.1f}"

def _pct(part: float, total: float) -> str:
    return f"{(part / total) * 100:.0f}%" if total > 0 else "0%"

def _is_fragment(text: str) -> bool:
    return len(text.split()) < 4 or text.lower() in ('controls', 'overview', 'summary')


def generate_session_title(query: str) -> str:
    """
    Generates a concise, management-oriented session title from a user query.
    """
    query_clean = query.strip().rstrip('?').rstrip('.').strip()
    
    # Pattern matching for common query structures
    patterns = [
        # "Why did X happen" → "X Analysis"
        (r"(?i)^why\s+(?:did|does|do|are|is|were|was)\s+(.+?)(?:\s+(?:drop|fall|decline|decrease))", lambda m: f"{_extract_subject(m.group(1))} Decline Analysis"),
        (r"(?i)^why\s+(?:did|does|do|are|is|were|was)\s+(.+?)(?:\s+(?:increase|grow|rise|improve))", lambda m: f"{_extract_subject(m.group(1))} Growth Analysis"),
        (r"(?i)^why\s+(?:are|is)\s+there\s+so\s+many\s+(.+)", lambda m: f"{_titleize(m.group(1))} Investigation"),
        (r"(?i)^why\s+(.+)", lambda m: f"{_extract_subject(m.group(1))} Analysis"),
        
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
    stop_prefixes = ['our', 'the', 'their', 'its', 'my', 'your', 'a', 'an', 'some', 'any']
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
    
    header_line = lines[dash_idx - 1]
    columns = [c.strip() for c in header_line.split('|') if c.strip()]
    data_lines = [l for l in lines[dash_idx + 1:] if not l.startswith('...')]
    
    logger.info(f"[synthesizer] Parsed {len(columns)} columns and {len(data_lines)} potential rows")
    
    rows = []
    for line in data_lines:
        values = [v.strip() for v in line.split('|')]
        if len(values) >= len(columns):
            row = {columns[ci]: values[ci] for ci in range(len(columns))}
            rows.append(row)
            
    if not rows: return None
    
    # 1. Determine Response Type
    res_type = "operational_analysis"
    q_lower = query.lower()
    if any(k in q_lower for k in ["compare", "vs", "difference"]): res_type = "metric_comparison"
    elif any(k in q_lower for k in ["trend", "over time", "month", "quarter"]): res_type = "trend_analysis"
    elif any(k in q_lower for k in ["breakdown", "contribution", "ratio"]): res_type = "breakdown_analysis"
    elif len(rows) > 5: res_type = "table_response"
    
    # 2. Build Structured Object
    structured = {
        "response_type": res_type,
        "title": generate_session_title(query),
        "table": {
            "columns": columns,
            "rows": rows[:20] # Cap for UI sanity
        }
    }
    
    # 3. Chart Detection
    metric_cols = [c for c in columns if _is_numeric_col(rows, c)]
    category_cols = [c for c in columns if c not in metric_cols and c.lower() not in ('id', 'pk', 'uuid')]
    
    if metric_cols and category_cols:
        metric = metric_cols[0]
        category = category_cols[0]
        
        # Limit labels for chart clarity
        labels = [str(r[category]) for r in rows[:10]]
        values = [_parse_num(r[metric]) for r in rows[:10]]
        
        chart_type = "bar"
        if res_type == "trend_analysis": chart_type = "line"
        elif res_type == "breakdown_analysis": chart_type = "pie"
        
        structured["chart"] = {
            "type": chart_type,
            "label": _humanize(metric),
            "labels": labels,
            "values": values
        }
        
        # Add KPI card if singular metric
        if len(rows) == 1:
            structured["kpi"] = {
                "label": _humanize(metric),
                "value": _fmt(values[0]),
                "context": f"Total for {rows[0][category]}"
            }
            
    return structured
