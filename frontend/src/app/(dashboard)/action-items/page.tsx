"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { CheckCircle, Plus, User, Calendar, Pencil, Trash2, Sparkles, CheckSquare } from "lucide-react";
import { actionItemsApi, type ActionItem } from "@/lib/api/action_items";
import { apiErrorMessage } from "@/lib/api/errors";
import { formatDate, humanize } from "@/lib/format";
import { toast } from "sonner";
import { clsx } from "clsx";
import { ErrorState, PageLoading } from "@/components/common/ErrorState";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Item, ItemActions, ItemContent, ItemDescription, ItemGroup, ItemMedia, ItemTitle,
} from "@/components/ui/item";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";

const PRIORITIES = ["low", "medium", "high", "urgent"];
const STATUSES = ["pending", "in_progress", "overdue", "completed"];

/** ISO calendar date for <input type="date">, or "" when the due date is free text */
function isoDay(value: string | null | undefined): string {
  return value && /^\d{4}-\d{2}-\d{2}/.test(value) ? value.slice(0, 10) : "";
}

interface EditForm {
  description: string;
  owner: string;
  due_date: string;
  priority: string;
  status: string;
}

export default function ActionItemsPage() {
  const [items, setItems] = useState<ActionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [isAdding, setIsAdding] = useState(false);
  const [newTask, setNewTask] = useState({ description: "", owner: "", due_date: "", priority: "medium" });
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<ActionItem | null>(null);
  const [form, setForm] = useState<EditForm | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState<ActionItem | null>(null);

  const loadActionItems = useCallback(async () => {
    try {
      const list = await actionItemsApi.list();
      setItems(list);
      setError("");
    } catch (err) {
      setError(apiErrorMessage(err, "Action items couldn't be loaded."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadActionItems();
  }, [loadActionItems]);

  const replace = (updated: ActionItem) =>
    setItems((prev) => prev.map((i) => (i.id === updated.id ? { ...updated, conversation_title: i.conversation_title } : i)));

  const handleToggleStatus = async (item: ActionItem) => {
    const nextStatus = item.status === "completed" ? "pending" : "completed";
    try {
      replace(await actionItemsApi.update(item.id, { status: nextStatus }));
      toast.success(nextStatus === "completed" ? "Task completed" : "Task reopened");
    } catch (err) {
      toast.error(apiErrorMessage(err, "Couldn't update the task"));
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTask.description.trim()) return;
    setCreating(true);
    try {
      const created = await actionItemsApi.create({
        description: newTask.description.trim(),
        owner: newTask.owner.trim() || undefined,
        due_date: newTask.due_date || undefined,
        priority: newTask.priority,
      });
      setItems((prev) => [created, ...prev]);
      toast.success("Task created");
      setNewTask({ description: "", owner: "", due_date: "", priority: "medium" });
      setIsAdding(false);
    } catch (err) {
      toast.error(apiErrorMessage(err, "Failed to create task"));
    } finally {
      setCreating(false);
    }
  };

  const openEditor = (item: ActionItem) => {
    setEditing(item);
    setForm({
      description: item.description,
      owner: item.owner ?? "",
      due_date: isoDay(item.due_date),
      priority: item.priority,
      status: item.status === "overdue" ? "pending" : item.status,
    });
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editing || !form) return;
    setSaving(true);
    try {
      const keepFreeTextDue = !form.due_date && editing.due_date && !isoDay(editing.due_date);
      replace(await actionItemsApi.update(editing.id, {
        description: form.description,
        owner: form.owner,
        priority: form.priority,
        status: form.status,
        ...(keepFreeTextDue ? {} : { due_date: form.due_date }),
      }));
      toast.success("Task updated");
      setEditing(null);
    } catch (err) {
      toast.error(apiErrorMessage(err, "Couldn't save the task"));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleting) return;
    try {
      await actionItemsApi.delete(deleting.id);
      setItems((prev) => prev.filter((i) => i.id !== deleting.id));
      toast.success("Task deleted");
    } catch (err) {
      toast.error(apiErrorMessage(err, "Couldn't delete the task"));
    } finally {
      setDeleting(null);
    }
  };

  const counts = Object.fromEntries(STATUSES.map((s) => [s, items.filter((i) => i.status === s).length]));
  const filteredItems = statusFilter === "all" ? items : items.filter((i) => i.status === statusFilter);

  return (
    <AppShell title="Action Items" subtitle="Track tasks extracted from business conversations by AI">
      <div className="space-y-6">
        {/* Actions bar */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <ToggleGroup
            type="single"
            variant="outline"
            size="sm"
            value={statusFilter}
            onValueChange={(v) => v && setStatusFilter(v)}
          >
            <ToggleGroupItem value="all" className="text-xs">All ({items.length})</ToggleGroupItem>
            {STATUSES.map((st) => (
              <ToggleGroupItem key={st} value={st} className="text-xs">
                {humanize(st)} ({counts[st]})
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
              <form onSubmit={handleCreate} className="flex flex-col md:flex-row gap-3 md:items-center">
                <Input
                  type="text"
                  placeholder="Task description..."
                  value={newTask.description}
                  onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
                  className="flex-1"
                  aria-label="Task description"
                  required
                />
                <Input
                  type="text"
                  placeholder="Owner (optional)"
                  value={newTask.owner}
                  onChange={(e) => setNewTask({ ...newTask, owner: e.target.value })}
                  className="md:w-44"
                  aria-label="Owner"
                />
                <Input
                  type="date"
                  value={newTask.due_date}
                  onChange={(e) => setNewTask({ ...newTask, due_date: e.target.value })}
                  className="md:w-40"
                  aria-label="Due date"
                />
                <Select value={newTask.priority} onValueChange={(v) => setNewTask({ ...newTask, priority: v })}>
                  <SelectTrigger className="md:w-32" aria-label="Priority"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {PRIORITIES.map((p) => <SelectItem key={p} value={p}>{humanize(p)}</SelectItem>)}
                  </SelectContent>
                </Select>
                <Button type="submit" disabled={creating}>
                  {creating && <Spinner data-icon="inline-start" />}
                  Save
                </Button>
              </form>
            </CardContent>
          </Card>
        )}

        {/* Task list */}
        {loading && items.length === 0 ? (
          <PageLoading />
        ) : error ? (
          <ErrorState message={error} onRetry={() => { setLoading(true); setError(""); loadActionItems(); }} />
        ) : filteredItems.length === 0 ? (
          <Empty className="border bg-card">
            <EmptyHeader>
              <EmptyMedia variant="icon"><CheckSquare /></EmptyMedia>
              <EmptyTitle>{statusFilter === "all" ? "No action items yet" : `No ${humanize(statusFilter).toLowerCase()} tasks`}</EmptyTitle>
              <EmptyDescription>Tasks extracted from analyzed conversations appear here, and you can add your own.</EmptyDescription>
            </EmptyHeader>
          </Empty>
        ) : (
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
                  <ItemDescription className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
                    {item.conversation_id && item.conversation_title && (
                      <Link href={`/conversations/${item.conversation_id}`} className="hover:underline">
                        Ref: {item.conversation_title}
                      </Link>
                    )}
                    {item.owner && (
                      <span className="flex items-center gap-1">
                        <User className="size-3" />
                        {item.owner}
                      </span>
                    )}
                    {item.due_date && (
                      <span className="flex items-center gap-1">
                        <Calendar className="size-3" />
                        Due {isoDay(item.due_date) ? formatDate(item.due_date) : item.due_date}
                      </span>
                    )}
                    {item.is_ai_generated && (
                      <span className="flex items-center gap-1">
                        <Sparkles className="size-3" />
                        AI-extracted
                      </span>
                    )}
                  </ItemDescription>
                </ItemContent>

                <ItemActions>
                  {item.status === "overdue" && <Badge variant="destructive">Overdue</Badge>}
                  {item.status === "in_progress" && <Badge variant="outline">In progress</Badge>}
                  <Badge
                    variant={item.priority === "urgent" ? "destructive" : item.priority === "high" ? "secondary" : "outline"}
                    className="capitalize"
                  >
                    {item.priority}
                  </Badge>
                  <Button variant="ghost" size="icon-xs" onClick={() => openEditor(item)} aria-label="Edit task">
                    <Pencil />
                  </Button>
                  <Button variant="ghost" size="icon-xs" onClick={() => setDeleting(item)} aria-label="Delete task">
                    <Trash2 />
                  </Button>
                </ItemActions>
              </Item>
            ))}
          </ItemGroup>
        )}
      </div>

      <Dialog open={editing !== null} onOpenChange={(open) => !open && setEditing(null)}>
        <DialogContent>
          {form && (
            <form onSubmit={handleSave} className="contents">
              <DialogHeader>
                <DialogTitle>Edit task</DialogTitle>
                {editing?.due_date && !isoDay(editing.due_date) && (
                  <DialogDescription>The AI recorded the due date as &quot;{editing.due_date}&quot;. Pick a date to track it as overdue.</DialogDescription>
                )}
              </DialogHeader>
              <FieldGroup className="gap-4">
                <Field>
                  <FieldLabel htmlFor="edit-description">Task</FieldLabel>
                  <Input id="edit-description" required value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
                </Field>
                <div className="grid grid-cols-2 gap-4">
                  <Field>
                    <FieldLabel htmlFor="edit-owner">Owner</FieldLabel>
                    <Input id="edit-owner" value={form.owner} onChange={(e) => setForm({ ...form, owner: e.target.value })} />
                  </Field>
                  <Field>
                    <FieldLabel htmlFor="edit-due">Due date</FieldLabel>
                    <Input id="edit-due" type="date" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} />
                  </Field>
                  <Field>
                    <FieldLabel htmlFor="edit-priority">Priority</FieldLabel>
                    <Select value={form.priority} onValueChange={(v) => setForm({ ...form, priority: v })}>
                      <SelectTrigger id="edit-priority"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {PRIORITIES.map((p) => <SelectItem key={p} value={p}>{humanize(p)}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </Field>
                  <Field>
                    <FieldLabel htmlFor="edit-status">Status</FieldLabel>
                    <Select value={form.status} onValueChange={(v) => setForm({ ...form, status: v })}>
                      <SelectTrigger id="edit-status"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {["pending", "in_progress", "completed"].map((s) => <SelectItem key={s} value={s}>{humanize(s)}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </Field>
                </div>
              </FieldGroup>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setEditing(null)}>Cancel</Button>
                <Button type="submit" disabled={saving}>
                  {saving && <Spinner data-icon="inline-start" />}
                  Save
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>

      <AlertDialog open={deleting !== null} onOpenChange={(open) => !open && setDeleting(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this task?</AlertDialogTitle>
            <AlertDialogDescription>&quot;{deleting?.description}&quot; will be removed. This can&apos;t be undone.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={handleDelete}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AppShell>
  );
}
