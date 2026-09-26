"""Pincode → Google location, so results and delivery estimates are for the shopper's city.

1. India Post public API: pincode → district + state (free, no key).
2. SerpApi Locations API: district/state → Google's canonical location name
   (free — does not consume SerpApi searches).
Results are cached in-process; unknown pincodes fall back to all-India.
"""
import re
import httpx

DEFAULT = "India"
_cache: dict[str, dict] = {}
_ALIASES = {"gurgaon": "gurugram", "bangalore": "bengaluru", "bombay": "mumbai", "calcutta": "kolkata",
            "madras": "chennai", "trivandrum": "thiruvananthapuram", "allahabad": "prayagraj"}


def _canonical(q: str) -> str | None:
    try:
        r = httpx.get("https://serpapi.com/locations.json", params={"q": q, "limit": 10}, timeout=10)
        rows = r.json() if r.status_code == 200 else []
    except Exception:
        return None
    rows = [x for x in rows if x.get("country_code") == "IN"]
    rows.sort(key=lambda x: (x.get("target_type") not in ("City", "Municipality", "District"), -(x.get("reach") or 0)))
    return rows[0]["canonical_name"] if rows else None


def resolve(pincode: str | None) -> dict:
    """Returns {"location": <google canonical name>, "label": "City, State", "pincode": ...}."""
    pin = re.sub(r"\D", "", pincode or "")
    if len(pin) != 6:
        return {"location": DEFAULT, "label": "India", "pincode": None}
    if pin in _cache:
        return _cache[pin]
    out = {"location": DEFAULT, "label": "India", "pincode": pin}
    try:
        r = httpx.get(f"https://api.postalpincode.in/pincode/{pin}", timeout=10)
        data = r.json()[0] if r.status_code == 200 else {}
        offices = data.get("PostOffice") or []
        if data.get("Status") == "Success" and offices:
            district, state = offices[0].get("District", ""), offices[0].get("State", "")
            city = _ALIASES.get(district.lower(), district.lower())
            loc = _canonical(f"{city} {state}") or _canonical(city) or _canonical(state)
            out = {"location": loc or DEFAULT, "label": f"{district}, {state}", "pincode": pin}
    except Exception:
        pass
    _cache[pin] = out
    return out


_rev_cache: dict[tuple, dict] = {}


def reverse(lat: float, lon: float) -> dict:
    """Coordinates → Indian pincode + "City, State" via OpenStreetMap Nominatim (free).
    Rounded to ~1 km and cached so repeat visitors don't hit the service again."""
    key = (round(lat, 2), round(lon, 2))
    if key in _rev_cache:
        return _rev_cache[key]
    out = {"pincode": None, "label": None}
    try:
        r = httpx.get("https://nominatim.openstreetmap.org/reverse",
                      params={"lat": lat, "lon": lon, "format": "jsonv2", "addressdetails": 1, "zoom": 18},
                      headers={"User-Agent": "OmniCompare/1.0 (price comparison; contact via site)",
                               "Accept-Language": "en"}, timeout=10)
        addr = (r.json() or {}).get("address", {}) if r.status_code == 200 else {}
        pin = re.sub(r"\D", "", addr.get("postcode", ""))[:6]
        city = addr.get("city") or addr.get("town") or addr.get("state_district") or addr.get("county") or ""
        if addr.get("country_code") == "in" and len(pin) == 6:
            out = {"pincode": pin, "label": ", ".join(x for x in (city, addr.get("state", "")) if x)}
    except Exception:
        pass
    if not out["pincode"]:                      # fallback geocoder (free, no key)
        try:
            r = httpx.get("https://api.bigdatacloud.net/data/reverse-geocode-client",
                          params={"latitude": lat, "longitude": lon, "localityLanguage": "en"}, timeout=10)
            d = r.json() if r.status_code == 200 else {}
            pin = re.sub(r"\D", "", str(d.get("postcode", "")))[:6]
            if d.get("countryCode") == "IN" and len(pin) == 6:
                out = {"pincode": pin, "label": ", ".join(x for x in (d.get("city") or d.get("locality"),
                                                                       d.get("principalSubdivision")) if x)}
        except Exception:
            pass
    if out["pincode"]:
        _rev_cache[key] = out                   # don't cache failures
    return out
