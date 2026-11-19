import { apiClient } from "./client";

export interface MeetingItem {
  conversation_id: string;
  title: string;
  conversation_type: string;
  objective: string | null;
  participants_summary: string | null;
  decisions_count: number;
  action_items_count: number;
  open_questions_count: number;
  next_meeting: string | null;
  duration_seconds: number | null;
  occurred_at: string | null;
  created_at: string;
}

export interface MeetingMinutes {
  conversation_id: string;
  title: string;
  objective: string | null;
  participants_summary: string | null;
  discussion_points: string[];
  decisions: string[];
  action_items_summary: string[];
  open_questions: string[];
  risks: string[];
  next_steps: string[];
  next_meeting: string | null;
  formatted_markdown: string;
}

export const meetingsApi = {
  list: async (params: { meetings_only?: boolean; search?: string } = {}) =>
    (await apiClient.get<MeetingItem[]>("/meetings", { params })).data,
  minutes: async (conversationId: string) =>
    (await apiClient.get<MeetingMinutes>(`/meetings/${conversationId}/minutes`)).data,
};
