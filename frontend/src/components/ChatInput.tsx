import React, { useState, useRef, useEffect } from "react";
import { ArrowUp, Square } from "lucide-react";

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  isStreaming: boolean;
  onStopStreaming: () => void;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  isStreaming,
  onStopStreaming,
}) => {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea height as text grows
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        140
      )}px`;
    }
  }, [input]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (isStreaming) {
      onStopStreaming();
      return;
    }
    const trimmed = input.trim();
    if (!trimmed) return;
    onSendMessage(trimmed);
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="sticky bottom-0 z-20 bg-gradient-to-t from-[#0c0d12] via-[#0c0d12]/95 to-transparent pt-4 pb-5 px-4">
      <div className="max-w-4xl mx-auto">
        <form
          onSubmit={handleSubmit}
          className="relative flex items-end bg-zinc-900/90 border border-zinc-800 focus-within:border-blue-500/60 focus-within:ring-1 focus-within:ring-blue-500/40 rounded-2xl shadow-xl shadow-black/40 transition-all p-2"
        >
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about students, marks, classes, or exams... (e.g. 'Show top students')"
            className="w-full bg-transparent text-zinc-100 placeholder-zinc-500 text-sm px-3 py-2 resize-none focus:outline-none max-h-36 font-sans leading-relaxed"
          />

          <div className="flex items-center space-x-1 pl-2">
            {isStreaming ? (
              <button
                type="button"
                onClick={onStopStreaming}
                title="Stop response"
                className="w-8 h-8 rounded-xl bg-red-600/90 hover:bg-red-500 text-white flex items-center justify-center transition-all shadow-md"
              >
                <Square className="w-3.5 h-3.5 fill-current" />
              </button>
            ) : (
              <button
                type="submit"
                disabled={!input.trim()}
                title="Send message"
                className="w-8 h-8 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:hover:bg-blue-600 text-white flex items-center justify-center transition-all shadow-md shadow-blue-600/20 disabled:cursor-not-allowed"
              >
                <ArrowUp className="w-4 h-4" />
              </button>
            )}
          </div>
        </form>

        <p className="text-[11px] text-zinc-400 text-center mt-2">
          Press <span className="font-mono text-zinc-400 bg-zinc-800/80 px-1 py-0.5 rounded">Enter</span> to send,{" "}
          <span className="font-mono text-zinc-400 bg-zinc-800/80 px-1 py-0.5 rounded">Shift + Enter</span> for new line
        </p>
      </div>
    </div>
  );
};
