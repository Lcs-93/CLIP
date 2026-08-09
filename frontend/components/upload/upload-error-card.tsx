"use client";

import { AlertTriangle, RotateCcw } from "lucide-react";
import { motion } from "framer-motion";

import { Button } from "@/components/ui/button";

interface UploadErrorCardProps {
  message: string;
  canRetry: boolean;
  onRetry: () => void;
  onReset: () => void;
}

export function UploadErrorCard({ message, canRetry, onRetry, onReset }: UploadErrorCardProps) {
  return (
    <motion.section
      layout
      initial={{ opacity: 0, y: 14, scale: 0.985 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -12, scale: 0.985 }}
      transition={{ duration: 0.34, ease: [0.16, 1, 0.3, 1] }}
      className="relative overflow-hidden rounded-[2rem] border border-rose-200/80 bg-white/82 px-6 py-8 shadow-[0_34px_84px_-56px_rgba(225,29,72,0.42)] backdrop-blur-xl sm:px-8"
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_16%,rgba(244,63,94,0.16),transparent_38%),radial-gradient(circle_at_80%_84%,rgba(251,113,133,0.14),transparent_40%)]" />

      <div className="relative z-10">
        <div className="inline-flex h-12 w-12 items-center justify-center rounded-full border border-rose-200 bg-rose-100 text-rose-700 shadow-[0_12px_24px_-14px_rgba(225,29,72,0.6)]">
          <AlertTriangle className="h-6 w-6" />
        </div>

        <div className="mt-4">
          <h2 className="text-[1.45rem] font-semibold tracking-[-0.02em] text-rose-900">Upload failed</h2>
          <p className="mt-2 text-sm text-rose-800/90">{message}</p>
        </div>

        <div className="mt-5 flex flex-wrap gap-2.5">
          <Button
            onClick={onRetry}
            disabled={!canRetry}
            className="h-10 rounded-full bg-rose-600 px-5 text-white hover:bg-rose-500"
          >
            <RotateCcw className="mr-2 h-4 w-4" />
            Retry
          </Button>
          <Button variant="outline" onClick={onReset} className="h-10 rounded-full border-rose-300/80 bg-white/75 px-5 text-rose-900">
            Reset
          </Button>
        </div>
      </div>
    </motion.section>
  );
}
