from pydantic import BaseModel, Field
from typing import Optional


class ListingInput(BaseModel):
    """Ad-hoc listing for POST /api/match (all fields optional except title)."""
    title: str
    brand: Optional[str] = None
    category: Optional[str] = None
    description: str = ""
    image_url: str = ""
    image_hash: str = ""
    product_attributes: dict = Field(default_factory=dict)


class MatchRequest(BaseModel):
    listing_a_id: Optional[int] = None
    listing_b_id: Optional[int] = None
    listing_a: Optional[ListingInput] = None
    listing_b: Optional[ListingInput] = None


class CompareRequest(BaseModel):
    listing_ids: list[int]
    pincode: Optional[str] = None
    sort: str = "price_asc"


class DeliveryEstimateRequest(BaseModel):
    marketplace: str
    listing_id: str
    pincode: str
