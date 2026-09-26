import * as React from "react";
import { cn } from "@/lib/utils";

const styles = {
  default: "bg-surface text-ink",
  cheap: "bg-cheap-bg text-cheap",
  fast: "bg-fast-bg text-fast",
  ok: "bg-cheap-bg text-cheap",
  warn: "bg-fast-bg text-fast",
  outline: "border border-line text-muted",
  accent: "bg-indigo-50 text-accent",
};

export function Badge({ className, tone = "default", ...props }: React.HTMLAttributes<HTMLSpanElement> & { tone?: keyof typeof styles }) {
  return <span className={cn("inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium", styles[tone], className)} {...props} />;
}
