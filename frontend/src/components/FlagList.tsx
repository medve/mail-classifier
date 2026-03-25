"use client";

import type { Flag } from "@/lib/api";

const severityColors: Record<string, string> = {
  critical: "border-l-red-500 bg-red-50",
  high: "border-l-orange-500 bg-orange-50",
  medium: "border-l-yellow-500 bg-yellow-50",
  low: "border-l-gray-400 bg-gray-50",
};

const typeIcons: Record<string, string> = {
  phishing: "\uD83D\uDEE1\uFE0F",
  escalation: "\u26A0\uFE0F",
  schedule_conflict: "\uD83D\uDCC5",
  deal_change: "\uD83D\uDCB0",
  deadline: "\u23F0",
  contradiction: "\uD83D\uDD04",
  info_resolved: "\u2705",
};

export function FlagList({ flags }: { flags: Flag[] }) {
  if (flags.length === 0) {
    return (
      <div className="text-center text-gray-400 py-8 text-sm">
        No flags detected
      </div>
    );
  }

  const severityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
  const sorted = [...flags].sort(
    (a, b) => (severityOrder[a.severity as keyof typeof severityOrder] ?? 4) - (severityOrder[b.severity as keyof typeof severityOrder] ?? 4)
  );

  return (
    <div className="space-y-2">
      {sorted.map((flag, i) => (
        <div
          key={i}
          className={`border-l-4 rounded-lg p-4 ${severityColors[flag.severity] || "bg-gray-50 border-l-gray-300"}`}
        >
          <div className="flex items-start gap-3">
            <span className="text-lg">{typeIcons[flag.type] || "\u2139\uFE0F"}</span>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-medium uppercase tracking-wide text-gray-500">
                  {flag.type.replace("_", " ")}
                </span>
                <span className="text-xs px-1.5 py-0.5 rounded bg-white/60 font-medium">
                  {flag.severity}
                </span>
                {flag.related_message_ids.length > 0 && (
                  <span className="text-xs text-gray-400">
                    Messages: {flag.related_message_ids.map((id) => `#${id}`).join(", ")}
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-800">{flag.description}</p>
              {flag.recommendation && (
                <p className="text-sm text-blue-700 mt-1 font-medium">
                  Recommendation: {flag.recommendation}
                </p>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
