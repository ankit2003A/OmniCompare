import Link from "next/link";
import { Layers } from "lucide-react";
import type { ProductGroup } from "@/lib/types";
import { inr, titleCase } from "@/lib/format";
import { imageSrc } from "@/lib/api";
import { MarketplaceBadge } from "./MarketplaceBadge";
import { Badge } from "./ui/badge";

const SUBTITLE_KEYS = ["storage", "ram", "colour", "gender", "fit", "size", "quantity", "shade"];

export function subtitleOf(attrs: Record<string, string>) {
  const seen = new Set<string>();
  return SUBTITLE_KEYS.map((k) => attrs[k]).filter((v): v is string => Boolean(v) && !seen.has(v) && Boolean(seen.add(v)))
    .map((v) => (/\d/.test(v) ? v : titleCase(v))).slice(0, 4).join(" · ");
}

export function ProductGroupCard({ g, pincode }: { g: ProductGroup; pincode?: string }) {
  const href = `/product/${g.id}${pincode ? `?pincode=${pincode}` : ""}`;
  const single = g.listing_count === 1;
  const stores = g.store_count ?? g.marketplaces.length;
  const multi = stores > 1;
  const FLAG_TEXT: Record<string, string> = { refurbished: "Refurbished", unusually_low_price: "Price unusually low — check listing", accessory: "Accessory" };
  return (
    <article className="group flex overflow-hidden rounded-card border border-line bg-white transition-shadow hover:shadow-lg sm:flex-col">
      <Link href={href} className="relative block w-28 shrink-0 self-start overflow-hidden bg-white sm:w-auto sm:self-auto">
        <div className="aspect-square">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={imageSrc(g.canonical_image)} alt={g.canonical_title} className="h-full w-full object-contain p-2 transition-transform duration-300 group-hover:scale-[1.03] sm:p-4" loading="lazy" />
        </div>
        {g.match.confidence !== null && (
          <span className="absolute left-3 top-3 hidden rounded-full bg-white/95 px-2.5 py-1 text-xs font-semibold shadow-sm sm:inline">
            {g.match.confidence}% match
          </span>
        )}
        <span className="absolute right-3 top-3 flex -space-x-1">
          {g.marketplaces.slice(0, 4).map((m) => (
            <span key={m.slug} title={m.name} className="h-5 w-5 rounded-full border-2 border-white" style={{ backgroundColor: m.brand_color }} />
          ))}
        </span>
      </Link>

      <div className="flex min-w-0 flex-1 flex-col gap-2.5 p-3 sm:gap-3 sm:p-4">
        <div>
          <Link href={href} className="line-clamp-2 text-[15px] font-semibold leading-snug hover:underline">{g.canonical_title}</Link>
          <p className="mt-1 text-xs text-muted">{subtitleOf(g.attributes) || titleCase(g.brand ?? g.category ?? "")}</p>
          {g.flags && g.flags.length > 0 && (
            <div className="mt-1.5 flex flex-wrap gap-1">
              {g.flags.map((f) => <span key={f} className="rounded-full bg-fast-bg px-2 py-0.5 text-[11px] font-medium text-fast">{FLAG_TEXT[f] ?? f}</span>)}
            </div>
          )}
        </div>

        <p className="flex items-center gap-1.5 text-sm text-muted">
          <Layers className="h-4 w-4" />
          {multi ? `Compared across ${stores} stores` : "Found at 1 store so far — open to compare all stores"}
        </p>

        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-xl bg-cheap-bg p-2.5 sm:p-3">
            <p className="text-[11px] font-medium text-cheap">{multi ? "Cheapest" : "Price"}</p>
            <p className="text-base font-bold leading-tight text-ink sm:text-lg">{g.cheapest ? inr(g.cheapest.price) : "—"}</p>
            {g.cheapest && <p className="text-xs text-cheap">{g.cheapest.marketplace.name}</p>}
          </div>
          <div className="rounded-xl bg-fast-bg p-2.5 sm:p-3">
            <p className="text-[11px] font-medium text-fast">{multi ? "Fastest" : "Delivery"}</p>
            <p className="line-clamp-2 text-sm font-bold leading-tight text-ink sm:text-base">{g.fastest ? g.fastest.deliveryText : "See store"}</p>
            {g.fastest && <p className="text-xs text-fast">{g.fastest.marketplace.name}</p>}
          </div>
        </div>

        {!single && (
          <div className="flex flex-wrap gap-1">
            {g.marketplaces.map((m) => <MarketplaceBadge key={m.slug} m={m} />)}
            {g.price_max > g.price_min && <Badge tone="outline">Save up to {inr(g.price_max - g.price_min)}</Badge>}
          </div>
        )}

        <Link href={href} className="mt-auto inline-flex h-9 items-center sm:h-10 justify-center rounded-full bg-ink text-sm font-medium text-white hover:bg-black">
          {multi ? `Compare ${stores} stores` : "Compare all stores"}
        </Link>
      </div>
    </article>
  );
}
