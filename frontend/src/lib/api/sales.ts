import { apiClient } from "./client";

export const PIPELINE_STAGES = ["new", "contacted", "qualified", "demo", "proposal", "negotiation", "won", "lost"] as const;
export type PipelineStage = (typeof PIPELINE_STAGES)[number];

export interface SalesLead {
  conversation_id: string;
  title: string;
  lead_score: number | null;
  purchase_intent: string | null;
  deal_health: string | null;
  pipeline_stage: string | null;
  budget_range: string | null;
  timeline: string | null;
  decision_maker_present: boolean;
  closing_probability: number | null;
  next_action: string | null;
  owner_name: string | null;
  last_activity_at: string;
  created_at: string;
}

export const salesApi = {
  pipeline: async (params: { stage?: string; min_score?: number; purchase_intent?: string; deal_health?: string; search?: string } = {}) =>
    (await apiClient.get<SalesLead[]>("/sales/pipeline", { params })).data,
  setStage: async (conversationId: string, stage: string) =>
    (await apiClient.patch<SalesLead>(`/sales/leads/${conversationId}`, { stage })).data,
};
