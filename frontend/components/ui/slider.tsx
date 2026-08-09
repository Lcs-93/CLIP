import * as React from "react";

import { cn } from "@/lib/cn";

interface SliderProps
  extends Omit<
    React.InputHTMLAttributes<HTMLInputElement>,
    "type" | "value" | "defaultValue" | "onChange"
  > {
  value: number;
  onValueChange: (nextValue: number) => void;
}

const Slider = React.forwardRef<HTMLInputElement, SliderProps>(
  ({ className, value, onValueChange, ...props }, ref) => {
    return (
      <input
        ref={ref}
        type="range"
        value={value}
        className={cn(
          "range-accent h-2 w-full cursor-pointer appearance-none rounded-full bg-muted",
          className
        )}
        onChange={(event) => onValueChange(Number(event.target.value))}
        {...props}
      />
    );
  }
);
Slider.displayName = "Slider";

export { Slider };
