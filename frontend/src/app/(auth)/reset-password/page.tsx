"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { ArrowLeft, Brain } from "lucide-react";
import { apiClient } from "@/lib/api/client";
import { apiErrorMessage } from "@/lib/api/errors";
import { AuthBrandPanel } from "@/components/auth/AuthBrandPanel";
import { ModeToggle } from "@/components/mode-toggle";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";

function ResetPasswordForm() {
  const router = useRouter();
  const token = useSearchParams().get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirm) {
      setError("The passwords don't match.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      await apiClient.post("/auth/reset-password", { token, new_password: password });
      toast.success("Password updated. Sign in with your new password.");
      router.push("/login");
    } catch (err) {
      setError(apiErrorMessage(err, "This reset link didn't work. Request a new one."));
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <Alert variant="destructive">
        <AlertDescription>
          This page needs the link from your reset email.{" "}
          <Link href="/forgot-password" className="font-medium underline">Request a new link</Link>.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <form onSubmit={handleSubmit}>
      <FieldGroup className="gap-4">
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        <Field>
          <FieldLabel htmlFor="new-password">New password</FieldLabel>
          <Input id="new-password" type="password" autoComplete="new-password" minLength={8} required
            value={password} onChange={(e) => setPassword(e.target.value)} />
          <FieldDescription>At least 8 characters.</FieldDescription>
        </Field>
        <Field>
          <FieldLabel htmlFor="confirm-password">Confirm new password</FieldLabel>
          <Input id="confirm-password" type="password" autoComplete="new-password" minLength={8} required
            value={confirm} onChange={(e) => setConfirm(e.target.value)} />
        </Field>
        <Button type="submit" size="lg" disabled={loading} className="w-full">
          {loading ? <Spinner /> : "Set new password"}
        </Button>
      </FieldGroup>
    </form>
  );
}

export default function ResetPasswordPage() {
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
            <h2 className="text-2xl font-semibold tracking-tight mb-1">Choose a new password</h2>
            <p className="text-muted-foreground text-sm">Reset links expire 30 minutes after they&apos;re sent.</p>
          </div>
          <Suspense fallback={<Spinner className="size-6" />}>
            <ResetPasswordForm />
          </Suspense>
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
