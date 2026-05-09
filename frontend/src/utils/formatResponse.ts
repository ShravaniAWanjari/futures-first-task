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

    // --- Markdown Table (Multi-table support) ---
    if (block.includes('|')) {
      const lines = block.split('\n');
      let currentIdx = 0;
      
      while (currentIdx < lines.length) {
        const tableStartIdx = lines.findIndex((l, i) => i >= currentIdx && (l.match(/\|/g) || []).length >= 2);
        
        if (tableStartIdx === -1) {
          // No more tables, add remaining lines as paragraph
          const remainingLines = lines.slice(currentIdx).filter(l => l.trim());
          if (remainingLines.length > 0) {
            segments.push({ type: 'paragraph', content: remainingLines.join('\n') });
          }
          break;
        }

        // Add text before this table
        const introLines = lines.slice(currentIdx, tableStartIdx).filter(l => l.trim());
        if (introLines.length > 0) {
          segments.push({ type: 'paragraph', content: introLines.join('\n') });
        }

        // Find table end
        let tableEndIdx = tableStartIdx;
        while (tableEndIdx < lines.length && (lines[tableEndIdx].match(/\|/g) || []).length >= 2) {
          tableEndIdx++;
        }

        const tableLines = lines.slice(tableStartIdx, tableEndIdx);
        const headerLine = tableLines[0];
        const columns = headerLine.split('|').map(c => c.trim()).filter(Boolean);
        const dataRows = tableLines.slice(1).filter(l => !l.includes('---'));
        
        const rows = dataRows.map(line => {
          const cells = line.split('|').map(c => c.trim()).filter(Boolean);
          const rowObj: any = {};
          columns.forEach((col, i) => {
            rowObj[col] = cells[i] || 'N/A';
          });
          return rowObj;
        });

        if (columns.length > 0 && rows.length > 0) {
          segments.push({ 
            type: 'table', 
            content: JSON.stringify({ columns, rows }) 
          });
        }

        currentIdx = tableEndIdx;
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
