import Link from "next/link";
import { Layers } from "lucide-react";
import type { ProductGroup } from "@/lib/types";
import { inr, titleCase } from "@/lib/format";
import { imageSrc } from "@/lib/api";
import { MarketplaceBadge } from "./MarketplaceBadge";
import { Badge } from "./ui/badge";

const SUBTITLE_KEYS = ["gender", "colour", "fit", "size", "quantity", "model", "shade"];

export function subtitleOf(attrs: Record<string, string>) {
  const seen = new Set<string>();
  return SUBTITLE_KEYS.map((k) => attrs[k]).filter((v): v is string => Boolean(v) && !seen.has(v) && Boolean(seen.add(v)))
    .map((v) => (/\d/.test(v) ? v : titleCase(v))).slice(0, 4).join(" · ");
}

export function ProductGroupCard({ g, pincode }: { g: ProductGroup; pincode?: string }) {
  const href = `/product/${g.id}${pincode ? `?pincode=${pincode}` : ""}`;
  const single = g.listing_count === 1;
  return (
    <article className="group flex flex-col overflow-hidden rounded-card border border-line bg-white transition-shadow hover:shadow-lg">
      <Link href={href} className="relative block aspect-square overflow-hidden bg-surface">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={imageSrc(g.canonical_image)} alt={g.canonical_title} className="h-full w-full object-cover" loading="lazy" />
        {g.match.confidence !== null && (
          <span className="absolute left-3 top-3 rounded-full bg-white/95 px-2.5 py-1 text-xs font-semibold shadow-sm">
            {g.match.confidence}% match
          </span>
        )}
        <span className="absolute right-3 top-3 flex -space-x-1">
          {g.marketplaces.slice(0, 4).map((m) => (
            <span key={m.slug} title={m.name} className="h-5 w-5 rounded-full border-2 border-white" style={{ backgroundColor: m.brand_color }} />
          ))}
        </span>
      </Link>

      <div className="flex flex-1 flex-col gap-3 p-4">
        <div>
          <Link href={href} className="line-clamp-2 text-[15px] font-semibold leading-snug hover:underline">{g.canonical_title}</Link>
          <p className="mt-1 text-xs text-muted">{subtitleOf(g.attributes) || g.brand || g.category}</p>
        </div>

        <p className="flex items-center gap-1.5 text-sm text-muted">
          <Layers className="h-4 w-4" />
          {single ? "1 listing found" : `${g.listing_count} listings found`}
        </p>

        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-xl bg-cheap-bg p-3">
            <p className="text-[11px] font-medium text-cheap">Cheapest</p>
            <p className="text-lg font-bold leading-tight text-ink">{g.cheapest ? inr(g.cheapest.price) : "—"}</p>
            {g.cheapest && <p className="text-xs text-cheap">{g.cheapest.marketplace.name}</p>}
          </div>
          <div className="rounded-xl bg-fast-bg p-3">
            <p className="text-[11px] font-medium text-fast">Fastest</p>
            <p className="text-lg font-bold leading-tight text-ink">{g.fastest ? g.fastest.deliveryText : "—"}</p>
            {g.fastest && <p className="text-xs text-fast">{g.fastest.marketplace.name}</p>}
          </div>
        </div>

        {!single && (
          <div className="flex flex-wrap gap-1">
            {g.marketplaces.map((m) => <MarketplaceBadge key={m.slug} m={m} />)}
            {g.price_max > g.price_min && <Badge tone="outline">Save up to {inr(g.price_max - g.price_min)}</Badge>}
          </div>
        )}

        <Link href={href} className="mt-auto inline-flex h-10 items-center justify-center rounded-full bg-ink text-sm font-medium text-white hover:bg-black">
          {single ? "View listing" : `Compare ${g.listing_count} listings`}
        </Link>
      </div>
    </article>
  );
}
