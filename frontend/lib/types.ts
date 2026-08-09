export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type VideoStatus =
  | "uploaded"
  | "analyzing"
  | "analyzed"
  | "generating"
  | "ready"
  | "error"
  | string;

export type JobStatus = "queued" | "running" | "done" | "error" | "failed" | string;

export type ExportStatus = "queued" | "running" | "done" | "error" | "failed" | string;

export interface Job {
  id: string;
  video_id?: string;
  type: string;
  status: JobStatus;
  progress?: number | null;
  message?: string | null;
  payload?: string | null;
  created_at?: string;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface ExportEntry {
  id: string;
  clip_id?: string;
  mode: string;
  output_path?: string | null;
  status: ExportStatus;
  created_at?: string;
  output_url?: string | null;
}

export interface ClipEntry {
  id: string;
  video_id?: string;
  start_seconds: number;
  end_seconds: number;
  score?: number | null;
  tag?: string | null;
  reason?: string | null;
  signals?: string | null;
  tiktok_title?: string | null;
  user_title?: string | null;
  preview_path?: string | null;
  preview_url?: string | null;
  status?: string;
  created_at?: string;
  exports?: ExportEntry[];
}

export interface VideoEntry {
  id: string;
  filename: string;
  source_path?: string;
  created_at?: string;
  status: VideoStatus;
  duration_seconds?: number | null;
  transcript_path?: string | null;
  clips?: ClipEntry[];
  jobs?: Job[];
}

export interface ClipDetailResponse {
  clip: ClipEntry;
  video: VideoEntry;
}

export interface UploadVideoResponse {
  id: string;
  filename?: string;
  status?: string;
}

export interface QueuedJobResponse {
  job_id: string;
  status: string;
}

export interface CreateExportResponse extends QueuedJobResponse {
  export_id: string;
}

export interface ExportRecord {
  exportEntry: ExportEntry;
  clip: ClipEntry;
  video: VideoEntry;
}

export interface TikTokAccount {
  id: string;
  open_id: string;
  display_name?: string | null;
  avatar_url?: string | null;
  token_expires_at: string;
  refresh_expires_at: string;
  created_at: string;
}

export interface TikTokUploadResult {
  status: string;
  publish_id: string;
}
