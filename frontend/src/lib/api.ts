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

/** Coordinates → pincode straight from the browser (BigDataCloud's free client-side API),
 *  so location works instantly even while the backend is waking up. */
export async function pincodeFromCoords(lat: number, lon: number): Promise<{ pincode: string | null; label: string | null }> {
  try {
    const u = `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${lat}&longitude=${lon}&localityLanguage=en`;
    const ctrl = new AbortController(); const t = setTimeout(() => ctrl.abort(), 6000);
    const d = await fetch(u, { signal: ctrl.signal }).then((r) => r.json()); clearTimeout(t);
    const pin = String(d.postcode ?? "").replace(/\D/g, "").slice(0, 6);
    if (d.countryCode === "IN" && pin.length === 6) return { pincode: pin, label: [d.city || d.locality, d.principalSubdivision].filter(Boolean).join(", ") };
  } catch {}
  try { return await api.locate(lat, lon); } catch { return { pincode: null, label: null }; }   // backend fallback
}

/** Fire-and-forget request that wakes the (free-tier) backend while the shopper is still typing. */
export function warmUpBackend() {
  try { fetch(`${API_URL}/health`, { cache: "no-store", mode: "cors" }).catch(() => {}); } catch {}
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
