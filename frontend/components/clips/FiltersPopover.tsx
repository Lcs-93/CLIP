import { motion } from "framer-motion";
import { SlidersHorizontal } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { cn } from "@/lib/cn";
import { ClipFilterChip, ClipSortOption } from "@/components/clips/clips-toolbar-types";

interface FiltersPopoverProps {
  open: boolean;
  isMobile: boolean;
  activeChip: ClipFilterChip;
  minScore: number;
  sort: ClipSortOption;
  onOpenChange: (open: boolean) => void;
  onChipChange: (value: ClipFilterChip) => void;
  onMinScoreChange: (value: number) => void;
  onSortChange: (value: ClipSortOption) => void;
  onReset: () => void;
}

const DURATION_ITEMS: Array<{ id: ClipFilterChip; label: string }> = [
  { id: "short", label: "Short" },
  { id: "medium", label: "Medium" },
  { id: "long", label: "Long" },
];

const STATUS_ITEMS: Array<{ id: ClipFilterChip; label: string }> = [
  { id: "ready", label: "Ready" },
  { id: "newest", label: "New" },
  { id: "best", label: "Best" },
];

function SegmentedButtons({
  items,
  active,
  onSelect,
}: {
  items: Array<{ id: ClipFilterChip; label: string }>;
  active: ClipFilterChip;
  onSelect: (value: ClipFilterChip) => void;
}) {
  return (
    <div className="grid grid-cols-3 gap-1 rounded-lg border border-border/65 bg-background/55 p-1">
      {items.map((item) => {
        const selected = active === item.id;
        return (
          <button
            key={item.id}
            type="button"
            aria-pressed={selected}
            onClick={() => onSelect(selected ? "all" : item.id)}
            className={cn(
              "rounded-md px-2 py-2 text-[11px] font-semibold uppercase tracking-[0.1em] transition",
              selected
                ? "border border-primary/35 bg-primary/12 text-primary"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            {item.label}
          </button>
        );
      })}
    </div>
  );
}

function FiltersPanelBody({
  activeChip,
  minScore,
  sort,
  onChipChange,
  onMinScoreChange,
  onSortChange,
  onReset,
  onApply,
}: {
  activeChip: ClipFilterChip;
  minScore: number;
  sort: ClipSortOption;
  onChipChange: (value: ClipFilterChip) => void;
  onMinScoreChange: (value: number) => void;
  onSortChange: (value: ClipSortOption) => void;
  onReset: () => void;
  onApply: () => void;
}) {
  return (
    <div className="space-y-4">
      <section className="space-y-2">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Duration</p>
        <SegmentedButtons items={DURATION_ITEMS} active={activeChip} onSelect={onChipChange} />
      </section>

      <section className="space-y-2">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Score</p>
        <div className="rounded-xl border border-border/65 bg-background/55 p-3">
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-medium text-foreground">Min score</p>
            <Input
              aria-label="Minimum score"
              type="number"
              min={0}
              max={100}
              value={minScore}
              onChange={(event) => {
                const parsed = Number(event.target.value);
                if (!Number.isFinite(parsed)) {
                  onMinScoreChange(0);
                  return;
                }
                onMinScoreChange(Math.max(0, Math.min(100, Math.round(parsed))));
              }}
              className="h-8 w-[92px] rounded-md px-2 text-xs"
            />
          </div>
          <Slider
            aria-label="Minimum score slider"
            min={0}
            max={100}
            step={1}
            value={minScore}
            onValueChange={onMinScoreChange}
            className="mt-3 h-8"
          />
        </div>
      </section>

      <section className="space-y-2">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Status</p>
        <SegmentedButtons items={STATUS_ITEMS} active={activeChip} onSelect={onChipChange} />
      </section>

      <section className="space-y-2">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Sort</p>
        <select
          aria-label="Sort clips"
          value={sort}
          onChange={(event) => onSortChange(event.target.value as ClipSortOption)}
          className="h-10 w-full rounded-lg border border-input bg-background/75 px-3 text-sm text-foreground outline-none transition focus-visible:ring-2 focus-visible:ring-ring"
        >
          <option value="score-desc">Score (high first)</option>
          <option value="duration-asc">Duration (short first)</option>
          <option value="duration-desc">Duration (long first)</option>
          <option value="date-desc">Date (newest first)</option>
        </select>
      </section>

      <div className="flex justify-end gap-2 border-t border-border/65 pt-3">
        <Button type="button" variant="outline" className="rounded-lg" onClick={onReset}>
          Reset
        </Button>
        <Button type="button" className="rounded-lg" onClick={onApply}>
          Apply
        </Button>
      </div>
    </div>
  );
}

export function FiltersPopover({
  open,
  isMobile,
  activeChip,
  minScore,
  sort,
  onOpenChange,
  onChipChange,
  onMinScoreChange,
  onSortChange,
  onReset,
}: FiltersPopoverProps) {
  if (isMobile) {
    return (
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent
          side="bottom"
          className="h-[82vh] rounded-t-[1.2rem] border-x-0 border-b-0 border-t border-border/70 bg-background/96 p-4"
        >
          <SheetHeader>
            <SheetTitle className="inline-flex items-center gap-2">
              <SlidersHorizontal className="h-4 w-4" />
              Advanced filters
            </SheetTitle>
            <SheetDescription>Fine tune duration, score, status and sorting.</SheetDescription>
          </SheetHeader>

          <div className="mt-4 h-[calc(82vh-8rem)] overflow-y-auto pb-6">
            <FiltersPanelBody
              activeChip={activeChip}
              minScore={minScore}
              sort={sort}
              onChipChange={onChipChange}
              onMinScoreChange={onMinScoreChange}
              onSortChange={onSortChange}
              onReset={onReset}
              onApply={() => onOpenChange(false)}
            />
          </div>
        </SheetContent>
      </Sheet>
    );
  }

  if (!open) return null;

  return (
    <>
      <button
        type="button"
        aria-label="Close advanced filters"
        className="fixed inset-0 z-40 cursor-default"
        onClick={() => onOpenChange(false)}
      />

      <motion.div
        initial={{ opacity: 0, y: 8, scale: 0.985 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -6, scale: 0.985 }}
        transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
        className="absolute right-0 top-[calc(100%+0.55rem)] z-50 w-[min(94vw,420px)] rounded-xl border border-border/70 bg-card/92 p-4 shadow-[0_24px_80px_-52px_rgba(15,23,42,0.64)] backdrop-blur-xl"
        role="dialog"
        aria-label="Advanced filters"
      >
        <p className="mb-3 inline-flex items-center gap-2 text-sm font-semibold text-foreground">
          <SlidersHorizontal className="h-4 w-4" />
          Advanced filters
        </p>
        <FiltersPanelBody
          activeChip={activeChip}
          minScore={minScore}
          sort={sort}
          onChipChange={onChipChange}
          onMinScoreChange={onMinScoreChange}
          onSortChange={onSortChange}
          onReset={onReset}
          onApply={() => onOpenChange(false)}
        />
      </motion.div>
    </>
  );
}
