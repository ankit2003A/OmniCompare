"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";

const ASKED = "omnicompare.geoAsked";

/** Browser geolocation → pincode. Auto-runs once on the first visit (if no pincode yet);
 *  `detect()` re-runs it from the 📍 button. Never blocks the page if denied. */
export function useLocate(pincode: string, setPincode: (p: string) => void, onFound?: (p: string) => void) {
  const [status, setStatus] = useState<"idle" | "locating" | "denied" | "failed">("idle");
  const cb = useRef(onFound);
  useEffect(() => { cb.current = onFound; }, [onFound]);

  const detect = useCallback(() => {
    if (typeof navigator === "undefined" || !navigator.geolocation) { setStatus("failed"); return; }
    try { window.localStorage.setItem(ASKED, "1"); } catch {}
    setStatus("locating");
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const r = await api.locate(pos.coords.latitude, pos.coords.longitude);
          if (r.pincode) { setPincode(r.pincode); cb.current?.(r.pincode); setStatus("idle"); }
          else setStatus("failed");
        } catch { setStatus("failed"); }
      },
      (err) => setStatus(err.code === err.PERMISSION_DENIED ? "denied" : "failed"),
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 30 * 60 * 1000 },
    );
  }, [setPincode]);

  useEffect(() => {
    let asked = false;
    try { asked = window.localStorage.getItem(ASKED) === "1"; } catch {}
    if (!pincode && !asked) {
      const t = setTimeout(detect, 600);        // let the page paint first
      return () => clearTimeout(t);
    }
  }, []);                                       // eslint-disable-line react-hooks/exhaustive-deps

  return { status, detect };
}
