from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from app.db import get_db
from app.models import Listing, Marketplace, Product, ProductMatch
from app.schemas import MatchRequest, CompareRequest, DeliveryEstimateRequest, ListingInput
from app.adapters.base import RawListing
from app.adapters.mock import ADAPTERS
from app.matching.engine import match_listings
from app.services.search import search_products, suggestions
from app.services.comparison import serialize_listing, serialize_group, group_explanation, compare
from app.services.sorting import sort_listings, SORT_OPTIONS
from app.services.delivery import get_delivery_estimate
from app.config import get_settings
from app.services.search import _passes
from app.live import service as live
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/api")


def _listing_opts():
    return (joinedload(Listing.marketplace), joinedload(Listing.product))


@router.get("/search")
def search(q: str = Query(..., min_length=1), pincode: str | None = None, sort: str = "relevance",
           marketplaces: str | None = None, price_min: float | None = None, price_max: float | None = None,
           max_delivery_days: int | None = None, min_rating: float | None = None, brands: str | None = None,
           in_stock_only: bool = False, db: Session = Depends(get_db)):
    if sort not in SORT_OPTIONS:
        raise HTTPException(400, f"Unknown sort '{sort}'. Options: {', '.join(SORT_OPTIONS)}")
    filters = {
        "marketplaces": marketplaces.split(",") if marketplaces else None,
        "price_min": price_min, "price_max": price_max, "max_delivery_days": max_delivery_days,
        "min_rating": min_rating, "brands": brands.split(",") if brands else None,
        "in_stock_only": in_stock_only,
    }
    if get_settings().live_mode:
        return live.live_search(db, q, pincode, sort, filters, _passes)
    return search_products(db, q, pincode, sort, filters)


@router.get("/usage")
def usage():
    """SerpApi quota (free call). Useful to keep an eye on the monthly search budget."""
    from app.live import serpapi
    return {"live_mode": get_settings().live_mode, **serpapi.account()}


@router.get("/go/{listing_id}")
def go_to_store(listing_id: int, db: Session = Depends(get_db)):
    """Redirect to the real store page for a live listing (resolved lazily, then cached)."""
    url = live.resolve_store_link(db, listing_id)
    if not url:
        raise HTTPException(404, "Store link not available")
    return RedirectResponse(url, status_code=302)


@router.get("/search/suggestions")
def search_suggestions(q: str = "", db: Session = Depends(get_db)):
    return suggestions(db, q)


@router.get("/sort-options")
def sort_options():
    return [{"value": k, **v} for k, v in SORT_OPTIONS.items()]


@router.get("/marketplaces")
def marketplaces(db: Session = Depends(get_db)):
    rows = db.execute(select(Marketplace)).scalars().all()
    return [{"id": m.id, "slug": m.slug, "name": m.name, "logo_url": m.logo_url,
             "base_url": m.base_url, "brand_color": m.brand_color} for m in rows]


def _product_or_404(db: Session, product_id: int) -> Product:
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Product group not found")
    return p


def _group_listings(db: Session, product_id: int) -> list[Listing]:
    return db.execute(select(Listing).options(*_listing_opts())
                      .where(Listing.product_id == product_id)).scalars().all()


def _group_matches(db: Session, ids: list[int], types=("EXACT_MATCH",)):
    if not ids:
        return []
    return db.execute(select(ProductMatch).where(
        ProductMatch.listing_a_id.in_(ids), ProductMatch.listing_b_id.in_(ids),
        ProductMatch.match_type.in_(types))).scalars().all()


@router.get("/products/{product_id}")
def product_detail(product_id: int, pincode: str | None = None, sort: str = "price_asc",
                   db: Session = Depends(get_db)):
    product = _product_or_404(db, product_id)
    live_error = live.enrich_product(db, product) if get_settings().live_mode else None
    rows = _group_listings(db, product_id)
    listings = sort_listings([serialize_listing(l) for l in rows], sort)
    explanation = group_explanation(_group_matches(db, [l.id for l in rows]))
    group = serialize_group(product, listings, explanation)
    group["similar_products"] = _similar(db, product, [l.id for l in rows])
    group["images"] = list(dict.fromkeys([l["image_url"] for l in listings]))
    group["delivery_is_demo"] = not get_settings().live_mode
    group["live"] = get_settings().live_mode
    group["error"] = live_error
    group["pincode"] = pincode
    return group


