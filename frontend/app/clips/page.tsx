"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, Eye, Loader2, Trash2 } from "lucide-react";

import { ClipGrid } from "@/components/clips/ClipGrid";
import { ClipInspectPanel } from "@/components/clips/ClipInspectPanel";
import { ClipInspectSkeleton, ClipGridSkeleton } from "@/components/clips/ClipsSkeletons";
import { EmptyState } from "@/components/clips/EmptyState";
import { FiltersBar } from "@/components/clips/FiltersBar";
import {
  ClipSortOption,
  ClipsFilterState,
  DEFAULT_CLIPS_FILTER_STATE,
  FilterRule,
  coerceSortOption,
  createFilterRule,
  deserializeRules,
  matchesRule,
  serializeRules,
} from "@/components/clips/filter-rules";
import { clipDateEpoch, clipTitle } from "@/components/clips/clip-ui-utils";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { useToast } from "@/components/ui/toast";
import { useClips } from "@/hooks/use-clips";
import { createClipExport, deleteClip } from "@/lib/api";
import { cn } from "@/lib/cn";
import { DEFAULT_EXPORT_PRESET_ID, EXPORT_PRESETS } from "@/lib/export-presets";
import { userFacingError } from "@/lib/user-error";
import { ClipEntry } from "@/lib/types";

const NEWEST_RATIO = 0.35;
const QUERY_DEBOUNCE_MS = 240;

function scoreValue(score?: number | null) {
  if (typeof score !== "number" || !Number.isFinite(score)) return 0;
  return score;
}

function clipDurationSeconds(clip: ClipEntry) {
  return Math.max(0, clip.end_seconds - clip.start_seconds);
}

function matchesSearch(clip: ClipEntry, search: string) {
  const query = search.trim().toLowerCase();
  if (!query) return true;

  const title = clipTitle(clip).toLowerCase();
  return (
    title.includes(query) ||
    clip.id.toLowerCase().includes(query) ||
    (clip.reason ?? "").toLowerCase().includes(query) ||
    (clip.tag ?? "").toLowerCase().includes(query)
  );
}

function sortClips(clips: ClipEntry[], sort: ClipSortOption) {
  const list = [...clips];

  if (sort === "timeline-asc") {
    return list.sort((a, b) => {
      const timelineDiff = a.start_seconds - b.start_seconds;
      if (timelineDiff !== 0) return timelineDiff;
      return scoreValue(b.score) - scoreValue(a.score);
    });
  }

  if (sort === "duration-asc") {
    return list.sort((a, b) => clipDurationSeconds(a) - clipDurationSeconds(b));
  }

  if (sort === "duration-desc") {
    return list.sort((a, b) => clipDurationSeconds(b) - clipDurationSeconds(a));
  }

  if (sort === "date-desc") {
    return list.sort((a, b) => {
      const dateDiff = clipDateEpoch(b) - clipDateEpoch(a);
      if (dateDiff !== 0) return dateDiff;
      return scoreValue(b.score) - scoreValue(a.score);
    });
  }

  return list.sort((a, b) => {
    const scoreDiff = scoreValue(b.score) - scoreValue(a.score);
    if (scoreDiff !== 0) return scoreDiff;
    return a.start_seconds - b.start_seconds;
  });
}

function parseFiltersFromUrl(params: URLSearchParams): ClipsFilterState {
  const query = params.get("q") ?? "";
  const sort = coerceSortOption(params.get("sort"));
  const rules = deserializeRules(params.get("rules"));

  return {
    query,
    rules,
    sort,
  };
}

function emptyFilterState(): ClipsFilterState {
  return {
    query: DEFAULT_CLIPS_FILTER_STATE.query,
    rules: [],
    sort: DEFAULT_CLIPS_FILTER_STATE.sort,
  };
}

