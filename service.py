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
from app.matching.clustering import cluster
from app.matching.engine import product_text
from app.models import Listing, Marketplace, Product, ProductMatch, LiveQuery
from app.services.normalizer import extract_attributes, normalize_title, tokens
from app.services.comparison import serialize_listing, serialize_group, group_explanation
from app.services.sorting import sort_listings, sort_groups
from app.live import serpapi
from app.live.image_hash import hash_images

CACHE_TTL = timedelta(hours=6)
_LOCK = threading.Lock()   # one ingest at a time (the UI can fire duplicate searches)

KNOWN_STORES = [  # (match substring, slug, display name, colour)
    ("amazon", "amazon", "Amazon", "#FF9900"), ("flipkart", "flipkart", "Flipkart", "#2874F0"),
    ("myntra", "myntra", "Myntra", "#FF3F6C"), ("ajio", "ajio", "AJIO", "#2C4152"),
    ("nykaa", "nykaa", "Nykaa", "#FC2779"), ("meesho", "meesho", "Meesho", "#9F2089"),
    ("croma", "croma", "Croma", "#00A99D"), ("reliance digital", "reliance-digital", "Reliance Digital", "#E42529"),
    ("jiomart", "jiomart", "JioMart", "#0078AD"), ("tata cliq", "tatacliq", "Tata CLiQ", "#DA1C5C"),
    ("vijay sales", "vijay-sales", "Vijay Sales", "#E31E24"), ("snapdeal", "snapdeal", "Snapdeal", "#E40046"),
    ("bigbasket", "bigbasket", "BigBasket", "#84C225"), ("blinkit", "blinkit", "Blinkit", "#F8CB46"),
    ("zepto", "zepto", "Zepto", "#5E17EB"), ("swiggy", "swiggy-instamart", "Swiggy Instamart", "#FC8019"),
    ("pepperfry", "pepperfry", "Pepperfry", "#F16521"), ("decathlon", "decathlon", "Decathlon", "#0082C3"),
    ("apple", "apple", "Apple Store", "#111111"), ("samsung", "samsung", "Samsung Shop", "#1428A0"),
]
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _store(source: str) -> tuple[str, str, str]:
    s = (source or "Store").lower()
    for sub, slug, name, colour in KNOWN_STORES:
        if sub in s:
            return slug, name, colour
    slug = re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:40] or "store"
    return slug, source.strip()[:90] or "Store", "#555555"


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


def _delivery(text: str | None) -> tuple[int, str]:
    """Best-effort days from Google's delivery text; unknown → 5 with the store's own text."""
    t = (text or "").lower()
    if not t:
        return 5, "See store for delivery"
    if "today" in t:
        return 0, text
    if "tomorrow" in t:
        return 1, text
    m = re.search(r"(\d+)\s*(?:-\s*\d+\s*)?(?:business\s+)?days?", t)
    if m:
        return int(m.group(1)), text
    for i, d in enumerate(WEEKDAYS):
        if re.search(rf"\b{d}", t):
            delta = (i - datetime.now(timezone.utc).weekday()) % 7 or 7
            return delta, text
    return 5, text


def _page_token(r: dict) -> str:
    if r.get("immersive_product_page_token"):
        return r["immersive_product_page_token"]
    api = r.get("serpapi_immersive_product_api") or ""
    return (parse_qs(urlparse(api).query).get("page_token") or [""])[0]


def _num(v, default=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _raw_from_result(r: dict) -> RawListing | None:
    price = _num(r.get("extracted_price"))
    title = (r.get("title") or "").strip()
    if not price or not title:
        return None
    source = r.get("source") or "Store"
    slug, _, _ = _store(source)
    pid = r.get("product_id") or hashlib.md5((title + source).encode()).hexdigest()[:16]
    days, dtext = _delivery(r.get("delivery"))
    return RawListing(
        listing_id=f"g-{pid}-{slug}"[:100], marketplace=slug, seller_name=source, title=title,
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
    row.product_url = link or f"/api/go/{row.id}"
    return row


def _ingest(db: Session, raws: list[RawListing]) -> list[int]:
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
    for r, h in zip(fresh, hash_images([r.image_url for r in fresh])):
        r.image_hash = h
    groups, pairs = cluster(fresh) if fresh else ([], [])
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
        row = existing.get(r.listing_id) or rows.get(r.listing_id)
        if row is not None and row.product_id not in order:
            order.append(row.product_id)
    return order


def _norm_query(q: str) -> str:
    return re.sub(r"\s+", " ", q.strip().lower())[:200]


def live_search(db: Session, query: str, pincode: str | None, sort: str, filters: dict, passes) -> dict:
    with _LOCK:
        return _live_search(db, query, pincode, sort, filters, passes)


def _live_search(db: Session, query: str, pincode: str | None, sort: str, filters: dict, passes) -> dict:
    key = _norm_query(query)
    cached = db.execute(select(LiveQuery).where(LiveQuery.query == key)).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    error = None
    if cached and now - cached.fetched_at.replace(tzinfo=timezone.utc) < CACHE_TTL:
        product_ids = cached.product_ids or []
    else:
        try:
            raws = [x for x in (_raw_from_result(r) for r in serpapi.shopping_search(query)) if x]
            product_ids = _ingest(db, raws)
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
        listings = [l for l in (serialize_listing(x, 1 - rank / 100) for x in rows) if passes(l, filters)]
        if not listings:
            continue
        ids = [x.id for x in rows]
        matches = db.execute(select(ProductMatch).where(
            ProductMatch.listing_a_id.in_(ids), ProductMatch.listing_b_id.in_(ids),
            ProductMatch.match_type == "EXACT_MATCH")).scalars().all()
        groups.append(serialize_group(product, sort_listings(listings, sort), group_explanation(matches),
                                      relevance=1 - rank / 100))
    groups = sort_groups(groups, sort)
    return {"query": query, "pincode": pincode, "sort": sort, "groups": groups,
            "total_groups": len(groups), "total_listings": sum(g["listing_count"] for g in groups),
            "delivery_is_demo": False, "live": True, "error": error}


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
        return None
    try:
        res = serpapi.product_stores(token)
    except serpapi.LiveDataError as e:
        return str(e)
    base = rows[0]
    for s in res.get("stores", []) or []:
        link, name = s.get("link") or "", s.get("name") or "Store"
        price = _num(s.get("extracted_price"))
        if not link or not price:
            continue
        match = next((r for r in rows if _same_store(r.seller_name, name)), None)
        if match is not None:        # the search listing → give it the direct store link
            match.product_url = link
            match.price = price
            match.product_attributes = {**match.product_attributes, "_direct": True}
            continue
        details = " · ".join(s.get("details_and_offers") or [])
        days, dtext = _delivery(details or s.get("shipping"))
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
    product.attributes = {**(product.attributes or {}), "_enriched": True}
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
