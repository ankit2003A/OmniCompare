"""Mock marketplace adapters backed by the seeded catalog.

To integrate a real marketplace: subclass MarketplaceAdapter, implement search /
get_product / get_delivery_estimate against the official API, and register it in
`ADAPTERS`. Nothing else changes.
"""
from typing import Optional
from app.adapters.base import MarketplaceAdapter, RawListing, DeliveryEstimate
from app.seed.catalog import CATALOG, MARKETPLACES


class MockAdapterBase(MarketplaceAdapter):
    def _listings(self) -> list[RawListing]:
        return [l for l in CATALOG if l.marketplace == self.slug]

    def all_listings(self) -> list[RawListing]:
        return self._listings()

    def search(self, query: str) -> list[RawListing]:
        q = query.lower().split()
        return [l for l in self._listings() if any(t in l.title.lower() for t in q)]

    def get_product(self, product_id: str) -> Optional[RawListing]:
        return next((l for l in self._listings() if l.listing_id == product_id), None)

    def get_delivery_estimate(self, product_id: str, pincode: str) -> DeliveryEstimate:
        # Seeded data only. A real adapter would call the marketplace serviceability API
        # with the pincode. We deliberately do not vary the estimate by pincode so nobody
        # mistakes it for live data.
        listing = self.get_product(product_id)
        if listing is None:
            return DeliveryEstimate(delivery_days=5, available=False)
        return DeliveryEstimate(
            delivery_days=listing.delivery_days,
            available=listing.availability != "out_of_stock",
        )


def _make(slug: str):
    meta = MARKETPLACES[slug]
    cls = type(
        f"Mock{meta['name']}Adapter",
        (MockAdapterBase,),
        {"slug": slug, "name": meta["name"], "base_url": meta["base_url"],
         "logo_url": meta["logo_url"], "brand_color": meta["brand_color"]},
    )
    return cls


MockAmazonAdapter = _make("amazon")
MockFlipkartAdapter = _make("flipkart")
MockMeeshoAdapter = _make("meesho")
MockMyntraAdapter = _make("myntra")
MockNykaaAdapter = _make("nykaa")
MockAjioAdapter = _make("ajio")

ADAPTERS: dict[str, MarketplaceAdapter] = {
    a.slug: a() for a in [MockAmazonAdapter, MockFlipkartAdapter, MockMeeshoAdapter,
                          MockMyntraAdapter, MockNykaaAdapter, MockAjioAdapter]
}


def get_adapter(slug: str) -> MarketplaceAdapter:
    return ADAPTERS[slug]
