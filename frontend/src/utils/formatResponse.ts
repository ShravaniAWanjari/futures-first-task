/**
 * Formats pre-synthesized backend responses for display.
 * Full markdown parsing: headings, bold, bullets, horizontal rules, tables, blockquotes.
 */

export interface FormattedSegment {
  type: 'heading' | 'bullet-list' | 'bold-paragraph' | 'paragraph' | 'divider' | 'table' | 'callout';
  content: string;
  items?: string[];   // For bullet lists
  level?: number;     // For headings (2 or 3)
}

/**
 * Strips all markdown bold markers from a string: **text** → text
 */
function stripBold(s: string): string {
  return s.replace(/\*\*(.*?)\*\*/g, '$1');
}

/**
 * Converts markdown bold markers to HTML strong tags: **text** → <strong>text</strong>
 */
function boldToHtml(s: string): string {
  return s.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
}

/**
 * Checks if a block is a "bold heading" — the entire block is wrapped in ** **
 * e.g. "**Executive Summary: Q2 FY2026**"
 */
function isBoldHeading(block: string): boolean {
  const trimmed = block.trim();
  return trimmed.startsWith('**') && trimmed.endsWith('**') && trimmed.length < 200 
    && (trimmed.match(/\*\*/g) || []).length === 2;
}

export function formatResponse(raw: string): FormattedSegment[] {
  if (!raw || !raw.trim()) {
    return [{ type: 'paragraph', content: 'No response available.' }];
  }

  // Pre-process: clean up blockquote markers and unprofessional language
  let cleaned = raw
    // Strip "> " blockquote prefix
    .replace(/^>\s*/gm, '')
    // Replace "SO WHAT?" with professional language
    .replace(/SO WHAT\??:?\s*/gi, 'Strategic Implication: ')
    .replace(/So What\??:?\s*/g, 'Strategic Implication: ');

  const segments: FormattedSegment[] = [];

  // Split by double-newline into blocks
  const blocks = cleaned.split(/\n\n+/).map(b => b.trim()).filter(Boolean);

  for (const block of blocks) {
    // --- Horizontal Rule ---
    if (/^-{3,}$/.test(block) || /^_{3,}$/.test(block)) {
      segments.push({ type: 'divider', content: '' });
      continue;
    }

    // --- Heading (### or ##) ---
    const headingMatch = block.match(/^(#{2,3})\s+(.+)/);
    if (headingMatch) {
      segments.push({
        type: 'heading',
        level: headingMatch[1].length,
        content: stripBold(headingMatch[2].trim()),
      });
      continue;
    }

    // --- Bold Heading (entire block is **Some Title**) ---
    if (isBoldHeading(block)) {
      segments.push({
        type: 'heading',
        level: 3,
        content: stripBold(block),
      });
      continue;
    }

    // --- Callout / Warning / Insight block ---
    const calloutMatch = block.match(/^(OPERATIONAL\s+(INSIGHT|WARNING|NOTE)|STRATEGIC\s+IMPLICATION|KEY\s+INSIGHT|CRITICAL\s+NOTE)[:\s]*(.*)/is);
    if (calloutMatch) {
      segments.push({
        type: 'callout',
        content: block,
      });
      continue;
    }

    // --- Bullet List (lines starting with - or *) ---
    const lines = block.split('\n').map(l => l.trim()).filter(Boolean);
    const bulletLines = lines.filter(l => /^[-*•]\s+/.test(l));
    if (bulletLines.length >= 2 || (bulletLines.length === lines.length && bulletLines.length >= 1)) {
      const intro = lines.filter(l => !/^[-*•]\s+/.test(l)).join(' ');
      const items = bulletLines.map(l => l.replace(/^[-*•]\s+/, ''));
      if (intro) {
        segments.push({ type: 'paragraph', content: intro });
      }
      segments.push({ type: 'bullet-list', content: '', items });
      continue;
    }

    // --- Mixed content: paragraph with inline bullets ---
    if (lines.length === 1 && (block.split(/\s[-*]\s/).length > 2)) {
      const parts = block.split(/\s[-*]\s/);
      const intro = parts[0];
      const items = parts.slice(1);
      if (intro) {
        segments.push({ type: 'paragraph', content: intro });
      }
      if (items.length > 0) {
        segments.push({ type: 'bullet-list', content: '', items });
      }
      continue;
    }

    // --- Markdown Table Parser (handles multiple tables + interleaved text) ---
    if (block.includes('|')) {
      const blockLines = block.split('\n');
      let i = 0;
      let foundTable = false;

      while (i < blockLines.length) {
        const line = blockLines[i];
        const pipeCount = (line.match(/\|/g) || []).length;

        if (pipeCount >= 2) {
          // Collect contiguous table lines
          const tableLines: string[] = [];
          while (i < blockLines.length && (blockLines[i].match(/\|/g) || []).length >= 2) {
            tableLines.push(blockLines[i]);
            i++;
          }

          if (tableLines.length >= 2) {
            foundTable = true;
            const headerLine = tableLines[0];
            // Strip ** from column headers
            const columns = headerLine.split('|').map(c => stripBold(c.trim())).filter(Boolean);
            const dataLines = tableLines.slice(1).filter(l => !/^\|?\s*[-:]+\s*\|/.test(l) && !l.includes('---'));

            const rows = dataLines.map(line => {
              const cells = line.split('|').map(c => c.trim()).filter(Boolean);
              const rowObj: any = {};
              columns.forEach((col, idx) => {
                rowObj[col] = cells[idx] || 'N/A';
              });
              return rowObj;
            });

            if (columns.length > 0 && rows.length > 0) {
              segments.push({ type: 'table', content: JSON.stringify({ columns, rows }) });
            }
          }
        } else {
          // Non-table line within a pipe-containing block
          if (line.trim()) {
            segments.push({ type: 'paragraph', content: line.trim() });
          }
          i++;
        }
      }
      if (foundTable) continue;
    }

    // --- Bold paragraph (contains ** but is NOT a heading) ---
    if (block.includes('**')) {
      // Check if it's a "LABEL: description" pattern (like "COMMUNITY AS INFRASTRUCTURE: ...")
      const labelMatch = block.match(/^\*\*([^*]+)\*\*[:\s]+(.+)/s);
      if (labelMatch) {
        // Render as a heading + body
        segments.push({ type: 'heading', level: 3, content: labelMatch[1].trim() });
        segments.push({ type: 'paragraph', content: labelMatch[2].trim() });
        continue;
      }
      segments.push({ type: 'paragraph', content: block });
      continue;
    }

    // --- ALL-CAPS heading (like "EXECUTIVE SUMMARY: ..." or "CORE CONTENT PERFORMANCE METRICS") ---
    if (/^[A-Z][A-Z\s&:,\-–]+$/.test(block.trim()) && block.trim().length < 120) {
      segments.push({ type: 'heading', level: 2, content: block.trim() });
      continue;
    }

    // --- Plain paragraph ---
    segments.push({ type: 'paragraph', content: block });
  }

  return segments;
}
