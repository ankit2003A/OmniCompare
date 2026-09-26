import { Suspense } from "react";
import { SearchResults } from "./SearchResults";

export default function SearchPage() {
  return <Suspense fallback={<div className="mx-auto max-w-7xl px-4 py-10 text-muted">Loading…</div>}><SearchResults /></Suspense>;
}
