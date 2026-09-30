import type { SSEEventData, TableData } from "../types/chat";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface StreamCallbacks {
  onSession?: (sessionId: string) => void;
  onStatus?: (stage: string, message: string) => void;
  onSql?: (sql: string) => void;
  onTable?: (table: TableData, error?: string | null) => void;
  onToken?: (token: string) => void;
  onDone?: (data: {
    sessionId?: string;
    sqlQuery?: string | null;
    resultTable?: TableData | null;
    response: string;
  }) => void;
  onError?: (error: string) => void;
}

export async function sendChatMessageStream(
  message: string,
  sessionId: string | null,
  callbacks: StreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message,
        session_id: sessionId || undefined,
      }),
      signal,
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Server returned ${response.status}: ${errText}`);
    }

    if (!response.body) {
      throw new Error("ReadableStream not supported on this browser.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop() || "";

      for (const rawEvent of events) {
        if (!rawEvent.trim()) continue;

        const lines = rawEvent.split("\n");
        let eventType = "message";
        let dataStr = "";

        for (const line of lines) {
          if (line.startsWith("event:")) {
            eventType = line.replace("event:", "").trim();
          } else if (line.startsWith("data:")) {
            dataStr = line.replace("data:", "").trim();
          }
        }

        if (!dataStr) continue;

        try {
          const parsed: SSEEventData = JSON.parse(dataStr);

          switch (eventType) {
            case "session":
              if (parsed.session_id && callbacks.onSession) {
                callbacks.onSession(parsed.session_id);
              }
              break;

            case "status":
              if (callbacks.onStatus) {
                callbacks.onStatus(parsed.stage || "", parsed.message || "");
              }
              break;

            case "sql":
              if (parsed.sql_query && callbacks.onSql) {
                callbacks.onSql(parsed.sql_query);
              }
              break;

            case "table":
              if (parsed.result_table && callbacks.onTable) {
                callbacks.onTable(parsed.result_table, parsed.error);
              }
              break;

            case "token":
              if (parsed.content && callbacks.onToken) {
                callbacks.onToken(parsed.content);
              }
              break;

            case "done":
              if (callbacks.onDone) {
                callbacks.onDone({
                  sessionId: parsed.session_id,
                  sqlQuery: parsed.sql_query,
                  resultTable: parsed.result_table,
                  response: parsed.response || "",
                });
              }
              break;

            case "error":
              if (callbacks.onError) {
                callbacks.onError(parsed.error || "An error occurred");
              }
              break;

            default:
              break;
          }
        } catch (jsonErr) {
          console.warn("Failed to parse SSE event data:", dataStr, jsonErr);
        }
      }
    }
  } catch (err: any) {
    if (err.name === "AbortError") {
      console.log("Chat stream was aborted.");
      return;
    }
    if (callbacks.onError) {
      callbacks.onError(err.message || "Failed to communicate with chat service.");
    }
  }
}
