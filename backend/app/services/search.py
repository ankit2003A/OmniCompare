"""Search / retrieval.

Stage 1 (DB): candidate retrieval with LIKE on `search_text` — portable across SQLite and
PostgreSQL. Swap for PostgreSQL tsvector or an Elasticsearch/OpenSearch client here; the
rest of the pipeline only needs a list of candidate Listing rows.
Stage 2 (Python): IDF-weighted query coverage ranking, grouped by product.
"""
import math
from sqlalchemy import or_, func, select
from sqlalchemy.orm import Session, joinedload
from app.models import Listing, Product, ProductMatch, SearchHistory
from app.services.normalizer import tokens
from app.services.comparison import serialize_listing, serialize_group, group_explanation
from app.services.sorting import sort_listings, sort_groups

MIN_COVERAGE = 0.55
SYNONYMS = {"hoodie": {"sweatshirt"}, "sweatshirt": {"hoodie"}, "case": {"cover"}, "cover": {"case"},
            "sneaker": {"shoe"}, "shoe": {"sneaker"}, "earbud": {"tws", "earphone"}, "earphone": {"earbud"}}


def _idf_table(db: Session) -> dict[str, float]:
    rows = db.execute(select(Listing.search_text)).scalars().all()
    df: dict[str, int] = {}
    for txt in rows:
        for t in set(txt.split()):
            df[t] = df.get(t, 0) + 1
    n = max(1, len(rows))
    return {t: 1 + math.log(n / c) for t, c in df.items()}


def _coverage(query_tokens: list[str], text: str, idf: dict[str, float]) -> float:
    words = set(text.split())
    total = got = 0.0
    for q in query_tokens:
        w = idf.get(q, 2.5)
        total += w
        if q in words:
            got += w
        elif any(s in words for s in SYNONYMS.get(q, ())):
            got += 0.7 * w
        elif len(q) >= 4 and any(x.startswith(q) for x in words):
            got += 0.6 * w
    return got / total if total else 0.0


def search_products(db: Session, query: str, pincode: str | None = None, sort: str = "relevance",
                    filters: dict | None = None, record: bool = True) -> dict:
    qtoks = tokens(query)
    if not qtoks:
        return {"query": query, "groups": [], "total_groups": 0, "total_listings": 0}
    if record:
        try:
            db.add(SearchHistory(query=query.strip(), pincode=pincode))
            db.commit()
        except Exception:      # history is a convenience; never fail a search over it
            db.rollback()

    stmt = (select(Listing).options(joinedload(Listing.marketplace), joinedload(Listing.product))
            .where(or_(*[Listing.search_text.like(f"%{t}%") for t in qtoks])))
    candidates = db.execute(stmt).scalars().all()
    idf = _idf_table(db)

    scored: dict[int, list[tuple[Listing, float]]] = {}
    for l in candidates:
        cov = _coverage(qtoks, l.search_text, idf)
        if cov < MIN_COVERAGE:
            continue
        rel = round(cov + 0.05 * min(1.0, l.review_count / 10000), 4)
        scored.setdefault(l.product_id, []).append((l, rel))

    groups = []
    f = filters or {}
    for pid, items in scored.items():
        product = items[0][0].product
        listings = [serialize_listing(l, rel) for l, rel in items]
        # Filters apply at the listing level; a group survives if any listing passes.
        listings = [l for l in listings if _passes(l, f)]
        if not listings:
            continue
        member_ids = [l.id for l, _ in items]
        matches = db.execute(select(ProductMatch).where(
            ProductMatch.listing_a_id.in_(member_ids), ProductMatch.listing_b_id.in_(member_ids),
            ProductMatch.match_type == "EXACT_MATCH")).scalars().all()
        g = serialize_group(product, sort_listings(listings, sort), group_explanation(matches),
                            relevance=max(r for _, r in items))
        groups.append(g)

    groups = sort_groups(groups, sort)
    return {"query": query, "pincode": pincode, "sort": sort, "groups": groups,
            "total_groups": len(groups), "total_listings": sum(g["listing_count"] for g in groups),
            "delivery_is_demo": True}


def _passes(l: dict, f: dict) -> bool:
    if f.get("marketplaces") and l["marketplace"]["slug"] not in f["marketplaces"]:
        return False
    if f.get("price_min") is not None and l["price"] < f["price_min"]:
        return False
    if f.get("price_max") is not None and l["price"] > f["price_max"]:
        return False
    if f.get("max_delivery_days") is not None and l["delivery"]["deliveryDays"] > f["max_delivery_days"]:
        return False
    if f.get("min_rating") is not None and l["rating"] < f["min_rating"]:
        return False
    if f.get("brands") and (l["brand"] or "").lower() not in [b.lower() for b in f["brands"]]:
        return False
    if f.get("in_stock_only") and l["availability"] == "out_of_stock":
        return False
    return True


def suggestions(db: Session, q: str, limit: int = 8) -> dict:
    q = (q or "").strip().lower()
    hist_stmt = select(SearchHistory.query).order_by(SearchHistory.created_at.desc()).limit(50)
    history = []
    for h in db.execute(hist_stmt).scalars().all():
        if h.lower() not in history and (not q or q in h.lower()):
            history.append(h)
    products = []
    if q:
        stmt = select(Product.canonical_title).where(func.lower(Product.canonical_title).like(f"%{q}%")).limit(limit)
        products = db.execute(stmt).scalars().all()
    return {"history": history[:5], "products": list(products)[:limit]}
