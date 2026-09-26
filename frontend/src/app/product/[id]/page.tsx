import { Suspense } from "react";
import { ProductDetailView } from "./ProductDetailView";

export default async function ProductPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <Suspense fallback={<div className="mx-auto max-w-7xl px-4 py-10 text-muted">Loading…</div>}><ProductDetailView id={id} /></Suspense>;
}
