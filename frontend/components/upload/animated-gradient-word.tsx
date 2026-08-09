"use client";

import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

import { cn } from "@/lib/cn";

interface AnimatedGradientWordProps {
  words: readonly string[];
  intervalMs?: number;
  className?: string;
  minWidthClassName?: string;
}

export function AnimatedGradientWord({
  words,
  intervalMs = 2400,
  className,
  minWidthClassName,
}: AnimatedGradientWordProps) {
  const [wordIndex, setWordIndex] = useState(0);
  const activeWord = useMemo(() => words[wordIndex] ?? "", [wordIndex, words]);

  useEffect(() => {
    if (words.length <= 1) return;
    const interval = window.setInterval(() => {
      setWordIndex((current) => (current + 1) % words.length);
    }, intervalMs);

    return () => {
      window.clearInterval(interval);
    };
  }, [intervalMs, words]);

  return (
    <span className={cn("relative inline-flex align-baseline", minWidthClassName)}>
      <AnimatePresence mode="wait">
        <motion.span
          key={activeWord}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.26, ease: [0.16, 1, 0.3, 1] }}
          className={cn("animated-gradient-word", className)}
        >
          {activeWord}
        </motion.span>
      </AnimatePresence>
    </span>
  );
}
