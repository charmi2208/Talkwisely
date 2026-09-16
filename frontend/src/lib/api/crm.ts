/**
 * CRM proposal API — AI-proposed CRM changes that need human approval.
 */

import apiClient from "./client";

export type CRMChange = { from?: unknown; to?: unknown } | string | number | null;

export interface CRMProposal {
  id: string;
  conversation_id: string;
  crm_entity_type: string;
  proposed_changes: Record<string, CRMChange>;
  status: "pending" | "rejected" | "applied";
  approved_by: string | null;
  applied_at: string | null;
  created_at: string;
  conversation_title: string | null;
  crm_provider: string;
}

export const crmApi = {
  list: async (params?: { conversation_id?: string; status_filter?: string }) => {
    const res = await apiClient.get<CRMProposal[]>("/crm/proposals", { params });
    return res.data;
  },

  approve: async (id: string, editedChanges?: Record<string, CRMChange>) => {
    const res = await apiClient.post<CRMProposal>(
      `/crm/proposals/${id}/approve`,
      editedChanges ? { edited_changes: editedChanges } : {}
    );
    return res.data;
  },

  reject: async (id: string) => {
    const res = await apiClient.post<CRMProposal>(`/crm/proposals/${id}/reject`);
    return res.data;
  },
};
