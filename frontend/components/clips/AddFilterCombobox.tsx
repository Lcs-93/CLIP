import { useEffect, useId, useMemo, useRef, useState } from "react";
import { ChevronDown, Plus } from "lucide-react";

import { FilterRule } from "@/components/clips/filter-rules";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/cn";

interface AddFilterComboboxProps {
  onAddFilter: (type: FilterRule["type"]) => void;
  className?: string;
  disabled?: boolean;
}

const FILTER_OPTIONS: Array<{ type: FilterRule["type"]; label: string; description: string }> = [
  { type: "score", label: "Score", description: "Numeric score filter." },
  { type: "duration", label: "Duration", description: "Clip duration in seconds." },
  { type: "status", label: "Status", description: "Clip processing status." },
  { type: "tag", label: "Tag / Quick", description: "Tag matching or quick preset." },
];

export function AddFilterCombobox({ onAddFilter, className, disabled }: AddFilterComboboxProps) {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState("");
  const containerRef = useRef<HTMLDivElement | null>(null);
  const listboxId = useId();

  const filteredOptions = useMemo(() => {
    const query = value.trim().toLowerCase();
    if (!query) return FILTER_OPTIONS;
    return FILTER_OPTIONS.filter(
      (option) =>
        option.label.toLowerCase().includes(query) ||
        option.description.toLowerCase().includes(query)
    );
  }, [value]);

  useEffect(() => {
    if (!open) return;

    const onPointerDown = (event: PointerEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };

    window.addEventListener("pointerdown", onPointerDown);
    return () => window.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  const addFilter = (type: FilterRule["type"]) => {
    onAddFilter(type);
    setValue("");
    setOpen(false);
  };

  return (
    <div ref={containerRef} className={cn("relative min-w-[220px]", className)}>
      <div className="relative">
        <Plus className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={value}
          disabled={disabled}
          onFocus={() => !disabled && setOpen(true)}
          onChange={(event) => {
            setValue(event.target.value);
            if (!open) setOpen(true);
          }}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              setOpen(false);
              return;
            }

            if (event.key === "Enter" && filteredOptions[0]) {
              event.preventDefault();
              addFilter(filteredOptions[0].type);
            }
          }}
          aria-label="Add filter"
          role="combobox"
          aria-expanded={open}
          aria-controls={listboxId}
          placeholder="Add filter..."
          className="h-10 pr-9 pl-9"
        />
        <button
          type="button"
          disabled={disabled}
          aria-label="Toggle filter types"
          onClick={() => !disabled && setOpen((state) => !state)}
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-muted-foreground transition hover:bg-muted/70 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50"
        >
          <ChevronDown className={cn("h-4 w-4 transition", open && "rotate-180")} />
        </button>
      </div>

      {open ? (
        <div
          id={listboxId}
          role="listbox"
          className="absolute left-0 top-[calc(100%+0.45rem)] z-50 w-full rounded-xl border border-border/70 bg-card/95 p-1 shadow-[0_18px_56px_-34px_rgba(15,23,42,0.5)] backdrop-blur-xl"
        >
          {filteredOptions.length === 0 ? (
            <p className="px-3 py-2 text-xs text-muted-foreground">No filter found.</p>
          ) : (
            filteredOptions.map((option) => (
              <button
                key={option.type}
                type="button"
                role="option"
                onClick={() => addFilter(option.type)}
                className="flex w-full items-start rounded-lg px-3 py-2 text-left transition hover:bg-muted/65"
              >
                <span className="text-sm font-medium text-foreground">{option.label}</span>
                <span className="ml-auto text-[11px] text-muted-foreground">{option.description}</span>
              </button>
            ))
          )}
        </div>
      ) : null}
    </div>
  );
}
