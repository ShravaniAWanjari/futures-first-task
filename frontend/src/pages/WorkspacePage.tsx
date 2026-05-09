import { useState, useEffect, useCallback, useRef } from 'react';
import { useSessions } from '../hooks/useSessions';
import Sidebar from '../components/Sidebar';
import ChatPanel from '../components/ChatPanel';
import QueryInput from '../components/QueryInput';
import Suggestions from '../components/Suggestions';
import SourcesPanel from '../components/SourcesPanel';

export default function WorkspacePage() {
  const {
    sessions, activeSession, loading, queryLoading, workspace, lastTrace, lastContext, health,
    loadSessions, loadSession, createSession, removeSession,
    renameActiveSession, sendMessage, setWorkspace,
  } = useSessions();

  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [selectedTrace, setSelectedTrace] = useState(lastTrace);
  const [selectedContext, setSelectedContext] = useState<string | undefined>();

  // Sync selectedTrace with lastTrace on new messages
  useEffect(() => {
    if (lastTrace) {
      setSelectedTrace(lastTrace);
      // Don't auto-update context from lastTrace as context comes from the message click
    }
  }, [lastTrace]);

  const isInitialMount = useRef(true);
  const prevWorkspace = useRef(workspace);

  useEffect(() => {
    // Auto-initialize session: stay on current if reloading, otherwise create new
    const workspaceChanged = prevWorkspace.current !== workspace;
    
    if ((isInitialMount.current || workspaceChanged) && !activeSession && !loading) {
      const persistedSessionId = sessionStorage.getItem('activeSessionId');
      
      if (persistedSessionId && !workspaceChanged) {
        loadSession(persistedSessionId);
      } else {
        createSession();
      }
      
      isInitialMount.current = false;
      prevWorkspace.current = workspace;
    }
  }, [activeSession, loading, createSession, loadSession, workspace]);

  // Persist active session ID for reloads
  useEffect(() => {
    if (activeSession?.id) {
      sessionStorage.setItem('activeSessionId', activeSession.id);
    }
  }, [activeSession]);

  const openSources = useCallback((trace?: any, context?: string) => {
    if (trace) {
      setSelectedTrace(trace);
      setSelectedContext(context);
      setSourcesOpen(true);
    } else if (selectedTrace) {
      setSourcesOpen(true);
    }
  }, [selectedTrace]);

  const handleNewChat = useCallback(() => {
    createSession();
    setSourcesOpen(false);
    setSelectedContext(undefined);
  }, [createSession]);

  const handleSuggestionSelect = useCallback(async (query: string) => {
    if (queryLoading) return;
    
    let targetSessionId = activeSession?.id;
    if (!targetSessionId) {
      const newSession = await createSession(workspace);
      if (newSession) {
        targetSessionId = newSession.id;
      }
    }
    
    if (targetSessionId) {
      sendMessage(query, targetSessionId);
    }
  }, [activeSession, createSession, sendMessage, workspace, queryLoading]);

  const handleSend = useCallback(async (query: string) => {
    if (queryLoading) return;
    
    let targetSessionId = activeSession?.id;
    if (!targetSessionId) {
      const newSession = await createSession(workspace);
      if (newSession) {
        targetSessionId = newSession.id;
      }
    }
    
    if (targetSessionId) {
      sendMessage(query, targetSessionId);
    }
  }, [activeSession, createSession, sendMessage, workspace, queryLoading]);

  const hasMessages = (activeSession && activeSession.messages.length > 0) || queryLoading;

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: 'var(--color-bg)' }}>
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSession?.id || null}
        workspace={workspace}
        onSelectSession={loadSession}
        onNewChat={handleNewChat}
        onDeleteSession={removeSession}
        onRenameSession={renameActiveSession}
        onChangeWorkspace={setWorkspace}
      />

      {/* Center */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Gemini Key Warning */}
        {health?.llm_service?.status === 'unhealthy' && (
          <div style={{
            background: '#fffbeb', borderBottom: '1px solid #fef3c7',
            padding: '12px 40px', display: 'flex', alignItems: 'flex-start', gap: 12
          }}>
            <div style={{ 
              background: '#f59e0b', color: '#fff', borderRadius: '50%', 
              width: 20, height: 20, display: 'flex', alignItems: 'center', 
              justifyContent: 'center', fontSize: 14, fontWeight: 'bold', marginTop: 2
            }}>!</div>
            <div style={{ flex: 1 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: '#92400e', marginBottom: 2 }}>
                Gemini API Key Missing
              </h3>
              <p style={{ fontSize: 12, color: '#b45309', lineHeight: 1.5 }}>
                LLM-based features are disabled. To fix this, create a <strong>.env</strong> file in the root directory 
                replicated from <strong>.env.example</strong> and add your <code>GEMINI_API_KEY</code>.
              </p>
              <div style={{ marginTop: 8, background: '#0000000a', padding: '6px 10px', borderRadius: 4, fontFamily: 'monospace', fontSize: 11, color: '#92400e' }}>
                # Run this to verify setup:<br/>
                python -m backend.config
              </div>
            </div>
          </div>
        )}

        {/* Header */}
        <header style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '10px 40px',
          borderBottom: '1px solid var(--color-border)',
          background: 'var(--color-surface)',
          minHeight: 44,
        }}>
          <h2 style={{ fontSize: 13, fontWeight: 500, color: 'var(--color-text-secondary)', letterSpacing: '-0.005em' }}>
            {activeSession?.title || 'New conversation'}
          </h2>
          {lastTrace && (
            <button
              onClick={() => setSourcesOpen(!sourcesOpen)}
              style={{
                fontSize: 11, padding: '6px 12px', borderRadius: 6,
                border: 'none',
                background: '#374151',
                color: '#ffffff',
                boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
                cursor: 'pointer', fontWeight: 600,
                fontFamily: 'inherit', transition: 'all 0.1s',
                textTransform: 'uppercase',
                letterSpacing: '0.02em'
              }}
              onMouseEnter={e => { e.currentTarget.style.background = '#1f2937'; e.currentTarget.style.transform = 'translateY(-1px)'; }}
              onMouseLeave={e => { e.currentTarget.style.background = '#374151'; e.currentTarget.style.transform = 'translateY(0)'; }}
            >
              View Data Sources
            </button>
          )}
        </header>

        {hasMessages ? (
          <ChatPanel messages={activeSession.messages} queryLoading={queryLoading} onOpenSources={openSources} />
        ) : (
          <Suggestions workspace={workspace} onSelect={handleSuggestionSelect} />
        )}

        <QueryInput onSend={handleSend} disabled={queryLoading} />
      </div>

      <SourcesPanel 
        trace={selectedTrace} 
        context={selectedContext || lastContext || undefined} 
        open={sourcesOpen} 
        onClose={() => setSourcesOpen(false)} 
      />
    </div>
  );
}
