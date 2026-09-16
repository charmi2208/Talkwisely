import { apiClient } from "./client";

export interface CopilotChatResponse {
  answer: str;
  query: str;
  citations: Array<{
    conversation_id?: string;
    title?: string;
    timestamp?: string;
    speaker?: string;
    text_snippet?: string;
    score?: number;
  }>;
  context_count: number;
}

export interface GenerateEmailRequest {
  conversation_id: string;
  email_type?: string;
  tone?: string;
  recipient_name?: string;
  sender_name?: string;
}

export interface GenerateEmailResponse {
  subject: string;
  body: string;
  suggested_actions: string[];
  email_type: string;
  tone: string;
}

export const aiApi = {
  chat: async (query: string, conversationId?: string, chatHistory?: any[]) => {
    const res = await apiClient.post<CopilotChatResponse>("/ai/copilot/chat", {
      query,
      conversation_id: conversationId,
      chat_history: chatHistory,
    });
    return res.data;
  },

  generateEmail: async (data: GenerateEmailRequest) => {
    const res = await apiClient.post<GenerateEmailResponse>("/ai/generate-email", data);
    return res.data;
  },

  naturalLanguageQuery: async (query: string) => {
    const res = await apiClient.post<any>("/ai/natural-language-query", { query });
    return res.data;
  },
};
