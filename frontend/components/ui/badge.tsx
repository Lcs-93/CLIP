import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/cn";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-medium tracking-[0.18em] uppercase transition-colors",
  {
    variants: {
      variant: {
        default: "border-primary/30 bg-primary/15 text-primary",
        secondary: "border-border bg-secondary text-secondary-foreground",
        outline: "border-border text-muted-foreground",
        success: "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-300",
        warning: "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300",
        danger: "border-destructive/30 bg-destructive/10 text-destructive",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
