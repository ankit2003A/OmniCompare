"use client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ArrowLeft, MapPin } from "lucide-react";
import { api, imageSrc } from "@/lib/api";
import type { Listing, ProductDetail } from "@/lib/types";
import { inr, titleCase } from "@/lib/format";
import { ComparisonTable } from "@/components/ComparisonTable";
import { MatchExplanation } from "@/components/MatchExplanation";
import { ProductGroupCard, subtitleOf } from "@/components/ProductGroupCard";
import { SortControl } from "@/components/SortControl";
import { MarketplaceBadge } from "@/components/MarketplaceBadge";
import { DemoLabel } from "@/components/DemoLabel";
import { SearchingAnimation } from "@/components/SearchingAnimation";
import { Tabs } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { usePincode } from "@/lib/usePincode";
import { cn } from "@/lib/utils";

type Tab = "overview" | "all" | "exact" | "similar";
const HIDE = new Set(["brand", "category"]);

function sortListings(ls: Listing[], sort: string) {
  const c = [...ls];
  switch (sort) {
    case "price_desc": return c.sort((a, b) => b.price - a.price);
    case "delivery_fastest": return c.sort((a, b) => Number(!a.delivery.available) - Number(!b.delivery.available) || a.delivery.deliveryDays - b.delivery.deliveryDays || a.price - b.price);
    case "delivery_slowest": return c.sort((a, b) => b.delivery.deliveryDays - a.delivery.deliveryDays);
    case "rating_desc": return c.sort((a, b) => b.rating - a.rating);
    case "rating_asc": return c.sort((a, b) => a.rating - b.rating);
    case "discount_desc": return c.sort((a, b) => b.discount_percentage - a.discount_percentage);
    case "relevance": return c.sort((a, b) => (b.relevance ?? b.rating) - (a.relevance ?? a.rating));
    default: return c.sort((a, b) => a.price - b.price);
  }
}

