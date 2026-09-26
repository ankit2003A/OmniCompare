"""Live mode: real Google Shopping (India) results → matcher → product groups.

Flow for a search:
  SerpApi google_shopping → RawListing per result → cluster() (same identity engine as the
  demo) → persisted as Product/Listing rows → serialized exactly like demo groups.

Store links: a Google Shopping result only carries a Google link. `resolve_store_link`
calls the Immersive Product engine once per product, which returns every store selling it
with its direct URL (Amazon, Flipkart, Croma, …). Those stores are also added to the
product group, so the product page becomes a real multi-store price comparison.
"""
import hashlib
import threading
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, parse_qs
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from app.adapters.base import RawListing
from app.live.matching import live_cluster, identity, VARIANT_WORDS
from app.live import location as locations
from app.matching.engine import product_text
from app.models import Listing, Marketplace, Product, ProductMatch, LiveQuery
from app.services.normalizer import extract_attributes, normalize_title, tokens
from app.services.comparison import serialize_listing, serialize_group, group_explanation
from app.services.sorting import sort_listings, sort_groups
from app.live import serpapi

CACHE_TTL = timedelta(hours=6)
MAX_RESULTS = 12
_LOCK = threading.Lock()   # one ingest at a time (the UI can fire duplicate searches)

# Only these stores are shown (owner's list). (aliases, slug, display name, colour)
MAIN_STORES = [
    (("amazon",), "amazon", "Amazon", "#FF9900"),
    (("flipkart",), "flipkart", "Flipkart", "#2874F0"),
    (("meesho",), "meesho", "Meesho", "#9F2089"),
    (("myntra",), "myntra", "Myntra", "#FF3F6C"),
    (("nykaa", "nykaa fashion", "nykaaman"), "nykaa", "Nykaa", "#FC2779"),
    (("ajio", "ajio luxe"), "ajio", "AJIO", "#2C4152"),
    (("tata cliq", "tatacliq", "tata cliq luxury", "tata cliq fashion"), "tatacliq", "Tata CLiQ", "#DA1C5C"),
    (("nike", "nike india"), "nike", "Nike", "#111111"),
    (("foot locker", "footlocker", "foot locker india"), "footlocker", "Foot Locker", "#E4002B"),
    (("apple", "apple store", "apple india"), "apple", "Apple Store", "#111111"),
    (("zepto",), "zepto", "Zepto", "#5E17EB"),
    (("croma",), "croma", "Croma", "#00A99D"),
    (("reliance digital", "reliancedigital"), "reliance-digital", "Reliance Digital", "#E42529"),
    (("vijay sales", "vijaysales"), "vijay-sales", "Vijay Sales", "#E31E24"),
    (("firstcry",), "firstcry", "FirstCry", "#F37021"),
    (("decathlon", "decathlon india"), "decathlon", "Decathlon", "#0082C3"),
    (("shoppers stop", "shoppersstop"), "shoppers-stop", "Shoppers Stop", "#1A1A1A"),
    (("lifestyle", "lifestyle stores", "lifestylestores"), "lifestyle", "Lifestyle", "#E91E63"),
    (("westside",), "westside", "Westside", "#8B6F47"),
    (("h&m", "h & m", "hm", "h&m india"), "hm", "H&M", "#E50010"),
    (("zara", "zara india"), "zara", "Zara", "#111111"),
    (("adidas", "adidas india"), "adidas", "Adidas", "#111111"),
    (("puma", "puma india"), "puma", "Puma", "#BA2025"),
    (("samsung", "samsung shop", "samsung india", "samsung store"), "samsung", "Samsung", "#1428A0"),
    (("oneplus", "oneplus india", "oneplus store"), "oneplus", "OnePlus", "#EB0028"),
    (("reliance trends", "trends"), "reliance-trends", "Reliance Trends", "#D71920"),
    (("jiomart", "jiomart grocery", "jio mart"), "jiomart", "JioMart", "#0078AD"),
    (("blinkit",), "blinkit", "Blinkit", "#F8CB46"),
    (("swiggy instamart", "instamart", "swiggy"), "swiggy-instamart", "Swiggy Instamart", "#FC8019"),
    (("bigbasket", "big basket", "bb now"), "bigbasket", "BigBasket", "#84C225"),
]
_ALIAS = {a: (slug, name, colour) for aliases, slug, name, colour in MAIN_STORES for a in aliases}
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _store_key(source: str) -> str:
    s = re.split(r"\s+[-–|]\s+", (source or "").strip())[0].lower().strip()
    s = re.sub(r"^(www|buy|shop|store|m)\.", "", s)
    return re.sub(r"\.(com|in|co\.in|shop|store)$", "", s).strip()


