"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { conversationsApi } from "@/lib/api/conversations";
import {
  ArrowLeft, RefreshCw, CheckCircle, TrendingUp,
  MessageSquare, BarChart3, Shield, Lightbulb, AlertTriangle,
  Star, Trash2, Volume2, Database, Bot
} from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { clsx } from "clsx";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle,
} from "@/components/ui/card";
import {
  Item, ItemActions, ItemContent, ItemDescription, ItemGroup, ItemMedia, ItemTitle,
} from "@/components/ui/item";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Spinner } from "@/components/ui/spinner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ConversationChat } from "@/components/conversation/ConversationChat";
import { CrmProposalsPanel } from "@/components/conversation/CrmProposalsPanel";
import { FollowUpEmailDialog } from "@/components/conversation/FollowUpEmailDialog";

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
      <span className="text-xs font-medium text-muted-foreground w-32 shrink-0">{label}</span>
      <Progress
        value={w}
        className={clsx("h-2 flex-1",
          w >= 80 ? "*:data-[slot=progress-indicator]:bg-emerald-500" :
          w >= 60 ? "*:data-[slot=progress-indicator]:bg-amber-500" :
          "*:data-[slot=progress-indicator]:bg-destructive"
        )}
      />
      <span className="text-xs font-semibold w-8 text-right tabular-nums">{score}</span>
    </div>
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

