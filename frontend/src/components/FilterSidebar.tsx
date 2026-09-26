"use client";
import type { Marketplace, SearchFilters } from "@/lib/types";
import { cn } from "@/lib/utils";

const DELIVERY = [{ v: 1, l: "Tomorrow" }, { v: 2, l: "Within 2 days" }, { v: 4, l: "Within 4 days" }];
const RATINGS = [4.5, 4, 3.5];

export function FilterSidebar({ filters, onChange, marketplaces, brands, className }: {
  filters: SearchFilters; onChange: (f: SearchFilters) => void; marketplaces: Marketplace[]; brands: string[]; className?: string;
}) {
  const toggle = (key: "marketplaces" | "brands", v: string) => {
    const cur = new Set(filters[key] ?? []);
    if (cur.has(v)) cur.delete(v); else cur.add(v);
    onChange({ ...filters, [key]: cur.size ? [...cur] : undefined });
  };
  const active = Object.values(filters).some((v) => v !== undefined && v !== false);

  return (
    <aside className={cn("space-y-6 text-sm", className)}>
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">Filters</h2>
        {active && <button className="text-xs text-accent hover:underline" onClick={() => onChange({})}>Clear all</button>}
      </div>

      <Section title="Marketplace">
        {marketplaces.map((m) => (
          <Check key={m.slug} checked={filters.marketplaces?.includes(m.slug) ?? false} onChange={() => toggle("marketplaces", m.slug)}>
            <span className="inline-flex items-center gap-2"><span className="h-2 w-2 rounded-full" style={{ backgroundColor: m.brand_color }} />{m.name}</span>
          </Check>
        ))}
      </Section>

      <Section title="Price">
        <div className="flex items-center gap-2">
          <input type="number" placeholder="Min" value={filters.price_min ?? ""} min={0}
            onChange={(e) => onChange({ ...filters, price_min: e.target.value ? Number(e.target.value) : undefined })}
            className="h-9 w-full rounded-lg border border-line px-3" aria-label="Minimum price" />
          <span className="text-muted">–</span>
          <input type="number" placeholder="Max" value={filters.price_max ?? ""} min={0}
            onChange={(e) => onChange({ ...filters, price_max: e.target.value ? Number(e.target.value) : undefined })}
            className="h-9 w-full rounded-lg border border-line px-3" aria-label="Maximum price" />
        </div>
      </Section>

      <Section title="Delivery">
        {DELIVERY.map((d) => (
          <Radio key={d.v} checked={filters.max_delivery_days === d.v} onChange={() => onChange({ ...filters, max_delivery_days: filters.max_delivery_days === d.v ? undefined : d.v })}>{d.l}</Radio>
        ))}
      </Section>

      <Section title="Rating">
        {RATINGS.map((r) => (
          <Radio key={r} checked={filters.min_rating === r} onChange={() => onChange({ ...filters, min_rating: filters.min_rating === r ? undefined : r })}>{r}★ &amp; up</Radio>
        ))}
      </Section>

      {brands.length > 0 && (
        <Section title="Brand">
          {brands.map((b) => <Check key={b} checked={filters.brands?.includes(b) ?? false} onChange={() => toggle("brands", b)}>{b}</Check>)}
        </Section>
      )}

      <Section title="Availability">
        <Check checked={filters.in_stock_only ?? false} onChange={() => onChange({ ...filters, in_stock_only: !filters.in_stock_only || undefined })}>In stock only</Check>
      </Section>
    </aside>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return <div><h3 className="mb-2 text-xs font-medium text-muted">{title}</h3><div className="space-y-1.5">{children}</div></div>;
}
function Check({ checked, onChange, children }: { checked: boolean; onChange: () => void; children: React.ReactNode }) {
  return <label className="flex cursor-pointer items-center gap-2"><input type="checkbox" checked={checked} onChange={onChange} className="h-4 w-4 accent-[var(--accent)]" />{children}</label>;
}
function Radio({ checked, onChange, children }: { checked: boolean; onChange: () => void; children: React.ReactNode }) {
  return <label className="flex cursor-pointer items-center gap-2"><input type="checkbox" checked={checked} onChange={onChange} className="h-4 w-4 rounded-full accent-[var(--accent)]" />{children}</label>;
}