def main_store(source: str) -> tuple[str, str, str] | None:
    """The owner's store list only: exact store name, or the store name followed by a word
    ("JioMart Grocery", "NIKE India"). Resellers like "iCrescent Apple Store" don't match."""
    key = _store_key(source)
    if key in _ALIAS:
        return _ALIAS[key]
    first = key.split(" ")[0] if key else ""
    two = " ".join(key.split(" ")[:2])
    for cand in (two, first):
        if cand in _ALIAS and cand not in ("trends", "swiggy", "apple", "samsung", "lifestyle"):
            return _ALIAS[cand]
    if key.startswith(("apple ", "samsung ")) and key.endswith(("store", "shop", "india", "online store")):
        return _ALIAS[first]
    return None


def _store(source: str) -> tuple[str, str, str]:
    hit = main_store(source)
    if hit:
        return hit
    key = _store_key(source) or "store"
    return re.sub(r"[^a-z0-9]+", "-", key).strip("-")[:40] or "store", (source or "Store").strip()[:90], "#555555"


def _marketplace(db: Session, source: str, link: str = "") -> Marketplace:
    slug, name, colour = _store(source)
    m = db.execute(select(Marketplace).where(Marketplace.slug == slug)).scalar_one_or_none()
    if m is None:
        host = urlparse(link).netloc if link else ""
        m = Marketplace(slug=slug, name=name, logo_url="", base_url=f"https://{host}" if host else "",
                        brand_color=colour)
        db.add(m)
        db.flush()
    return m


UNKNOWN_DAYS = 99     # delivery time not stated by the store → never counted as "fastest"
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


def _delivery(text: str | None) -> tuple[int, str]:
    """Days from Google/store delivery text. Unknown → UNKNOWN_DAYS (shown as "See store")."""
    raw = (text or "").strip()
    t = raw.lower()
    if not t:
        return UNKNOWN_DAYS, "See store for delivery"
    if re.search(r"\b\d+\s*(min|mins|minutes|hr|hrs|hour|hours)\b", t) or "today" in t or "same day" in t:
        return 0, raw
    if "tomorrow" in t or "next day" in t:
        return 1, raw
    m = re.search(r"(\d+)\s*(?:-|to)?\s*(\d+)?\s*(?:business\s+|working\s+)?days?", t)
    if m:
        return int(m.group(2) or m.group(1)), raw
    now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)      # IST
    m = re.search(r"\b(\d{1,2})\s*(" + "|".join(MONTHS) + r")", t) or re.search(r"\b(" + "|".join(MONTHS) + r")[a-z]*\s*(\d{1,2})\b", t)
    if m:
        a, b = m.groups()
        day, mon = (int(a), b) if a.isdigit() else (int(b), a)
        try:
            target = now.replace(month=MONTHS.index(mon[:3]) + 1, day=day)
            if target.date() < now.date():
                target = target.replace(year=now.year + 1)
            return max(0, (target.date() - now.date()).days), raw
        except ValueError:
            pass
    for i, d in enumerate(WEEKDAYS):
        if re.search(rf"\b{d}", t):
            return (i - now.weekday()) % 7 or 7, raw
    return UNKNOWN_DAYS, raw


_DEBUG: dict[str, object] = {}     # last raw payload summaries (free to inspect via /api/debug)


def _page_token(r: dict) -> str:
    for k in ("immersive_product_page_token", "page_token"):
        if r.get(k):
            return r[k]
    api = r.get("serpapi_immersive_product_api") or ""
    return (parse_qs(urlparse(api).query).get("page_token") or [""])[0]


