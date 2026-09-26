"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Search, MapPin, Clock, Tag } from "lucide-react";
import { api } from "@/lib/api";
import { usePincode } from "@/lib/usePincode";
import { cn } from "@/lib/utils";

export function SearchBar({ compact = false }: { compact?: boolean }) {
  const router = useRouter();
  const params = useSearchParams();
  const [q, setQ] = useState(params.get("q") ?? "");
  const { pincode, setPincode } = usePincode(params.get("pincode"));
  const [open, setOpen] = useState(false);
  const [sugg, setSugg] = useState<{ history: string[]; products: string[] }>({ history: [], products: [] });
  const box = useRef<HTMLFormElement>(null);

  useEffect(() => {
    if (!open) return;
    const t = setTimeout(() => api.suggestions(q).then(setSugg).catch(() => {}), 150);
    return () => clearTimeout(t);
  }, [q, open]);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => { if (!box.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const go = (query: string) => {
    if (!query.trim()) return;
    setOpen(false);
    const sp = new URLSearchParams({ q: query.trim() });
    if (pincode) sp.set("pincode", pincode);
    const sort = params.get("sort");
    if (sort) sp.set("sort", sort);
    router.push(`/search?${sp.toString()}`);
  };

  const items = [
    ...sugg.history.map((s) => ({ s, kind: "history" as const })),
    ...sugg.products.filter((p) => !sugg.history.includes(p)).map((s) => ({ s, kind: "product" as const })),
  ];

  return (
    <form ref={box} onSubmit={(e) => { e.preventDefault(); go(q); }} className="relative w-full">
      <div className={cn("flex items-center gap-2 rounded-full border border-line bg-white pl-4 pr-1.5 shadow-sm focus-within:border-ink",
        compact ? "h-11" : "h-14 shadow-md")}>
        <Search className="h-5 w-5 shrink-0 text-muted" />
        <input
          value={q} onChange={(e) => { setQ(e.target.value); setOpen(true); }} onFocus={() => setOpen(true)}
          placeholder="Search for a product..." aria-label="Search for a product"
          className={cn("min-w-0 flex-1 bg-transparent outline-none placeholder:text-muted", compact ? "text-sm" : "text-base")}
        />
        <label className="flex items-center gap-1 border-l border-line pl-2 text-sm text-muted sm:pl-3">
          <MapPin className="h-4 w-4" />
          <input
            value={pincode} onChange={(e) => setPincode(e.target.value)} inputMode="numeric" placeholder="Pincode"
            aria-label="Enter pincode" className="w-16 bg-transparent text-ink outline-none placeholder:text-muted sm:w-[5.5rem]"
          />
        </label>
        <button type="submit" className={cn("shrink-0 rounded-full bg-ink px-5 font-medium text-white hover:bg-black", compact ? "h-8 text-sm" : "h-11 text-base")}>
          Search
        </button>
      </div>

      {open && items.length > 0 && (
        <ul className="absolute left-0 right-0 top-full z-40 mt-2 overflow-hidden rounded-2xl border border-line bg-white py-1 shadow-lg">
          {items.slice(0, 8).map(({ s, kind }) => (
            <li key={kind + s}>
              <button type="button" onMouseDown={() => { setQ(s); go(s); }}
                className="flex w-full items-center gap-3 px-4 py-2 text-left text-sm hover:bg-surface">
                {kind === "history" ? <Clock className="h-4 w-4 text-muted" /> : <Tag className="h-4 w-4 text-muted" />}
                <span className="truncate">{s}</span>
                {kind === "history" && <span className="ml-auto text-xs text-muted">recent</span>}
              </button>
            </li>
          ))}
        </ul>
      )}
    </form>
  );
}
