"""Normalize raw listings: clean titles, canonicalize brands and extract attributes.

Adapter-supplied attributes always win over attributes inferred from the title.
"""
import re
from app.adapters.base import RawListing

STOPWORDS = {"for", "with", "the", "and", "a", "an", "of", "in", "by", "to", "x", "-", "&",
             "new", "original", "pack", "type", "lace", "up", "lace-up", "casual", "all", "types",
             # marketplace filler that carries no product identity
             "solid", "stretchable", "lightweight", "mobile", "next", "nature", "super", "fast",
             "charging", "adapter", "laptop", "big", "logo", "compartment", "c"}

BRAND_ALIASES = {
    "maybelline new york": "maybelline", "lakmé": "lakme", "levis": "levi's", "levi s": "levi's",
    "boat lifestyle": "boat", "american tourister": "american tourister", "nike inc": "nike",
}
GENERIC_BRANDS = {"", "generic", "unbranded", "no brand", "none", "others"}

CATEGORY_ALIASES = {
    "hooded sweatshirt": "hoodie", "hoodies": "hoodie", "sweatshirts": "sweatshirt",
    "sneaker": "sneakers", "shoes": "sneakers", "earbud": "earbuds", "tws": "earbuds",
    "lip color": "lipstick", "lip colour": "lipstick", "back cover": "phone case",
    "cover": "phone case", "case": "phone case", "facewash": "face wash", "jean": "jeans",
}
# Categories that are close cousins get partial attribute credit instead of zero.
RELATED_CATEGORIES = {frozenset({"hoodie", "sweatshirt"}), frozenset({"sneakers", "shoes"})}

COLOURS = ["black", "white", "navy", "grey", "gray", "blue", "dark blue", "dark indigo", "indigo",
           "red", "pink", "teal", "brown", "tan", "silver", "clear", "crystal clear", "transparent",
           "thunder grey", "bold black", "very black"]
COLOUR_ALIASES = {"gray": "grey", "thunder grey": "grey", "bold black": "black", "very black": "black",
                  "crystal clear": "clear", "transparent": "clear", "dark blue": "dark indigo", "indigo": "dark indigo"}
MATERIALS = ["cotton blend", "cotton", "polyester", "fleece", "leather", "silicone", "tpu", "rayon", "denim"]
FITS = ["oversized", "loose fit", "loose", "slim taper", "slim", "regular", "relaxed"]
FIT_ALIASES = {"loose fit": "oversized", "loose": "oversized"}
GENDERS = {"women's": "women", "womens": "women", "women": "women", "woman": "women", "ladies": "women",
           "men's": "men", "mens": "men", "men": "men", "man": "men", "unisex": "unisex"}


def canonical_brand(brand: str | None) -> str | None:
    if not brand:
        return None
    b = brand.strip().lower().replace("é", "e")
    b = BRAND_ALIASES.get(b, b)
    return None if b in GENERIC_BRANDS else b


def canonical_category(cat: str | None) -> str | None:
    if not cat:
        return None
    c = cat.strip().lower()
    return CATEGORY_ALIASES.get(c, c)


TITLE_ALIASES = [
    ("maybelline new york", "maybelline"), ("lakmé", "lakme"), ("levis", "levi's"),
    ("9 to 5", "9to5"), (" lo ", " low "), ("hooded sweatshirt", "hoodie"), ("lip color", "lipstick"),
    ("back cover", "case"), ("true wireless", "tws"), ("bluetooth headset", "earbuds"),
    ("dark blue", "dark indigo"), ("thunder grey", "grey"), ("crystal clear", "clear"), ("transparent", "clear"),
]


