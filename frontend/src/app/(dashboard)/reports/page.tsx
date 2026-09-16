"use client";

import { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Download, Sparkles } from "lucide-react";
import { apiClient } from "@/lib/api/client";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldLabel } from "@/components/ui/field";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Spinner } from "@/components/ui/spinner";

export default function ReportsPage() {
  const [reportType, setReportType] = useState("executive");
  const [timePeriod, setTimePeriod] = useState("weekly");
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await apiClient.post<any>("/reports/generate", {
        report_type: reportType,
        time_period: timePeriod,
      });
      setReport(res.data || res);
      toast.success("Executive report synthesized!");
    } catch {
      toast.error("Failed to generate report (Using local sample)");
      setReport({
        title: `${reportType.replace("_", " ").toUpperCase()} REPORT (${timePeriod.toUpperCase()})`,
        executive_summary: "Over the past weekly period, conversation volume increased by 14% with strong positive customer sentiment across sales demos.",
        key_insights: [
          "Total conversations evaluated: 142 calls & meetings",
          "High-intent lead conversion rate at 68%",
          "Top feature inquiry: Virtual Phone Numbers & Cloud PBX webhooks",
        ],
        strategic_recommendations: [
          "Follow up on pending enterprise pricing proposals within 24 hours.",
          "Host coaching session on objection handling for integration topics.",
        ],
        formatted_markdown: `# Executive Report\n\n## Summary\nOver the past weekly period, conversation volume increased by 14%.\n\n## Key Recommendations\n1. Follow up on high-intent lead opportunities.\n2. Address top pricing objections.`,
      });
    } finally {
      setLoading(false);
    }
  };

  const [exporting, setExporting] = useState(false);

  const handleDownloadCSV = async () => {
    setExporting(true);
    try {
      // Goes through apiClient so the Bearer token is attached
      const res = await apiClient.get<Blob>("/reports/export/csv", { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = "talkwise_conversations_report.csv";
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Couldn't export the CSV. Please try again.");
    } finally {
      setExporting(false);
    }
  };

  return (
    <AppShell title="Executive Reports" subtitle="Synthesize conversation analytics into management reports & export data">
      <div className="space-y-6">
        {/* Form */}
        <Card>
          <CardContent>
            <form onSubmit={handleGenerate} className="flex flex-col md:flex-row md:items-end gap-4">
              <Field className="flex-1 gap-1.5">
                <FieldLabel htmlFor="report-type" className="text-xs">Report Type</FieldLabel>
                <Select value={reportType} onValueChange={setReportType}>
                  <SelectTrigger id="report-type" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="executive">Executive Summary Report</SelectItem>
                    <SelectItem value="sales">Sales Performance Report</SelectItem>
                    <SelectItem value="sentiment_objections">Sentiment & Objection Analysis</SelectItem>
                    <SelectItem value="team_qa">Team QA & Coaching Report</SelectItem>
                  </SelectContent>
                </Select>
              </Field>

              <Field className="flex-1 gap-1.5">
                <FieldLabel htmlFor="time-period" className="text-xs">Time Period</FieldLabel>
                <Select value={timePeriod} onValueChange={setTimePeriod}>
                  <SelectTrigger id="time-period" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="daily">Daily</SelectItem>
                    <SelectItem value="weekly">Weekly</SelectItem>
                    <SelectItem value="monthly">Monthly</SelectItem>
                  </SelectContent>
                </Select>
              </Field>

              <div className="flex items-center gap-3">
                <Button type="submit" disabled={loading}>
                  {loading ? <Spinner data-icon="inline-start" /> : <Sparkles data-icon="inline-start" />}
                  Synthesize Report
                </Button>
                <Button type="button" variant="outline" onClick={handleDownloadCSV} disabled={exporting}>
                  {exporting ? <Spinner data-icon="inline-start" /> : <Download data-icon="inline-start" />}
                  Export CSV
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Report Output */}
        {report && (
          <Card className="[--card-spacing:--spacing(8)]">
            <CardHeader className="border-b">
              <CardTitle className="text-xl font-semibold">{report.title}</CardTitle>
            </CardHeader>

            <CardContent className="gap-6">
              <div>
                <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Executive Summary</h3>
                <p className="text-sm leading-relaxed">{report.executive_summary}</p>
              </div>

              {report.key_insights?.length > 0 && (
                <>
                  <Separator />
                  <div>
                    <h3 className="text-xs font-semibold text-success uppercase tracking-wide mb-2">Key Highlights</h3>
                    <ul className="space-y-1.5">
                      {report.key_insights.map((insight: string, idx: number) => (
                        <li key={idx} className="text-sm flex items-start gap-2">
                          <span className="text-success font-bold">•</span>
                          {insight}
                        </li>
                      ))}
                    </ul>
                  </div>
                </>
              )}

              {report.strategic_recommendations?.length > 0 && (
                <>
                  <Separator />
                  <div>
                    <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Strategic Recommendations</h3>
                    <ul className="space-y-1.5">
                      {report.strategic_recommendations.map((rec: string, idx: number) => (
                        <li key={idx} className="text-sm flex items-start gap-2">
                          <span className="font-bold tabular-nums">{idx + 1}.</span>
                          {rec}
                        </li>
                      ))}
                    </ul>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </AppShell>
  );
}
