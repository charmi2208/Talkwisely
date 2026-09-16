"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { conversationsApi } from "@/lib/api/conversations";
import {
  ArrowLeft, Loader2, RefreshCw, CheckCircle, TrendingUp,
  MessageSquare, BarChart3, Shield, Lightbulb, AlertTriangle,
  Star, Trash2, Volume2
} from "lucide-react";
import Link from "next/link";
import toast from "react-hot-toast";
import { clsx } from "clsx";

// Processing state poller
function useProcessingPoller(conversationId: string, initialStatus: string, onComplete: () => void) {
  const [progress, setProgress] = useState(0);
  const [step, setStep] = useState("Starting...");
  const [isPolling, setIsPolling] = useState(false);

  useEffect(() => {
    if (!["processing", "transcribing", "analyzing", "queued", "uploaded"].includes(initialStatus)) return;

    setIsPolling(true);
    const interval = setInterval(async () => {
      try {
        const status = await conversationsApi.getProcessingStatus(conversationId);
        if (status.job) {
          setProgress(status.job.progress || 0);
          setStep(status.job.current_step || "Processing...");
        }
        if (status.conversation_status === "completed" || status.conversation_status === "failed") {
          clearInterval(interval);
          setIsPolling(false);
          onComplete();
        }
      } catch { /* silent */ }
    }, 2500);

    return () => clearInterval(interval);
  }, [conversationId, initialStatus, onComplete]);

  return { progress, step, isPolling };
}

function ScoreBar({ score, label }: { score: number; label: string }) {
  const w = Math.min(100, Math.max(0, score));
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs font-medium text-slate-600 w-32 flex-shrink-0">{label}</span>
      <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden border border-slate-200">
        <div
          className={clsx("h-full rounded-full", w >= 80 ? "bg-emerald-500" : w >= 60 ? "bg-amber-500" : "bg-rose-500")}
          style={{ width: `${w}%` }}
        />
      </div>
      <span className="text-xs font-bold text-slate-900 w-8 text-right">{score}</span>
    </div>
  );
}

function SentimentBadge({ sentiment }: { sentiment: string }) {
  const cls = sentiment === "positive" ? "badge-positive" : sentiment === "negative" ? "badge-negative" : "badge-neutral";
  return <span className={clsx("text-xs px-2.5 py-0.5 rounded-full font-semibold capitalize border", cls)}>{sentiment}</span>;
}

