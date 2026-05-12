import type { Message } from '../types';
import { formatResponse, type FormattedSegment } from '../utils/formatResponse';
import { DataTable, KPICard, SimpleBarChart, SimpleLineChart, SimplePieChart } from './AnalyticalComponents';

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

interface ChartRendererProps {
  chart: any;
}

const ChartRenderer: React.FC<ChartRendererProps> = ({ chart }) => {
  return (
    <>
      {chart.type === 'bar' && (
        <SimpleBarChart 
          title={chart.title} 
          data={chart.data} 
          labels={chart.labels}
          values={chart.values}
        />
      )}
      {chart.type === 'line' && (
        <SimpleLineChart 
          title={chart.title} 
          data={chart.data} 
          labels={chart.labels}
          values={chart.values}
        />
      )}
      {chart.type === 'pie' && (
        <SimplePieChart 
          title={chart.title} 
          data={chart.data} 
          labels={chart.labels}
          values={chart.values}
        />
      )}
    </>
  );
};

import { FileText } from 'lucide-react';

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
    const isImage = message.image && message.image.startsWith('data:image/');

    return (
      <div className="animate-fade-in" style={{ marginBottom: 28 }}>
        {message.image && (
          <div style={{ marginBottom: 12 }}>
            {isImage ? (
              <img
                src={message.image}
                alt={message.file_name || "User uploaded"}
                style={{
                  maxHeight: 180, maxWidth: 320, borderRadius: 10,
                  objectFit: 'cover',
                  border: '1px solid var(--color-border)',
                }}
              />
            ) : (
              <div style={{
                display: 'inline-flex', alignItems: 'center', gap: 12,
                padding: '12px 16px', background: 'var(--color-surface)',
                borderRadius: 12, border: '1px solid var(--color-border)',
                boxShadow: '0 2px 4px rgba(0,0,0,0.02)',
              }}>
                <div style={{
                  width: 36, height: 36, borderRadius: 8,
                  background: 'var(--color-primary-soft)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <FileText style={{ width: 20, height: 20, color: 'var(--color-primary)' }} />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text)' }}>
                    {message.file_name || "Document attached"}
                  </span>
                  <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
                    {message.image.includes('pdf') ? 'PDF Document' : 'CSV Spreadsheet'}
                  </span>
                </div>
              </div>
            )}
          </div>
        )}
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
  const narrativeSegments = structured?.table
    ? segments.filter((seg) => seg.type !== 'table')
    : segments;
  const hasSources = message.sources && message.sources.split(',').filter(Boolean).length > 0;
  const sourceCount = hasSources ? message.sources!.split(',').filter(Boolean).length : 0;
  const charts = structured
    ? (Array.isArray(structured.charts) && structured.charts.length > 0
        ? structured.charts
        : (structured.chart ? [structured.chart] : []))
    : [];

  return (
    <div className="animate-fade-in" style={{ marginBottom: 32, borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: 28 }}>
      {/* Executive Header if structured data exists */}
      {structured && structured.title && (
        <div style={{ marginBottom: 20 }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--color-text)', marginBottom: 8, letterSpacing: '-0.02em' }}>
            {structured.title}
          </h2>
          {/* response_type is internal, no need to show it */}
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
          
          {structured.table && (
            <DataTable 
              columns={structured.table.columns} 
              rows={structured.table.rows} 
            />
          )}

          {charts.map((c: any, ci: number) => (
            <ChartRenderer key={ci} chart={c} />
          ))}
        </div>
      )}

      {/* Narrative segments */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {narrativeSegments.map((seg, i) => (
          <SegmentRenderer key={i} segment={seg} isFirst={i === 0 && !structured} />
        ))}
      </div>



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
        </div>
      );
    }

    case 'heading':
      return (
        <div style={{
          fontSize: segment.level === 2 ? 18 : 15,
          fontWeight: 700,
          color: 'var(--color-text)',
          margin: 0,
          marginTop: isFirst ? 0 : 32,
          marginBottom: 12,
          letterSpacing: '-0.02em',
          ...(segment.level === 2 ? { 
            borderLeft: '4px solid var(--color-primary)',
            paddingLeft: 12,
            lineHeight: 1.2,
          } : {
            lineHeight: 1.4,
          }),
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
          listStyleType: 'disc',
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
