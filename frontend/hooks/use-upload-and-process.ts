"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { VideoEntry } from "@/lib/types";
import { getStoredActiveVideoId, useAppStore } from "@/store/app-store";

const PROCESSING_STATUSES = new Set(["uploaded", "analyzing", "analyzed", "generating"]);

function shouldPoll(status?: string | null) {
  return status ? PROCESSING_STATUSES.has(status) : false;
}

function toEpoch(value?: string | null) {
  if (!value) return 0;
  const epoch = Date.parse(value);
  return Number.isFinite(epoch) ? epoch : 0;
}

function resolveResumableVideo(videos: VideoEntry[]) {
  const candidates = videos.filter((video) => shouldPoll(video.status));
  if (candidates.length === 0) return null;
  return [...candidates].sort((a, b) => toEpoch(b.created_at) - toEpoch(a.created_at))[0] ?? null;
}

export function useUploadAndProcess() {
  const activeVideoId = useAppStore((state) => state.activeVideoId);
  const videos = useAppStore((state) => state.videos);
  const uploadState = useAppStore((state) => state.uploadState);
  const processingState = useAppStore((state) => state.processingState);

  const refreshVideos = useAppStore((state) => state.refreshVideos);
  const setActiveVideoId = useAppStore((state) => state.setActiveVideoId);
  const startUpload = useAppStore((state) => state.startUpload);
  const pollVideoStatus = useAppStore((state) => state.pollVideoStatus);

  const [isPolling, setIsPolling] = useState(false);
  const [hasUserStartedUpload, setHasUserStartedUpload] = useState(false);

  const activeVideo = useMemo(
    () => (activeVideoId ? videos.find((video) => video.id === activeVideoId) ?? null : null),
    [activeVideoId, videos]
  );
  const resumableVideo = useMemo(() => resolveResumableVideo(videos), [videos]);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      const params = new URLSearchParams(window.location.search);
      const queryVideoId = params.get("videoId");
      const storedVideoId = getStoredActiveVideoId();
      const preferredVideoId = queryVideoId ?? storedVideoId ?? null;
      const nextVideos = await refreshVideos();
      if (cancelled) return;

      const resolvedVideoId =
        preferredVideoId && nextVideos.some((video) => video.id === preferredVideoId)
          ? preferredVideoId
          : nextVideos[0]?.id ?? null;

      if (!resolvedVideoId) return;
      setActiveVideoId(resolvedVideoId);
      setIsPolling(false);
    }

    bootstrap().catch(() => null);

    return () => {
      cancelled = true;
    };
  }, [refreshVideos, setActiveVideoId]);

  useEffect(() => {
    if (!isPolling || !activeVideoId || !hasUserStartedUpload) return;

    const tick = async () => {
      const video = await pollVideoStatus(activeVideoId, { silent: true });
      if (!video) {
        setIsPolling(false);
        return;
      }

      if (video.status === "ready" || video.status === "error") {
        setIsPolling(false);
      }
    };

    tick();
    const interval = window.setInterval(tick, 2500);
    return () => window.clearInterval(interval);
  }, [activeVideoId, hasUserStartedUpload, isPolling, pollVideoStatus]);

  useEffect(() => {
    if (processingState.hasError) {
      setIsPolling(false);
    }
  }, [processingState.hasError]);

  const handleUpload = useCallback(
    async (file: File) => {
      setHasUserStartedUpload(true);
      const videoId = await startUpload(file);
      setIsPolling(true);
      return videoId;
    },
    [startUpload]
  );

  const refresh = useCallback(async () => {
    if (!activeVideoId) return null;
    return pollVideoStatus(activeVideoId);
  }, [activeVideoId, pollVideoStatus]);

  const resumeLastProcessing = useCallback(async () => {
    const targetVideoId = resumableVideo?.id ?? activeVideoId;
    if (!targetVideoId) return null;

    setHasUserStartedUpload(true);
    setActiveVideoId(targetVideoId);
    const video = await pollVideoStatus(targetVideoId, { silent: true });
    setIsPolling(shouldPoll(video?.status));
    return video;
  }, [activeVideoId, pollVideoStatus, resumableVideo?.id, setActiveVideoId]);

  return {
    activeVideoId,
    activeVideo,
    resumableVideo,
    hasUserStartedUpload,
    uploadState,
    processingState,
    isPolling,
    handleUpload,
    resumeLastProcessing,
    refresh,
    setActiveVideoId,
  };
}
