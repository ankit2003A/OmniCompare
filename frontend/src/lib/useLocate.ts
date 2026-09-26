"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { pincodeFromCoords } from "./api";

const SESSION = "omnicompare.geoThisVisit";

export type GeoStatus = "idle" | "locating" | "denied" | "failed";

/** Browser geolocation → pincode.
 *  Runs automatically every time the site is opened (once per browser tab/visit) so the
 *  pincode always matches where the shopper is now. `detect()` re-runs it from the 📍 button.
 *  If the shopper has blocked location, browsers never show the prompt again — we report
 *  "denied" so the UI can explain how to turn it back on. */
export function useLocate(setPincode: (p: string) => void, onFound?: (p: string) => void) {
  const [status, setStatus] = useState<GeoStatus>("idle");
  const cb = useRef(onFound);
  useEffect(() => { cb.current = onFound; }, [onFound]);

  const detect = useCallback(() => {
    if (typeof navigator === "undefined" || !navigator.geolocation) { setStatus("failed"); return; }
    setStatus("locating");
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const r = await pincodeFromCoords(pos.coords.latitude, pos.coords.longitude);
          if (r.pincode) { setPincode(r.pincode); cb.current?.(r.pincode); setStatus("idle"); }
          else setStatus("failed");
        } catch { setStatus("failed"); }
      },
      (err) => setStatus(err.code === err.PERMISSION_DENIED ? "denied" : "failed"),
      { enableHighAccuracy: false, timeout: 12000, maximumAge: 5 * 60 * 1000 },
    );
  }, [setPincode]);

  useEffect(() => {
    let done = false;
    try { done = window.sessionStorage.getItem(SESSION) === "1"; window.sessionStorage.setItem(SESSION, "1"); } catch {}
    if (done) {
      // Same visit, new page: don't prompt again, but still surface a blocked permission.
      navigator.permissions?.query({ name: "geolocation" }).then((p) => p.state === "denied" && setStatus("denied")).catch(() => {});
      return;
    }
    const t = setTimeout(detect, 500);          // let the page paint first, then ask
    return () => clearTimeout(t);
  }, [detect]);

  return { status, detect };
}