@router.get("/products/{product_id}/listings")
def product_listings(product_id: int, sort: str = "price_asc", db: Session = Depends(get_db)):
    _product_or_404(db, product_id)
    return sort_listings([serialize_listing(l) for l in _group_listings(db, product_id)], sort)


@router.get("/products/{product_id}/similar")
def product_similar(product_id: int, db: Session = Depends(get_db)):
    product = _product_or_404(db, product_id)
    return _similar(db, product, [l.id for l in _group_listings(db, product_id)])


def _similar(db: Session, product: Product, member_ids: list[int]) -> list[dict]:
    if not member_ids:
        return []
    from sqlalchemy import or_, and_
    rows = db.execute(select(ProductMatch).where(
        ProductMatch.match_type == "SIMILAR",
        or_(ProductMatch.listing_a_id.in_(member_ids), ProductMatch.listing_b_id.in_(member_ids)),
        ~and_(ProductMatch.listing_a_id.in_(member_ids), ProductMatch.listing_b_id.in_(member_ids)),
    )).scalars().all()
    best: dict[int, ProductMatch] = {}
    for m in rows:
        other_id = m.listing_b_id if m.listing_a_id in member_ids else m.listing_a_id
        other = db.get(Listing, other_id)
        if other is None or other.product_id == product.id:
            continue
        if other.product_id not in best or m.combined_score > best[other.product_id].combined_score:
            best[other.product_id] = m
    out = []
    for pid, m in sorted(best.items(), key=lambda kv: -kv[1].combined_score):
        p = db.get(Product, pid)
        listings = [serialize_listing(l) for l in _group_listings(db, pid)]
        g = serialize_group(p, sort_listings(listings, "price_asc"))
        g["similarity"] = round(m.combined_score * 100)
        g["reasons"] = (m.reasons or {}).get("reasons", [])
        out.append(g)
    return out


def _to_raw(l: Listing | None, inp: ListingInput | None, tag: str) -> RawListing:
    if l is not None:
        return RawListing(l.listing_id, l.marketplace.slug, l.seller_name, l.title, l.description, l.brand,
                          l.category or "", l.price, l.mrp, l.currency, l.image_url, l.image_hash, l.rating,
                          l.review_count, l.delivery_days, l.availability, l.product_attributes, l.product_url)
    if inp is None:
        raise HTTPException(400, f"Provide listing_{tag}_id or listing_{tag}")
    return RawListing(f"adhoc-{tag}", "adhoc", "", inp.title, inp.description, inp.brand, inp.category or "",
                      0, 0, "INR", inp.image_url, inp.image_hash, 0, 0, 0, "in_stock", inp.product_attributes, "")


@router.post("/match")
def match(req: MatchRequest, db: Session = Depends(get_db)):
    la = db.execute(select(Listing).options(*_listing_opts()).where(Listing.id == req.listing_a_id)).scalar_one_or_none() if req.listing_a_id else None
    lb = db.execute(select(Listing).options(*_listing_opts()).where(Listing.id == req.listing_b_id)).scalar_one_or_none() if req.listing_b_id else None
    a, b = _to_raw(la, req.listing_a, "a"), _to_raw(lb, req.listing_b, "b")
    s = get_settings()
    return {**match_listings(a, b).as_dict(),
            "weights": {"text": s.match_weight_text, "attribute": s.match_weight_attribute, "image": s.match_weight_image},
            "thresholds": {"exact": s.match_threshold_exact, "similar": s.match_threshold_similar}}


@router.post("/compare")
def compare_listings(req: CompareRequest, db: Session = Depends(get_db)):
    rows = db.execute(select(Listing).options(*_listing_opts()).where(Listing.id.in_(req.listing_ids))).scalars().all()
    listings = sort_listings([serialize_listing(l) for l in rows], req.sort)
    return {"listings": listings, **compare(listings), "pincode": req.pincode, "delivery_is_demo": True}


@router.post("/delivery-estimate")
def delivery_estimate(req: DeliveryEstimateRequest):
    if req.marketplace not in ADAPTERS:
        raise HTTPException(404, "Unknown marketplace")
    info = get_delivery_estimate(req.marketplace, req.listing_id, req.pincode)
    return {**info.as_dict(), "pincode": req.pincode, "marketplace": req.marketplace,
            "note": "Demo delivery estimate — seeded data, not a live marketplace query."}
