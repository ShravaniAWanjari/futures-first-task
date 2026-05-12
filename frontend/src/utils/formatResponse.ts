/**
 * Formats pre-synthesized backend responses for display.
 * Full markdown parsing: headings, bold, bullets, horizontal rules, tables, callouts.
 */

export interface FormattedSegment {
  type: 'heading' | 'bullet-list' | 'bold-paragraph' | 'paragraph' | 'divider' | 'table' | 'callout';
  content: string;
  items?: string[];
  level?: number;
}

/** Strips all ** markers: **text** → text */
function stripBold(s: string): string {
  return s.replace(/\*\*(.*?)\*\*/g, '$1');
}

function isTableLine(line: string): boolean {
  return (line.match(/\|/g) || []).length >= 1;
}

/** Checks if a line is a separator row like |---|---|--- */
function isSeparatorLine(line: string): boolean {
  return /^\|?[\s\-:]+(\|[\s\-:]+)+\|?$/.test(line.trim());
}

/**
 * Parses a pipe-delimited table row into cells.
 * Preserves empty cells (e.g. "| | Subscriber Churn |" → ['', 'Subscriber Churn'])
 * by only stripping the very first and last empty segments from the split.
 */
function parseTableRow(line: string): string[] {
  const parts = line.split('|');
  // Remove first and last elements if they're empty (from leading/trailing pipes)
  const trimmed = parts[0].trim() === '' ? parts.slice(1) : parts;
  const result = trimmed[trimmed.length - 1]?.trim() === '' ? trimmed.slice(0, -1) : trimmed;
  return result.map(c => stripBold(c.trim()));
}

