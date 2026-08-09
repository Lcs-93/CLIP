import { useEffect, useRef } from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { Clock3, ExternalLink, Film, Maximize2, Minimize2, PenSquare, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { API_BASE, ClipEntry } from "@/lib/types";
import {
  clipDurationLabel,
  clipScoreChipClass,
  clipScoreLabel,
  clipTimeRangeLabel,
  clipTitle,
  scorePercent,
} from "@/components/clips/clip-ui-utils";

interface ClipInspectPanelProps {
  clip: ClipEntry | null;
  videoId: string | null;
  videoLabel?: string;
  compact?: boolean;
  onDeleteClip?: (clip: ClipEntry) => void;
  isExpanded?: boolean;
  onToggleExpanded?: () => void;
  shouldAutoplay?: boolean;
  autoplayToken?: number;
}

function editHref(clipId: string, videoId: string | null) {
  if (!videoId) return `/clips/${clipId}`;
  return `/clips/${clipId}?videoId=${videoId}`;
}

function exportHref(videoId: string | null, clipId: string) {
  const params = new URLSearchParams();
  if (videoId) params.set("videoId", videoId);
  params.set("clipId", clipId);
  const suffix = params.toString();
  return suffix.length > 0 ? `/exports?${suffix}` : "/exports";
}

export function ClipInspectPanel({
  clip,
  videoId,
  videoLabel,
  compact = false,
  onDeleteClip,
  isExpanded = true,
  onToggleExpanded,
  shouldAutoplay = false,
  autoplayToken = 0,
}: ClipInspectPanelProps) {
  const playerRef = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    if (!clip?.preview_url || !shouldAutoplay) return;

    const video = playerRef.current;
    if (!video) return;

    const startPlayback = () => {
      try {
        video.currentTime = 0;
        const playAttempt = video.play();
        if (playAttempt && typeof playAttempt.catch === "function") {
          playAttempt.catch(() => undefined);
        }
      } catch {
        return;
      }
    };

    if (video.readyState >= 2) {
      startPlayback();
      return;
    }

    const onLoadedData = () => {
      startPlayback();
    };

    video.addEventListener("loadeddata", onLoadedData, { once: true });
    return () => {
      video.removeEventListener("loadeddata", onLoadedData);
    };
  }, [autoplayToken, clip?.id, clip?.preview_url, shouldAutoplay]);

  return (
    <div
      className={cn(
        "rounded-[1.5rem] border border-border/65 bg-card/78 shadow-[0_22px_64px_-40px_rgba(15,23,42,0.52)] backdrop-blur-xl",
        compact ? "p-4" : "p-5",
        !compact && isExpanded && "p-6"
      )}
    >
      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={clip?.id ?? "no-selected-clip"}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
          className="space-y-4"
        >
          {!clip ? (
            <div className="rounded-xl border border-dashed border-border/80 bg-background/50 px-4 py-10 text-center">
              <div className="mx-auto inline-flex h-12 w-12 items-center justify-center rounded-full border border-border/80 bg-background/90 text-muted-foreground">
                <Film className="h-5 w-5" />
              </div>
              <p className="mt-3 text-sm font-medium text-foreground">Select a clip to inspect</p>
              <p className="mt-1 text-xs uppercase tracking-[0.12em] text-muted-foreground">
                Preview, metadata and export actions will appear here
              </p>
            </div>
          ) : (
            <>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                    {videoLabel ?? "Selected clip"}
                  </p>
                  <h2 className="mt-1 line-clamp-2 text-lg font-semibold tracking-[-0.015em] text-foreground">
                    {clipTitle(clip)}
                  </h2>
                </div>

                {!compact && onToggleExpanded ? (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-8 shrink-0 rounded-lg px-2.5 text-xs"
                    onClick={onToggleExpanded}
                  >
                    {isExpanded ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
                    <span className="ml-1.5">{isExpanded ? "Collapse" : "Expand"}</span>
                  </Button>
                ) : null}
              </div>

              <div className="overflow-hidden rounded-xl border border-border/70 bg-black/88 shadow-[0_20px_50px_-36px_rgba(15,23,42,0.68)]">
                {clip.preview_url ? (
                  <div className="aspect-video w-full bg-black">
                    <video
                      ref={playerRef}
                      className="h-full w-full object-contain"
                      src={`${API_BASE}${clip.preview_url}`}
                      controls
                      playsInline
                      preload="metadata"
                    />
                  </div>
                ) : (
                  <div className="flex aspect-video items-center justify-center text-xs uppercase tracking-[0.14em] text-slate-400">
                    Preview unavailable
                  </div>
                )}
              </div>

              <div className="flex flex-wrap gap-2">
                <span
                  className={cn(
                    "inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.11em]",
                    clipScoreChipClass(clip.score)
                  )}
                >
                  {clipScoreLabel(clip.score)}
                  <span className="ml-1.5 text-[10px]">
                    {scorePercent(clip.score) != null ? `${scorePercent(clip.score)}%` : "--"}
                  </span>
                </span>

                <span className="inline-flex items-center gap-1 rounded-full border border-border/70 bg-background/75 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.11em] text-foreground">
                  Duration {clipDurationLabel(clip)}
                </span>

                <span className="inline-flex items-center gap-1 rounded-full border border-border/70 bg-background/75 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.11em] text-foreground">
                  <Clock3 className="h-3.5 w-3.5 text-muted-foreground" />
                  {clipTimeRangeLabel(clip)}
                </span>
              </div>

              <Button asChild className="h-11 w-full rounded-xl text-sm font-semibold">
                <Link href={exportHref(videoId, clip.id)}>
                  Open / Export
                  <ExternalLink className="ml-2 h-4 w-4" />
                </Link>
              </Button>

              <div className="flex flex-wrap gap-2">
                <Button asChild variant="outline" className="h-10 flex-1 rounded-xl">
                  <Link href={editHref(clip.id, videoId)}>
                    <PenSquare className="mr-2 h-4 w-4" />
                    Edit
                  </Link>
                </Button>

                {onDeleteClip ? (
                  <Button
                    type="button"
                    variant="outline"
                    className="h-10 rounded-xl border-destructive/40 text-destructive hover:bg-destructive/10"
                    onClick={() => onDeleteClip(clip)}
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Delete
                  </Button>
                ) : null}
              </div>
            </>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
