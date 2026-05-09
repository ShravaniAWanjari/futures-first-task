/**
 * Formats pre-synthesized backend responses for display.
 * Full markdown parsing: headings, bold, bullets, horizontal rules, tables.
 */

export interface FormattedSegment {
  type: 'heading' | 'bullet-list' | 'bold-paragraph' | 'paragraph' | 'divider' | 'table';
  content: string;
  items?: string[];   // For bullet lists
  level?: number;     // For headings (2 or 3)
}

export function formatResponse(raw: string): FormattedSegment[] {
  if (!raw || !raw.trim()) {
    return [{ type: 'paragraph', content: 'No response available.' }];
  }

  const segments: FormattedSegment[] = [];

  // Split by double-newline into blocks
  const blocks = raw.split(/\n\n+/).map(b => b.trim()).filter(Boolean);

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
        content: headingMatch[2].trim(),
      });
      continue;
    }

    // --- Bullet List (lines starting with - or *) ---
    const lines = block.split('\n').map(l => l.trim()).filter(Boolean);
    const bulletLines = lines.filter(l => /^[-*•]\s+/.test(l));
    if (bulletLines.length >= 2 || (bulletLines.length === lines.length && bulletLines.length >= 1)) {
      // Extract bullet items, keep non-bullet lines as intro text
      const intro = lines.filter(l => !/^[-*•]\s+/.test(l)).join(' ');
      const items = bulletLines.map(l => l.replace(/^[-*•]\s+/, ''));
      if (intro) {
        segments.push({ type: 'bold-paragraph', content: intro });
      }
      segments.push({ type: 'bullet-list', content: '', items });
      continue;
    }

    // --- Mixed content: paragraph with inline bullets ---
    // If a single line has multiple " - " or " * " patterns, split them
    if (lines.length === 1 && (block.split(/\s[-*]\s/).length > 2)) {
      const parts = block.split(/\s[-*]\s/);
      const intro = parts[0];
      const items = parts.slice(1);
      if (intro) {
        segments.push({ type: 'bold-paragraph', content: intro });
      }
      if (items.length > 0) {
        segments.push({ type: 'bullet-list', content: '', items });
      }
      continue;
    }

    // --- Markdown Table Parser (Multi-table support) ---
    if (block.includes('|')) {
      const lines = block.split('\n');
      let i = 0;
      while (i < lines.length) {
        // Is this line a table row?
        if ((lines[i].match(/\|/g) || []).length >= 2) {
          // Find table block
          let tableLines = [];
          while (i < lines.length && (lines[i].match(/\|/g) || []).length >= 2) {
            tableLines.push(lines[i]);
            i++;
          }
          
          if (tableLines.length >= 2) {
            const headerLine = tableLines[0];
            const columns = headerLine.split('|').map(c => c.trim()).filter(Boolean);
            const dataLines = tableLines.slice(1).filter(l => !l.includes('---'));
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
          // Paragraph line
          if (lines[i].trim()) {
            segments.push({ type: 'paragraph', content: lines[i] });
          }
          i++;
        }
      }
      continue;
    }

    // --- Bold paragraph (contains **) ---
    if (block.includes('**')) {
      segments.push({ type: 'bold-paragraph', content: block });
      continue;
    }

    // --- Plain paragraph ---
    segments.push({ type: 'paragraph', content: block });
  }

  return segments;
}
