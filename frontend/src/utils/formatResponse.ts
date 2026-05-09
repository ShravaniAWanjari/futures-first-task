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

    // --- Markdown Table ---
    if (block.includes('|') && block.includes('---')) {
      const lines = block.split('\n').map(l => l.trim()).filter(Boolean);
      // Find the header row (usually the first line with pipes)
      const headerIdx = lines.findIndex(l => l.startsWith('|') && l.endsWith('|'));
      const sepIdx = lines.findIndex(l => l.includes('|') && l.includes('---'));
      
      if (headerIdx !== -1 && sepIdx !== -1) {
        const columns = lines[headerIdx].split('|').map(c => c.trim()).filter(Boolean);
        const rows = lines.slice(sepIdx + 1).map(line => {
          const cells = line.split('|').map(c => c.trim()).filter(Boolean);
          const rowObj: any = {};
          columns.forEach((col, i) => {
            rowObj[col] = cells[i] || '';
          });
          return rowObj;
        });

        segments.push({ 
          type: 'table', 
          content: JSON.stringify({ columns, rows }) 
        });
        continue;
      }
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
