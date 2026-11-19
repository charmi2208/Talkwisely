import { apiClient } from "./client";

export interface IntegrationConfigField {
  key: string;
  label: string;
  type: "text" | "number" | "email";
  description: string;
  min?: number | null;
  max?: number | null;
}

export interface Integration {
  key: "talkwisely" | "meetings" | "crm" | "calendar" | "email";
  name: string;
  description: string;
  provider: string;
  provider_label: string;
  is_enabled: boolean;
  is_mock: boolean;
  status: "mock_active" | "disabled";
  config: Record<string, string | number>;
  config_fields: IntegrationConfigField[];
  providers: { key: string; label: string; available: boolean; note: string }[];
  last_synced_at: string | null;
}

export const integrationsApi = {
  list: async () => (await apiClient.get<Integration[]>("/integrations")).data,
  update: async (key: string, data: { is_enabled?: boolean; provider?: string; config?: Record<string, unknown> }) =>
    (await apiClient.put<Integration>(`/integrations/${key}`, data)).data,
  test: async (key: string) =>
    (await apiClient.post<{ ok: boolean; latency_ms: number | null; message: string }>(`/integrations/${key}/test`)).data,
  /** Import new recordings: "talkwisely" (PBX calls) or "meetings" (Zoom, Meet, Teams) */
  sync: async (key: "talkwisely" | "meetings") =>
    (await apiClient.post<{ imported: number; skipped: number; message: string }>(`/integrations/${key}/sync`)).data,
  syncPbx: async () =>
    (await apiClient.post<{ imported: number; skipped: number; message: string }>("/integrations/talkwisely/sync")).data,
};
