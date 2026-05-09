import { useState, useEffect, useCallback, useRef } from 'react';
import { useSessions } from '../hooks/useSessions';
import Sidebar from '../components/Sidebar';
import ChatPanel from '../components/ChatPanel';
import QueryInput from '../components/QueryInput';
import Suggestions from '../components/Suggestions';
import SourcesPanel from '../components/SourcesPanel';

export default function WorkspacePage() {
  const {
    sessions, activeSession, loading, queryLoading, workspace, lastTrace,
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

  const hasMessages = activeSession && activeSession.messages.length > 0;

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
                fontSize: 12, padding: '4px 10px', borderRadius: 5,
                border: 'none',
                background: sourcesOpen ? 'var(--color-active)' : 'transparent',
                color: sourcesOpen ? 'var(--color-text-secondary)' : 'var(--color-text-muted)',
                cursor: 'pointer', fontWeight: 500,
                fontFamily: 'inherit', transition: 'all 0.1s',
              }}
              onMouseEnter={e => { e.currentTarget.style.background = 'var(--color-primary-soft)'; e.currentTarget.style.color = 'var(--color-text-secondary)'; }}
              onMouseLeave={e => { if (!sourcesOpen) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--color-text-muted)'; } }}
            >
              Sources
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
        context={selectedContext} 
        open={sourcesOpen} 
        onClose={() => setSourcesOpen(false)} 
      />
    </div>
  );
}
