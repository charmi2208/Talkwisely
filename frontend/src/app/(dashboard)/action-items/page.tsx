"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { CheckCircle, Plus, User, Calendar } from "lucide-react";
import { actionItemsApi, ActionItem } from "@/lib/api/action_items";
import toast from "react-hot-toast";
import { clsx } from "clsx";

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
          <div className="flex items-center gap-2">
            {["all", "pending", "in_progress", "completed"].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={clsx(
                  "px-3 py-1.5 rounded-lg text-xs font-semibold capitalize transition-all",
                  statusFilter === st ? "bg-indigo-600 text-white shadow-xs" : "bg-slate-100 text-slate-600 hover:text-slate-900 hover:bg-slate-200"
                )}
              >
                {st.replace("_", " ")}
              </button>
            ))}
          </div>
          <button
            onClick={() => setIsAdding(!isAdding)}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-xs font-semibold text-white shadow-sm transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Task
          </button>
        </div>

        {/* Create Task Form */}
        {isAdding && (
          <form onSubmit={handleCreate} className="glass-card p-4 flex flex-col md:flex-row gap-3 items-center">
            <input
              type="text"
              placeholder="Task description..."
              value={newDescription}
              onChange={(e) => setNewDescription(e.target.value)}
              className="flex-1 bg-white border border-slate-300 rounded-lg px-3.5 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-600"
              required
            />
            <input
              type="text"
              placeholder="Owner (optional)"
              value={newOwner}
              onChange={(e) => setNewOwner(e.target.value)}
              className="w-48 bg-white border border-slate-300 rounded-lg px-3.5 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-600"
            />
            <button type="submit" className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-xs font-semibold text-white shadow-xs">
              Save
            </button>
          </form>
        )}

        {/* Task list */}
        <div className="space-y-2.5">
          {filteredItems.map((item) => (
            <div key={item.id} className="glass-card p-4 flex items-center gap-4 hover:border-slate-300 transition-all">
              <button
                onClick={() => handleToggleStatus(item)}
                className={clsx(
                  "w-5 h-5 rounded-full border flex items-center justify-center transition-colors flex-shrink-0",
                  item.status === "completed" ? "bg-emerald-600 border-emerald-600 text-white" : "border-slate-300 hover:border-indigo-600"
                )}
              >
                {item.status === "completed" && <CheckCircle className="w-3.5 h-3.5" />}
              </button>

              <div className="flex-1 min-w-0">
                <p className={clsx("text-sm font-semibold", item.status === "completed" ? "line-through text-slate-400" : "text-slate-900")}>
                  {item.description}
                </p>
                <div className="flex items-center gap-4 mt-0.5 text-xs text-slate-500">
                  {item.conversation_title && <span>Ref: {item.conversation_title}</span>}
                  {item.owner && (
                    <span className="flex items-center gap-1">
                      <User className="w-3 h-3 text-slate-400" />
                      {item.owner}
                    </span>
                  )}
                  {item.due_date && (
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3 h-3 text-slate-400" />
                      {item.due_date}
                    </span>
                  )}
                </div>
              </div>

              <span className={clsx("text-xs px-2.5 py-0.5 rounded-full capitalize font-semibold border",
                item.priority === "urgent" ? "badge-high" :
                item.priority === "high" ? "badge-medium" :
                "badge-neutral"
              )}>
                {item.priority}
              </span>
            </div>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
