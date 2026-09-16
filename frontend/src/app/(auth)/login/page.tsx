"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { Eye, EyeOff, Brain, ArrowRight, AlertCircle } from "lucide-react";
import { authApi } from "@/lib/api/auth";
import { useAuthStore } from "@/lib/stores/authStore";
import { AuthBrandPanel } from "@/components/auth/AuthBrandPanel";
import { ModeToggle } from "@/components/mode-toggle";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { InputGroup, InputGroupAddon, InputGroupButton, InputGroupInput } from "@/components/ui/input-group";
import { Spinner } from "@/components/ui/spinner";

export default function LoginPage() {
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const tokenData = await authApi.login({ email, password });
      localStorage.setItem("access_token", tokenData.access_token);
      localStorage.setItem("refresh_token", tokenData.refresh_token);
      const profile = await authApi.me();
      setAuth(
        { accessToken: tokenData.access_token, refreshToken: tokenData.refresh_token },
        profile
      );
      toast.success(`Welcome back, ${profile.full_name.split(" ")[0]}!`);
      router.push("/dashboard");
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Login failed. Please check your credentials.";
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const fillDemo = (role: "admin" | "manager" | "agent") => {
    const creds = {
      admin: { email: "admin@demo.talkwiseai.com", password: "admin123" },
      manager: { email: "manager@demo.talkwiseai.com", password: "manager123" },
      agent: { email: "agent@demo.talkwiseai.com", password: "agent123" },
    }[role];
    setEmail(creds.email);
    setPassword(creds.password);
  };

  return (
    <div className="min-h-screen bg-muted flex">
      <AuthBrandPanel />

      {/* Right login panel */}
      <div className="relative w-full lg:w-1/2 flex items-center justify-center p-8 bg-background">
        <div className="absolute top-4 right-4">
          <ModeToggle />
        </div>
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="flex items-center gap-3 mb-8 lg:hidden">
            <div className="size-9 rounded-lg bg-primary text-primary-foreground flex items-center justify-center">
              <Brain className="size-5" />
            </div>
            <span className="text-lg font-semibold">TalkWiseAI</span>
          </div>

          <div className="mb-8">
            <h2 className="text-2xl font-semibold tracking-tight mb-1">Welcome back</h2>
            <p className="text-muted-foreground text-sm">Sign in to your account to continue</p>
          </div>

          {/* Demo quick fill */}
          <Card size="sm" className="mb-6 bg-muted/50">
            <CardHeader>
              <CardTitle className="text-xs font-semibold">Demo Quick Login</CardTitle>
            </CardHeader>
            <CardContent className="flex-row gap-2">
              {(["admin", "manager", "agent"] as const).map((role) => (
                <Button
                  key={role}
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => fillDemo(role)}
                  className="flex-1 capitalize"
                >
                  {role}
                </Button>
              ))}
            </CardContent>
          </Card>

          <form onSubmit={handleSubmit}>
            <FieldGroup className="gap-4">
              {error && (
                <Alert variant="destructive">
                  <AlertCircle />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <Field>
                <FieldLabel htmlFor="email">Email address</FieldLabel>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  required
                />
              </Field>

              <Field>
                <FieldLabel htmlFor="password">Password</FieldLabel>
                <InputGroup>
                  <InputGroupInput
                    id="password"
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                  />
                  <InputGroupAddon align="inline-end">
                    <InputGroupButton
                      size="icon-xs"
                      onClick={() => setShowPassword(!showPassword)}
                      aria-label={showPassword ? "Hide password" : "Show password"}
                    >
                      {showPassword ? <EyeOff /> : <Eye />}
                    </InputGroupButton>
                  </InputGroupAddon>
                </InputGroup>
              </Field>

              <Button type="submit" size="lg" disabled={loading} className="w-full">
                {loading ? (
                  <Spinner />
                ) : (
                  <>
                    Sign In
                    <ArrowRight data-icon="inline-end" />
                  </>
                )}
              </Button>
            </FieldGroup>
          </form>

          <div className="mt-6 text-center">
            <p className="text-muted-foreground text-sm">
              Don't have an account?{" "}
              <Button variant="link" asChild className="h-auto p-0 font-semibold">
                <Link href="/register">Create one</Link>
              </Button>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
