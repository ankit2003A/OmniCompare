"use client";
import { Select } from "./ui/select";
import type { SortOption } from "@/lib/types";

export const DEFAULT_SORTS: SortOption[] = [
  { value: "relevance", label: "Relevance" },
  { value: "price_asc", label: "Price: Low → High" },
  { value: "price_desc", label: "Price: High → Low" },
  { value: "delivery_fastest", label: "Fastest delivery" },
  { value: "delivery_slowest", label: "Slowest delivery" },
  { value: "rating_desc", label: "Highest rated" },
  { value: "rating_asc", label: "Lowest rated" },
  { value: "discount_desc", label: "Highest discount" },
];

export function SortControl({ value, onChange, options = DEFAULT_SORTS }: { value: string; onChange: (v: string) => void; options?: SortOption[] }) {
  return (
    <label className="flex items-center gap-2 text-sm text-muted">
      Sort by
      <Select value={value} onChange={(e) => onChange(e.target.value)} aria-label="Sort results">
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </Select>
    </label>
  );
}
