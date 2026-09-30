import React, { useState } from "react";
import { Table, Download, Copy, Check } from "lucide-react";
import type { TableData } from "../types/chat";

interface DataTableProps {
  data: TableData;
}

export const DataTable: React.FC<DataTableProps> = ({ data }) => {
  const [copied, setCopied] = useState(false);
  const { columns, rows, row_count } = data;

  if (!columns || columns.length === 0 || !rows || rows.length === 0) {
    return null;
  }

  const copyMarkdown = () => {
    if (data.markdown_table) {
      navigator.clipboard.writeText(data.markdown_table);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const downloadCsv = () => {
    const csvHeader = columns.join(",") + "\n";
    const csvRows = rows
      .map((row) =>
        columns
          .map((col) => {
            const val = row[col] !== undefined && row[col] !== null ? String(row[col]) : "";
            if (val.includes(",") || val.includes('"') || val.includes("\n")) {
              return `"${val.replace(/"/g, '""')}"`;
            }
            return val;
          })
          .join(",")
      )
      .join("\n");

    const blob = new Blob([csvHeader + csvRows], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `query_results_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="my-3 rounded-xl border border-zinc-800 bg-zinc-950/70 overflow-hidden text-xs">
      <div className="flex items-center justify-between px-3.5 py-2.5 bg-zinc-900/60 border-b border-zinc-800">
        <div className="flex items-center space-x-2">
          <Table className="w-3.5 h-3.5 text-indigo-400" />
          <span className="font-medium text-zinc-300">Query Results</span>
          <span className="text-[11px] bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded-full font-mono">
            {row_count ?? rows.length} {rows.length === 1 ? "row" : "rows"}
          </span>
        </div>

        <div className="flex items-center space-x-2">
          {data.markdown_table && (
            <button
              onClick={copyMarkdown}
              title="Copy Markdown Table"
              className="flex items-center space-x-1 text-zinc-400 hover:text-zinc-200 px-2 py-1 rounded hover:bg-zinc-800 transition-colors"
            >
              {copied ? (
                <Check className="w-3 h-3 text-emerald-400" />
              ) : (
                <Copy className="w-3 h-3" />
              )}
              <span className="text-[11px]">Markdown</span>
            </button>
          )}

          <button
            onClick={downloadCsv}
            title="Download CSV"
            className="flex items-center space-x-1 text-zinc-400 hover:text-zinc-200 px-2 py-1 rounded hover:bg-zinc-800 transition-colors"
          >
            <Download className="w-3 h-3" />
            <span className="text-[11px]">CSV</span>
          </button>
        </div>
      </div>

      <div className="overflow-x-auto max-h-72">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-zinc-900/80 border-b border-zinc-800 text-zinc-400 font-medium sticky top-0">
              {columns.map((col) => (
                <th key={col} className="px-3.5 py-2 text-zinc-300 font-semibold tracking-wider font-mono uppercase text-[11px]">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-900">
            {rows.map((row, idx) => (
              <tr
                key={idx}
                className="hover:bg-zinc-900/40 transition-colors even:bg-zinc-950 odd:bg-[#0e0f15]"
              >
                {columns.map((col) => (
                  <td key={col} className="px-3.5 py-2 text-zinc-300 font-mono text-[12px] whitespace-nowrap">
                    {row[col] !== undefined && row[col] !== null ? String(row[col]) : "—"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
