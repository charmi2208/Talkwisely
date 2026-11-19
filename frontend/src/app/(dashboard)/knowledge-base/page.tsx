"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Upload, FileText, Trash2, Database } from "lucide-react";
import { apiClient } from "@/lib/api/client";
import { apiErrorMessage } from "@/lib/api/errors";
import { formatDate, humanize } from "@/lib/format";
import { useRole } from "@/lib/stores/authStore";
import { toast } from "sonner";
import { ErrorState, PageLoading } from "@/components/common/ErrorState";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
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
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState<KnowledgeDoc | null>(null);
  const isAdmin = useRole() === "admin";

  const loadDocs = async () => {
    try {
      const res = await apiClient.get<KnowledgeDoc[]>("/knowledge-base");
      setDocs(Array.isArray(res.data) ? res.data : []);
      setError("");
    } catch (err) {
      setError(apiErrorMessage(err, "Knowledge documents couldn't be loaded."));
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
      toast.success("Document uploaded and indexed for search");
      setTitle("");
      setSelectedFile(null);
      (e.target as HTMLFormElement).reset();
      loadDocs();
    } catch (err) {
      toast.error(apiErrorMessage(err, "Upload failed"));
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async () => {
    if (!deleting) return;
    try {
      await apiClient.delete(`/knowledge-base/${deleting.id}`);
      setDocs((prev) => prev.filter((d) => d.id !== deleting.id));
      toast.success("Document removed");
    } catch (err) {
      toast.error(apiErrorMessage(err, "Couldn't remove the document"));
    } finally {
      setDeleting(null);
    }
  };

  return (
    <AppShell title="Knowledge Base" subtitle="Upload product, sales & support documentation for RAG AI assistance">
      <div className="space-y-6">
        {/* Upload card */}
        {!isAdmin && (
          <Card size="sm">
            <CardContent className="text-sm text-muted-foreground">
              Ask the AI Copilot about these documents. Only admins can upload or remove them.
            </CardContent>
          </Card>
        )}
        {isAdmin && (
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
        )}

        {/* Document List */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="size-4" />
              Indexed Knowledge Documents ({docs.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading && docs.length === 0 ? (
              <PageLoading />
            ) : error ? (
              <ErrorState message={error} onRetry={() => { setLoading(true); setError(""); loadDocs(); }} />
            ) : docs.length === 0 ? (
              <Empty>
                <EmptyHeader>
                  <EmptyMedia variant="icon"><FileText /></EmptyMedia>
                  <EmptyTitle>No documents yet</EmptyTitle>
                  <EmptyDescription>Upload pricing sheets, playbooks or FAQs so the Copilot can answer from them.</EmptyDescription>
                </EmptyHeader>
              </Empty>
            ) : (
            <ItemGroup className="gap-2.5">
              {docs.map((doc) => (
                <Item key={doc.id} variant="muted">
                  <ItemMedia variant="icon">
                    <FileText className="size-5" />
                  </ItemMedia>
                  <ItemContent>
                    <ItemTitle>{doc.title}</ItemTitle>
                    <ItemDescription className="text-xs">
                      {doc.file_name} · {(doc.file_size_bytes / 1024).toFixed(0)} KB · {doc.chunk_count} search chunks · added {formatDate(doc.created_at)}
                    </ItemDescription>
                  </ItemContent>
                  <ItemActions>
                    <Badge variant="outline" className="capitalize bg-background">
                      {humanize(doc.category)}
                    </Badge>
                    {isAdmin && (
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => setDeleting(doc)}
                        className="text-muted-foreground hover:text-destructive"
                        aria-label="Delete document"
                      >
                        <Trash2 />
                      </Button>
                    )}
                  </ItemActions>
                </Item>
              ))}
            </ItemGroup>
            )}
          </CardContent>
        </Card>
      </div>

      <AlertDialog open={deleting !== null} onOpenChange={(open) => !open && setDeleting(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove &quot;{deleting?.title}&quot;?</AlertDialogTitle>
            <AlertDialogDescription>
              The file and its search index are deleted, and the Copilot will stop citing it. This can&apos;t be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={handleDelete}>Remove</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AppShell>
  );
}
