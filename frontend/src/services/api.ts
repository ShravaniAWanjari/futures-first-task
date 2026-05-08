import type { APIResponse, QueryResponse, Session, SuggestionResponse } from '../types';

const BASE_URL = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => null);
    throw new Error(errorBody?.error?.message || `Request failed: ${res.status}`);
  }

  const envelope: APIResponse<T> = await res.json();
  if (!envelope.success) {
    throw new Error(envelope.error?.message || 'Unknown API error');
  }
  return envelope.data as T;
}

// --- Sessions ---

export async function fetchSessions(workspace?: string): Promise<Session[]> {
  const url = workspace ? `/sessions?workspace=${workspace}` : '/sessions';
  return request<Session[]>(url);
}

export async function createSession(workspace: string): Promise<{ session_id: string }> {
  return request<{ session_id: string }>('/sessions', {
    method: 'POST',
    body: JSON.stringify({ workspace }),
  });
}

export async function fetchSession(id: string): Promise<Session> {
  return request<Session>(`/sessions/${id}`);
}

export async function deleteSession(id: string): Promise<void> {
  await request<{ status: string }>(`/sessions/${id}`, { method: 'DELETE' });
}

export async function renameSession(id: string, title: string): Promise<void> {
  await request<{ status: string }>(`/sessions/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ title }),
  });
}

// --- Query ---

export async function sendQuery(
  query: string,
  sessionId: string,
  workspace: string
): Promise<QueryResponse> {
  return request<QueryResponse>('/query', {
    method: 'POST',
    body: JSON.stringify({ query, session_id: sessionId, workspace }),
  });
}

// --- Suggestions ---

export async function fetchSuggestions(workspace: string): Promise<SuggestionResponse> {
  return request<SuggestionResponse>(`/suggestions?workspace=${workspace}`);
}

// --- Health ---

export async function fetchHealth(dataset: string = 'vistastream') {
  return request<Record<string, unknown>>(`/health?dataset=${dataset}`);
}
