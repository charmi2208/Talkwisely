"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Brain, MailCheck } from "lucide-react";
import { apiClient } from "@/lib/api/client";
import { apiErrorMessage } from "@/lib/api/errors";
import { AuthBrandPanel } from "@/components/auth/AuthBrandPanel";
import { ModeToggle } from "@/components/mode-toggle";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState<{ message: string; devUrl?: string } | null>(null);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await apiClient.post<{ message: string; dev_reset_url?: string }>("/auth/forgot-password", { email });
      setSent({ message: res.data.message, devUrl: res.data.dev_reset_url });
    } catch (err) {
      setError(apiErrorMessage(err, "Something went wrong. Please try again."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-muted flex">
      <AuthBrandPanel />
      <div className="relative w-full lg:w-1/2 flex items-center justify-center p-8 bg-background">
        <div className="absolute top-4 right-4">
          <ModeToggle />
        </div>
        <div className="w-full max-w-md">
          <div className="flex items-center gap-3 mb-8 lg:hidden">
            <div className="size-9 rounded-lg bg-primary text-primary-foreground flex items-center justify-center">
              <Brain className="size-5" />
            </div>
            <span className="text-lg font-semibold">TalkWiseAI</span>
          </div>

          <div className="mb-8">
            <h2 className="text-2xl font-semibold tracking-tight mb-1">Reset your password</h2>
            <p className="text-muted-foreground text-sm">Enter your account email and we&apos;ll send you a reset link.</p>
          </div>

          {sent ? (
            <div className="space-y-4">
              <Alert>
                <MailCheck />
                <AlertTitle>Check your email</AlertTitle>
                <AlertDescription>{sent.message} The link expires in 30 minutes.</AlertDescription>
              </Alert>
              {sent.devUrl && (
                <Alert>
                  <AlertTitle>Development mode</AlertTitle>
                  <AlertDescription>
                    Email delivery is mocked, so here is the link that would have been sent:{" "}
                    <Link href={sent.devUrl.replace(/^https?:\/\/[^/]+/, "")} className="font-medium underline">
                      open the reset page
                    </Link>
                  </AlertDescription>
                </Alert>
              )}
            </div>
          ) : (
            <form onSubmit={handleSubmit}>
              <FieldGroup className="gap-4">
                {error && (
                  <Alert variant="destructive">
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}
                <Field>
                  <FieldLabel htmlFor="email">Email address</FieldLabel>
                  <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" required />
                </Field>
                <Button type="submit" size="lg" disabled={loading} className="w-full">
                  {loading ? <Spinner /> : "Send reset link"}
                </Button>
              </FieldGroup>
            </form>
          )}

          <div className="mt-6 text-center">
            <Button variant="link" asChild className="h-auto p-0">
              <Link href="/login"><ArrowLeft data-icon="inline-start" />Back to sign in</Link>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
