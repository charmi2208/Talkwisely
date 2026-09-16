import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "TalkWiseAI — AI-Powered Meeting & Sales Intelligence",
    template: "%s | TalkWiseAI",
  },
  description:
    "Transform every business conversation into actionable intelligence. AI-powered meeting summaries, sales insights, sentiment analysis, and more.",
  keywords: [
    "AI meeting intelligence",
    "call analytics",
    "sales intelligence",
    "conversation AI",
    "meeting summary",
    "sentiment analysis",
  ],
  authors: [{ name: "TalkWiseAI" }],
  openGraph: {
    title: "TalkWiseAI — AI-Powered Conversation Intelligence",
    description: "Turn meetings and calls into structured business intelligence",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable} suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
      </head>
      <body className="antialiased">
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          <TooltipProvider>{children}</TooltipProvider>
          <Toaster position="top-right" />
        </ThemeProvider>
      </body>
    </html>
  );
}
