"use client";

import { useCallback, useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Download, FileText, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { apiErrorMessage } from "@/lib/api/errors";
import { REPORT_PERIODS, REPORT_TYPES, reportsApi, type Report, type ReportListItem } from "@/lib/api/reports";
import { downloadFile } from "@/lib/download";
import { useRole } from "@/lib/stores/authStore";
import { formatDateTime } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Field, FieldLabel } from "@/components/ui/field";
import { Item, ItemContent, ItemDescription, ItemGroup, ItemTitle } from "@/components/ui/item";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Spinner } from "@/components/ui/spinner";

function ReportSection({ title, items, numbered = false }: { title: string; items: string[]; numbered?: boolean }) {
  if (!items?.length) return null;
  return (
    <>
      <Separator />
      <div>
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">{title}</h3>
        <ul className="space-y-1.5">
          {items.map((item, idx) => (
            <li key={idx} className="text-sm flex items-start gap-2">
              <span className="font-semibold tabular-nums text-muted-foreground">{numbered ? `${idx + 1}.` : "-"}</span>
              {item}
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}

export default function ReportsPage() {
  const role = useRole();
  const canGenerate = role !== "agent";
  const [reportType, setReportType] = useState("executive");
  const [timePeriod, setTimePeriod] = useState("weekly");
  const [report, setReport] = useState<Report | null>(null);
  const [history, setHistory] = useState<ReportListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [opening, setOpening] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);

  const loadHistory = useCallback(async () => {
    if (!canGenerate) return;
    try {
      const list = await reportsApi.list();
      setHistory(list);
    } catch (err) {
      toast.error(apiErrorMessage(err, "Couldn't load saved reports"));
    }
  }, [canGenerate]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const generated = await reportsApi.generate(reportType, timePeriod);
      setReport(generated);
      toast.success("Report generated and saved");
      loadHistory();
    } catch (err) {
      toast.error(apiErrorMessage(err, "The report couldn't be generated"));
    } finally {
      setLoading(false);
    }
  };

  const openReport = async (id: string) => {
    setOpening(id);
    try {
      setReport(await reportsApi.get(id));
    } catch (err) {
      toast.error(apiErrorMessage(err, "Couldn't open this report"));
    } finally {
      setOpening(null);
    }
  };

  const download = async (format: "pdf" | "csv" | "md") => {
    if (!report?.id) return;
    setDownloading(format);
    try {
      const slug = report.title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
      await downloadFile(`/reports/${report.id}/download`, `${slug}.${format}`, { format });
    } catch (err) {
      toast.error(apiErrorMessage(err, "Download failed"));
    } finally {
      setDownloading(null);
    }
  };

  const handleDownloadCSV = async () => {
    setExporting(true);
    try {
      await downloadFile("/reports/export/csv", "talkwise_conversations.csv");
    } catch {
      toast.error("Couldn't export the CSV. Please try again.");
    } finally {
      setExporting(false);
    }
  };

  return (
    <AppShell title="Executive Reports" subtitle="Synthesize conversation analytics into management reports & export data">
      <div className="space-y-6">
        <Card>
          <CardContent>
            <form onSubmit={handleGenerate} className="flex flex-col md:flex-row md:items-end gap-4">
              {canGenerate && (
                <>
                  <Field className="flex-1 gap-1.5">
                    <FieldLabel htmlFor="report-type" className="text-xs">Report Type</FieldLabel>
                    <Select value={reportType} onValueChange={setReportType}>
                      <SelectTrigger id="report-type" className="w-full"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {REPORT_TYPES.map((t) => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </Field>
                  <Field className="flex-1 gap-1.5">
                    <FieldLabel htmlFor="time-period" className="text-xs">Time Period</FieldLabel>
                    <Select value={timePeriod} onValueChange={setTimePeriod}>
                      <SelectTrigger id="time-period" className="w-full"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {REPORT_PERIODS.map((p) => <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </Field>
                </>
              )}
              {!canGenerate && (
                <p className="flex-1 text-sm text-muted-foreground">
                  Managers and admins generate team reports. You can export your own conversations as CSV.
                </p>
              )}

              <div className="flex items-center gap-3">
                {canGenerate && (
                  <Button type="submit" disabled={loading}>
                    {loading ? <Spinner data-icon="inline-start" /> : <Sparkles data-icon="inline-start" />}
                    Synthesize Report
                  </Button>
                )}
                <Button type="button" variant="outline" onClick={handleDownloadCSV} disabled={exporting}>
                  {exporting ? <Spinner data-icon="inline-start" /> : <Download data-icon="inline-start" />}
                  Export conversations CSV
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <div className={canGenerate ? "grid grid-cols-1 lg:grid-cols-3 gap-6" : ""}>
          <div className="lg:col-span-2">
            {report ? (
              <Card className="[--card-spacing:--spacing(8)]">
                <CardHeader className="border-b">
                  <CardTitle className="text-xl font-semibold">{report.title}</CardTitle>
                  <CardDescription>
                    {report.created_at ? `Generated ${formatDateTime(report.created_at)}` : ""}
                    {report.created_by_name ? ` by ${report.created_by_name}` : ""}
                  </CardDescription>
                  {report.id && (
                    <CardAction className="flex gap-2">
                      {(["pdf", "csv", "md"] as const).map((format) => (
                        <Button key={format} size="sm" variant="outline" onClick={() => download(format)} disabled={downloading !== null}>
                          {downloading === format ? <Spinner data-icon="inline-start" /> : <Download data-icon="inline-start" />}
                          {format.toUpperCase()}
                        </Button>
                      ))}
                    </CardAction>
                  )}
                </CardHeader>

                <CardContent className="gap-6">
                  <div>
                    <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Executive Summary</h3>
                    <p className="text-sm leading-relaxed">{report.executive_summary}</p>
                  </div>
                  <ReportSection title="Key Highlights" items={report.key_insights} />
                  <ReportSection title="Risks & Bottlenecks" items={report.risks_and_bottlenecks} />
                  <ReportSection title="Strategic Recommendations" items={report.strategic_recommendations} numbered />
                </CardContent>
              </Card>
            ) : canGenerate ? (
              <Empty className="border bg-card">
                <EmptyHeader>
                  <EmptyMedia variant="icon"><FileText /></EmptyMedia>
                  <EmptyTitle>No report open</EmptyTitle>
                  <EmptyDescription>Generate a report, or open a saved one. Reports cite only the metrics recorded in TalkWiseAI.</EmptyDescription>
                </EmptyHeader>
              </Empty>
            ) : null}
          </div>

          {canGenerate && (
            <Card>
              <CardHeader>
                <CardTitle>Saved reports</CardTitle>
                <CardDescription>Everyone with manager or admin access can open these.</CardDescription>
              </CardHeader>
              <CardContent>
                {history.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No reports yet.</p>
                ) : (
                  <ItemGroup className="gap-2">
                    {history.map((r) => (
                      <Item
                        key={r.id}
                        variant={report?.id === r.id ? "muted" : "outline"}
                        size="sm"
                        asChild
                      >
                        <button type="button" onClick={() => openReport(r.id)} className="w-full text-left">
                          <ItemContent>
                            <ItemTitle>
                              {r.title}
                              {opening === r.id && <Spinner className="size-3.5" />}
                            </ItemTitle>
                            <ItemDescription className="text-xs">
                              {formatDateTime(r.created_at)}{r.created_by_name ? ` · ${r.created_by_name}` : ""}
                            </ItemDescription>
                          </ItemContent>
                        </button>
                      </Item>
                    ))}
                  </ItemGroup>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </AppShell>
  );
}
