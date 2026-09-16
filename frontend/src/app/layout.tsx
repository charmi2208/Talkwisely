import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Toaster } from "react-hot-toast";

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
    <html lang="en" className={inter.variable}>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
      </head>
      <body className="antialiased">
        {children}
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: "#1e293b",
              color: "#e2e8f0",
              border: "1px solid rgba(59, 130, 246, 0.2)",
              borderRadius: "8px",
            },
          }}
        />
      </body>
    </html>
  );
}
