"""Thin client for SerpApi's Google Shopping + Google Immersive Product engines (India).

Real products, real prices, real images and real store links. Every call costs one
SerpApi search, so callers cache results in the database.
"""
import httpx
from app.config import get_settings

BASE = "https://serpapi.com/search.json"


class LiveDataError(RuntimeError):
    pass


def _get(params: dict) -> dict:
    key = get_settings().serpapi_api_key
    if not key:
        raise LiveDataError("SERPAPI_API_KEY is not configured")
    try:
        r = httpx.get(BASE, params={**params, "api_key": key}, timeout=25)
    except httpx.HTTPError as e:
        raise LiveDataError(f"SerpApi request failed: {e}") from e
    data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if r.status_code != 200 or data.get("error"):
        # "Google hasn't returned any results" is not an error for us — just empty.
        msg = data.get("error") or f"HTTP {r.status_code}"
        if "hasn't returned any results" in msg:
            return {}
        raise LiveDataError(msg)
    return data


def account() -> dict:
    """Plan usage from SerpApi's account endpoint (free — does not use a search)."""
    key = get_settings().serpapi_api_key
    if not key:
        return {}
    try:
        d = httpx.get("https://serpapi.com/account.json", params={"api_key": key}, timeout=15).json()
    except Exception as e:
        return {"error": str(e)}
    return {k: d.get(k) for k in ("plan_name", "searches_per_month", "this_month_usage", "plan_searches_left",
                                  "total_searches_left", "last_hour_searches")}


def shopping_search(query: str, location: str = "India") -> list[dict]:
    data = _get({"engine": "google_shopping", "q": query, "gl": "in", "hl": "en",
                 "google_domain": "google.co.in", "location": location or "India"})
    return data.get("shopping_results", []) or []


def amazon_search(query: str) -> list[dict]:
    data = _get({"engine": "amazon", "amazon_domain": "amazon.in", "k": query})
    return [r for r in (data.get("organic_results") or []) if not r.get("sponsored")]


def product_stores(page_token: str) -> dict:
    data = _get({"engine": "google_immersive_product", "page_token": page_token, "more_stores": "true"})
    return data.get("product_results", {}) or {}