def normalize_title(title: str) -> str:
    t = " " + title.lower().replace("é", "e").replace("’", "'") + " "
    for a, b in TITLE_ALIASES:
        t = t.replace(a, b)
    t = re.sub(r"(\d)\s+(ml|g|l|ltrs|ltr|w|gb)\b", r"\1\2", t)           # "7.2 ml" -> "7.2ml"
    t = re.sub(r"\bltrs?\b", "l", t)
    t = re.sub(r"\b(\d{2})w(?:\s*x\s*\d{2}l)?\b", r"\1", t)                  # "32w x 32l" -> "32"
    t = re.sub(r"\b(uk|size)\s+(\d{1,2})\b", r"\2", t)
    t = re.sub(r"[()\[\],/|]", " ", t)
    t = re.sub(r"\s+-\s+", " ", t)
    t = re.sub(r"[^a-z0-9.'\-+ ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def tokens(text: str) -> list[str]:
    out = []
    for tok in normalize_title(text).split():
        tok = tok.strip(".'-")
        if not tok or tok in STOPWORDS:
            continue
        if tok in GENDERS:
            tok = GENDERS[tok]
        elif len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss") and not tok[-2].isdigit():
            tok = tok[:-1]                                                    # crude singularization
        out.append(tok)
    return out


def _find_first(text: str, options: list[str]) -> str | None:
    for opt in sorted(options, key=len, reverse=True):
        if re.search(rf"\b{re.escape(opt)}\b", text):
            return opt
    return None


def extract_attributes(listing: RawListing) -> dict:
    """Return a normalized attribute dict merging adapter attrs (priority) with title inference."""
    text = normalize_title(listing.title + " " + (listing.description or ""))
    attrs: dict = {}

    colour = _find_first(text, COLOURS)
    if colour:
        attrs["colour"] = COLOUR_ALIASES.get(colour, colour)
    material = _find_first(text, MATERIALS)
    if material:
        attrs["material"] = material
    fit = _find_first(text, FITS)
    if fit:
        attrs["fit"] = FIT_ALIASES.get(fit, fit)
    for word, g in GENDERS.items():
        if re.search(rf"\b{re.escape(word)}\b", text):
            attrs["gender"] = g
            break
    qty = re.search(r"\b(\d+(?:\.\d+)?)(ml|g|l|gb)\b", text)
    if qty:
        attrs["quantity"] = f"{qty.group(1)} {qty.group(2)}"
    watt = re.search(r"\b(\d+)w\b", text)
    if watt:
        attrs["wattage"] = f"{watt.group(1)}W"
    size = re.search(r"\b(?:uk|size)\s*(\d{1,2})\b", text) or re.search(r"\b(\d{2})w\b", text)
    if size:
        attrs["size"] = size.group(1)
    else:
        s = re.search(r"\b(xs|s|m|l|xl|xxl|free)\b(?![a-z])", text.replace(" size", ""))
        if s and s.group(1) not in ("s", "l", "m"):   # single letters are too noisy from titles
            attrs["size"] = s.group(1)

    # Adapter-provided attributes win; normalize their values the same way.
    for k, v in (listing.product_attributes or {}).items():
        if v is None or v == "":
            continue
        key = k.lower()
        val = str(v).strip().lower().replace("é", "e")
        if key in ("colour", "color"):
            val = COLOUR_ALIASES.get(val, val)
            key = "colour"
        elif key == "fit":
            val = FIT_ALIASES.get(val, val)
        elif key == "size":
            val = re.sub(r"^(uk|size)\s*", "", val)
        elif key == "quantity":
            m = re.match(r"(\d+(?:\.\d+)?)\s*([a-z]+)", val)
            val = f"{m.group(1)} {m.group(2)}" if m else val
        elif key == "shade":
            # shade codes like "MR1 Red Coat" / "Red Coat MR1" → canonical code
            code = re.search(r"\b([a-z]{1,3}\d{1,3})\b", val)
            val = code.group(1) if code else val
        elif key == "model":
            val = re.sub(r"\s+", " ", val)
        attrs[key] = val

    attrs["brand"] = canonical_brand(listing.brand)
    attrs["category"] = canonical_category(listing.category)
    return {k: v for k, v in attrs.items() if v is not None}
