"use client";
import { useEffect, useState } from "react";

const STORES = [
  { name: "Amazon", color: "#FF9900" },
  { name: "Flipkart", color: "#2874F0" },
  { name: "Croma", color: "#00A99D" },
  { name: "Reliance Digital", color: "#E42529" },
  { name: "Myntra", color: "#FF3F6C" },
  { name: "Nykaa", color: "#FC2779" },
];

const STEPS = [
  "Searching Amazon…",
  "Checking Flipkart prices…",
  "Looking at Croma & Reliance Digital…",
  "Scanning Myntra, Nykaa and more…",
  "Matching the same product across stores…",
  "Finding the cheapest and fastest deal…",
];

/** Full-width live-search loader: sweeping lens over store chips, rotating status,
 *  easing progress bar, elapsed-time reassurance and shimmering skeleton cards. */
export function SearchingAnimation({ query, title = "Searching live prices for", skeletons = 3 }: { query: string; title?: string; skeletons?: number }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const start = Date.now();
    const id = setInterval(() => setElapsed((Date.now() - start) / 1000), 200);
    // Warn before a refresh / tab close while the live search is still running.
    const warn = (e: BeforeUnloadEvent) => { e.preventDefault(); e.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => { clearInterval(id); window.removeEventListener("beforeunload", warn); };
  }, []);

  const step = Math.floor(elapsed / 2.2) % STEPS.length;
  const active = Math.floor(elapsed / 0.9) % STORES.length;
  const checked = Math.min(STORES.length, Math.floor(elapsed / 0.9));
  // Eases toward 95% (~63% at 8s, ~86% at 16s) — never claims to be done early.
  const progress = Math.round(95 * (1 - Math.exp(-elapsed / 8)));
  const slow = elapsed > 12;

  return (
    <div role="status" aria-live="polite" className="oc-fade-in">
      <div className="relative overflow-hidden rounded-card border border-line bg-gradient-to-b from-white to-surface px-6 py-10 text-center">
        {/* Lens + rings */}
        <div className="relative mx-auto h-28 w-28">
          <span className="oc-ring absolute inset-0 rounded-full border-2 border-accent/30" />
          <span className="oc-ring oc-ring-2 absolute inset-0 rounded-full border-2 border-accent/20" />
          <svg viewBox="0 0 64 64" className="oc-lens absolute inset-0 m-auto h-16 w-16 text-accent" aria-hidden="true">
            <circle cx="27" cy="27" r="16" fill="white" stroke="currentColor" strokeWidth="5" />
            <path d="M39 39 L54 54" stroke="currentColor" strokeWidth="7" strokeLinecap="round" />
            <path d="M19 23 a9 9 0 0 1 9 -7" stroke="currentColor" strokeOpacity=".35" strokeWidth="3" fill="none" strokeLinecap="round" />
          </svg>
        </div>

        <h2 className="mt-5 text-lg font-semibold">
          {title} <span className="text-accent">“{query}”</span>
        </h2>
        <p key={step} className="oc-step mt-1 h-5 text-sm text-muted">{STEPS[step]}</p>

        {/* Store chips light up as the lens passes */}
        <div className="mx-auto mt-6 flex max-w-2xl flex-wrap justify-center gap-2">
          {STORES.map((s, i) => {
            const on = i === active;
            const done = i < checked;
            return (
              <span key={s.name}
                className="inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-all duration-300"
                style={{
                  borderColor: on || done ? s.color : "var(--line)",
                  background: on ? s.color : done ? `${s.color}14` : "white",
                  color: on ? "white" : done ? s.color : "var(--muted)",
                  transform: on ? "translateY(-3px) scale(1.06)" : "none",
                  boxShadow: on ? `0 6px 16px ${s.color}55` : "none",
                }}>
                {done && !on ? "✓" : <span className="h-1.5 w-1.5 rounded-full" style={{ background: on ? "white" : s.color }} />}
                {s.name}
              </span>
            );
          })}
        </div>

        {/* Progress */}
        <div className="mx-auto mt-7 max-w-md">
          <div className="h-2 overflow-hidden rounded-full bg-line">
            <div className="oc-bar h-full rounded-full bg-accent transition-[width] duration-500 ease-out" style={{ width: `${progress}%` }} />
          </div>
          <div className="mt-2 flex justify-between text-xs text-muted">
            <span>{progress}%</span>
            <span>{Math.floor(elapsed)}s</span>
          </div>
        </div>

        <p className="mt-4 text-sm font-medium text-ink">Please don’t refresh — we’re fetching live prices from every store.</p>
        {slow && (
          <p className="oc-fade-in mt-1 text-xs text-muted">
            Waking up the price engine — the first search can take up to a minute. Hang tight!
          </p>
        )}
      </div>

      {/* Skeleton result cards */}
      <div className="mt-6 grid gap-5 sm:grid-cols-2 xl:grid-cols-3" aria-hidden="true">
        {Array.from({ length: skeletons }, (_, i) => i).map((i) => (
          <div key={i} className="overflow-hidden rounded-card border border-line" style={{ animationDelay: `${i * 120}ms` }}>
            <div className="oc-shimmer aspect-square" />
            <div className="space-y-3 p-4">
              <div className="oc-shimmer h-4 w-4/5 rounded" />
              <div className="oc-shimmer h-3 w-1/2 rounded" />
              <div className="grid grid-cols-2 gap-2">
                <div className="oc-shimmer h-16 rounded-xl" />
                <div className="oc-shimmer h-16 rounded-xl" />
              </div>
              <div className="oc-shimmer h-10 rounded-full" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
