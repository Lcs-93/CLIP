import * as React from "react";

import { cn } from "@/lib/cn";

export interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: number;
}

const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(
  ({ className, value = 0, ...props }, ref) => {
    const clamped = Math.min(100, Math.max(0, value));
    return (
      <div
        ref={ref}
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={clamped}
        className={cn("relative h-2 w-full overflow-hidden rounded-full bg-muted/80", className)}
        {...props}
      >
        <div
          className="h-full w-full origin-left rounded-full bg-gradient-to-r from-primary via-chart-1 to-chart-2 transition-transform duration-500 ease-out"
          style={{ transform: `scaleX(${clamped / 100})` }}
        />
      </div>
    );
  }
);
Progress.displayName = "Progress";

export { Progress };