export function ProductDetailView({ id }: { id: string }) {
  const params = useSearchParams();
  const { pincode, setPincode } = usePincode(params.get("pincode"));
  const [data, setData] = useState<ProductDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("overview");
  const [sort, setSort] = useState("price_asc");
  const [image, setImage] = useState<string | null>(null);
  const [mkt, setMkt] = useState<string | null>(null);

  useEffect(() => {
    api.product(id, pincode || undefined).then((d) => { setData(d); setImage(d.images[0] ?? d.canonical_image); })
      .catch((e) => setError(String(e.message ?? e)));
  }, [id, pincode]);

  const listings = useMemo(() => data ? sortListings(data.listings.filter((l) => !mkt || l.marketplace.slug === mkt), sort) : [], [data, sort, mkt]);

  if (error) return (
    <div className="mx-auto max-w-xl px-4 py-16 text-center">
      <p className="text-lg font-semibold">{error.startsWith("404") ? "This price comparison has expired" : "Couldn’t load this product right now"}</p>
      <p className="mt-2 text-sm text-muted">{error.startsWith("404") ? "Prices change often, so comparisons are refreshed regularly. Search again to see the latest prices." : "Our price service may be waking up. Please try again in a few seconds."}</p>
      <div className="mt-5 flex justify-center gap-2">
        <button onClick={() => history.back()} className="rounded-full border border-line px-4 py-2 text-sm font-medium hover:bg-surface">Back</button>
        <Link href="/" className="rounded-full bg-ink px-4 py-2 text-sm font-medium text-white hover:bg-black">New search</Link>
      </div>
    </div>
  );
  if (!data) return <div className="mx-auto max-w-7xl px-4 py-6"><SearchingAnimation query="this product" title="Comparing every store for" skeletons={0} /></div>;

  const attrs = Object.entries(data.attributes).filter(([k]) => !HIDE.has(k));
  const exactCount = data.listing_count;
  const similarCount = data.similar_products.length;

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <button onClick={() => history.back()} className="inline-flex items-center gap-1 text-sm text-muted hover:text-ink"><ArrowLeft className="h-4 w-4" /> Back to results</button>

      {/* Product header */}
      <div className="mt-4 grid gap-8 lg:grid-cols-[minmax(0,420px)_1fr]">
        <div>
          <div className="aspect-square overflow-hidden rounded-card border border-line bg-surface">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            {image && <img src={imageSrc(image)} alt={data.canonical_title} className="h-full w-full bg-white object-contain p-6" />}
          </div>
          {data.images.length > 1 && (
            <div className="mt-3 flex gap-2 overflow-x-auto">
              {data.images.map((src) => (
                <button key={src} onClick={() => setImage(src)} className={cn("h-16 w-16 shrink-0 overflow-hidden rounded-xl border-2", image === src ? "border-ink" : "border-line")}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={imageSrc(src)} alt="" className="h-full w-full object-cover" />
                </button>
              ))}
            </div>
          )}
        </div>

        <div>
          <div className="flex flex-wrap items-center gap-2 text-sm text-muted">
            {data.brand && <span className="font-medium text-ink">{titleCase(data.brand)}</span>}
            {data.category && <Badge tone="outline">{titleCase(data.category)}</Badge>}
            {data.match.confidence !== null && <Badge tone="accent">{data.match.confidence}% match</Badge>}
          </div>
          <h1 className="mt-2 text-2xl font-bold leading-tight tracking-tight sm:text-3xl">{data.canonical_title}</h1>
          <p className="mt-1 text-sm text-muted">{subtitleOf(data.attributes)}</p>

          <div className={cn("mt-5 grid gap-3 sm:max-w-md", data.fastest ? "grid-cols-2" : "grid-cols-1")}>
            <div className="rounded-xl bg-cheap-bg p-4">
              <p className="text-xs font-medium text-cheap">{(data.store_count ?? data.marketplaces.length) > 1 ? "Cheapest" : "Price"}</p>
              <p className="text-2xl font-bold">{data.cheapest ? inr(data.cheapest.price) : "—"}</p>
              {data.cheapest && <p className="text-sm text-cheap">{data.cheapest.marketplace.name}</p>}
            </div>
            {data.fastest && (
              <div className="rounded-xl bg-fast-bg p-4">
                <p className="text-xs font-medium text-fast">{(data.store_count ?? data.marketplaces.length) > 1 ? "Fastest" : "Delivery"}</p>
                <p className="text-2xl font-bold">{data.fastest.deliveryText}</p>
                <p className="text-sm text-fast">{data.fastest.marketplace.name}</p>
              </div>
            )}
          </div>
          {data.price_max > data.price_min && <p className="mt-2 text-sm text-muted">Prices range from {inr(data.price_min)} to {inr(data.price_max)} across {data.store_count ?? data.listing_count} stores.</p>}

          {data.delivery_is_demo && (
            <label className="mt-5 flex w-fit items-center gap-2 rounded-full border border-line px-3 py-1.5 text-sm">
              <MapPin className="h-4 w-4 text-muted" />
              <input value={pincode} onChange={(e) => setPincode(e.target.value)} placeholder="Enter pincode" inputMode="numeric" className="w-28 bg-transparent outline-none" aria-label="Enter pincode" />
              <DemoLabel />
            </label>
          )}
          {data.error && <p className="mt-4 rounded-lg bg-fast-bg px-3 py-2 text-sm text-fast">Couldn’t load every store right now — showing the stores we have. ({data.error})</p>}

          {attrs.length > 0 && (
            <dl className="mt-5 grid grid-cols-2 gap-x-6 gap-y-1.5 text-sm sm:grid-cols-3">
              {attrs.map(([k, v]) => <div key={k}><dt className="text-xs text-muted">{titleCase(k)}</dt><dd className="font-medium">{/\d/.test(String(v)) ? String(v) : titleCase(String(v))}</dd></div>)}
            </dl>
          )}
          {data.description && <p className="mt-5 max-w-prose text-sm leading-relaxed text-muted">{data.description}</p>}
        </div>
      </div>

      {/* Tabs */}
      <div className="mt-10 flex flex-wrap items-center justify-between gap-3">
        <Tabs value={tab} onChange={setTab} items={[
          { value: "overview", label: "Overview" },
          { value: "all", label: "All listings", count: exactCount + data.similar_products.reduce((n, s) => n + s.listing_count, 0) },
          { value: "exact", label: "Exact matches", count: exactCount },
          { value: "similar", label: "Similar products", count: similarCount },
        ]} />
        {(tab === "all" || tab === "exact" || tab === "overview") && (
          <div className="flex flex-wrap items-center gap-2">
            <select value={mkt ?? ""} onChange={(e) => setMkt(e.target.value || null)} aria-label="Filter by marketplace" className="h-10 rounded-full border border-line bg-white px-4 text-sm">
              <option value="">All marketplaces</option>
              {data.marketplaces.map((m) => <option key={m.slug} value={m.slug}>{m.name}</option>)}
            </select>
            <SortControl value={sort} onChange={setSort} />
          </div>
        )}
      </div>

      <div className="mt-5 space-y-10">
        {(tab === "overview" || tab === "exact" || tab === "all") && (
          <section>
            <h2 className="mb-3 text-lg font-semibold">Same product at {data.listing_count} store{data.listing_count === 1 ? "" : "s"}</h2>
            <ComparisonTable listings={listings} cheapestId={data.cheapest?.listing_id} fastestId={data.fastest?.listing_id} />
          </section>
        )}

        {tab === "overview" && (
          <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
            <MatchExplanation match={data.match} listingCount={data.listing_count} live={data.live} />
            <section className="rounded-card border border-line p-5">
              <h3 className="font-semibold">Seller details</h3>
              <ul className="mt-3 divide-y divide-line text-sm">
                {listings.map((l) => (
                  <li key={l.id} className="flex flex-wrap items-center justify-between gap-2 py-2.5">
                    <div className="flex items-center gap-2"><MarketplaceBadge m={l.marketplace} /><span className="text-muted">Seller: {l.seller_name}</span></div>
                    <div className="flex items-center gap-3 text-xs text-muted">
                      <span>MRP {inr(l.mrp)}</span><span>{Math.round(l.discount_percentage)}% off</span>{l.delivery.deliveryDays < 90 && <span>{l.delivery.deliveryText}</span>}
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          </div>
        )}

        {(tab === "overview" || tab === "similar" || tab === "all") && data.similar_products.length > 0 && (
          <section>
            <h2 className="text-lg font-semibold">Similar products</h2>
            <p className="mb-4 mt-1 text-sm text-muted">Strong visual or textual similarity, but not confirmed to be the same item — a different size, shade, quantity or material.</p>
            <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
              {data.similar_products.map((s) => (
                <div key={s.id} className="relative">
                  <span className="absolute left-3 top-3 z-10 rounded-full bg-white/95 px-2.5 py-1 text-xs font-semibold shadow-sm">{s.similarity}% similar</span>
                  <ProductGroupCard g={{ ...s, match: { confidence: null, reasons: [] } }} pincode={pincode || undefined} />
                  <ul className="mt-2 flex flex-wrap gap-1.5 text-[11px]">
                    {s.reasons.filter((r) => r.status !== "ok").slice(0, 3).map((r) => <li key={r.label} className="rounded-full bg-fast-bg px-2 py-0.5 text-fast">{r.label}</li>)}
                  </ul>
                </div>
              ))}
            </div>
          </section>
        )}
        {tab === "similar" && data.similar_products.length === 0 && <p className="text-sm text-muted">No similar products were found for this group.</p>}
      </div>
    </div>
  );
}
