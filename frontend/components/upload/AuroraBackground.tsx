"use client";

import { motion } from "framer-motion";

interface AuroraBackgroundProps {
  isProcessing?: boolean;
}

const PARTICLES = [
  { left: "10%", top: "24%", delay: 0 },
  { left: "22%", top: "76%", delay: 0.18 },
  { left: "38%", top: "18%", delay: 0.28 },
  { left: "58%", top: "74%", delay: 0.4 },
  { left: "74%", top: "26%", delay: 0.52 },
  { left: "88%", top: "62%", delay: 0.64 },
] as const;

export function AuroraBackground({ isProcessing = false }: AuroraBackgroundProps) {
  return (
    <div className="pointer-events-none absolute inset-0 -z-20 overflow-hidden">
      <div className="wow-aurora-veil absolute inset-0" />

      <motion.span
        className="wow-aurora-ribbon wow-aurora-ribbon-a"
        animate={isProcessing ? { opacity: [0.24, 0.4, 0.24] } : { opacity: [0.18, 0.3, 0.18] }}
        transition={{ duration: 4.2, ease: "easeInOut", repeat: Infinity }}
      />
      <motion.span
        className="wow-aurora-ribbon wow-aurora-ribbon-b"
        animate={isProcessing ? { opacity: [0.2, 0.34, 0.2] } : { opacity: [0.14, 0.28, 0.14] }}
        transition={{ duration: 4.8, ease: "easeInOut", repeat: Infinity, delay: 0.3 }}
      />
      <motion.span
        className="wow-aurora-ribbon wow-aurora-ribbon-c"
        animate={isProcessing ? { opacity: [0.16, 0.3, 0.16] } : { opacity: [0.1, 0.24, 0.1] }}
        transition={{ duration: 5.3, ease: "easeInOut", repeat: Infinity, delay: 0.5 }}
      />

      <motion.span
        className="absolute inset-0 bg-[radial-gradient(circle_at_50%_42%,rgba(56,189,248,0.14),transparent_54%)]"
        animate={isProcessing ? { opacity: [0.18, 0.4, 0.18], scale: [1, 1.04, 1] } : { opacity: 0.14, scale: 1 }}
        transition={{ duration: 2.2, ease: "easeInOut", repeat: Infinity }}
      />

      <div className="absolute inset-0">
        {PARTICLES.map((particle, index) => (
          <motion.span
            key={`p-${index}`}
            className="absolute h-1 w-1 rounded-full bg-sky-400/35"
            style={{ left: particle.left, top: particle.top }}
            animate={{ y: [0, -8, 0], opacity: [0.25, 0.7, 0.25] }}
            transition={{ duration: 3.8, repeat: Infinity, ease: "easeInOut", delay: particle.delay }}
          />
        ))}
      </div>
    </div>
  );
}
