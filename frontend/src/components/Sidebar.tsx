import { useState, useEffect, useRef } from 'react';
import { Plus, Trash2, Pencil, Check, X, ChevronDown } from 'lucide-react';
import type { Session } from '../types';

interface SidebarProps {
  sessions: Session[];
  activeSessionId: string | null;
  workspace: string;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  onDeleteSession: (id: string) => void;
  onRenameSession: (title: string) => void;
  onChangeWorkspace: (ws: string) => void;
}

export default function Sidebar({
  sessions, activeSessionId, workspace,
  onSelectSession, onNewChat, onDeleteSession, onRenameSession, onChangeWorkspace,
}: SidebarProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [wsOpen, setWsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const currentWs = workspace === 'vistastream' ? 'VistaStream' : 'NeonPlay';

  // Close dropdown on outside click
  useEffect(() => {
    if (!wsOpen) return;
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setWsOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [wsOpen]);

  return (
    <aside style={{
      width: 256, height: '100vh', display: 'flex', flexDirection: 'column', flexShrink: 0,
      borderRight: '1px solid var(--color-border)', background: 'var(--color-sidebar-bg)',
    }}>
      {/* Brand */}
      <div style={{ padding: '18px 16px 12px', display: 'flex', alignItems: 'center', gap: 10 }}>
        <img src="/logo-iris-grey.png" alt="Iris Logo" style={{ height: 28, display: 'block' }} />
        <p style={{ fontSize: 21, fontWeight: 1000, color: '#424242', letterSpacing: '0.06em', margin: 0 }}>
          Iris.
        </p>
      </div>

      {/* Workspace Context */}
      <div style={{ padding: '8px 12px' }}>
        <p style={{ fontSize: 10, fontWeight: 600, color: 'var(--color-text-muted)', letterSpacing: '0.04em', textTransform: 'uppercase', padding: '0 4px', marginBottom: 4 }}>
          Workspace
        </p>
        <div style={{ position: 'relative' }} ref={dropdownRef}>
          <button
            onClick={() => setWsOpen(!wsOpen)}
            style={{
              width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '7px 8px', fontSize: 13, fontWeight: 500, borderRadius: 6,
              background: 'transparent', border: 'none',
              cursor: 'pointer', color: 'var(--color-text)',
              fontFamily: 'inherit',
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--color-primary-soft)'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
          >
            <span>{currentWs}</span>
            <ChevronDown style={{ width: 12, height: 12, color: 'var(--color-text-muted)', transform: wsOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }} />
          </button>
          {wsOpen && (
            <div className="animate-fade-in" style={{
              position: 'absolute', top: '100%', left: 0, right: 0, marginTop: 2, zIndex: 10,
              border: '1px solid var(--color-border)', borderRadius: 8, background: 'var(--color-surface)',
              overflow: 'hidden', boxShadow: '0 4px 16px rgba(0,0,0,0.07)',
            }}>
              {['vistastream', 'neonplay'].map(ws => (
                <button
                  key={ws}
                  onClick={() => { onChangeWorkspace(ws); setWsOpen(false); }}
                  style={{
                    width: '100%', padding: '8px 10px', fontSize: 13, textAlign: 'left',
                    background: workspace === ws ? 'var(--color-active)' : 'transparent',
                    color: 'var(--color-text)', fontWeight: workspace === ws ? 500 : 400,
                    border: 'none', cursor: 'pointer', fontFamily: 'inherit',
                    display: 'flex', flexDirection: 'column', gap: 1,
                  }}
                  onMouseEnter={e => { if (workspace !== ws) (e.currentTarget as HTMLElement).style.background = 'var(--color-primary-soft)'; }}
                  onMouseLeave={e => { if (workspace !== ws) (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                >
                  <span>{ws === 'vistastream' ? 'VistaStream Global' : 'NeonPlay Media'}</span>
                  <span style={{ fontSize: 10, color: 'var(--color-text-muted)', fontWeight: 400 }}>
                    {ws === 'vistastream' ? 'Clean Enterprise Input Data' : 'Messy Startup Input Data'}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* New conversation */}
      <div style={{ padding: '4px 12px 8px' }}>
        <button
          onClick={onNewChat}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', gap: 7,
            padding: '7px 8px', fontSize: 13, fontWeight: 500, borderRadius: 6,
            background: 'transparent', border: 'none',
            cursor: 'pointer', color: 'var(--color-text-secondary)', transition: 'all 0.1s',
            fontFamily: 'inherit',
          }}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--color-primary-soft)'; e.currentTarget.style.color = 'var(--color-text)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--color-text-secondary)'; }}
        >
          <Plus style={{ width: 14, height: 14 }} />
          New conversation
        </button>
      </div>

      {/* Separator */}
      <div style={{ height: 1, background: 'var(--color-border)', margin: '2px 14px' }} />

      {/* Sessions */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '8px 8px 16px' }}>
        {sessions.length === 0 && (
          <p style={{ fontSize: 12, color: 'var(--color-text-muted)', padding: '24px 8px', textAlign: 'center' }}>
            No conversations yet
          </p>
        )}
        {sessions.map(session => (
          <div
            key={session.id}
            className="group"
            style={{
              display: 'flex', alignItems: 'center', borderRadius: 6, padding: '5px 8px',
              cursor: 'pointer', marginBottom: 1, transition: 'background 0.08s',
              background: activeSessionId === session.id ? 'var(--color-active)' : 'transparent',
            }}
            onMouseEnter={e => { if (activeSessionId !== session.id) e.currentTarget.style.background = 'var(--color-primary-soft)'; }}
            onMouseLeave={e => { if (activeSessionId !== session.id) e.currentTarget.style.background = 'transparent'; }}
          >
            {editingId === session.id ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 3, flex: 1 }}>
                <input
                  value={editTitle}
                  onChange={e => setEditTitle(e.target.value)}
                  autoFocus
                  onKeyDown={e => {
                    if (e.key === 'Enter') { onRenameSession(editTitle); setEditingId(null); }
                    if (e.key === 'Escape') setEditingId(null);
                  }}
                  style={{ flex: 1, fontSize: 12, padding: '2px 6px', borderRadius: 4, border: '1px solid var(--color-border)', background: 'var(--color-surface)', outline: 'none', fontFamily: 'inherit' }}
                />
                <button onClick={() => { onRenameSession(editTitle); setEditingId(null); }} style={{ padding: 2, border: 'none', background: 'none', cursor: 'pointer', color: 'var(--color-success)' }}><Check style={{ width: 12, height: 12 }} /></button>
                <button onClick={() => setEditingId(null)} style={{ padding: 2, border: 'none', background: 'none', cursor: 'pointer', color: 'var(--color-text-muted)' }}><X style={{ width: 12, height: 12 }} /></button>
              </div>
            ) : (
              <>
                <button
                  onClick={() => onSelectSession(session.id)}
                  style={{
                    flex: 1, textAlign: 'left', fontSize: 13, overflow: 'hidden',
                    textOverflow: 'ellipsis', whiteSpace: 'nowrap', background: 'none',
                    border: 'none', cursor: 'pointer', padding: 0, fontFamily: 'inherit',
                    color: activeSessionId === session.id ? 'var(--color-text)' : 'var(--color-text-secondary)',
                    fontWeight: activeSessionId === session.id ? 500 : 400,
                  }}
                >
                  {session.title}
                </button>
                <div className="hidden group-hover:flex" style={{ alignItems: 'center', gap: 0, flexShrink: 0 }}>
                  <button
                    onClick={e => { e.stopPropagation(); setEditingId(session.id); setEditTitle(session.title); }}
                    style={{ padding: 3, border: 'none', background: 'none', cursor: 'pointer', color: 'var(--color-text-muted)' }}
                  ><Pencil style={{ width: 11, height: 11 }} /></button>
                  <button
                    onClick={e => { e.stopPropagation(); onDeleteSession(session.id); }}
                    style={{ padding: 3, border: 'none', background: 'none', cursor: 'pointer', color: 'var(--color-text-muted)' }}
                  ><Trash2 style={{ width: 11, height: 11 }} /></button>
                </div>
              </>
            )}
          </div>
        ))}
      </div>
    </aside>
  );
}
