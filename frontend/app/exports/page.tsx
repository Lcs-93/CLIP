"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, Download, ExternalLink, Eye, Loader2, RefreshCcw, Search, Trash2 } from "lucide-react";

import { ExportInspectPanel } from "@/components/exports/ExportInspectPanel";
import { ExportInspectSkeleton, ExportsListSkeleton } from "@/components/exports/ExportsSkeletons";
import { clipTitle, exportStatus, exportStatusTone, formatDate, rowSearchText } from "@/components/exports/export-ui-utils";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Input } from "@/components/ui/input";
import { SelectToggle } from "@/components/ui/select-toggle";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/cn";
import { deleteExport, downloadExportUrl } from "@/lib/api";
import { userFacingError } from "@/lib/user-error";
import { ExportRecord } from "@/lib/types";
import { useExports } from "@/hooks/use-exports";

type ExportFilter = "all" | "ready" | "running" | "error";
type ExportSort = "newest" | "oldest" | "video" | "preset";

const FILTER_ITEMS: Array<{ id: ExportFilter; label: string }> = [
  { id: "all", label: "All" },
  { id: "ready", label: "Ready" },
  { id: "running", label: "Running" },
  { id: "error", label: "Error" },
];

function sortRows(rows: ExportRecord[], sort: ExportSort) {
  const next = [...rows];

  if (sort === "oldest") {
    return next.sort((a, b) => Date.parse(a.exportEntry.created_at ?? "") - Date.parse(b.exportEntry.created_at ?? ""));
  }

  if (sort === "video") {
    return next.sort((a, b) => a.video.filename.localeCompare(b.video.filename));
  }

  if (sort === "preset") {
    return next.sort((a, b) => a.exportEntry.mode.localeCompare(b.exportEntry.mode));
  }

  return next.sort((a, b) => Date.parse(b.exportEntry.created_at ?? "") - Date.parse(a.exportEntry.created_at ?? ""));
}

function matchesFilter(row: ExportRecord, filter: ExportFilter) {
  if (filter === "all") return true;
  const status = exportStatus(row.exportEntry.status, row.exportEntry.output_url).toLowerCase();
  return status === filter;
}

function clipHref(row: ExportRecord) {
  return `/clips/${row.clip.id}?videoId=${row.video.id}`;
}

