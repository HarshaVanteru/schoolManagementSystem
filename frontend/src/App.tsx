import { useState, useRef, useEffect } from "react";
import { Header } from "./components/Header";
import { SuggestedPrompts } from "./components/SuggestedPrompts";
import { ChatMessageItem } from "./components/ChatMessageItem";
import { ChatInput } from "./components/ChatInput";
import type { ChatMessage } from "./types/chat";
import { sendChatMessageStream } from "./services/api";

export function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);

  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest message
  const scrollToBottom = (behavior: ScrollBehavior = "smooth") => {
    messagesEndRef.current?.scrollIntoView({ behavior });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isStreaming]);

  const handleSendMessage = async (text: string) => {
    if (isStreaming) return;

    const timestamp = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });

    const userMessageId = `user-${Date.now()}`;
    const assistantMessageId = `assistant-${Date.now()}`;

    const userMessage: ChatMessage = {
      id: userMessageId,
      role: "user",
      content: text,
      timestamp,
    };

    const assistantPlaceholder: ChatMessage = {
      id: assistantMessageId,
      role: "assistant",
      content: "",
      statusText: "Analyzing question and preparing query...",
      isStreaming: true,
      timestamp,
    };

    setMessages((prev) => [...prev, userMessage, assistantPlaceholder]);
    setIsStreaming(true);

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    await sendChatMessageStream(
      text,
      sessionId,
      {
        onSession: (newSessionId) => {
          setSessionId(newSessionId);
        },
        onStatus: (_stage, message) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, statusText: message }
                : msg
            )
          );
        },
        onSql: (sql) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, sqlQuery: sql }
                : msg
            )
          );
        },
        onTable: (table, err) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? {
                    ...msg,
                    resultTable: table,
                    error: err || msg.error,
                  }
                : msg
            )
          );
        },
        onToken: (token) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, content: msg.content + token }
                : msg
            )
          );
        },
        onDone: (data) => {
          setIsStreaming(false);
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? {
                    ...msg,
                    isStreaming: false,
                    statusText: undefined,
                    content: data.response || msg.content,
                    sqlQuery: data.sqlQuery !== undefined ? data.sqlQuery : msg.sqlQuery,
                    resultTable: data.resultTable !== undefined ? data.resultTable : msg.resultTable,
                  }
                : msg
            )
          );
        },
        onError: (errorMessage) => {
          setIsStreaming(false);
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? {
                    ...msg,
                    isStreaming: false,
                    statusText: undefined,
                    error: errorMessage,
                  }
                : msg
            )
          );
        },
      },
      abortController.signal
    );
  };

  const handleStopStreaming = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
    setMessages((prev) =>
      prev.map((msg) => (msg.isStreaming ? { ...msg, isStreaming: false, statusText: undefined } : msg))
    );
  };

  const handleResetChat = () => {
    if (isStreaming) {
      handleStopStreaming();
    }
    setMessages([]);
    setSessionId(null);
  };

  return (
    <div className="flex flex-col min-h-screen bg-[#0c0d12] text-zinc-100 font-sans selection:bg-blue-500/30 selection:text-blue-200">
      {/* Top Header */}
      <Header
        sessionId={sessionId}
        onReset={handleResetChat}
        isStreaming={isStreaming}
      />

      {/* Main Chat Thread Area */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-2 sm:px-4 py-4 flex flex-col justify-between">
        {messages.length === 0 ? (
          <div className="flex-1 flex items-center justify-center">
            <SuggestedPrompts onSelectPrompt={handleSendMessage} />
          </div>
        ) : (
          <div className="flex-1 space-y-2">
            {messages.map((message) => (
              <ChatMessageItem key={message.id} message={message} />
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </main>

      {/* Fixed Bottom Input */}
      <ChatInput
        onSendMessage={handleSendMessage}
        isStreaming={isStreaming}
        onStopStreaming={handleStopStreaming}
      />
    </div>
  );
}

export default App;
