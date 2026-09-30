import React, { useState } from "react";
import { Database, Copy, Check, ChevronDown, ChevronRight } from "lucide-react";

interface SqlCardProps {
  sql: string;
}

export const SqlCard: React.FC<SqlCardProps> = ({ sql }) => {
  const [copied, setCopied] = useState(false);
  const [isOpen, setIsOpen] = useState(true);

  const copySql = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-2 rounded-xl border border-zinc-800 bg-zinc-950/60 overflow-hidden text-xs">
      <div
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between px-3 py-2 bg-zinc-900/60 border-b border-zinc-800/60 cursor-pointer select-none hover:bg-zinc-800/40 transition-colors"
      >
        <div className="flex items-center space-x-2 text-zinc-300 font-mono font-medium">
          <Database className="w-3.5 h-3.5 text-blue-400" />
          <span>Generated SQL Query</span>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={copySql}
            className="flex items-center space-x-1 text-zinc-400 hover:text-zinc-200 px-2 py-0.5 rounded hover:bg-zinc-800 transition-colors"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 text-emerald-400" />
                <span className="text-emerald-400 text-[11px]">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3 h-3" />
                <span className="text-[11px]">Copy</span>
              </>
            )}
          </button>
          {isOpen ? (
            <ChevronDown className="w-3.5 h-3.5 text-zinc-400" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5 text-zinc-400" />
          )}
        </div>
      </div>

      {isOpen && (
        <div className="p-3 overflow-x-auto bg-[#090a0f]">
          <pre className="text-emerald-300 font-mono text-[12px] leading-relaxed whitespace-pre-wrap">
            {sql}
          </pre>
        </div>
      )}
    </div>
  );
};
