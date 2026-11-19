import { apiClient } from "./client";

export interface Report {
  id: string | null;
  title: string;
  report_type: string;
  time_period: string;
  executive_summary: string;
  key_insights: string[];
  trends: Record<string, unknown>[];
  risks_and_bottlenecks: string[];
  strategic_recommendations: string[];
  formatted_markdown: string;
  created_at: string | null;
  created_by_name: string | null;
}

export interface ReportListItem {
  id: string;
  title: string;
  report_type: string;
  time_period: string;
  date_from: string | null;
  date_to: string | null;
  created_at: string;
  created_by_name: string | null;
}

export const REPORT_TYPES = [
  { value: "executive", label: "Executive report" },
  { value: "conversation", label: "Conversation report" },
  { value: "sales", label: "Sales report" },
  { value: "team_qa", label: "Agent performance report" },
  { value: "sentiment", label: "Customer sentiment report" },
  { value: "objections", label: "Objection report" },
] as const;

export const REPORT_PERIODS = [
  { value: "daily", label: "Last 24 hours" },
  { value: "weekly", label: "Last 7 days" },
  { value: "monthly", label: "Last 30 days" },
  { value: "quarterly", label: "Last 90 days" },
] as const;

export const reportsApi = {
  generate: async (report_type: string, time_period: string) =>
    (await apiClient.post<Report>("/reports/generate", { report_type, time_period }, { timeout: 120000 })).data,
  list: async () => (await apiClient.get<ReportListItem[]>("/reports")).data,
  get: async (id: string) => (await apiClient.get<Report>(`/reports/${id}`)).data,
};
