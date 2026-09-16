import { apiClient } from "./client";

export interface Citation {
  source: number;
  doc_type?: "transcript" | "summary" | "knowledge_base" | null;
  conversation_id?: string | null;
  document_id?: string | null;
  title?: string | null;
  timestamp?: string | null;
  start_time?: number | null;
  speaker?: string | null;
  text_snippet?: string;
  score?: number;
}

/** "Title at 01:23, Customer" style label for a citation. */
export function citationLabel(c: Citation): string {
  let label = c.title || (c.doc_type === "knowledge_base" ? "Knowledge base" : "Conversation");
  if (c.timestamp) label += ` at ${c.timestamp}`;
  if (c.doc_type === "summary") label += " (summary)";
  if (c.speaker && c.speaker !== "Multiple speakers") label += `, ${c.speaker}`;
  return label;
}

export interface CopilotChatResponse {
  answer: string;
  query: string;
  citations: Citation[];
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
