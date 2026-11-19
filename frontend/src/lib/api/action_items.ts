import { apiClient } from "./client";

export interface ActionItem {
  id: string;
  conversation_id?: string;
  description: string;
  owner?: string;
  due_date?: string | null;
  due_at?: string | null;
  priority: string;
  status: string;
  source_timestamp?: number | null;
  related_topic?: string | null;
  created_at: string;
  completed_at?: string | null;
  is_ai_generated?: boolean;
  conversation_title?: string | null;
}

export const actionItemsApi = {
  list: async (params?: { priority?: string; status?: string; conversation_id?: string }) => {
    const res = await apiClient.get<ActionItem[]>("/action-items", { params });
    return res.data;
  },

  create: async (data: { conversation_id?: string; description: string; owner?: string; due_date?: string; priority?: string }) => {
    const res = await apiClient.post<ActionItem>("/action-items", data);
    return res.data;
  },

  update: async (id: string, data: { description?: string; owner?: string; due_date?: string; priority?: string; status?: string }) => {
    const res = await apiClient.patch<ActionItem>(`/action-items/${id}`, data);
    return res.data;
  },

  delete: async (id: string) => {
    const res = await apiClient.delete(`/action-items/${id}`);
    return res.data;
  },
};
