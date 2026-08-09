"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, Download, Loader2, RefreshCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { downloadExportUrl } from "@/lib/api";
import { DEFAULT_EXPORT_PRESET_ID, EXPORT_PRESETS } from "@/lib/export-presets";
import { API_BASE } from "@/lib/types";
import { userFacingError } from "@/lib/user-error";
import { formatTimestamp, parseSignals } from "@/lib/workflow-utils";
import { useClip } from "@/hooks/use-clip";

function clipTitle(rawTitle?: string | null, fallbackTitle?: string | null, clipId?: string) {
  return (rawTitle ?? fallbackTitle ?? "").trim() || `Clip ${clipId?.slice(0, 8) ?? ""}`;
}

function isExportReady(status: string, outputUrl?: string | null) {
  return Boolean(outputUrl) || status === "done";
}

export default function ClipPage() {
  const { showToast } = useToast();

  const params = useParams<{ clipId: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const requestedVideoId = searchParams.get("videoId");

  const clipId = params?.clipId;
  const { clip, video, exportsList, isLoading, isExporting, isSavingTitle, error, refresh, saveTitle, startExport } = useClip(clipId);

  const [title, setTitle] = useState("");
  const [selectedPreset, setSelectedPreset] = useState<string>(DEFAULT_EXPORT_PRESET_ID);

  const activePreset = useMemo(
    () => EXPORT_PRESETS.find((item) => item.id === selectedPreset) ?? EXPORT_PRESETS[0],
    [selectedPreset]
  );

  useEffect(() => {
    if (!clip) return;
    setTitle((previous) =>
      previous.length > 0 ? previous : clipTitle(clip.user_title, clip.tiktok_title, clip.id)
    );
  }, [clip]);

  const metadata = useMemo(() => {
    if (!clip) return [] as string[];

    const parts = [
      `Start ${formatTimestamp(clip.start_seconds)}`,
      `End ${formatTimestamp(clip.end_seconds)}`,
      `Duration ${formatTimestamp(Math.max(0, clip.end_seconds - clip.start_seconds))}`,
    ];

    if (typeof clip.score === "number") {
      parts.push(`Score ${Math.round(clip.score * 100)}%`);
    }

    if (clip.tag) {
      parts.push(`Tag ${clip.tag}`);
    }

    return parts;
  }, [clip]);

  const signalPreview = useMemo(() => {
    if (!clip?.signals) return "";
    return parseSignals(clip.signals).slice(0, 4).join(" | ");
  }, [clip?.signals]);

  const handleSaveTitle = async () => {
    try {
      await saveTitle(title);
      showToast({
        variant: "success",
        title: "Title saved",
        description: "Clip title was updated.",
      });
    } catch (err) {
      showToast({
        variant: "error",
        title: "Save failed",
        description: userFacingError(err, "Unable to save title."),
      });
    }
  };

  const handleExport = async () => {
    try {
      const response = await startExport(selectedPreset, title);
      if (!response?.export_id) {
        showToast({
          variant: "error",
          title: "Export failed",
          description: "No export id returned by the server.",
        });
        return;
      }

      showToast({
        variant: "success",
        title: "Export queued",
        description: "Opening export workspace...",
      });

      const nextParams = new URLSearchParams();
      nextParams.set("focus", response.export_id);
      if (requestedVideoId ?? video?.id) {
        nextParams.set("videoId", requestedVideoId ?? video?.id ?? "");
      }

      router.push(`/exports?${nextParams.toString()}`);
    } catch (err) {
      showToast({
        variant: "error",
        title: "Export failed",
        description: userFacingError(err, "Unable to create export."),
      });
    }
  };

  if (isLoading && !clip) {
    return (
      <main className="app-shell flex min-h-[60vh] items-center justify-center">
        <div className="inline-flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading clip...
        </div>
      </main>
    );
  }

  if (!clip) {
    return (
      <main className="app-shell">
        <Card>
          <CardContent className="space-y-3 py-8">
            <p className="text-lg font-semibold">Clip not found</p>
            <p className="text-sm text-muted-foreground">The clip is unavailable or was deleted.</p>
            <Button asChild className="rounded-lg bg-slate-900 text-slate-50 hover:bg-slate-800">
              <Link href="/clips">Back to clips</Link>
            </Button>
          </CardContent>
        </Card>
      </main>
    );
  }

  const backHref = requestedVideoId ? `/clips?videoId=${requestedVideoId}` : "/clips";

  return (
    <main className="app-shell pb-14">
      <div className="mx-auto w-full max-w-6xl space-y-6">
        <section className="flex flex-wrap items-center justify-between gap-3">
          <Button asChild variant="ghost" className="rounded-lg">
            <Link href={backHref}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to clips
            </Link>
          </Button>

          <Button variant="outline" className="rounded-lg" onClick={() => refresh()}>
            <RefreshCcw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </section>

        {error ? (
          <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        ) : null}

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
          <Card className="overflow-hidden">
            <div className="flex items-center justify-center bg-black p-3">
              {clip.preview_url ? (
                <div
                  className="relative w-full overflow-hidden rounded-md border border-white/10 transition-[aspect-ratio,max-width] duration-300 ease-out"
                  style={{
                    aspectRatio: activePreset.aspectRatio,
                    maxWidth: `min(100%, calc(62vh * ${activePreset.aspectRatio}))`,
                  }}
                >
                  <video
                    className={`h-full w-full bg-black ${activePreset.objectFit === "contain" ? "object-contain" : "object-cover"}`}
                    controls
                    playsInline
                    preload="metadata"
                    src={`${API_BASE}${clip.preview_url}`}
                  />

                  <span className="pointer-events-none absolute right-2 top-2 rounded-full border border-white/20 bg-black/55 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-white">
                    {activePreset.ratioLabel}
                  </span>
                </div>
              ) : (
                <div
                  className="flex w-full items-center justify-center rounded-md border border-white/10 text-xs uppercase tracking-[0.16em] text-slate-400"
                  style={{
                    aspectRatio: activePreset.aspectRatio,
                    maxWidth: `min(100%, calc(62vh * ${activePreset.aspectRatio}))`,
                  }}
                >
                  <span>Preview unavailable</span>
                </div>
              )}
            </div>
            <CardHeader>
              <CardTitle className="text-xl">{clipTitle(clip.user_title, clip.tiktok_title, clip.id)}</CardTitle>
              <p className="text-sm text-muted-foreground">{video?.filename ?? "Unknown video"}</p>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex flex-wrap gap-2">
                {metadata.map((item) => (
                  <span
                    key={item}
                    className="rounded-full border border-border bg-muted/50 px-2.5 py-1 text-[11px] uppercase tracking-[0.14em] text-muted-foreground"
                  >
                    {item}
                  </span>
                ))}
              </div>
              {signalPreview ? <p className="text-xs text-muted-foreground">{signalPreview}</p> : null}
            </CardContent>
          </Card>

          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Export</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="space-y-1.5">
                  <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Title</p>
                  <div className="flex gap-2">
                    <Input value={title} onChange={(event) => setTitle(event.target.value)} />
                    <Button variant="outline" onClick={handleSaveTitle} disabled={isSavingTitle}>
                      {isSavingTitle ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save"}
                    </Button>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Preset</p>
                  <select
                    value={selectedPreset}
                    onChange={(event) => setSelectedPreset(event.target.value)}
                    className="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm"
                  >
                    {EXPORT_PRESETS.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                </div>

                <Button
                  className="w-full rounded-lg bg-slate-900 text-slate-50 hover:bg-slate-800"
                  onClick={handleExport}
                  disabled={isExporting}
                >
                  {isExporting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                  Export
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Recent exports</CardTitle>
              </CardHeader>
              <CardContent>
                {exportsList.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No exports yet.</p>
                ) : (
                  <ul className="space-y-2">
                    {exportsList.map((entry) => {
                      const ready = isExportReady(entry.status, entry.output_url);
                      return (
                        <li
                          key={entry.id}
                          className="flex items-center justify-between rounded-lg border border-border/70 bg-muted/30 px-3 py-2"
                        >
                          <div>
                            <p className="text-sm font-medium">{entry.mode}</p>
                            <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                              {ready ? "Ready" : entry.status}
                            </p>
                          </div>
                          {ready ? (
                            <Button asChild size="sm" className="rounded-lg bg-slate-900 text-slate-50 hover:bg-slate-800">
                              <a href={downloadExportUrl(entry.id)}>
                                <Download className="mr-1.5 h-3.5 w-3.5" />
                                Download
                              </a>
                            </Button>
                          ) : (
                            <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Pending</span>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </main>
  );
}
