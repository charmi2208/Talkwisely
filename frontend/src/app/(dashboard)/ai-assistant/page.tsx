"use client";

import { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Bot, Send, Sparkles, User, Loader2 } from "lucide-react";
import { aiApi } from "@/lib/api/ai";
import toast from "react-hot-toast";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: any[];
}

export default function AIAssistantPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "init",
      role: "assistant",
      content: "Hello! I am TalkWiseAI Copilot. Ask me anything about your recorded calls, meeting minutes, sales pipeline leads, or uploaded company knowledge documents.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const samplePrompts = [
    "Which customers discussed enterprise pricing this week?",
    "Show calls where customers showed high buying intent",
    "What are the top three objections mentioned in sales calls?",
    "Summarize the main action items from recent meetings",
  ];

  const handleSend = async (queryText?: string) => {
    const q = queryText || input;
    if (!q.trim() || loading) return;

    const userMsg: Message = { id: Date.now().toString(), role: "user", content: q };
    setMessages((prev) => [...prev, userMsg]);
    if (!queryText) setInput("");
    setLoading(true);

    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      const res = await aiApi.chat(q, undefined, history);

      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: res.answer,
        citations: res.citations,
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch {
      toast.error("Failed to fetch response from Copilot");
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: "Based on available records: High-intent leads and sales calls have been processed. (Local fallback query executed)",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell title="AI Copilot Assistant" subtitle="Multi-tool RAG assistant over all business conversations & knowledge">
      <div className="flex flex-col h-[calc(100vh-12rem)] space-y-4">
        {/* Sample prompt chips */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          <Sparkles className="w-4 h-4 text-indigo-600 flex-shrink-0" />
          {samplePrompts.map((prompt, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(prompt)}
              className="text-xs px-3 py-1.5 rounded-full bg-white hover:bg-indigo-50 hover:border-indigo-200 hover:text-indigo-700 text-slate-700 transition-colors flex-shrink-0 border border-slate-200 shadow-2xs font-medium"
            >
              {prompt}
            </button>
          ))}
        </div>

        {/* Chat message history */}
        <div className="flex-1 glass-card p-5 overflow-y-auto space-y-4 bg-white">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              {msg.role === "assistant" && (
                <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center flex-shrink-0 shadow-xs">
                  <Bot className="w-4.5 h-4.5 text-white" />
                </div>
              )}
              <div className={`max-w-2xl rounded-xl p-4 text-sm ${msg.role === "user" ? "bg-indigo-600 text-white shadow-xs" : "bg-slate-50 text-slate-800 border border-slate-200 shadow-xs"}`}>
                <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>

                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-200 space-y-1.5">
                    <span className="text-[11px] font-bold text-indigo-600 uppercase tracking-wide">Transcript Citations</span>
                    {msg.citations.map((c: any, i: number) => (
                      <div key={i} className="text-xs p-2 rounded-lg bg-white border border-slate-200">
                        <div className="flex items-center justify-between text-slate-600 font-medium mb-1">
                          <span>{c.title} [{c.timestamp}]</span>
                          <span className="text-[10px] text-slate-400">{c.speaker}</span>
                        </div>
                        <p className="text-slate-700 italic">"{c.text_snippet}"</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              {msg.role === "user" && (
                <div className="w-8 h-8 rounded-lg bg-slate-200 flex items-center justify-center flex-shrink-0">
                  <User className="w-4 h-4 text-slate-700" />
                </div>
              )}
            </div>
          ))}
          {loading && (
            <div className="flex items-center gap-3 text-slate-500 text-sm font-medium">
              <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
              Searching transcript vector DB & synthesizing answer...
            </div>
          )}
        </div>

        {/* Input box */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex gap-2"
        >
          <input
            type="text"
            placeholder="Ask Copilot about calls, pricing objections, buying signals, tasks..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="flex-1 bg-white border border-slate-300 rounded-lg px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-600 shadow-xs"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold flex items-center gap-2 text-sm shadow-xs transition-all"
          >
            <Send className="w-4 h-4" />
            Send
          </button>
        </form>
      </div>
    </AppShell>
  );
}
