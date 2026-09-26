import { Suspense } from "react";
import Link from "next/link";
import { SearchBar } from "@/components/SearchBar";

const EXAMPLES = ["black oversized hoodie", "Maybelline Sky High mascara", "iPhone 17 case", "white sneakers", "Levi's 511", "Airdopes 141"];
const MARKETS = [["Amazon", "#FF9900"], ["Flipkart", "#2874F0"], ["Meesho", "#9F2089"], ["Myntra", "#FF3F6C"], ["Nykaa", "#FC2779"], ["AJIO", "#2C4152"]];

export default function Home() {
  return (
    <div className="mx-auto max-w-4xl px-4 pb-16 pt-14 sm:pt-24">
      <div className="text-center">
        <h1 className="text-4xl font-bold leading-[1.05] tracking-tight sm:text-6xl">
          Find the same product.<br />Compare every seller.<br />Buy smarter.
        </h1>
        <p className="mx-auto mt-5 max-w-xl text-lg text-muted">AI-powered product matching across marketplaces.</p>
      </div>

      <div className="mx-auto mt-10 max-w-2xl">
        <Suspense><SearchBar /></Suspense>
        <div className="mt-4 flex flex-wrap justify-center gap-2">
          {EXAMPLES.map((e) => (
            <Link key={e} href={`/search?q=${encodeURIComponent(e)}`} className="rounded-full border border-line bg-white px-3 py-1.5 text-sm text-muted hover:border-ink hover:text-ink">
              {e}
            </Link>
          ))}
        </div>
      </div>

      <div className="mt-16 grid gap-6 sm:grid-cols-3">
        <Step n="1" title="One search, six marketplaces" body="Listings from Amazon, Flipkart, Meesho, Myntra, Nykaa and AJIO, pulled into one place." />
        <Step n="2" title="Same product, grouped" body="Titles, attributes and imagery are compared so 'Sky High Mascara 7.2ml' and 'Sky High Washable Mascara' land in one group." />
        <Step n="3" title="Cheapest and fastest, side by side" body="Price, delivery time, seller and rating for every listing. Sort by what matters to you." />
      </div>

      <div className="mt-14 flex flex-wrap items-center justify-center gap-x-6 gap-y-3 text-sm text-muted">
        {MARKETS.map(([n, c]) => <span key={n} className="inline-flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: c }} />{n}</span>)}
      </div>
      <p className="mt-6 text-center text-xs text-muted">Marketplace listings shown in this MVP are demo data. Delivery estimates are seeded, not live.</p>
    </div>
  );
}

function Step({ n, title, body }: { n: string; title: string; body: string }) {
  return (
    <div className="rounded-card border border-line p-5">
      <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-ink text-xs font-semibold text-white">{n}</span>
      <h2 className="mt-3 font-semibold">{title}</h2>
      <p className="mt-1 text-sm leading-relaxed text-muted">{body}</p>
    </div>
  );
}
