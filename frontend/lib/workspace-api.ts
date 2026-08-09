import {
  analyzeVideo,
  ApiError,
  clearVideoClips,
  clearVideoJobs,
  createClipExport,
  deleteClip,
  deleteExport,
  deleteVideo,
  getClip,
  getVideo,
  isApiErrorStatus,
  listVideos,
  patchClipTitle,
  resetSession,
  retryStuckJobs,
  triggerGenerate,
  uploadVideo,
} from "@/lib/api";

export {
  analyzeVideo,
  ApiError,
  clearVideoClips,
  clearVideoJobs,
  deleteClip,
  deleteExport,
  deleteVideo,
  getClip,
  getVideo,
  isApiErrorStatus,
  listVideos,
  patchClipTitle,
  resetSession,
  retryStuckJobs,
  triggerGenerate,
  uploadVideo,
};

export async function apiJson<T>(path: string, init?: RequestInit) {
  const { API_BASE } = await import("@/lib/types");
  const response = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    ...init,
  });
  if (!response.ok) {
    throw new ApiError(response.status, path);
  }
  return (await response.json()) as T;
}

export function exportClip(clipId: string, preset: string) {
  return createClipExport(clipId, preset);
}
