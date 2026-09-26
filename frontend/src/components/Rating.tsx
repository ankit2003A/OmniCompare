import { Star } from "lucide-react";
import { compact } from "@/lib/format";

export function Rating({ value, count }: { value: number; count?: number }) {
  return (
    <span className="inline-flex items-center gap-1 text-sm">
      <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
      <span className="font-medium">{value.toFixed(1)}</span>
      {count !== undefined && <span className="text-muted">({compact(count)})</span>}
    </span>
  );
}
