import type { MarketplaceRef } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Text badge in the marketplace's brand colour. Logos are intentionally not bundled (trademarked assets). */
export function MarketplaceBadge({ m, size = "sm", className }: { m: MarketplaceRef; size?: "sm" | "md"; className?: string }) {
  return (
    <span
      className={cn("inline-flex items-center gap-1.5 rounded-md font-semibold tracking-tight",
        size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-sm", className)}
      style={{ backgroundColor: `${m.brand_color}14`, color: m.brand_color }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: m.brand_color }} />
      {m.name}
    </span>
  );
}
