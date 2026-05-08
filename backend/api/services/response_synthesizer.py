"""
Module: response_synthesizer.py
Purpose: Transforms raw orchestration output into management-quality narrative analysis.
Responsibility: bridges retrieval artifacts and executive communication.
"""

import re
from typing import List, Dict, Any, Optional


def synthesize_response(answer_context: str, sources: List[str], confidence: float, history: List[Dict[str, Any]] = None, original_query: str = "") -> str:
    """
    Takes raw orchestration answer_context and produces a coherent,
    management-oriented narrative summary with insights and implications.
    """
    sections = _split_sections(answer_context)
    history = history or []
    
    # 1. Detect if this is an operational domain query
    classification = None
    # We can infer domain from the answer_context if needed, but let's look for SQL lead
    is_operational = "ingestion_logs" in answer_context or "validation_summaries" in answer_context
    
    # 2. Detect if this is a follow-up expansion
    is_follow_up = _is_follow_up_prompt(original_query)
    last_assistant_msg = ""
    if is_follow_up and history:
        for msg in reversed(history):
            if msg.get('role') == 'assistant':
                last_assistant_msg = msg.get('content', '')
                break

    synthesized_parts = []
    
    # Lead-in selection
    if is_operational:
        synthesized_parts.append("Operational analysis of the latest data pipeline activity indicates:")
    elif is_follow_up and last_assistant_msg:
        synthesized_parts.append("Expanding on the prior analysis:")

    # Core Content Extraction
    content_found = False
    for section_type, content in sections:
        narrative = None
        if section_type == 'sql':
            narrative = _synthesize_sql_narrative(content)
        elif section_type == 'retrieval':
            narrative = _synthesize_retrieval_narrative(content)
        elif section_type == 'plain':
            narrative = content.strip() if content.strip() else None
            
        if narrative:
            synthesized_parts.append(narrative)
            content_found = True
    
    if not content_found:
        if is_follow_up:
            return "No additional operational details could be retrieved to expand on the previous answer."
        return "No specific operational data matching this query was identified. Re-phrasing the request with different regions or metrics may provide more visibility."

    # Add Operational Recommendation/Implication (Synthesized based on context)
    recommendation = _generate_operational_implication(answer_context, original_query)
    if recommendation:
        synthesized_parts.append(recommendation)
    
    return "\n\n".join(synthesized_parts)


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
            
    return None


def _synthesize_retrieval_narrative(content: str) -> Optional[str]:
    """Transforms raw retrieval chunks into management-grade narrative analysis."""
    results = re.split(r'\[Document Result \d+\]', content)
    results = [r.strip() for r in results if r.strip()]
    
    raw_snippets = []
    for res in results:
        match = re.search(r'Snippet:(.*)', res, re.DOTALL)
        if match:
            s = match.group(1).strip()
            if len(s) > 30 and not _is_fragment(s):
                raw_snippets.append(s)
    
    if not raw_snippets: return None
    
    # 1. Clean and Normalize
    cleaned = []
    for s in raw_snippets:
        s = s.replace('Snippet:', '').strip()
        # Remove metadata leakages
        s = re.sub(r'Source File:.*?\n', '', s)
        s = re.sub(r'Section:.*?\n', '', s)
        s = re.sub(r'Page \d+', '', s)
        cleaned.append(s.strip())
        
    # 2. Semantic Deduplication (Mock)
    unique = []
    for c in cleaned:
        if not any(u[:50].lower() in c[:50].lower() for u in unique):
            unique.append(c)
            
    # 3. Structural Synthesis
    if not unique: return None
    
    main_point = unique[0]
    if not main_point.endswith('.'): main_point += '.'
    
    if len(unique) > 1:
        support = unique[1]
        # Soften the connection
        lead = "Additional operational reports suggest that" if len(support.split()) > 10 else "Related commentary notes:"
        return f"{main_point} {lead} {support.lower() if support[0].isupper() and len(support.split()) > 3 else support}"
    
    return main_point


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
    try: return float(val.replace(',', ''))
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
    title = re.sub(r'\s+', ' ', title.strip())
    return title[:47] + '...' if len(title) > 50 else title
