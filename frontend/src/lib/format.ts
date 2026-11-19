import { parseApiDate } from "@/lib/dates";

export const CONVERSATION_TYPES = [
  "sales", "customer_support", "product_demo", "follow_up", "internal_meeting",
  "client_meeting", "complaint", "general_business", "other",
] as const;

/** "customer_support" -> "Customer support" */
export function humanize(value: string | null | undefined): string {
  if (!value) return "";
  const text = value.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function formatDuration(seconds: number | null | undefined): string {
  if (!seconds) return "-";
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return m ? `${m}m ${s.toString().padStart(2, "0")}s` : `${s}s`;
}

export function formatDate(value: string | null | undefined, opts: Intl.DateTimeFormatOptions = { dateStyle: "medium" }): string {
  if (!value) return "-";
  return parseApiDate(value).toLocaleDateString(undefined, opts);
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "-";
  return parseApiDate(value).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

/** Chart axis label for an ISO day ("2026-11-03" -> "Nov 3"), read as a calendar day. */
export function shortDay(day: string): string {
  const [y, m, d] = day.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
