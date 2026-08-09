"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Check, Loader2, RefreshCw } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";

const STAGE_CHIPS = ["Upload", "Extract", "Analyze", "Highlights", "Generate", "Ready"] as const;

interface ProcessingShowcaseProps {
  statusLabel: string;
  statusDetail?: string | null;
  activeStepIndex: number;
  isRefreshing: boolean;
  elapsedSeconds?: number | null;
  clipsHref?: string | null;
  canOpenClips?: boolean;
  onRefresh: () => void | Promise<void>;
}

function formatElapsed(seconds?: number | null) {
  if (typeof seconds !== "number" || !Number.isFinite(seconds) || seconds < 0) return "00:00";
  const total = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(total / 60);
  const remaining = total % 60;
  return `${minutes.toString().padStart(2, "0")}:${remaining.toString().padStart(2, "0")}`;
}

function stageState(index: number, active: number, canOpenClips: boolean) {
  if (canOpenClips) return "done";
  if (index < active) return "done";
  if (index === active) return "active";
  return "queued";
}

export function ProcessingShowcase({
  statusLabel,
  statusDetail,
  activeStepIndex,
  isRefreshing,
  elapsedSeconds,
  clipsHref,
  canOpenClips = false,
  onRefresh,
}: ProcessingShowcaseProps) {
  const [spinToken, setSpinToken] = useState(0);
  const [showSyncing, setShowSyncing] = useState(false);
  const syncingTimerRef = useRef<number | null>(null);
  const clampedStep = Math.max(0, Math.min(STAGE_CHIPS.length - 1, activeStepIndex));

  useEffect(() => {
    if (isRefreshing) {
      setShowSyncing(true);
      return;
    }
    if (syncingTimerRef.current != null) window.clearTimeout(syncingTimerRef.current);
    syncingTimerRef.current = window.setTimeout(() => setShowSyncing(false), 280);
  }, [isRefreshing]);

  useEffect(() => {
    return () => {
      if (syncingTimerRef.current != null) window.clearTimeout(syncingTimerRef.current);
    };
  }, []);

  const handleRefresh = async () => {
    setSpinToken((value) => value + 1);
    setShowSyncing(true);
    await Promise.resolve(onRefresh());
  };

  return (
    <motion.section
      layout
      initial={{ opacity: 0, y: 14, scale: 0.985 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -12, scale: 0.985 }}
      transition={{ duration: 0.34, ease: [0.16, 1, 0.3, 1] }}
      className="wow-processing-shell relative overflow-hidden rounded-[2rem] border border-slate-200/80 bg-white/80 p-6 shadow-[0_36px_90px_-60px_rgba(15,23,42,0.38)] backdrop-blur-xl sm:p-8"
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_16%_12%,rgba(14,165,233,0.2),transparent_36%),radial-gradient(circle_at_80%_88%,rgba(59,130,246,0.16),transparent_40%)]" />

      <div className="relative z-10 flex items-center justify-between gap-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-600">Processing</p>
        <p className="rounded-full border border-slate-300/80 bg-white/80 px-3 py-1 text-xs text-slate-600">
          {formatElapsed(elapsedSeconds)}
        </p>
      </div>

      <div className="relative z-10 mt-7">
        <div className="mx-auto wow-loader-wrap">
          <span className="wow-loader-glow" />
          <span className="wow-loader-ring" />
          <span className="wow-loader-ring wow-loader-ring-secondary" />
          <span className="wow-loader-core" />
        </div>

        <div className="mt-5 text-center">
          <AnimatePresence mode="wait">
            <motion.p
              key={statusLabel}
              initial={{ opacity: 0, y: 10, filter: "blur(8px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              exit={{ opacity: 0, y: -8, filter: "blur(6px)" }}
              transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
              className="text-[1.35rem] font-semibold tracking-[-0.02em] text-slate-950 sm:text-[1.55rem]"
            >
              {statusLabel}
            </motion.p>
          </AnimatePresence>
          <p className="mx-auto mt-2 max-w-2xl text-sm text-slate-600">{statusDetail || "This usually takes a few minutes."}</p>
        </div>

        <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
          {STAGE_CHIPS.map((stage, index) => {
            const state = stageState(index, clampedStep, canOpenClips);
            return (
              <motion.span
                key={stage}
                layout
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
                  state === "done" && "border-emerald-200/90 bg-emerald-50 text-emerald-700",
                  state === "active" && "border-sky-300/80 bg-sky-100 text-sky-800",
                  state === "queued" && "border-slate-300/80 bg-white/80 text-slate-500"
                )}
              >
                {state === "done" ? <Check className="h-3.5 w-3.5" /> : null}
                {state === "active" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
                <span>{stage}</span>
              </motion.span>
            );
          })}
        </div>

        <div className="mt-5 flex items-center justify-center gap-1.5">
          {Array.from({ length: 4 }).map((_, index) => (
            <motion.span
              key={`dot-${index}`}
              animate={{ opacity: [0.25, 1, 0.25], scale: [0.8, 1, 0.8] }}
              transition={{ duration: 1.25, repeat: Infinity, ease: "easeInOut", delay: index * 0.14 }}
              className="h-1.5 w-1.5 rounded-full bg-sky-500/70"
            />
          ))}
        </div>

        <div className="mt-7 flex flex-wrap items-center justify-center gap-3">
          <Button
            variant="outline"
            className="h-11 rounded-full border-slate-300/80 bg-white/85 px-5 text-slate-700 hover:text-slate-950"
            onClick={handleRefresh}
          >
            <motion.span
              key={spinToken}
              initial={{ rotate: 0 }}
              animate={{ rotate: 360 }}
              transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
              className="mr-2 inline-flex"
            >
              <RefreshCw className={cn("h-4 w-4", isRefreshing && "animate-spin")} />
            </motion.span>
            Refresh
          </Button>

          {clipsHref ? (
            <Button
              asChild
              className="h-11 rounded-full bg-slate-950 px-6 text-white shadow-[0_20px_34px_-24px_rgba(15,23,42,0.85)] hover:bg-slate-900"
              disabled={!canOpenClips}
            >
              <Link href={clipsHref}>Open clips</Link>
            </Button>
          ) : (
            <Button className="h-11 rounded-full bg-slate-950 px-6 text-white" disabled>
              Open clips
            </Button>
          )}

          <AnimatePresence>
            {showSyncing ? (
              <motion.span
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
                className="text-xs text-slate-600"
              >
                Syncing status...
              </motion.span>
            ) : null}
          </AnimatePresence>
        </div>
      </div>
    </motion.section>
  );
}
