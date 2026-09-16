"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { conversationsApi, type Conversation } from "@/lib/api/conversations";
import {
  Upload, Search, Plus, PhoneCall, Clock, TrendingUp,
  CheckCircle, AlertCircle, Hourglass, FileAudio, FileVideo, ArrowUpRight, Trash2
} from "lucide-react";
import { toast } from "sonner";
import { clsx } from "clsx";
import { formatDistanceToNow } from "date-fns";
import { parseApiDate } from "@/lib/dates";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogClose, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import {
  Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle,
} from "@/components/ui/empty";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { InputGroup, InputGroupAddon, InputGroupInput } from "@/components/ui/input-group";
import {
  Item, ItemActions, ItemContent, ItemDescription, ItemGroup, ItemMedia, ItemTitle,
} from "@/components/ui/item";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { label: string; icon: React.ElementType }> = {
    completed: { label: "Completed", icon: CheckCircle },
    failed: { label: "Failed", icon: AlertCircle },
    processing: { label: "Processing", icon: Spinner },
    analyzing: { label: "Analyzing", icon: Hourglass },
    transcribing: { label: "Transcribing", icon: Hourglass },
    queued: { label: "Queued", icon: Hourglass },
    uploaded: { label: "Uploaded", icon: FileAudio },
  };
  const { label, icon: Icon } = config[status] || config.uploaded;
  return (
    <Badge variant={status === "failed" ? "destructive" : status === "completed" ? "secondary" : "outline"}>
      <Icon
        data-icon="inline-start"
        className={clsx(
          status === "completed" && "text-success",
          status === "analyzing" && "animate-spin"
        )}
      />
      {label}
    </Badge>
  );
}

function SentimentBadge({ sentiment }: { sentiment: string }) {
  return (
    <Badge
      variant={sentiment === "negative" ? "destructive" : sentiment === "positive" ? "secondary" : "outline"}
      className="capitalize"
    >
      {sentiment}
    </Badge>
  );
}

