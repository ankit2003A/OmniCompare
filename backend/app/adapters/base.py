"""Marketplace adapter interface.

Every marketplace (real or mock) is accessed through this interface. The rest of the
application only ever sees `RawListing` objects, so swapping a mock adapter for a real
API-backed adapter never touches the matching, comparison or UI layers.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RawListing:
    listing_id: str
    marketplace: str            # slug: amazon | flipkart | meesho | myntra | nykaa | ajio
    seller_name: str
    title: str
    description: str
    brand: Optional[str]
    category: str
    price: float
    mrp: float
    currency: str
    image_url: str
    image_hash: str             # perceptual hash (hex). Mock adapters ship a simulated one.
    rating: float
    review_count: int
    delivery_days: int
    availability: str           # in_stock | low_stock | out_of_stock
    product_attributes: dict = field(default_factory=dict)
    product_url: str = ""

    @property
    def discount_percentage(self) -> float:
        if self.mrp <= 0:
            return 0.0
        return round(max(0.0, (self.mrp - self.price) / self.mrp * 100), 1)


@dataclass
class DeliveryEstimate:
    delivery_days: int
    available: bool
    is_demo: bool = True
    source: str = "seeded"


class MarketplaceAdapter:
    slug: str = ""
    name: str = ""
    base_url: str = ""
    logo_url: str = ""
    brand_color: str = "#333333"

    def search(self, query: str) -> list[RawListing]:
        raise NotImplementedError

    def get_product(self, product_id: str) -> Optional[RawListing]:
        raise NotImplementedError

    def get_delivery_estimate(self, product_id: str, pincode: str) -> DeliveryEstimate:
        raise NotImplementedError

    def all_listings(self) -> list[RawListing]:
        """Used by the seeder / offline indexer. Real adapters may not support this."""
        raise NotImplementedError
