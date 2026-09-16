"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import toast from "react-hot-toast";
import { Eye, EyeOff, Loader2, Brain, ArrowRight } from "lucide-react";
import { authApi } from "@/lib/api/auth";
import { useAuthStore } from "@/lib/stores/authStore";

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
    <div className="min-h-screen bg-slate-50 flex">
      {/* Left branding panel */}
      <div className="hidden lg:flex lg:w-1/2 relative bg-indigo-900 text-white flex-col justify-between p-12">
        <div className="absolute inset-0 bg-gradient-to-br from-indigo-900 via-indigo-950 to-slate-950 opacity-90" />
        
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-16">
            <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center shadow-md">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-bold text-white tracking-tight">TalkWiseAI</span>
          </div>

          <h1 className="text-4xl font-extrabold text-white leading-tight mb-6">
            Every conversation<br />
            <span className="text-indigo-300">becomes intelligence</span>
          </h1>

          <p className="text-indigo-200/80 text-lg leading-relaxed mb-12 max-w-md">
            AI-powered platform that transforms your meetings and calls into actionable
            sales insights, meeting intelligence, and business analytics.
          </p>

          {/* Feature highlights */}
          <div className="space-y-4 max-w-md">
            {[
              "🎯 Lead scoring & purchase intent detection",
              "📊 Real-time sentiment & conversation analytics",
              "✅ Automatic action item extraction",
              "🤖 17 specialized AI agents working in parallel",
              "💬 RAG-powered conversation assistant",
            ].map((feature) => (
              <div key={feature} className="flex items-center gap-3 text-indigo-100/90 text-sm">
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 flex-shrink-0" />
                <span>{feature}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="relative z-10 border-t border-indigo-800/60 pt-6">
          <p className="text-indigo-300/60 text-xs">
            Powered by LangGraph Multi-Agent Architecture
          </p>
        </div>
      </div>

      {/* Right login panel */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-white">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="flex items-center gap-3 mb-8 lg:hidden">
            <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <span className="text-lg font-bold text-slate-900">TalkWiseAI</span>
          </div>

          <div className="mb-8">
            <h2 className="text-2xl font-bold text-slate-900 mb-1">Welcome back</h2>
            <p className="text-slate-500 text-sm">Sign in to your account to continue</p>
          </div>

          {/* Demo quick fill */}
          <div className="mb-6 p-4 rounded-xl bg-indigo-50/80 border border-indigo-100">
            <p className="text-xs font-semibold text-indigo-900 mb-2.5">🚀 Demo Quick Login</p>
            <div className="flex gap-2">
              {(["admin", "manager", "agent"] as const).map((role) => (
                <button
                  key={role}
                  type="button"
                  onClick={() => fillDemo(role)}
                  className="flex-1 py-1.5 px-2 text-xs font-medium rounded-lg bg-white border border-indigo-200 hover:border-indigo-400 text-indigo-700 shadow-sm transition-all capitalize"
                >
                  {role}
                </button>
              ))}
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
                {error}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5" htmlFor="email">
                Email address
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                required
                className="w-full px-3.5 py-2.5 rounded-lg bg-white border border-slate-300 text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600 text-sm transition-all"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5" htmlFor="password">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full px-3.5 py-2.5 pr-10 rounded-lg bg-white border border-slate-300 text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600 text-sm transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm flex items-center justify-center gap-2 shadow-sm transition-all duration-150 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  Sign In
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-slate-500 text-sm">
              Don't have an account?{" "}
              <Link href="/register" className="text-indigo-600 hover:text-indigo-700 font-semibold transition-colors">
                Create one
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
