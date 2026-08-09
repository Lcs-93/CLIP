import { ExportRecord } from "@/lib/types";

export type ExportComputedStatus = "READY" | "RUNNING" | "ERROR";

export function exportStatus(entryStatus: string, outputUrl?: string | null): ExportComputedStatus {
  if (outputUrl || entryStatus === "done") return "READY";
  if (entryStatus === "error" || entryStatus === "failed") return "ERROR";
  return "RUNNING";
}

export function exportStatusTone(status: ExportComputedStatus) {
  if (status === "READY") {
    return "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300";
  }
  if (status === "ERROR") {
    return "border-destructive/30 bg-destructive/10 text-destructive";
  }
  return "border-sky-500/30 bg-sky-500/10 text-sky-700 dark:text-sky-300";
}

export function clipTitle(userTitle?: string | null, tiktokTitle?: string | null, clipId?: string) {
  return (userTitle ?? tiktokTitle ?? "").trim() || `Clip ${clipId?.slice(0, 8) ?? ""}`;
}

export function formatDate(value?: string) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  return date.toLocaleString();
}

export function rowSearchText(row: ExportRecord) {
  return [
    row.exportEntry.id,
    row.clip.id,
    row.video.id,
    row.video.filename,
    row.exportEntry.mode,
    clipTitle(row.clip.user_title, row.clip.tiktok_title, row.clip.id),
  ]
    .join(" ")
    .toLowerCase();
}
