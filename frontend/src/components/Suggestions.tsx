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

  return (
    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40 }}>
      <div className="animate-fade-in" style={{ maxWidth: 520, width: '100%' }}>
        {/* Header */}
        <div style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 22, fontWeight: 600, color: 'var(--color-text)', letterSpacing: '-0.025em', marginBottom: 6 }}>
            {workspace === 'vistastream' ? 'VistaStream Global' : 'NeonPlay Media'}
          </h2>
          <p style={{ fontSize: 14, color: 'var(--color-text-muted)', lineHeight: 1.5 }}>
            Ask about operational data, reports, and policy documents.
          </p>
        </div>

        {/* Suggestions */}
        {loading ? (
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
        )}
      </div>
    </div>
  );
}
