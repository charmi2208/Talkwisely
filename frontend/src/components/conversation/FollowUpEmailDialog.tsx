"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Copy, Mail, Sparkles } from "lucide-react";
import { aiApi, type GenerateEmailResponse } from "@/lib/api/ai";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";

const EMAIL_TYPES = [
  { value: "thank_you", label: "Thank-you email" },
  { value: "meeting_summary", label: "Meeting summary" },
  { value: "proposal_follow_up", label: "Proposal follow-up" },
  { value: "demo_follow_up", label: "Demo follow-up" },
];

const TONES = [
  { value: "professional", label: "Professional" },
  { value: "friendly", label: "Friendly" },
  { value: "concise", label: "Concise" },
  { value: "formal", label: "Formal" },
];

export function FollowUpEmailDialog({ conversationId }: { conversationId: string }) {
  const [open, setOpen] = useState(false);
  const [emailType, setEmailType] = useState("thank_you");
  const [tone, setTone] = useState("professional");
  const [recipientName, setRecipientName] = useState("");
  const [generating, setGenerating] = useState(false);
  const [draft, setDraft] = useState<GenerateEmailResponse | null>(null);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const res = await aiApi.generateEmail({
        conversation_id: conversationId,
        email_type: emailType,
        tone,
        recipient_name: recipientName.trim() || undefined,
      });
      setDraft(res);
      setSubject(res.subject);
      setBody(res.body);
    } catch {
      toast.error("Couldn't generate the email. Please try again.");
    } finally {
      setGenerating(false);
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(`Subject: ${subject}\n\n${body}`);
      toast.success("Email copied to clipboard");
    } catch {
      toast.error("Couldn't copy. Select the text and copy it manually.");
    }
  };

  const mailtoHref = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Mail data-icon="inline-start" />
          Follow-up email
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-2xl max-h-[90svh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Draft a follow-up email</DialogTitle>
          <DialogDescription>
            The draft is written from this conversation. Review and edit it before sending; nothing is sent automatically.
          </DialogDescription>
        </DialogHeader>

        <FieldGroup className="gap-4">
          <div className="grid gap-4 sm:grid-cols-3">
            <Field>
              <FieldLabel htmlFor="email-type">Email type</FieldLabel>
              <Select value={emailType} onValueChange={setEmailType}>
                <SelectTrigger id="email-type" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {EMAIL_TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field>
              <FieldLabel htmlFor="email-tone">Tone</FieldLabel>
              <Select value={tone} onValueChange={setTone}>
                <SelectTrigger id="email-tone" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TONES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field>
              <FieldLabel htmlFor="email-recipient">Recipient name</FieldLabel>
              <Input
                id="email-recipient"
                value={recipientName}
                onChange={(e) => setRecipientName(e.target.value)}
                placeholder="Optional"
              />
            </Field>
          </div>

          <Button onClick={handleGenerate} disabled={generating} className="w-fit">
            {generating ? <Spinner data-icon="inline-start" /> : <Sparkles data-icon="inline-start" />}
            {draft ? "Regenerate draft" : "Generate draft"}
          </Button>

          {draft && (
            <>
              <Field>
                <FieldLabel htmlFor="email-subject">Subject</FieldLabel>
                <Input id="email-subject" value={subject} onChange={(e) => setSubject(e.target.value)} />
              </Field>
              <Field>
                <FieldLabel htmlFor="email-body">Body</FieldLabel>
                <Textarea
                  id="email-body"
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  className="min-h-56 max-h-80 font-sans"
                />
              </Field>
              {draft.suggested_actions.length > 0 && (
                <Alert>
                  <AlertDescription>
                    <span className="font-medium text-foreground">Suggested next steps: </span>
                    {draft.suggested_actions.join("; ")}
                  </AlertDescription>
                </Alert>
              )}
            </>
          )}
        </FieldGroup>

        {draft && (
          <DialogFooter>
            <Button variant="outline" onClick={handleCopy}>
              <Copy data-icon="inline-start" />
              Copy
            </Button>
            <Button asChild>
              <a href={mailtoHref}>
                <Mail data-icon="inline-start" />
                Open in email app
              </a>
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}
