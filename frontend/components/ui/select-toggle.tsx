"use client";

import { Check } from "lucide-react";

import { cn } from "@/lib/cn";

type SelectToggleVariant = "default" | "overlay";
type SelectToggleSize = "sm" | "md";

interface SelectToggleProps {
  selected: boolean;
  onToggle: () => void;
  label: string;
  variant?: SelectToggleVariant;
  size?: SelectToggleSize;
  className?: string;
}

function sizeClasses(size: SelectToggleSize) {
  if (size === "sm") return "h-7 w-7";
  return "h-9 w-9";
}

function toneClasses(variant: SelectToggleVariant, selected: boolean) {
  if (variant === "overlay") {
    if (selected) {
      return "border-sky-300/90 bg-gradient-to-br from-sky-200 to-cyan-300 text-slate-950 shadow-[0_16px_34px_-20px_rgba(56,189,248,0.95)]";
    }
    return "border-white/45 bg-black/50 text-transparent shadow-[inset_0_1px_0_rgba(255,255,255,0.18)] hover:border-sky-300/80 hover:bg-black/65";
  }

  if (selected) {
    return "border-primary/55 bg-gradient-to-br from-primary to-primary/80 text-primary-foreground shadow-[0_16px_34px_-20px_rgba(59,130,246,0.9)]";
  }
  return "border-border/85 bg-background/85 text-transparent shadow-[inset_0_1px_0_rgba(255,255,255,0.22)] hover:border-primary/45 hover:bg-primary/12";
}

export function SelectToggle({
  selected,
  onToggle,
  label,
  variant = "default",
  size = "sm",
  className,
}: SelectToggleProps) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={selected}
      aria-label={label}
      onClick={(event) => {
        event.stopPropagation();
        onToggle();
      }}
      className={cn(
        "inline-flex items-center justify-center rounded-full border transition-all duration-200 hover:scale-[1.03] active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        sizeClasses(size),
        toneClasses(variant, selected),
        className
      )}
    >
      <Check
        className={cn(
          "h-4 w-4 transition-all duration-200",
          selected ? "scale-100 opacity-100" : "scale-75 opacity-0"
        )}
      />
    </button>
  );
}
