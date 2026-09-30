import React from "react";
import { User, Bot, Loader2, AlertCircle } from "lucide-react";
import type { ChatMessage } from "../types/chat";
import { SqlCard } from "./SqlCard";
import { DataTable } from "./DataTable";

interface ChatMessageItemProps {
  message: ChatMessage;
}

export const ChatMessageItem: React.FC<ChatMessageItemProps> = ({ message }) => {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end my-4 px-2">
        <div className="flex items-start space-x-2 max-w-[85%] sm:max-w-[75%]">
          <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 shadow-md shadow-blue-900/10">
            <p className="text-sm leading-relaxed whitespace-pre-wrap">
              {message.content}
            </p>
            <span className="text-[10px] text-blue-200/70 mt-1 block text-right">
              {message.timestamp}
            </span>
          </div>
          <div className="w-7 h-7 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-zinc-300 flex-shrink-0 mt-0.5">
            <User className="w-4 h-4" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start my-4 px-2">
      <div className="flex items-start space-x-3 max-w-[95%] sm:max-w-[85%] w-full">
        <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-blue-500 to-indigo-600 flex items-center justify-center text-white flex-shrink-0 shadow-sm mt-1">
          <Bot className="w-4 h-4" />
        </div>

        <div className="flex-1 min-w-0 bg-zinc-900/70 border border-zinc-800 rounded-2xl rounded-tl-sm p-4 shadow-sm">
          {/* Active status indicator while streaming */}
          {message.isStreaming && message.statusText && (
            <div className="flex items-center space-x-2 mb-3 text-xs text-blue-400 font-medium bg-blue-500/10 border border-blue-500/20 px-2.5 py-1.5 rounded-lg w-fit">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span>{message.statusText}</span>
            </div>
          )}

          {/* Generated SQL Query card */}
          {message.sqlQuery && <SqlCard sql={message.sqlQuery} />}

          {/* Tabular query result */}
          {message.resultTable && <DataTable data={message.resultTable} />}

          {/* Natural language response */}
          {message.content && (
            <div className="text-sm text-zinc-200 leading-relaxed mt-2 whitespace-pre-wrap">
              {message.content}
              {message.isStreaming && <span className="cursor-blink" />}
            </div>
          )}

          {/* Error notification if any */}
          {message.error && (
            <div className="mt-3 flex items-start space-x-2 p-3 bg-red-950/40 border border-red-800/60 rounded-xl text-red-300 text-xs">
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
              <p>{message.error}</p>
            </div>
          )}

          <div className="flex items-center justify-between mt-2 pt-2 border-t border-zinc-800/40">
            <span className="text-[10px] text-zinc-400">
              {message.timestamp}
            </span>
            {message.isStreaming && (
              <span className="text-[10px] text-zinc-400 flex items-center gap-1 font-mono">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Live Stream
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
