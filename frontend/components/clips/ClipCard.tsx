import Link from "next/link";
import { motion } from "framer-motion";
import { Check, ExternalLink, MoreHorizontal, PenSquare, Play } from "lucide-react";

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

interface ClipCardProps {
  clip: ClipEntry;
  index: number;
  selected: boolean;
  bulkSelected: boolean;
  editHref: string;
  openHref: string;
  onSelect: (clip: ClipEntry) => void;
  onPlay: (clip: ClipEntry) => void;
  onToggleBulkSelect: (clip: ClipEntry) => void;
}

function IconAction({
  label,
  children,
  onClick,
}: {
  label: string;
  children: React.ReactNode;
  onClick?: (event: React.MouseEvent<HTMLButtonElement>) => void;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-white/35 bg-black/45 text-white backdrop-blur-sm transition hover:bg-black/62 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-300"
    >
      {children}
    </button>
  );
}

function CardMoreMenu({ editHref, openHref }: { editHref: string; openHref: string }) {
  return (
    <details className="relative">
      <summary className="inline-flex h-9 w-9 cursor-pointer list-none items-center justify-center rounded-full border border-white/35 bg-black/45 text-white backdrop-blur-sm transition hover:bg-black/62 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-300 [&::-webkit-details-marker]:hidden">
        <MoreHorizontal className="h-4 w-4" />
      </summary>
      <div
        role="menu"
        className="absolute right-0 top-11 z-30 w-44 rounded-xl border border-border/70 bg-card/95 p-1 shadow-lg backdrop-blur-xl"
      >
        <Link
          role="menuitem"
          href={editHref}
          className="flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium uppercase tracking-[0.08em] text-foreground transition hover:bg-muted/70"
        >
          <PenSquare className="h-3.5 w-3.5" />
          Edit
        </Link>
        <Link
          role="menuitem"
          href={openHref}
          className="mt-1 flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium uppercase tracking-[0.08em] text-foreground transition hover:bg-muted/70"
        >
          <ExternalLink className="h-3.5 w-3.5" />
          Open export
        </Link>
      </div>
    </details>
  );
}

export function ClipCard({
  clip,
  index,
  selected,
  bulkSelected,
  editHref,
  openHref,
  onSelect,
  onPlay,
  onToggleBulkSelect,
}: ClipCardProps) {
  const percent = scorePercent(clip.score);

  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 16, scale: 0.985 }}
      whileInView={{ opacity: 1, y: 0, scale: 1 }}
      viewport={{ amount: 0.22, once: true }}
      transition={{ duration: 0.32, delay: Math.min(index * 0.03, 0.18), ease: [0.16, 1, 0.3, 1] }}
      className={cn(
        "group overflow-visible rounded-[1.45rem] border bg-card/78 shadow-[0_22px_64px_-46px_rgba(15,23,42,0.52)] backdrop-blur-xl transition",
        selected
          ? "border-primary/55 ring-2 ring-primary/20"
          : bulkSelected
            ? "border-sky-400/55 ring-2 ring-sky-400/15"
            : "border-border/65 hover:border-border"
      )}
    >
      <div className="relative overflow-hidden rounded-t-[1.35rem]">
        <button
          type="button"
          onClick={() => onSelect(clip)}
          className="relative block aspect-video w-full text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          aria-label={`Select ${clipTitle(clip)}`}
        >
          {clip.preview_url ? (
            <video
              className="h-full w-full object-cover"
              src={`${API_BASE}${clip.preview_url}`}
              preload="metadata"
              muted
              playsInline
              aria-hidden="true"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center bg-black/60 text-xs uppercase tracking-[0.14em] text-slate-300">
              Preview unavailable
            </div>
          )}

          <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/65 via-black/10 to-transparent" />

          <div className="absolute left-3 top-3 flex items-center gap-1.5">
            <span className={cn("rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em]", clipScoreChipClass(clip.score))}>
              {clipScoreLabel(clip.score)}
            </span>
            <span className="rounded-full border border-white/35 bg-black/45 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-white">
              {percent != null ? `${percent}%` : "--"}
            </span>
          </div>

          <span className="absolute bottom-3 right-3 rounded-full border border-white/28 bg-black/50 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-white">
            {clipDurationLabel(clip)}
          </span>
        </button>

        <div className="pointer-events-none absolute inset-0 flex items-center justify-center gap-2 opacity-0 transition duration-200 group-hover:pointer-events-auto group-hover:opacity-100 group-focus-within:pointer-events-auto group-focus-within:opacity-100">
          <IconAction label="Play clip" onClick={(event) => {
            event.stopPropagation();
            onPlay(clip);
          }}>
            <Play className="h-4 w-4" />
          </IconAction>

          <Link
            href={editHref}
            aria-label="Edit clip"
            className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-white/35 bg-black/45 text-white backdrop-blur-sm transition hover:bg-black/62 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-300"
            onClick={(event) => event.stopPropagation()}
          >
            <PenSquare className="h-4 w-4" />
          </Link>

          <Link
            href={openHref}
            aria-label="Open exports"
            className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-white/35 bg-black/45 text-white backdrop-blur-sm transition hover:bg-black/62 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-300"
            onClick={(event) => event.stopPropagation()}
          >
            <ExternalLink className="h-4 w-4" />
          </Link>

          <div onClick={(event) => event.stopPropagation()}>
            <CardMoreMenu editHref={editHref} openHref={openHref} />
          </div>
        </div>
      </div>

      <div className="space-y-2 p-4">
        <div className="flex items-start justify-between gap-3">
          <button
            type="button"
            onClick={() => onSelect(clip)}
            className="line-clamp-2 flex-1 text-left text-base font-semibold tracking-[-0.012em] text-foreground transition hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {clipTitle(clip)}
          </button>

          <button
            type="button"
            aria-pressed={bulkSelected}
            aria-label={`${bulkSelected ? "Unselect" : "Select"} clip ${clip.id} for bulk actions`}
            onClick={(event) => {
              event.stopPropagation();
              onToggleBulkSelect(clip);
            }}
            className={cn(
              "inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              bulkSelected
                ? "border-sky-300/75 bg-gradient-to-r from-sky-500/18 to-cyan-400/16 text-sky-200 shadow-[0_12px_26px_-18px_rgba(56,189,248,0.95)]"
                : "border-border/70 bg-background/70 text-muted-foreground hover:border-sky-300/45 hover:text-sky-100"
            )}
          >
            <span
              className={cn(
                "inline-flex h-4 w-4 items-center justify-center rounded-full border transition",
                bulkSelected
                  ? "border-sky-300/85 bg-sky-300/90 text-slate-950"
                  : "border-border/80 bg-transparent text-transparent"
              )}
            >
              <Check className="h-3 w-3" />
            </span>
            <span>{bulkSelected ? "Selected" : "Select"}</span>
          </button>
        </div>

        <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">{clipTimeRangeLabel(clip)}</p>
      </div>
    </motion.article>
  );
}
