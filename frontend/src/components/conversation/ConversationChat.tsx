"use client";

import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Bot, Send, User } from "lucide-react";
import { clsx } from "clsx";
import { aiApi, citationLabel, type CopilotChatResponse } from "@/lib/api/ai";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Item, ItemContent, ItemDescription, ItemTitle } from "@/components/ui/item";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Spinner } from "@/components/ui/spinner";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: CopilotChatResponse["citations"];
}

const SUGGESTIONS = [
  "What did the customer want?",
  "What objections came up and were they resolved?",
  "What was agreed as next steps?",
];

export function ConversationChat({ conversationId }: { conversationId: string }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages, loading]);

  const send = async (text?: string) => {
    const query = (text ?? input).trim();
    if (!query || loading) return;
    const history = messages.map((m) => ({ role: m.role, content: m.content }));
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "user", content: query }]);
    setInput("");
    setLoading(true);
    try {
      const res = await aiApi.chat(query, conversationId, history);
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "assistant", content: res.answer, citations: res.citations },
      ]);
    } catch {
      toast.error("The assistant couldn't answer. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="gap-0 py-0">
      <CardHeader className="border-b py-4">
        <CardTitle>Ask about this conversation</CardTitle>
        <CardDescription>Answers are grounded in this conversation&apos;s transcript and insights, with sources.</CardDescription>
      </CardHeader>
      <CardContent className="px-0">
        <ScrollArea className="h-[420px]">
          <div className="space-y-4 p-5">
            {messages.length === 0 && (
              <div className="flex flex-wrap gap-2">
                {SUGGESTIONS.map((s) => (
                  <Button key={s} variant="outline" size="xs" className="rounded-full px-3" onClick={() => send(s)}>
                    {s}
                  </Button>
                ))}
              </div>
            )}
            {messages.map((m) => (
              <div key={m.id} className={clsx("flex gap-3", m.role === "user" ? "justify-end" : "justify-start")}>
                {m.role === "assistant" && (
                  <Avatar className="rounded-lg after:rounded-lg">
                    <AvatarFallback className="rounded-lg bg-primary text-primary-foreground">
                      <Bot className="size-4" />
                    </AvatarFallback>
                  </Avatar>
                )}
                <div
                  className={clsx(
                    "max-w-2xl rounded-xl px-4 py-3 text-sm",
                    m.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"
                  )}
                >
                  <p className="whitespace-pre-wrap leading-relaxed">{m.content}</p>
                  {m.citations && m.citations.length > 0 && (
                    <div className="mt-3 space-y-1.5">
                      <p className="text-[11px] font-semibold text-muted-foreground">Sources</p>
                      {m.citations.map((c, i) => (
                        <Item key={i} variant="outline" size="xs" className="bg-background">
                          <ItemContent>
                            <ItemTitle className="w-full justify-between text-xs">
                              <span>[{c.source}] {c.timestamp ? `${c.timestamp}${c.speaker && c.speaker !== "Multiple speakers" ? `, ${c.speaker}` : ""}` : citationLabel(c)}</span>
                            </ItemTitle>
                            {c.text_snippet && (
                              <ItemDescription className="text-xs italic text-foreground">&ldquo;{c.text_snippet}&rdquo;</ItemDescription>
                            )}
                          </ItemContent>
                        </Item>
                      ))}
                    </div>
                  )}
                </div>
                {m.role === "user" && (
                  <Avatar className="rounded-lg after:rounded-lg">
                    <AvatarFallback className="rounded-lg">
                      <User className="size-4" />
                    </AvatarFallback>
                  </Avatar>
                )}
              </div>
            ))}
            {loading && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Spinner />
                Reading the conversation...
              </div>
            )}
            <div ref={endRef} />
          </div>
        </ScrollArea>
      </CardContent>
      <CardFooter className="border-t py-4">
        <form
          className="flex w-full gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about this call..."
            aria-label="Question about this conversation"
          />
          <Button type="submit" disabled={loading || !input.trim()}>
            <Send data-icon="inline-start" />
            Ask
          </Button>
        </form>
      </CardFooter>
    </Card>
  );
}
