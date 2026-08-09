import { useState } from "react";
import { motion } from "framer-motion";
import { Film, RefreshCcw, Search, SlidersHorizontal, Sparkles } from "lucide-react";

import { AddFilterCombobox } from "@/components/clips/AddFilterCombobox";
import { FilterToken } from "@/components/clips/FilterToken";
import {
  ClipSortOption,
  ClipsFilterState,
  FilterRule,
  SORT_OPTIONS,
  hasActiveFilterState,
} from "@/components/clips/filter-rules";
import { scorePercent, videoStatusLabel, videoStatusTone } from "@/components/clips/clip-ui-utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { cn } from "@/lib/cn";
import { VideoEntry } from "@/lib/types";

interface FiltersBarProps {
  videoId: string | null;
  selectedVideo: VideoEntry | null;
  videos: VideoEntry[];
  clipCount: number;
  averageScore?: number | null;
  bestScore?: number | null;
  filters: ClipsFilterState;
  availableStatuses: string[];
  availableTags: string[];
  onQueryChange: (value: string) => void;
  onSortChange: (value: ClipSortOption) => void;
  onAddRule: (type: FilterRule["type"]) => void;
  onRuleChange: (ruleId: string, nextRule: FilterRule) => void;
  onRemoveRule: (ruleId: string) => void;
  onClearAll: () => void;
  onVideoChange: (videoId: string) => void;
  onRefresh: () => void;
  isRefreshing: boolean;
}

