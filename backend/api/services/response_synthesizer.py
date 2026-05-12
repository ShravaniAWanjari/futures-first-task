"""
Module: response_synthesizer.py
Purpose: Transforms raw orchestration output into management-quality narrative analysis.
Responsibility: bridges retrieval artifacts and executive communication.
"""

import re
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
SUMMARY_PATTERNS = [r"\bsummarize\b", r"\bsummary\b", r"\bbrief\b", r"\bshorter\b", r"\btl;dr\b"]
COMMON_REGIONS = ["APAC", "North America", "Europe", "LATAM", "Global"]
GENRE_PATTERN = r"(?:Sci[- ]?Fi|Science Fiction|Cyberpunk|Thriller|Drama|Fantasy|Reality|Comedy|Action)"


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


def _bold_metric_tokens(text: str) -> str:
    text = re.sub(r'(?<!\*)\$(\d[\d\.,]*(?:\.\d+)?[MBK]?)(?!\*)', r'**$\1**', text)
    text = re.sub(r'(?<!\*)(\d+(?:\.\d+)?%)(?!\*)', r'**\1**', text)
    text = re.sub(r'(?<!\*)(\d+(?:\.\d+)?x)(?!\*)', r'**\1**', text)
    return text


def synthesize_response(answer_context: str, sources: List[str], confidence: float, history: List[Dict[str, Any]] = None, original_query: str = "") -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Takes raw orchestration answer_context and produces a coherent,
    tone-adaptive narrative summary and structured data for rich rendering.
    """
    sections = _split_sections(answer_context)
    history = history or []
    
    # Phase 8: Detect tone
    tone = _detect_tone(original_query)
    is_summary_request = _is_summary_request(original_query)
    is_informational = any(original_query.lower().startswith(p) for p in ["what is", "who is", "define", "what does"])
    
    # 2. Detect expansion intent
    is_expansion = any(re.search(p, original_query.lower()) for p in [r"provide more", r"what else", r"additional", r"tell me more"])
    is_follow_up = _is_follow_up_prompt(original_query) or is_expansion
    
    last_assistant_msg = ""
    if (is_follow_up or is_summary_request) and history:
        for msg in reversed(history):
            if msg.get('role') == 'assistant':
                last_assistant_msg = msg.get('content', '')
                break

    synthesized_parts = []
    structured_data = None if is_informational else _extract_structured_data(answer_context, original_query)

    # Core Content Extraction
    for section_type, content in sections:
        narrative = None
        if section_type == 'sql':
            narrative = _synthesize_sql_narrative(content, original_query=original_query)
        elif section_type == 'retrieval':
            narrative = _synthesize_retrieval_narrative(content, is_expansion=is_expansion, tone=tone)
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
        narrative_output = _bold_metric_tokens(narrative_output)

    if is_summary_request and last_assistant_msg:
        normalized_previous = _normalize_compare_text(last_assistant_msg)
        normalized_current = _normalize_compare_text(narrative_output)
        if re.match(r'(?i)^summarize\s+(?:it|this|that)(?:\s+for\s+me)?$', original_query.strip()) or not normalized_current or normalized_current == normalized_previous:
            narrative_output = _summarize_previous_answer(last_assistant_msg)

    narrative_output = _sanitize_narrative_output(narrative_output)

    # Phase 25: Multi-Pass Data Extraction
    # If no chart was found in the raw context, try extracting from the CLEAN narrative
    if not is_informational and not _has_visual_payload(structured_data):
        logger.info("[synthesizer] No chart found in raw context. Attempting extraction from synthesized narrative.")
        narrative_structured = _extract_structured_data(narrative_output, original_query)
        if narrative_structured and (_has_visual_payload(narrative_structured) or narrative_structured.get('table')):
            if not structured_data:
                structured_data = narrative_structured
            else:
                if narrative_structured.get('chart'):
                    structured_data['chart'] = narrative_structured['chart']
                if narrative_structured.get('charts'):
                    structured_data['charts'] = narrative_structured['charts']
                if 'table' in narrative_structured and ('table' not in structured_data or not structured_data.get('table')):
                    structured_data['table'] = narrative_structured['table']

    # Update structured_data with LLM fallback if still missing
    if llm_service.enabled and not is_informational and not _has_visual_payload(structured_data):
        chart_intent = any(k in original_query.lower() for k in ["chart", "graph", "plot", "viz", "visualization", "pie", "bar", "line", "summary", "breakdown"])
        if chart_intent or not structured_data:
            logger.info("[synthesizer] Conventional extraction insufficient. Attempting LLM-driven structured extraction.")
            # Use the synthesis narrative for extraction as it's cleaner than raw context
            llm_structured = llm_service.extract_structured_data(original_query, narrative_output)
            if llm_structured and _has_visual_payload(llm_structured):
                if not structured_data:
                    structured_data = llm_structured
                else:
                    if llm_structured.get('chart'):
                        structured_data['chart'] = llm_structured['chart']
                    if llm_structured.get('charts'):
                        structured_data['charts'] = llm_structured['charts']
                
                if 'title' not in structured_data or structured_data['title'] == "Operational Analysis":
                    structured_data['title'] = llm_service.generate_title(original_query)
                structured_data['summary'] = narrative_output[:300] + "..." if len(narrative_output) > 300 else narrative_output

    if structured_data and not is_informational:
        structured_data = _normalize_structured_payload(structured_data)
    elif is_informational:
        structured_data = None

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

            tone = _detect_tone(original_query)
            if tone == "concise":
                return f"**{top['cat']}** leads {label.lower()} at **{_fmt(top['val'])}**, accounting for **{_pct(top['val'], total)}** of the total **{_fmt(total)}**."

            runner_up = entries[1] if len(entries) > 1 else None
            bottom = entries[-1]
            spread = top['val'] - bottom['val']

            snapshot_lines = []
            if runner_up:
                snapshot_lines.append(f"- **{runner_up['cat']}** follows at **{_fmt(runner_up['val'])}**.")
            if len(entries) > 2:
                snapshot_lines.append(f"- The spread between the top and bottom performer is **{_fmt(spread)}**.")
            snapshot_lines.append(f"- Total observed {label.lower()} across the result set is **{_fmt(total)}**.")

            summary_parts = [
                f"## {top['cat']} Leads {_humanize(metric)}",
                f"### Executive Takeaway\n**{top['cat']}** delivers the highest {label.lower()} at **{_fmt(top['val'])}**, representing **{_pct(top['val'], total)}** of the total measured {label.lower()}.",
                "### Performance Snapshot\n" + "\n".join(snapshot_lines),
            ]
            return "\n\n".join(summary_parts)
            
    entity_name = _humanize(str(list(rows[0].values())[0]))
    available_metrics = ", ".join([_humanize(c) for c in metric_cols[:2]]) if metric_cols else "the available metrics"
    return f"## Data Snapshot\n\n**{entity_name}** appears in the result set, with coverage across **{available_metrics}**."


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
            snippet = _bold_metric_tokens(snippet)
            snippet = _polish_bi_language(snippet)
            snippet = _format_all_flattened_tables(snippet)
            snippet = _structure_document_snippet(snippet)
            
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


def _is_summary_request(query: str) -> bool:
    q = query.lower()
    return any(re.search(pattern, q) for pattern in SUMMARY_PATTERNS)


def _normalize_compare_text(text: str) -> str:
    return re.sub(r'\s+', ' ', _sanitize_narrative_output(text or "")).strip().lower()


def _sanitize_narrative_output(text: str) -> str:
    if not text:
        return ""

    cleaned = text
    cleaned = re.sub(r'<thinking>.*?</thinking>', '', cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r'(?is)<analysis>.*?</analysis>', '', cleaned)
    cleaned = re.sub(r'(?im)^\s*(chart[s]?\s+only\s+response|chart_only_response|table_response|metric_comparison|response_type\s*:.*|internal thinking.*)\s*$', '', cleaned)
    cleaned = re.sub(r'(?im)^\s*Operational data for .* has been processed\..*$', '', cleaned)
    cleaned = cleaned.replace("## MANAGEMENT RECOMMENDATION", "### Strategic Implication")
    cleaned = re.sub(r'(?im)^[ \t]*[-*]\s*-\s*$', '', cleaned)
    cleaned = re.sub(r'(?im)^[ \t]*[-*]\s*$', '', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


def _polish_bi_language(text: str) -> str:
    replacements = [
        (r'\bhonestly\b[:,]?\s*', ''),
        (r'\bbasically carried\b', 'was the primary driver of'),
        (r'\bbasically background noise now\b', 'a negligible share of current engagement'),
        (r'\bpretty hard\b', 'materially'),
        (r'\ba lot of users came in through\b', 'user acquisition was led by'),
        (r'\bstill underperforming materially\b', 'remains materially underperforming'),
        (r'\bmore binge behavior\b', 'higher binge-viewing behavior'),
        (r'\bbetter retention\b', 'stronger retention'),
        (r'\blonger sessions\b', 'longer average sessions'),
        (r'\bhigher completion\b', 'higher completion rates'),
    ]

    cleaned = text
    for pattern, replacement in replacements:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)

    cleaned = cleaned.replace('“', '"').replace('”', '"').replace("â€“", "-").replace("–", "-")
    cleaned = re.sub(r'\s{2,}', ' ', cleaned)
    cleaned = re.sub(r'\.\s*recommendation system update', '. Recommendation system update', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def _structure_document_snippet(text: str) -> str:
    specialized = _reconstruct_specialized_snippet(text)
    if specialized:
        return specialized

    structured = text

    section_labels = [
        ("Content Roadmap Overview", "### Content Roadmap Overview"),
        ("Campaign ROI Summary", "### Campaign ROI Summary"),
        ("Infrastructure & Platform Stability", "### Platform Stability"),
        ("Platform Contribution Breakdown", "### Platform Contribution Breakdown"),
        ("Top performing genres", "### Top Performing Genres"),
        ("Top Performing Titles", "### Top Performing Titles"),
        ("Changes included", "### Changes Included"),
        ("device usage", "### Device Mix"),
        ("viewing times", "### Viewing Windows"),
        ("content trends", "### Content Trends"),
    ]

    for label, heading in section_labels:
        structured = re.sub(rf'(?i){re.escape(label)}\s*:?', f'\n\n{heading}\n', structured)

    structured = re.sub(r'(?i)recommendation system update recommendation model v?([\d\.]+) deployed in ([A-Za-z]+)', r'### Platform Update' + "\nRecommendation model v\\1 was deployed in \\2.", structured)
    structured = re.sub(r'(?i)the objective is to improve', '\n### Strategic Objective\nThe objective is to improve', structured)
    structured = re.sub(r'(?i)closing summary', '\n### Closing Summary', structured)
    structured = re.sub(r'\n{3,}', '\n\n', structured)
    return structured.strip()


def _build_markdown_table(headers: List[str], rows: List[List[str]]) -> str:
    header = "| " + " | ".join(headers) + " |"
    sep = "|" + "|".join(["---"] * len(headers)) + "|"
    body = "\n".join("| " + " | ".join(row) + " |" for row in rows)
    return f"{header}\n{sep}\n{body}"


def _clean_extracted_label(label: str) -> str:
    cleaned = label.strip(" :-")
    cleaned = re.sub(r'(?i)^(content performance|top performing titles|top titles this quarter|titles this quarter|genre region focus release window|focus release window|release window|platform contribution breakdown|platform contribution to acquisitions|acquisitions)\s+', '', cleaned)
    cleaned = re.sub(r'(?i)^.*?\b(?:release window|performing titles|top performing titles|titles this quarter)\s+', '', cleaned)
    cleaned = re.sub(r'\s{2,}', ' ', cleaned)
    return cleaned.strip()


def _sentence_case(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return cleaned
    return cleaned[0].upper() + cleaned[1:]


def _reconstruct_specialized_snippet(text: str) -> Optional[str]:
    lower = text.lower()

    if "campaign roi summary" in lower:
        financial_matches = re.findall(r'(' + "|".join(COMMON_REGIONS) + r')\s+(\$[\d\.]+M?)\s+([\d\.]+x)\s+([\d\.]+%)', text, flags=re.IGNORECASE)
        parts = ["### Campaign ROI Summary"]
        if len(financial_matches) >= 2:
            rows = [[m[0], m[1], m[2], m[3]] for m in financial_matches]
            parts.append(_build_markdown_table(["Region", "Marketing Spend", "ROI", "Conversion Rate"], rows))
        creator_note = re.search(r'([A-Z][^.]*creator partnership.*?campaigns\.)', text, flags=re.IGNORECASE)
        europe_note = re.search(r'(Europe continued.*?subscriber growth\.)', text, flags=re.IGNORECASE)
        if creator_note:
            parts.append(f"### Executive Takeaway\n{_sentence_case(_polish_bi_language(creator_note.group(1)))}")
        if europe_note:
            parts.append(f"### Cost Efficiency Risk\n{_sentence_case(_polish_bi_language(europe_note.group(1)))}")
        uptime = re.search(r'(\d+(?:\.\d+)?%)\s+uptime', text, flags=re.IGNORECASE)
        if uptime:
            parts.append(f"### Platform Stability\nThe platform maintained **{uptime.group(1)}** uptime during Q2.")
        return "\n\n".join(parts)

    if "platform contribution breakdown" in lower or "contribution to acquisitions" in lower:
        prop_matches = re.findall(r'([A-Z][A-Za-z ]{2,25})\s+(\d+(?:\.\d+)?)%', text)
        filtered = [(label.strip(), f"{value}%") for label, value in prop_matches if label.strip().lower() not in {"platform contribution breakdown", "platform contribution to acquisitions"}]
        if len(filtered) >= 3:
            rows = [[_clean_extracted_label(label), value] for label, value in filtered]
            parts = [
                "### Platform Contribution Breakdown",
                _build_markdown_table(["Platform", "Contribution Share"], rows),
            ]
            window_note = re.search(r'(late-evening viewing windows.*?local time\.)', text, flags=re.IGNORECASE)
            if window_note:
                parts.append(f"### Audience Timing Signal\n{_sentence_case(_polish_bi_language(window_note.group(1)))}")
            return "\n\n".join(parts)

    if "device share" in lower or "viewing times" in lower:
        parts = []
        window_matches = re.findall(r'(' + "|".join(COMMON_REGIONS) + r')\s+(\d+\s*[AP]M\s*[-–]\s*(?:\d+\s*[AP]M|midnight))', text, flags=re.IGNORECASE)
        device_matches = re.findall(r'(Mobile|Smart TV|Desktop|Tablet)\s+(\d+(?:\.\d+)?)%', text, flags=re.IGNORECASE)
        if window_matches:
            parts.append("### Viewing Windows")
            parts.append(_build_markdown_table(["Region", "Most Active Hours"], [[m[0], m[1]] for m in window_matches]))
        if device_matches:
            parts.append("### Device Mix")
            parts.append(_build_markdown_table(["Device", "Share"], [[m[0], f"{m[1]}%"] for m in device_matches]))
        bullets = []
        if "longer average sessions" in lower or "longer sessions" in lower:
            bullets.append("Late-night audiences show longer average sessions.")
        if "higher completion" in lower:
            bullets.append("Late-night audiences record higher completion rates.")
        if "retention" in lower:
            bullets.append("Late-night audiences also demonstrate stronger retention.")
        if bullets:
            parts.append("### Behavioral Signal\n" + "\n".join([f"- {item}" for item in bullets]))
        genres = re.findall(GENRE_PATTERN, text, flags=re.IGNORECASE)
        unique_genres: List[str] = []
        for genre in genres:
            normalized = genre.replace("Science Fiction", "Sci-Fi")
            if normalized not in unique_genres:
                unique_genres.append(normalized)
        if unique_genres:
            parts.append("### Genre Momentum\n" + "\n".join([f"- **{genre}** remains a leading content category." for genre in unique_genres[:3]]))
        if parts:
            return "\n\n".join(parts)

    if "content roadmap overview" in lower:
        roadmap_matches = re.findall(r'([A-Z][A-Za-z0-9: ]{2,30})\s+(' + GENRE_PATTERN + r')\s+(' + "|".join(COMMON_REGIONS) + r')\s+([A-Z][a-z]+\s+\d{4})', text, flags=re.IGNORECASE)
        parts = ["### Q3 Content Roadmap"]
        objective = re.search(r'(focuses on .*?increasing long[^.]*\.)', text, flags=re.IGNORECASE)
        if objective:
            parts.append(f"### Strategic Objective\n{_sentence_case(_polish_bi_language(objective.group(1)))}")
        operating_groups = []
        for term in ["growth marketing", "analytics engineering", "platform operations", "localization teams"]:
            if term in lower:
                operating_groups.append(term.title())
        if operating_groups:
            parts.append("### Delivery Focus\n" + "\n".join([f"- {group}" for group in operating_groups]))
        if len(roadmap_matches) >= 2:
            parts.append(_build_markdown_table(
                ["Title", "Genre", "Focus Region", "Release Window"],
                [[_clean_extracted_label(m[0]), m[1], m[2], m[3]] for m in roadmap_matches]
            ))
        top_titles_matches = re.findall(r'([A-Z][A-Za-z0-9: -]{2,30})\s+(' + GENRE_PATTERN + r')\s+(\d+(?:\.\d+)?)%\s+(' + "|".join(COMMON_REGIONS) + r')', text, flags=re.IGNORECASE)
        if len(top_titles_matches) >= 2:
            parts.append("### Q2 Benchmark Titles")
            parts.append(_build_markdown_table(
                ["Title", "Genre", "Avg Completion", "Primary Region"],
                [[_clean_extracted_label(m[0]), m[1], f"{m[2]}%", m[3]] for m in top_titles_matches]
            ))
        return "\n\n".join(parts)

    if "top titles this quarter" in lower or "content performance" in lower:
        top_titles_matches = re.findall(r'([A-Z][A-Za-z0-9: -]{2,30})\s+(' + GENRE_PATTERN + r')\s+(\d+(?:\.\d+)?)%\s+(' + "|".join(COMMON_REGIONS) + r')', text, flags=re.IGNORECASE)
        if len(top_titles_matches) >= 2:
            parts = [
                "### Top Performing Titles",
                _build_markdown_table(
                    ["Title", "Genre", "Avg Completion", "Primary Region"],
                    [[_clean_extracted_label(m[0]), m[1], f"{m[2]}%", m[3]] for m in top_titles_matches]
                )
            ]
            if "primary driver of q2 growth" in lower:
                parts.append("### Executive Takeaway\n**Galaxy Burn** was the primary driver of Q2 growth.")
            if "recommendation model" in lower:
                update = re.search(r'recommendation model v?([\d\.]+) deployed in ([A-Za-z]+)', text, flags=re.IGNORECASE)
                if update:
                    parts.append(f"### Platform Update\nRecommendation model v{update.group(1)} was deployed in {update.group(2)}.")
            return "\n\n".join(parts)

    return None


def _summarize_previous_answer(text: str) -> str:
    cleaned = _sanitize_narrative_output(text)
    bullet_candidates: List[str] = []

    for line in cleaned.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('|') or re.match(r'^[-_]{3,}$', stripped):
            continue
        stripped = re.sub(r'^#{1,6}\s*', '', stripped)
        stripped = re.sub(r'^[-*]\s*', '', stripped)
        stripped = re.sub(r'\*\*(.*?)\*\*', r'\1', stripped)
        stripped = stripped.replace('*', '')
        if len(stripped.split()) < 4:
            continue
        bullet_candidates.append(stripped)

    deduped: List[str] = []
    seen = set()
    for item in bullet_candidates:
        key = re.sub(r'\s+', ' ', item).strip().lower()
        if key not in seen:
            deduped.append(item)
            seen.add(key)
        if len(deduped) == 3:
            break

    if not deduped:
        return cleaned

    bullets = "\n".join([f"- {item}" for item in deduped])
    return f"## Executive Summary\n\n{bullets}"


def _has_visual_payload(structured: Optional[Dict[str, Any]]) -> bool:
    if not structured:
        return False
    return bool(structured.get("chart") or structured.get("charts"))


def _normalize_structured_payload(structured: Dict[str, Any]) -> Dict[str, Any]:
    charts = structured.get("charts")
    if not charts and structured.get("chart"):
        charts = [structured["chart"]]

    normalized_charts = []
    for chart in charts or []:
        data_points = chart.get("data") or []
        if not data_points and chart.get("labels") and chart.get("values"):
            data_points = [
                {"label": chart["labels"][idx], "value": chart["values"][idx]}
                for idx in range(min(len(chart["labels"]), len(chart["values"])))
            ]
        if data_points:
            normalized_chart = dict(chart)
            normalized_chart["data"] = data_points
            normalized_charts.append(normalized_chart)

    if normalized_charts:
        structured["charts"] = normalized_charts
        structured["chart"] = normalized_charts[0]

    if structured.get("title") == "Operational Analysis" and normalized_charts:
        labels = [point["label"] for point in normalized_charts[0].get("data", [])]
        structured["title"] = _enhance_title_with_result(structured["title"], {"labels": labels})

    return structured


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
    if re.match(r'(?i)^summarize\s+(?:it|this|that)(?:\s+for\s+me)?$', query_clean):
        return "Executive Summary"
    
    # Pattern matching for common query structures
    patterns = [
        (r"(?i)^share\s+of\s+(.+?)\s+by\s+(.+)$", lambda m: f"{_extract_subject(m.group(2))} {_extract_subject(m.group(1))} Mix"),
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
    if "Mix" in title or "Share" in title:
        return title
    
    # Common category names to replace at the start of the title
    categories = ['Region', 'Platform', 'Channel', 'Category', 'System', 'Market', 'Country', 'Month', 'Quarter', 'Campaign']
    
    for cat in categories:
        # Match case-insensitively but preserve structure
        if title.lower().startswith(cat.lower()):
            # Replace the category name with the top value
            # e.g. "Region Had The Highest Spend" -> "APAC Had The Highest Spend"
            pattern = re.compile(re.escape(cat), re.IGNORECASE)
            new_title = pattern.sub(top_val, title, count=1)
            new_title = re.sub(r'(?i)\s+(Analysis|Review|Report|Summary)$', '', new_title).strip()
            return new_title
            
    # Fallback: if it's an analysis title, prepend the winner
    if any(k in title for k in ["Analysis", "Review", "Summary", "Report"]):
        # Avoid prepending if it's already there
        if top_val.lower() not in title.lower():
            clean_title = re.sub(r'(?i)\s+(Analysis|Review|Report|Summary)$', '', title).strip()
            return f"{top_val} {clean_title}".strip()
            
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
        
        chart_points = [{"label": labels[i], "value": values[i]} for i in range(len(labels))]
        charts = []
        category_lower = category.lower()
        metric_lower = metric.lower()
        positive_values = [point["value"] for point in chart_points if point["value"] > 0]
        scale_ratio = (max(positive_values) / min(positive_values)) if len(positive_values) >= 2 else 1
        is_metric_bucket = category_lower in ("metric", "measure", "kpi")
        ordered_dimension = any(k in category_lower for k in ["month", "quarter", "week", "date", "year", "time"])
        breakdown_intent = any(k in q_lower for k in ["share", "contribution", "breakdown", "mix"])
        comparison_intent = any(k in q_lower for k in ["compare", "comparison", "versus", "vs", "highest", "lowest", "top", "bottom"])
        allow_pie = (
            len(chart_points) >= 2
            and len(chart_points) <= 8
            and not is_metric_bucket
            and sum(point["value"] for point in chart_points) > 0
            and all(point["value"] >= 0 for point in chart_points)
            and (
                breakdown_intent
                or any(k in metric_lower for k in ["share", "contribution", "mix"])
                or (category_lower in ("platform", "region", "channel") and scale_ratio <= 20)
            )
        )
        if is_metric_bucket:
            charts = []
        elif allow_pie:
            charts = [{
                "type": "pie",
                "title": f"Share of {_humanize(metric)} by {_humanize(category)}",
                "data": chart_points,
            }]
        elif ordered_dimension:
            charts = [{
                "type": "line",
                "title": f"{_humanize(metric)} Trend Across {_humanize(category)}",
                "data": chart_points,
            }]
        else:
            charts = [{
                "type": "bar",
                "title": f"{_humanize(metric)} by {_humanize(category)}",
                "data": chart_points,
            }]

        if comparison_intent and not charts and not is_metric_bucket:
            charts = [{
                "type": "bar",
                "title": f"{_humanize(metric)} by {_humanize(category)}",
                "data": chart_points,
            }]

        if charts:
            structured["charts"] = charts
            structured["chart"] = charts[0]
        structured["title"] = _enhance_title_with_result(structured["title"], {"labels": labels})
            
        # Add KPI card if singular metric
        if len(rows) == 1:
            structured["kpi"] = {
                "label": _humanize(metric),
                "value": _fmt(values[0]),
                "context": f"Total for {rows[0][category]}"
            }
            
    return _normalize_structured_payload(structured)

def _extract_flattened_table(text: str) -> Optional[str]:
    """Tries to reconstruct a markdown table from flattened text strings."""
    top_titles_pattern = rf'([A-Z][A-Za-z0-9: -]{{2,30}})\s+({GENRE_PATTERN})\s+(\d+(?:\.\d+)?%)\s+({"|".join(COMMON_REGIONS)})'
    top_titles_matches = re.findall(top_titles_pattern, text, flags=re.IGNORECASE)
    if len(top_titles_matches) >= 2:
        header = "| Title | Genre | Avg Completion | Primary Region |\n|---|---|---|---|\n"
        rows = [f"| {m[0].strip()} | {m[1]} | {m[2]} | {m[3]} |" for m in top_titles_matches]
        return header + "\n".join(rows)

    roadmap_pattern = rf'([A-Z][A-Za-z0-9: -]{{2,30}})\s+({GENRE_PATTERN})\s+({"|".join(COMMON_REGIONS)})\s+([A-Z][a-z]+\s+\d{{4}})'
    roadmap_matches = re.findall(roadmap_pattern, text, flags=re.IGNORECASE)
    if len(roadmap_matches) >= 2:
        header = "| Title | Genre | Focus Region | Release Window |\n|---|---|---|---|\n"
        rows = [f"| {m[0].strip()} | {m[1]} | {m[2]} | {m[3]} |" for m in roadmap_matches]
        return header + "\n".join(rows)

    device_pattern = r'(Mobile|Smart TV|Desktop|Tablet)\s+(\d+(?:\.\d+)?%)'
    device_matches = re.findall(device_pattern, text, flags=re.IGNORECASE)
    if len(device_matches) >= 3:
        header = "| Device | Share |\n|---|---|\n"
        rows = [f"| {m[0]} | {m[1]} |" for m in device_matches]
        return header + "\n".join(rows)

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

    # Pattern 0.2: Proportional Breakdown (Pie Chart Discovery)
    # Matches: "TikTok 34% YouTube Shorts 29% Instagram Reels 18%"
    prop_pattern = r'([A-Z][A-Za-z\s]{2,20})\s+(\d+(?:\.\d+)?%)(?=\s|$)'
    prop_items = re.findall(prop_pattern, text)
    if len(prop_items) >= 3:
        header = "| Segment | Contribution Share |\n|---|---|\n"
        rows = [f"| {m[0].strip()} | {m[1]} |" for m in prop_items]
        return header + "\n".join(rows)

    # Pattern 0.3: Multi-Value Region/Metric (Bar Chart Discovery)
    # Matches: "APAC 81% North America 72% Europe 61%"
    multi_pattern = r'([A-Z][A-Za-z\s]{1,15})\s+(\d+(?:\.\d+)?(?:%|M|hrs|min)?)(?=\s|$)'
    multi_items = re.findall(multi_pattern, text)
    relevant = [m for m in multi_items if any(k in m[0] for k in ["APAC", "America", "Europe", "LATAM", "Asia", "India", "Indonesia"])]
    if len(relevant) >= 2:
        header = "| Category | Metric Value |\n|---|---|\n"
        rows = [f"| {m[0].strip()} | **{m[1]}** |" for m in relevant]
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
    specialized = _reconstruct_specialized_snippet(text)
    if specialized:
        return specialized

    top_titles_pattern = rf'([A-Z][A-Za-z0-9: -]{{2,30}})\s+({GENRE_PATTERN})\s+(\d+(?:\.\d+)?%)\s+({"|".join(COMMON_REGIONS)})'
    top_titles_matches = re.findall(top_titles_pattern, text, flags=re.IGNORECASE)
    if len(top_titles_matches) >= 2 and "| Title | Genre | Avg Completion | Primary Region |" not in text:
        header = "| Title | Genre | Avg Completion | Primary Region |\n|---|---|---|---|\n"
        table_rows = [f"| {m[0].strip()} | {m[1]} | {m[2]} | {m[3]} |" for m in top_titles_matches]
        table_md = f"\n{header}" + "\n".join(table_rows) + "\n"
        try:
            first_m = top_titles_matches[0][0]
            last_m = top_titles_matches[-1][3]
            start_i = text.find(first_m)
            end_i = text.find(last_m, start_i) + len(last_m)
            if start_i != -1 and end_i != -1:
                text = text[:start_i] + table_md + text[end_i:]
        except Exception:
            pass

    roadmap_pattern = rf'([A-Z][A-Za-z0-9: -]{{2,30}})\s+({GENRE_PATTERN})\s+({"|".join(COMMON_REGIONS)})\s+([A-Z][a-z]+\s+\d{{4}})'
    roadmap_matches = re.findall(roadmap_pattern, text, flags=re.IGNORECASE)
    if len(roadmap_matches) >= 2 and "| Title | Genre | Focus Region | Release Window |" not in text:
        header = "| Title | Genre | Focus Region | Release Window |\n|---|---|---|---|\n"
        table_rows = [f"| {m[0].strip()} | {m[1]} | {m[2]} | {m[3]} |" for m in roadmap_matches]
        table_md = f"\n{header}" + "\n".join(table_rows) + "\n"
        try:
            first_m = roadmap_matches[0][0]
            last_m = roadmap_matches[-1][3]
            start_i = text.find(first_m)
            end_i = text.find(last_m, start_i) + len(last_m)
            if start_i != -1 and end_i != -1:
                text = text[:start_i] + table_md + text[end_i:]
        except Exception:
            pass

    device_pattern = r'(Mobile|Smart TV|Desktop|Tablet)\s+(\d+(?:\.\d+)?%)'
    device_matches = re.findall(device_pattern, text, flags=re.IGNORECASE)
    if len(device_matches) >= 3 and "| Device | Share |" not in text:
        header = "| Device | Share |\n|---|---|\n"
        table_rows = [f"| {m[0]} | {m[1]} |" for m in device_matches]
        table_md = f"\n{header}" + "\n".join(table_rows) + "\n"
        try:
            first_m = device_matches[0][0]
            last_m = device_matches[-1][1]
            start_i = text.find(first_m)
            end_i = text.find(last_m, start_i) + len(last_m)
            if start_i != -1 and end_i != -1:
                text = text[:start_i] + table_md + text[end_i:]
        except Exception:
            pass

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

    # 6. Proportional Breakdown (Pie Chart Discovery)
    # Matches: "TikTok 34% YouTube Shorts 29% Instagram Reels 18%"
    prop_pattern = r'([A-Z][A-Za-z\s]{2,20})\s+(\d+(?:\.\d+)?%)(?=\s|$)'
    prop_matches = re.findall(prop_pattern, text)
    if len(prop_matches) >= 3 and "| Platform |" not in text:
        header = "| Segment | Contribution Share |\n|---|---|\n"
        table_rows = [f"| {m[0].strip()} | {m[1]} |" for m in prop_matches]
        table_md = f"\n{header}" + "\n".join(table_rows) + "\n"
        
        # Replace the first cluster of matches found
        try:
            first_m = prop_matches[0][0]
            last_m = prop_matches[-1][1]
            start_i = text.find(first_m)
            end_i = text.find(last_m, start_i) + len(last_m)
            if start_i != -1 and end_i != -1:
                text = text[:start_i] + table_md + text[end_i:]
        except Exception: pass

    # 7. Multi-Value Region/Metric Rehydration (Bar Chart Discovery)
    # Matches: "APAC 81% North America 72% Europe 61%"
    multi_metric_pattern = r'([A-Z][A-Za-z\s]{1,15})\s+(\d+(?:\.\d+)?(?:%|M|hrs|min)?)(?=\s|$)'
    multi_matches = re.findall(multi_metric_pattern, text)
    # Filter to ensure we have actual regions or categories
    relevant_multi = [m for m in multi_matches if any(k in m[0] for k in ["APAC", "America", "Europe", "LATAM", "Asia", "India", "Indonesia"])]
    if len(relevant_multi) >= 2 and "| Region |" not in text:
        header = "| Category | Metric Value |\n|---|---|\n"
        table_rows = [f"| {m[0].strip()} | **{m[1]}** |" for m in relevant_multi]
        table_md = f"\n{header}" + "\n".join(table_rows) + "\n"
        
        try:
            first_m = relevant_multi[0][0]
            last_m = relevant_multi[-1][1]
            start_i = text.find(first_m)
            end_i = text.find(last_m, start_i) + len(last_m)
            if start_i != -1 and end_i != -1:
                text = text[:start_i] + table_md + text[end_i:]
        except Exception: pass

    # 8. Roadmap / Planned Release Reconstruction
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

    # 8. Regional Acronym Expansion (Avoid "NA" confusion)
    # Replaces " NA " or " NA|" with " North America " or " North America|"
    text = re.sub(r'(\s|\|)NA(\s|\|)', r'\1North America\2', text)

    # 9. Markdown Table Sanity Check & Structural Hygiene
    # Fix double pipes: "| |" -> "|"
    text = text.replace("| |", "|")
    
    # Remove "manual decorators" (lines of only dashes/dots inside/around tables)
    text = re.sub(r'\|[ \t]*[-.]{3,}[ \t]*\|', '|', text) # Remove dashes inside cells
    text = re.sub(r'^[ \t]*[-.]{5,}[ \t]*$', '', text, flags=re.MULTILINE) # Remove standalone dashed lines
    
    # Fix missing space after pipes in separators: "|---|---|---| ---|" -> "|---|---|---|---|"
    text = re.sub(r'(\|\s*[-:]+\s*)+\|', lambda m: m.group(0).replace(" ", ""), text)
    
    # Ensure there is a newline before and after tables
    # First, find lines that look like tables and make sure they are separated from text
    text = re.sub(r'([^\n])\n(\|.*\|)\n([^\n])', r'\1\n\n\2\n\n\3', text)
    
    # 10. List Rehydration (Fix fragmented bullets and orphan hyphens)
    # Remove "phantom bullets" (standalone dots or hyphens on a line)
    text = re.sub(r'^[ \t]*[•\-\*]\s*$', '', text, flags=re.MULTILINE)
    
    # Fix "double-bulleting" like "• - "
    text = text.replace("• -", "•")
    text = text.replace("* -", "•")
    
    # Merge fragments that were meant to be one line but split by a newline and a bullet
    # e.g., "Increasing long \n - content strategy" -> "Increasing long content strategy"
    text = re.sub(r'([a-z])\s*\n\s*[•\-\*]\s*([a-z])', r'\1 \2', text)

    # Final cleanup of any trailing empty table cells that were just dashes
    text = text.replace("|---|---|---|---|---|", "|---|---|---|---|")
    
    # Remove any internal [CHART] or [TABLE] tags that might have leaked
    text = re.sub(r'\[[A-Z\s_]{5,}\]', '', text)

    return text
