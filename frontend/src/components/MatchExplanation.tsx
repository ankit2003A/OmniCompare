import { Check, AlertTriangle, Sparkles } from "lucide-react";
import type { MatchExplanation as ME } from "@/lib/types";

export function MatchExplanation({ match, listingCount, live = false }: { match: ME; listingCount: number; live?: boolean }) {
  if (listingCount < 2 || match.confidence === null) {
    return (
      <div className="rounded-card border border-line bg-surface/50 p-5">
        <h3 className="flex items-center gap-2 font-semibold"><Sparkles className="h-4 w-4 text-accent" /> Why these products were grouped</h3>
        <p className="mt-2 text-sm text-muted">{live ? "Only one store was found selling this exact variant right now." : "Only one marketplace listing was found for this product, so there was nothing to group. Similar products are listed below."}</p>
      </div>
    );
  }
  const ok = match.reasons.filter((r) => r.status === "ok");
  const warn = match.reasons.filter((r) => r.status !== "ok");
  const uncertain = match.confidence < 90;
  return (
    <div className="rounded-card border border-line p-5">
      <h3 className="flex items-center gap-2 font-semibold"><Sparkles className="h-4 w-4 text-accent" /> Why these products were grouped</h3>
      <div className="mt-3 flex items-baseline gap-3">
        <span className="text-4xl font-bold tracking-tight">{match.confidence}%</span>
        <span className="text-sm text-muted">{uncertain ? "match — some details differ" : "match — same product across sellers"}</span>
      </div>
      {match.scores && !live && (
        <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
          {([["Title", match.scores.text], ["Attributes", match.scores.attribute], ["Imagery", match.scores.image]] as const).map(([k, v]) => (
            <div key={k} className="rounded-lg bg-surface p-2">
              <div className="flex justify-between text-muted"><span>{k}</span><span>{Math.round(v * 100)}%</span></div>
              <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-line"><div className="h-full rounded-full bg-accent" style={{ width: `${v * 100}%` }} /></div>
            </div>
          ))}
        </div>
      )}
      <ul className="mt-4 space-y-1.5 text-sm">
        {ok.map((r) => <li key={r.label} className="flex items-center gap-2"><Check className="h-4 w-4 text-cheap" /> {r.label}</li>)}
        {warn.map((r) => <li key={r.label} className="flex items-center gap-2 text-fast"><AlertTriangle className="h-4 w-4" /> {r.label}</li>)}
      </ul>
      <p className="mt-4 text-xs text-muted">{live
        ? "Matched on brand, model, variant, storage, RAM, colour and condition from each store’s listing, with a price sanity check."
        : "Hybrid score: title similarity 40% · attribute agreement 25% · image similarity 35%. Weights and thresholds are configurable on the backend."}</p>
    </div>
  );
}
