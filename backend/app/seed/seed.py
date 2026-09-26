"""Seed the database: adapters → normalize → match → cluster → persist.

Run:  python -m app.seed.seed
"""
from sqlalchemy.orm import Session
from app.db import Base, engine, SessionLocal
from app.models import Marketplace, Product, Listing, ProductMatch, SearchHistory
from app.adapters.mock import ADAPTERS
from app.matching.clustering import cluster
from app.matching.engine import product_text
from app.services.normalizer import extract_attributes, normalize_title, tokens
from app.services.delivery import build_delivery_info


def run_seed(db: Session | None = None, verbose: bool = True) -> dict:
    own = db is None
    Base.metadata.create_all(bind=engine if own else db.get_bind())
    db = db or SessionLocal()
    try:
        for model in (ProductMatch, Listing, Product, Marketplace, SearchHistory):
            db.query(model).delete()
        db.commit()

        mkts = {}
        for slug, adapter in ADAPTERS.items():
            m = Marketplace(slug=slug, name=adapter.name, logo_url=adapter.logo_url,
                            base_url=adapter.base_url, brand_color=adapter.brand_color)
            db.add(m)
            mkts[slug] = m
        db.flush()

        raw = [l for a in ADAPTERS.values() for l in a.all_listings()]
        groups, pairs = cluster(raw)

        listing_rows: dict[str, Listing] = {}
        for g in groups:
            product = Product(canonical_title=g.canonical_title, brand=g.brand, category=g.category,
                              description=g.description, canonical_image=g.canonical_image,
                              attributes=g.attributes)
            db.add(product)
            db.flush()
            for l in g.listings:
                attrs = extract_attributes(l)
                d = build_delivery_info(l.delivery_days, l.availability != "out_of_stock")
                row = Listing(
                    listing_id=l.listing_id, product_id=product.id, marketplace_id=mkts[l.marketplace].id,
                    seller_name=l.seller_name, title=l.title, description=l.description, brand=l.brand,
                    category=l.category, price=l.price, mrp=l.mrp, discount_percentage=l.discount_percentage,
                    currency=l.currency, image_url=l.image_url, image_hash=l.image_hash, rating=l.rating,
                    review_count=l.review_count, delivery_days=l.delivery_days, delivery_date=d.deliveryDate,
                    delivery_text=d.deliveryText, availability=l.availability, product_attributes=attrs,
                    normalized_title=normalize_title(l.title),
                    search_text=" ".join(tokens(product_text(l, attrs))), product_url=l.product_url,
                )
                db.add(row)
                listing_rows[l.listing_id] = row
        db.flush()

        for p in pairs:
            r = p.result
            db.add(ProductMatch(listing_a_id=listing_rows[p.a].id, listing_b_id=listing_rows[p.b].id,
                                text_score=r.text_score, image_score=r.image_score,
                                attribute_score=r.attribute_score, combined_score=r.combined_score,
                                match_type=r.match_type, reasons={"reasons": [{"label": x.label, "status": x.status} for x in r.reasons]}))
        db.commit()
        summary = {"marketplaces": len(mkts), "listings": len(raw), "products": len(groups),
                   "multi_listing_groups": sum(1 for g in groups if len(g.listings) > 1),
                   "matches": len(pairs)}
        if verbose:
            print("Seeded:", summary)
        return summary
    finally:
        if own:
            db.close()


if __name__ == "__main__":
    run_seed()