function UploadModal({ onClose, onUploaded }: { onClose: () => void; onUploaded: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const handleFile = (f: File) => {
    setFile(f);
    if (!title) setTitle(f.name.replace(/\.[^/.]+$/, ""));
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !title.trim()) return;
    setUploading(true);
    try {
      await conversationsApi.upload(file, title.trim());
      toast.success("File uploaded! Processing has started.");
      onUploaded();
      onClose();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Upload failed. Please try again.";
      toast.error(msg);
    } finally {
      setUploading(false);
    }
  };

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Upload Recording</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <FieldGroup className="gap-4">
            {/* Drop zone */}
            <Empty
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => document.getElementById("file-input")?.click()}
              className={clsx(
                "cursor-pointer border p-8 transition-colors",
                dragOver ? "border-primary bg-muted" : "hover:bg-muted/50",
                file && "border-success bg-success/10"
              )}
            >
              <Input
                id="file-input"
                type="file"
                accept=".mp3,.wav,.m4a,.ogg,.flac,.mp4,.avi,.mov,.mkv,.webm"
                className="hidden"
                onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
              />
              {file ? (
                <div className="flex items-center justify-center gap-3">
                  {file.type.startsWith("video") ? <FileVideo className="size-8 text-success" /> : <FileAudio className="size-8 text-success" />}
                  <div className="text-left">
                    <p className="text-sm font-semibold text-success">{file.name}</p>
                    <p className="text-xs text-muted-foreground">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                  </div>
                </div>
              ) : (
                <EmptyHeader>
                  <EmptyMedia variant="icon">
                    <Upload />
                  </EmptyMedia>
                  <EmptyTitle className="text-sm">Drag & drop or click to upload</EmptyTitle>
                  <EmptyDescription className="text-xs">MP3, WAV, M4A, MP4, MOV — up to 500MB</EmptyDescription>
                </EmptyHeader>
              )}
            </Empty>

            <Field>
              <FieldLabel htmlFor="conversation-title">Conversation Title</FieldLabel>
              <Input
                id="conversation-title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Sales Call — Acme Corp"
                required
              />
            </Field>

            <DialogFooter className="pt-2">
              <DialogClose asChild>
                <Button type="button" variant="outline" className="flex-1">
                  Cancel
                </Button>
              </DialogClose>
              <Button type="submit" disabled={!file || !title || uploading} className="flex-1">
                {uploading ? <Spinner data-icon="inline-start" /> : <Upload data-icon="inline-start" />}
                {uploading ? "Uploading..." : "Upload & Analyze"}
              </Button>
            </DialogFooter>
          </FieldGroup>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function ConversationsPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [showUpload, setShowUpload] = useState(false);
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState("");
  const [page, setPage] = useState(1);

  const loadConversations = useCallback(async () => {
    setLoading(true);
    try {
      const data = await conversationsApi.list({
        page,
        page_size: 20,
        search: search || undefined,
        conversation_type: filterType || undefined,
      });
      setConversations(data.items);
      setTotal(data.total);
    } catch (err) {
      toast.error("Failed to load conversations");
    } finally {
      setLoading(false);
    }
  }, [page, search, filterType]);

  useEffect(() => { loadConversations(); }, [loadConversations]);

  const handleDeleteConversation = async (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await conversationsApi.delete(id);
      toast.success("Conversation deleted");
      loadConversations();
    } catch {
      toast.error("Failed to delete conversation");
    }
  };

  const convTypes = ["sales", "customer_support", "product_demo", "follow_up", "internal_meeting", "client_meeting"];

  return (
    <AppShell title="Conversations" subtitle={`${total} total conversations`}>
      {showUpload && (
        <UploadModal onClose={() => setShowUpload(false)} onUploaded={loadConversations} />
      )}

      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <InputGroup className="flex-1">
          <InputGroupInput
            type="text"
            placeholder="Search conversations..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          />
          <InputGroupAddon>
            <Search />
          </InputGroupAddon>
        </InputGroup>

        <Select
          value={filterType || "all"}
          onValueChange={(v) => { setFilterType(v === "all" ? "" : v); setPage(1); }}
        >
          <SelectTrigger className="w-full sm:w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            {convTypes.map((t) => (
              <SelectItem key={t} value={t}>{t.replace("_", " ").replace(/\b\w/g, c => c.toUpperCase())}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button onClick={() => setShowUpload(true)}>
          <Plus data-icon="inline-start" />
          Upload Recording
        </Button>
      </div>

      {/* Conversations list */}
      {loading ? (
        <div className="flex items-center justify-center h-48">
          <Spinner className="size-6" />
        </div>
      ) : conversations.length === 0 ? (
        <Empty className="border">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <PhoneCall />
            </EmptyMedia>
            <EmptyTitle>No conversations yet</EmptyTitle>
            <EmptyDescription>Upload your first recording to get AI-powered intelligence</EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <Button onClick={() => setShowUpload(true)}>
              <Upload data-icon="inline-start" />
              Upload Recording
            </Button>
          </EmptyContent>
        </Empty>
      ) : (
        <ItemGroup className="gap-2.5">
          {conversations.map((conv) => (
            <Item key={conv.id} variant="outline" className="bg-card" asChild>
              <Link href={`/conversations/${conv.id}`}>
                <ItemMedia variant="icon" className="size-10 rounded-lg border bg-muted">
                  <PhoneCall className="size-5" />
                </ItemMedia>

                <ItemContent className="min-w-0">
                  <ItemTitle>{conv.title}</ItemTitle>
                  <ItemDescription className="flex items-center gap-4 text-xs">
                    <span className="capitalize">{conv.conversation_type.replace("_", " ")}</span>
                    {conv.duration_seconds && (
                      <span className="flex items-center gap-1">
                        <Clock className="size-3" />
                        {Math.round(conv.duration_seconds / 60)}m
                      </span>
                    )}
                    <span>
                      {formatDistanceToNow(parseApiDate(conv.created_at), { addSuffix: true })}
                    </span>
                  </ItemDescription>
                </ItemContent>

                <ItemActions className="gap-3">
                  {conv.lead_score && (
                    <div className="flex items-center gap-1">
                      <TrendingUp className="size-3.5" />
                      <span className="text-xs font-bold tabular-nums">{conv.lead_score}</span>
                    </div>
                  )}
                  {conv.overall_sentiment && <SentimentBadge sentiment={conv.overall_sentiment} />}
                  <StatusBadge status={conv.status} />
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={(e) => handleDeleteConversation(e, conv.id)}
                    className="text-muted-foreground hover:text-destructive"
                    title="Delete conversation"
                  >
                    <Trash2 />
                  </Button>
                  <ArrowUpRight className="size-4 text-muted-foreground" />
                </ItemActions>
              </Link>
            </Item>
          ))}
        </ItemGroup>
      )}
    </AppShell>
  );
}
