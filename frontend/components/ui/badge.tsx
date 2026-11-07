import { cn } from "@/lib/utils";
import type { HTMLAttributes } from "react";

const variants = {
  default: "border-border-strong bg-surface-overlay text-text-secondary",
  success: "border-success/30 bg-success/10 text-success",
  warning: "border-warning/30 bg-warning/10 text-warning",
  danger: "border-danger/30 bg-danger/10 text-danger",
  brand: "border-brand-500/30 bg-brand-500/10 text-brand-300",
} as const;

export function Badge({
  variant = "default",
  className,
  ...props
}: HTMLAttributes<HTMLSpanElement> & { variant?: keyof typeof variants }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}
