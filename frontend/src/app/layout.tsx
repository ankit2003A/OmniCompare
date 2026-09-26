import type { Metadata } from "next";
import "./globals.css";
import { Suspense } from "react";
import { Header } from "@/components/Header";

export const metadata: Metadata = {
  title: "OmniCompare — Find the same product. Compare every seller.",
  description: "AI-powered product matching across Amazon, Flipkart, Meesho, Myntra, Nykaa and AJIO. Demo data.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full flex flex-col bg-bg text-ink">
        <Suspense><Header /></Suspense>
        <main className="flex-1">{children}</main>
        <footer className="border-t border-line mt-16">
          <div className="mx-auto max-w-7xl px-4 py-6 text-sm text-muted flex flex-col sm:flex-row gap-2 justify-between">
            <span>OmniCompare MVP · marketplace listings are demo data; delivery estimates are seeded, not live.</span>
            <span>Compare smarter</span>
          </div>
        </footer>
      </body>
    </html>
  );
}
