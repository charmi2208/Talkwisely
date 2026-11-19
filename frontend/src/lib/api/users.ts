import { apiClient } from "./client";

export interface TeamMember {
  id: string;
  email: string;
  full_name: string;
  role: "admin" | "manager" | "agent";
  organization_id: string;
  organization_name?: string | null;
  is_active: boolean;
  last_login_at: string | null;
  conversation_count: number | null;
  created_at: string;
}

export interface Preferences {
  auto_action_items: boolean;
  lead_intent_alerts: boolean;
  pbx_auto_sync: boolean;
}

export const usersApi = {
  list: async () => (await apiClient.get<TeamMember[]>("/users")).data,
  create: async (data: { email: string; full_name: string; role: string; temporary_password: string }) =>
    (await apiClient.post<TeamMember>("/users", data)).data,
  update: async (id: string, data: { full_name?: string; is_active?: boolean }) =>
    (await apiClient.patch<TeamMember>(`/users/${id}`, data)).data,
  setRole: async (id: string, role: string) =>
    (await apiClient.patch<TeamMember>(`/users/${id}/role`, { role })).data,
  updateMe: async (full_name: string) => (await apiClient.patch<TeamMember>("/users/me", { full_name })).data,
  changePassword: async (current_password: string, new_password: string) =>
    apiClient.post("/users/me/password", { current_password, new_password }),
  preferences: async () => (await apiClient.get<Preferences>("/users/me/preferences")).data,
  savePreferences: async (prefs: Partial<Preferences>) =>
    (await apiClient.put<Preferences>("/users/me/preferences", prefs)).data,
};
