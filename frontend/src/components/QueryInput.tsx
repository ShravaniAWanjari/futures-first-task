import { useState, useRef, useEffect } from 'react';
import { ArrowUp, Plus, X, Image as ImageIcon } from 'lucide-react';

interface QueryInputProps {
  onSend: (query: string, image?: string | null) => void;
  disabled: boolean;
}

export default function QueryInput({ onSend, disabled }: QueryInputProps) {
  const [value, setValue] = useState('');
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageBase64, setImageBase64] = useState<string | null>(null);
  const [showWarning, setShowWarning] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!disabled) inputRef.current?.focus();
  }, [disabled]);

  const handlePlusClick = () => {
    if (disabled) return;
    setShowWarning(true);
    // Auto-dismiss warning after 4 seconds
    setTimeout(() => setShowWarning(false), 4000);
    fileInputRef.current?.click();
  };

  const handleSubmit = () => {
    const trimmed = value.trim();
    if ((!trimmed && !imageBase64) || disabled) return;
    onSend(trimmed || 'Analyze this image', imageBase64);
    setValue('');
    setImagePreview(null);
    setImageBase64(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      return;
    }

    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      setImagePreview(result);
      // Strip the data:image/...;base64, prefix for the API
      setImageBase64(result);
    };
    reader.readAsDataURL(file);

    // Reset file input so the same file can be selected again
    e.target.value = '';
  };

  const removeImage = () => {
    setImagePreview(null);
    setImageBase64(null);
  };

  const canSend = (value.trim().length > 0 || !!imageBase64) && !disabled;

  return (
    <div style={{ padding: '10px 40px 28px', background: 'var(--color-bg)' }}>
      <div style={{
        maxWidth: 660, margin: '0 auto', position: 'relative',
        background: 'var(--color-surface)', borderRadius: 14,
        boxShadow: '0 0 0 1px var(--color-border), 0 1px 6px rgba(0,0,0,0.03), 0 3px 12px rgba(0,0,0,0.03)',
        transition: 'box-shadow 0.15s',
      }}>
        {/* Image Preview Strip */}
        {imagePreview && (
          <div style={{
            padding: '10px 14px 0', display: 'flex', alignItems: 'flex-start', gap: 8,
          }}>
            <div style={{ position: 'relative', display: 'inline-block' }}>
              <img
                src={imagePreview}
                alt="Upload preview"
                style={{
                  height: 64, maxWidth: 120, borderRadius: 8,
                  objectFit: 'cover', border: '1px solid var(--color-border)',
                }}
              />
              <button
                onClick={removeImage}
                style={{
                  position: 'absolute', top: -6, right: -6,
                  width: 18, height: 18, borderRadius: '50%',
                  background: 'var(--color-text)', color: '#fff',
                  border: 'none', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  padding: 0,
                }}
                aria-label="Remove image"
              >
                <X style={{ width: 10, height: 10 }} />
              </button>
            </div>
            <span style={{
              fontSize: 11, color: 'var(--color-text-muted)',
              padding: '4px 0', lineHeight: 1.4,
            }}>
              <ImageIcon style={{ width: 11, height: 11, display: 'inline', verticalAlign: 'middle', marginRight: 3 }} />
              Image attached
            </span>
          </div>
        )}

        <div style={{ display: 'flex', alignItems: 'flex-end' }}>
          {/* Plus / Image Upload Button */}
          <div style={{ position: 'relative', padding: '0 0 8px 8px' }}>
            <button
              onClick={handlePlusClick}
              disabled={disabled}
              style={{
                width: 32, height: 32, borderRadius: 8, border: 'none',
                cursor: disabled ? 'default' : 'pointer',
                background: 'transparent',
                color: 'var(--color-text-muted)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'all 0.12s',
                opacity: disabled ? 0.4 : 1,
              }}
              onMouseOver={e => { if (!disabled) e.currentTarget.style.color = 'var(--color-text)'; e.currentTarget.style.background = 'var(--color-primary-soft)'; }}
              onMouseOut={e => { e.currentTarget.style.color = 'var(--color-text-muted)'; e.currentTarget.style.background = 'transparent'; }}
              aria-label="Attach image"
            >
              <Plus style={{ width: 16, height: 16 }} />
            </button>
            
            {/* Schema Compatibility Warning */}
            {showWarning && !disabled && (
              <div className="animate-fade-in" style={{
                position: 'absolute', bottom: '100%', left: 0, 
                marginBottom: 12, width: 280, padding: '12px 14px', borderRadius: 10,
                background: '#fffbeb', border: '1px solid #fef3c7',
                color: '#92400e', fontSize: 12, lineHeight: 1.5,
                boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                zIndex: 50,
              }}>
                <div style={{ fontWeight: 600, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ fontSize: 14 }}>⚠️</span> Schema Compatibility
                </div>
                Ensure uploaded files have compatible schemas. Unrelated data structures may disrupt the conversation and result in inaccurate intelligence.
              </div>
            )}
          </div>

          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            style={{ display: 'none' }}
            onChange={handleFileSelect}
          />

          <textarea
            id="query-input"
            name="query"
            ref={inputRef}
            value={value}
            onChange={e => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            rows={1}
            placeholder={imageBase64 ? "Ask about this image…" : "Ask a question…"}
            style={{
              flex: 1, resize: 'none', border: 'none', outline: 'none',
              borderRadius: 14, padding: '14px 50px 14px 6px', fontSize: 14,
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
    </div>
  );
}
