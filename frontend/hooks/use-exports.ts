"use client";

import { useEffect, useMemo, useState } from "react";

import { useAppStore } from "@/store/app-store";
import { userFacingError } from "@/lib/user-error";

function isPendingStatus(status: string, outputUrl?: string | null) {
  if (outputUrl) return false;
  return !["done", "error", "failed"].includes(status);
}

export function useExports(videoId?: string | null, _focusId?: string | null) {
  const allExports = useAppStore((state) => state.exports);
  const exportsLoading = useAppStore((state) => state.exportsLoading);
  const lastExportsRefreshAt = useAppStore((state) => state.lastExportsRefreshAt);

  const refreshExports = useAppStore((state) => state.refreshExports);
  const pollExportStatus = useAppStore((state) => state.pollExportStatus);

  const [error, setError] = useState<string | null>(null);

  const exports = useMemo(() => {
    if (!videoId) return allExports;
    return allExports.filter((entry) => entry.video.id === videoId);
  }, [allExports, videoId]);

  const hasPending = useMemo(
    () => exports.some((entry) => isPendingStatus(entry.exportEntry.status, entry.exportEntry.output_url)),
    [exports]
  );

  useEffect(() => {
    let cancelled = false;

    refreshExports(videoId ?? undefined)
      .then(() => {
        if (!cancelled) setError(null);
      })
      .catch((err) => {
        if (!cancelled) {
          const message = userFacingError(err, "Unable to load exports.");
          setError(message);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [refreshExports, videoId]);

  useEffect(() => {
    if (!hasPending) return;

    const interval = window.setInterval(() => {
      pollExportStatus(videoId ?? undefined).catch((err) => {
        const message = userFacingError(err, "Unable to refresh exports.");
        setError(message);
      });
    }, 3000);

    return () => window.clearInterval(interval);
  }, [hasPending, pollExportStatus, videoId]);

  const refresh = async () => {
    setError(null);
    try {
      await refreshExports(videoId ?? undefined);
    } catch (err) {
      const message = userFacingError(err, "Unable to refresh exports.");
      setError(message);
    }
  };

  return {
    exports,
    isLoading: exportsLoading,
    hasPending,
    error,
    lastUpdatedAt: lastExportsRefreshAt,
    refresh,
  };
}
