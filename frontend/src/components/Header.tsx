import React from "react";
import { GraduationCap, RotateCcw, Copy, Check, Sparkles } from "lucide-react";

interface HeaderProps {
  sessionId: string | null;
  onReset: () => void;
  isStreaming: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  sessionId,
  onReset,
  isStreaming,
}) => {
  const [copied, setCopied] = React.useState(false);

  const copySession = () => {
    if (!sessionId) return;
    navigator.clipboard.writeText(sessionId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <header className="sticky top-0 z-20 backdrop-blur-md bg-[#0c0d12]/80 border-b border-zinc-800/80 px-4 py-3">
      <div className="max-w-4xl mx-auto flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/20 text-white">
            <GraduationCap className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-base font-semibold text-zinc-100 tracking-tight">
                School Management AI
              </h1>
              <span className="flex items-center gap-1 text-[11px] font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2 py-0.5 rounded-full">
                <Sparkles className="w-3 h-3" />
                LangGraph
              </span>
            </div>
            <p className="text-xs text-zinc-400">
              Natural language queries for students, classes & academic records
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {sessionId && (
            <button
              onClick={copySession}
              title="Copy Session ID"
              className="hidden sm:flex items-center space-x-1.5 text-xs text-zinc-400 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 px-2.5 py-1.5 rounded-lg transition-colors"
            >
              <span>Session: {sessionId.slice(0, 8)}...</span>
              {copied ? (
                <Check className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <Copy className="w-3.5 h-3.5 text-zinc-400" />
              )}
            </button>
          )}

          <button
            onClick={onReset}
            disabled={isStreaming}
            title="Start New Chat"
            className="flex items-center space-x-1.5 text-xs font-medium text-zinc-300 bg-zinc-900 hover:bg-zinc-800 hover:text-white border border-zinc-800 px-3 py-1.5 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">New Chat</span>
          </button>
        </div>
      </div>
    </header>
  );
};
