import { Info } from "lucide-react";

export function DemoLabel({ text = "Demo delivery estimate" }: { text?: string }) {
  return (
    <span className="inline-flex items-center gap-1 text-[11px] text-muted" title="Seeded data, not a live marketplace query">
      <Info className="h-3 w-3" /> {text}
    </span>
  );
}