export function FiltersBar({
  videoId,
  selectedVideo,
  videos,
  clipCount,
  averageScore,
  bestScore,
  filters,
  availableStatuses,
  availableTags,
  onQueryChange,
  onSortChange,
  onAddRule,
  onRuleChange,
  onRemoveRule,
  onClearAll,
  onVideoChange,
  onRefresh,
  isRefreshing,
}: FiltersBarProps) {
  const avgPercent = scorePercent(averageScore);
  const bestPercent = scorePercent(bestScore);
  const [openTokenId, setOpenTokenId] = useState<string | null>(null);
  const [isMobileFiltersOpen, setIsMobileFiltersOpen] = useState(false);
  const hasActiveFilters = hasActiveFilterState(filters);

  const renderTokenList = (className?: string) => (
    <div className={cn("flex items-center gap-2", className)}>
      {filters.rules.length > 0 ? (
        filters.rules.map((rule) => (
          <FilterToken
            key={rule.id}
            rule={rule}
            open={openTokenId === rule.id}
            availableStatuses={availableStatuses}
            availableTags={availableTags}
            onOpenChange={(open) => setOpenTokenId(open ? rule.id : null)}
            onChange={(nextRule) => onRuleChange(rule.id, nextRule)}
            onRemove={() => {
              if (openTokenId === rule.id) setOpenTokenId(null);
              onRemoveRule(rule.id);
            }}
          />
        ))
      ) : (
        <p className="text-xs text-muted-foreground">No active filter tokens.</p>
      )}
    </div>
  );

  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.32, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="rounded-[1.5rem] border border-border/65 bg-card/68 p-4 shadow-[0_16px_48px_-34px_rgba(15,23,42,0.42)] sm:p-5">
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

        <div className="mt-4 grid gap-3 xl:grid-cols-[minmax(220px,280px)_minmax(260px,1fr)_220px_auto] xl:items-end">
          <label className="space-y-1.5 text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Source video
            <select
              aria-label="Source video"
              value={videoId ?? ""}
              onChange={(event) => onVideoChange(event.target.value)}
              disabled={videos.length === 0}
              className="h-10 w-full rounded-xl border border-input bg-background/75 px-3 text-sm text-foreground outline-none transition focus-visible:ring-2 focus-visible:ring-ring"
            >
              {videos.length === 0 ? <option value="">No video</option> : null}
              {videos.map((video) => (
                <option key={video.id} value={video.id}>
                  {video.filename}
                </option>
              ))}
            </select>
          </label>

          <label className="space-y-1.5 text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Search
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                aria-label="Search clips"
                value={filters.query}
                onChange={(event) => onQueryChange(event.target.value)}
                placeholder="Search title, clip id..."
                className="h-10 w-full pl-9"
              />
            </div>
          </label>

          <label className="space-y-1.5 text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Sort
            <select
              aria-label="Sort clips"
              value={filters.sort}
              onChange={(event) => onSortChange(event.target.value as ClipSortOption)}
              className="h-10 w-full rounded-xl border border-input bg-background/75 px-3 text-sm text-foreground outline-none transition focus-visible:ring-2 focus-visible:ring-ring"
            >
              {SORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              className="h-10 rounded-xl px-4 lg:hidden"
              onClick={() => setIsMobileFiltersOpen(true)}
            >
              <SlidersHorizontal className="mr-2 h-4 w-4" />
              Filters
              {filters.rules.length > 0 ? (
                <span className="ml-2 inline-flex h-5 min-w-5 items-center justify-center rounded-full border border-primary/30 bg-primary/12 px-1.5 text-[10px] font-semibold text-primary">
                  {filters.rules.length}
                </span>
              ) : null}
            </Button>

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

        <div className="mt-3 hidden items-center gap-2 lg:flex">
          <AddFilterCombobox onAddFilter={onAddRule} />
          {hasActiveFilters ? (
            <Button
              type="button"
              variant="ghost"
              className="h-8 rounded-full px-3 text-[11px] uppercase tracking-[0.11em]"
              onClick={onClearAll}
            >
              Clear all
            </Button>
          ) : null}
        </div>

        <div className="mt-3 hidden lg:block">
          {renderTokenList("flex-wrap")}
        </div>

        <div className="mt-3 space-y-2 lg:hidden">
          <div className="flex items-center gap-2">
            {hasActiveFilters ? (
              <Button
                type="button"
                variant="ghost"
                className="h-8 rounded-full px-3 text-[11px] uppercase tracking-[0.11em]"
                onClick={onClearAll}
              >
                Clear all
              </Button>
            ) : (
              <p className="text-xs text-muted-foreground">Use Filters to add rules.</p>
            )}
          </div>
          <div className="overflow-x-auto pb-1 [scrollbar-width:thin]">
            {renderTokenList("w-max pr-2")}
          </div>
        </div>
      </div>

      <Sheet open={isMobileFiltersOpen} onOpenChange={setIsMobileFiltersOpen}>
        <SheetContent
          side="bottom"
          className="h-[82vh] rounded-t-[1.2rem] border-x-0 border-b-0 border-t border-border/70 bg-background/96 p-4"
        >
          <SheetHeader>
            <SheetTitle className="inline-flex items-center gap-2">
              <SlidersHorizontal className="h-4 w-4" />
              Filters
            </SheetTitle>
            <SheetDescription>Add rules and edit active filter tokens.</SheetDescription>
          </SheetHeader>

          <div className="mt-4 h-[calc(82vh-8rem)] space-y-3 overflow-y-auto pb-6">
            <label className="space-y-1.5 text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
              Search
              <Input
                aria-label="Search clips in drawer"
                value={filters.query}
                onChange={(event) => onQueryChange(event.target.value)}
                placeholder="Search title, clip id..."
                className="h-10"
              />
            </label>

            <AddFilterCombobox onAddFilter={onAddRule} className="w-full min-w-0" />

            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                Active filters
              </p>
              <div className="flex flex-wrap gap-2">
                {filters.rules.length > 0 ? (
                  filters.rules.map((rule) => (
                    <FilterToken
                      key={`mobile-${rule.id}`}
                      rule={rule}
                      open={openTokenId === rule.id}
                      availableStatuses={availableStatuses}
                      availableTags={availableTags}
                      onOpenChange={(open) => setOpenTokenId(open ? rule.id : null)}
                      onChange={(nextRule) => onRuleChange(rule.id, nextRule)}
                      onRemove={() => {
                        if (openTokenId === rule.id) setOpenTokenId(null);
                        onRemoveRule(rule.id);
                      }}
                    />
                  ))
                ) : (
                  <p className="text-xs text-muted-foreground">No active filter tokens.</p>
                )}
              </div>
            </div>

            {hasActiveFilters ? (
              <Button type="button" variant="outline" className="h-10 rounded-xl" onClick={onClearAll}>
                Clear all
              </Button>
            ) : null}
          </div>
        </SheetContent>
      </Sheet>
    </motion.section>
  );
}
