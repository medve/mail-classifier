"use client";

import { useState, useCallback } from "react";
import type { PipelineResult } from "@/lib/api";
import { submitMessages, getTaskState } from "@/lib/api";
import { Briefing } from "@/components/Briefing";
import { TriageList } from "@/components/TriageList";
import { FlagList } from "@/components/FlagList";

type Tab = "decisions" | "flags" | "delegated" | "ignored";

const STAGES = ["Normalizing", "Correlating", "Classifying", "Drafting", "Verifying", "Briefing"];

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export default function Home() {
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("decisions");

  const pollTask = useCallback(async (taskId: string) => {
    const stageInterval = setInterval(() => {
      setStage((s) => Math.min(s + 1, STAGES.length - 1));
    }, 3000);

    try {
      for (;;) {
        await sleep(2000);
        const state = await getTaskState(taskId);

        if (state.status === "completed" && state.result) {
          setResult(state.result);
          return;
        }
        if (state.status === "failed") {
          setError(state.error ?? "Processing failed");
          return;
        }
      }
    } finally {
      clearInterval(stageInterval);
    }
  }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setError(null);
    setStage(0);

    try {
      const { task_id } = await submitMessages(file);
      await pollTask(task_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Processing failed");
    } finally {
      setLoading(false);
    }
  };

  const decisions = result?.classifications.filter((c) => c.category === "decide") ?? [];
  const delegated = result?.classifications.filter((c) => c.category === "delegate") ?? [];
  const ignored = result?.classifications.filter((c) => c.category === "ignore") ?? [];

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">CEO Triage</h1>
            {result && (
              <p className="text-sm text-gray-500">
                {result.date} &middot; {result.messages_processed} messages processed
              </p>
            )}
          </div>
          <label className="cursor-pointer bg-gray-900 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-800 transition-colors">
            {loading ? "Processing..." : "Upload Messages"}
            <input
              type="file"
              accept=".json"
              onChange={handleUpload}
              className="hidden"
              disabled={loading}
            />
          </label>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* Loading state */}
        {loading && (
          <div className="bg-white rounded-xl border border-gray-200 p-8 mb-8">
            <div className="flex flex-col items-center gap-4">
              <div className="animate-spin rounded-full h-8 w-8 border-2 border-gray-300 border-t-gray-900" />
              <p className="font-medium">Processing messages...</p>
              <div className="flex gap-2">
                {STAGES.map((s, i) => (
                  <span
                    key={s}
                    className={`text-xs px-2 py-1 rounded-full ${
                      i < stage
                        ? "bg-green-100 text-green-700"
                        : i === stage
                          ? "bg-blue-100 text-blue-700 animate-pulse"
                          : "bg-gray-100 text-gray-400"
                    }`}
                  >
                    {s}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-8 text-red-700">
            {error}
          </div>
        )}

        {/* Empty state */}
        {!result && !loading && (
          <div className="bg-white rounded-xl border border-gray-200 p-16 text-center">
            <div className="text-4xl mb-4">&#128233;</div>
            <h2 className="text-lg font-medium mb-2">No messages processed yet</h2>
            <p className="text-gray-500 text-sm">
              Upload a messages.json file to get started
            </p>
          </div>
        )}

        {/* Results */}
        {result && (
          <>
            {/* Briefing */}
            <Briefing markdown={result.briefing} />

            {/* Tabs */}
            <div className="flex gap-1 bg-gray-100 rounded-lg p-1 mb-6">
              {[
                { key: "decisions" as Tab, label: "Decisions", count: decisions.length, color: "red" },
                { key: "flags" as Tab, label: "Flags", count: result.flags.length, color: "orange" },
                { key: "delegated" as Tab, label: "Delegated", count: delegated.length, color: "blue" },
                { key: "ignored" as Tab, label: "Ignored", count: ignored.length, color: "gray" },
              ].map((t) => (
                <button
                  key={t.key}
                  onClick={() => setTab(t.key)}
                  className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-colors ${
                    tab === t.key
                      ? "bg-white shadow-sm text-gray-900"
                      : "text-gray-500 hover:text-gray-700"
                  }`}
                >
                  {t.label}
                  <span
                    className={`ml-2 inline-flex items-center justify-center px-2 py-0.5 rounded-full text-xs ${
                      tab === t.key ? `bg-${t.color}-100 text-${t.color}-700` : "bg-gray-200 text-gray-500"
                    }`}
                  >
                    {t.count}
                  </span>
                </button>
              ))}
            </div>

            {/* Tab content */}
            {tab === "decisions" && (
              <TriageList items={decisions} drafts={result.drafts} />
            )}
            {tab === "flags" && <FlagList flags={result.flags} />}
            {tab === "delegated" && (
              <TriageList items={delegated} drafts={result.drafts} />
            )}
            {tab === "ignored" && (
              <TriageList items={ignored} drafts={result.drafts} />
            )}
          </>
        )}
      </main>
    </div>
  );
}
