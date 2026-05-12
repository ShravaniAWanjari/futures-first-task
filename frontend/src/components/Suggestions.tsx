import { useEffect, useState } from 'react';
import { ArrowRight } from 'lucide-react';
import * as api from '../services/api';

interface SuggestionsProps {
  workspace: string;
  onSelect: (query: string) => void;
}

export default function Suggestions({ workspace, onSelect }: SuggestionsProps) {
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.fetchSuggestions(workspace)
      .then(res => setSuggestions(res.suggestions))
      .catch(() => setSuggestions([]))
      .finally(() => setLoading(false));
  }, [workspace]);

  const workspaceTitle = workspace === 'vistastream' ? 'VistaStream Global' : 
                         workspace === 'neonplay' ? 'NeonPlay Media' : 
                         'Custom Input Analysis';

  return (
    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40 }}>
      <div className="animate-fade-in" style={{ maxWidth: 520, width: '100%', textAlign: 'center' }}>
        {/* Central Branding (Unified) */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, marginBottom: 8 }}>
          <img src="/logo-iris-grey.png" alt="Iris Logo" style={{ height: 42, display: 'block' }} />
          <p style={{ fontSize: 32, fontWeight: 1000, color: '#424242', letterSpacing: '0.06em', margin: 0 }}>
            Iris.
          </p>
        </div>
        
        {/* Workspace Context */}
        <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--color-text-secondary)', letterSpacing: '-0.02em', marginBottom: 6 }}>
          {workspaceTitle}
        </h2>
        
        <p style={{ fontSize: 14, color: 'var(--color-text-muted)', lineHeight: 1.5, marginBottom: workspace === 'custom' ? 32 : 32 }}>
          Ask about operational data, reports, and policy documents.
        </p>

        {workspace === 'custom' && (
          <div style={{ 
            marginTop: 0, padding: '24px', borderRadius: 12, 
            background: 'rgba(0,0,0,0.02)', border: '1px solid var(--color-border-subtle)',
            textAlign: 'left'
          }}>
            <p style={{ fontSize: 13, color: 'var(--color-text-secondary)', lineHeight: 1.6, marginBottom: 12 }}>
              <strong>Getting Started</strong>: Please add documents to the <code>docs/</code> directory to begin analysis. 
              If nothing is uploaded, Iris. cannot provide grounded insights.
            </p>
            <p style={{ fontSize: 12, color: 'var(--color-text-muted)', lineHeight: 1.5 }}>
              <span style={{ color: 'var(--color-success)', fontWeight: 600 }}>● Secure Data Flow</span>: 
              Your documents are safe. Data is processed via secure flows that separate private document inputs from LLM training sets.
            </p>
          </div>
        )}

        {/* Suggestions (Only for Enterprise Workspaces) */}
        {workspace !== 'custom' && (
          loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {[1,2,3,4].map(i => <div key={i} className="skeleton" style={{ height: 40 }} />)}
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {suggestions.map((s, i) => (
                <button
                  key={i}
                  onClick={() => onSelect(s)}
                  style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    textAlign: 'left', padding: '11px 12px', fontSize: 13.5, borderRadius: 8,
                    border: 'none', background: 'transparent',
                    color: 'var(--color-text-secondary)', cursor: 'pointer', transition: 'all 0.1s',
                    lineHeight: 1.45, fontFamily: 'inherit', gap: 12,
                  }}
                  onMouseEnter={e => { e.currentTarget.style.background = 'var(--color-primary-soft)'; e.currentTarget.style.color = 'var(--color-text)'; }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--color-text-secondary)'; }}
                >
                  <span>{s}</span>
                  <ArrowRight style={{ width: 14, height: 14, flexShrink: 0, opacity: 0.4 }} />
                </button>
              ))}
            </div>
          )
        )}
      </div>
    </div>
  );
}
