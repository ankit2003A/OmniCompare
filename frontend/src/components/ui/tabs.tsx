"use client";
import * as React from "react";
import { cn } from "@/lib/utils";

export function Tabs<T extends string>({ value, onChange, items, className }: {
  value: T; onChange: (v: T) => void; items: { value: T; label: string; count?: number }[]; className?: string;
}) {
  return (
    <div role="tablist" className={cn("flex gap-1 overflow-x-auto rounded-full bg-surface p-1", className)}>
      {items.map((it) => (
        <button
          key={it.value} role="tab" aria-selected={value === it.value} onClick={() => onChange(it.value)}
          className={cn("whitespace-nowrap rounded-full px-4 py-1.5 text-sm transition-colors",
            value === it.value ? "bg-white text-ink shadow-sm" : "text-muted hover:text-ink")}
        >
          {it.label}{it.count !== undefined && <span className="ml-1.5 text-xs text-muted">{it.count}</span>}
        </button>
      ))}
    </div>
  );
}
