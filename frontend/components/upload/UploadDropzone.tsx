"use client";

import Link from "next/link";
import { Loader2, Sparkles, Upload, Video } from "lucide-react";
import { motion } from "framer-motion";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";

interface UploadDropzoneProps {
  isDragActive: boolean;
  isResuming?: boolean;
  disabled?: boolean;
  clipsHref: string;
  resumeAvailable?: boolean;
  onResume?: () => void;
  onOpenPicker: () => void;
  onDragEnter: (event: React.DragEvent<HTMLDivElement>) => void;
  onDragOver: (event: React.DragEvent<HTMLDivElement>) => void;
  onDragLeave: (event: React.DragEvent<HTMLDivElement>) => void;
  onDrop: (event: React.DragEvent<HTMLDivElement>) => void;
}

export function UploadDropzone({
  isDragActive,
  isResuming = false,
  disabled = false,
  clipsHref,
  resumeAvailable = false,
  onResume,
  onOpenPicker,
  onDragEnter,
  onDragOver,
  onDragLeave,
  onDrop,
}: UploadDropzoneProps) {
  return (
    <motion.section
      layout
      initial={{ opacity: 0, y: 14, scale: 0.985 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -12, scale: 0.985 }}
      transition={{ duration: 0.34, ease: [0.16, 1, 0.3, 1] }}
      className={cn("wow-upload-shell border border-slate-200/75 p-4 dark:border-slate-700/70 sm:p-5", isDragActive && "wow-upload-active")}
    >
      <div
        className={cn(
          "relative overflow-hidden rounded-[1.65rem] border-2 border-dashed px-5 py-12 text-center transition-all duration-300 sm:px-10",
          isDragActive
            ? "border-cyan-400/75 bg-cyan-100/50 shadow-[0_0_0_1px_rgba(14,165,233,0.24),0_30px_70px_-44px_rgba(14,165,233,0.5)] dark:border-cyan-400/60 dark:bg-cyan-500/10 dark:shadow-[0_0_0_1px_rgba(34,211,238,0.3),0_28px_68px_-44px_rgba(8,47,73,0.68)]"
            : "border-slate-300/85 bg-white/58 hover:border-sky-300/75 hover:bg-white/72 dark:border-slate-700/85 dark:bg-slate-950/45 dark:hover:border-cyan-500/45 dark:hover:bg-slate-900/62",
          disabled && "cursor-not-allowed opacity-70"
        )}
        onDragEnter={onDragEnter}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={disabled ? undefined : onOpenPicker}
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-disabled={disabled}
        onKeyDown={(event) => {
          if (disabled) return;
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            onOpenPicker();
          }
        }}
      >
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_18%,rgba(56,189,248,0.2),transparent_34%),radial-gradient(circle_at_82%_80%,rgba(59,130,246,0.15),transparent_36%)]" />

        <div className="relative z-10 mx-auto max-w-2xl">
          <motion.span
            animate={isDragActive ? { scale: [1, 1.05, 1], rotate: [0, 2, -2, 0] } : { scale: 1, rotate: 0 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="mx-auto inline-flex h-14 w-14 items-center justify-center rounded-2xl border border-slate-300/80 bg-white/85 text-slate-900 shadow-[0_16px_40px_-28px_rgba(15,23,42,0.55)] dark:border-slate-600/70 dark:bg-slate-900/80 dark:text-slate-100"
          >
            <Upload className="h-6 w-6" />
          </motion.span>

          <h2 className="mt-5 text-[1.65rem] font-semibold tracking-[-0.02em] text-slate-950 dark:text-slate-100 sm:text-[2rem]">Drop video</h2>

          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            <Button
              className="h-11 rounded-full bg-slate-950 px-6 text-[0.95rem] text-white shadow-[0_18px_34px_-24px_rgba(15,23,42,0.85)] transition-all hover:-translate-y-0.5 hover:bg-slate-900"
              onClick={(event) => {
                event.stopPropagation();
                onOpenPicker();
              }}
              disabled={disabled}
            >
              Upload video
            </Button>
            <Button
              asChild
              variant="ghost"
              className="h-11 rounded-full border border-slate-300/80 bg-white/70 px-5 text-slate-700 hover:bg-white hover:text-slate-950 dark:border-slate-600/70 dark:bg-slate-900/70 dark:text-slate-300 dark:hover:bg-slate-900 dark:hover:text-slate-100"
            >
              <Link
                href={clipsHref}
                onClick={(event) => {
                  event.stopPropagation();
                }}
              >
                Open clips
              </Link>
            </Button>
          </div>

          <div className="mt-6 flex flex-wrap items-center justify-center gap-3 text-xs text-slate-600 dark:text-slate-300">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-300/70 bg-white/75 px-3 py-1.5 dark:border-slate-600/65 dark:bg-slate-900/75">
              <Video className="h-3.5 w-3.5" />
              MP4, MOV, MKV
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-300/70 bg-white/75 px-3 py-1.5 dark:border-slate-600/65 dark:bg-slate-900/75">
              <Sparkles className="h-3.5 w-3.5" />
              Fast AI processing
            </span>
          </div>
        </div>
      </div>

      {resumeAvailable ? (
        <div className="mt-4 flex justify-center">
          <button
            type="button"
            onClick={onResume}
            disabled={isResuming}
            className="inline-flex items-center gap-1.5 rounded-full border border-slate-300/70 bg-white/75 px-4 py-2 text-xs font-medium text-slate-600 transition-colors hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-65 dark:border-slate-600/65 dark:bg-slate-900/75 dark:text-slate-300 dark:hover:text-slate-100"
          >
            {isResuming ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
            Resume last processing
          </button>
        </div>
      ) : null}
    </motion.section>
  );
}
