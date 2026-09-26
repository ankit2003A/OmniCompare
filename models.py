from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, ForeignKey, JSON, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class Marketplace(Base):
    __tablename__ = "marketplaces"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    logo_url: Mapped[str] = mapped_column(String(500))
    base_url: Mapped[str] = mapped_column(String(500))
    brand_color: Mapped[str] = mapped_column(String(20), default="#333333")
    listings: Mapped[list["Listing"]] = relationship(back_populates="marketplace")


class Product(Base):
    """A canonical product group produced by the identity engine."""
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    canonical_title: Mapped[str] = mapped_column(String(300))
    brand: Mapped[str | None] = mapped_column(String(100))
    category: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    canonical_image: Mapped[str | None] = mapped_column(String(500))
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    listings: Mapped[list["Listing"]] = relationship(back_populates="product")


class Listing(Base):
    __tablename__ = "listings"
    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[str] = mapped_column(String(100), unique=True)  # marketplace-native id
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    marketplace_id: Mapped[int] = mapped_column(ForeignKey("marketplaces.id"))
    seller_name: Mapped[str] = mapped_column(String(150))
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    brand: Mapped[str | None] = mapped_column(String(100))
    category: Mapped[str | None] = mapped_column(String(100))
    price: Mapped[float] = mapped_column(Float)
    mrp: Mapped[float] = mapped_column(Float)
    discount_percentage: Mapped[float] = mapped_column(Float, default=0)
    currency: Mapped[str] = mapped_column(String(5), default="INR")
    image_url: Mapped[str] = mapped_column(String(500))
    image_hash: Mapped[str] = mapped_column(String(64), default="")  # perceptual-hash stand-in
    rating: Mapped[float] = mapped_column(Float, default=0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    delivery_days: Mapped[int] = mapped_column(Integer)
    delivery_date: Mapped[str] = mapped_column(String(20))
    delivery_text: Mapped[str] = mapped_column(String(100))
    availability: Mapped[str] = mapped_column(String(30), default="in_stock")
    product_attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    normalized_title: Mapped[str] = mapped_column(String(300), default="")
    search_text: Mapped[str] = mapped_column(Text, default="")  # tokens for retrieval; swap for tsvector/ES later
    product_url: Mapped[str] = mapped_column(String(500))

    marketplace: Mapped[Marketplace] = relationship(back_populates="listings")
    product: Mapped[Product | None] = relationship(back_populates="listings")


class ProductMatch(Base):
    __tablename__ = "product_matches"
    id: Mapped[int] = mapped_column(primary_key=True)
    listing_a_id: Mapped[int] = mapped_column(ForeignKey("listings.id"))
    listing_b_id: Mapped[int] = mapped_column(ForeignKey("listings.id"))
    text_score: Mapped[float] = mapped_column(Float)
    image_score: Mapped[float] = mapped_column(Float)
    attribute_score: Mapped[float] = mapped_column(Float)
    combined_score: Mapped[float] = mapped_column(Float)
    match_type: Mapped[str] = mapped_column(String(20))  # EXACT_MATCH | SIMILAR | DIFFERENT
    reasons: Mapped[dict] = mapped_column(JSON, default=dict)


class LiveQuery(Base):
    """Cache of live search results (query → product ids in rank order) to save API calls."""
    __tablename__ = "live_queries"
    id: Mapped[int] = mapped_column(primary_key=True)
    query: Mapped[str] = mapped_column(String(200), unique=True)
    product_ids: Mapped[list] = mapped_column(JSON, default=list)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class SearchHistory(Base):
    __tablename__ = "search_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    query: Mapped[str] = mapped_column(String(200))
    pincode: Mapped[str | None] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
