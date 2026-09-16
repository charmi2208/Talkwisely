import { Brain } from "lucide-react";
import { Separator } from "@/components/ui/separator";

const features = [
  "Lead scoring & purchase intent detection",
  "Real-time sentiment & conversation analytics",
  "Automatic action item extraction",
  "17 specialized AI agents working in parallel",
  "RAG-powered conversation assistant",
];

/** Left-hand brand panel shared by the login and register screens. */
export function AuthBrandPanel() {
  return (
    <div className="hidden lg:flex lg:w-1/2 relative bg-brand-panel text-brand-panel-foreground flex-col justify-between p-12">
      <div className="relative z-10">
        <div className="flex items-center gap-3 mb-16">
          <div className="size-10 rounded-lg bg-brand-panel-foreground text-brand-panel flex items-center justify-center">
            <Brain className="size-6" />
          </div>
          <span className="text-xl font-semibold tracking-tight">TalkWiseAI</span>
        </div>

        <h1 className="text-4xl font-bold leading-tight mb-6">
          Every conversation<br />
          <span className="text-brand-panel-foreground/60">becomes intelligence</span>
        </h1>

        <p className="text-brand-panel-foreground/70 text-lg leading-relaxed mb-12 max-w-md">
          AI-powered platform that transforms your meetings and calls into actionable
          sales insights, meeting intelligence, and business analytics.
        </p>

        <div className="space-y-4 max-w-md">
          {features.map((feature) => (
            <div key={feature} className="flex items-center gap-3 text-brand-panel-foreground/90 text-sm">
              <div className="size-1.5 rounded-full bg-brand-panel-foreground/60 shrink-0" />
              <span>{feature}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="relative z-10">
        <Separator className="mb-6 bg-brand-panel-foreground/15" />
        <p className="text-brand-panel-foreground/50 text-xs">
          Powered by LangGraph Multi-Agent Architecture
        </p>
      </div>
    </div>
  );
}
