import type { Marketplace, ProductDetail, SearchFilters, SearchResponse, SortOption } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Seeded listings use backend-relative image paths; real adapters return absolute URLs. */
export const imageSrc = (url: string | null | undefined) =>
  !url ? "" : url.startsWith("/") ? `${API_URL}${url}` : url;

async function get<T>(path: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
  const url = new URL(path, API_URL);
  Object.entries(params ?? {}).forEach(([k, v]) => {
    if (v !== undefined && v !== "" && v !== null) url.searchParams.set(k, String(v));
  });
  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

export const api = {
  search: (q: string, opts: { pincode?: string; sort?: string; filters?: SearchFilters } = {}) =>
    get<SearchResponse>("/api/search", {
      q,
      pincode: opts.pincode,
      sort: opts.sort,
      marketplaces: opts.filters?.marketplaces?.join(","),
      price_min: opts.filters?.price_min,
      price_max: opts.filters?.price_max,
      max_delivery_days: opts.filters?.max_delivery_days,
      min_rating: opts.filters?.min_rating,
      brands: opts.filters?.brands?.join(","),
      in_stock_only: opts.filters?.in_stock_only,
    }),
  suggestions: (q: string) => get<{ history: string[]; products: string[] }>("/api/search/suggestions", { q }),
  product: (id: string | number, pincode?: string, sort?: string) =>
    get<ProductDetail>(`/api/products/${id}`, { pincode, sort }),
  locate: (lat: number, lon: number) => get<{ pincode: string | null; label: string | null }>("/api/locate", { lat, lon }),
  marketplaces: () => get<Marketplace[]>("/api/marketplaces"),
  sortOptions: () => get<SortOption[]>("/api/sort-options"),
};
