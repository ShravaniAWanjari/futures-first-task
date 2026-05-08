import type { Message } from '../types';
import { formatResponse, type FormattedSegment } from '../utils/formatResponse';

interface MessageBubbleProps {
  message: Message;
  onOpenSources?: (trace?: any) => void;
}

export default function MessageBubble({ message, onOpenSources }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  const handleOpenSources = () => {
    if (!onOpenSources) return;
    let traceData = null;
    if (message.trace) {
      try {
        traceData = typeof message.trace === 'string' ? JSON.parse(message.trace) : message.trace;
      } catch (e) {
        console.error('Failed to parse message trace', e);
      }
    }
    onOpenSources(traceData);
  };

  if (isUser) {
    return (
      <div className="animate-fade-in" style={{ marginBottom: 28 }}>
        <p style={{ fontSize: 14, lineHeight: 1.7, color: 'var(--color-text)' }}>
          {message.content}
        </p>
      </div>
    );
  }

  const segments = formatResponse(message.content);
  const hasSources = message.sources && message.sources.split(',').filter(Boolean).length > 0;
  const sourceCount = hasSources ? message.sources!.split(',').filter(Boolean).length : 0;

  return (
    <div className="animate-fade-in" style={{ marginBottom: 28, borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: 24 }}>
      {/* Rendered segments */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {segments.map((seg, i) => (
          <SegmentRenderer key={i} segment={seg} isFirst={i === 0} />
        ))}
      </div>

      {/* Supporting Sources link */}
      {hasSources && onOpenSources && (
        <button
          onClick={handleOpenSources}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            marginTop: 16, fontSize: 12, fontWeight: 500,
            color: 'var(--color-text-muted)', background: 'none', border: 'none',
            cursor: 'pointer', padding: '5px 0', fontFamily: 'inherit',
            transition: 'color 0.12s', letterSpacing: '0.01em',
          }}
          onMouseEnter={e => e.currentTarget.style.color = 'var(--color-text)'}
          onMouseLeave={e => e.currentTarget.style.color = 'var(--color-text-muted)'}
        >
          <span style={{
            minWidth: 18, height: 18, borderRadius: 4,
            background: 'var(--color-primary-soft)', display: 'inline-flex',
            alignItems: 'center', justifyContent: 'center',
            fontSize: 10, fontWeight: 700, color: 'var(--color-text-secondary)',
          }}>
            {sourceCount}
          </span>
          Supporting Sources
        </button>
      )}
    </div>
  );
}

function SegmentRenderer({ segment, isFirst }: { segment: FormattedSegment; isFirst: boolean }) {
  switch (segment.type) {
    case 'bold-paragraph':
      return (
        <div
          style={{
            fontSize: isFirst ? 14 : 13.5,
            lineHeight: 1.75,
            color: 'var(--color-text)',
          }}
          dangerouslySetInnerHTML={{
            __html: segment.content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>'),
          }}
        />
      );

    case 'retrieval':
      return (
        <div style={{
          borderLeft: '2px solid var(--color-border)',
          paddingLeft: 14,
          fontSize: 13, lineHeight: 1.7,
          color: 'var(--color-text-secondary)',
          fontStyle: 'normal',
        }}>
          {segment.content}
        </div>
      );

    case 'paragraph':
    default:
      return (
        <p style={{
          fontSize: isFirst ? 14 : 13.5,
          lineHeight: 1.75,
          color: isFirst ? 'var(--color-text)' : 'var(--color-text-secondary)',
        }}>
          {segment.content}
        </p>
      );
  }
}
