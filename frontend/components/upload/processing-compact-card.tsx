"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Check, Loader2, RefreshCw } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";

const STEP_CHIPS = ["Upload", "Audio", "Analyze", "Select", "Render"] as const;

interface ProcessingCompactCardProps {
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

function chipState(index: number, activeStep: number, total: number) {
  if (activeStep >= total) return "done";
  if (index < activeStep) return "done";
  if (index === activeStep) return "active";
  return "queued";
}

export function ProcessingCompactCard({
  statusLabel,
  statusDetail,
  activeStepIndex,
  isRefreshing,
  elapsedSeconds,
  clipsHref,
  canOpenClips = false,
  onRefresh,
}: ProcessingCompactCardProps) {
  const [spinToken, setSpinToken] = useState(0);
  const [flashToken, setFlashToken] = useState(0);
  const [showUpdating, setShowUpdating] = useState(false);
  const updatingTimerRef = useRef<number | null>(null);
  const activeStep = Math.max(0, Math.min(STEP_CHIPS.length, activeStepIndex));

  useEffect(() => {
    if (isRefreshing) {
      setShowUpdating(true);
      return;
    }
    if (updatingTimerRef.current != null) window.clearTimeout(updatingTimerRef.current);
    updatingTimerRef.current = window.setTimeout(() => {
      setShowUpdating(false);
    }, 200);
  }, [isRefreshing]);

  useEffect(() => {
    return () => {
      if (updatingTimerRef.current != null) window.clearTimeout(updatingTimerRef.current);
    };
  }, []);

  const handleRefreshClick = async () => {
    setSpinToken((value) => value + 1);
    setFlashToken((value) => value + 1);
    setShowUpdating(true);
    await Promise.resolve(onRefresh());
  };

  return (
    <motion.section
      layout
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
      className="relative overflow-hidden rounded-[1.7rem] border border-slate-200/85 bg-[#fbfcfd]/92 px-5 py-6 shadow-[0_10px_40px_-34px_rgba(15,23,42,0.28)] sm:px-7"
    >
      <AnimatePresence>
        {flashToken > 0 ? (
          <motion.span
            key={flashToken}
            initial={{ opacity: 0 }}
            animate={{ opacity: [0, 0.55, 0] }}
            transition={{ duration: 0.34, ease: [0.16, 1, 0.3, 1] }}
            className="pointer-events-none absolute inset-0 bg-cyan-100/65"
          />
        ) : null}
      </AnimatePresence>

      <div className="relative z-10 flex items-center justify-between gap-4">
        <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-slate-500">Processing</p>
        <p className="text-xs text-slate-500">{formatElapsed(elapsedSeconds)}</p>
      </div>

      <div className="relative z-10 mt-5 space-y-4">
        <div className="mx-auto flex h-14 w-14 items-center justify-center">
          <span className="relative inline-flex h-full w-full rounded-full border border-slate-300/80 bg-slate-50">
            <motion.span
              className="absolute inset-0 rounded-full border border-transparent border-t-primary/85 border-r-primary/45"
              animate={{ rotate: 360 }}
              transition={{ duration: 1.35, ease: "linear", repeat: Infinity }}
            />
          </span>
        </div>

        <div className="space-y-1 text-center">
          <AnimatePresence mode="wait">
            <motion.p
              key={statusLabel}
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
              transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
              className="text-base font-medium text-slate-900 sm:text-lg"
            >
              {statusLabel}
            </motion.p>
          </AnimatePresence>
          <p className="mx-auto max-w-xl text-xs text-slate-500">{statusDetail || "Usually takes a few minutes."}</p>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-2.5">
          {STEP_CHIPS.map((chip, index) => {
            const state = chipState(index, activeStep, STEP_CHIPS.length);
            return (
              <span
                key={chip}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs transition-all duration-200",
                  state === "done" && "border-slate-300/80 bg-slate-100 text-slate-600",
                  state === "active" && "border-primary/35 bg-primary/10 text-primary",
                  state === "queued" && "border-slate-200/90 bg-white text-slate-500"
                )}
              >
                {state === "done" ? <Check className="h-3.5 w-3.5" /> : null}
                {state === "active" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
                <span>{chip}</span>
              </span>
            );
          })}
        </div>

        <div className="flex flex-wrap items-center justify-center gap-2.5 pt-1">
          <Button variant="outline" className="rounded-full border-slate-300" onClick={handleRefreshClick}>
            <motion.span
              key={spinToken}
              initial={{ rotate: 0 }}
              animate={{ rotate: 360 }}
              transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
              className="mr-2 inline-flex"
            >
              <RefreshCw className={cn("h-4 w-4", isRefreshing && "animate-spin")} />
            </motion.span>
            Refresh status
          </Button>

          <AnimatePresence>
            {showUpdating ? (
              <motion.span
                initial={{ opacity: 0, y: 3 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -3 }}
                transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
                className="text-xs text-slate-500"
              >
                Updating...
              </motion.span>
            ) : null}
          </AnimatePresence>

          {canOpenClips && clipsHref ? (
            <Button asChild className="rounded-full bg-slate-900 text-slate-50 hover:bg-slate-800">
              <Link href={clipsHref}>Open clips</Link>
            </Button>
          ) : (
            <Button className="rounded-full bg-slate-900 text-slate-50 hover:bg-slate-800" disabled>
              Open clips
            </Button>
          )}
        </div>
      </div>
    </motion.section>
  );
}
