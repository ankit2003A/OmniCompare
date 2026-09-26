"""Sorting for listings and product groups. Fastest delivery sorts on delivery_days, never price."""

SORT_OPTIONS = {
    "relevance":        {"label": "Relevance"},
    "price_asc":        {"label": "Price: Low → High"},
    "price_desc":       {"label": "Price: High → Low"},
    "delivery_fastest": {"label": "Fastest delivery"},
    "delivery_slowest": {"label": "Slowest delivery"},
    "rating_desc":      {"label": "Highest rated"},
    "rating_asc":       {"label": "Lowest rated"},
    "discount_desc":    {"label": "Highest discount"},
}

_LISTING_KEYS = {
    "price_asc":        (lambda l: (l["price"],), False),
    "price_desc":       (lambda l: (l["price"],), True),
    "delivery_fastest": (lambda l: (not l["delivery"]["available"], l["delivery"]["deliveryDays"], l["price"]), False),
    "delivery_slowest": (lambda l: (l["delivery"]["deliveryDays"],), True),
    "rating_desc":      (lambda l: (l["rating"], l["review_count"]), True),
    "rating_asc":       (lambda l: (l["rating"],), False),
    "discount_desc":    (lambda l: (l["discount_percentage"],), True),
    "relevance":        (lambda l: (l.get("relevance", 0), l["rating"]), True),
}

_GROUP_KEYS = {
    "price_asc":        (lambda g: (g["price_min"],), False),
    "price_desc":       (lambda g: (g["price_max"],), True),
    "delivery_fastest": (lambda g: (g["fastest"]["deliveryDays"] if g["fastest"] else 99, g["price_min"]), False),
    "delivery_slowest": (lambda g: (g["slowest_days"],), True),
    "rating_desc":      (lambda g: (g["rating_max"],), True),
    "rating_asc":       (lambda g: (g["rating_min"],), False),
    "discount_desc":    (lambda g: (g["discount_max"],), True),
    "relevance":        (lambda g: (g.get("relevance", 0), g["listing_count"]), True),
}


def sort_listings(listings: list[dict], sort: str) -> list[dict]:
    key, reverse = _LISTING_KEYS.get(sort, _LISTING_KEYS["relevance"])
    return sorted(listings, key=key, reverse=reverse)


def sort_groups(groups: list[dict], sort: str) -> list[dict]:
    key, reverse = _GROUP_KEYS.get(sort, _GROUP_KEYS["relevance"])
    return sorted(groups, key=key, reverse=reverse)
