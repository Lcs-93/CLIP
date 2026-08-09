"use client";

import Link from "next/link";
import { Loader2, Upload, Video } from "lucide-react";
import { motion } from "framer-motion";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";

interface UploadIdleCardProps {
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

export function UploadIdleCard({
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
}: UploadIdleCardProps) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      transition={{ duration: 0.24, delay: 0.05, ease: [0.16, 1, 0.3, 1] }}
    >
      <section className="relative">
        <div
          className={cn(
            "group rounded-[1.7rem] border border-dashed border-slate-200/85 bg-[#fbfcfd]/90 px-4 py-10 text-center shadow-[0_10px_40px_-34px_rgba(15,23,42,0.28)] transition-all duration-200 sm:px-8",
            !isDragActive && "hover:border-slate-300/80 hover:ring-1 hover:ring-slate-300/45",
            isDragActive && !disabled && "border-primary/45 bg-cyan-50/60 ring-1 ring-primary/25",
            disabled && "cursor-not-allowed opacity-65"
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
          <span className="mx-auto inline-flex h-11 w-11 items-center justify-center rounded-full border border-slate-300/80 bg-slate-50 text-slate-700 transition-transform duration-300 group-hover:scale-[1.03]">
            <Upload className="h-5 w-5" />
          </span>
          <h2 className="mt-4 text-lg font-semibold tracking-tight text-slate-900 sm:text-xl">Drop your video here</h2>
          <p className="mt-1 text-sm text-slate-500">or click to browse local files</p>

          <div className="mt-6 flex flex-wrap items-center justify-center gap-2.5">
            <Button
              className="rounded-full bg-slate-900 px-5 text-slate-50 transition-transform active:scale-[0.98] hover:bg-slate-800"
              onClick={(event) => {
                event.stopPropagation();
                onOpenPicker();
              }}
              disabled={disabled}
            >
              Upload video
            </Button>

            <Button asChild variant="ghost" className="rounded-full text-slate-500 hover:text-slate-900">
              <Link
                href={clipsHref}
                onClick={(event) => {
                  event.stopPropagation();
                }}
              >
                Go to Clips
              </Link>
            </Button>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-center gap-3 text-xs text-slate-500">
          <span className="inline-flex items-center gap-1">
            <Video className="h-3.5 w-3.5" />
            mp4, mov, mkv and common formats
          </span>
          <span className="hidden h-1 w-1 rounded-full bg-slate-300 sm:inline-flex" />
          <span>Usually 2-6 minutes</span>
        </div>

        {resumeAvailable ? (
          <div className="mt-3 text-center">
            <button
              type="button"
              onClick={onResume}
              disabled={isResuming}
              className="inline-flex items-center gap-1 text-xs text-slate-500 underline-offset-2 transition hover:text-slate-800 hover:underline disabled:cursor-not-allowed disabled:opacity-70"
            >
              {isResuming ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
              Resume last processing
            </button>
          </div>
        ) : null}
      </section>
    </motion.div>
  );
}
