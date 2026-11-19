import { apiClient } from "@/lib/api/client";

/** Download an authenticated API file (window.open can't send the bearer token). */
export async function downloadFile(path: string, filename: string, params?: Record<string, string>) {
  const res = await apiClient.get<Blob>(path, { params, responseType: "blob" });
  saveBlob(res.data, filename);
}

/** Save in-memory text or a Blob as a file. */
export function saveBlob(data: Blob | string, filename: string, type = "text/plain") {
  const blob = typeof data === "string" ? new Blob([data], { type }) : data;
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
