"use client";

import Link from "next/link";
import { Check } from "lucide-react";
import { motion } from "framer-motion";

import { Button } from "@/components/ui/button";

interface SuccessStateProps {
  clipsHref: string;
  redirectSeconds: number;
}

export function SuccessState({ clipsHref, redirectSeconds }: SuccessStateProps) {
  return (
    <motion.section
      layout
      initial={{ opacity: 0, y: 14, scale: 0.985 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -12, scale: 0.985 }}
      transition={{ duration: 0.34, ease: [0.16, 1, 0.3, 1] }}
      className="relative overflow-hidden rounded-[2rem] border border-emerald-200/80 bg-white/82 px-6 py-10 text-center shadow-[0_36px_86px_-56px_rgba(5,150,105,0.42)] backdrop-blur-xl sm:px-8"
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_24%_14%,rgba(16,185,129,0.18),transparent_36%),radial-gradient(circle_at_76%_86%,rgba(52,211,153,0.16),transparent_38%)]" />

      <div className="relative z-10">
        <div className="mx-auto flex h-20 w-20 items-center justify-center">
          <motion.span
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: [0, 0.85, 0], scale: [0.8, 1.18, 1.28] }}
            transition={{ duration: 0.65, ease: "easeOut" }}
            className="absolute h-20 w-20 rounded-full border border-emerald-300/80"
          />
          <motion.span
            initial={{ opacity: 0, scale: 0.6, rotate: -6 }}
            animate={{ opacity: 1, scale: 1, rotate: 0 }}
            transition={{ duration: 0.42, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
            className="inline-flex h-14 w-14 items-center justify-center rounded-full border border-emerald-200 bg-emerald-100 text-emerald-700 shadow-[0_16px_34px_-20px_rgba(5,150,105,0.6)]"
          >
            <Check className="h-7 w-7" />
          </motion.span>
        </div>

        <h2 className="mt-4 text-[2rem] font-semibold tracking-[-0.03em] text-slate-950 sm:text-[2.25rem]">Clips ready</h2>
        <p className="mt-2 text-sm text-slate-600">Opening clips in {Math.max(1, redirectSeconds)}s...</p>

        <div className="mt-6">
          <Button
            asChild
            className="h-11 rounded-full bg-slate-950 px-6 text-white shadow-[0_20px_36px_-24px_rgba(15,23,42,0.85)] hover:bg-slate-900"
          >
            <Link href={clipsHref}>Open clips</Link>
          </Button>
        </div>
      </div>
    </motion.section>
  );
}
