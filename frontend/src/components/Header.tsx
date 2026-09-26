"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect } from "react";
import { SearchBar } from "./SearchBar";
import { warmUpBackend } from "@/lib/api";

export function Header() {
  const pathname = usePathname();
  const onHome = pathname === "/";
  useEffect(() => { warmUpBackend(); }, []);   // wake the backend as soon as anyone opens the site
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
        <Link href="/" className="flex shrink-0 items-baseline gap-1 text-lg font-bold tracking-tight">
          Omni<span className="text-accent">Compare</span>
        </Link>
        {!onHome && <div className="order-last w-full sm:order-none sm:w-auto sm:flex-1"><SearchBar compact /></div>}
        <span className="hidden shrink-0 text-sm text-muted md:inline">Compare smarter</span>
      </div>
    </header>
  );
}
