"use client";

import { useEffect, useMemo, useState } from "react";

import { useAppStore } from "@/store/app-store";

export function useClips(videoId?: string | null) {
  const activeVideoId = useAppStore((state) => state.activeVideoId);
  const videos = useAppStore((state) => state.videos);
  const clipsByVideoId = useAppStore((state) => state.clipsByVideoId);
  const clipsLoadingByVideoId = useAppStore((state) => state.clipsLoadingByVideoId);

  const refreshVideos = useAppStore((state) => state.refreshVideos);
  const setActiveVideoId = useAppStore((state) => state.setActiveVideoId);
  const fetchClips = useAppStore((state) => state.fetchClips);

  const [isBootLoading, setIsBootLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const resolvedVideoId = videoId ?? activeVideoId;

  const selectedVideo = useMemo(
    () => (resolvedVideoId ? videos.find((entry) => entry.id === resolvedVideoId) ?? null : null),
    [resolvedVideoId, videos]
  );

  const clips = resolvedVideoId ? clipsByVideoId[resolvedVideoId] ?? [] : [];
  const isLoading = isBootLoading || (resolvedVideoId ? Boolean(clipsLoadingByVideoId[resolvedVideoId]) : false);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      setIsBootLoading(true);
      setError(null);

      try {
        const list = await refreshVideos();
        if (cancelled) return;

        const preferredVideoId =
          videoId && list.some((entry) => entry.id === videoId) ? videoId : list[0]?.id ?? null;

        if (!preferredVideoId) return;

        setActiveVideoId(preferredVideoId);
        await fetchClips(preferredVideoId, { force: true });
      } catch (err) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : "Unable to load clips.";
          setError(message);
        }
      } finally {
        if (!cancelled) setIsBootLoading(false);
      }
    }

    bootstrap();

    return () => {
      cancelled = true;
    };
  }, [fetchClips, refreshVideos, setActiveVideoId, videoId]);

  const selectVideo = async (nextVideoId: string) => {
    setError(null);
    setActiveVideoId(nextVideoId);

    try {
      await fetchClips(nextVideoId, { force: true });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to switch video.";
      setError(message);
    }
  };

  const refresh = async () => {
    const target = resolvedVideoId;
    if (!target) return;

    setError(null);
    try {
      await Promise.all([refreshVideos(), fetchClips(target, { force: true })]);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to refresh clips.";
      setError(message);
    }
  };

  return {
    videoId: resolvedVideoId,
    selectedVideo,
    videos,
    clips,
    isLoading,
    error,
    selectVideo,
    refresh,
  };
}
