"use client";

import { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Download, Sparkles, Loader2 } from "lucide-react";
import { apiClient } from "@/lib/api/client";
import toast from "react-hot-toast";

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

  const handleDownloadCSV = () => {
    window.open(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/reports/export/csv`, "_blank");
  };

  return (
    <AppShell title="Executive Reports" subtitle="Synthesize conversation analytics into management reports & export data">
      <div className="space-y-6">
        {/* Form */}
        <form onSubmit={handleGenerate} className="glass-card p-6 flex flex-col md:flex-row items-center gap-4">
          <div className="flex-1 space-y-1">
            <label className="text-xs font-semibold text-slate-600">Report Type</label>
            <select
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
              className="w-full bg-white border border-slate-300 rounded-lg px-3.5 py-2 text-sm text-slate-700 focus:outline-none focus:border-indigo-600"
            >
              <option value="executive">Executive Summary Report</option>
              <option value="sales">Sales Performance Report</option>
              <option value="sentiment_objections">Sentiment & Objection Analysis</option>
              <option value="team_qa">Team QA & Coaching Report</option>
            </select>
          </div>

          <div className="flex-1 space-y-1">
            <label className="text-xs font-semibold text-slate-600">Time Period</label>
            <select
              value={timePeriod}
              onChange={(e) => setTimePeriod(e.target.value)}
              className="w-full bg-white border border-slate-300 rounded-lg px-3.5 py-2 text-sm text-slate-700 focus:outline-none focus:border-indigo-600"
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </div>

          <div className="flex items-center gap-3 pt-5">
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2 px-5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-xs font-semibold text-white transition-all shadow-xs"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
              Synthesize Report
            </button>
            <button
              type="button"
              onClick={handleDownloadCSV}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white border border-slate-300 hover:bg-slate-50 text-xs font-semibold text-slate-700 transition-colors shadow-xs"
            >
              <Download className="w-4 h-4" />
              Export CSV
            </button>
          </div>
        </form>

        {/* Report Output */}
        {report && (
          <div className="glass-card p-8 space-y-6">
            <h2 className="text-xl font-bold text-slate-900 border-b border-slate-200 pb-3">{report.title}</h2>

            <div>
              <h3 className="text-xs font-bold text-indigo-600 uppercase tracking-wide mb-2">Executive Summary</h3>
              <p className="text-sm text-slate-700 leading-relaxed">{report.executive_summary}</p>
            </div>

            {report.key_insights?.length > 0 && (
              <div>
                <h3 className="text-xs font-bold text-emerald-700 uppercase tracking-wide mb-2">Key Highlights</h3>
                <ul className="space-y-1.5">
                  {report.key_insights.map((insight: string, idx: number) => (
                    <li key={idx} className="text-sm text-slate-700 flex items-start gap-2">
                      <span className="text-emerald-600 font-bold">•</span>
                      {insight}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {report.strategic_recommendations?.length > 0 && (
              <div>
                <h3 className="text-xs font-bold text-purple-700 uppercase tracking-wide mb-2">Strategic Recommendations</h3>
                <ul className="space-y-1.5">
                  {report.strategic_recommendations.map((rec: string, idx: number) => (
                    <li key={idx} className="text-sm text-slate-700 flex items-start gap-2">
                      <span className="text-purple-600 font-bold">{idx + 1}.</span>
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </AppShell>
  );
}
