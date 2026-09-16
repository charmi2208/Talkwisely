"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { conversationsApi, type Conversation } from "@/lib/api/conversations";
import {
  Upload, Search, Plus, Loader2, PhoneCall, Clock, TrendingUp,
  CheckCircle, AlertCircle, Hourglass, X, FileAudio, FileVideo, ArrowUpRight, Trash2
} from "lucide-react";
import toast from "react-hot-toast";
import { clsx } from "clsx";
import { formatDistanceToNow } from "date-fns";

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { label: string; class: string; icon: React.ElementType }> = {
    completed: { label: "Completed", class: "text-emerald-700 bg-emerald-50 border-emerald-200", icon: CheckCircle },
    failed: { label: "Failed", class: "text-rose-700 bg-rose-50 border-rose-200", icon: AlertCircle },
    processing: { label: "Processing", class: "text-indigo-700 bg-indigo-50 border-indigo-200", icon: Loader2 },
    analyzing: { label: "Analyzing", class: "text-purple-700 bg-purple-50 border-purple-200", icon: Hourglass },
    transcribing: { label: "Transcribing", class: "text-amber-700 bg-amber-50 border-amber-200", icon: Hourglass },
    queued: { label: "Queued", class: "text-slate-600 bg-slate-100 border-slate-200", icon: Hourglass },
    uploaded: { label: "Uploaded", class: "text-slate-600 bg-slate-100 border-slate-200", icon: FileAudio },
  };
  const { label, class: cls, icon: Icon } = config[status] || config.uploaded;
  return (
    <span className={clsx("inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border", cls)}>
      <Icon className={clsx("w-3 h-3", status === "processing" || status === "analyzing" ? "animate-spin" : "")} />
      {label}
    </span>
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
    <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
      <div className="bg-white border border-slate-200 shadow-xl rounded-xl w-full max-w-lg p-6 relative">
        <button onClick={onClose} className="absolute right-4 top-4 text-slate-400 hover:text-slate-600">
          <X className="w-5 h-5" />
        </button>
        <h2 className="text-lg font-bold text-slate-900 mb-6">Upload Recording</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Drop zone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => document.getElementById("file-input")?.click()}
            className={clsx(
              "border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all",
              dragOver ? "border-indigo-500 bg-indigo-50/50" : "border-slate-300 bg-slate-50 hover:border-slate-400 hover:bg-slate-100/50",
              file ? "border-emerald-500 bg-emerald-50/50" : ""
            )}
          >
            <input
              id="file-input"
              type="file"
              accept=".mp3,.wav,.m4a,.ogg,.flac,.mp4,.avi,.mov,.mkv,.webm"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
            />
            {file ? (
              <div className="flex items-center justify-center gap-3">
                {file.type.startsWith("video") ? <FileVideo className="w-8 h-8 text-emerald-600" /> : <FileAudio className="w-8 h-8 text-emerald-600" />}
                <div className="text-left">
                  <p className="text-sm font-semibold text-emerald-700">{file.name}</p>
                  <p className="text-xs text-slate-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
              </div>
            ) : (
              <>
                <Upload className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                <p className="text-sm font-semibold text-slate-700 mb-0.5">Drag & drop or click to upload</p>
                <p className="text-xs text-slate-400">MP3, WAV, M4A, MP4, MOV — up to 500MB</p>
              </>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Conversation Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Sales Call — Acme Corp"
              required
              className="w-full px-3.5 py-2.5 rounded-lg bg-white border border-slate-300 text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-600 text-sm transition-all"
            />
          </div>

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 py-2 px-4 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 text-sm font-medium transition-all">
              Cancel
            </button>
            <button
              type="submit"
              disabled={!file || !title || uploading}
              className="flex-1 py-2 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm transition-all"
            >
              {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
              {uploading ? "Uploading..." : "Upload & Analyze"}
            </button>
          </div>
        </form>
      </div>
    </div>
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
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search conversations..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="w-full pl-9 pr-4 py-2 rounded-lg bg-white border border-slate-300 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-600 transition-all shadow-xs"
          />
        </div>

        <select
          value={filterType}
          onChange={(e) => { setFilterType(e.target.value); setPage(1); }}
          className="px-3.5 py-2 rounded-lg bg-white border border-slate-300 text-sm text-slate-700 focus:outline-none focus:border-indigo-600 shadow-xs"
        >
          <option value="">All Types</option>
          {convTypes.map((t) => (
            <option key={t} value={t}>{t.replace("_", " ").replace(/\b\w/g, c => c.toUpperCase())}</option>
          ))}
        </select>

        <button
          onClick={() => setShowUpload(true)}
          className="flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold shadow-sm transition-all"
        >
          <Plus className="w-4 h-4" />
          Upload Recording
        </button>
      </div>

      {/* Conversations list */}
      {loading ? (
        <div className="flex items-center justify-center h-48">
          <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
        </div>
      ) : conversations.length === 0 ? (
        <div className="glass-card p-16 text-center">
          <PhoneCall className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-base font-bold text-slate-900 mb-1">No conversations yet</h3>
          <p className="text-slate-500 text-sm mb-6">Upload your first recording to get AI-powered intelligence</p>
          <button
            onClick={() => setShowUpload(true)}
            className="px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold shadow-sm transition-all inline-flex items-center gap-2"
          >
            <Upload className="w-4 h-4" />
            Upload Recording
          </button>
        </div>
      ) : (
        <div className="space-y-2.5">
          {conversations.map((conv) => (
            <Link
              key={conv.id}
              href={`/conversations/${conv.id}`}
              className="glass-card p-4 flex items-center gap-4 hover:border-slate-300 transition-all group block"
            >
              <div className={clsx("w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 border",
                conv.conversation_type.includes("sales") ? "bg-indigo-50 text-indigo-600 border-indigo-100" :
                conv.conversation_type.includes("meeting") ? "bg-purple-50 text-purple-600 border-purple-100" :
                conv.conversation_type.includes("support") ? "bg-amber-50 text-amber-600 border-amber-100" :
                "bg-slate-50 text-slate-600 border-slate-200"
              )}>
                <PhoneCall className="w-5 h-5" />
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-start gap-2">
                  <h3 className="text-sm font-semibold text-slate-900 group-hover:text-indigo-600 transition-colors truncate">{conv.title}</h3>
                </div>
                <div className="flex items-center gap-4 mt-0.5">
                  <span className="text-xs text-slate-500 capitalize">{conv.conversation_type.replace("_", " ")}</span>
                  {conv.duration_seconds && (
                    <span className="flex items-center gap-1 text-xs text-slate-400">
                      <Clock className="w-3 h-3" />
                      {Math.round(conv.duration_seconds / 60)}m
                    </span>
                  )}
                  <span className="text-xs text-slate-400">
                    {formatDistanceToNow(new Date(conv.created_at), { addSuffix: true })}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-3 flex-shrink-0">
                {conv.lead_score && (
                  <div className="flex items-center gap-1">
                    <TrendingUp className="w-3.5 h-3.5 text-indigo-600" />
                    <span className="text-xs font-bold text-indigo-600">{conv.lead_score}</span>
                  </div>
                )}
                {conv.overall_sentiment && (
                  <span className={clsx("text-xs px-2.5 py-0.5 rounded-full font-medium capitalize border",
                    conv.overall_sentiment === "positive" ? "badge-positive" :
                    conv.overall_sentiment === "negative" ? "badge-negative" : "badge-neutral"
                  )}>
                    {conv.overall_sentiment}
                  </span>
                )}
                <StatusBadge status={conv.status} />
                <button
                  onClick={(e) => handleDeleteConversation(e, conv.id)}
                  className="p-1.5 rounded-md text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-all"
                  title="Delete conversation"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
                <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-indigo-600 transition-colors" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </AppShell>
  );
}
