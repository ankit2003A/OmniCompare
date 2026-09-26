"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { SearchBar } from "./SearchBar";

export function Header() {
  const pathname = usePathname();
  const onHome = pathname === "/";
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-3">
        <Link href="/" className="flex shrink-0 items-baseline gap-1 text-lg font-bold tracking-tight">
          Omni<span className="text-accent">Compare</span>
        </Link>
        {!onHome && <div className="flex-1"><SearchBar compact /></div>}
        <span className="hidden shrink-0 text-sm text-muted md:inline">Compare smarter</span>
      </div>
    </header>
  );
}
