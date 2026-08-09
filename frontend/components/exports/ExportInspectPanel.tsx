import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { Clock3, Download, ExternalLink, Film, Loader2, Send, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { downloadExportUrl, listTikTokAccounts, sendToTikTok } from "@/lib/api";
import { API_BASE, ExportRecord, TikTokAccount } from "@/lib/types";
import { clipTitle, exportStatus, exportStatusTone, formatDate } from "@/components/exports/export-ui-utils";

interface ExportInspectPanelProps {
  row: ExportRecord | null;
  compact?: boolean;
  deleting?: boolean;
  onDelete?: (exportId: string) => void;
}

function clipHref(row: ExportRecord) {
  return `/clips/${row.clip.id}?videoId=${row.video.id}`;
}

export function ExportInspectPanel({ row, compact = false, deleting, onDelete }: ExportInspectPanelProps) {
  const [tiktokAccounts, setTiktokAccounts] = useState<TikTokAccount[]>([]);
  const [showAccountPicker, setShowAccountPicker] = useState(false);
  const [uploadingAccountId, setUploadingAccountId] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<"success" | "error" | null>(null);

  useEffect(() => {
    listTikTokAccounts().then(setTiktokAccounts).catch(() => null);
  }, []);

  useEffect(() => {
    setUploadResult(null);
    setShowAccountPicker(false);
  }, [row?.exportEntry.id]);

  const onSendToTikTok = async (accountId: string) => {
    if (!row) return;
    setUploadingAccountId(accountId);
    setShowAccountPicker(false);
    try {
      await sendToTikTok(row.exportEntry.id, accountId);
      setUploadResult("success");
    } catch {
      setUploadResult("error");
    } finally {
      setUploadingAccountId(null);
    }
  };

  return (
    <div className={cn("rounded-[1.45rem] border border-border/65 bg-card/78 p-4 shadow-[0_22px_62px_-42px_rgba(15,23,42,0.52)] backdrop-blur-xl", compact ? "p-4" : "p-5")}>
      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={row?.exportEntry.id ?? "no-export"}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
          className="space-y-4"
        >
          {!row ? (
            <div className="rounded-xl border border-dashed border-border/80 bg-background/55 px-4 py-10 text-center">
              <div className="mx-auto inline-flex h-12 w-12 items-center justify-center rounded-full border border-border/75 bg-background text-muted-foreground">
                <Film className="h-5 w-5" />
              </div>
              <p className="mt-3 text-sm font-medium text-foreground">Select an export row</p>
              <p className="mt-1 text-xs uppercase tracking-[0.14em] text-muted-foreground">
                Preview and actions appear here
              </p>
            </div>
          ) : (
            <>
              <div className="overflow-hidden rounded-xl border border-border/70 bg-black/85">
                {row.clip.preview_url ? (
                  <video
                    className="aspect-video w-full object-contain"
                    src={`${API_BASE}${row.clip.preview_url}`}
                    controls
                    playsInline
                    preload="metadata"
                  />
                ) : (
                  <div className="flex aspect-video items-center justify-center text-xs uppercase tracking-[0.14em] text-slate-400">
                    Preview unavailable
                  </div>
                )}
              </div>

              <div>
                <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Selected export</p>
                <h2 className="mt-1 line-clamp-2 text-lg font-semibold tracking-[-0.015em] text-foreground">
                  {clipTitle(row.clip.user_title, row.clip.tiktok_title, row.clip.id)}
                </h2>
                <p className="mt-1 text-xs uppercase tracking-[0.14em] text-muted-foreground">
                  {row.video.filename}
                </p>
              </div>

              <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-1">
                <div className="rounded-xl border border-border/70 bg-background/70 px-3 py-2">
                  <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Status</p>
                  <p className={cn("mt-1 inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.14em]", exportStatusTone(exportStatus(row.exportEntry.status, row.exportEntry.output_url)))}>
                    {exportStatus(row.exportEntry.status, row.exportEntry.output_url)}
                  </p>
                </div>

                <div className="rounded-xl border border-border/70 bg-background/70 px-3 py-2">
                  <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Preset</p>
                  <p className="mt-1 text-sm font-semibold uppercase tracking-[0.12em] text-foreground">{row.exportEntry.mode}</p>
                </div>

                <div className="rounded-xl border border-border/70 bg-background/70 px-3 py-2">
                  <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Created</p>
                  <p className="mt-1 inline-flex items-center gap-1 text-sm font-medium text-foreground">
                    <Clock3 className="h-3.5 w-3.5 text-muted-foreground" />
                    {formatDate(row.exportEntry.created_at)}
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                <Button asChild className="h-10 flex-1 rounded-xl">
                  <Link href={clipHref(row)}>
                    <ExternalLink className="mr-2 h-4 w-4" />
                    Open clip
                  </Link>
                </Button>

                {exportStatus(row.exportEntry.status, row.exportEntry.output_url) === "READY" ? (
                  <Button asChild className="h-10 flex-1 rounded-xl" variant="outline">
                    <a href={downloadExportUrl(row.exportEntry.id)}>
                      <Download className="mr-2 h-4 w-4" />
                      Download
                    </a>
                  </Button>
                ) : (
                  <Button className="h-10 flex-1 rounded-xl" variant="outline" disabled>
                    Pending
                  </Button>
                )}
              </div>

              {/* TikTok upload */}
              {exportStatus(row.exportEntry.status, row.exportEntry.output_url) === "READY" && (
                <div className="space-y-2">
                  {uploadResult === "success" && (
                    <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-300">
                      ✓ Envoyé en brouillon TikTok — ouvre l&apos;app TikTok pour publier.
                    </div>
                  )}
                  {uploadResult === "error" && (
                    <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                      Erreur lors de l&apos;envoi TikTok. Vérifie que ton compte est connecté dans Settings.
                    </div>
                  )}

                  {tiktokAccounts.length === 0 ? (
                    <Button asChild variant="outline" className="h-10 w-full rounded-xl border-border/60">
                      <a href="/settings">
                        <Send className="mr-2 h-4 w-4" />
                        Connecter TikTok dans Settings
                      </a>
                    </Button>
                  ) : tiktokAccounts.length === 1 ? (
                    <Button
                      type="button"
                      variant="outline"
                      className="h-10 w-full rounded-xl border-border/60"
                      onClick={() => onSendToTikTok(tiktokAccounts[0].id)}
                      disabled={uploadingAccountId !== null}
                    >
                      {uploadingAccountId ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      ) : (
                        <Send className="mr-2 h-4 w-4" />
                      )}
                      {uploadingAccountId ? "Envoi en cours..." : `Envoyer sur TikTok — ${tiktokAccounts[0].display_name ?? "Compte"}`}
                    </Button>
                  ) : (
                    <div className="space-y-1.5">
                      <Button
                        type="button"
                        variant="outline"
                        className="h-10 w-full rounded-xl border-border/60"
                        onClick={() => setShowAccountPicker((v) => !v)}
                        disabled={uploadingAccountId !== null}
                      >
                        {uploadingAccountId ? (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                          <Send className="mr-2 h-4 w-4" />
                        )}
                        {uploadingAccountId ? "Envoi en cours..." : "Envoyer sur TikTok →"}
                      </Button>
                      {showAccountPicker && (
                        <div className="rounded-xl border border-border/70 bg-background/80 p-2 space-y-1">
                          {tiktokAccounts.map((account) => (
                            <button
                              key={account.id}
                              type="button"
                              className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm hover:bg-accent transition-colors text-left"
                              onClick={() => onSendToTikTok(account.id)}
                            >
                              <Send className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                              {account.display_name ?? account.open_id}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {onDelete ? (
                <Button
                  type="button"
                  variant="outline"
                  className="h-10 w-full rounded-xl border-destructive/40 text-destructive hover:bg-destructive/10"
                  onClick={() => onDelete(row.exportEntry.id)}
                  disabled={deleting}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  {deleting ? "Deleting..." : "Delete export"}
                </Button>
              ) : null}
            </>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
