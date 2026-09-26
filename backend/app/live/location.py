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
