import { useState, useRef, useEffect } from 'react';
import { ArrowUp, Plus, X, Image as ImageIcon, FileText, AlertCircle } from 'lucide-react';

interface QueryInputProps {
  onSend: (query: string, image?: string | null) => void;
  disabled: boolean;
  workspace: string;
}

export default function QueryInput({ onSend, disabled, workspace }: QueryInputProps) {
  const [value, setValue] = useState('');
  const [filePreview, setFilePreview] = useState<{ type: 'image' | 'doc', url: string, name: string } | null>(null);
  const [fileBase64, setFileBase64] = useState<string | null>(null);
  const [showWarning, setShowWarning] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!disabled) inputRef.current?.focus();
  }, [disabled]);

  const handlePlusClick = () => {
    if (disabled) return;
    fileInputRef.current?.click();
  };

  const handleSubmit = () => {
    const trimmed = value.trim();
    if ((!trimmed && !fileBase64) || disabled) return;
    onSend(trimmed || (filePreview?.type === 'image' ? 'Analyze this image' : 'Analyze this document'), fileBase64);
    setValue('');
    setFilePreview(null);
    setFileBase64(null);
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

    const isImage = file.type.startsWith('image/');
    const isDoc = file.type === 'application/pdf' || file.type === 'text/csv';

    // Enforcement: Only images for enterprise, docs allowed for custom
    if (workspace !== 'custom' && !isImage) {
      alert("Only image uploads are permitted in enterprise workspaces.");
      return;
    }

    // Validate file size
    const maxSize = isImage ? 10 * 1024 * 1024 : 5 * 1024 * 1024; // 10MB image, 5MB doc
    if (file.size > maxSize) {
      alert(`File is too large. Max size is ${maxSize / (1024 * 1024)}MB.`);
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      setFilePreview({ 
        type: isImage ? 'image' : 'doc', 
        url: isImage ? result : '', 
        name: file.name 
      });
      setFileBase64(result);
    };
    reader.readAsDataURL(file);

    e.target.value = '';
  };

  const removeFile = () => {
    setFilePreview(null);
    setFileBase64(null);
  };

  const canSend = (value.trim().length > 0 || !!fileBase64) && !disabled;

  // Determine accepted file types
  const acceptTypes = workspace === 'custom' ? "image/*,application/pdf,text/csv" : "image/*";

  return (
    <div style={{ padding: '10px 40px 28px', background: 'var(--color-bg)' }}>
      <div style={{
        maxWidth: 660, margin: '0 auto', position: 'relative',
        background: 'var(--color-surface)', borderRadius: 14,
        boxShadow: '0 0 0 1px var(--color-border), 0 1px 6px rgba(0,0,0,0.03), 0 3px 12px rgba(0,0,0,0.03)',
        transition: 'box-shadow 0.15s',
      }}>
        {/* Attachment Preview Strip */}
        {filePreview && (
          <div style={{
            padding: '10px 14px 0', display: 'flex', alignItems: 'flex-start', gap: 8,
          }}>
            <div style={{ position: 'relative', display: 'inline-block' }}>
              {filePreview.type === 'image' ? (
                <img
                  src={filePreview.url}
                  alt="Upload preview"
                  style={{
                    height: 64, maxWidth: 120, borderRadius: 8,
                    objectFit: 'cover', border: '1px solid var(--color-border)',
                  }}
                />
              ) : (
                <div style={{
                  height: 64, width: 80, borderRadius: 8,
                  background: 'var(--color-primary-soft)', border: '1px solid var(--color-border)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <FileText style={{ width: 32, height: 32, color: 'var(--color-primary)' }} />
                </div>
              )}
              <button
                onClick={removeFile}
                style={{
                  position: 'absolute', top: -6, right: -6,
                  width: 18, height: 18, borderRadius: '50%',
                  background: 'var(--color-text)', color: '#fff',
                  border: 'none', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  padding: 0,
                }}
                aria-label="Remove attachment"
              >
                <X style={{ width: 10, height: 10 }} />
              </button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2, padding: '4px 0' }}>
              <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-text)' }}>
                {filePreview.name.length > 25 ? filePreview.name.substring(0, 22) + '...' : filePreview.name}
              </span>
              <span style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>
                {filePreview.type === 'image' ? 'Image attached' : 'Document attached'}
              </span>
            </div>
          </div>
        )}

        <div style={{ display: 'flex', alignItems: 'flex-end' }}>
          {/* Plus / Upload Button */}
          <div style={{ position: 'relative', padding: '0 0 8px 8px' }}>
            <button
              onClick={handlePlusClick}
              disabled={disabled}
              onMouseEnter={() => { if (workspace === 'custom') setShowWarning(true); }}
              onMouseLeave={() => setShowWarning(false)}
              style={{
                width: 32, height: 32, borderRadius: 8, border: 'none',
                cursor: disabled ? 'default' : 'pointer',
                background: 'transparent',
                color: 'var(--color-text-muted)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'all 0.12s',
                opacity: disabled ? 0.4 : 1,
              }}
              aria-label="Attach file"
            >
              <Plus style={{ width: 16, height: 16 }} />
            </button>
            
            {/* Schema Compatibility Warning (Hover Only) */}
            {showWarning && workspace === 'custom' && !disabled && (
              <div className="animate-fade-in" style={{
                position: 'absolute', bottom: '100%', left: 0, 
                marginBottom: 12, width: 280, padding: '14px 16px', borderRadius: 12,
                background: '#ffffff', border: '1px solid var(--color-border)',
                color: 'var(--color-text)', fontSize: 12, lineHeight: 1.5,
                boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
                zIndex: 50, pointerEvents: 'none',
              }}>
                <div style={{ fontWeight: 600, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 8, color: 'var(--color-warning)' }}>
                  <AlertCircle style={{ width: 14, height: 14 }} /> Schema Compatibility
                </div>
                Ensure uploaded files (PDF/CSV) have compatible structures. Incompatible data may result in analytical hallucinations or reasoning errors.
              </div>
            )}
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept={acceptTypes}
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
            placeholder={fileBase64 ? "Ask about this attachment…" : "Ask a question…"}
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