def _num(v, default=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _raw_from_amazon(r: dict) -> RawListing | None:
    price = _num(r.get("extracted_price"))
    title = (r.get("title") or "").strip()
    link = r.get("link_clean") or r.get("link") or ""
    if not price or not title or not link or round(price, 2) != round(price):
        return None
    delivery = r.get("delivery")
    if isinstance(delivery, list):
        delivery = next((d for d in delivery if "deliver" in d.lower() or "get it" in d.lower()), delivery[0] if delivery else "")
    days, dtext = _delivery(delivery)
    asin = r.get("asin") or hashlib.md5(title.encode()).hexdigest()[:10]
    return RawListing(
        listing_id=f"a-{asin}", marketplace="amazon", seller_name="Amazon.in", title=title, description="",
        brand=None, category="", price=price, mrp=max(price, _num(r.get("extracted_old_price"), price)), currency="INR",
        image_url=r.get("thumbnail") or "", image_hash="", rating=_num(r.get("rating")),
        review_count=int(_num(r.get("reviews"))), delivery_days=days, availability="in_stock",
        product_attributes={"_live": True, "_delivery_text": dtext, "_direct": True, "_source": "Amazon.in",
                            "_position": 0.5 + (r.get("position") or 50)},
        product_url=link,
    )


def _raw_from_result(r: dict) -> RawListing | None:
    price = _num(r.get("extracted_price"))
    title = (r.get("title") or "").strip()
    if not price or not title:
        return None
    if round(price, 2) != round(price) or ("₹" not in str(r.get("price", "₹")) and "rs" not in str(r.get("price", "")).lower()):
        return None        # converted foreign-currency price → overseas store, not useful for India
    source = (r.get("source") or "").strip()
    if not source or main_store(source) is None:
        return None        # not one of the main stores → not shown
    slug, _, _ = _store(source)
    pid = r.get("product_id") or hashlib.md5((title + source).encode()).hexdigest()[:16]
    days, dtext = _delivery(r.get("delivery"))
    return RawListing(
        listing_id=f"g-{pid}-{slug}-{hashlib.md5(title.lower().encode()).hexdigest()[:8]}"[:100], marketplace=slug, seller_name=source, title=title,
        description=r.get("snippet") or "", brand=None, category="", price=price,
        mrp=max(price, _num(r.get("extracted_old_price"), price)), currency="INR",
        image_url=r.get("thumbnail") or "", image_hash="", rating=_num(r.get("rating")),
        review_count=int(_num(r.get("reviews"))), delivery_days=days, availability="in_stock",
        product_attributes={"_live": True, "_delivery_text": dtext, "_page_token": _page_token(r),
                            "_google_link": r.get("product_link") or "", "_source": source,
                            "_position": r.get("position") or 99},
        product_url="",
    )


def _listing_row(db: Session, l: RawListing, product_id: int, source: str, link: str = "") -> Listing:
    attrs = {**extract_attributes(l), **{k: v for k, v in l.product_attributes.items() if k.startswith("_")}}
    m = _marketplace(db, source, link)
    row = Listing(
        listing_id=l.listing_id, product_id=product_id, marketplace_id=m.id, seller_name=l.seller_name,
        title=l.title[:300], description=l.description or "", brand=l.brand, category=l.category,
        price=l.price, mrp=l.mrp, discount_percentage=l.discount_percentage, currency="INR",
        image_url=l.image_url[:500], image_hash=l.image_hash or "", rating=l.rating, review_count=l.review_count,
        delivery_days=l.delivery_days, delivery_date="", delivery_text=attrs["_delivery_text"][:100],
        availability=l.availability, product_attributes=attrs, normalized_title=normalize_title(l.title)[:300],
        search_text=" ".join(tokens(product_text(l, attrs))), product_url="",
    )
    db.add(row)
    db.flush()
    row.product_url = link or l.product_url or f"/api/go/{row.id}"
    return row


def _ingest(db: Session, raws: list[RawListing], query: str = "") -> list[int]:
    """Persist results; returns product ids in Google rank order."""
    existing = {l.listing_id: l for l in db.execute(
        select(Listing).where(Listing.listing_id.in_([r.listing_id for r in raws]))).scalars().all()}
    fresh = []
    for r in raws:
        row = existing.get(r.listing_id)
        if row is not None:           # refresh price on an already-known listing
            row.price, row.mrp = r.price, r.mrp
            row.discount_percentage = r.discount_percentage
        else:
            fresh.append(r)
    groups, pairs, _ = live_cluster(fresh, query) if fresh else ([], [], {})
    rows: dict[str, Listing] = {}
    for g in groups:
        p = Product(canonical_title=g.canonical_title[:300], brand=g.brand, category=g.category,
                    description=g.description, canonical_image=g.canonical_image,
                    attributes={k: v for k, v in g.attributes.items() if not str(k).startswith("_")})
        db.add(p)
        db.flush()
        for l in g.listings:
            rows[l.listing_id] = _listing_row(db, l, p.id, l.seller_name)
    for pm in pairs:
        r = pm.result
        db.add(ProductMatch(listing_a_id=rows[pm.a].id, listing_b_id=rows[pm.b].id, text_score=r.text_score,
                            image_score=r.image_score, attribute_score=r.attribute_score,
                            combined_score=r.combined_score, match_type=r.match_type,
                            reasons={"reasons": [{"label": x.label, "status": x.status} for x in r.reasons]}))
    db.commit()
    order: list[int] = []
    for r in raws:
        row = existing.get(r.listing_id) or rows.get(r.listing_id)     # (duplicates dropped by clustering)
        if row is not None and row.product_id not in order:
            order.append(row.product_id)
    return order


def _norm_query(q: str) -> str:
    return re.sub(r"\s+", " ", q.strip().lower())[:200]


def live_search(db: Session, query: str, pincode: str | None, sort: str, filters: dict, passes) -> dict:
    with _LOCK:
        return _live_search(db, query, pincode, sort, filters, passes)


def _live_search(db: Session, query: str, pincode: str | None, sort: str, filters: dict, passes) -> dict:
    loc = locations.resolve(pincode)
    key = f"{_norm_query(query)}|{loc['location']}"[:200]
    cached = db.execute(select(LiveQuery).where(LiveQuery.query == key)).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    error = None
    if cached and now - cached.fetched_at.replace(tzinfo=timezone.utc) < CACHE_TTL:
        product_ids = cached.product_ids or []
    else:
        try:
            from concurrent.futures import ThreadPoolExecutor
            from app.config import get_settings
            with ThreadPoolExecutor(2) as pool:
                g_fut = pool.submit(serpapi.shopping_search, query, loc["location"])
                a_fut = pool.submit(serpapi.amazon_search, query) if get_settings().amazon_search else None
                results = g_fut.result()
                try:
                    amazon = a_fut.result() if a_fut else []
                except serpapi.LiveDataError:
                    amazon = []                      # Amazon is a bonus source; never fail the search over it
            _DEBUG["last_search"] = {"query": query, "location": loc["location"], "count": len(results),
                                     "items": [{k: (v if k in ("title", "source", "price", "delivery", "position") else
                                                   (bool(v) if not isinstance(v, (int, float)) else v))
                                                for k, v in r.items()} for r in results[:40]]}
            raws = [x for x in (_raw_from_result(r) for r in results) if x]
            raws += [x for x in (_raw_from_amazon(r) for r in amazon[:20]) if x]
            product_ids = _ingest(db, raws, query)
            if cached:
                cached.product_ids, cached.fetched_at = product_ids, now
            else:
                db.add(LiveQuery(query=key, product_ids=product_ids, fetched_at=now))
            db.commit()
        except serpapi.LiveDataError as e:
            db.rollback()
            error = str(e)
            product_ids = cached.product_ids if cached else []

    groups = []
    for rank, pid in enumerate(product_ids):
        product = db.get(Product, pid)
        if product is None:
            continue
        rows = db.execute(select(Listing).options(joinedload(Listing.marketplace))
                          .where(Listing.product_id == pid)).scalars().all()
        listings = [l for l in (serialize_listing(x) for x in rows) if passes(l, filters)]
        if not listings:
            continue
        ids = [x.id for x in rows]
        matches = db.execute(select(ProductMatch).where(
            ProductMatch.listing_a_id.in_(ids), ProductMatch.listing_b_id.in_(ids),
            ProductMatch.match_type == "EXACT_MATCH")).scalars().all()
        g = serialize_group(product, sort_listings(listings, sort), group_explanation(matches))
        g["_rank"] = rank
        groups.append(g)
    _score_groups(groups, query)
    # Keep the page focused: hide spare parts / refurbished / suspicious listings, drop weak matches, cap at 12.
    groups = [g for g in groups if not g["flags"]]
    strong = [g for g in groups if g["relevance"] >= 0.5]
    if len(strong) >= 3:
        groups = strong
    groups = sorted(groups, key=lambda g: (-g["relevance"], -len(g["marketplaces"]), g["_rank"]))
    seen_titles: set[str] = set()
    unique = []
    for g in groups:                       # two cards that look identical to a shopper → keep the better one
        key = re.sub(r"[^a-z0-9]+", " ", g["canonical_title"].lower()).strip()
        if key in seen_titles:
            continue
        seen_titles.add(key)
        unique.append(g)
    groups = unique[:MAX_RESULTS]
    if sort == "relevance":
        groups.sort(key=lambda g: (-g["relevance"], g["_rank"]))
    else:
        groups = sort_groups(groups, sort)
    for g in groups:
        g.pop("_rank", None)
    return {"query": query, "pincode": loc["pincode"], "location": loc["label"], "sort": sort, "groups": groups,
            "total_groups": len(groups), "total_listings": sum(g["listing_count"] for g in groups),
            "delivery_is_demo": False, "live": True, "error": error}


def _score_groups(groups: list[dict], query: str) -> None:
    """Relevance = how well the product matches the query, minus penalties for extra model
    variants, refurbished units, accessories and suspiciously cheap listings."""
    q_ident = identity(query, query)
    q_tokens = {t for t in (q_ident.model | q_ident.family)}
    q_words = set(query.lower().split())
    prices = sorted(g["price_min"] for g in groups if g["price_min"])
    median = prices[len(prices) // 2] if prices else 0
    for g in groups:
        idn = identity(g["canonical_title"], query)
        tokens = idn.model | idn.family
        hit = sum(1 for t in q_tokens if t in tokens)
        if q_ident.storage:
            hit += 1 if idn.storage == q_ident.storage else 0
        total = len(q_tokens) + (1 if q_ident.storage else 0)
        score = hit / total if total else 0.5
        flags = []
        extra = [m for m in idn.model - q_ident.model
                 if m in VARIANT_WORDS or m == "e"
                 or any(m != qm and m.startswith(qm) and qm.isdigit() for qm in q_ident.model)]
        score -= 0.2 * len(extra)
        if q_ident.brand:                                   # "maybelline mascara" → other brands rank lower
            g_brand = idn.brand or (idn.tokens[0] if idn.tokens else None)
            if g_brand != q_ident.brand:
                score -= 0.6
        if idn.condition == "refurbished" and not ({"refurbished", "renewed", "used", "second"} & q_words):
            score -= 0.25
            flags.append("refurbished")
        if idn.accessory:
            score -= 0.6
            flags.append("accessory")
        if median and g["price_min"] < 0.4 * median:
            score -= 0.9
            flags.append("unusually_low_price")
        score += 0.05 * (len(g["marketplaces"]) - 1)
        g["relevance"] = round(score, 3)
        g["flags"] = flags


def _same_store(a: str, b: str) -> bool:
    return _store(a)[0] == _store(b)[0]


def enrich_product(db: Session, product: Product) -> str | None:
    """Fetch every store selling this product (one SerpApi call, cached on the product)."""
    with _LOCK:
        db.refresh(product)
        return _enrich(db, product)


def _enrich(db: Session, product: Product) -> str | None:
    if (product.attributes or {}).get("_enriched"):
        return None
    rows = db.execute(select(Listing).options(joinedload(Listing.marketplace))
                      .where(Listing.product_id == product.id)).scalars().all()
    token = next((r.product_attributes.get("_page_token") for r in rows if r.product_attributes.get("_page_token")), "")
    if not token:
        product.attributes = {**(product.attributes or {}), "_enrich_note": "no page token on any listing"}
        db.commit()
        return None
    try:
        res = serpapi.product_stores(token)
    except serpapi.LiveDataError as e:
        product.attributes = {**(product.attributes or {}), "_enrich_note": f"error: {e}"}
        db.commit()
        return str(e)
    notes = {"stores_returned": len(res.get("stores") or []), "added": 0, "linked": 0, "skipped": []}
    _DEBUG[f"stores:{product.id}"] = {"keys": sorted(res.keys()), "stores": [
        {k: s.get(k) for k in ("name", "title", "price", "extracted_price", "details_and_offers")} | {"has_link": bool(s.get("link"))}
        for s in (res.get("stores") or [])[:20]]}
    base = min(rows, key=lambda r: r.product_attributes.get("_position", 99))
    base_id = identity(base.title)
    ref_price = min(r.price for r in rows)
    for s in res.get("stores", []) or []:
        link, name = s.get("link") or "", s.get("name") or "Store"
        price = _num(s.get("extracted_price"))
        if main_store(name) is None:
            notes["skipped"].append(f"{name}: not a main store")
            continue
        if not link or not price or round(price, 2) != round(price):
            notes["skipped"].append(f"{name}: no link/price or foreign")
            continue                                   # no link, or converted foreign price
        if max(price, ref_price) / max(1.0, min(price, ref_price)) > 1.6:
            notes["skipped"].append(f"{name}: price {price} too far from {ref_price}")
            continue                                   # not plausibly the same item
        st_title = s.get("title") or ""
        if st_title:
            sid = identity(st_title)
            if any(getattr(sid, k) and getattr(base_id, k) and getattr(sid, k) != getattr(base_id, k)
                   for k in ("storage", "ram", "colour", "condition")):
                notes["skipped"].append(f"{name}: different variant ({st_title[:60]})")
                continue                               # a different variant of the product
        match = next((r for r in rows if _same_store(r.seller_name, name)), None)
        placeholder = next((r for r in rows if r.seller_name == "Multiple stores"), None)
        if match is None and placeholder is not None:
            # The search result had no merchant name: it becomes this store's offer.
            placeholder.seller_name, placeholder.marketplace_id = name, _marketplace(db, name, link).id
            match = placeholder
        if match is not None:        # the search listing → give it the direct store link
            match.product_url = link
            match.price = price
            match.product_attributes = {**match.product_attributes, "_direct": True}
            notes["linked"] += 1
            continue
        offers = s.get("details_and_offers") or []
        dline = next((o for o in offers if "deliver" in o.lower() or "arrives" in o.lower() or "shipping" in o.lower()), "")
        days, dtext = _delivery(dline or s.get("shipping"))
        raw = RawListing(
            listing_id=f"s-{product.id}-{_store(name)[0]}"[:100], marketplace=_store(name)[0], seller_name=name,
            title=s.get("title") or base.title, description="", brand=None, category="", price=price,
            mrp=max(price, _num(s.get("extracted_original_price"), price)), currency="INR",
            image_url=base.image_url, image_hash="", rating=_num(s.get("rating")),
            review_count=int(_num(s.get("reviews"))), delivery_days=days, availability="in_stock",
            product_attributes={"_live": True, "_delivery_text": dtext, "_direct": True, "_source": name}, product_url=link,
        )
        if db.execute(select(Listing).where(Listing.listing_id == raw.listing_id)).scalar_one_or_none() is None:
            _listing_row(db, raw, product.id, name, link)
            notes["added"] += 1
    notes["skipped"] = notes["skipped"][:15]
    product.attributes = {**(product.attributes or {}), "_enriched": True, "_enrich_note": notes}
    db.commit()
    return None


def resolve_store_link(db: Session, listing_id: int) -> str:
    row = db.get(Listing, listing_id)
    if row is None:
        return ""
    if row.product_attributes.get("_direct") and not row.product_url.startswith("/api/go/"):
        return row.product_url
    product = db.get(Product, row.product_id)
    if product is not None:
        enrich_product(db, product)
        db.refresh(row)
        if not row.product_url.startswith("/api/go/"):
            return row.product_url
    return row.product_attributes.get("_google_link") or store_search_url(row.seller_name, row.title)


STORE_SEARCH = {
    "amazon": "https://www.amazon.in/s?k={q}", "flipkart": "https://www.flipkart.com/search?q={q}",
    "myntra": "https://www.myntra.com/{q}", "ajio": "https://www.ajio.com/search/?text={q}",
    "nykaa": "https://www.nykaa.com/search/result/?q={q}", "meesho": "https://www.meesho.com/search?q={q}",
    "croma": "https://www.croma.com/searchB?q={q}", "reliance-digital": "https://www.reliancedigital.in/products?q={q}",
    "jiomart": "https://www.jiomart.com/search/{q}", "tatacliq": "https://www.tatacliq.com/search/?searchCategory=all&text={q}",
    "vijay-sales": "https://www.vijaysales.com/search/{q}", "snapdeal": "https://www.snapdeal.com/search?keyword={q}",
}


def store_search_url(source: str, title: str) -> str:
    from urllib.parse import quote_plus
    q = quote_plus(" ".join(title.split()[:8]))
    tpl = STORE_SEARCH.get(_store(source)[0])
    return tpl.format(q=q) if tpl else f"https://www.google.com/search?tbm=shop&q={q}"
