"use client";

import { MoonStar, SunMedium } from "lucide-react";

import { useTheme } from "@/components/theme-provider";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";

export function ThemeToggle({ className }: { className?: string }) {
  const { resolvedTheme, toggleTheme } = useTheme();
  const isDark = resolvedTheme === "dark";

  return (
    <Button
      type="button"
      variant="outline"
      size="icon"
      className={cn("rounded-full", className)}
      onClick={toggleTheme}
      aria-label={isDark ? "Activer le theme clair" : "Activer le theme sombre"}
    >
      <SunMedium
        className={cn(
          "h-4 w-4 transition-all",
          isDark ? "scale-0 -rotate-90 opacity-0" : "scale-100 rotate-0 opacity-100"
        )}
      />
      <MoonStar
        className={cn(
          "absolute h-4 w-4 transition-all",
          isDark ? "scale-100 rotate-0 opacity-100" : "scale-0 rotate-90 opacity-0"
        )}
      />
    </Button>
  );
}
