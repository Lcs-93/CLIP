import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Film, RefreshCcw, Search, SlidersHorizontal, Sparkles } from "lucide-react";

import { ActiveFiltersRow } from "@/components/clips/ActiveFiltersRow";
import { FiltersPopover } from "@/components/clips/FiltersPopover";
import { QuickFilters } from "@/components/clips/QuickFilters";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { cn } from "@/lib/cn";
import { VideoEntry } from "@/lib/types";
import { scorePercent, videoStatusLabel, videoStatusTone } from "@/components/clips/clip-ui-utils";
import { ClipFilterChip, ClipSortOption } from "@/components/clips/clips-toolbar-types";

interface ClipsToolbarProps {
  videoId: string | null;
  selectedVideo: VideoEntry | null;
  videos: VideoEntry[];
  clipCount: number;
  averageScore?: number | null;
  bestScore?: number | null;
  search: string;
  onSearchChange: (value: string) => void;
  activeChip: ClipFilterChip;
  onChipChange: (value: ClipFilterChip) => void;
  minScore: number;
  onMinScoreChange: (value: number) => void;
  sort: ClipSortOption;
  onSortChange: (value: ClipSortOption) => void;
  onVideoChange: (videoId: string) => void;
  onRefresh: () => void;
  isRefreshing: boolean;
  onResetFilters: () => void;
}