function LevelBadge({ level, className }: { level: string; className?: string }) {
  return (
    <Badge
      variant={level === "urgent" || level === "high" ? "destructive" : level === "medium" ? "secondary" : "outline"}
      className={clsx("capitalize", className)}
    >
      {level}
    </Badge>
  );
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
    { id: "crm", label: "CRM Updates", icon: Database },
    { id: "chat", label: "Ask AI", icon: Bot },
  ];

  if (loading) {
    return (
      <AppShell title="Loading..." >
        <div className="flex items-center justify-center h-64">
          <Spinner className="size-8" />
        </div>
      </AppShell>
    );
  }

  if (!conversation) {
    return (
      <AppShell title="Not Found">
        <div className="text-center py-16 text-muted-foreground">Conversation not found.</div>
      </AppShell>
    );
  }

  const isProcessing = ["processing", "transcribing", "analyzing", "queued", "uploaded"].includes(conversation.status);

  const handleDelete = async () => {
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
        <div className="flex items-center gap-2">
          <Button variant="ghost" asChild>
            <Link href="/conversations">
              <ArrowLeft data-icon="inline-start" />
              Back
            </Link>
          </Button>
          <div className="flex-1" />
          {conversation.status === "completed" && <FollowUpEmailDialog conversationId={id} />}
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="destructive" size="sm">
                <Trash2 data-icon="inline-start" />
                Delete
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete conversation?</AlertDialogTitle>
                <AlertDialogDescription>
                  Are you sure you want to delete this conversation?
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction variant="destructive" onClick={handleDelete}>
                  Delete
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
          <Button variant="outline" size="sm" onClick={loadConversation}>
            <RefreshCw data-icon="inline-start" />
            Refresh
          </Button>
        </div>

        {/* Processing state */}
        {isProcessing && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-3">
                <Spinner className="size-5" />
                Processing your recording...
              </CardTitle>
              <CardDescription>{step}</CardDescription>
              <CardAction className="text-sm font-semibold tabular-nums">{progress}%</CardAction>
            </CardHeader>
            <CardContent>
              <Progress value={progress} className="h-2" />
              <p className="text-xs text-muted-foreground mt-1">
                AI is running 15+ specialized agents in parallel. This may take 1-3 minutes.
              </p>
            </CardContent>
          </Card>
        )}

        {/* Failed state */}
        {conversation.status === "failed" && (
          <Alert variant="destructive">
            <AlertTriangle />
            <AlertTitle>Processing Failed</AlertTitle>
            <AlertDescription>{conversation.error_message || "An error occurred during processing"}</AlertDescription>
          </Alert>
        )}

        {/* Key metrics (when completed) */}
        {conversation.status === "completed" && insights && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {insights.sentiment && (
              <Card size="sm">
                <CardHeader>
                  <CardDescription>Overall Sentiment</CardDescription>
                </CardHeader>
                <CardContent className="items-start gap-1">
                  <SentimentBadge sentiment={insights.sentiment.overall_sentiment} />
                  <p className="text-xs text-muted-foreground">
                    Score: {insights.sentiment.overall_score?.toFixed(2)}
                  </p>
                </CardContent>
              </Card>
            )}
            {insights.sales_insight?.lead_score && (
              <Card size="sm">
                <CardHeader>
                  <CardDescription>Lead Score</CardDescription>
                  <CardTitle className="text-3xl font-semibold tabular-nums">{insights.sales_insight.lead_score}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground">/100</p>
                </CardContent>
              </Card>
            )}
            {insights.intent && (
              <Card size="sm">
                <CardHeader>
                  <CardDescription>Primary Intent</CardDescription>
                  <CardTitle className="capitalize">
                    {insights.intent.primary_intent?.replace("_", " ")}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground">{Math.round((insights.intent.confidence || 0) * 100)}% confident</p>
                </CardContent>
              </Card>
            )}
            {insights.action_items && (
              <Card size="sm">
                <CardHeader>
                  <CardDescription>Action Items</CardDescription>
                  <CardTitle className="text-3xl font-semibold tabular-nums">{insights.action_items.length}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground">tasks identified</p>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {/* Audio Player Card */}
        {conversation.file_name && (
          <Item variant="outline" className="bg-card flex-col sm:flex-row">
            <ItemMedia variant="icon" className="size-10 rounded-lg bg-muted">
              <Volume2 className="size-5" />
            </ItemMedia>
            <ItemContent className="min-w-0">
              <ItemTitle>{conversation.file_name || "Audio Recording"}</ItemTitle>
              <ItemDescription className="text-xs">Audio playback stream</ItemDescription>
            </ItemContent>
            <ItemActions className="w-full sm:w-auto">
              {audioSrc ? (
                <audio
                  controls
                  src={audioSrc}
                  className="w-full sm:w-80 h-9 rounded-md"
                />
              ) : (
                <Badge variant="outline">
                  <Spinner data-icon="inline-start" />
                  Loading audio stream...
                </Badge>
              )}
            </ItemActions>
          </Item>
        )}

        {/* Tabs */}
        {conversation.status === "completed" && (
          <Tabs value={activeTab} onValueChange={setActiveTab} className="gap-4">
            <TabsList variant="line" className="w-full justify-start overflow-x-auto">
              {tabs.map((tab) => (
                <TabsTrigger key={tab.id} value={tab.id} className="flex-none">
                  <tab.icon />
                  {tab.label}
                </TabsTrigger>
              ))}
            </TabsList>

            {/* Insights tab */}
            <TabsContent value="insights">
              {insights?.summary && (
                <div className="space-y-4">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Lightbulb className="size-4" />
                        Executive Summary
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm leading-relaxed">{insights.summary.executive_summary}</p>
                    </CardContent>
                  </Card>

                  {insights.summary.key_topics?.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle>Key Topics</CardTitle>
                      </CardHeader>
                      <CardContent className="flex-row flex-wrap gap-2">
                        {insights.summary.key_topics.map((topic: string) => (
                          <Badge key={topic} variant="secondary">
                            {topic}
                          </Badge>
                        ))}
                      </CardContent>
                    </Card>
                  )}

                  {insights.pain_points?.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <AlertTriangle className="size-4 text-warning" />
                          Pain Points Detected
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <ItemGroup className="gap-3">
                          {insights.pain_points.map((pp: any) => (
                            <Item key={pp.id} variant="muted" size="sm" className="items-stretch">
                              <ItemMedia className="self-stretch group-has-data-[slot=item-description]/item:translate-y-0 group-has-data-[slot=item-description]/item:self-stretch">
                                <span className={clsx("w-1.5 self-stretch rounded-full",
                                  pp.severity === "high" ? "bg-destructive" : pp.severity === "medium" ? "bg-amber-500" : "bg-muted-foreground/40"
                                )} />
                              </ItemMedia>
                              <ItemContent>
                                <ItemTitle className="line-clamp-none">{pp.description}</ItemTitle>
                                {pp.evidence && <ItemDescription className="text-xs italic line-clamp-none">"{pp.evidence}"</ItemDescription>}
                              </ItemContent>
                            </Item>
                          ))}
                        </ItemGroup>
                      </CardContent>
                    </Card>
                  )}

                  {insights.recommendations?.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <Lightbulb className="size-4 text-success" />
                          AI Recommendations
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <ItemGroup className="gap-3">
                          {insights.recommendations.map((rec: any) => (
                            <Item key={rec.id} variant="muted">
                              <ItemMedia>
                                <LevelBadge level={rec.priority} />
                              </ItemMedia>
                              <ItemContent>
                                <ItemTitle className="line-clamp-none">{rec.action}</ItemTitle>
                                <ItemDescription className="text-xs line-clamp-none">{rec.reasoning}</ItemDescription>
                              </ItemContent>
                            </Item>
                          ))}
                        </ItemGroup>
                      </CardContent>
                    </Card>
                  )}
                </div>
              )}
            </TabsContent>

            {/* Transcript tab */}
            <TabsContent value="transcript">
              {transcript && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <MessageSquare className="size-4" />
                      Transcript
                      <span className="text-xs text-muted-foreground font-normal ml-2">
                        {transcript.segments?.length} segments
                      </span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ScrollArea className="pr-3 *:data-[slot=scroll-area-viewport]:max-h-[600px]">
                      <ItemGroup className="gap-4">
                        {transcript.segments?.map((seg: any) => (
                          <Item key={seg.id} variant="muted" size="sm">
                            <ItemMedia>
                              <Avatar size="sm" className="size-7">
                                <AvatarFallback className="text-xs font-semibold">
                                  {seg.speaker_label?.charAt(0) || "S"}
                                </AvatarFallback>
                              </Avatar>
                            </ItemMedia>
                            <ItemContent>
                              <ItemTitle className="text-xs">
                                {seg.speaker_label}
                                <span className="font-normal text-muted-foreground tabular-nums">
                                  {Math.floor(seg.start_time / 60)}:{String(Math.floor(seg.start_time % 60)).padStart(2, "0")}
                                </span>
                              </ItemTitle>
                              <p className="text-sm leading-relaxed">{seg.text}</p>
                            </ItemContent>
                          </Item>
                        ))}
                      </ItemGroup>
                    </ScrollArea>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            {/* Sales tab */}
            <TabsContent value="sales">
              {insights?.sales_insight && (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    <Card size="sm">
                      <CardHeader>
                        <CardDescription>Lead Score</CardDescription>
                        <CardTitle className="text-3xl font-semibold tabular-nums">{insights.sales_insight.lead_score ?? "N/A"}</CardTitle>
                      </CardHeader>
                    </Card>
                    <Card size="sm">
                      <CardHeader>
                        <CardDescription>Purchase Intent</CardDescription>
                        <CardTitle className={clsx("capitalize",
                          insights.sales_insight.purchase_intent === "high" ? "text-success" :
                          insights.sales_insight.purchase_intent === "medium" ? "text-warning" : "text-muted-foreground"
                        )}>{insights.sales_insight.purchase_intent ?? "N/A"}</CardTitle>
                      </CardHeader>
                    </Card>
                    <Card size="sm">
                      <CardHeader>
                        <CardDescription>Deal Health</CardDescription>
                        <CardTitle className={clsx("capitalize",
                          insights.sales_insight.deal_health === "healthy" ? "text-success" :
                          insights.sales_insight.deal_health === "at_risk" ? "text-warning" : "text-destructive"
                        )}>{insights.sales_insight.deal_health ?? "N/A"}</CardTitle>
                      </CardHeader>
                    </Card>
                    <Card size="sm">
                      <CardHeader>
                        <CardDescription>Closing Probability</CardDescription>
                        <CardTitle>
                          {insights.sales_insight.closing_probability ? `${Math.round(insights.sales_insight.closing_probability * 100)}%` : "N/A"}
                        </CardTitle>
                      </CardHeader>
                    </Card>
                  </div>

                  {insights.objections?.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle>Objections Detected</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <ItemGroup className="gap-3">
                          {insights.objections.map((obj: any) => (
                            <Item key={obj.id} variant="muted">
                              <ItemContent>
                                <div className="flex items-center gap-2 mb-1">
                                  <LevelBadge level={obj.severity} />
                                  <span className="text-xs font-semibold text-muted-foreground capitalize">{obj.category.replace("_", " ")}</span>
                                  {obj.was_resolved && (
                                    <Badge variant="outline" className="ml-auto">
                                      <CheckCircle data-icon="inline-start" className="text-success" />
                                      Resolved
                                    </Badge>
                                  )}
                                </div>
                                <ItemTitle className="line-clamp-none">{obj.description}</ItemTitle>
                                {obj.exact_quote && <ItemDescription className="text-xs italic line-clamp-none">"{obj.exact_quote}"</ItemDescription>}
                                {obj.suggested_response && (
                                  <p className="text-xs font-medium mt-1 flex items-start gap-1.5">
                                    <Lightbulb className="size-3.5 shrink-0 mt-px" />
                                    {obj.suggested_response}
                                  </p>
                                )}
                              </ItemContent>
                            </Item>
                          ))}
                        </ItemGroup>
                      </CardContent>
                    </Card>
                  )}

                  {insights.sales_insight.buying_signals?.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle>Buying Signals</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <ItemGroup className="gap-2">
                          {insights.sales_insight.buying_signals.map((s: any, i: number) => (
                            <Item key={i} variant="outline" size="sm">
                              <ItemMedia variant="icon">
                                <CheckCircle className="text-success" />
                              </ItemMedia>
                              <ItemContent>
                                <ItemTitle className="line-clamp-none">{s.signal}</ItemTitle>
                                {s.evidence && <ItemDescription className="text-xs line-clamp-none">"{s.evidence}"</ItemDescription>}
                              </ItemContent>
                            </Item>
                          ))}
                        </ItemGroup>
                      </CardContent>
                    </Card>
                  )}
                </div>
              )}
            </TabsContent>

            {/* Action items tab */}
            <TabsContent value="actions">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <CheckCircle className="size-4 text-success" />
                    Action Items ({insights?.action_items?.length ?? 0})
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ItemGroup className="gap-3">
                    {(insights?.action_items || []).map((item: any) => (
                      <Item key={item.id} variant="muted">
                        <ItemMedia>
                          <span className={clsx("size-2 rounded-full",
                            item.priority === "urgent" ? "bg-destructive" :
                            item.priority === "high" ? "bg-amber-500" : "bg-muted-foreground/40"
                          )} />
                        </ItemMedia>
                        <ItemContent>
                          <ItemTitle className="line-clamp-none">{item.description}</ItemTitle>
                          <div className="flex items-center gap-3">
                            {item.owner && <span className="text-xs text-muted-foreground">Owner: {item.owner}</span>}
                            {item.due_date && <span className="text-xs text-muted-foreground">Due: {item.due_date}</span>}
                            <LevelBadge level={item.priority} />
                          </div>
                        </ItemContent>
                        <ItemActions>
                          <Badge variant={item.status === "completed" ? "secondary" : "outline"}>
                            {item.status}
                          </Badge>
                        </ItemActions>
                      </Item>
                    ))}
                    {(!insights?.action_items || insights.action_items.length === 0) && (
                      <p className="text-muted-foreground text-sm text-center py-6">No action items detected</p>
                    )}
                  </ItemGroup>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Agent Score tab */}
            <TabsContent value="agent">
              {insights?.agent_score && (
                <div className="space-y-4">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Star className="size-4 text-warning" />
                        AI Performance Assessment
                      </CardTitle>
                      <CardAction className="text-center">
                        <div className="text-4xl font-semibold tabular-nums">{insights.agent_score.overall_score}</div>
                        <div className="text-xs text-muted-foreground">/100</div>
                      </CardAction>
                    </CardHeader>
                    <CardContent>
                      <ScoreBar score={insights.agent_score.greeting_score} label="Greeting" />
                      <ScoreBar score={insights.agent_score.professionalism_score} label="Professionalism" />
                      <ScoreBar score={insights.agent_score.empathy_score} label="Empathy" />
                      <ScoreBar score={insights.agent_score.listening_score} label="Active Listening" />
                      <ScoreBar score={insights.agent_score.question_quality_score} label="Question Quality" />
                      <ScoreBar score={insights.agent_score.product_knowledge_score} label="Product Knowledge" />
                      <ScoreBar score={insights.agent_score.objection_handling_score} label="Objection Handling" />
                      <ScoreBar score={insights.agent_score.closing_score} label="Closing" />
                    </CardContent>
                  </Card>

                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <Card size="sm">
                      <CardHeader>
                        <CardTitle className="text-xs font-semibold text-success uppercase tracking-wide">Strengths</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <ul className="space-y-2">
                          {insights.agent_score.strengths?.map((s: string, i: number) => (
                            <li key={i} className="flex items-start gap-2 text-xs font-medium">
                              <CheckCircle className="size-3.5 text-success shrink-0 mt-0.5" />
                              {s}
                            </li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>
                    <Card size="sm">
                      <CardHeader>
                        <CardTitle className="text-xs font-semibold text-warning uppercase tracking-wide">Areas to Improve</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <ul className="space-y-2">
                          {insights.agent_score.weaknesses?.map((w: string, i: number) => (
                            <li key={i} className="flex items-start gap-2 text-xs font-medium">
                              <AlertTriangle className="size-3.5 text-warning shrink-0 mt-0.5" />
                              {w}
                            </li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>
                  </div>

                  {insights.agent_score.disclaimer && (
                    <Alert>
                      <Shield />
                      <AlertDescription className="text-xs">{insights.agent_score.disclaimer}</AlertDescription>
                    </Alert>
                  )}
                </div>
              )}
            </TabsContent>

            {/* Meeting Minutes tab */}
            <TabsContent value="minutes">
              {insights?.meeting_minutes && (
                <Card>
                  <CardContent>
                    {insights.meeting_minutes.formatted_markdown ? (
                      <pre className="whitespace-pre-wrap text-sm font-sans leading-relaxed">
                        {insights.meeting_minutes.formatted_markdown}
                      </pre>
                    ) : (
                      <div className="space-y-4">
                        <div>
                          <h4 className="text-xs font-semibold text-muted-foreground uppercase mb-2">Objective</h4>
                          <p className="text-sm">{insights.meeting_minutes.objective}</p>
                        </div>
                        <div>
                          <h4 className="text-xs font-semibold text-muted-foreground uppercase mb-2">Next Steps</h4>
                          <ul className="space-y-1">
                            {insights.meeting_minutes.next_steps?.map((s: string, i: number) => (
                              <li key={i} className="text-sm flex items-start gap-2">
                                <span className="font-bold mt-0.5">→</span> {s}
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}
            </TabsContent>
            {/* CRM Updates tab */}
            <TabsContent value="crm">
              <CrmProposalsPanel conversationId={id} />
            </TabsContent>

            {/* Ask AI tab */}
            <TabsContent value="chat">
              <ConversationChat conversationId={id} />
            </TabsContent>
          </Tabs>
        )}
      </div>
    </AppShell>
  );
}
