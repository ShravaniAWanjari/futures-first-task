import type { Message } from '../types';
import { formatResponse, type FormattedSegment } from '../utils/formatResponse';
import { DataTable, DataChart, KPICard, InlineChart } from './AnalyticalComponents';

interface MessageBubbleProps {
  message: Message;
  onOpenSources?: (trace?: any, context?: string) => void;
}

/**
 * Converts markdown bold markers to HTML strong tags
 */
function boldToHtml(s: string): string {
  return s.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
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
    onOpenSources(traceData, message.context || undefined);
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

  // Parse Analytical Data
  let structured = null;
  if (message.structured_data) {
    try {
      structured = typeof message.structured_data === 'string' 
        ? JSON.parse(message.structured_data) 
        : message.structured_data;
      console.log('[MessageBubble] Structured Data:', structured);
    } catch (e) {
      console.error('[MessageBubble] Failed to parse structured data', e);
    }
  }

  const segments = formatResponse(message.content);
  const hasSources = message.sources && message.sources.split(',').filter(Boolean).length > 0;
  const sourceCount = hasSources ? message.sources!.split(',').filter(Boolean).length : 0;

  return (
    <div className="animate-fade-in" style={{ marginBottom: 32, borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: 28 }}>
      {/* Executive Header if structured data exists */}
      {structured && structured.title && (
        <div style={{ marginBottom: 20 }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--color-text)', marginBottom: 8, letterSpacing: '-0.02em' }}>
            {structured.title}
          </h2>
          {structured.response_type && (
            <span style={{ 
              fontSize: 10, 
              fontWeight: 700, 
              background: 'var(--color-primary-soft)', 
              color: 'var(--color-text-secondary)', 
              padding: '2px 8px', 
              borderRadius: '4px',
              textTransform: 'uppercase',
              letterSpacing: '0.05em'
            }}>
              {structured.response_type.replace(/_/g, ' ')}
            </span>
          )}
        </div>
      )}

      {/* Structured KPIs & Visualization */}
      {structured && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20, marginBottom: 24 }}>
          {structured.kpi && (
            <KPICard 
              label={structured.kpi.label} 
              value={structured.kpi.value} 
              context={structured.kpi.context} 
            />
          )}
          
          {structured.chart && (
            <DataChart 
              type={structured.chart.type} 
              labels={structured.chart.labels} 
              values={structured.chart.values} 
              label={structured.chart.label}
            />
          )}

          {structured.table && structured.response_type === 'table_response' && (
            <DataTable 
              columns={structured.table.columns} 
              rows={structured.table.rows} 
            />
          )}
        </div>
      )}

      {/* Narrative segments */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {segments.map((seg, i) => (
          <SegmentRenderer key={i} segment={seg} isFirst={i === 0 && !structured} />
        ))}
      </div>

      {/* Tables for analysis if not already shown as primary */}
      {structured && structured.table && structured.response_type !== 'table_response' && (
        <div style={{ marginTop: 24 }}>
          <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 8 }}>
            DATA BREAKDOWN
          </p>
          <DataTable 
            columns={structured.table.columns} 
            rows={structured.table.rows.slice(0, 5)} 
          />
        </div>
      )}

      {/* Supporting Sources link */}
      {hasSources && onOpenSources && (
        <button
          onClick={handleOpenSources}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            marginTop: 20, fontSize: 12, fontWeight: 500,
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
          Analysis & Supporting Sources
        </button>
      )}
    </div>
  );
}

function SegmentRenderer({ segment, isFirst }: { segment: FormattedSegment; isFirst: boolean }) {
  switch (segment.type) {
    case 'table': {
      const { columns, rows } = JSON.parse(segment.content);
      return (
        <div>
          <DataTable columns={columns} rows={rows} />
          <InlineChart columns={columns} rows={rows} />
        </div>
      );
    }

    case 'heading':
      return (
        <div style={{
          fontSize: segment.level === 2 ? 16 : 14,
          fontWeight: 700,
          color: 'var(--color-text)',
          margin: 0,
          marginTop: isFirst ? 0 : 24,
          marginBottom: 8,
          letterSpacing: '-0.01em',
          textTransform: segment.level === 2 ? 'uppercase' as const : 'none' as const,
          ...(segment.level === 2 ? { 
            fontSize: 12, 
            letterSpacing: '0.08em', 
            opacity: 0.6,
            borderBottom: '1px solid var(--color-border-subtle)',
            paddingBottom: 8,
          } : {}),
        }}>
          {segment.content}
        </div>
      );

    case 'callout':
      return (
        <div style={{
          margin: '16px 0',
          padding: '16px 20px',
          background: 'rgba(255, 255, 255, 0.02)',
          borderLeft: '3px solid var(--color-text)',
          borderRadius: '0 12px 12px 0',
          fontSize: 13.5,
          lineHeight: 1.7,
          color: 'var(--color-text)',
          fontWeight: 500,
        }}
        dangerouslySetInnerHTML={{ __html: boldToHtml(segment.content) }}
        />
      );

    case 'bullet-list':
      return (
        <ul style={{
          margin: '4px 0',
          paddingLeft: 20,
          display: 'flex',
          flexDirection: 'column',
          gap: 6,
        }}>
          {segment.items?.map((item, idx) => (
            <li
              key={idx}
              style={{
                fontSize: 13.5,
                lineHeight: 1.7,
                color: 'var(--color-text-secondary)',
              }}
              dangerouslySetInnerHTML={{
                __html: boldToHtml(item),
              }}
            />
          ))}
        </ul>
      );

    case 'divider':
      return (
        <hr style={{
          border: 'none',
          borderTop: '1px solid var(--color-border-subtle)',
          margin: '16px 0',
        }} />
      );

    case 'bold-paragraph':
      return (
        <div
          style={{
            fontSize: 14,
            lineHeight: 1.7,
            color: 'var(--color-text)',
            marginBottom: 8,
          }}
          dangerouslySetInnerHTML={{
            __html: boldToHtml(segment.content),
          }}
        />
      );

    case 'paragraph':
    default:
      return (
        <p 
          style={{
            fontSize: isFirst ? 14 : 13.5,
            lineHeight: 1.75,
            color: isFirst ? 'var(--color-text)' : 'var(--color-text-secondary)',
            margin: 0,
            marginBottom: 8,
          }}
          dangerouslySetInnerHTML={{
            __html: boldToHtml(segment.content),
          }}
        />
      );
  }
}
