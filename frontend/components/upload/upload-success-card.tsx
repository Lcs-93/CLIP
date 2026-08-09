"use client";

import Link from "next/link";
import { Check } from "lucide-react";
import { motion } from "framer-motion";

import { Button } from "@/components/ui/button";

interface UploadSuccessCardProps {
  clipsHref: string;
  redirectSeconds: number;
}

export function UploadSuccessCard({ clipsHref, redirectSeconds }: UploadSuccessCardProps) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
    >
      <section className="rounded-[1.7rem] border border-emerald-200/70 bg-[#fbfcfd]/92 px-6 py-8 text-center shadow-[0_10px_40px_-34px_rgba(15,23,42,0.28)]">
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
          className="mx-auto inline-flex h-11 w-11 items-center justify-center rounded-full border border-emerald-200 bg-emerald-50 text-emerald-700"
        >
          <Check className="h-5 w-5" />
        </motion.div>

        <div className="mt-4 space-y-1.5">
          <h2 className="text-2xl font-semibold tracking-tight text-slate-900">Your clips are ready</h2>
          <p className="text-sm text-slate-500">Redirecting in {Math.max(1, redirectSeconds)}s...</p>
        </div>

        <div className="mt-5">
          <Button asChild className="rounded-full bg-slate-900 px-6 text-slate-50 hover:bg-slate-800">
            <Link href={clipsHref}>Open clips</Link>
          </Button>
        </div>
      </section>
    </motion.div>
  );
}
