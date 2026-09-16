"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Upload, FileText, Trash2, Database } from "lucide-react";
import { apiClient } from "@/lib/api/client";
import toast from "react-hot-toast";

interface KnowledgeDoc {
  id: string;
  title: string;
  file_name: string;
  file_type: string;
  file_size_bytes: number;
  category: string;
  chunk_count: number;
  created_at: string;
}

export default function KnowledgeBasePage() {
  const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("sales_playbook");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const loadDocs = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get<KnowledgeDoc[]>("/knowledge-base");
      setDocs(Array.isArray(res.data) ? res.data : []);
    } catch {
      // Fallback demo documents
      setDocs([
        {
          id: "kb_1",
          title: "TalkWisely Enterprise Pricing & Feature Matrix 2026",
          file_name: "enterprise_pricing_2026.pdf",
          file_type: "pdf",
          file_size_bytes: 1420000,
          category: "pricing",
          chunk_count: 14,
          created_at: new Date().toISOString(),
        },
        {
          id: "kb_2",
          title: "Cloud PBX & Virtual Phone Numbers Battlecard",
          file_name: "cloud_pbx_battlecard.docx",
          file_type: "docx",
          file_size_bytes: 850000,
          category: "sales_playbook",
          chunk_count: 8,
          created_at: new Date().toISOString(),
        },
        {
          id: "kb_3",
          title: "AI Call Analytics & CRM Webhook Integration Docs",
          file_name: "crm_integration_guide.md",
          file_type: "md",
          file_size_bytes: 420000,
          category: "technical",
          chunk_count: 6,
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocs();
  }, []);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || !title.trim()) {
      toast.error("Please select a file and title");
      return;
    }

    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("title", title.trim());
    formData.append("category", category);

    try {
      await apiClient.post("/knowledge-base/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success("Document uploaded & indexed into Vector DB!");
      setTitle("");
      setSelectedFile(null);
      loadDocs();
    } catch {
      toast.error("Upload failed (Mock index active)");
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await apiClient.delete(`/knowledge-base/${id}`);
      toast.success("Document removed");
      loadDocs();
    } catch {
      setDocs((prev) => prev.filter((d) => d.id !== id));
    }
  };

  return (
    <AppShell title="Knowledge Base" subtitle="Upload product, sales & support documentation for RAG AI assistance">
      <div className="space-y-6">
        {/* Upload card */}
        <form onSubmit={handleUpload} className="glass-card p-6 space-y-4">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Upload className="w-4 h-4 text-indigo-600" />
            Upload New Document
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <input
              type="text"
              placeholder="Document Title (e.g. Sales Objection Playbook)"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="bg-white border border-slate-300 rounded-lg px-3.5 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-600"
              required
            />
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="bg-white border border-slate-300 rounded-lg px-3.5 py-2 text-sm text-slate-700 focus:outline-none focus:border-indigo-600"
            >
              <option value="sales_playbook">Sales Playbook</option>
              <option value="pricing">Pricing Matrix</option>
              <option value="technical">Technical Specs</option>
              <option value="faq">Customer FAQ</option>
            </select>
            <input
              type="file"
              accept=".pdf,.docx,.txt,.md"
              onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              className="bg-white border border-slate-300 rounded-lg px-3.5 py-1.5 text-xs text-slate-600 file:mr-3 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-xs file:bg-indigo-600 file:text-white hover:file:bg-indigo-700"
              required
            />
          </div>
          <button
            type="submit"
            disabled={isUploading}
            className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-xs font-semibold text-white shadow-xs transition-colors"
          >
            {isUploading ? "Chunking & Indexing..." : "Upload & Index into Vector Store"}
          </button>
        </form>

        {/* Document List */}
        <div className="glass-card p-6">
          <h3 className="text-sm font-bold text-slate-900 mb-4 flex items-center gap-2">
            <Database className="w-4 h-4 text-emerald-600" />
            Indexed Knowledge Documents ({docs.length})
          </h3>
          <div className="space-y-2.5">
            {docs.map((doc) => (
              <div key={doc.id} className="flex items-center justify-between p-4 rounded-lg bg-slate-50 border border-slate-200">
                <div className="flex items-center gap-3">
                  <FileText className="w-5 h-5 text-indigo-600 flex-shrink-0" />
                  <div>
                    <p className="text-sm font-semibold text-slate-900">{doc.title}</p>
                    <p className="text-xs text-slate-500">
                      {doc.file_name} • {(doc.file_size_bytes / 1024).toFixed(0)} KB • {doc.chunk_count} vector chunks
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs px-2.5 py-1 rounded-full bg-white text-slate-700 font-semibold capitalize border border-slate-300">
                    {doc.category}
                  </span>
                  <button onClick={() => handleDelete(doc.id)} className="text-slate-400 hover:text-rose-600 transition-colors p-1">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
