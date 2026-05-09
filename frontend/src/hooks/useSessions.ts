import { useState, useCallback, useRef, useEffect } from 'react';
import type { Session, Message, QueryResponse } from '../types';
import * as api from '../services/api';

export function useSessions() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSession, setActiveSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(false);
  const [queryLoading, setQueryLoading] = useState(false);
  const [lastTrace, setLastTrace] = useState<QueryResponse['trace'] | null>(null);
  const [workspaceOverride, setWorkspaceOverride] = useState<string | null>(null);
  const pendingRef = useRef(false);

  const workspace = workspaceOverride || activeSession?.workspace || 'vistastream';

  const loadSessions = useCallback(async (ws: string) => {
    setLoading(true);
    try {
      const list = await api.fetchSessions(ws);
      setSessions(list);
      return list;
    } catch {
      console.error('Failed to load sessions');
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  // Sync sessions whenever workspace changes
  useEffect(() => {
    loadSessions(workspace);
  }, [workspace, loadSessions]);

  const setWorkspace = useCallback((ws: string) => {
    setWorkspaceOverride(ws);
    setActiveSession(null);
    setLastTrace(null);
  }, []);

  const loadSession = useCallback(async (id: string) => {
    setLoading(true);
    try {
      const session = await api.fetchSession(id);
      setActiveSession(session);
      setWorkspaceOverride(session.workspace);
      // Update trace to the last message's trace if available
      if (session.messages.length > 0) {
        const lastMsg = session.messages[session.messages.length - 1];
        if (lastMsg.role === 'assistant' && lastMsg.trace) {
          try {
            setLastTrace(JSON.parse(lastMsg.trace));
          } catch {
            setLastTrace(null);
          }
        }
      } else {
        setLastTrace(null);
      }
    } catch {
      console.error('Failed to load session');
    } finally {
      setLoading(false);
    }
  }, []);

  const createSession = useCallback(async (ws?: string) => {
    const targetWs = ws || workspace;
    try {
      const { session_id } = await api.createSession(targetWs);
      const session: Session = {
        id: session_id,
        title: 'New conversation',
        workspace: targetWs,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        messages: [],
      };
      setSessions(prev => [session, ...prev]);
      setActiveSession(session);
      setWorkspaceOverride(targetWs);
      setLastTrace(null);
      return session;
    } catch {
      console.error('Failed to create session');
      return null;
    }
  }, [workspace]);

  const removeSession = useCallback(async (id: string) => {
    try {
      await api.deleteSession(id);
      setSessions(prev => prev.filter(s => s.id !== id));
      if (activeSession?.id === id) {
        setActiveSession(null);
        setLastTrace(null);
      }
    } catch {
      console.error('Failed to delete session');
    }
  }, [activeSession]);

  const renameActiveSession = useCallback(async (title: string) => {
    if (!activeSession) return;
    try {
      await api.renameSession(activeSession.id, title);
      setActiveSession(prev => prev ? { ...prev, title } : null);
      setSessions(prev => prev.map(s => s.id === activeSession.id ? { ...s, title } : s));
    } catch {
      console.error('Failed to rename session');
    }
  }, [activeSession]);

  const sendMessage = useCallback(async (query: string, overrideSessionId?: string) => {
    const targetSessionId = overrideSessionId || activeSession?.id;
    if (!targetSessionId || pendingRef.current) return;
    
    pendingRef.current = true;
    setQueryLoading(true);

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: query,
      timestamp: new Date().toISOString(),
    };
    
    // Optimistic update if sending to active session
    if (activeSession?.id === targetSessionId) {
      setActiveSession(prev => prev ? { ...prev, messages: [...prev.messages, userMsg] } : null);
    }

    try {
      const res = await api.sendQuery(query, targetSessionId, workspace);
      console.log('[useSessions] API Response:', res);

      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: res.answer_context,
        sources: res.sources.join(','),
        trace: JSON.stringify(res.trace),
        structured_data: res.structured_data ? JSON.stringify(res.structured_data) : null,
        timestamp: new Date().toISOString(),
      };

      if (activeSession?.id === targetSessionId) {
        setActiveSession(prev => prev ? { ...prev, messages: [...prev.messages, assistantMsg] } : null);
        setLastTrace(res.trace);
      }

      // Refetch session to pick up backend-generated semantic title if it was empty
      const isFirstMsg = activeSession?.id === targetSessionId && activeSession.messages.length === 0;
      if (isFirstMsg) {
        try {
          const updated = await api.fetchSession(targetSessionId);
          if (updated.title && updated.title !== 'New conversation' && updated.title !== 'New Chat') {
            setSessions(prev => prev.map(s => s.id === targetSessionId ? { ...s, title: updated.title } : s));
            setActiveSession(prev => prev?.id === targetSessionId ? { ...prev, title: updated.title } : prev);
          }
        } catch { /* title update is non-critical */ }
      }
      return res;
    } catch (err) {
      if (activeSession?.id === targetSessionId) {
        const errorMsg: Message = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: `Unable to process this request. ${err instanceof Error ? err.message : 'Please try again.'}`,
          timestamp: new Date().toISOString(),
        };
        setActiveSession(prev => prev ? { ...prev, messages: [...prev.messages, errorMsg] } : null);
      }
    } finally {
      setQueryLoading(false);
      pendingRef.current = false;
    }
  }, [activeSession, workspace]);

  return {
    sessions, activeSession, loading, queryLoading, workspace, lastTrace,
    loadSessions, loadSession, createSession, removeSession,
    renameActiveSession, sendMessage, setActiveSession, setWorkspace,
  };
}
