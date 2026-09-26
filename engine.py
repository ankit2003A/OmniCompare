"""Product identity engine: decides whether two listings are the same product.

    match_score = text * W_text + attribute * W_attr + image * W_img

Weights and thresholds come from Settings (env-configurable). Hard attribute
conflicts (different brand / size / quantity / model / shade) cap the classification
regardless of score — a 4.5-star shoe in UK 8 is not the same purchasable item as UK 9.
"""
from dataclasses import dataclass, field
from app.adapters.base import RawListing
from app.ai.embeddings import get_embedding_provider, cosine
from app.ai.image_similarity import calculate_image_similarity, ImageRef
from app.config import get_settings
from app.services.normalizer import extract_attributes, tokens, RELATED_CATEGORIES

EXACT_MATCH, SIMILAR, DIFFERENT = "EXACT_MATCH", "SIMILAR", "DIFFERENT"

# Attribute weights for attribute_similarity; only attributes present on BOTH sides count.
ATTRIBUTE_WEIGHTS = {"brand": 3.0, "model": 3.0, "category": 2.0, "colour": 2.0, "size": 2.0,
                     "quantity": 2.0, "shade": 2.0, "wattage": 2.0, "capacity": 2.0,
                     "variant": 1.5, "material": 1.0, "fit": 1.0, "gender": 1.0, "storage": 2.0, "ram": 1.5}
# Attributes where a mismatch means "not the same purchasable item" (caps at SIMILAR)
VARIANT_ATTRIBUTES = ("size", "quantity", "shade", "model", "wattage", "capacity", "variant", "colour", "storage", "ram")
# Attributes where a mismatch means "different product entirely" (caps at DIFFERENT)
IDENTITY_ATTRIBUTES = ("brand", "category")
LABELS = {"brand": "brand", "category": "product category", "colour": "colour", "size": "size",
          "quantity": "quantity", "shade": "shade", "model": "model", "material": "material",
          "fit": "fit", "gender": "gender", "wattage": "wattage", "capacity": "capacity",
          "variant": "variant", "storage": "storage", "ram": "RAM"}


@dataclass
class Reason:
    label: str
    status: str  # ok | warn | info


@dataclass
class MatchResult:
    text_score: float
    attribute_score: float
    image_score: float
    combined_score: float
    match_type: str
    reasons: list[Reason] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "text_score": self.text_score, "attribute_score": self.attribute_score,
            "image_score": self.image_score, "combined_score": self.combined_score,
            "match_type": self.match_type,
            "reasons": [{"label": r.label, "status": r.status} for r in self.reasons],
        }


_IDF: dict[str, float] = {}


def set_corpus(listings: list[RawListing]) -> None:
    """Compute inverse document frequency over the listing corpus so that filler tokens
    ("men", "black") weigh less than identity tokens ("511", "airdopes")."""
    import math
    df: dict[str, int] = {}
    for l in listings:
        for t in set(tokens(l.title)):
            df[t] = df.get(t, 0) + 1
    n = max(1, len(listings))
    _IDF.clear()
    _IDF.update({t: 1.0 + math.log(n / c) for t, c in df.items()})


def _idf(t: str) -> float:
    return _IDF.get(t, 1.0 + (2.0 if any(ch.isdigit() for ch in t) else 1.0))


def product_text(listing: RawListing, attrs: dict | None = None) -> str:
    """Normalized text the matcher compares: title + brand + category + key attributes."""
    attrs = attrs if attrs is not None else extract_attributes(listing)
    keys = ("brand", "category", "colour", "size", "model", "quantity", "shade", "wattage", "capacity", "variant")
    return listing.title + " " + " ".join(str(attrs[k]) for k in keys if attrs.get(k))


def text_similarity(a: RawListing, b: RawListing, attrs_a: dict | None = None, attrs_b: dict | None = None) -> float:
    pa, pb = product_text(a, attrs_a), product_text(b, attrs_b)
    ta, tb = set(tokens(pa)), set(tokens(pb))
    if not ta or not tb:
        return 0.0
    shared = sum(_idf(t) for t in ta & tb)
    dice = 2 * shared / (sum(_idf(t) for t in ta) + sum(_idf(t) for t in tb))
    provider = get_embedding_provider()
    cos = cosine(provider.embed_text(pa), provider.embed_text(pb))
    return round(0.5 * dice + 0.5 * cos, 4)


