import { useState, useRef, useEffect } from 'react';
import { ArrowUp } from 'lucide-react';

interface QueryInputProps {
  onSend: (query: string) => void;
  disabled: boolean;
}

export default function QueryInput({ onSend, disabled }: QueryInputProps) {
  const [value, setValue] = useState('');
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!disabled) inputRef.current?.focus();
  }, [disabled]);

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const canSend = value.trim().length > 0 && !disabled;

  return (
    <div style={{ padding: '10px 40px 28px', background: 'var(--color-bg)' }}>
      <div style={{
        maxWidth: 660, margin: '0 auto', position: 'relative',
        background: 'var(--color-surface)', borderRadius: 14,
        boxShadow: '0 0 0 1px var(--color-border), 0 1px 6px rgba(0,0,0,0.03), 0 3px 12px rgba(0,0,0,0.03)',
        transition: 'box-shadow 0.15s',
      }}>
        <textarea
          ref={inputRef}
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={1}
          placeholder="Ask a question…"
          style={{
            width: '100%', resize: 'none', border: 'none', outline: 'none',
            borderRadius: 14, padding: '14px 50px 14px 18px', fontSize: 14,
            background: 'transparent', color: 'var(--color-text)', fontFamily: 'inherit',
            minHeight: 48, maxHeight: 140, lineHeight: 1.5,
            opacity: disabled ? 0.5 : 1,
          }}
        />
        <button
          onClick={handleSubmit}
          disabled={!canSend}
          style={{
            position: 'absolute', right: 8, bottom: 8,
            width: 32, height: 32, borderRadius: 8, border: 'none',
            cursor: canSend ? 'pointer' : 'default',
            background: canSend ? 'var(--color-primary)' : 'var(--color-border)',
            color: canSend ? '#fff' : 'var(--color-text-muted)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'all 0.12s',
          }}
          onMouseEnter={e => { if (canSend) e.currentTarget.style.background = 'var(--color-primary-hover)'; }}
          onMouseLeave={e => { if (canSend) e.currentTarget.style.background = 'var(--color-primary)'; }}
          aria-label="Send message"
        >
          <ArrowUp style={{ width: 15, height: 15 }} />
        </button>
      </div>
    </div>
  );
}