export default function ExportsPage() {
  const { showToast } = useToast();

  const [focusId, setFocusId] = useState<string | null>(null);
  const [videoId, setVideoId] = useState<string | null>(null);

  const { exports, isLoading, hasPending, error, lastUpdatedAt, refresh } = useExports(videoId, focusId);

  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<ExportFilter>("all");
  const [sort, setSort] = useState<ExportSort>("newest");
  const [deleting, setDeleting] = useState<Record<string, boolean>>({});
  const [selectedExportId, setSelectedExportId] = useState<string | null>(null);
  const [selectedExportIds, setSelectedExportIds] = useState<string[]>([]);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [isInspectOpen, setIsInspectOpen] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [focusApplied, setFocusApplied] = useState(false);
  const [pendingDeleteIds, setPendingDeleteIds] = useState<string[] | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setFocusId(params.get("focus"));
    setVideoId(params.get("videoId"));
  }, []);

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
    setFocusApplied(false);
  }, [focusId]);

  const stats = useMemo(() => {
    let ready = 0;
    let running = 0;
    let failed = 0;

    exports.forEach((row) => {
      const status = exportStatus(row.exportEntry.status, row.exportEntry.output_url);
      if (status === "READY") ready += 1;
      else if (status === "RUNNING") running += 1;
      else failed += 1;
    });

    return {
      total: exports.length,
      ready,
      running,
      failed,
    };
  }, [exports]);

  const filteredRows = useMemo(() => {
    const query = search.trim().toLowerCase();

    const filtered = exports.filter((row) => {
      if (!matchesFilter(row, filter)) return false;
      if (!query) return true;
      return rowSearchText(row).includes(query);
    });

    return sortRows(filtered, sort);
  }, [exports, filter, search, sort]);

  const filteredRowIds = useMemo(() => filteredRows.map((row) => row.exportEntry.id), [filteredRows]);
  const selectedCount = selectedExportIds.length;
  const allFilteredSelected =
    filteredRowIds.length > 0 && filteredRowIds.every((id) => selectedExportIds.includes(id));

  const selectedRow = useMemo(() => {
    if (filteredRows.length === 0) return null;
    if (!selectedExportId) return filteredRows[0];
    return filteredRows.find((row) => row.exportEntry.id === selectedExportId) ?? filteredRows[0];
  }, [filteredRows, selectedExportId]);

  useEffect(() => {
    if (!selectedRow) {
      if (selectedExportId !== null) setSelectedExportId(null);
      return;
    }

    if (selectedRow.exportEntry.id !== selectedExportId) {
      setSelectedExportId(selectedRow.exportEntry.id);
    }
  }, [selectedExportId, selectedRow]);

  useEffect(() => {
    setSelectedExportIds((current) => current.filter((id) => filteredRowIds.includes(id)));
  }, [filteredRowIds]);

  useEffect(() => {
    if (!focusId || focusApplied || filteredRows.length === 0) return;

    const target = filteredRows.find((row) => row.exportEntry.id === focusId);
    if (!target) return;

    setSelectedExportId(target.exportEntry.id);
    setFocusApplied(true);

    const timer = window.setTimeout(() => {
      document.getElementById(`export-row-${target.exportEntry.id}`)?.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    }, 120);

    return () => window.clearTimeout(timer);
  }, [filteredRows, focusApplied, focusId]);

  const onRefresh = async () => {
    setActionError(null);
    setIsRefreshing(true);
    await refresh();
    window.setTimeout(() => setIsRefreshing(false), 220);
  };

  const onSelectRow = (row: ExportRecord) => {
    setSelectedExportId(row.exportEntry.id);
    if (isMobile) {
      setIsInspectOpen(true);
    }
  };

  const onToggleSelectExport = (exportId: string) => {
    setSelectedExportIds((current) =>
      current.includes(exportId) ? current.filter((id) => id !== exportId) : [...current, exportId]
    );
  };

  const onSelectAllFiltered = () => {
    setSelectedExportIds(filteredRowIds);
  };

  const onClearSelection = () => {
    setSelectedExportIds([]);
  };

  const onRequestDeleteExport = (exportId: string) => {
    setPendingDeleteIds([exportId]);
  };

  const onRequestDeleteSelected = () => {
    if (selectedExportIds.length === 0) return;
    setPendingDeleteIds([...selectedExportIds]);
  };

  const onConfirmDeleteExports = async () => {
    if (!pendingDeleteIds || pendingDeleteIds.length === 0) return;

    const targetIds = [...pendingDeleteIds];
    setActionError(null);
    setDeleting((state) => {
      const next = { ...state };
      targetIds.forEach((id) => {
        next[id] = true;
      });
      return next;
    });

    try {
      const results = await Promise.allSettled(targetIds.map((id) => deleteExport(id)));
      const deletedIds: string[] = [];
      let failedCount = 0;

      results.forEach((result, index) => {
        if (result.status === "fulfilled") {
          deletedIds.push(targetIds[index]);
        } else {
          failedCount += 1;
        }
      });

      if (deletedIds.length > 0) {
        await refresh();
        if (selectedExportId && deletedIds.includes(selectedExportId)) {
          setSelectedExportId(null);
        }
        setSelectedExportIds((current) => current.filter((id) => !deletedIds.includes(id)));
        showToast({
          variant: "success",
          title: deletedIds.length === 1 ? "Export deleted" : `${deletedIds.length} exports deleted`,
          description: "The selected exports were removed from the workspace.",
        });
      }

      if (failedCount > 0) {
        const message = failedCount === 1 ? "1 export could not be deleted." : `${failedCount} exports could not be deleted.`;
        setActionError(message);
        showToast({
          variant: "error",
          title: "Partial delete failure",
          description: message,
        });
      }

      setPendingDeleteIds(null);
    } catch (err) {
      const message = userFacingError(err, "Unable to delete exports.");
      setActionError(message);
      showToast({
        variant: "error",
        title: "Delete failed",
        description: message,
      });
    } finally {
      setDeleting((state) => {
        const next = { ...state };
        targetIds.forEach((id) => {
          delete next[id];
        });
        return next;
      });
    }
  };

  const resetFilters = () => {
    setSearch("");
    setFilter("all");
    setSort("newest");
  };

  const showSkeletons = isLoading && exports.length === 0;
  const effectiveError = actionError ?? error;

  return (
    <main className="app-page">
      <div className="app-page-inner pb-24 lg:pb-14">
        <div className="w-full space-y-4">
        <motion.section
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.34, ease: [0.16, 1, 0.3, 1] }}
          className="sticky top-[var(--app-header-offset)] z-30"
        >
          <div className="rounded-[1.5rem] border border-border/65 bg-card/68 p-4 shadow-[0_16px_48px_-34px_rgba(15,23,42,0.42)] backdrop-blur-xl sm:p-5">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <p className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">Exports</p>
                <h1 className="mt-1 text-[clamp(1.65rem,3.8vw,2.65rem)] font-semibold leading-[0.95] tracking-[-0.03em] text-foreground">
                  Export workspace
                </h1>
                <p className="mt-1 text-sm text-muted-foreground">
                  {hasPending ? "Live tracking is active while exports are running." : "All exports are stable."}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="inline-flex items-center rounded-full border border-border/70 bg-background/65 px-3 py-1.5 font-medium text-muted-foreground">
                  {stats.total} exports
                </span>
                <span className="inline-flex items-center rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 font-medium text-emerald-700 dark:text-emerald-300">
                  {stats.ready} ready
                </span>
                <span className="inline-flex items-center rounded-full border border-sky-500/30 bg-sky-500/10 px-3 py-1.5 font-medium text-sky-700 dark:text-sky-300">
                  {stats.running} running
                </span>
                <span className="inline-flex items-center rounded-full border border-destructive/30 bg-destructive/10 px-3 py-1.5 font-medium text-destructive">
                  {stats.failed} errors
                </span>
              </div>
            </div>

            <div className="mt-4 grid gap-3 xl:grid-cols-[minmax(0,1fr)_auto_auto_auto] xl:items-center">
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search export, clip, video..."
                  className="h-11 pl-9"
                  aria-label="Search exports"
                />
              </div>

              <div className="flex flex-wrap gap-1.5">
                {FILTER_ITEMS.map((item) => {
                  const active = item.id === filter;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      aria-pressed={active}
                      onClick={() => setFilter(item.id)}
                      className={cn(
                        "rounded-full border px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.12em] transition",
                        active
                          ? "border-primary/45 bg-primary/15 text-primary"
                          : "border-border/70 bg-background/65 text-muted-foreground hover:text-foreground"
                      )}
                    >
                      {item.label}
                    </button>
                  );
                })}
              </div>

              <label className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                <span className="sr-only">Sort exports</span>
                <select
                  value={sort}
                  onChange={(event) => setSort(event.target.value as ExportSort)}
                  className="h-11 min-w-[210px] rounded-xl border border-input bg-background/75 px-3 text-sm text-foreground outline-none transition focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <option value="newest">Date (newest first)</option>
                  <option value="oldest">Date (oldest first)</option>
                  <option value="video">Video name</option>
                  <option value="preset">Preset</option>
                </select>
              </label>

              <Button variant="outline" className="h-11 rounded-xl px-4" onClick={onRefresh} disabled={isRefreshing}>
                <RefreshCcw className={cn("mr-2 h-4 w-4", isRefreshing && "animate-spin")} />
                Refresh
              </Button>
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-2">
              <Button
                type="button"
                variant="outline"
                className="h-9 rounded-full px-3 text-xs font-semibold uppercase tracking-[0.11em]"
                onClick={allFilteredSelected ? onClearSelection : onSelectAllFiltered}
                disabled={filteredRowIds.length === 0}
              >
                {allFilteredSelected ? "Clear selection" : "Select all filtered"}
              </Button>

              {selectedCount > 0 ? (
                <>
                  <span className="inline-flex items-center rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.11em] text-primary">
                    {selectedCount} selected
                  </span>
                  <Button
                    type="button"
                    variant="destructive"
                    className="h-9 rounded-full px-3 text-xs font-semibold uppercase tracking-[0.11em]"
                    onClick={onRequestDeleteSelected}
                  >
                    <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                    Delete selected
                  </Button>
                </>
              ) : null}
            </div>
          </div>
        </motion.section>

        {effectiveError ? (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-2xl border border-destructive/35 bg-destructive/10 px-4 py-3 text-sm text-destructive"
          >
            <p className="inline-flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" />
              {effectiveError}
            </p>
          </motion.div>
        ) : null}

        {lastUpdatedAt ? (
          <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
            Last update: {new Date(lastUpdatedAt).toLocaleTimeString()}
          </p>
        ) : null}

        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px] xl:grid-cols-[minmax(0,1fr)_390px]">
          <section className="min-h-[340px]">
            {showSkeletons ? (
              <ExportsListSkeleton count={7} />
            ) : filteredRows.length === 0 ? (
              exports.length === 0 ? (
                <div className="rounded-[1.55rem] border border-border/70 bg-card/78 px-6 py-12 text-center shadow-[0_28px_80px_-56px_rgba(15,23,42,0.5)] backdrop-blur-xl">
                  <p className="text-base font-semibold text-foreground">No exports yet</p>
                  <p className="mx-auto mt-1 max-w-xl text-sm text-muted-foreground">
                    Create an export from the clips workspace and it will appear here.
                  </p>
                  <div className="mt-5">
                    <Button asChild className="rounded-full px-6">
                      <Link href={videoId ? `/clips?videoId=${videoId}` : "/clips"}>Open clips</Link>
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="rounded-[1.55rem] border border-border/70 bg-card/78 px-6 py-12 text-center shadow-[0_28px_80px_-56px_rgba(15,23,42,0.5)] backdrop-blur-xl">
                  <p className="text-base font-semibold text-foreground">No exports match these filters</p>
                  <p className="mx-auto mt-1 max-w-xl text-sm text-muted-foreground">
                    Adjust search or status filters to reveal matching exports.
                  </p>
                  <div className="mt-5">
                    <Button variant="outline" className="rounded-full px-6" onClick={resetFilters}>
                      Reset filters
                    </Button>
                  </div>
                </div>
              )
            ) : (
              <motion.ul layout className={cn("space-y-2.5", isRefreshing && "processing-refresh-pulse")}>
                <AnimatePresence mode="popLayout" initial={false}>
                  {filteredRows.map((row, index) => {
                    const status = exportStatus(row.exportEntry.status, row.exportEntry.output_url);
                    const selected = selectedRow?.exportEntry.id === row.exportEntry.id;
                    const focused = focusId === row.exportEntry.id;
                    const isDeleting = Boolean(deleting[row.exportEntry.id]);

                    return (
                      <motion.li
                        layout
                        key={row.exportEntry.id}
                        initial={{ opacity: 0, y: 14, scale: 0.992 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: -10, scale: 0.992 }}
                        transition={{ duration: 0.26, delay: Math.min(index * 0.02, 0.14), ease: [0.16, 1, 0.3, 1] }}
                      >
                        <div
                          id={`export-row-${row.exportEntry.id}`}
                          role="button"
                          tabIndex={0}
                          onClick={() => onSelectRow(row)}
                          onKeyDown={(event) => {
                            if (event.key === "Enter" || event.key === " ") {
                              event.preventDefault();
                              onSelectRow(row);
                            }
                          }}
                          className={cn(
                            "rounded-2xl border bg-card/78 p-3 shadow-[0_18px_52px_-38px_rgba(15,23,42,0.46)] backdrop-blur-xl transition",
                            selected || focused
                              ? "border-primary/55 ring-2 ring-primary/20"
                              : "border-border/65 hover:border-border"
                          )}
                          aria-label={`Inspect export ${row.exportEntry.id}`}
                        >
                          <div className="grid gap-3 md:grid-cols-[40px_120px_minmax(0,1fr)_auto] md:items-center">
                            <div className="flex items-center justify-center" onClick={(event) => event.stopPropagation()}>
                              <SelectToggle
                                selected={selectedExportIds.includes(row.exportEntry.id)}
                                onToggle={() => onToggleSelectExport(row.exportEntry.id)}
                                label={`Select export ${row.exportEntry.id}`}
                                size="md"
                              />
                            </div>

                            <span className={cn("inline-flex w-fit rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em]", exportStatusTone(status))}>
                              {status}
                            </span>

                            <div>
                              <p className="line-clamp-1 text-sm font-semibold text-foreground">
                                {clipTitle(row.clip.user_title, row.clip.tiktok_title, row.clip.id)}
                              </p>
                              <p className="mt-0.5 text-xs uppercase tracking-[0.12em] text-muted-foreground">
                                {row.video.filename} | {row.exportEntry.mode} | {formatDate(row.exportEntry.created_at)}
                              </p>
                              <p className="mt-1 text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
                                clip {row.clip.id.slice(0, 8)} | export {row.exportEntry.id.slice(0, 8)}
                              </p>
                            </div>

                            <div className="flex flex-wrap items-center justify-end gap-1.5" onClick={(event) => event.stopPropagation()}>
                              <Button asChild size="sm" variant="outline" className="rounded-full px-3">
                                <Link href={clipHref(row)}>
                                  <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
                                  Open
                                </Link>
                              </Button>

                              {status === "READY" ? (
                                <Button asChild size="sm" className="rounded-full px-3">
                                  <a href={downloadExportUrl(row.exportEntry.id)}>
                                    <Download className="mr-1.5 h-3.5 w-3.5" />
                                    Download
                                  </a>
                                </Button>
                              ) : (
                                <Button size="sm" variant="outline" className="rounded-full px-3" disabled>
                                  {status === "RUNNING" ? (
                                    <>
                                      <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                                      Pending
                                    </>
                                  ) : (
                                    "Unavailable"
                                  )}
                                </Button>
                              )}

                              <Button
                                size="icon"
                                variant="outline"
                                className="h-8 w-8 rounded-full border-destructive/35 text-destructive hover:bg-destructive/10"
                                disabled={isDeleting}
                                onClick={() => onRequestDeleteExport(row.exportEntry.id)}
                                aria-label="Delete export"
                              >
                                {isDeleting ? (
                                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                ) : (
                                  <Trash2 className="h-3.5 w-3.5" />
                                )}
                              </Button>
                            </div>
                          </div>
                        </div>
                      </motion.li>
                    );
                  })}
                </AnimatePresence>
              </motion.ul>
            )}
          </section>

          <aside className="hidden lg:block">
            <div className="sticky top-[calc(var(--app-header-offset)+6.65rem)]">
              <AnimatePresence mode="wait" initial={false}>
                {showSkeletons ? (
                  <motion.div
                    key="export-inspect-skeleton"
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -6 }}
                  >
                    <ExportInspectSkeleton />
                  </motion.div>
                ) : (
                  <motion.div
                    key={selectedRow?.exportEntry.id ?? "export-inspect-empty"}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -6 }}
                  >
                    <ExportInspectPanel
                      row={selectedRow}
                      deleting={selectedRow ? Boolean(deleting[selectedRow.exportEntry.id]) : false}
                      onDelete={onRequestDeleteExport}
                    />
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </aside>
        </div>
        </div>
      </div>

      {selectedRow ? (
        <div className="fixed inset-x-4 bottom-4 z-40 lg:hidden">
          <Button
            type="button"
            onClick={() => setIsInspectOpen(true)}
            className="h-12 w-full rounded-2xl border border-border/70 bg-card/92 text-foreground shadow-[0_20px_50px_-34px_rgba(15,23,42,0.62)] backdrop-blur-xl"
            variant="outline"
          >
            <Eye className="mr-2 h-4 w-4" />
            Preview selected export
          </Button>
        </div>
      ) : null}

      <Sheet open={isInspectOpen} onOpenChange={setIsInspectOpen}>
        <SheetContent
          side="bottom"
          className="h-[86vh] rounded-t-[1.3rem] border-x-0 border-b-0 border-t border-border/70 bg-background/96 p-4"
        >
          <SheetHeader className="mb-3">
            <SheetTitle>Export preview</SheetTitle>
            <SheetDescription>
              {selectedRow
                ? clipTitle(selectedRow.clip.user_title, selectedRow.clip.tiktok_title, selectedRow.clip.id)
                : "Select an export from the list"}
            </SheetDescription>
          </SheetHeader>

          {showSkeletons ? (
            <div className="pt-2">
              <ExportInspectSkeleton />
            </div>
          ) : (
            <div className="h-[calc(86vh-6.8rem)] overflow-y-auto pb-6">
              <ExportInspectPanel
                row={selectedRow}
                compact
                deleting={selectedRow ? Boolean(deleting[selectedRow.exportEntry.id]) : false}
                onDelete={onRequestDeleteExport}
              />
            </div>
          )}
        </SheetContent>
      </Sheet>

      {(isLoading || hasPending) && !showSkeletons ? (
        <div className="pointer-events-none fixed bottom-5 right-5 z-50 inline-flex items-center gap-2 rounded-full border border-border/70 bg-card/85 px-3 py-1.5 text-xs font-medium text-muted-foreground shadow-lg backdrop-blur-xl">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          {hasPending ? "Monitoring running exports" : "Syncing exports"}
        </div>
      ) : null}

      <ConfirmDialog
        open={Boolean(pendingDeleteIds && pendingDeleteIds.length > 0)}
        onOpenChange={(open) => {
          if (!open) {
            const isConfirming = Boolean(
              pendingDeleteIds?.some((id) => Boolean(deleting[id]))
            );
            if (isConfirming) return;
            setPendingDeleteIds(null);
          }
        }}
        title={
          pendingDeleteIds && pendingDeleteIds.length > 1
            ? `Delete ${pendingDeleteIds.length} exports?`
            : "Delete this export?"
        }
        description="This action is permanent."
        confirmLabel="Delete"
        cancelLabel="Cancel"
        confirmVariant="destructive"
        isConfirming={Boolean(
          pendingDeleteIds?.some((id) => Boolean(deleting[id]))
        )}
        onConfirm={onConfirmDeleteExports}
      >
        {pendingDeleteIds ? (
          <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
            {pendingDeleteIds.length} export{pendingDeleteIds.length > 1 ? "s" : ""} selected for deletion
          </p>
        ) : null}
      </ConfirmDialog>
    </main>
  );
}
