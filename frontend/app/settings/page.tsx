"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  CircleDashed,
  Clapperboard,
  Film,
  Loader2,
  RefreshCcw,
  Settings2,
  Trash2,
  Video,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/cn";
import { deleteVideo, deleteTikTokAccount, listTikTokAccounts, tiktokLoginUrl } from "@/lib/api";
import { userFacingError } from "@/lib/user-error";
import { useAppStore } from "@/store/app-store";
import { TikTokAccount } from "@/lib/types";

function statusTone(status?: string) {
  if (status === "ready") return "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300";
  if (status === "error") return "border-destructive/30 bg-destructive/10 text-destructive";
  if (status === "generating" || status === "analyzing" || status === "analyzed" || status === "uploaded") {
    return "border-sky-500/30 bg-sky-500/10 text-sky-700 dark:text-sky-300";
  }
  return "border-border/70 bg-background/70 text-muted-foreground";
}

function statusLabel(status?: string) {
  if (!status) return "Unknown";
  if (status === "ready") return "Ready";
  if (status === "analyzing") return "Analyzing";
  if (status === "analyzed") return "Analyzed";
  if (status === "generating") return "Generating";
  if (status === "uploaded") return "Queued";
  if (status === "error") return "Error";
  return status;
}

export default function SettingsPage() {
  const { showToast } = useToast();

  const videos = useAppStore((state) => state.videos);
  const activeVideoId = useAppStore((state) => state.activeVideoId);
  const clipsByVideoId = useAppStore((state) => state.clipsByVideoId);
  const exportsRows = useAppStore((state) => state.exports);

  const refreshVideos = useAppStore((state) => state.refreshVideos);
  const refreshExports = useAppStore((state) => state.refreshExports);
  const setActiveVideoId = useAppStore((state) => state.setActiveVideoId);

  const [isSyncing, setIsSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [lastSyncAt, setLastSyncAt] = useState<number | null>(null);
  const [deletingVideoId, setDeletingVideoId] = useState<string | null>(null);
  const [pendingDeleteVideo, setPendingDeleteVideo] = useState<{ id: string; filename: string } | null>(null);

  // TikTok accounts
  const [tiktokAccounts, setTiktokAccounts] = useState<TikTokAccount[]>([]);
  const [isLoadingTiktok, setIsLoadingTiktok] = useState(false);
  const [isDeletingTiktok, setIsDeletingTiktok] = useState<string | null>(null);

  const loadTiktokAccounts = useCallback(async () => {
    setIsLoadingTiktok(true);
    try {
      const accounts = await listTikTokAccounts();
      setTiktokAccounts(accounts);
    } catch {
      // silencieux
    } finally {
      setIsLoadingTiktok(false);
    }
  }, []);

  const onDeleteTiktokAccount = useCallback(async (accountId: string) => {
    setIsDeletingTiktok(accountId);
    try {
      await deleteTikTokAccount(accountId);
      setTiktokAccounts((prev) => prev.filter((a) => a.id !== accountId));
      showToast({ variant: "success", title: "Compte TikTok déconnecté" });
    } catch (err) {
      showToast({ variant: "error", title: "Erreur", description: userFacingError(err, "Impossible de supprimer le compte.") });
    } finally {
      setIsDeletingTiktok(null);
    }
  }, [showToast]);

  const syncWorkspace = useCallback(async (options?: { silent?: boolean }) => {
    setIsSyncing(true);
    setSyncError(null);

    try {
      await Promise.all([refreshVideos(), refreshExports(undefined, { silent: true })]);
      setLastSyncAt(Date.now());
      if (!options?.silent) {
        showToast({
          variant: "success",
          title: "Workspace synced",
          description: "Videos, clips and exports are up to date.",
        });
      }
    } catch (err) {
      const message = userFacingError(err, "Unable to sync workspace.");
      setSyncError(message);
      if (!options?.silent) {
        showToast({
          variant: "error",
          title: "Sync failed",
          description: message,
        });
      }
    } finally {
      setIsSyncing(false);
    }
  }, [refreshExports, refreshVideos, showToast]);

  useEffect(() => {
    syncWorkspace({ silent: true }).catch(() => null);
  }, [syncWorkspace]);

  useEffect(() => {
    loadTiktokAccounts();
    // Après un callback OAuth TikTok, on reload les comptes
    const params = new URLSearchParams(window.location.search);
    if (params.get("tiktok_connected") === "1") {
      showToast({ variant: "success", title: "Compte TikTok connecté !" });
      window.history.replaceState({}, "", "/settings");
    }
  }, [loadTiktokAccounts, showToast]);

  const onRequestDeleteVideo = useCallback((videoId: string, filename: string) => {
    setPendingDeleteVideo({ id: videoId, filename });
  }, []);

  const onConfirmDeleteVideo = useCallback(async () => {
      if (!pendingDeleteVideo) return;
      const { id: videoId } = pendingDeleteVideo;

      setDeletingVideoId(videoId);
      setSyncError(null);

      try {
        await deleteVideo(videoId);

        if (activeVideoId === videoId) {
          setActiveVideoId(null);
        }

        await syncWorkspace({ silent: true });
        setPendingDeleteVideo(null);
        showToast({
          variant: "success",
          title: "Video deleted",
          description: "Associated clips and exports were removed.",
        });
      } catch (err) {
        const message = userFacingError(err, "Unable to delete video.");
        setSyncError(message);
        showToast({
          variant: "error",
          title: "Delete failed",
          description: message,
        });
      } finally {
        setDeletingVideoId(null);
      }
    },
    [activeVideoId, pendingDeleteVideo, setActiveVideoId, showToast, syncWorkspace]
  );

  const stats = useMemo(() => {
    const ready = videos.filter((video) => video.status === "ready").length;
    const processing = videos.filter((video) => ["uploaded", "analyzing", "analyzed", "generating"].includes(video.status)).length;
    const errors = videos.filter((video) => video.status === "error").length;

    const totalClips = videos.reduce((sum, video) => {
      const count = video.clips?.length ?? clipsByVideoId[video.id]?.length ?? 0;
      return sum + count;
    }, 0);

    return {
      totalVideos: videos.length,
      ready,
      processing,
      errors,
      totalClips,
      totalExports: exportsRows.length,
    };
  }, [clipsByVideoId, exportsRows.length, videos]);

  const activeVideo = useMemo(
    () => (activeVideoId ? videos.find((video) => video.id === activeVideoId) ?? null : null),
    [activeVideoId, videos]
  );

  const sortedVideos = useMemo(() => {
    return [...videos].sort((a, b) => {
      const aDate = Date.parse(a.created_at ?? "");
      const bDate = Date.parse(b.created_at ?? "");
      return bDate - aDate;
    });
  }, [videos]);

  return (
    <main className="app-page">
      <div className="app-page-inner pb-14">
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
                <p className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">Settings</p>
                <h1 className="mt-1 text-[clamp(1.65rem,3.8vw,2.65rem)] font-semibold leading-[0.95] tracking-[-0.03em] text-foreground">
                  Settings control center
                </h1>
                <p className="mt-1 text-sm text-muted-foreground">
                  Workspace-level overview and quick operational shortcuts.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="inline-flex items-center rounded-full border border-border/70 bg-background/65 px-3 py-1.5 font-medium text-muted-foreground">
                  {stats.totalVideos} videos
                </span>
                <span className="inline-flex items-center rounded-full border border-border/70 bg-background/65 px-3 py-1.5 font-medium text-muted-foreground">
                  {stats.totalClips} clips
                </span>
                <span className="inline-flex items-center rounded-full border border-border/70 bg-background/65 px-3 py-1.5 font-medium text-muted-foreground">
                  {stats.totalExports} exports
                </span>
              </div>
            </div>

            <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                {lastSyncAt ? `Last sync ${new Date(lastSyncAt).toLocaleTimeString()}` : "No sync yet"}
              </p>

              <Button variant="outline" className="h-11 rounded-xl px-4" onClick={() => void syncWorkspace()} disabled={isSyncing}>
                <RefreshCcw className={cn("mr-2 h-4 w-4", isSyncing && "animate-spin")} />
                Sync workspace
              </Button>
            </div>
          </div>
        </motion.section>

        {syncError ? (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-2xl border border-destructive/35 bg-destructive/10 px-4 py-3 text-sm text-destructive"
          >
            <p className="inline-flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" />
              {syncError}
            </p>
          </motion.div>
        ) : null}

        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
          <section className="space-y-5">
            <motion.article
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ amount: 0.25, once: true }}
              className="rounded-[1.5rem] border border-border/65 bg-card/78 p-5 shadow-[0_22px_62px_-42px_rgba(15,23,42,0.52)] backdrop-blur-xl"
            >
              <h2 className="inline-flex items-center gap-2 text-lg font-semibold text-foreground">
                <Settings2 className="h-4 w-4" />
                Product flow
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Active flow: upload and processing, clips review, export creation, export tracking.
              </p>

              <div className="mt-4 flex flex-wrap gap-2">
                <Button asChild className="rounded-full px-4">
                  <Link href="/">
                    Open upload
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
                <Button asChild variant="outline" className="rounded-full px-4">
                  <Link href={activeVideoId ? `/clips?videoId=${activeVideoId}` : "/clips"}>Open clips</Link>
                </Button>
                <Button asChild variant="outline" className="rounded-full px-4">
                  <Link href={activeVideoId ? `/exports?videoId=${activeVideoId}` : "/exports"}>Open exports</Link>
                </Button>
              </div>
            </motion.article>

            <motion.article
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ amount: 0.25, once: true }}
              className="rounded-[1.5rem] border border-border/65 bg-card/78 p-5 shadow-[0_22px_62px_-42px_rgba(15,23,42,0.52)] backdrop-blur-xl"
            >
              <h2 className="text-lg font-semibold text-foreground">Workspace snapshot</h2>
              <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                <div className="rounded-xl border border-border/70 bg-background/70 px-3 py-3">
                  <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Ready videos</p>
                  <p className="mt-1 text-xl font-semibold text-foreground">{stats.ready}</p>
                </div>
                <div className="rounded-xl border border-border/70 bg-background/70 px-3 py-3">
                  <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Processing</p>
                  <p className="mt-1 text-xl font-semibold text-foreground">{stats.processing}</p>
                </div>
                <div className="rounded-xl border border-border/70 bg-background/70 px-3 py-3">
                  <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Error videos</p>
                  <p className="mt-1 text-xl font-semibold text-foreground">{stats.errors}</p>
                </div>
                <div className="rounded-xl border border-border/70 bg-background/70 px-3 py-3">
                  <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Total clips</p>
                  <p className="mt-1 text-xl font-semibold text-foreground">{stats.totalClips}</p>
                </div>
              </div>
            </motion.article>

            <motion.article
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ amount: 0.25, once: true }}
              className="rounded-[1.5rem] border border-border/65 bg-card/78 p-5 shadow-[0_22px_62px_-42px_rgba(15,23,42,0.52)] backdrop-blur-xl"
            >
              <h2 className="text-lg font-semibold text-foreground">Video health</h2>
              <p className="mt-1 text-sm text-muted-foreground">Current status across source videos.</p>

              {sortedVideos.length === 0 ? (
                <div className="mt-4 rounded-xl border border-dashed border-border/75 bg-background/55 px-4 py-8 text-center text-sm text-muted-foreground">
                  No videos found in this workspace.
                </div>
              ) : (
                <div className="mt-4 space-y-2.5">
                  {sortedVideos.slice(0, 8).map((video) => {
                    const clipCount = video.clips?.length ?? clipsByVideoId[video.id]?.length ?? 0;
                    const active = activeVideoId === video.id;

                    return (
                      <div
                        key={video.id}
                        className={cn(
                          "rounded-xl border border-border/70 bg-background/70 px-3 py-3 transition",
                          active && "border-primary/45 ring-1 ring-primary/20"
                        )}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <p className="line-clamp-1 text-sm font-semibold text-foreground">{video.filename}</p>
                            <p className="mt-0.5 text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
                              video {video.id.slice(0, 8)} | {clipCount} clips
                            </p>
                          </div>

                          <div className="flex shrink-0 items-center gap-2">
                            <span className={cn("inline-flex rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em]", statusTone(video.status))}>
                              {statusLabel(video.status)}
                            </span>

                            <Button
                              type="button"
                              size="sm"
                              variant="outline"
                              className="h-8 rounded-lg border-destructive/40 px-2.5 text-destructive hover:bg-destructive/10"
                              onClick={() => onRequestDeleteVideo(video.id, video.filename)}
                              disabled={isSyncing || deletingVideoId === video.id}
                            >
                              {deletingVideoId === video.id ? (
                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                              ) : (
                                <Trash2 className="h-3.5 w-3.5" />
                              )}
                            </Button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </motion.article>
          </section>

          <aside className="space-y-5">
            <motion.article
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ amount: 0.25, once: true }}
              className="rounded-[1.5rem] border border-border/65 bg-card/78 p-5 shadow-[0_22px_62px_-42px_rgba(15,23,42,0.52)] backdrop-blur-xl"
            >
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-lg font-semibold text-foreground">TikTok accounts</h2>
                <Button
                  asChild
                  size="sm"
                  className="rounded-full px-4"
                >
                  <a href={tiktokLoginUrl()} target="_self">
                    + Connect
                  </a>
                </Button>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                Connected accounts available for sending exports as drafts.
              </p>

              {isLoadingTiktok ? (
                <div className="mt-4 flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading...
                </div>
              ) : tiktokAccounts.length === 0 ? (
                <div className="mt-4 rounded-xl border border-dashed border-border/75 bg-background/55 px-4 py-7 text-center text-sm text-muted-foreground">
                  No TikTok account connected yet.
                </div>
              ) : (
                <div className="mt-4 space-y-2">
                  {tiktokAccounts.map((account) => (
                    <div
                      key={account.id}
                      className="flex items-center justify-between gap-3 rounded-xl border border-border/70 bg-background/70 px-3 py-3"
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        {account.avatar_url ? (
                          <img
                            src={account.avatar_url}
                            alt=""
                            className="h-8 w-8 rounded-full border border-border/60 object-cover shrink-0"
                          />
                        ) : (
                          <div className="h-8 w-8 rounded-full border border-border/60 bg-muted flex items-center justify-center shrink-0 text-xs font-semibold text-muted-foreground">
                            {(account.display_name ?? "T").slice(0, 1).toUpperCase()}
                          </div>
                        )}
                        <div className="min-w-0">
                          <p className="text-sm font-semibold text-foreground truncate">
                            {account.display_name ?? account.open_id}
                          </p>
                          <p className="text-[11px] text-muted-foreground uppercase tracking-[0.12em]">
                            TikTok
                          </p>
                        </div>
                      </div>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        className="h-8 rounded-lg border-destructive/40 px-2.5 text-destructive hover:bg-destructive/10 shrink-0"
                        onClick={() => onDeleteTiktokAccount(account.id)}
                        disabled={isDeletingTiktok === account.id}
                      >
                        {isDeletingTiktok === account.id ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <Trash2 className="h-3.5 w-3.5" />
                        )}
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </motion.article>

            <motion.article
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ amount: 0.25, once: true }}
              className="rounded-[1.5rem] border border-border/65 bg-card/78 p-5 shadow-[0_22px_62px_-42px_rgba(15,23,42,0.52)] backdrop-blur-xl"
            >
              <h2 className="text-lg font-semibold text-foreground">Active context</h2>

              {activeVideo ? (
                <div className="mt-3 rounded-xl border border-border/70 bg-background/70 p-3">
                  <p className="line-clamp-2 text-sm font-semibold text-foreground">{activeVideo.filename}</p>
                  <p className="mt-1 text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
                    video {activeVideo.id.slice(0, 8)}
                  </p>
                  <span className={cn("mt-2 inline-flex rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em]", statusTone(activeVideo.status))}>
                    {statusLabel(activeVideo.status)}
                  </span>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button asChild size="sm" variant="outline" className="rounded-full px-3">
                      <Link href={`/clips?videoId=${activeVideo.id}`}>
                        <Clapperboard className="mr-1.5 h-3.5 w-3.5" />
                        Clips
                      </Link>
                    </Button>
                    <Button asChild size="sm" variant="outline" className="rounded-full px-3">
                      <Link href={`/exports?videoId=${activeVideo.id}`}>
                        <Film className="mr-1.5 h-3.5 w-3.5" />
                        Exports
                      </Link>
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="mt-3 rounded-xl border border-dashed border-border/75 bg-background/55 px-4 py-7 text-center text-sm text-muted-foreground">
                  No active video selected.
                </div>
              )}
            </motion.article>

            <motion.article
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ amount: 0.25, once: true }}
              className="rounded-[1.5rem] border border-border/65 bg-card/78 p-5 shadow-[0_22px_62px_-42px_rgba(15,23,42,0.52)] backdrop-blur-xl"
            >
              <h2 className="text-lg font-semibold text-foreground">System notes</h2>
              <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
                <li className="inline-flex items-start gap-2">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-600 dark:text-emerald-300" />
                  Clip and export indexes are read from the current workspace store.
                </li>
                <li className="inline-flex items-start gap-2">
                  <CircleDashed className="mt-0.5 h-4 w-4 text-sky-600 dark:text-sky-300" />
                  Sync refreshes videos and exports without changing business behavior.
                </li>
                <li className="inline-flex items-start gap-2">
                  <Video className="mt-0.5 h-4 w-4 text-muted-foreground" />
                  Use Clips and Exports pages for editing, exporting and tracking operations.
                </li>
              </ul>
            </motion.article>
          </aside>
        </div>
        </div>
      </div>

      <ConfirmDialog
        open={Boolean(pendingDeleteVideo)}
        onOpenChange={(open) => {
          if (!open && !deletingVideoId) setPendingDeleteVideo(null);
        }}
        title="Supprimer cette video ?"
        description="Cette action supprimera aussi tous les clips et exports associes."
        confirmLabel="Supprimer"
        cancelLabel="Annuler"
        confirmVariant="destructive"
        isConfirming={Boolean(deletingVideoId)}
        onConfirm={onConfirmDeleteVideo}
      >
        {pendingDeleteVideo ? (
          <div className="rounded-xl border border-border/70 bg-background/70 p-3">
            <p className="line-clamp-2 text-sm font-semibold text-foreground">{pendingDeleteVideo.filename}</p>
            <p className="mt-1 text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
              video {pendingDeleteVideo.id.slice(0, 8)}
            </p>
          </div>
        ) : null}
      </ConfirmDialog>
    </main>
  );
}
