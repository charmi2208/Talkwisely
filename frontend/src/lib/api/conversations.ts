/**
 * Conversations API functions
 */

import apiClient from "./client";

export interface Conversation {
  id: string;
  title: string;
  conversation_type: string;
  status: string;
  duration_seconds: number | null;
  language: string;
  file_name: string | null;
  lead_score: number | null;
  overall_sentiment: string | null;
  created_at: string;
  occurred_at: string | null;
}

export interface ConversationListResponse {
  items: Conversation[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ConversationDetail extends Conversation {
  error_message: string | null;
  speakers: Array<{
    id: string;
    speaker_label: string;
    display_name: string;
    role: string | null;
    talk_time_seconds: number | null;
  }>;
}

export interface TranscriptSegment {
  id: string;
  speaker_label: string;
  start_time: number;
  end_time: number;
  text: string;
  confidence: number | null;
  sequence_index: number;
  is_important: boolean;
  importance_reason: string | null;
}

export interface TranscriptResponse {
  conversation_id: string;
  language: string;
  duration_seconds: number | null;
  segments: TranscriptSegment[];
  speakers: Array<{ id: string; speaker_label: string; display_name: string; role: string | null }>;
}

export interface ProcessingStatus {
  conversation_id: string;
  conversation_status: string;
  job: {
    id: string;
    status: string;
    progress: number;
    current_step: string | null;
    error_message: string | null;
  } | null;
}

export const conversationsApi = {
  list: async (params?: {
    page?: number;
    page_size?: number;
    conversation_type?: string;
    status?: string;
    search?: string;
  }): Promise<ConversationListResponse> => {
    const res = await apiClient.get<ConversationListResponse>("/conversations", { params });
    return res.data;
  },

  upload: async (
    file: File,
    title: string,
    occurredAt?: string
  ): Promise<{ conversation_id: string; job_id: string; status: string }> => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("title", title);
    if (occurredAt) formData.append("occurred_at", occurredAt);

    const res = await apiClient.post("/conversations/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 120000, // 2 minute timeout for upload
    });
    return res.data;
  },

  get: async (id: string): Promise<ConversationDetail> => {
    const res = await apiClient.get<ConversationDetail>(`/conversations/${id}`);
    return res.data;
  },

  getTranscript: async (id: string): Promise<TranscriptResponse> => {
    const res = await apiClient.get<TranscriptResponse>(`/conversations/${id}/transcript`);
    return res.data;
  },

  getInsights: async (id: string): Promise<any> => {
    const res = await apiClient.get(`/conversations/${id}/insights`);
    return res.data;
  },

  getProcessingStatus: async (id: string): Promise<ProcessingStatus> => {
    const res = await apiClient.get<ProcessingStatus>(`/conversations/${id}/processing-status`);
    return res.data;
  },

  getAudioBlob: async (id: string): Promise<Blob> => {
    const res = await apiClient.get(`/conversations/${id}/audio`, {
      responseType: "blob",
    });
    return res.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/conversations/${id}`);
  },
};
