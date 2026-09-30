export interface TableData {
  columns: string[];
  rows: Record<string, any>[];
  markdown_table?: string;
  row_count?: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sqlQuery?: string | null;
  resultTable?: TableData | null;
  statusText?: string;
  isStreaming?: boolean;
  timestamp: string;
  error?: string | null;
}

export interface SSEEventData {
  type: "session" | "status" | "sql" | "table" | "token" | "done" | "error";
  session_id?: string;
  stage?: string;
  message?: string;
  sql_query?: string;
  result_table?: TableData;
  content?: string;
  response?: string;
  error?: string;
}
