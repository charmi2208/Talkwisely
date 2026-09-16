"use client";

import { useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { Bot, Send, Sparkles, User } from "lucide-react";
import { aiApi, citationLabel, type Citation } from "@/lib/api/ai";
import { toast } from "sonner";
import { clsx } from "clsx";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Item, ItemContent, ItemDescription, ItemTitle } from "@/components/ui/item";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Spinner } from "@/components/ui/spinner";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
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

    const userMsg: Message = { id: crypto.randomUUID(), role: "user", content: q };
    setMessages((prev) => [...prev, userMsg]);
    if (!queryText) setInput("");
    setLoading(true);

    try {
      const history = messages.filter((m) => m.id !== "init").map((m) => ({ role: m.role, content: m.content }));
      const res = await aiApi.chat(q, undefined, history);

      const botMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: res.answer,
        citations: res.citations,
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch {
      toast.error("Copilot couldn't answer right now. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell title="AI Copilot Assistant" subtitle="Multi-tool RAG assistant over all business conversations & knowledge">
      <div className="flex flex-col h-[calc(100vh-12rem)] space-y-4">
        {/* Sample prompt chips */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          <Sparkles className="size-4 shrink-0" />
          {samplePrompts.map((prompt, idx) => (
            <Button
              key={idx}
              variant="outline"
              size="xs"
              onClick={() => handleSend(prompt)}
              className="rounded-full px-3"
            >
              {prompt}
            </Button>
          ))}
        </div>

        {/* Chat message history */}
        <Card className="flex-1 min-h-0 py-0">
          <ScrollArea className="h-full">
            <div className="p-5 space-y-4">
              {messages.map((msg) => (
                <div key={msg.id} className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                  {msg.role === "assistant" && (
                    <Avatar className="rounded-lg after:rounded-lg">
                      <AvatarFallback className="rounded-lg bg-primary text-primary-foreground">
                        <Bot className="size-4" />
                      </AvatarFallback>
                    </Avatar>
                  )}
                  <div
                    className={clsx(
                      "max-w-2xl rounded-xl p-4 text-sm",
                      msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"
                    )}
                  >
                    <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>

                    {msg.citations && msg.citations.length > 0 && (
                      <div className="mt-3 space-y-1.5">
                        <Separator className="mb-3" />
                        <span className="text-[11px] font-semibold text-muted-foreground">Sources</span>
                        {msg.citations.map((c) => {
                          const body = (
                            <ItemContent>
                              <ItemTitle className="text-xs">[{c.source}] {citationLabel(c)}</ItemTitle>
                              {c.text_snippet && (
                                <ItemDescription className="text-xs italic text-foreground">&ldquo;{c.text_snippet}&rdquo;</ItemDescription>
                              )}
                            </ItemContent>
                          );
                          return c.conversation_id ? (
                            <Item key={c.source} variant="outline" size="xs" className="bg-background" asChild>
                              <Link href={`/conversations/${c.conversation_id}`}>{body}</Link>
                            </Item>
                          ) : (
                            <Item key={c.source} variant="outline" size="xs" className="bg-background">{body}</Item>
                          );
                        })}
                      </div>
                    )}
                  </div>
                  {msg.role === "user" && (
                    <Avatar className="rounded-lg after:rounded-lg">
                      <AvatarFallback className="rounded-lg">
                        <User className="size-4" />
                      </AvatarFallback>
                    </Avatar>
                  )}
                </div>
              ))}
              {loading && (
                <div className="flex items-center gap-3 text-muted-foreground text-sm font-medium">
                  <Spinner />
                  Searching transcript vector DB & synthesizing answer...
                </div>
              )}
            </div>
          </ScrollArea>
        </Card>

        {/* Input box */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex gap-2"
        >
          <Input
            type="text"
            placeholder="Ask Copilot about calls, pricing objections, buying signals, tasks..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="flex-1 h-10"
          />
          <Button type="submit" size="lg" disabled={loading || !input.trim()}>
            <Send data-icon="inline-start" />
            Send
          </Button>
        </form>
      </div>
    </AppShell>
  );
}