export default function ClipsPage() {
  const router = useRouter();
  const { showToast } = useToast();
  const [queryVideoId, setQueryVideoId] = useState<string | null>(null);
  const [selectedClipId, setSelectedClipId] = useState<string | null>(null);
  const [selectedClipIds, setSelectedClipIds] = useState<string[]>([]);
  const [bulkPreset, setBulkPreset] = useState<string>(DEFAULT_EXPORT_PRESET_ID);
  const [isBulkExporting, setIsBulkExporting] = useState(false);
  const [deletingClipIds, setDeletingClipIds] = useState<Record<string, boolean>>({});
  const [pendingDeleteClipIds, setPendingDeleteClipIds] = useState<string[] | null>(null);
  const [filters, setFilters] = useState<ClipsFilterState>(emptyFilterState);
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [isFiltersHydrated, setIsFiltersHydrated] = useState(false);

  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [isMobileInspectOpen, setIsMobileInspectOpen] = useState(false);
  const [isInspectCollapsed, setIsInspectCollapsed] = useState(false);
  const [autoplayClipId, setAutoplayClipId] = useState<string | null>(null);
  const [autoplayToken, setAutoplayToken] = useState(0);

  const { videoId, selectedVideo, videos, clips, isLoading, error, selectVideo, refresh } = useClips(queryVideoId);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setQueryVideoId(params.get("videoId"));
    setFilters(parseFiltersFromUrl(params));
    setIsFiltersHydrated(true);
  }, []);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setDebouncedQuery(filters.query);
    }, QUERY_DEBOUNCE_MS);

    return () => window.clearTimeout(timeoutId);
  }, [filters.query]);

  useEffect(() => {
    if (!isFiltersHydrated) return;

    const params = new URLSearchParams(window.location.search);
    if (queryVideoId) params.set("videoId", queryVideoId);
    else params.delete("videoId");

    const query = filters.query.trim();
    if (query) params.set("q", query);
    else params.delete("q");

    if (filters.sort !== DEFAULT_CLIPS_FILTER_STATE.sort) {
      params.set("sort", filters.sort);
    } else {
      params.delete("sort");
    }

    const serializedRules = serializeRules(filters.rules);
    if (serializedRules) params.set("rules", serializedRules);
    else params.delete("rules");

    const nextQuery = params.toString();
    const nextHref = nextQuery ? `/clips?${nextQuery}` : "/clips";
    router.replace(nextHref, { scroll: false });
  }, [filters.query, filters.rules, filters.sort, isFiltersHydrated, queryVideoId, router]);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(max-width: 1023px)");
    const update = () => setIsMobile(mediaQuery.matches);

    update();
    mediaQuery.addEventListener("change", update);

    return () => {
      mediaQuery.removeEventListener("change", update);
    };
  }, []);

  const scoreStats = useMemo(() => {
    if (clips.length === 0) return null;

    const scored = clips
      .map((clip) => clip.score)
      .filter((score): score is number => typeof score === "number" && Number.isFinite(score));

    if (scored.length === 0) {
      return {
        average: null,
        best: null,
      };
    }

    return {
      average: scored.reduce((sum, score) => sum + score, 0) / scored.length,
      best: Math.max(...scored),
    };
  }, [clips]);

  const newestIds = useMemo(() => {
    const byDate = [...clips].sort((a, b) => clipDateEpoch(b) - clipDateEpoch(a));
    const keep = Math.max(1, Math.ceil(byDate.length * NEWEST_RATIO));
    return new Set(byDate.slice(0, keep).map((clip) => clip.id));
  }, [clips]);

  const availableStatuses = useMemo(() => {
    const values = new Set<string>();
    clips.forEach((clip) => {
      const normalized = (clip.status ?? "").trim().toLowerCase();
      if (normalized) values.add(normalized);
    });
    return Array.from(values).sort((a, b) => a.localeCompare(b));
  }, [clips]);

  const availableTags = useMemo(() => {
    const values = new Set<string>();
    clips.forEach((clip) => {
      const tag = (clip.tag ?? "").trim();
      if (tag) values.add(tag);
    });
    return Array.from(values).sort((a, b) => a.localeCompare(b));
  }, [clips]);

  const filteredClips = useMemo(() => {
    const filtered = clips.filter((clip) => {
      if (!matchesSearch(clip, debouncedQuery)) return false;
      return filters.rules.every((rule) => matchesRule(clip, rule, { newestIds }));
    });

    return sortClips(filtered, filters.sort);
  }, [clips, debouncedQuery, filters.rules, filters.sort, newestIds]);

  const selectedClip = useMemo(() => {
    if (filteredClips.length === 0) return null;
    if (!selectedClipId) return filteredClips[0];
    return filteredClips.find((clip) => clip.id === selectedClipId) ?? filteredClips[0];
  }, [filteredClips, selectedClipId]);

  const filteredClipIds = useMemo(() => filteredClips.map((clip) => clip.id), [filteredClips]);
  const allFilteredSelected =
    filteredClipIds.length > 0 && filteredClipIds.every((id) => selectedClipIds.includes(id));
  const selectedCount = selectedClipIds.length;

  useEffect(() => {
    if (selectedClip) {
      setSelectedClipId(selectedClip.id);
      return;
    }
    setSelectedClipId(null);
  }, [selectedClip]);

  useEffect(() => {
    setSelectedClipIds((current) => current.filter((id) => filteredClipIds.includes(id)));
  }, [filteredClipIds]);

  const onSelectVideo = async (nextVideoId: string) => {
    setIsRefreshing(true);
    setSelectedClipId(null);
    setSelectedClipIds([]);
    setAutoplayClipId(null);
    setIsInspectCollapsed(false);

    await selectVideo(nextVideoId);
    setQueryVideoId(nextVideoId);

    window.setTimeout(() => setIsRefreshing(false), 180);
  };

  const onRefresh = async () => {
    setIsRefreshing(true);
    await refresh();
    window.setTimeout(() => setIsRefreshing(false), 220);
  };

  const onSelectClip = (clip: ClipEntry) => {
    setSelectedClipId(clip.id);
    setAutoplayClipId(null);
    setIsInspectCollapsed(false);
    if (isMobile) {
      setIsMobileInspectOpen(true);
    }
  };

  const onPlayClip = (clip: ClipEntry) => {
    setSelectedClipId(clip.id);
    setAutoplayClipId(clip.id);
    setAutoplayToken((current) => current + 1);
    setIsInspectCollapsed(false);
    if (isMobile) {
      setIsMobileInspectOpen(true);
      return;
    }

    const panel = document.getElementById("clip-inspect-panel");
    panel?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const onToggleSelectClip = (clip: ClipEntry) => {
    setSelectedClipIds((current) =>
      current.includes(clip.id) ? current.filter((id) => id !== clip.id) : [...current, clip.id]
    );
  };

  const onSelectAllFiltered = () => {
    setSelectedClipIds(filteredClipIds);
  };

  const onClearSelection = () => {
    setSelectedClipIds([]);
  };

  const onRequestDeleteClip = (clip: ClipEntry) => {
    setPendingDeleteClipIds([clip.id]);
  };

  const onRequestDeleteSelected = () => {
    if (selectedClipIds.length === 0) return;
    setPendingDeleteClipIds([...selectedClipIds]);
  };

  const onConfirmDeleteClips = async () => {
    if (!pendingDeleteClipIds || pendingDeleteClipIds.length === 0) return;
    const targetIds = [...pendingDeleteClipIds];

    setDeletingClipIds((state) => {
      const next = { ...state };
      targetIds.forEach((id) => {
        next[id] = true;
      });
      return next;
    });

    try {
      const results = await Promise.allSettled(targetIds.map((id) => deleteClip(id)));
      const deletedIds: string[] = [];
      let failedCount = 0;

      results.forEach((result, index) => {
        if (result.status === "fulfilled") deletedIds.push(targetIds[index]);
        else failedCount += 1;
      });

      if (deletedIds.length > 0) {
        await refresh();
        setSelectedClipIds((current) => current.filter((id) => !deletedIds.includes(id)));
        if (selectedClipId && deletedIds.includes(selectedClipId)) {
          setSelectedClipId(null);
        }
        showToast({
          variant: "success",
          title: deletedIds.length === 1 ? "Clip deleted" : `${deletedIds.length} clips deleted`,
          description: "Selected clips were removed.",
        });
      }

      if (failedCount > 0) {
        showToast({
          variant: "error",
          title: "Partial delete failure",
          description:
            failedCount === 1
              ? "1 clip could not be deleted."
              : `${failedCount} clips could not be deleted.`,
        });
      }

      setPendingDeleteClipIds(null);
    } catch (err) {
      showToast({
        variant: "error",
        title: "Delete failed",
        description: userFacingError(err, "Unable to delete clips."),
      });
    } finally {
      setDeletingClipIds((state) => {
        const next = { ...state };
        targetIds.forEach((id) => {
          delete next[id];
        });
        return next;
      });
    }
  };

  const onBulkExport = async () => {
    if (selectedClipIds.length === 0) return;
    setIsBulkExporting(true);

    try {
      const results = await Promise.allSettled(
        selectedClipIds.map((clipId) => createClipExport(clipId, bulkPreset))
      );
      const successCount = results.filter((result) => result.status === "fulfilled").length;
      const failedCount = results.length - successCount;

      if (successCount > 0) {
        showToast({
          variant: "success",
          title:
            successCount === 1
              ? "1 export queued"
              : `${successCount} exports queued`,
          description: "You can track progress in the Exports workspace.",
        });
      }

      if (failedCount > 0) {
        showToast({
          variant: "error",
          title: "Partial export failure",
          description:
            failedCount === 1
              ? "1 clip could not be queued."
              : `${failedCount} clips could not be queued.`,
        });
      }
    } catch (err) {
      showToast({
        variant: "error",
        title: "Export failed",
        description: userFacingError(err, "Unable to queue exports."),
      });
    } finally {
      setIsBulkExporting(false);
    }
  };

  const onAddRule = (type: FilterRule["type"]) => {
    setFilters((current) => ({
      ...current,
      rules: [...current.rules, createFilterRule(type)],
    }));
  };

  const onRuleChange = (ruleId: string, nextRule: FilterRule) => {
    setFilters((current) => ({
      ...current,
      rules: current.rules.map((rule) => (rule.id === ruleId ? { ...nextRule, id: ruleId } : rule)),
    }));
  };

  const onRuleRemove = (ruleId: string) => {
    setFilters((current) => ({
      ...current,
      rules: current.rules.filter((rule) => rule.id !== ruleId),
    }));
  };

  const resetFilters = () => {
    setFilters(emptyFilterState());
  };

  const isInspectExpanded = Boolean(selectedClip) && !isInspectCollapsed;
  const shouldAutoplaySelectedClip = Boolean(selectedClip && autoplayClipId === selectedClip.id);

  const showSkeletons = isLoading && (clips.length === 0 || isRefreshing);
  const hasVideos = videos.length > 0;
  const hasAnyClips = clips.length > 0;

  return (
    <main className="app-page">
      <div className="app-page-inner pb-24 lg:pb-16">
        <div className="w-full space-y-4">
          <FiltersBar
            videoId={videoId}
            selectedVideo={selectedVideo}
            videos={videos}
            clipCount={filteredClips.length}
            averageScore={scoreStats?.average}
            bestScore={scoreStats?.best}
            filters={filters}
            availableStatuses={availableStatuses}
            availableTags={availableTags}
            onQueryChange={(query) => setFilters((current) => ({ ...current, query }))}
            onSortChange={(sort) => setFilters((current) => ({ ...current, sort }))}
            onAddRule={onAddRule}
            onRuleChange={onRuleChange}
            onRemoveRule={onRuleRemove}
            onClearAll={resetFilters}
            onVideoChange={onSelectVideo}
            onRefresh={onRefresh}
            isRefreshing={isRefreshing}
          />

          {error ? (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-2xl border border-destructive/35 bg-destructive/10 px-4 py-3 text-sm text-destructive"
            >
              <p className="inline-flex items-center gap-2">
                <AlertTriangle className="h-4 w-4" />
                {error}
              </p>
            </motion.div>
          ) : null}

          {filteredClips.length > 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-xl border border-border/70 bg-card/74 px-4 py-3 shadow-[0_12px_34px_-26px_rgba(15,23,42,0.52)] backdrop-blur-xl"
            >
              <div className="flex flex-wrap items-center gap-2.5">
                <Button
                  type="button"
                  variant="outline"
                  className="h-9 rounded-full px-3 text-xs font-semibold uppercase tracking-[0.11em]"
                  onClick={allFilteredSelected ? onClearSelection : onSelectAllFiltered}
                >
                  {allFilteredSelected ? "Clear selection" : "Select all filtered"}
                </Button>

                {selectedCount > 0 ? (
                  <span className="inline-flex items-center rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.11em] text-primary">
                    {selectedCount} selected
                  </span>
                ) : (
                  <span className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
                    Select clips to export or delete in bulk
                  </span>
                )}

                <label className="ml-auto inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                  Preset
                  <select
                    value={bulkPreset}
                    onChange={(event) => setBulkPreset(event.target.value)}
                    className="h-9 min-w-[140px] rounded-lg border border-input bg-background/75 px-2.5 text-xs text-foreground outline-none transition focus-visible:ring-2 focus-visible:ring-ring"
                    disabled={selectedCount === 0 || isBulkExporting}
                  >
                    {EXPORT_PRESETS.map((preset) => (
                      <option key={preset.id} value={preset.id}>
                        {preset.label}
                      </option>
                    ))}
                  </select>
                </label>

                <Button
                  type="button"
                  className="h-9 rounded-full px-3 text-xs font-semibold uppercase tracking-[0.11em]"
                  onClick={onBulkExport}
                  disabled={selectedCount === 0 || isBulkExporting}
                >
                  {isBulkExporting ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : null}
                  Export selected
                </Button>

                <Button
                  type="button"
                  variant="destructive"
                  className="h-9 rounded-full px-3 text-xs font-semibold uppercase tracking-[0.11em]"
                  onClick={onRequestDeleteSelected}
                  disabled={selectedCount === 0}
                >
                  <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                  Delete selected
                </Button>
              </div>
            </motion.div>
          ) : null}

          <div
            className={cn(
              "grid gap-5",
              isInspectExpanded
                ? "lg:[grid-template-columns:minmax(0,1fr)_clamp(460px,36vw,520px)]"
                : "lg:grid-cols-[minmax(0,1fr)_420px]"
            )}
          >
            <section className="min-h-[320px]">
              {showSkeletons ? (
                <ClipGridSkeleton count={6} />
              ) : !hasVideos ? (
                <EmptyState mode="no-videos" />
              ) : filteredClips.length === 0 ? (
                hasAnyClips ? (
                  <EmptyState mode="no-results" onResetFilters={resetFilters} />
                ) : (
                  <EmptyState mode="no-clips" isProcessing={selectedVideo?.status !== "ready" && selectedVideo?.status !== "error"} />
                )
              ) : (
                <div className={isRefreshing ? "processing-refresh-pulse" : undefined}>
                  <ClipGrid
                    clips={filteredClips}
                    selectedClipId={selectedClip?.id ?? null}
                    selectedClipIds={selectedClipIds}
                    videoId={videoId}
                    onSelectClip={onSelectClip}
                    onPlayClip={onPlayClip}
                    onToggleSelectClip={onToggleSelectClip}
                  />
                </div>
              )}
            </section>

            <aside id="clip-inspect-panel" className="hidden lg:block">
              <div className="sticky top-[calc(var(--app-header-offset)+1rem)]">
                <AnimatePresence mode="wait" initial={false}>
                  {showSkeletons ? (
                    <motion.div
                      key="inspect-skeleton"
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -6 }}
                    >
                      <ClipInspectSkeleton />
                    </motion.div>
                  ) : (
                    <motion.div
                      key={selectedClip?.id ?? "inspect-empty"}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -6 }}
                    >
                      <ClipInspectPanel
                        clip={selectedClip}
                        videoId={videoId}
                        videoLabel={selectedVideo?.filename}
                        onDeleteClip={onRequestDeleteClip}
                        isExpanded={isInspectExpanded}
                        onToggleExpanded={() => setIsInspectCollapsed((current) => !current)}
                        shouldAutoplay={shouldAutoplaySelectedClip}
                        autoplayToken={autoplayToken}
                      />
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </aside>
          </div>
        </div>
      </div>

      {selectedClip ? (
        <div className="fixed inset-x-4 bottom-4 z-40 lg:hidden">
          <Button
            type="button"
            onClick={() => setIsMobileInspectOpen(true)}
            className="h-12 w-full rounded-2xl border border-border/70 bg-card/92 text-foreground shadow-[0_20px_50px_-34px_rgba(15,23,42,0.62)] backdrop-blur-xl"
            variant="outline"
          >
            <Eye className="mr-2 h-4 w-4" />
            Preview selected clip
          </Button>
        </div>
      ) : null}

      <Sheet open={isMobileInspectOpen} onOpenChange={setIsMobileInspectOpen}>
        <SheetContent
          side="bottom"
          className="h-[86vh] rounded-t-[1.3rem] border-x-0 border-b-0 border-t border-border/70 bg-background/96 p-4"
        >
          <SheetHeader className="mb-3">
            <SheetTitle>Clip preview</SheetTitle>
            <SheetDescription>
              {selectedClip ? clipTitle(selectedClip) : "Select a clip from the grid"}
            </SheetDescription>
          </SheetHeader>

          {showSkeletons ? (
            <div className="pt-2">
              <ClipInspectSkeleton />
            </div>
          ) : (
            <div className="h-[calc(86vh-6.8rem)] overflow-y-auto pb-6">
              <ClipInspectPanel
                clip={selectedClip}
                videoId={videoId}
                videoLabel={selectedVideo?.filename}
                compact
                onDeleteClip={onRequestDeleteClip}
                shouldAutoplay={shouldAutoplaySelectedClip}
                autoplayToken={autoplayToken}
              />
            </div>
          )}
        </SheetContent>
      </Sheet>

      {isLoading && !showSkeletons ? (
        <div className="pointer-events-none fixed bottom-5 right-5 z-50 inline-flex items-center gap-2 rounded-full border border-border/70 bg-card/85 px-3 py-1.5 text-xs font-medium text-muted-foreground shadow-lg backdrop-blur-xl">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Syncing clips
        </div>
      ) : null}

      <ConfirmDialog
        open={Boolean(pendingDeleteClipIds && pendingDeleteClipIds.length > 0)}
        onOpenChange={(open) => {
          if (!open) {
            const isConfirming = Boolean(
              pendingDeleteClipIds?.some((id) => Boolean(deletingClipIds[id]))
            );
            if (isConfirming) return;
            setPendingDeleteClipIds(null);
          }
        }}
        title={
          pendingDeleteClipIds && pendingDeleteClipIds.length > 1
            ? `Delete ${pendingDeleteClipIds.length} clips?`
            : "Delete this clip?"
        }
        description="This action is permanent."
        confirmLabel="Delete"
        cancelLabel="Cancel"
        confirmVariant="destructive"
        isConfirming={Boolean(
          pendingDeleteClipIds?.some((id) => Boolean(deletingClipIds[id]))
        )}
        onConfirm={onConfirmDeleteClips}
      >
        {pendingDeleteClipIds ? (
          <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
            {pendingDeleteClipIds.length} clip{pendingDeleteClipIds.length > 1 ? "s" : ""} selected for deletion
          </p>
        ) : null}
      </ConfirmDialog>
    </main>
  );
}
