"""Delivery abstraction.

The MVP returns seeded delivery data through the marketplace adapter. The signature
`get_delivery_estimate(marketplace, product, pincode)` is the future hook for real
serviceability APIs; `is_demo` tells the UI to show the "Demo delivery estimate" label.
"""
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from app.adapters.mock import get_adapter


@dataclass
class DeliveryInfo:
    deliveryDays: int
    deliveryDate: str
    deliveryText: str
    available: bool
    isDemo: bool = True

    def as_dict(self) -> dict:
        return asdict(self)


def delivery_text_for(days: int) -> str:
    if days <= 0:
        return "Today"
    if days == 1:
        return "Tomorrow"
    if days <= 3:
        return f"In {days} days"
    return f"By {(date.today() + timedelta(days=days)).strftime('%a, %d %b')}"


def build_delivery_info(days: int, available: bool = True, is_demo: bool = True) -> DeliveryInfo:
    return DeliveryInfo(
        deliveryDays=days,
        deliveryDate=(date.today() + timedelta(days=days)).isoformat(),
        deliveryText=delivery_text_for(days) if available else "Currently unavailable",
        available=available,
        isDemo=is_demo,
    )


def get_delivery_estimate(marketplace: str, product_id: str, pincode: str | None) -> DeliveryInfo:
    est = get_adapter(marketplace).get_delivery_estimate(product_id, pincode or "")
    return build_delivery_info(est.delivery_days, est.available, est.is_demo)
