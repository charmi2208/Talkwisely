"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { CheckCircle, Plus, User, Calendar } from "lucide-react";
import { actionItemsApi, ActionItem } from "@/lib/api/action_items";
import { toast } from "sonner";
import { clsx } from "clsx";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Item, ItemActions, ItemContent, ItemDescription, ItemGroup, ItemMedia, ItemTitle,
} from "@/components/ui/item";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";

export default function ActionItemsPage() {
  const [items, setItems] = useState<ActionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [newDescription, setNewDescription] = useState("");
  const [newOwner, setNewOwner] = useState("");
  const [isAdding, setIsAdding] = useState(false);

  const loadActionItems = async () => {
    setLoading(true);
    try {
      const data = await actionItemsApi.list();
      setItems(data || []);
    } catch {
      // Fallback demo items
      setItems([
        {
          id: "act_1",
          description: "Send Enterprise Cloud PBX pricing proposal to Acme Corp",
          owner: "Sarah Jenkins",
          due_date: "2026-08-22",
          priority: "high",
          status: "pending",
          created_at: new Date().toISOString(),
          conversation_title: "Enterprise PBX Discovery Call",
        },
        {
          id: "act_2",
          description: "Schedule technical API demo for UK/USA virtual numbers integration",
          owner: "Michael Chang",
          due_date: "2026-08-21",
          priority: "urgent",
          status: "in_progress",
          created_at: new Date().toISOString(),
          conversation_title: "Contact Center Technical Review",
        },
        {
          id: "act_3",
          description: "Confirm CRM webhook endpoint security compliance documentation",
          owner: "Alex Rivera",
          due_date: "2026-08-25",
          priority: "medium",
          status: "completed",
          created_at: new Date().toISOString(),
          conversation_title: "Security & CRM Sync Review",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadActionItems();
  }, []);

  const handleToggleStatus = async (item: ActionItem) => {
    const nextStatus = item.status === "completed" ? "pending" : "completed";
    try {
      await actionItemsApi.update(item.id, { status: nextStatus });
      toast.success(nextStatus === "completed" ? "Task completed!" : "Task reopened");
      loadActionItems();
    } catch {
      // Local optimistic state
      setItems((prev) => prev.map((i) => (i.id === item.id ? { ...i, status: nextStatus } : i)));
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDescription.trim()) return;

    try {
      await actionItemsApi.create({
        description: newDescription.trim(),
        owner: newOwner || "Unassigned",
        priority: "medium",
      });
      toast.success("Task created!");
      setNewDescription("");
      setNewOwner("");
      setIsAdding(false);
      loadActionItems();
    } catch {
      toast.error("Failed to create task");
    }
  };

  const safeItems = Array.isArray(items) ? items : [];
  const filteredItems = statusFilter === "all" ? safeItems : safeItems.filter((i) => i.status === statusFilter);

  return (
    <AppShell title="Action Items" subtitle="Track tasks extracted from business conversations by AI">
      <div className="space-y-6">
        {/* Actions bar */}
        <div className="flex items-center justify-between gap-4">
          <ToggleGroup
            type="single"
            variant="outline"
            size="sm"
            value={statusFilter}
            onValueChange={(v) => v && setStatusFilter(v)}
          >
            {["all", "pending", "in_progress", "completed"].map((st) => (
              <ToggleGroupItem key={st} value={st} className="text-xs capitalize">
                {st.replace("_", " ")}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
          <Button size="sm" onClick={() => setIsAdding(!isAdding)}>
            <Plus data-icon="inline-start" />
            Add Task
          </Button>
        </div>

        {/* Create Task Form */}
        {isAdding && (
          <Card size="sm">
            <CardContent>
              <form onSubmit={handleCreate} className="flex flex-col md:flex-row gap-3 items-center">
                <Input
                  type="text"
                  placeholder="Task description..."
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  className="flex-1"
                  required
                />
                <Input
                  type="text"
                  placeholder="Owner (optional)"
                  value={newOwner}
                  onChange={(e) => setNewOwner(e.target.value)}
                  className="md:w-48"
                />
                <Button type="submit">
                  Save
                </Button>
              </form>
            </CardContent>
          </Card>
        )}

        {/* Task list */}
        <ItemGroup className="gap-2.5">
          {filteredItems.map((item) => (
            <Item key={item.id} variant="outline" className="bg-card">
              <ItemMedia>
                <Button
                  variant={item.status === "completed" ? "default" : "outline"}
                  size="icon-xs"
                  className="rounded-full"
                  onClick={() => handleToggleStatus(item)}
                  aria-label={item.status === "completed" ? "Reopen task" : "Complete task"}
                >
                  {item.status === "completed" && <CheckCircle />}
                </Button>
              </ItemMedia>

              <ItemContent className="min-w-0">
                <ItemTitle className={clsx(item.status === "completed" && "line-through text-muted-foreground")}>
                  {item.description}
                </ItemTitle>
                <ItemDescription className="flex items-center gap-4 text-xs">
                  {item.conversation_title && <span>Ref: {item.conversation_title}</span>}
                  {item.owner && (
                    <span className="flex items-center gap-1">
                      <User className="size-3" />
                      {item.owner}
                    </span>
                  )}
                  {item.due_date && (
                    <span className="flex items-center gap-1">
                      <Calendar className="size-3" />
                      {item.due_date}
                    </span>
                  )}
                </ItemDescription>
              </ItemContent>

              <ItemActions>
                <Badge
                  variant={item.priority === "urgent" ? "destructive" : item.priority === "high" ? "secondary" : "outline"}
                  className="capitalize"
                >
                  {item.priority}
                </Badge>
              </ItemActions>
            </Item>
          ))}
        </ItemGroup>
      </div>
    </AppShell>
  );
}
