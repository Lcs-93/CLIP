import { motion } from "framer-motion";

import { cn } from "@/lib/cn";
import { ClipFilterChip } from "@/components/clips/clips-toolbar-types";

interface QuickFiltersProps {
  activeChip: ClipFilterChip;
  onChipChange: (value: ClipFilterChip) => void;
}

const QUICK_FILTERS: Array<{ id: ClipFilterChip; label: string }> = [
  { id: "best", label: "Best" },
  { id: "ready", label: "Ready" },
  { id: "short", label: "Short" },
  { id: "newest", label: "New" },
];

export function QuickFilters({ activeChip, onChipChange }: QuickFiltersProps) {
  return (
    <div className="rounded-xl border border-border/65 bg-background/55 p-1">
      <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-thin sm:pb-0">
        {QUICK_FILTERS.map((item) => {
          const active = activeChip === item.id;

          return (
            <motion.button
              key={item.id}
              type="button"
              whileTap={{ scale: 0.98 }}
              aria-pressed={active}
              onClick={() => onChipChange(active ? "all" : item.id)}
              className={cn(
                "relative whitespace-nowrap rounded-lg px-3 py-2 text-xs font-semibold uppercase tracking-[0.12em] transition",
                active
                  ? "text-primary"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {active ? (
                <motion.span
                  layoutId="clips-quick-filter-active"
                  className="absolute inset-0 -z-10 rounded-lg border border-primary/35 bg-primary/12"
                  transition={{ type: "spring", stiffness: 520, damping: 34, mass: 0.6 }}
                />
              ) : null}
              {item.label}
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}
