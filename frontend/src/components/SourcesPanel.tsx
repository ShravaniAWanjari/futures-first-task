import { useState } from 'react';
import { X, Clock, ChevronDown, ChevronRight } from 'lucide-react';
import type { QueryResponse } from '../types';

interface SourcesPanelProps {
  trace: QueryResponse['trace'] | null;
  context?: string;
  open: boolean;
  onClose: () => void;
}

export default function SourcesPanel({ trace, context, open, onClose }: SourcesPanelProps) {
  if (!open || !trace) return null;

  const classification = trace.classification;
  const tools = trace.tool_executions;
  const rawReasoningText = buildRawReasoningText(trace, context);

  return (
    <div
      className="animate-fade-in"
      style={{
        width: 320, height: '100vh', borderLeft: '1px solid var(--color-border)',
        background: 'var(--color-surface)', flexShrink: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden',
        boxShadow: '-4px 0 24px rgba(0,0,0,0.1)'
      }}
    >
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '16px 20px', borderBottom: '1px solid var(--color-border)',
      }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--color-text)', letterSpacing: '-0.01em' }}>Data Lineage</h3>
        <button
          onClick={onClose}
          style={{ padding: 6, borderRadius: 6, border: 'none', background: 'none', cursor: 'pointer', color: 'var(--color-text-muted)' }}
          onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
          onMouseLeave={e => e.currentTarget.style.background = 'none'}
        >
          <X style={{ width: 16, height: 16 }} />
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* Query Understanding */}
        <SourceSection title="Intent Classification">
          <InfoRow label="Type" value={classification.query_type} />
          <InfoRow label="Confidence" value={`${(classification.confidence * 100).toFixed(0)}%`} />
          <p style={{ fontSize: 12, color: 'var(--color-text-secondary)', marginTop: 8, lineHeight: 1.6, fontStyle: 'italic' }}>
            "{classification.reasoning}"
          </p>
        </SourceSection>

        {/* Raw Reasoning (from context) */}
        {rawReasoningText && (
          <SourceSection title="Raw Reasoning" noBorder>
            <div style={{ 
              fontSize: 11, 
              color: '#4b5563', 
              lineHeight: 1.6, 
              maxHeight: 280, 
              overflowY: 'auto',
              background: '#e5e7eb',
              padding: '14px 16px',
              borderRadius: '8px',
              fontFamily: '"SF Mono", "Fira Code", "Cascadia Code", monospace',
              border: '1px solid #d1d5db',
              whiteSpace: 'pre-wrap',
              boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.05)',
              letterSpacing: '-0.01em'
            }}>
              {rawReasoningText}
            </div>
          </SourceSection>
        )}

        {/* Tool results */}
        {tools.map((tool, i) => (
          <SourceSection key={i} title={tool.tool === 'query_structured_data' ? 'Structured Access' : 'Semantic Retrieval'}>
            <InfoRow label="Outcome" value={tool.success ? 'Success' : 'Failed'} />
            <InfoRow label="Latency" value={`${tool.timing_ms?.toFixed(0)}ms`} />

            {'table_references' in tool && (tool.table_references as string[])?.length > 0 && (
              <div style={{ marginTop: 10 }}>
                <p style={{ fontSize: 10, fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 6, textTransform: 'uppercase' }}>Accessed Tables</p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {(tool.table_references as string[]).map((t, j) => (
                    <span key={j} style={{ fontSize: 11, padding: '3px 8px', borderRadius: 4, background: 'var(--color-border-subtle)', color: 'var(--color-text)', fontWeight: 500, border: '1px solid var(--color-border)' }}>{t}</span>
                  ))}
                </div>
              </div>
            )}

            {'n_results' in tool && (
               <div style={{ marginTop: 6 }}>
                 <InfoRow label="Matches" value={String((tool as { n_results: number }).n_results)} />
               </div>
            )}

            {'query_used' in tool && tool.query_used && (
              <CollapsibleSQL sql={tool.query_used} />
            )}
          </SourceSection>
        ))}

        {/* Performance Summary */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '12px 16px', fontSize: 11, color: 'var(--color-text-muted)',
          background: 'rgba(255,255,255,0.02)', borderRadius: 8,
          border: '1px solid var(--color-border)',
        }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Clock style={{ width: 14, height: 14 }} /> Total Process Time
          </span>
          <span style={{ fontWeight: 700, fontVariantNumeric: 'tabular-nums', color: 'var(--color-text)' }}>{trace.total_timing_ms?.toFixed(0)}ms</span>
        </div>
      </div>
    </div>
  );
}

function buildRawReasoningText(trace: QueryResponse['trace'], context?: string): string {
  const classification = trace.classification;
  const cleanContext = (context || '').trim();
  const cleanReasoning = (classification.reasoning || '').trim();

  // If backend already returned rich reasoning, use it as-is.
  if (cleanContext && cleanContext.length > 220) return cleanContext;
  if (cleanContext && cleanContext !== cleanReasoning) return cleanContext;

  // Frontend fallback for sparse/older payloads.
  const lines: string[] = [];
  lines.push('=== ORCHESTRATION REASONING ===');
  lines.push(`Route: ${classification.query_type} (confidence: ${classification.confidence.toFixed(2)})`);
  if (cleanReasoning) {
    lines.push(`Classifier rationale: ${cleanReasoning}`);
  }

  if ('intent' in classification && classification.intent) {
    lines.push(`Intent: ${String(classification.intent)}`);
  }
  if ('routing_plan' in classification && classification.routing_plan) {
    lines.push(`Routing plan: ${String(classification.routing_plan)}`);
  }

  trace.tool_executions.forEach((tool, i) => {
    const toolName = 'tool' in tool ? String(tool.tool) : 'unknown';
    const success = 'success' in tool ? String(tool.success) : 'false';
    const latency = 'timing_ms' in tool ? String(tool.timing_ms) : 'n/a';
    lines.push(`[Tool ${i + 1}] ${toolName} | success=${success} | latency=${latency}ms`);
    if ('n_results' in tool) {
      lines.push(`  retrieval: n_results=${String(tool.n_results)}`);
    }
    if ('query_used' in tool && tool.query_used) {
      lines.push(`  sql: ${tool.query_used}`);
    }
  });

  return lines.join('\n');
}

function SourceSection({ title, children, noBorder }: { title: string; children: React.ReactNode; noBorder?: boolean }) {
  return (
    <section>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <div style={{ height: '1px', flex: 1, background: 'var(--color-border-subtle)' }} />
        <p style={{ fontSize: 10, fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          {title}
        </p>
        <div style={{ height: '1px', flex: 1, background: 'var(--color-border-subtle)' }} />
      </div>
      <div style={{
        background: noBorder ? 'transparent' : 'rgba(255,255,255,0.01)', 
        border: noBorder ? 'none' : '1px solid var(--color-border-subtle)',
        borderRadius: 12, padding: noBorder ? '0' : '16px', display: 'flex', flexDirection: 'column', gap: 8,
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
