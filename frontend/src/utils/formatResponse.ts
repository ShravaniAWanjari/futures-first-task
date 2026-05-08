/**
 * Formats pre-synthesized backend responses for display.
 * The heavy synthesis now happens server-side; this handles
 * markdown rendering and structural presentation.
 */

export interface FormattedSegment {
  type: 'paragraph' | 'bold-paragraph' | 'retrieval';
  title?: string;
  content: string;
}

export function formatResponse(raw: string): FormattedSegment[] {
  if (!raw || !raw.trim()) {
    return [{ type: 'paragraph', content: 'No response available.' }];
  }

  const segments: FormattedSegment[] = [];

  // Split by double-newline into paragraphs
  const paragraphs = raw.split(/\n\n+/).map(p => p.trim()).filter(Boolean);

  for (const para of paragraphs) {
    // Check if this is a retrieval attribution
    if (para.startsWith('Based on available documentation:') || para.startsWith('Supporting documentation indicates:')) {
      segments.push({
        type: 'retrieval',
        content: para,
      });
    } else if (para.includes('**')) {
      // Has bold markers — treat as primary insight
      segments.push({
        type: 'bold-paragraph',
        content: para,
      });
    } else {
      segments.push({
        type: 'paragraph',
        content: para,
      });
    }
  }

  return segments;
}
