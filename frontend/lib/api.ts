/** Thin client for the JD Intel FastAPI backend. */

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export interface SkillMatch {
  skill: string;
  status: "matched" | "partial" | "missing";
  similarity: number;
}

export interface BulletSuggestion {
  original: string;
  issue: string;
  rewrites: string[];
}

export interface AnalysisReport {
  composite_score: number;
  jd_match_score: number;
  interview_coverage_score: number;
  formatting_score: number;
  section_scores: Record<string, number>;
  missing_skills: string[];
  skill_matches: SkillMatch[];
  interview_blindspots: string[];
  top_interview_topics: string[];
  bullet_suggestions: BulletSuggestion[];
  parsability_issues: string[];
  warnings: string[];
}

export interface AgentProgressEvent {
  type: "status" | "agent_complete" | "error" | "done";
  agent?: string;
  progress?: number;
  detail?: string;
  report?: AnalysisReport;
}

export interface AnalyzeInput {
  resumeFile?: File | null;
  resumeText?: string;
  jd: string;
  company: string;
  role: string;
}

/** Streams /api/analyze via SSE, invoking onEvent for each progress/result event. */
export async function analyzeResume(
  input: AnalyzeInput,
  onEvent: (event: AgentProgressEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const formData = new FormData();
  if (input.resumeFile) formData.append("resume", input.resumeFile);
  if (input.resumeText) formData.append("resume_text", input.resumeText);
  formData.append("jd", input.jd);
  formData.append("company", input.company);
  formData.append("role", input.role);

  const response = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    body: formData,
    signal,
  });

  if (!response.ok || !response.body) {
    throw new Error(`Analyze request failed: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";

    for (const chunk of chunks) {
      const lines = chunk.split("\n");
      const eventLine = lines.find((l) => l.startsWith("event:"));
      const dataLine = lines.find((l) => l.startsWith("data:"));
      if (!dataLine) continue;
      const type = (eventLine?.replace("event:", "").trim() ?? "status") as AgentProgressEvent["type"];
      const data = JSON.parse(dataLine.replace("data:", "").trim());
      onEvent({ type, ...data });
    }
  }
}

export async function fetchSignals(company: string, role: string) {
  const res = await fetch(`${API_BASE}/api/signals/${encodeURIComponent(company)}/${encodeURIComponent(role)}`);
  if (!res.ok) throw new Error(`No signals found for ${company} / ${role}`);
  return res.json();
}

export async function requestRewrite(payload: {
  bullet: string;
  jd_skills: string[];
  interview_topics: string[];
  company: string;
}) {
  const res = await fetch(`${API_BASE}/api/rewrite`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Rewrite request failed");
  return res.json() as Promise<{ rewrites: string[] }>;
}
