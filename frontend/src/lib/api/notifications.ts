/**
 * In-app notifications API.
 */

import apiClient from "./client";

export interface AppNotification {
  id: string;
  conversation_id: string | null;
  type: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export const notificationsApi = {
  list: async () => {
    const res = await apiClient.get<AppNotification[]>("/notifications");
    return res.data;
  },

  markRead: async (id: string) => {
    const res = await apiClient.post<AppNotification>(`/notifications/${id}/read`);
    return res.data;
  },

  markAllRead: async () => {
    await apiClient.post("/notifications/read-all");
  },
};
