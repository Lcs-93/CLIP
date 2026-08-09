import { ClipEntry, VideoEntry } from "@/lib/types";
import { formatTimestamp } from "@/lib/workflow-utils";

export const SCORE_THRESHOLDS = {
  topPick: 0.82,
  good: 0.64,
};

export type ClipScoreBand = "top" | "good" | "low" | "none";

export function clipTitle(clip: ClipEntry) {
  return (clip.user_title ?? clip.tiktok_title ?? "").trim() || `Clip ${clip.id.slice(0, 8)}`;
}

export function scorePercent(score?: number | null) {
  if (typeof score !== "number" || !Number.isFinite(score)) return null;
  return Math.round(score * 100);
}

export function clipDurationSeconds(clip: ClipEntry) {
  return Math.max(0, clip.end_seconds - clip.start_seconds);
}

export function clipDurationLabel(clip: ClipEntry) {
  return formatTimestamp(clipDurationSeconds(clip));
}

export function clipTimeRangeLabel(clip: ClipEntry) {
  return `${formatTimestamp(clip.start_seconds)} - ${formatTimestamp(clip.end_seconds)}`;
}

export function clipScoreBand(score?: number | null): ClipScoreBand {
  if (typeof score !== "number" || !Number.isFinite(score)) return "none";
  if (score >= SCORE_THRESHOLDS.topPick) return "top";
  if (score >= SCORE_THRESHOLDS.good) return "good";
  return "low";
}

export function clipScoreLabel(score?: number | null) {
  const band = clipScoreBand(score);
  if (band === "top") return "Top pick";
  if (band === "good") return "Good";
  if (band === "low") return "Low";
  return "No score";
}

export function clipScoreChipClass(score?: number | null) {
  const band = clipScoreBand(score);
  if (band === "top") {
    return "border-emerald-500/30 bg-emerald-500/15 text-emerald-700 dark:text-emerald-300";
  }
  if (band === "good") {
    return "border-sky-500/30 bg-sky-500/14 text-sky-700 dark:text-sky-300";
  }
  if (band === "low") {
    return "border-amber-500/30 bg-amber-500/14 text-amber-700 dark:text-amber-300";
  }
  return "border-border/70 bg-background/70 text-muted-foreground";
}

export function clipReady(status?: string | null) {
  if (!status) return true;
  const normalized = status.toLowerCase();
  return ["ready", "done", "completed", "ok"].some((value) => normalized.includes(value));
}

export function clipDateEpoch(clip: ClipEntry) {
  if (!clip.created_at) return 0;
  const epoch = Date.parse(clip.created_at);
  return Number.isFinite(epoch) ? epoch : 0;
}

export function videoStatusLabel(video?: VideoEntry | null) {
  if (!video?.status) return "No video selected";
  if (video.status === "ready") return "Ready";
  if (video.status === "generating") return "Generating";
  if (video.status === "analyzing") return "Analyzing";
  if (video.status === "analyzed") return "Analyzed";
  if (video.status === "uploaded") return "Queued";
  if (video.status === "error") return "Error";
  return video.status;
}

export function videoStatusTone(status?: string) {
  if (status === "ready") return "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300";
  if (status === "error") return "border-destructive/30 bg-destructive/10 text-destructive";
  if (status === "generating" || status === "analyzing") {
    return "border-sky-500/30 bg-sky-500/10 text-sky-700 dark:text-sky-300";
  }
  return "border-border/70 bg-background/70 text-muted-foreground";
}
