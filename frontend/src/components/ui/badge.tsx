import type { ReactNode } from "react";
import { cn } from "../../lib/utils";

type BadgeProps = {
  children: ReactNode;
  tone?: "default" | "ok" | "warn" | "error";
  className?: string;
};

export function Badge({ children, tone = "default", className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex h-6 items-center rounded-sm border px-2 text-xs font-medium",
        tone === "default" && "border-border bg-muted text-muted-foreground",
        tone === "ok" && "border-emerald-200 bg-emerald-50 text-emerald-800",
        tone === "warn" && "border-amber-200 bg-amber-50 text-amber-800",
        tone === "error" && "border-red-200 bg-red-50 text-red-800",
        className,
      )}
    >
      {children}
    </span>
  );
}