export function ClipsToolbar({
  videoId,
  selectedVideo,
  videos,
  clipCount,
  averageScore,
  bestScore,
  search,
  onSearchChange,
  activeChip,
  onChipChange,
  minScore,
  onMinScoreChange,
  sort,
  onSortChange,
  onVideoChange,
  onRefresh,
  isRefreshing,
  onResetFilters,
}: ClipsToolbarProps) {
  const avgPercent = scorePercent(averageScore);
  const bestPercent = scorePercent(bestScore);

  const [isMobile, setIsMobile] = useState(false);
  const [isAdvancedOpen, setIsAdvancedOpen] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(max-width: 1023px)");
    const update = () => setIsMobile(mediaQuery.matches);

    update();
    mediaQuery.addEventListener("change", update);

    return () => {
      mediaQuery.removeEventListener("change", update);
    };
  }, []);

  useEffect(() => {
    if (isMobile) return;

    const onEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsAdvancedOpen(false);
      }
    };

    window.addEventListener("keydown", onEscape);
    return () => window.removeEventListener("keydown", onEscape);
  }, [isMobile]);

  const advancedCount = useMemo(() => {
    let count = 0;
    if (activeChip === "medium" || activeChip === "long") count += 1;
    if (minScore > 0) count += 1;
    if (sort !== "score-desc") count += 1;
    return count;
  }, [activeChip, minScore, sort]);

  const labelClassName =
    "text-xs font-semibold uppercase tracking-[0.14em] leading-none whitespace-nowrap text-muted-foreground/90";

  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.32, ease: [0.16, 1, 0.3, 1] }}
      className="sticky top-[var(--app-header-offset)] z-30"
    >
      <div className="rounded-[1.5rem] border border-border/65 bg-card/68 p-4 shadow-[0_16px_48px_-34px_rgba(15,23,42,0.42)] backdrop-blur-xl sm:p-5">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">Clips</p>
            <h1 className="mt-1 text-[clamp(1.65rem,3.8vw,2.55rem)] font-semibold leading-[0.95] tracking-[-0.03em] text-foreground">
              Clip workspace
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {selectedVideo?.filename ?? "Select a source video to inspect generated clips."}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 font-medium", videoStatusTone(selectedVideo?.status))}>
              <Film className="h-3.5 w-3.5" />
              {videoStatusLabel(selectedVideo)}
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-background/65 px-3 py-1.5 font-medium text-muted-foreground">
              {clipCount} clips
            </span>
            {avgPercent != null && bestPercent != null ? (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-background/65 px-3 py-1.5 font-medium text-muted-foreground">
                <Sparkles className="h-3.5 w-3.5" />
                Avg {avgPercent}% | Best {bestPercent}%
              </span>
            ) : null}
          </div>
        </div>

        <div className="mt-4 flex flex-col gap-3 xl:flex-row xl:flex-wrap xl:items-end 2xl:flex-nowrap">
          <div className="grid min-w-0 gap-3 md:grid-cols-[220px_minmax(0,1fr)] lg:grid-cols-[240px_minmax(0,1fr)] xl:min-w-[520px] xl:flex-1">
            <label className={cn("space-y-1.5", labelClassName)}>
              Source video
              <select
                aria-label="Source video"
                value={videoId ?? ""}
                onChange={(event) => onVideoChange(event.target.value)}
                disabled={videos.length === 0}
                className="h-10 w-full min-w-[220px] rounded-xl border border-input bg-background/75 px-3 text-sm text-foreground outline-none transition focus-visible:ring-2 focus-visible:ring-ring lg:min-w-[240px]"
              >
                {videos.length === 0 ? <option value="">No video</option> : null}
                {videos.map((video) => (
                  <option key={video.id} value={video.id}>
                    {video.filename}
                  </option>
                ))}
              </select>
            </label>

            <label className={cn("min-w-0 space-y-1.5", labelClassName)}>
              Search
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  aria-label="Search clips"
                  value={search}
                  onChange={(event) => onSearchChange(event.target.value)}
                  placeholder="Search title, clip id..."
                  className="h-10 min-w-[260px] w-full pl-9"
                />
              </div>
            </label>
          </div>

          <div className="min-w-0 xl:w-[360px] xl:flex-none">
            <p className={cn("mb-1", labelClassName)}>Quick filters</p>
            <QuickFilters activeChip={activeChip} onChipChange={onChipChange} />
          </div>

          <div className="grid min-w-0 gap-2 sm:grid-cols-2 lg:grid-cols-[minmax(150px,180px)_minmax(170px,200px)_auto_auto] lg:items-end xl:flex-none">
            <label className={cn("space-y-1.5", labelClassName)}>
              Min score {minScore}%
              <Slider
                aria-label="Minimum score"
                min={0}
                max={100}
                step={1}
                value={minScore}
                onValueChange={onMinScoreChange}
                className="h-10"
              />
            </label>

            <label className={cn("space-y-1.5", labelClassName)}>
              Sort
              <select
                aria-label="Sort clips"
                value={sort}
                onChange={(event) => onSortChange(event.target.value as ClipSortOption)}
                className="h-10 w-full rounded-xl border border-input bg-background/75 px-3 text-sm text-foreground outline-none transition focus-visible:ring-2 focus-visible:ring-ring"
              >
                <option value="score-desc">Score (high first)</option>
                <option value="duration-asc">Duration (short first)</option>
                <option value="duration-desc">Duration (long first)</option>
                <option value="date-desc">Date (newest first)</option>
              </select>
            </label>

            <div className="relative lg:self-end">
              <Button
                type="button"
                variant="outline"
                className="h-10 rounded-xl px-4"
                onClick={() => setIsAdvancedOpen((value) => !value)}
                aria-haspopup="dialog"
                aria-expanded={isAdvancedOpen}
              >
                <SlidersHorizontal className="mr-2 h-4 w-4" />
                Filters
                {advancedCount > 0 ? (
                  <span className="ml-2 inline-flex h-5 min-w-5 items-center justify-center rounded-full border border-primary/30 bg-primary/12 px-1.5 text-[10px] font-semibold text-primary">
                    {advancedCount}
                  </span>
                ) : null}
              </Button>

              <FiltersPopover
                open={isAdvancedOpen}
                isMobile={isMobile}
                activeChip={activeChip}
                minScore={minScore}
                sort={sort}
                onOpenChange={setIsAdvancedOpen}
                onChipChange={onChipChange}
                onMinScoreChange={onMinScoreChange}
                onSortChange={onSortChange}
                onReset={onResetFilters}
              />
            </div>

            <Button
              variant="outline"
              className="h-10 rounded-xl px-4"
              onClick={onRefresh}
              disabled={isRefreshing}
            >
              <RefreshCcw className={cn("mr-2 h-4 w-4", isRefreshing && "animate-spin")} />
              Refresh
            </Button>
          </div>
        </div>

        <div className="mt-3">
          <ActiveFiltersRow
            search={search}
            activeChip={activeChip}
            minScore={minScore}
            sort={sort}
            onSearchChange={onSearchChange}
            onChipChange={onChipChange}
            onMinScoreChange={onMinScoreChange}
            onSortChange={onSortChange}
            onReset={onResetFilters}
          />
        </div>
      </div>
    </motion.section>
  );
}
