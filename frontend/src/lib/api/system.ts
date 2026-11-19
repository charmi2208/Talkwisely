import { apiClient } from "./client";

export interface AiSettings {
  providers: { kind: string; provider: string; model: string | null; is_mock: boolean; note: string }[];
  task_queue: string;
  llm_api_key_configured: boolean;
  how_to_change: string;
}

export interface AuditLogItem {
  id: string;
  action: string;
  user_name: string | null;
  resource_type: string | null;
  resource_id: string | null;
  details: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
}

export const systemApi = {
  aiSettings: async () => (await apiClient.get<AiSettings>("/system/ai-settings")).data,
  auditLogs: async (limit = 50) => (await apiClient.get<AuditLogItem[]>("/system/audit-logs", { params: { limit } })).data,
};
