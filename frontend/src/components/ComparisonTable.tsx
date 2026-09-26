import { ExternalLink } from "lucide-react";
import type { Listing } from "@/lib/types";
import { inr } from "@/lib/format";
import { MarketplaceBadge } from "./MarketplaceBadge";
import { Rating } from "./Rating";
import { Badge } from "./ui/badge";
import { DemoLabel } from "./DemoLabel";
import { cn } from "@/lib/utils";
import { imageSrc } from "@/lib/api";

export function ComparisonTable({ listings, cheapestId, fastestId, dense = false }: {
  listings: Listing[]; cheapestId?: number | null; fastestId?: number | null; dense?: boolean;
}) {
  const live = listings.some((l) => l.is_live);
  return (
    <>
    <ul className="space-y-3 sm:hidden">
      {listings.map((l) => {
        const cheap = l.id === cheapestId, fast = l.id === fastestId;
        return (
          <li key={l.id} className={cn("rounded-card border p-4", cheap ? "border-cheap/40 bg-cheap-bg/40" : "border-line")}>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <MarketplaceBadge m={l.marketplace} />
                <p className="mt-1 line-clamp-2 text-xs text-muted">{l.title}</p>
              </div>
              <div className="shrink-0 text-right">
                <p className={cn("text-lg font-bold", cheap && "text-cheap")}>{inr(l.price)}</p>
                {l.mrp > l.price && <p className="text-xs text-muted"><span className="line-through">{inr(l.mrp)}</span> · {Math.round(l.discount_percentage)}% off</p>}
              </div>
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
              {cheap && <Badge tone="cheap">Cheapest</Badge>}
              {fast && <Badge tone="fast">Fastest</Badge>}
              {l.delivery.deliveryDays < 90 && <span className={cn(fast ? "font-medium text-fast" : "text-muted")}>{l.delivery.deliveryText}</span>}
              {l.rating > 0 && <Rating value={l.rating} count={l.review_count} />}
            </div>
            <a href={imageSrc(l.product_url)} target="_blank" rel="noopener noreferrer"
              className="mt-3 flex h-10 w-full items-center justify-center gap-1.5 rounded-full bg-ink text-sm font-medium text-white active:bg-black">
              View on {l.marketplace.name} <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </li>
        );
      })}
    </ul>
    <div className="hidden overflow-x-auto rounded-card border border-line sm:block">
      <table className="w-full min-w-[720px] text-sm">
        <thead className="bg-surface text-left text-xs text-muted">
          <tr>
            <th className="px-4 py-3 font-medium">Marketplace</th>
            <th className="px-4 py-3 font-medium">Price</th>
            <th className="px-4 py-3 font-medium">Delivery {listings.some((l) => l.delivery?.isDemo) && <DemoLabel text="demo" />}</th>
            <th className="px-4 py-3 font-medium">Rating</th>
            {!dense && <th className="px-4 py-3 font-medium">Seller</th>}
            {!dense && !live && <th className="px-4 py-3 font-medium">Availability</th>}
            <th className="px-4 py-3" />
          </tr>
        </thead>
        <tbody>
          {listings.map((l) => {
            const cheap = l.id === cheapestId, fast = l.id === fastestId;
            return (
              <tr key={l.id} className={cn("border-t border-line", (cheap || fast) && "bg-surface/60")}>
                <td className="px-4 py-3">
                  <div className="flex flex-col gap-1">
                    <MarketplaceBadge m={l.marketplace} />
                    {!dense && <span className="line-clamp-1 max-w-[260px] text-xs text-muted" title={l.title}>{l.title}</span>}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={cn("text-base font-bold", cheap && "text-cheap")}>{inr(l.price)}</span>
                    {l.mrp > l.price && <span className="text-xs text-muted line-through">{inr(l.mrp)}</span>}
                    {l.discount_percentage > 0 && <Badge tone="default">{Math.round(l.discount_percentage)}% off</Badge>}
                    {cheap && <Badge tone="cheap">Cheapest</Badge>}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={cn("font-medium", fast && "text-fast")}>{l.delivery.deliveryDays < 90 ? l.delivery.deliveryText : "—"}</span>
                    <span className="text-xs text-muted">{l.delivery.deliveryDays === 0 || l.delivery.deliveryDays >= 90 || /\d|tomorrow|today/i.test(l.delivery.deliveryText) ? "" : `~${l.delivery.deliveryDays} day${l.delivery.deliveryDays > 1 ? "s" : ""}`}</span>
                    {fast && <Badge tone="fast">Fastest</Badge>}
                  </div>
                </td>
                <td className="px-4 py-3">{l.rating > 0 ? <Rating value={l.rating} count={l.review_count} /> : <span className="text-xs text-muted">No reviews</span>}</td>
                {!dense && <td className="px-4 py-3 text-muted">{l.seller_name}</td>}
                {!dense && !live && (
                  <td className="px-4 py-3">
                    <span className={cn("text-xs font-medium", l.availability === "in_stock" ? "text-cheap" : l.availability === "low_stock" ? "text-fast" : "text-muted")}>
                      {l.availability === "in_stock" ? "In stock" : l.availability === "low_stock" ? "Few left" : "Out of stock"}
                    </span>
                  </td>
                )}
                <td className="px-4 py-3 text-right">
                  <a href={imageSrc(l.product_url)} target="_blank" rel="noopener noreferrer"
                    className="inline-flex h-8 items-center gap-1 whitespace-nowrap rounded-full border border-line px-3 text-xs font-medium hover:bg-surface">
                    View on {l.marketplace.name} <ExternalLink className="h-3 w-3" />
                  </a>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
    </>
  );
}
