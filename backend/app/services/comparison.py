"""Comparison engine: turns listings of a product group into cheapest / fastest / ranges,
and serializes listings and groups for the API."""
from collections import Counter
from app.models import Listing, Product, ProductMatch
from app.services.delivery import build_delivery_info


def serialize_listing(l: Listing, relevance: float | None = None) -> dict:
    delivery = build_delivery_info(l.delivery_days, l.availability != "out_of_stock")
    d = {
        "id": l.id, "listing_id": l.listing_id, "product_id": l.product_id,
        "marketplace": {"slug": l.marketplace.slug, "name": l.marketplace.name,
                        "logo_url": l.marketplace.logo_url, "brand_color": l.marketplace.brand_color},
        "seller_name": l.seller_name, "title": l.title, "description": l.description,
        "brand": l.brand, "category": l.category,
        "price": l.price, "mrp": l.mrp, "discount_percentage": l.discount_percentage,
        "currency": l.currency, "image_url": l.image_url, "rating": l.rating,
        "review_count": l.review_count, "availability": l.availability,
        "delivery_days": delivery.deliveryDays, "delivery_date": delivery.deliveryDate,
        "delivery_text": delivery.deliveryText, "delivery": delivery.as_dict(),
        "product_attributes": l.product_attributes, "product_url": l.product_url,
    }
    if relevance is not None:
        d["relevance"] = relevance
    return d


def compare(listings: list[dict]) -> dict:
    """Cheapest / fastest / ranges. Never labels anything 'best'."""
    if not listings:
        return {"cheapest": None, "fastest": None, "price_min": 0, "price_max": 0,
                "rating_max": 0, "rating_min": 0, "discount_max": 0, "slowest_days": 0}
    available = [l for l in listings if l["delivery"]["available"]] or listings
    cheapest = min(available, key=lambda l: l["price"])
    fastest = min(available, key=lambda l: (l["delivery"]["deliveryDays"], l["price"]))
    return {
        "cheapest": {"listing_id": cheapest["id"], "price": cheapest["price"],
                     "marketplace": cheapest["marketplace"]},
        "fastest": {"listing_id": fastest["id"], "deliveryDays": fastest["delivery"]["deliveryDays"],
                    "deliveryText": fastest["delivery"]["deliveryText"], "marketplace": fastest["marketplace"]},
        "price_min": min(l["price"] for l in listings),
        "price_max": max(l["price"] for l in listings),
        "rating_max": max(l["rating"] for l in listings),
        "rating_min": min(l["rating"] for l in listings),
        "discount_max": max(l["discount_percentage"] for l in listings),
        "slowest_days": max(l["delivery"]["deliveryDays"] for l in listings),
    }


def group_explanation(matches: list[ProductMatch]) -> dict:
    """Aggregate pairwise match results of a group into one transparent explanation."""
    if not matches:
        return {"confidence": None, "reasons": [], "pair_count": 0}
    confidence = sum(m.combined_score for m in matches) / len(matches)
    ok, warn = Counter(), Counter()
    for m in matches:
        seen = set()
        for r in (m.reasons or {}).get("reasons", []):
            if r["label"] in seen:
                continue
            seen.add(r["label"])
            (ok if r["status"] == "ok" else warn)[r["label"]] += 1
    n = len(matches)
    reasons = [{"label": lbl, "status": "ok"} for lbl, c in ok.most_common() if c >= n / 2]
    reasons += [{"label": lbl, "status": "warn"} for lbl, c in warn.most_common() if c >= max(1, n / 3)]
    return {"confidence": round(confidence * 100), "reasons": reasons, "pair_count": n,
            "scores": {"text": round(sum(m.text_score for m in matches) / n, 3),
                       "attribute": round(sum(m.attribute_score for m in matches) / n, 3),
                       "image": round(sum(m.image_score for m in matches) / n, 3)}}


def serialize_group(product: Product, listings: list[dict], explanation: dict | None = None,
                    relevance: float | None = None) -> dict:
    cmp = compare(listings)
    marketplaces = []
    for l in listings:
        if l["marketplace"]["slug"] not in [m["slug"] for m in marketplaces]:
            marketplaces.append(l["marketplace"])
    d = {
        "id": product.id, "canonical_title": product.canonical_title, "brand": product.brand,
        "category": product.category, "description": product.description,
        "canonical_image": product.canonical_image, "attributes": product.attributes,
        "listing_count": len(listings), "marketplaces": marketplaces,
        "listings": listings, "match": explanation or {"confidence": None, "reasons": []},
        **cmp,
    }
    if relevance is not None:
        d["relevance"] = round(relevance, 3)
    return d
