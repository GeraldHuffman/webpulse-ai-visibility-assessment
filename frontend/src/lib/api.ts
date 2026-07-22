const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

export interface AssessmentResponse {
  id: string;
  company_name: string;
  website_url: string;
  status: string;
  created_at: string;
  completed_at: string | null;
}

export interface ReportData {
  id: string;
  assessment_id: string;
  visibility_score: number;
  category_scores: Record<string, number>;
  summary: string;
  actions: ActionItem[];
  findings: Finding[];
  unknowns: string[];
  methodology: string;
  generated_at: string;
}

export interface ActionItem {
  priority: number;
  title: string;
  description: string;
  difficulty: string;
  impact: string;
  category: string;
}

export interface Finding {
  category: string;
  status: string;
  observation: string;
  what_it_means: string;
}

export interface ProgressUpdate {
  progress: number;
  step: string;
}

export async function createAssessment(data: Record<string, unknown>): Promise<AssessmentResponse> {
  const resp = await fetch(`${API_BASE}/assessments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || `HTTP ${resp.status}`);
  }
  return resp.json();
}

export async function getReport(assessmentId: string): Promise<ReportData> {
  const resp = await fetch(`${API_BASE}/assessments/${assessmentId}/report`);
  if (!resp.ok) throw new Error(`Report not ready (${resp.status})`);
  return resp.json();
}

export async function getAssessment(assessmentId: string): Promise<AssessmentResponse> {
  const resp = await fetch(`${API_BASE}/assessments/${assessmentId}`);
  if (!resp.ok) throw new Error(`Assessment not found (${resp.status})`);
  return resp.json();
}

export function subscribeToProgress(
  assessmentId: string,
  onUpdate: (data: ProgressUpdate) => void,
  onComplete: () => void,
  onError: (err: Error) => void,
): EventSource {
  const es = new EventSource(`${API_BASE}/assessments/${assessmentId}/status`);
  es.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onUpdate(data);
      if (data.step === "completed" || data.progress >= 100) {
        es.close();
        onComplete();
      } else if (data.step?.startsWith("failed")) {
        es.close();
        onError(new Error(data.step));
      }
    } catch (e) {
      es.close();
      onError(new Error("Failed to parse progress data"));
    }
  };
  es.onerror = () => {
    es.close();
    onError(new Error("Connection lost"));
  };
  return es;
}
