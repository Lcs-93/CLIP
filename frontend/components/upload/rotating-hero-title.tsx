"use client";

import { motion } from "framer-motion";

import { AnimatedGradientWord } from "@/components/upload/animated-gradient-word";

const ROTATING_WORDS = ["clips", "highlights", "shorts", "viral clips"] as const;

export function RotatingHeroTitle() {
  return (
    <motion.section
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.36, ease: [0.16, 1, 0.3, 1] }}
      className="space-y-5"
    >
      <p className="font-sans text-[11px] font-medium uppercase tracking-[0.18em] text-slate-500">Upload Flow</p>

      <h1 className="max-w-4xl font-sans text-[2.05rem] font-semibold leading-[0.98] tracking-[-0.035em] text-slate-900 sm:text-[4rem]">
        Upload a video. Get{" "}
        <AnimatedGradientWord words={ROTATING_WORDS} intervalMs={2500} minWidthClassName="min-w-[8.8ch]" />
        . Export.
      </h1>

      <motion.p
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
        className="max-w-2xl text-sm text-slate-600 sm:text-[15px]"
      >
        Upload once. We'll detect highlights and generate clips automatically.
      </motion.p>
    </motion.section>
  );
}
