import { ClipEntry, VideoEntry } from "@/lib/workspace-types";

export function extractPercent(message?: string | null) {
  if (!message) return null;
  const match = message.match(/(\d+)\s*%/);
  if (!match) return null;
  const value = Number(match[1]);
  return Number.isFinite(value) ? value : null;
}

export function statusLabel(video?: VideoEntry | null) {
  if (!video) return "No video selected";
  if (video.status === "analyzing") return "Analysis in progress";
  if (video.status === "generating") return "Generating clips";
  if (video.status === "uploaded") return "Queued";
  if (video.status === "analyzed") return "Analysis completed";
  if (video.status === "ready") return "Clips ready";
  if (video.status === "error") return "Error";
  return video.status;
}

export function statusVariant(status: string) {
  if (status === "ready") return "success" as const;
  if (status === "error") return "danger" as const;
  if (status === "analyzing" || status === "generating") return "default" as const;
  return "secondary" as const;
}

export function formatTimestamp(rawSeconds: number) {
  if (!Number.isFinite(rawSeconds)) return "--:--";
  const seconds = Math.max(0, Math.floor(rawSeconds));
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remaining = seconds % 60;
  const pad = (value: number) => value.toString().padStart(2, "0");
  if (hours > 0) return `${hours}:${pad(minutes)}:${pad(remaining)}`;
  return `${pad(minutes)}:${pad(remaining)}`;
}

export function parseSignals(signals?: string | null) {
  if (!signals) return [] as string[];
  try {
    const parsed = JSON.parse(signals);
    if (Array.isArray(parsed)) return parsed as string[];
    if (parsed?.signals && Array.isArray(parsed.signals)) return parsed.signals as string[];
  } catch (error) {
    return [] as string[];
  }
  return [] as string[];
}

export function clipStats(clips: ClipEntry[] = []) {
  if (clips.length === 0) return null;
  const scores = clips.map((clip) => clip.score ?? 0);
  return {
    count: clips.length,
    bestScore: Math.max(...scores),
    avgScore: scores.reduce((acc, score) => acc + score, 0) / scores.length,
  };
}

export function normalizeText(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}
