"use client";
import { useSyncExternalStore, useCallback } from "react";

const KEY = "omnicompare.pincode";
const listeners = new Set<() => void>();

function read(): string {
  try { return window.localStorage.getItem(KEY) ?? ""; } catch { return ""; }
}
function subscribe(cb: () => void) {
  listeners.add(cb);
  window.addEventListener("storage", cb);
  return () => { listeners.delete(cb); window.removeEventListener("storage", cb); };
}

/** Pincode persisted per browser. A pincode in the URL wins over the saved one. */
export function usePincode(initial?: string | null) {
  const saved = useSyncExternalStore(subscribe, read, () => "");
  const pincode = initial || saved;
  const setPincode = useCallback((p: string) => {
    const clean = p.replace(/\D/g, "").slice(0, 6);
    try { window.localStorage.setItem(KEY, clean); } catch {}
    listeners.forEach((l) => l());
  }, []);
  return { pincode, setPincode };
}