export default function ConversationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [conversation, setConversation] = useState<any>(null);
  const [insights, setInsights] = useState<any>(null);
  const [transcript, setTranscript] = useState<any>(null);
  const [audioSrc, setAudioSrc] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("insights");

  const loadConversation = useCallback(async () => {
    try {
      const [conv, ins, trans] = await Promise.all([
        conversationsApi.get(id),
        conversationsApi.getInsights(id),
        conversationsApi.getTranscript(id),
      ]);
      setConversation(conv);
      setInsights(ins);
      setTranscript(trans);
    } catch (err: any) {
      toast.error("Failed to load conversation");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { loadConversation(); }, [loadConversation]);

  useEffect(() => {
    let url: string | null = null;
    if (id && conversation?.file_name) {
      conversationsApi
        .getAudioBlob(id)
        .then((blob) => {
          url = URL.createObjectURL(blob);
          setAudioSrc(url);
        })
        .catch(() => {
          setAudioSrc(null);
        });
    }
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [id, conversation?.file_name]);

  const { progress, step } = useProcessingPoller(
    id,
    conversation?.status || "",
    () => {
      toast.success("Analysis complete!");
      loadConversation();
    }
  );

  const tabs = [
    { id: "insights", label: "Insights", icon: Lightbulb },
    { id: "transcript", label: "Transcript", icon: MessageSquare },
    { id: "sales", label: "Sales", icon: TrendingUp },
    { id: "actions", label: "Actions", icon: CheckCircle },
    { id: "agent", label: "Agent Score", icon: Star },
    { id: "minutes", label: "Meeting Minutes", icon: BarChart3 },
  ];

  if (loading) {
    return (
      <AppShell title="Loading..." >
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
        </div>
      </AppShell>
    );
  }

  if (!conversation) {
    return (
      <AppShell title="Not Found">
        <div className="text-center py-16 text-slate-500">Conversation not found.</div>
      </AppShell>
    );
  }

  const isProcessing = ["processing", "transcribing", "analyzing", "queued", "uploaded"].includes(conversation.status);

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete this conversation?")) return;
    try {
      await conversationsApi.delete(id);
      toast.success("Conversation deleted");
      router.push("/conversations");
    } catch {
      toast.error("Failed to delete conversation");
    }
  };

  return (
    <AppShell
      title={conversation.title}
      subtitle={`${conversation.conversation_type?.replace("_", " ")} • ${conversation.language?.toUpperCase()}`}
    >
      <div className="space-y-6">
        {/* Header bar */}
        <div className="flex items-center gap-4">
          <Link
            href="/conversations"
            className="flex items-center gap-2 text-sm font-semibold text-slate-600 hover:text-slate-900 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </Link>
          <div className="flex-1" />
          <button
            onClick={handleDelete}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-rose-50 border border-rose-200 text-sm font-semibold text-rose-700 hover:bg-rose-100 transition-all shadow-xs"
          >
            <Trash2 className="w-4 h-4" />
            Delete
          </button>
          <button
            onClick={loadConversation}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white border border-slate-300 text-sm font-medium text-slate-700 hover:bg-slate-50 shadow-xs transition-all"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>

        {/* Processing state */}
        {isProcessing && (
          <div className="glass-card p-6 border-indigo-100 bg-indigo-50/30">
            <div className="flex items-center gap-3 mb-4">
              <Loader2 className="w-5 h-5 animate-spin text-indigo-600" />
              <div>
                <p className="text-sm font-bold text-slate-900">Processing your recording...</p>
                <p className="text-xs text-slate-500">{step}</p>
              </div>
              <span className="ml-auto text-sm font-bold text-indigo-600">{progress}%</span>
            </div>
            <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-indigo-600 rounded-full transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-xs text-slate-500 mt-3">
              AI is running 15+ specialized agents in parallel. This may take 1-3 minutes.
            </p>
          </div>
        )}

        {/* Failed state */}
        {conversation.status === "failed" && (
          <div className="glass-card p-6 border-rose-200 bg-rose-50">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-rose-600" />
              <div>
                <p className="text-sm font-bold text-rose-700">Processing Failed</p>
                <p className="text-xs text-rose-600">{conversation.error_message || "An error occurred during processing"}</p>
              </div>
            </div>
          </div>
        )}

        {/* Key metrics (when completed) */}
        {conversation.status === "completed" && insights && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {insights.sentiment && (
              <div className="glass-card p-4">
                <p className="text-xs font-semibold text-slate-500 mb-2">Overall Sentiment</p>
                <SentimentBadge sentiment={insights.sentiment.overall_sentiment} />
                <p className="text-xs text-slate-400 mt-1">
                  Score: {insights.sentiment.overall_score?.toFixed(2)}
                </p>
              </div>
            )}
            {insights.sales_insight?.lead_score && (
              <div className="glass-card p-4">
                <p className="text-xs font-semibold text-slate-500 mb-1">Lead Score</p>
                <p className="text-3xl font-extrabold text-indigo-600">{insights.sales_insight.lead_score}</p>
                <p className="text-xs text-slate-400">/100</p>
              </div>
            )}
            {insights.intent && (
              <div className="glass-card p-4">
                <p className="text-xs font-semibold text-slate-500 mb-1">Primary Intent</p>
                <p className="text-sm font-bold text-slate-900 capitalize">
                  {insights.intent.primary_intent?.replace("_", " ")}
                </p>
                <p className="text-xs text-slate-400">{Math.round((insights.intent.confidence || 0) * 100)}% confident</p>
              </div>
            )}
            {insights.action_items && (
              <div className="glass-card p-4">
                <p className="text-xs font-semibold text-slate-500 mb-1">Action Items</p>
                <p className="text-3xl font-extrabold text-amber-600">{insights.action_items.length}</p>
                <p className="text-xs text-slate-400">tasks identified</p>
              </div>
            )}
          </div>
        )}

        {/* Audio Player Card */}
        {conversation.file_name && (
          <div className="glass-card p-4 flex flex-col sm:flex-row items-center gap-4 bg-slate-50/50 border-slate-200">
            <div className="w-10 h-10 rounded-lg bg-indigo-100 text-indigo-600 flex items-center justify-center flex-shrink-0">
              <Volume2 className="w-5 h-5" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-bold text-slate-900 truncate">{conversation.file_name || "Audio Recording"}</p>
              <p className="text-xs text-slate-500">Audio playback stream</p>
            </div>
            {audioSrc ? (
              <audio
                controls
                src={audioSrc}
                className="w-full sm:w-80 h-9 rounded-md"
              />
            ) : (
              <div className="flex items-center gap-2 text-xs text-slate-500 font-medium py-1.5 px-3 rounded-lg bg-slate-100 border border-slate-200">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-600" />
                Loading audio stream...
              </div>
            )}
          </div>
        )}

        {/* Tabs */}
        {conversation.status === "completed" && (
          <>
            <div className="flex gap-1 border-b border-slate-200">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={clsx(
                    "flex items-center gap-2 px-4 py-3 text-sm font-semibold transition-all border-b-2 -mb-px",
                    activeTab === tab.id
                      ? "text-indigo-600 border-indigo-600"
                      : "text-slate-500 border-transparent hover:text-slate-900"
                  )}
                >
                  <tab.icon className="w-4 h-4" />
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Insights tab */}
            {activeTab === "insights" && insights?.summary && (
              <div className="space-y-4">
                <div className="glass-card p-6">
                  <h3 className="text-sm font-bold text-slate-900 mb-3 flex items-center gap-2">
                    <Lightbulb className="w-4 h-4 text-indigo-600" />
                    Executive Summary
                  </h3>
                  <p className="text-sm text-slate-700 leading-relaxed">{insights.summary.executive_summary}</p>
                </div>

                {insights.summary.key_topics?.length > 0 && (
                  <div className="glass-card p-6">
                    <h3 className="text-sm font-bold text-slate-900 mb-3">Key Topics</h3>
                    <div className="flex flex-wrap gap-2">
                      {insights.summary.key_topics.map((topic: string) => (
                        <span key={topic} className="px-3 py-1 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-100">
                          {topic}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {insights.pain_points?.length > 0 && (
                  <div className="glass-card p-6">
                    <h3 className="text-sm font-bold text-slate-900 mb-4 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-amber-600" />
                      Pain Points Detected
                    </h3>
                    <div className="space-y-3">
                      {insights.pain_points.map((pp: any) => (
                        <div key={pp.id} className="flex gap-3 p-3.5 rounded-lg bg-slate-50 border border-slate-200">
                          <div className={clsx("w-1.5 rounded-full flex-shrink-0",
                            pp.severity === "high" ? "bg-rose-500" : pp.severity === "medium" ? "bg-amber-500" : "bg-slate-400"
                          )} />
                          <div>
                            <p className="text-sm font-medium text-slate-900">{pp.description}</p>
                            {pp.evidence && <p className="text-xs text-slate-500 mt-1 italic">"{pp.evidence}"</p>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {insights.recommendations?.length > 0 && (
                  <div className="glass-card p-6">
                    <h3 className="text-sm font-bold text-slate-900 mb-4 flex items-center gap-2">
                      <Lightbulb className="w-4 h-4 text-emerald-600" />
                      AI Recommendations
                    </h3>
                    <div className="space-y-3">
                      {insights.recommendations.map((rec: any) => (
                        <div key={rec.id} className="flex gap-3 p-4 rounded-lg bg-slate-50 border border-slate-200">
                          <span className={clsx("text-xs px-2.5 py-0.5 rounded-full font-semibold h-fit mt-0.5 border",
                            rec.priority === "urgent" ? "badge-high" : rec.priority === "high" ? "badge-medium" : "badge-low"
                          )}>
                            {rec.priority}
                          </span>
                          <div>
                            <p className="text-sm font-bold text-slate-900">{rec.action}</p>
                            <p className="text-xs text-slate-600 mt-1">{rec.reasoning}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Transcript tab */}
            {activeTab === "transcript" && transcript && (
              <div className="glass-card p-6">
                <h3 className="text-sm font-bold text-slate-900 mb-4 flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-indigo-600" />
                  Transcript
                  <span className="text-xs text-slate-500 font-normal ml-2">
                    {transcript.segments?.length} segments
                  </span>
                </h3>
                <div className="space-y-4 max-h-[600px] overflow-y-auto pr-2">
                  {transcript.segments?.map((seg: any) => (
                    <div key={seg.id} className="flex gap-3 p-3 rounded-lg bg-slate-50/50 border border-slate-100">
                      <div className="flex-shrink-0 mt-0.5">
                        <div className="w-7 h-7 rounded-full bg-indigo-100 border border-indigo-200 flex items-center justify-center text-xs font-bold text-indigo-700">
                          {seg.speaker_label?.charAt(0) || "S"}
                        </div>
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-bold text-slate-700">{seg.speaker_label}</span>
                          <span className="text-xs text-slate-400">
                            {Math.floor(seg.start_time / 60)}:{String(Math.floor(seg.start_time % 60)).padStart(2, "0")}
                          </span>
                        </div>
                        <p className="text-sm text-slate-800 leading-relaxed">{seg.text}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Sales tab */}
            {activeTab === "sales" && insights?.sales_insight && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="glass-card p-4">
                    <p className="text-xs font-semibold text-slate-500 mb-1">Lead Score</p>
                    <p className="text-3xl font-extrabold text-indigo-600">{insights.sales_insight.lead_score ?? "N/A"}</p>
                  </div>
                  <div className="glass-card p-4">
                    <p className="text-xs font-semibold text-slate-500 mb-1">Purchase Intent</p>
                    <p className={clsx("text-base font-bold capitalize",
                      insights.sales_insight.purchase_intent === "high" ? "text-emerald-700" :
                      insights.sales_insight.purchase_intent === "medium" ? "text-amber-700" : "text-slate-600"
                    )}>{insights.sales_insight.purchase_intent ?? "N/A"}</p>
                  </div>
                  <div className="glass-card p-4">
                    <p className="text-xs font-semibold text-slate-500 mb-1">Deal Health</p>
                    <p className={clsx("text-base font-bold capitalize",
                      insights.sales_insight.deal_health === "healthy" ? "text-emerald-700" :
                      insights.sales_insight.deal_health === "at_risk" ? "text-amber-700" : "text-rose-700"
                    )}>{insights.sales_insight.deal_health ?? "N/A"}</p>
                  </div>
                  <div className="glass-card p-4">
                    <p className="text-xs font-semibold text-slate-500 mb-1">Closing Probability</p>
                    <p className="text-base font-bold text-purple-700">
                      {insights.sales_insight.closing_probability ? `${Math.round(insights.sales_insight.closing_probability * 100)}%` : "N/A"}
                    </p>
                  </div>
                </div>

                {insights.objections?.length > 0 && (
                  <div className="glass-card p-6">
                    <h3 className="text-sm font-bold text-slate-900 mb-4">Objections Detected</h3>
                    <div className="space-y-3">
                      {insights.objections.map((obj: any) => (
                        <div key={obj.id} className="p-4 rounded-lg bg-slate-50 border border-slate-200">
                          <div className="flex items-center gap-2 mb-2">
                            <span className={clsx("text-xs px-2 py-0.5 rounded-full font-semibold capitalize border",
                              obj.severity === "high" ? "badge-high" : obj.severity === "medium" ? "badge-medium" : "badge-low"
                            )}>
                              {obj.severity}
                            </span>
                            <span className="text-xs font-semibold text-slate-600 capitalize">{obj.category.replace("_", " ")}</span>
                            {obj.was_resolved && <span className="text-xs text-emerald-700 ml-auto flex items-center gap-1 font-semibold"><CheckCircle className="w-3.5 h-3.5" />Resolved</span>}
                          </div>
                          <p className="text-sm font-medium text-slate-900">{obj.description}</p>
                          {obj.exact_quote && <p className="text-xs text-slate-500 mt-1 italic">"{obj.exact_quote}"</p>}
                          {obj.suggested_response && (
                            <p className="text-xs text-indigo-700 font-medium mt-2">💡 {obj.suggested_response}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {insights.sales_insight.buying_signals?.length > 0 && (
                  <div className="glass-card p-6">
                    <h3 className="text-sm font-bold text-slate-900 mb-4">Buying Signals</h3>
                    <div className="space-y-2">
                      {insights.sales_insight.buying_signals.map((s: any, i: number) => (
                        <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-emerald-50/60 border border-emerald-100">
                          <CheckCircle className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                          <div>
                            <p className="text-sm font-medium text-slate-900">{s.signal}</p>
                            {s.evidence && <p className="text-xs text-slate-500 mt-0.5">"{s.evidence}"</p>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Action items tab */}
            {activeTab === "actions" && (
              <div className="glass-card p-6">
                <h3 className="text-sm font-bold text-slate-900 mb-4 flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-600" />
                  Action Items ({insights?.action_items?.length ?? 0})
                </h3>
                <div className="space-y-3">
                  {(insights?.action_items || []).map((item: any) => (
                    <div key={item.id} className="flex items-start gap-3 p-4 rounded-lg bg-slate-50 border border-slate-200">
                      <div className={clsx("w-2 h-2 rounded-full mt-2 flex-shrink-0",
                        item.priority === "urgent" ? "bg-rose-500" :
                        item.priority === "high" ? "bg-amber-500" : "bg-slate-400"
                      )} />
                      <div className="flex-1">
                        <p className="text-sm font-semibold text-slate-900">{item.description}</p>
                        <div className="flex items-center gap-3 mt-1">
                          {item.owner && <span className="text-xs text-slate-500">Owner: {item.owner}</span>}
                          {item.due_date && <span className="text-xs text-slate-500">Due: {item.due_date}</span>}
                          <span className={clsx("text-xs px-2 py-0.5 rounded-full capitalize border",
                            item.priority === "urgent" ? "badge-high" : "badge-medium"
                          )}>{item.priority}</span>
                        </div>
                      </div>
                      <span className={clsx("text-xs px-2.5 py-1 rounded-full font-semibold border",
                        item.status === "completed" ? "badge-positive" : "badge-neutral"
                      )}>
                        {item.status}
                      </span>
                    </div>
                  ))}
                  {(!insights?.action_items || insights.action_items.length === 0) && (
                    <p className="text-slate-400 text-sm text-center py-6">No action items detected</p>
                  )}
                </div>
              </div>
            )}

            {/* Agent Score tab */}
            {activeTab === "agent" && insights?.agent_score && (
              <div className="space-y-4">
                <div className="glass-card p-6">
                  <div className="flex items-center justify-between mb-6">
                    <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                      <Star className="w-4 h-4 text-amber-500" />
                      AI Performance Assessment
                    </h3>
                    <div className="text-center">
                      <div className="text-4xl font-extrabold text-amber-600">{insights.agent_score.overall_score}</div>
                      <div className="text-xs text-slate-400">/100</div>
                    </div>
                  </div>
                  <div className="space-y-3">
                    <ScoreBar score={insights.agent_score.greeting_score} label="Greeting" />
                    <ScoreBar score={insights.agent_score.professionalism_score} label="Professionalism" />
                    <ScoreBar score={insights.agent_score.empathy_score} label="Empathy" />
                    <ScoreBar score={insights.agent_score.listening_score} label="Active Listening" />
                    <ScoreBar score={insights.agent_score.question_quality_score} label="Question Quality" />
                    <ScoreBar score={insights.agent_score.product_knowledge_score} label="Product Knowledge" />
                    <ScoreBar score={insights.agent_score.objection_handling_score} label="Objection Handling" />
                    <ScoreBar score={insights.agent_score.closing_score} label="Closing" />
                  </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  <div className="glass-card p-5">
                    <h4 className="text-xs font-bold text-emerald-700 mb-3 uppercase tracking-wide">Strengths</h4>
                    <ul className="space-y-2">
                      {insights.agent_score.strengths?.map((s: string, i: number) => (
                        <li key={i} className="flex items-start gap-2 text-xs text-slate-700 font-medium">
                          <CheckCircle className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0 mt-0.5" />
                          {s}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="glass-card p-5">
                    <h4 className="text-xs font-bold text-amber-700 mb-3 uppercase tracking-wide">Areas to Improve</h4>
                    <ul className="space-y-2">
                      {insights.agent_score.weaknesses?.map((w: string, i: number) => (
                        <li key={i} className="flex items-start gap-2 text-xs text-slate-700 font-medium">
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-600 flex-shrink-0 mt-0.5" />
                          {w}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {insights.agent_score.disclaimer && (
                  <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
                    <p className="text-xs text-slate-500 flex items-center gap-2">
                      <Shield className="w-3.5 h-3.5 text-slate-400" />
                      {insights.agent_score.disclaimer}
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Meeting Minutes tab */}
            {activeTab === "minutes" && insights?.meeting_minutes && (
              <div className="glass-card p-6">
                {insights.meeting_minutes.formatted_markdown ? (
                  <div className="prose prose-slate prose-sm max-w-none">
                    <pre className="whitespace-pre-wrap text-sm text-slate-800 font-sans leading-relaxed">
                      {insights.meeting_minutes.formatted_markdown}
                    </pre>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div>
                      <h4 className="text-xs font-bold text-slate-500 uppercase mb-2">Objective</h4>
                      <p className="text-sm text-slate-800">{insights.meeting_minutes.objective}</p>
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-500 uppercase mb-2">Next Steps</h4>
                      <ul className="space-y-1">
                        {insights.meeting_minutes.next_steps?.map((s: string, i: number) => (
                          <li key={i} className="text-sm text-slate-800 flex items-start gap-2">
                            <span className="text-indigo-600 font-bold mt-0.5">→</span> {s}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
