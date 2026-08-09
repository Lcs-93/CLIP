import { create } from "zustand";

import {
  analyzeVideo,
  createClipExport,
  getClip,
  getVideo,
  listVideos,
  patchClipTitle,
  triggerGenerate,
  uploadVideo,
} from "@/lib/api";
import {
  ClipDetailResponse,
  ClipEntry,
  CreateExportResponse,
  ExportEntry,
  ExportRecord,
  VideoEntry,
} from "@/lib/types";

export type UploadStatus = "idle" | "uploading" | "done" | "error";

export type ProcessingStep = "idle" | "uploaded" | "analyzing" | "generating" | "ready" | "error";

export interface UploadState {
  status: UploadStatus;
  error: string | null;
  filename: string | null;
  videoId: string | null;
}

export interface ProcessingState {
  step: ProcessingStep;
  message: string;
  progress: number;
  isDone: boolean;
  hasError: boolean;
}

interface AppStore {
  activeVideoId: string | null;
  videos: VideoEntry[];
  videosLoading: boolean;

  uploadState: UploadState;
  processingState: ProcessingState;

  clipsByVideoId: Record<string, ClipEntry[]>;
  clipsLoadingByVideoId: Record<string, boolean>;

  clipDetails: Record<string, ClipDetailResponse>;
  clipLoadingById: Record<string, boolean>;

  exports: ExportRecord[];
  exportsLoading: boolean;

  lastVideoPollAt: number | null;
  lastExportsRefreshAt: number | null;

  setActiveVideoId: (videoId: string | null) => void;

  refreshVideos: () => Promise<VideoEntry[]>;
  startUpload: (file: File) => Promise<string>;
  pollVideoStatus: (videoId?: string, options?: { silent?: boolean }) => Promise<VideoEntry | null>;

  fetchClips: (videoId: string, options?: { force?: boolean; silent?: boolean }) => Promise<ClipEntry[]>;
  fetchClip: (clipId: string, options?: { force?: boolean }) => Promise<ClipDetailResponse | null>;
  updateClipTitle: (clipId: string, title: string) => Promise<void>;

  createExport: (clipId: string, preset: string) => Promise<CreateExportResponse>;
  refreshExports: (videoId?: string, options?: { silent?: boolean }) => Promise<ExportRecord[]>;
  pollExportStatus: (videoId?: string) => Promise<boolean>;
}

const GENERATE_TRIGGER_LOCK = new Set<string>();

const DEFAULT_UPLOAD_STATE: UploadState = {
  status: "idle",
  error: null,
  filename: null,
  videoId: null,
};

const DEFAULT_PROCESSING_STATE: ProcessingState = {
  step: "idle",
  message: "Upload a video to start processing.",
  progress: 0,
  isDone: false,
  hasError: false,
};

function persistActiveVideoId(videoId: string | null) {
  if (typeof window === "undefined") return;
  if (!videoId) {
    window.localStorage.removeItem("activeVideoId");
    return;
  }
  window.localStorage.setItem("activeVideoId", videoId);
}

function extractPercent(message?: string | null) {
  if (!message) return null;
  const match = message.match(/(\d+)\s*%/);
  if (!match) return null;
  const value = Number(match[1]);
  return Number.isFinite(value) ? value : null;
}

function normalizeProgress(value?: number | null) {
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  if (value <= 1) return Math.round(Math.max(0, Math.min(1, value)) * 100);
  return Math.round(Math.max(0, Math.min(100, value)));
}

function hasGenerateJob(video: VideoEntry) {
  return (video.jobs ?? []).some((job) => job.type === "generate");
}

