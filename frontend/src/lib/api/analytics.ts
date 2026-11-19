import { apiClient } from "./client";

export interface AnalyticsFilters {
  days?: number;
  conversation_type?: string;
  agent_id?: string;
}

export interface AnalyticsOverview {
  period_days: number;
  total_conversations: number;
  total_calls: number;
  total_meetings: number;
  completed_conversations: number;
  in_progress_conversations: number;
  failed_conversations: number;
  conversations_by_type: Record<string, number>;
  high_intent_leads: number;
  sales_opportunities: number;
  average_closing_probability: number | null;
  open_action_items: number;
  overdue_action_items: number;
  average_lead_score: number;
  average_agent_score: number;
  average_sentiment_score: number | null;
  average_duration_seconds: number | null;
  sentiment_distribution: Record<string, number>;
  dominant_sentiment: string | null;
  top_objection_category: string | null;
  changes: {
    total_conversations_pct: number | null;
    high_intent_leads_pct: number | null;
    average_agent_score_points: number | null;
    average_sentiment_score_points: number | null;
  };
}

export interface VolumePoint {
  date: string;
  total: number;
  calls: number;
  meetings: number;
  avg_duration_seconds: number | null;
}

export interface SentimentPoint {
  date: string;
  positive: number;
  neutral: number;
  negative: number;
  mixed: number;
  average_score: number | null;
}

export interface ObjectionStat {
  category: string;
  count: number;
  avg_severity: number;
  resolved: number;
  resolution_rate: number;
}

export interface SalesMetrics {
  purchase_intent_distribution: Record<string, number>;
  pipeline_stage_distribution: Record<string, number>;
  deal_health_distribution: Record<string, number>;
  top_competitors: { name: string; mentions: number }[];
}

export type ScoreKey = "overall" | "empathy" | "listening" | "product_knowledge" | "objection_handling" | "closing";

export interface AgentPerformance {
  average_scores: Record<ScoreKey, number>;
  total_conversations_scored: number;
  leaderboard: {
    user_id: string;
    name: string;
    conversations_scored: number;
    scores: Record<ScoreKey, number | null>;
  }[];
  disclaimer: string;
}

function clean(filters: AnalyticsFilters) {
  return Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== undefined && v !== "" && v !== "all"));
}

export const analyticsApi = {
  overview: async (f: AnalyticsFilters = {}) =>
    (await apiClient.get<AnalyticsOverview>("/analytics/overview", { params: clean(f) })).data,
  volume: async (f: AnalyticsFilters = {}) =>
    (await apiClient.get<{ data: VolumePoint[] }>("/analytics/conversations", { params: clean(f) })).data.data,
  sentiment: async (f: AnalyticsFilters = {}) =>
    (await apiClient.get<{ data: SentimentPoint[] }>("/analytics/sentiment", { params: clean(f) })).data.data,
  objections: async (f: AnalyticsFilters = {}) =>
    (await apiClient.get<{ data: ObjectionStat[] }>("/analytics/objections", { params: clean(f) })).data.data,
  sales: async (f: AnalyticsFilters = {}) =>
    (await apiClient.get<SalesMetrics>("/analytics/sales", { params: clean(f) })).data,
  agents: async (f: AnalyticsFilters = {}) =>
    (await apiClient.get<AgentPerformance>("/analytics/agents", { params: clean(f) })).data,
  topics: async (f: AnalyticsFilters = {}) =>
    (await apiClient.get<{ data: { topic: string; count: number }[] }>("/analytics/topics", { params: clean(f) })).data.data,
};
