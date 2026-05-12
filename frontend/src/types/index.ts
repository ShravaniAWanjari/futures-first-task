export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  image?: string | null;
  file_name?: string | null;
  context?: string | null;
  sources?: string | null;
  trace?: string | null;
  structured_data?: string | null;
  timestamp: string;
}

export interface Session {
  id: string;
  title: string;
  workspace: string;
  created_at: string;
  updated_at: string;
  messages: Message[];
}

export interface ClassificationTrace {
  query_type: string;
  reasoning: string;
  recommended_tools: string[];
  confidence: number;
}

export interface SQLTrace {
  tool: string;
  success: boolean;
  query_used: string;
  error?: string | null;
  timing_ms: number;
  table_references: string[];
}

export interface RetrievalTrace {
  tool: string;
  success: boolean;
  n_results: number;
  error?: string | null;
  timing_ms: number;
}

export interface QueryTrace {
  request_id: string;
  dataset: string;
  classification: ClassificationTrace;
  tool_executions: (SQLTrace | RetrievalTrace)[];
  total_timing_ms: number;
}

export interface QueryResponse {
  request_id: string;
  answer_context: string;
  raw_reasoning?: string;
  sources: string[];
  trace: QueryTrace;
  overall_confidence: number;
  warnings: string[];
  errors: string[];
  structured_data?: any;
  session_title?: string;
}

export interface APIResponse<T> {
  success: boolean;
  request_id: string;
  data: T | null;
  error: { type: string; message: string } | null;
  api_version: string;
}

export interface SuggestionResponse {
  suggestions: string[];
}