export function formatResponse(raw: string): FormattedSegment[] {
  if (!raw || !raw.trim()) {
    return [{ type: 'paragraph', content: 'No response available.' }];
  }

  // ── Pre-processing ──────────────────────────────────────────────────────────
  // 1. Strip blockquote markers
  // 2. Replace unprofessional "SO WHAT?" with BI-grade language
  let cleaned = raw
    .replace(/^>\s*/gm, '')
    .replace(/SO WHAT\??:?\s*/gi, 'Strategic Implication: ')
    .replace(/So What\??:?\s*/g, 'Strategic Implication: ')
    .replace(/^\s*(chart[s]?\s+only\s+response|chart_only_response|table_response|metric_comparison)\s*$/gim, '')
    .replace(/^\s*response_type\s*:.*$/gim, '')
    .replace(/<thinking>[\s\S]*?<\/thinking>/gi, '');

  // ── Table Re-assembly ───────────────────────────────────────────────────────
  // The AI often inserts blank lines BETWEEN table rows, splitting them into
  // separate \n\n blocks. We fix this by joining consecutive pipe-containing
  // lines (even when separated by blank lines) back into a single block.
  const reassembled: string[] = [];
  const rawLines = cleaned.split('\n');
  let tableBuffer: string[] = [];

  for (let i = 0; i < rawLines.length; i++) {
    const line = rawLines[i];
    const isBlank = line.trim() === '';

    if (isTableLine(line)) {
      tableBuffer.push(line);
    } else if (isBlank && tableBuffer.length > 0) {
      // Look ahead: if next non-blank line is also a table row, keep buffering
      let lookahead = i + 1;
      while (lookahead < rawLines.length && rawLines[lookahead].trim() === '') lookahead++;
      if (lookahead < rawLines.length && isTableLine(rawLines[lookahead])) {
        // Skip blank — will be absorbed into the table
        continue;
      } else {
        // End of table block — flush buffer
        reassembled.push(tableBuffer.join('\n'));
        tableBuffer = [];
        reassembled.push(''); // preserve blank line
      }
    } else {
      if (tableBuffer.length > 0) {
        reassembled.push(tableBuffer.join('\n'));
        tableBuffer = [];
      }
      reassembled.push(line);
    }
  }
  if (tableBuffer.length > 0) {
    reassembled.push(tableBuffer.join('\n'));
  }

  cleaned = reassembled.join('\n');

  // ── Block-level parsing ─────────────────────────────────────────────────────
  const segments: FormattedSegment[] = [];
  const blocks = cleaned.split(/\n\n+/).map(b => b.trim()).filter(Boolean);

  for (const block of blocks) {
    // --- Horizontal Rule ---
    if (/^-{3,}$/.test(block) || /^_{3,}$/.test(block)) {
      segments.push({ type: 'divider', content: '' });
      continue;
    }

    const headingMatch = block.match(/^(#{1,6})\s+(.+)/);
    if (headingMatch) {
      segments.push({
        type: 'heading',
        level: headingMatch[1].length,
        content: stripBold(headingMatch[2].trim()),
      });
      // If there's more text after the heading in the same block, add it as a paragraph
      const lines = block.split('\n');
      if (lines.length > 1) {
        const rest = lines.slice(1).join('\n').trim();
        if (rest) segments.push({ type: 'paragraph', content: rest });
      }
      continue;
    }

    // --- Bold Heading: entire block is **Some Title** ---
    const boldHeadingMatch = block.match(/^\*\*([^*\n]{1,150})\*\*$/);
    if (boldHeadingMatch) {
      segments.push({ type: 'heading', level: 3, content: boldHeadingMatch[1].trim() });
      continue;
    }

    // --- ALL-CAPS heading (e.g. "EXECUTIVE SUMMARY: APAC GROWTH") ---
    if (/^[A-Z][A-Z\s&:,\-–()]+$/.test(block.trim()) && block.trim().length < 120) {
      segments.push({ type: 'heading', level: 2, content: block.trim() });
      continue;
    }

    // --- Callout / Strategic Implication ---
    if (/^(OPERATIONAL\s+(INSIGHT|WARNING|NOTE)|STRATEGIC\s+IMPLICATION|KEY\s+INSIGHT|CRITICAL\s+(NOTE|FINDING))/i.test(block.trim())) {
      segments.push({ type: 'callout', content: block });
      continue;
    }

    // --- Markdown Table ---
    if (isTableLine(block)) {
      const blockLines = block.split('\n');
      let i = 0;
      let producedTable = false;

      while (i < blockLines.length) {
        const line = blockLines[i];

        if (isTableLine(line)) {
          // Collect all contiguous table lines
          const tableLines: string[] = [];
          while (i < blockLines.length && isTableLine(blockLines[i])) {
            tableLines.push(blockLines[i]);
            i++;
          }

          // Extract header (first non-separator row)
          const headerLine = tableLines.find(l => !isSeparatorLine(l));
          if (!headerLine) continue;

          const columns = parseTableRow(headerLine);
          const dataLines = tableLines.filter(l => l !== headerLine && !isSeparatorLine(l));

          const rows = dataLines.map(line => {
            const cells = parseTableRow(line);
            const rowObj: any = {};
            columns.forEach((col, idx) => {
              // Use column name, or 'Column N' for empty headers
              const key = col || `Column ${idx + 1}`;
              rowObj[key] = cells[idx] ?? 'N/A';
            });
            return rowObj;
          });

          // Normalize column names (replace empty with placeholder)
          const normalizedColumns = columns.map((c, i) => c || `Column ${i + 1}`);

          if (normalizedColumns.length > 0 && rows.length > 0) {
            producedTable = true;
            segments.push({ type: 'table', content: JSON.stringify({ columns: normalizedColumns, rows }) });
          }
        } else {
          // Narrative line within a pipe-containing block
          if (line.trim()) segments.push({ type: 'paragraph', content: line.trim() });
          i++;
        }
      }
      if (producedTable) continue;
    }

    // --- Bullet List (lines starting with - or *) ---
    const lines = block.split('\n').map(l => l.trim()).filter(Boolean);
    const bulletLines = lines.filter(l => /^[-*•]\s+/.test(l));
    if (bulletLines.length >= 1) {
      const intro = lines.filter(l => !/^[-*•]\s+/.test(l)).join(' ');
      const items = bulletLines.map(l => l.replace(/^[-*•]\s+/, ''));
      if (intro) segments.push({ type: 'paragraph', content: intro });
      segments.push({ type: 'bullet-list', content: '', items });
      continue;
    }

    const labelBodyMatch = block.match(/^\*\*([^*\n]{1,80})\*\*[:\-]+\s*(.{10,})/s);
    if (labelBodyMatch) {
      segments.push({ type: 'heading', level: 3, content: labelBodyMatch[1].trim() });
      segments.push({ type: 'paragraph', content: labelBodyMatch[2].trim() });
      continue;
    }

    // --- Bold paragraph (has ** markers but not a heading) ---
    if (block.includes('**')) {
      segments.push({ type: 'paragraph', content: block });
      continue;
    }

    // --- Plain paragraph ---
    segments.push({ type: 'paragraph', content: block });
  }

  return segments;
}
