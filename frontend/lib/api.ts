import {
  API_BASE,
  ClipDetailResponse,
  CreateExportResponse,
  QueuedJobResponse,
  TikTokAccount,
  TikTokUploadResult,
  UploadVideoResponse,
  VideoEntry,
} from "@/lib/types";

export class ApiError extends Error {
  status: number;
  path: string;

  constructor(status: number, path: string, message?: string) {
    super(message ?? `API request failed (${status}): ${path}`);
    this.name = "ApiError";
    this.status = status;
    this.path = path;
  }
}

export function isApiErrorStatus(error: unknown, status: number) {
  return error instanceof ApiError && error.status === status;
}

async function readErrorMessage(response: Response) {
  try {
    const data = await response.json();
    if (typeof data?.detail === "string") {
      return data.detail;
    }
  } catch {
    return undefined;
  }
  return undefined;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    ...init,
  });

  if (!response.ok) {
    throw new ApiError(response.status, path, await readErrorMessage(response));
  }

  return (await response.json()) as T;
}

async function requestVoid(path: string, init?: RequestInit): Promise<void> {
  const response = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    ...init,
  });

  if (!response.ok) {
    throw new ApiError(response.status, path, await readErrorMessage(response));
  }
}

export function listVideos() {
  return requestJson<VideoEntry[]>("/api/videos");
}

// ---------------------------------------------------------------------------
// TikTok
// ---------------------------------------------------------------------------

export function listTikTokAccounts() {
  return requestJson<TikTokAccount[]>("/api/tiktok/accounts");
}

export function deleteTikTokAccount(accountId: string) {
  return requestVoid(`/api/tiktok/accounts/${accountId}`, { method: "DELETE" });
}

export function sendToTikTok(exportId: string, accountId: string) {
  return requestJson<TikTokUploadResult>("/api/tiktok/upload", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ export_id: exportId, account_id: accountId }),
  });
}

export function tiktokLoginUrl() {
  return `${API_BASE}/api/tiktok/login`;
}

export function getVideo(videoId: string) {
  return requestJson<VideoEntry>(`/api/videos/${videoId}`);
}

export function getClip(clipId: string) {
  return requestJson<ClipDetailResponse>(`/api/clips/${clipId}`);
}

export async function uploadVideo(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/api/videos`, {
    method: "POST",
    body: formData,
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(response.status, "/api/videos", await readErrorMessage(response));
  }

  return (await response.json()) as UploadVideoResponse;
}

export function analyzeVideo(videoId: string) {
  return requestJson<QueuedJobResponse>(`/api/videos/${videoId}/analyze`, { method: "POST" });
}

export function triggerGenerate(videoId: string) {
  return requestJson<QueuedJobResponse>(`/api/videos/${videoId}/generate`, { method: "POST" });
}

export function patchClipTitle(clipId: string, userTitle: string | null) {
  return requestJson<{ clip?: ClipDetailResponse["clip"] }>(`/api/clips/${clipId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_title: userTitle }),
  });
}

export function createClipExport(clipId: string, preset: string) {
  return requestJson<CreateExportResponse>(`/api/clips/${clipId}/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ preset }),
  });
}

export function deleteExport(exportId: string) {
  return requestVoid(`/api/exports/${exportId}`, { method: "DELETE" });
}

export function deleteClip(clipId: string) {
  return requestVoid(`/api/clips/${clipId}`, { method: "DELETE" });
}

export function deleteVideo(videoId: string) {
  return requestVoid(`/api/videos/${videoId}`, { method: "DELETE" });
}

export function clearVideoClips(videoId: string) {
  return requestVoid(`/api/videos/${videoId}/clips`, { method: "DELETE" });
}

export function clearVideoJobs(videoId: string) {
  return requestVoid(`/api/videos/${videoId}/jobs`, { method: "DELETE" });
}

export async function retryStuckJobs() {
  const data = await requestJson<{ jobs_reset: number }>("/api/jobs/retry-stuck", { method: "POST" });
  return data.jobs_reset;
}

export function resetSession() {
  return requestVoid("/api/reset", { method: "POST" });
}

export function downloadExportUrl(exportId: string) {
  return `${API_BASE}/api/exports/${exportId}/download`;
}
