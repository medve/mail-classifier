"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";

export function Briefing({ markdown }: { markdown: string }) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="bg-white rounded-xl border border-gray-200 mb-6 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-lg">&#128203;</span>
          <h2 className="text-base font-semibold">Daily Briefing</h2>
          <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
            ~2 min read
          </span>
        </div>
        <span className="text-gray-400 text-sm">{expanded ? "Collapse" : "Expand"}</span>
      </button>

      {expanded && (
        <div className="px-6 pb-6 prose prose-sm max-w-none prose-headings:text-gray-900 prose-p:text-gray-700 prose-li:text-gray-700 prose-strong:text-gray-900">
          <ReactMarkdown>{markdown}</ReactMarkdown>
        </div>
      )}
    </div>
  );
}
