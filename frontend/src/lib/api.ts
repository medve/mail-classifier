const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Flag {
  type: string;
  description: string;
  severity: string;
  related_message_ids: number[];
  recommendation: string;
}

export interface PersonRef {
  name: string;
  role: string | null;
}

export interface ClassifiedItem {
  thread_id: string | null;
  message_ids: number[];
  category: "ignore" | "delegate" | "decide";
  reasoning: string;
  flags: Flag[];
  delegate_to: PersonRef | null;
  urgency: "low" | "medium" | "high" | "critical";
  requires_response: boolean;
  topic_summary: string;
}

export interface DraftResponse {
  message_id: number;
  channel: string;
  draft_response: string;
  tone_notes: string;
  subject: string | null;
}

export interface Thread {
  id: string;
  message_ids: number[];
  topic: string;
  latest_state: string;
  contradictions: {
    earlier_message_id: number;
    later_message_id: number;
    description: string;
    field: string;
  }[];
  superseded_message_ids: number[];
}

export interface VerificationResult {
  message_id: number | null;
  thread_id: string | null;
  passed: boolean;
  issues: string[];
  suggested_fix: string;
  issue_type: string;
}

export interface PipelineResult {
  date: string;
  messages_processed: number;
  threads: Thread[];
  classifications: ClassifiedItem[];
  flags: Flag[];
  drafts: DraftResponse[];
  verification: VerificationResult[];
  briefing: string;
  people_discovered: { id: string; name: string; role: string | null }[];
}

export interface TaskSubmitted {
  task_id: string;
  status: "pending" | "running" | "completed" | "failed";
}

export interface TaskState {
  task_id: string;
  status: "pending" | "running" | "completed" | "failed";
  error: string | null;
  result: PipelineResult | null;
  created_at: string;
  updated_at: string;
}

export async function submitMessages(file: File): Promise<TaskSubmitted> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/api/process`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error(`Submit failed: ${res.statusText}`);
  return res.json();
}

export async function getTaskState(taskId: string): Promise<TaskState> {
  const res = await fetch(`${API_BASE}/api/tasks/${taskId}`);
  if (!res.ok) throw new Error(`Task not found: ${res.statusText}`);
  return res.json();
}
