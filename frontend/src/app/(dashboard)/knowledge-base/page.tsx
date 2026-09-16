"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Upload, FileText, Trash2, Database } from "lucide-react";
import { apiClient } from "@/lib/api/client";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Item, ItemActions, ItemContent, ItemDescription, ItemGroup, ItemMedia, ItemTitle,
} from "@/components/ui/item";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";

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
        <Card>
          <form onSubmit={handleUpload} className="flex flex-col gap-(--card-spacing)">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="size-4" />
                Upload New Document
              </CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Field>
                <FieldLabel htmlFor="kb-title" className="sr-only">Document Title</FieldLabel>
                <Input
                  id="kb-title"
                  type="text"
                  placeholder="Document Title (e.g. Sales Objection Playbook)"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="kb-category" className="sr-only">Category</FieldLabel>
                <Select value={category} onValueChange={setCategory}>
                  <SelectTrigger id="kb-category" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="sales_playbook">Sales Playbook</SelectItem>
                    <SelectItem value="pricing">Pricing Matrix</SelectItem>
                    <SelectItem value="technical">Technical Specs</SelectItem>
                    <SelectItem value="faq">Customer FAQ</SelectItem>
                  </SelectContent>
                </Select>
              </Field>
              <Field>
                <FieldLabel htmlFor="kb-file" className="sr-only">File</FieldLabel>
                <Input
                  id="kb-file"
                  type="file"
                  accept=".pdf,.docx,.txt,.md"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  required
                />
              </Field>
            </CardContent>
            <CardFooter>
              <Button type="submit" size="sm" disabled={isUploading}>
                {isUploading && <Spinner data-icon="inline-start" />}
                {isUploading ? "Chunking & Indexing..." : "Upload & Index into Vector Store"}
              </Button>
            </CardFooter>
          </form>
        </Card>

        {/* Document List */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="size-4" />
              Indexed Knowledge Documents ({docs.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ItemGroup className="gap-2.5">
              {docs.map((doc) => (
                <Item key={doc.id} variant="muted">
                  <ItemMedia variant="icon">
                    <FileText className="size-5" />
                  </ItemMedia>
                  <ItemContent>
                    <ItemTitle>{doc.title}</ItemTitle>
                    <ItemDescription className="text-xs">
                      {doc.file_name} • {(doc.file_size_bytes / 1024).toFixed(0)} KB • {doc.chunk_count} vector chunks
                    </ItemDescription>
                  </ItemContent>
                  <ItemActions>
                    <Badge variant="outline" className="capitalize bg-background">
                      {doc.category}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => handleDelete(doc.id)}
                      className="text-muted-foreground hover:text-destructive"
                      aria-label="Delete document"
                    >
                      <Trash2 />
                    </Button>
                  </ItemActions>
                </Item>
              ))}
            </ItemGroup>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