function processingFromVideo(video?: VideoEntry | null): ProcessingState {
  if (!video) return DEFAULT_PROCESSING_STATE;

  const activeJob =
    (video.jobs ?? []).find((job) => job.status === "running") ??
    (video.jobs ?? []).find((job) => job.status === "queued") ??
    (video.jobs ?? [])[0];

  const rawProgress = normalizeProgress(activeJob?.progress) ?? extractPercent(activeJob?.message);
  const jobMessage = activeJob?.message?.trim();

  if (video.status === "uploaded") {
    return {
      step: "uploaded",
      message: "Video uploaded. Analysis is queued.",
      progress: 10,
      isDone: false,
      hasError: false,
    };
  }

  if (video.status === "analyzing") {
    return {
      step: "analyzing",
      message: jobMessage || "Analyzing video content...",
      progress: rawProgress == null ? 38 : Math.min(70, Math.max(18, Math.round(rawProgress * 0.55 + 18))),
      isDone: false,
      hasError: false,
    };
  }

  if (video.status === "analyzed") {
    return {
      step: "analyzing",
      message: "Analysis complete. Clip generation is starting.",
      progress: 72,
      isDone: false,
      hasError: false,
    };
  }

  if (video.status === "generating") {
    return {
      step: "generating",
      message: jobMessage || "Generating clips...",
      progress: rawProgress == null ? 86 : Math.min(98, Math.max(72, Math.round(rawProgress * 0.26 + 72))),
      isDone: false,
      hasError: false,
    };
  }

  if (video.status === "ready") {
    return {
      step: "ready",
      message: "Processing complete. Clips are ready.",
      progress: 100,
      isDone: true,
      hasError: false,
    };
  }

  if (video.status === "error") {
    return {
      step: "error",
      message: jobMessage || "Processing failed.",
      progress: 100,
      isDone: false,
      hasError: true,
    };
  }

  return {
    step: "uploaded",
    message: jobMessage || "Processing...",
    progress: rawProgress ?? 16,
    isDone: false,
    hasError: false,
  };
}

function upsertVideo(videos: VideoEntry[], incoming: VideoEntry) {
  const index = videos.findIndex((video) => video.id === incoming.id);
  if (index === -1) return [incoming, ...videos];

  const next = [...videos];
  next[index] = {
    ...next[index],
    ...incoming,
  };
  return next;
}

function upsertClip(clips: ClipEntry[], clip: ClipEntry) {
  const index = clips.findIndex((entry) => entry.id === clip.id);
  if (index === -1) return [clip, ...clips];

  const next = [...clips];
  next[index] = {
    ...next[index],
    ...clip,
  };
  return next;
}

function toEpoch(value?: string | null) {
  if (!value) return 0;
  const epoch = Date.parse(value);
  return Number.isFinite(epoch) ? epoch : 0;
}

function flattenExports(videos: VideoEntry[], clipsByVideoId: Record<string, ClipEntry[]>) {
  const rows: ExportRecord[] = [];

  videos.forEach((video) => {
    const clips = video.clips ?? clipsByVideoId[video.id] ?? [];
    clips.forEach((clip) => {
      (clip.exports ?? []).forEach((exportEntry: ExportEntry) => {
        rows.push({
          exportEntry,
          clip,
          video,
        });
      });
    });
  });

  rows.sort((a, b) => toEpoch(b.exportEntry.created_at) - toEpoch(a.exportEntry.created_at));
  return rows;
}

function isExportPending(entry: ExportEntry) {
  if (entry.output_url) return false;
  return !["done", "error", "failed"].includes(entry.status);
}

async function triggerGenerateIfNeeded(video: VideoEntry) {
  if (video.status !== "analyzed") {
    GENERATE_TRIGGER_LOCK.delete(video.id);
    return;
  }

  if (hasGenerateJob(video)) {
    GENERATE_TRIGGER_LOCK.delete(video.id);
    return;
  }

  if (GENERATE_TRIGGER_LOCK.has(video.id)) return;

  GENERATE_TRIGGER_LOCK.add(video.id);
  try {
    await triggerGenerate(video.id);
  } catch {
    // Best effort: next poll will retry if still required.
  } finally {
    GENERATE_TRIGGER_LOCK.delete(video.id);
  }
}

