"use client";

import { useState } from "react";
import type { ClassifiedItem, DraftResponse } from "@/lib/api";

const urgencyColors: Record<string, string> = {
  critical: "bg-red-100 text-red-700 border-red-200",
  high: "bg-orange-100 text-orange-700 border-orange-200",
  medium: "bg-yellow-100 text-yellow-700 border-yellow-200",
  low: "bg-gray-100 text-gray-600 border-gray-200",
};

const categoryColors: Record<string, string> = {
  decide: "bg-red-600 text-white",
  delegate: "bg-blue-600 text-white",
  ignore: "bg-gray-400 text-white",
};

const channelEmoji: Record<string, string> = {
  email: "\u2709\uFE0F",
  slack: "\uD83D\uDCAC",
  whatsapp: "\uD83D\uDCF1",
};

function ItemCard({
  item,
  drafts,
}: {
  item: ClassifiedItem;
  drafts: DraftResponse[];
}) {
  const [expanded, setExpanded] = useState(false);
  const relatedDrafts = drafts.filter((d) => item.message_ids.includes(d.message_id));

  return (
    <div className="border border-gray-200 rounded-lg bg-white overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span
                className={`text-xs font-medium px-2 py-0.5 rounded-full ${categoryColors[item.category]}`}
              >
                {item.category.toUpperCase()}
              </span>
              <span
                className={`text-xs font-medium px-2 py-0.5 rounded-full border ${urgencyColors[item.urgency]}`}
              >
                {item.urgency}
              </span>
              {item.flags.map((f, i) => (
                <span
                  key={i}
                  className="text-xs px-2 py-0.5 rounded-full bg-purple-100 text-purple-700"
                >
                  {f.type.replace("_", " ")}
                </span>
              ))}
            </div>
            <p className="font-medium text-sm truncate">{item.topic_summary}</p>
            {item.delegate_to && (
              <p className="text-xs text-blue-600 mt-0.5">
                → {item.delegate_to.name}
                {item.delegate_to.role && ` (${item.delegate_to.role})`}
              </p>
            )}
          </div>
          <span className="text-gray-400 text-xs shrink-0">
            {item.message_ids.map((id) => `#${id}`).join(", ")}
          </span>
        </div>
      </button>

      {expanded && (
        <div className="border-t border-gray-100 px-4 py-3 space-y-3 bg-gray-50">
          <div>
            <p className="text-xs font-medium text-gray-500 mb-1">Reasoning</p>
            <p className="text-sm text-gray-700">{item.reasoning}</p>
          </div>

          {item.flags.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-500 mb-1">Flags</p>
              {item.flags.map((f, i) => (
                <div key={i} className="text-sm text-gray-700 mb-1">
                  <span className="font-medium">[{f.type}]</span> {f.description}
                  {f.recommendation && (
                    <span className="text-blue-600 ml-1">— {f.recommendation}</span>
                  )}
                </div>
              ))}
            </div>
          )}

          {relatedDrafts.map((draft) => (
            <div key={draft.message_id}>
              <p className="text-xs font-medium text-gray-500 mb-1">
                {channelEmoji[draft.channel] || ""} Draft Response (msg #{draft.message_id})
                {draft.subject && ` — ${draft.subject}`}
              </p>
              <pre className="text-sm text-gray-700 whitespace-pre-wrap bg-white border border-gray-200 rounded-md p-3">
                {draft.draft_response}
              </pre>
              {draft.tone_notes && (
                <p className="text-xs text-gray-400 mt-1">Tone: {draft.tone_notes}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function TriageList({
  items,
  drafts,
}: {
  items: ClassifiedItem[];
  drafts: DraftResponse[];
}) {
  if (items.length === 0) {
    return (
      <div className="text-center text-gray-400 py-8 text-sm">
        No items in this category
      </div>
    );
  }

  // Sort by urgency: critical first
  const urgencyOrder = { critical: 0, high: 1, medium: 2, low: 3 };
  const sorted = [...items].sort(
    (a, b) => (urgencyOrder[a.urgency] ?? 4) - (urgencyOrder[b.urgency] ?? 4)
  );

  return (
    <div className="space-y-2">
      {sorted.map((item, i) => (
        <ItemCard key={i} item={item} drafts={drafts} />
      ))}
    </div>
  );
}