def attribute_similarity(attrs_a: dict, attrs_b: dict) -> tuple[float, list[Reason]]:
    reasons: list[Reason] = []
    total = 0.0
    got = 0.0
    for key, w in ATTRIBUTE_WEIGHTS.items():
        va, vb = attrs_a.get(key), attrs_b.get(key)
        if va is None or vb is None:
            if key in ("size", "material", "quantity", "model") and (va is None) != (vb is None):
                reasons.append(Reason(f"{LABELS[key].capitalize()} unavailable on one listing", "warn"))
            continue
        total += w
        if va == vb:
            got += w
            reasons.append(Reason(f"Same {LABELS[key]}", "ok"))
        elif key == "category" and frozenset({va, vb}) in RELATED_CATEGORIES:
            got += w * 0.5
            reasons.append(Reason(f"Related category ({va} / {vb})", "warn"))
        else:
            reasons.append(Reason(f"{LABELS[key].capitalize()} differs ({va} vs {vb})", "warn"))
    if total == 0:
        return 0.5, reasons
    return round(got / total, 4), reasons


def classify(score: float, thresholds: tuple[float, float] | None = None) -> str:
    s = get_settings()
    exact, similar = thresholds or (s.match_threshold_exact, s.match_threshold_similar)
    if score >= exact:
        return EXACT_MATCH
    if score >= similar:
        return SIMILAR
    return DIFFERENT


def match_listings(a: RawListing, b: RawListing, attrs_a: dict | None = None,
                   attrs_b: dict | None = None) -> MatchResult:
    s = get_settings()
    attrs_a = attrs_a if attrs_a is not None else extract_attributes(a)
    attrs_b = attrs_b if attrs_b is not None else extract_attributes(b)

    text = text_similarity(a, b, attrs_a, attrs_b)
    attr, reasons = attribute_similarity(attrs_a, attrs_b)
    image = calculate_image_similarity(ImageRef(a.image_url, a.image_hash), ImageRef(b.image_url, b.image_hash))

    combined = (text * s.match_weight_text + attr * s.match_weight_attribute
                + image * s.match_weight_image)
    combined = round(min(1.0, combined), 4)

    if image >= 0.9:
        reasons.append(Reason("Similar product imagery", "ok"))
    elif image >= 0.75:
        reasons.append(Reason("Partially similar imagery", "warn"))
    else:
        reasons.append(Reason("Imagery differs", "warn"))
    if text >= 0.7:
        reasons.append(Reason("Similar product title", "ok"))
    elif text >= 0.45:
        reasons.append(Reason("Partially similar title", "warn"))
    else:
        reasons.append(Reason("Titles differ", "warn"))

    match_type = classify(combined)

    # Hard caps: attribute conflicts override the score.
    for key in IDENTITY_ATTRIBUTES:
        va, vb = attrs_a.get(key), attrs_b.get(key)
        if va and vb and va != vb and frozenset({va, vb}) not in RELATED_CATEGORIES:
            match_type = DIFFERENT
            combined = min(combined, s.match_threshold_similar - 0.01)
    if match_type != DIFFERENT:
        for key in VARIANT_ATTRIBUTES:
            va, vb = attrs_a.get(key), attrs_b.get(key)
            if va and vb and va != vb:
                match_type = SIMILAR if match_type == EXACT_MATCH else match_type
                combined = min(combined, s.match_threshold_exact - 0.01)
    # Category cousins (hoodie vs sweatshirt) are never the same purchasable item.
    ca, cb = attrs_a.get("category"), attrs_b.get("category")
    if ca and cb and ca != cb and match_type == EXACT_MATCH:
        match_type = SIMILAR
        combined = min(combined, s.match_threshold_exact - 0.01)

    return MatchResult(text, attr, image, round(combined, 4), match_type, reasons)