export const useAppStore = create<AppStore>((set, get) => ({
  activeVideoId: null,
  videos: [],
  videosLoading: false,

  uploadState: DEFAULT_UPLOAD_STATE,
  processingState: DEFAULT_PROCESSING_STATE,

  clipsByVideoId: {},
  clipsLoadingByVideoId: {},

  clipDetails: {},
  clipLoadingById: {},

  exports: [],
  exportsLoading: false,

  lastVideoPollAt: null,
  lastExportsRefreshAt: null,

  setActiveVideoId: (videoId) => {
    persistActiveVideoId(videoId);
    set((state) => {
      const activeVideo = videoId ? state.videos.find((video) => video.id === videoId) : null;
      return {
        activeVideoId: videoId,
        processingState: activeVideo ? processingFromVideo(activeVideo) : state.processingState,
      };
    });
  },

  refreshVideos: async () => {
    set({ videosLoading: true });
    try {
      const videos = await listVideos();

      set((state) => {
        const nextActive =
          state.activeVideoId && videos.some((video) => video.id === state.activeVideoId)
            ? state.activeVideoId
            : videos[0]?.id ?? null;

        const activeVideo = nextActive ? videos.find((video) => video.id === nextActive) ?? null : null;
        persistActiveVideoId(nextActive);

        return {
          videos,
          activeVideoId: nextActive,
          processingState: activeVideo ? processingFromVideo(activeVideo) : state.processingState,
        };
      });

      return videos;
    } finally {
      set({ videosLoading: false });
    }
  },

  startUpload: async (file) => {
    set({
      uploadState: {
        status: "uploading",
        error: null,
        filename: file.name,
        videoId: null,
      },
      processingState: {
        step: "uploaded",
        message: "Uploading video...",
        progress: 4,
        isDone: false,
        hasError: false,
      },
    });

    try {
      const uploaded = await uploadVideo(file);
      await analyzeVideo(uploaded.id);

      set((state) => ({
        activeVideoId: uploaded.id,
        uploadState: {
          status: "done",
          error: null,
          filename: uploaded.filename ?? file.name,
          videoId: uploaded.id,
        },
        processingState: {
          step: "uploaded",
          message: "Video uploaded. Analysis started.",
          progress: 12,
          isDone: false,
          hasError: false,
        },
        videos: state.videos,
      }));
      persistActiveVideoId(uploaded.id);

      await get().pollVideoStatus(uploaded.id);
      return uploaded.id;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Upload failed.";
      set({
        uploadState: {
          status: "error",
          error: message,
          filename: file.name,
          videoId: null,
        },
        processingState: {
          step: "error",
          message,
          progress: 100,
          isDone: false,
          hasError: true,
        },
      });
      throw error;
    }
  },

  pollVideoStatus: async (videoId, _options) => {
    const targetVideoId = videoId ?? get().activeVideoId;
    if (!targetVideoId) return null;

    try {
      const video = await getVideo(targetVideoId);
      await triggerGenerateIfNeeded(video);

      set((state) => {
        const nextVideos = upsertVideo(state.videos, video);
        const nextClips = {
          ...state.clipsByVideoId,
          [video.id]: video.clips ?? state.clipsByVideoId[video.id] ?? [],
        };

        const shouldUpdateProcessing = state.activeVideoId === video.id || targetVideoId === video.id;
        const nextUploadState =
          state.uploadState.videoId === video.id && video.status === "error"
            ? {
                ...state.uploadState,
                status: "error" as const,
                error: "Processing failed.",
              }
            : state.uploadState;

        return {
          videos: nextVideos,
          clipsByVideoId: nextClips,
          processingState: shouldUpdateProcessing ? processingFromVideo(video) : state.processingState,
          uploadState: nextUploadState,
          lastVideoPollAt: Date.now(),
        };
      });

      return video;
    } catch {
      await get().refreshVideos();
      return null;
    }
  },

  fetchClips: async (videoId, options) => {
    const cached = get().clipsByVideoId[videoId];
    if (cached && !options?.force) return cached;

    set((state) => ({
      clipsLoadingByVideoId: {
        ...state.clipsLoadingByVideoId,
        [videoId]: true,
      },
    }));

    try {
      const video = await getVideo(videoId);
      await triggerGenerateIfNeeded(video);

      const clips = video.clips ?? [];
      set((state) => ({
        videos: upsertVideo(state.videos, video),
        clipsByVideoId: {
          ...state.clipsByVideoId,
          [videoId]: clips,
        },
        processingState:
          state.activeVideoId === video.id ? processingFromVideo(video) : state.processingState,
      }));

      return clips;
    } finally {
      set((state) => ({
        clipsLoadingByVideoId: {
          ...state.clipsLoadingByVideoId,
          [videoId]: false,
        },
      }));
    }
  },

  fetchClip: async (clipId, options) => {
    const cached = get().clipDetails[clipId];
    if (cached && !options?.force) return cached;

    set((state) => ({
      clipLoadingById: {
        ...state.clipLoadingById,
        [clipId]: true,
      },
    }));

    try {
      const detail = await getClip(clipId);

      set((state) => {
        const currentClips = state.clipsByVideoId[detail.video.id] ?? [];
        const nextVideos = upsertVideo(state.videos, detail.video);

        return {
          videos: nextVideos,
          clipDetails: {
            ...state.clipDetails,
            [clipId]: detail,
          },
          clipsByVideoId: {
            ...state.clipsByVideoId,
            [detail.video.id]: upsertClip(currentClips, detail.clip),
          },
        };
      });

      return detail;
    } finally {
      set((state) => ({
        clipLoadingById: {
          ...state.clipLoadingById,
          [clipId]: false,
        },
      }));
    }
  },

  updateClipTitle: async (clipId, title) => {
    const normalized = title.trim();
    await patchClipTitle(clipId, normalized.length > 0 ? normalized : null);
    await get().fetchClip(clipId, { force: true });
  },

  createExport: async (clipId, preset) => {
    const response = await createClipExport(clipId, preset);
    await get().fetchClip(clipId, { force: true });
    await get().refreshExports(undefined, { silent: true });
    return response;
  },

  refreshExports: async (videoId, options) => {
    if (!options?.silent) set({ exportsLoading: true });

    try {
      let sourceVideos: VideoEntry[] = [];

      if (videoId) {
        sourceVideos = [await getVideo(videoId)];
      } else {
        const videos = await listVideos();
        sourceVideos = await Promise.all(
          videos.map(async (video) => {
            try {
              return await getVideo(video.id);
            } catch {
              return video;
            }
          })
        );
      }

      const state = get();
      const videosMap = new Map<string, VideoEntry>(state.videos.map((video) => [video.id, video]));
      sourceVideos.forEach((video) => {
        videosMap.set(video.id, {
          ...videosMap.get(video.id),
          ...video,
        });
      });

      let nextVideos = Array.from(videosMap.values());
      if (!videoId) {
        const rank = new Map(sourceVideos.map((video, index) => [video.id, index]));
        nextVideos = nextVideos.sort((a, b) => {
          const aRank = rank.get(a.id) ?? Number.MAX_SAFE_INTEGER;
          const bRank = rank.get(b.id) ?? Number.MAX_SAFE_INTEGER;
          return aRank - bRank;
        });
      }

      const nextClipsByVideoId = {
        ...state.clipsByVideoId,
      };
      sourceVideos.forEach((video) => {
        if (video.clips) nextClipsByVideoId[video.id] = video.clips;
      });

      const exportsRows = flattenExports(nextVideos, nextClipsByVideoId);

      set({
        videos: nextVideos,
        clipsByVideoId: nextClipsByVideoId,
        exports: exportsRows,
        lastExportsRefreshAt: Date.now(),
      });

      return exportsRows;
    } finally {
      if (!options?.silent) set({ exportsLoading: false });
    }
  },

  pollExportStatus: async (videoId) => {
    const rows = await get().refreshExports(videoId, { silent: true });
    return rows.some((row) => {
      if (videoId && row.video.id !== videoId) return false;
      return isExportPending(row.exportEntry);
    });
  },
}));

export function getStoredActiveVideoId() {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("activeVideoId");
}
