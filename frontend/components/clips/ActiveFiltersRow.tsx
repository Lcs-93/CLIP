import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { ClipFilterChip, ClipSortOption } from "@/components/clips/clips-toolbar-types";

interface ActiveFiltersRowProps {
  search: string;
  activeChip: ClipFilterChip;
  minScore: number;
  sort: ClipSortOption;
  onSearchChange: (value: string) => void;
  onChipChange: (value: ClipFilterChip) => void;
  onMinScoreChange: (value: number) => void;
  onSortChange: (value: ClipSortOption) => void;
  onReset: () => void;
}

const CHIP_LABELS: Record<Exclude<ClipFilterChip, "all">, string> = {
  best: "Best",
  newest: "New",
  ready: "Ready",
  short: "Short",
  medium: "Medium",
  long: "Long",
};

const SORT_LABELS: Record<ClipSortOption, string> = {
  "score-desc": "Score high first",
  "duration-asc": "Shortest first",
  "duration-desc": "Longest first",
  "date-desc": "Newest date",
};

export function ActiveFiltersRow({
  search,
  activeChip,
  minScore,
  sort,
  onSearchChange,
  onChipChange,
  onMinScoreChange,
  onSortChange,
  onReset,
}: ActiveFiltersRowProps) {
  const searchValue = search.trim();

  const pills: Array<{ id: string; label: string; onRemove: () => void }> = [];

  if (activeChip !== "all") {
    pills.push({
      id: "chip",
      label: CHIP_LABELS[activeChip],
      onRemove: () => onChipChange("all"),
    });
  }

  if (minScore > 0) {
    pills.push({
      id: "score",
      label: `Score >= ${minScore}`,
      onRemove: () => onMinScoreChange(0),
    });
  }

  if (sort !== "score-desc") {
    pills.push({
      id: "sort",
      label: SORT_LABELS[sort],
      onRemove: () => onSortChange("score-desc"),
    });
  }

  if (searchValue.length > 0) {
    pills.push({
      id: "search",
      label: `Search: ${searchValue}`,
      onRemove: () => onSearchChange(""),
    });
  }

  return (
    <AnimatePresence initial={false}>
      {pills.length > 0 ? (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
          className="flex flex-wrap items-center gap-2 rounded-xl border border-border/65 bg-background/55 px-3 py-2"
        >
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Active filters
          </p>

          <div className="flex flex-wrap gap-1.5">
            {pills.map((pill) => (
              <span
                key={pill.id}
                className={cn(
                  "inline-flex items-center gap-1 rounded-full border border-primary/30 bg-primary/10 px-2.5 py-1",
                  "text-[11px] font-semibold uppercase tracking-[0.11em] text-primary"
                )}
              >
                {pill.label}
                <button
                  type="button"
                  aria-label={`Remove ${pill.label}`}
                  onClick={pill.onRemove}
                  className="rounded-full p-0.5 text-primary/80 transition hover:bg-primary/14 hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>

          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="ml-auto h-7 rounded-full px-3 text-[11px] uppercase tracking-[0.11em]"
            onClick={onReset}
          >
            Clear all
          </Button>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
