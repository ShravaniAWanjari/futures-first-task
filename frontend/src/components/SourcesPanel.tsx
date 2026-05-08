import { useState } from 'react';
import { X, Clock, ChevronDown, ChevronRight } from 'lucide-react';
import type { QueryResponse } from '../types';

interface SourcesPanelProps {
  trace: QueryResponse['trace'] | null;
  open: boolean;
  onClose: () => void;
}

export default function SourcesPanel({ trace, open, onClose }: SourcesPanelProps) {
  if (!open || !trace) return null;

  const classification = trace.classification;
  const tools = trace.tool_executions;

  return (
    <div
      className="animate-fade-in"
      style={{
        width: 300, height: '100vh', borderLeft: '1px solid var(--color-border)',
        background: 'var(--color-surface)', flexShrink: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '13px 16px', borderBottom: '1px solid var(--color-border)',
      }}>
        <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text)' }}>Sources</h3>
        <button
          onClick={onClose}
          style={{ padding: 4, borderRadius: 4, border: 'none', background: 'none', cursor: 'pointer', color: 'var(--color-text-muted)' }}
          onMouseEnter={e => e.currentTarget.style.background = 'var(--color-primary-soft)'}
          onMouseLeave={e => e.currentTarget.style.background = 'none'}
        >
          <X style={{ width: 14, height: 14 }} />
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '14px 14px 20px', display: 'flex', flexDirection: 'column', gap: 12 }}>

        {/* Query Understanding */}
        <SourceSection title="Query Understanding">
          <InfoRow label="Category" value={classification.query_type} />
          <InfoRow label="Confidence" value={`${(classification.confidence * 100).toFixed(0)}%`} />
          <p style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 6, lineHeight: 1.55 }}>
            {classification.reasoning}
          </p>
        </SourceSection>

        {/* Tool results */}
        {tools.map((tool, i) => {
          const isSql = tool.tool === 'query_structured_data';
          return (
            <SourceSection key={i} title={isSql ? 'Structured Data' : 'Document Search'}>
              <InfoRow label="Status" value={tool.success ? 'Retrieved' : 'Unavailable'} />
              <InfoRow label="Response time" value={`${tool.timing_ms?.toFixed(0)}ms`} />

              {'table_references' in tool && (tool.table_references as string[])?.length > 0 && (
                <div style={{ marginTop: 6 }}>
                  <p style={{ fontSize: 11, color: 'var(--color-text-muted)', marginBottom: 4 }}>Referenced tables</p>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {(tool.table_references as string[]).map((t, j) => (
                      <span key={j} style={{ fontSize: 11, padding: '2px 7px', borderRadius: 4, background: 'var(--color-primary-soft)', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{t}</span>
                    ))}
                  </div>
                </div>
              )}

              {'n_results' in tool && <InfoRow label="Excerpts" value={String((tool as { n_results: number }).n_results)} />}

              {'query_used' in tool && tool.query_used && (
                <CollapsibleSQL sql={tool.query_used} />
              )}
            </SourceSection>
          );
        })}

        {/* Performance */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '8px 10px', fontSize: 11, color: 'var(--color-text-muted)',
          background: 'var(--color-surface-raised)', borderRadius: 6,
          border: '1px solid var(--color-border-subtle)',
        }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <Clock style={{ width: 11, height: 11 }} /> Total
          </span>
          <span style={{ fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>{trace.total_timing_ms?.toFixed(0)}ms</span>
        </div>
      </div>
    </div>
  );
}

function SourceSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 6, letterSpacing: '0.02em' }}>
        {title}
      </p>
      <div style={{
        background: 'var(--color-surface-raised)', border: '1px solid var(--color-border-subtle)',
        borderRadius: 8, padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 4,
      }}>
        {children}
      </div>
    </section>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, alignItems: 'center' }}>
      <span style={{ color: 'var(--color-text-muted)' }}>{label}</span>
      <span style={{ fontWeight: 500, color: 'var(--color-text)', textTransform: 'capitalize' }}>{value}</span>
    </div>
  );
}

function CollapsibleSQL({ sql }: { sql: string }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div style={{ marginTop: 6 }}>
      <button
        onClick={() => setExpanded(!expanded)}
        style={{
          display: 'flex', alignItems: 'center', gap: 3, fontSize: 11, fontWeight: 500,
          color: 'var(--color-text-muted)', background: 'none', border: 'none',
          cursor: 'pointer', padding: 0, fontFamily: 'inherit',
        }}
        onMouseEnter={e => e.currentTarget.style.color = 'var(--color-text-secondary)'}
        onMouseLeave={e => e.currentTarget.style.color = 'var(--color-text-muted)'}
      >
        {expanded ? <ChevronDown style={{ width: 11, height: 11 }} /> : <ChevronRight style={{ width: 11, height: 11 }} />}
        View query
      </button>
      {expanded && (
        <pre className="animate-fade-in" style={{
          fontSize: 10.5, background: 'var(--color-bg)', borderRadius: 5,
          padding: '8px 10px', overflowX: 'auto',
          fontFamily: '"SF Mono", "Fira Code", "Cascadia Code", monospace',
          color: 'var(--color-text-secondary)', marginTop: 4, lineHeight: 1.5,
          border: '1px solid var(--color-border)',
        }}>
          {sql}
        </pre>
      )}
    </div>
  );
}
