"use client";

import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

import { cn } from "@/lib/cn";

const DEFAULT_WORDS = ["Viral Clips", "Highlights", "Shorts", "Best Moments"] as const;

interface RainbowRotatingTitleProps {
  words?: readonly string[];
  intervalMs?: number;
  className?: string;
}

export function RainbowRotatingTitle({
  words = DEFAULT_WORDS,
  intervalMs = 2600,
  className,
}: RainbowRotatingTitleProps) {
  const [wordIndex, setWordIndex] = useState(0);
  const activeWord = useMemo(() => words[wordIndex] ?? "", [wordIndex, words]);

  useEffect(() => {
    if (words.length <= 1) return;
    const interval = window.setInterval(() => {
      setWordIndex((value) => (value + 1) % words.length);
    }, intervalMs);
    return () => window.clearInterval(interval);
  }, [intervalMs, words]);

  return (
    <motion.h1
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className={cn(
        "mx-auto max-w-5xl text-center text-[clamp(2.8rem,8vw,6.2rem)] font-semibold leading-[0.9] tracking-[-0.04em] text-slate-950 dark:text-slate-100",
        className
      )}
    >
      <span className="block">Turn videos into</span>
      <span className="mt-2 block min-h-[1.12em]">
        <span className="wow-rainbow-glow inline-flex min-w-[11ch] justify-center align-baseline">
          <AnimatePresence mode="wait">
            <motion.span
              key={activeWord}
              initial={{ opacity: 0, y: 20, filter: "blur(10px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              exit={{ opacity: 0, y: -18, filter: "blur(8px)" }}
              transition={{ duration: 0.42, ease: [0.16, 1, 0.3, 1] }}
              className="wow-rainbow-text"
            >
              {activeWord}
            </motion.span>
          </AnimatePresence>
        </span>
      </span>
    </motion.h1>
  );
}
