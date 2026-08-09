"use client";

import { useEffect, useMemo, useState } from "react";

import { useAppStore } from "@/store/app-store";
import { userFacingError } from "@/lib/user-error";

export function useClip(clipId?: string) {
  const clipDetails = useAppStore((state) => state.clipDetails);
  const clipLoadingById = useAppStore((state) => state.clipLoadingById);

  const fetchClip = useAppStore((state) => state.fetchClip);
  const updateClipTitle = useAppStore((state) => state.updateClipTitle);
  const createExport = useAppStore((state) => state.createExport);
  const setActiveVideoId = useAppStore((state) => state.setActiveVideoId);

  const detail = clipId ? clipDetails[clipId] ?? null : null;
  const isLoading = clipId ? Boolean(clipLoadingById[clipId]) : false;

  const [error, setError] = useState<string | null>(null);
  const [isSavingTitle, setIsSavingTitle] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  useEffect(() => {
    if (!clipId) return;

    let cancelled = false;

    fetchClip(clipId, { force: true })
      .then((nextDetail) => {
        if (!cancelled && nextDetail?.video?.id) {
          setActiveVideoId(nextDetail.video.id);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          const message = userFacingError(err, "Unable to load clip.");
          setError(message);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [clipId, fetchClip, setActiveVideoId]);

  const refresh = async () => {
    if (!clipId) return null;
    setError(null);

    try {
      const next = await fetchClip(clipId, { force: true });
      if (next?.video?.id) setActiveVideoId(next.video.id);
      return next;
    } catch (err) {
      const message = userFacingError(err, "Unable to refresh clip.");
      setError(message);
      return null;
    }
  };

  const saveTitle = async (title: string) => {
    if (!clipId) return;
    setIsSavingTitle(true);
    setError(null);

    try {
      await updateClipTitle(clipId, title);
    } catch (err) {
      const message = userFacingError(err, "Unable to save title.");
      setError(message);
      throw err;
    } finally {
      setIsSavingTitle(false);
    }
  };

  const startExport = async (preset: string, title?: string) => {
    if (!clipId) return null;
    setIsExporting(true);
    setError(null);

    try {
      if (typeof title === "string") {
        await updateClipTitle(clipId, title);
      }
      const response = await createExport(clipId, preset);
      return response;
    } catch (err) {
      const message = userFacingError(err, "Unable to create export.");
      setError(message);
      throw err;
    } finally {
      setIsExporting(false);
    }
  };

  const clip = detail?.clip ?? null;
  const video = detail?.video ?? null;

  const exportsList = useMemo(() => clip?.exports ?? [], [clip?.exports]);

  return {
    detail,
    clip,
    video,
    exportsList,
    isLoading,
    isSavingTitle,
    isExporting,
    error,
    refresh,
    saveTitle,
    startExport,
  };
}
