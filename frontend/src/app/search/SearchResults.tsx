"use client";
import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { SlidersHorizontal, X } from "lucide-react";
import { api } from "@/lib/api";
import type { Marketplace, SearchFilters, SearchResponse } from "@/lib/types";
import { ProductGroupCard } from "@/components/ProductGroupCard";
import { FilterSidebar } from "@/components/FilterSidebar";
import { SortControl } from "@/components/SortControl";
import { DemoLabel } from "@/components/DemoLabel";
import { Button } from "@/components/ui/button";
import { SearchingAnimation } from "@/components/SearchingAnimation";

export function SearchResults() {
  const params = useSearchParams();
  const router = useRouter();
  const q = params.get("q") ?? "";
  const pincode = params.get("pincode") ?? undefined;
  const sort = params.get("sort") ?? "relevance";

  const [data, setData] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(Boolean(q));
  const [filters, setFilters] = useState<SearchFilters>({});
  const [marketplaces, setMarketplaces] = useState<Marketplace[]>([]);
  const [showFilters, setShowFilters] = useState(false);
  const [brands, setBrands] = useState<string[]>([]);

  useEffect(() => { api.marketplaces().then(setMarketplaces).catch(() => {}); }, []);

  useEffect(() => {
    if (!q) return;
    let cancelled = false;
    const t = setTimeout(() => setLoading(true), 0);
    api.search(q, { pincode, sort, filters })
      .then((r) => {
        if (cancelled) return;
        setData(r); setError(null);
        if (r.live && !filters.marketplaces) {
          const seen = new Map<string, Marketplace>();
          r.groups.forEach((g) => g.marketplaces.forEach((m) => seen.set(m.slug, { ...m, id: 0, base_url: "" })));
          setMarketplaces([...seen.values()].sort((a, b) => a.name.localeCompare(b.name)));
        }
        if (!filters.brands) {
          const b = new Set<string>();
          r.groups.forEach((g) => g.listings.forEach((l) => l.brand && b.add(l.brand)));
          setBrands([...b].sort());
        }
      })
      .catch((e) => !cancelled && setError(String(e.message ?? e)))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; clearTimeout(t); };
  }, [q, pincode, sort, filters]);

  const setSort = (s: string) => {
    const sp = new URLSearchParams(params.toString());
    sp.set("sort", s);
    router.replace(`/search?${sp.toString()}`);
  };

  const groups = data?.groups ?? [];
  const sortLabel = useMemo(() => ({ delivery_fastest: "fastest delivery", price_asc: "lowest price", rating_desc: "highest rating", discount_desc: "highest discount" }[sort]), [sort]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Results for “{q}”</h1>
          <p className="mt-1 text-sm text-muted">
            {data && !loading ? `${data.total_groups} product${data.total_groups === 1 ? "" : "s"} · ${new Set(groups.flatMap((g) => g.marketplaces.map((m) => m.slug))).size} stores` : "Searching…"}
            {pincode && !data?.live && <> · delivering to <span className="font-medium text-ink">{pincode}</span></>}
            {data?.delivery_is_demo && <>{" · "}<DemoLabel /></>}
            {data?.live && <> · Live prices{data.location && data.location !== "India" ? <> for <span className="font-medium text-ink">{data.location}</span></> : " for all India (add your pincode for local delivery)"}</>}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="lg:hidden" onClick={() => setShowFilters(true)}><SlidersHorizontal className="h-4 w-4" /> Filters</Button>
          <SortControl value={sort} onChange={setSort} />
        </div>
      </div>

      {sortLabel && <p className="mt-3 rounded-lg bg-surface px-3 py-2 text-sm text-muted">Sorted by {sortLabel}. Cards still show both the cheapest and the fastest option for each product.</p>}

      <div className="mt-6 grid gap-8 lg:grid-cols-[240px_1fr]">
        <FilterSidebar className="hidden lg:block" filters={filters} onChange={setFilters} marketplaces={marketplaces} brands={brands} />

        {showFilters && (
          <div className="fixed inset-0 z-40 bg-black/30 lg:hidden" onClick={() => setShowFilters(false)}>
            <div className="absolute inset-y-0 left-0 w-80 max-w-[85vw] overflow-y-auto bg-white p-5" onClick={(e) => e.stopPropagation()}>
              <button className="mb-4 ml-auto flex items-center gap-1 text-sm text-muted" onClick={() => setShowFilters(false)}><X className="h-4 w-4" /> Close</button>
              <FilterSidebar filters={filters} onChange={setFilters} marketplaces={marketplaces} brands={brands} />
            </div>
          </div>
        )}

        <section aria-busy={loading}>
          {error && (
            <div className="rounded-card border border-line p-6 text-sm">
              <p className="font-semibold">Our price service is taking a moment to respond.</p>
              <p className="mt-1 text-muted">It may be waking up after a quiet period. Please try again in a few seconds.</p>
              <button onClick={() => setFilters({ ...filters })} className="mt-3 rounded-full bg-ink px-4 py-2 text-sm font-medium text-white hover:bg-black">Try again</button>
            </div>
          )}
          {!loading && !error && data?.error && (
            <div className="mb-4 rounded-card border border-line p-4 text-sm">
              <p className="font-semibold">Live prices are temporarily unavailable.</p>
              <p className="mt-1 text-muted">{data.error}</p>
            </div>
          )}
          {!loading && !error && data && groups.length === 0 && (
            <div className="rounded-card border border-line p-10 text-center">
              <p className="font-semibold">No products match “{q}”.</p>
              <p className="mt-1 text-sm text-muted">Try a different spelling or a broader term, or clear the filters.</p>
            </div>
          )}
          {loading ? (
            <SearchingAnimation query={q} />
          ) : (
            <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
              {groups.map((g) => <ProductGroupCard key={g.id} g={g} pincode={pincode} />)}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
