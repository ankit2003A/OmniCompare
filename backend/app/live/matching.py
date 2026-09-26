"""Product identity for LIVE listings (real Google Shopping titles from many stores).

Why not the demo engine? Across real stores the photos differ (so image similarity is
noise) and titles vary wildly, while the things that decide "same purchasable item" are
explicit: brand, model line + number, variant words (Pro/Plus/Max/e…), storage, RAM,
colour and condition. Two listings are the same product only when all of those agree
(a missing value on one side is tolerated, a conflicting one is not), the product line
words overlap, and the prices are plausibly the same item.
"""
import re
from dataclasses import dataclass, field
from app.adapters.base import RawListing
from app.matching.clustering import ProductGroup, PairMatch
from app.matching.engine import MatchResult, Reason, EXACT_MATCH

VARIANT_WORDS = {"pro", "plus", "max", "mini", "ultra", "lite", "fe", "air", "neo", "prime", "power", "edge",
                 "fold", "flip", "se", "slim", "turbo", "classic", "sport", "go", "xl", "xs"}
CONDITION_RE = re.compile(r"\b(refurbished|renewed|pre[- ]?owned|second[- ]?hand|used|open[- ]?box|unboxed)\b", re.I)
ACCESSORY_WORDS = {"case", "cover", "skin", "tempered", "protector", "guard", "charger", "cable", "adapter",
                   "strap", "holder", "stand", "mount", "pouch", "sleeve", "unlock", "unlocking", "tray",
                   "replacement", "spare", "parts", "housing", "sticker", "decal", "wrap", "dummy", "backcover"}
FILLER = {"the", "and", "with", "for", "of", "in", "by", "a", "an", "new", "latest", "original", "genuine", "official",
          "smartphone", "phone", "mobile", "cellphone", "unlocked", "dual", "sim", "5g", "4g", "lte", "storage",
          "ram", "rom", "gb", "tb", "variant", "edition", "model", "india", "warranty", "brand", "box", "sealed",
          "free", "delivery", "only", "series", "certified", "grade", "good", "superb", "fair", "excellent", "like",
          "renewed", "refurbished", "used", "pre", "owned", "open", "by", "&"}
BRAND_ALIASES = {"iphone": "apple", "ipad": "apple", "macbook": "apple", "airpods": "apple", "imac": "apple",
                 "galaxy": "samsung", "redmi": "xiaomi", "poco": "xiaomi", "mi": "xiaomi", "pixel": "google",
                 "playstation": "sony", "ps5": "sony", "bravia": "sony", "xbox": "microsoft", "surface": "microsoft",
                 "thinkpad": "lenovo", "ideapad": "lenovo", "legion": "lenovo", "vivobook": "asus", "zenbook": "asus",
                 "rog": "asus", "tuf": "asus", "inspiron": "dell", "vostro": "dell", "xps": "dell", "alienware": "dell",
                 "pavilion": "hp", "victus": "hp", "omen": "hp", "envy": "hp", "omnibook": "hp", "aspire": "acer",
                 "nitro": "acer", "predator": "acer", "airdopes": "boat", "rockerz": "boat", "nord": "oneplus"}
BRANDS = {"apple", "samsung", "xiaomi", "oneplus", "realme", "vivo", "oppo", "iqoo", "motorola", "moto", "nothing",
          "google", "nokia", "lava", "infinix", "tecno", "honor", "huawei", "sony", "lg", "hp", "dell", "lenovo",
          "asus", "acer", "msi", "boat", "noise", "jbl", "bose", "sennheiser", "philips", "havells", "bajaj",
          "prestige", "puma", "nike", "adidas", "reebok", "levi's", "levis", "maybelline", "lakme", "loreal",
          "canon", "nikon", "fujifilm", "gopro", "dji", "microsoft", "nintendo", "amazon", "whirlpool", "godrej",
          "voltas", "daikin", "haier", "panasonic", "ifb", "bosch", "dyson", "titan", "fastrack", "casio", "fossil",
          "boult", "cmf", "redmi", "poco"}
COLOURS = ["desert titanium", "natural titanium", "black titanium", "white titanium", "blue titanium", "space black",
           "space grey", "space gray", "midnight", "starlight", "ultramarine", "teal", "mist purple", "jet black",
           "black", "white", "blue", "navy", "green", "red", "pink", "purple", "lavender", "violet", "yellow", "gold",
           "silver", "grey", "gray", "graphite", "titanium", "orange", "brown", "beige", "cream", "mint", "coral",
           "bronze", "champagne", "olive", "sage", "icy blue", "ocean blue", "sky blue", "rose gold"]
COLOUR_RE = re.compile(r"\b(" + "|".join(re.escape(c) for c in sorted(COLOURS, key=len, reverse=True)) + r")\b")
PRICE_RATIO_MAX = 1.6


def _norm(title: str) -> str:
    t = title.lower().replace("’", "'").replace("é", "e")
    t = re.sub(r"(iphone|galaxy|pixel|redmi|note|ipad)(\d)", r"\1 \2", t)        # "iphone16" -> "iphone 16"
    t = re.sub(r"(\d+)\s*(gb|tb)\b", r"\1\2", t)                                   # "128 gb" -> "128gb"
    t = re.sub(r"\[[^\]]*\]", " ", t)                                            # "[Duplicate-8245…]"
    t = re.sub(r"[()\[\],|/+–—:;!\"*]", " ", t)
    t = re.sub(r"\s-\s|\s-|-\s", " ", t)
    return re.sub(r"\s+", " ", t).strip()


@dataclass
class Identity:
    brand: str | None
    model: frozenset          # digit-bearing model tokens + variant words
    family: frozenset         # remaining descriptive words (product line)
    storage: str | None
    ram: str | None
    colour: str | None
    condition: str
    accessory: bool
    quantity: str | None = None
    tokens: list = field(default_factory=list)


def identity(title: str, query: str = "") -> Identity:
    t = _norm(title)
    condition = "refurbished" if CONDITION_RE.search(t) else "new"
    ram = None
    m = re.search(r"\b(\d{1,2})gb\s*ram\b|\bram\s*(\d{1,2})gb\b", t)
    if m:
        ram = f"{m.group(1) or m.group(2)}gb"
    sizes = []
    for n, u in re.findall(r"\b(\d+(?:\.\d+)?)(gb|tb)\b", t):
        v = f"{n}{u}"
        if v != ram:
            sizes.append((float(n) * (1024 if u == "tb" else 1), v))
    # "8gb 256gb" without the word RAM: the smaller one is RAM for phones/laptops
    if not ram and len(sizes) >= 2:
        sizes.sort()
        if sizes[0][0] <= 24:
            ram = sizes[0][1]
            sizes = sizes[1:]
    storage = max(sizes)[1] if sizes else None
    qty = re.search(r"\b(\d+(?:\.\d+)?)\s?(ml|l|g|kg|mah|w|inch|cm)\b", re.sub(r"\b[2-5]g\b", " ", t))
    quantity = f"{qty.group(1)}{qty.group(2)}" if qty else None
    if quantity in ("2g", "3g", "4g", "5g"):                                          # network, not grams
        quantity = None
    colours = COLOUR_RE.findall(t)
    colour = colours[-1].replace("gray", "grey") if colours else None

    words = t.split()
    brand = next((w for w in words if w in BRANDS), None)
    if brand is None:
        brand = next((BRAND_ALIASES[w] for w in words if w in BRAND_ALIASES), None)
    brand = {"redmi": "xiaomi", "poco": "xiaomi", "moto": "motorola", "levis": "levi's"}.get(brand, brand)

    colour_words = set(" ".join(colours).split())
    model, family = set(), set()
    for w in words:
        w = w.strip(".'")
        if not w or w in FILLER or w in colour_words or w == brand:
            continue
        if re.fullmatch(r"\d+(?:\.\d+)?(gb|tb)", w) or w in ("5g", "4g"):
            continue
        if re.search(r"\d{5,}", w):             # SKU / listing ids
            continue
        if any(ch.isdigit() for ch in w) or w in VARIANT_WORDS:
            model.add(w)
        elif len(w) > 1:
            family.add(w)
    q = set(_norm(query).split())
    accessory = bool((family | model) & ACCESSORY_WORDS - q) and not (ACCESSORY_WORDS & q)
    return Identity(brand, frozenset(model), frozenset(family), storage, ram, colour, condition, accessory,
                    quantity, words)


def _dice(a: frozenset, b: frozenset) -> float:
    return 2 * len(a & b) / (len(a) + len(b)) if a and b else 0.0


def compare(a: RawListing, b: RawListing, ia: Identity, ib: Identity) -> MatchResult:
    reasons: list[Reason] = []
    ok = True

    def check(label, va, vb, hard=True):
        nonlocal ok
        if va and vb:
            if va == vb:
                reasons.append(Reason(f"Same {label}", "ok"))
            else:
                reasons.append(Reason(f"{label.capitalize()} differs ({va} vs {vb})", "warn"))
                ok = ok and not hard
        elif va or vb:
            reasons.append(Reason(f"{label.capitalize()} not stated on one listing", "info"))

    check("brand", ia.brand, ib.brand)
    if ia.model != ib.model:
        ok = False
        reasons.append(Reason(f"Model differs ({' '.join(sorted(ia.model)) or '—'} vs {' '.join(sorted(ib.model)) or '—'})", "warn"))
    elif ia.model:
        reasons.append(Reason(f"Same model ({' '.join(sorted(ia.model))})", "ok"))
    check("storage", ia.storage, ib.storage)
    check("RAM", ia.ram, ib.ram)
    check("colour", ia.colour, ib.colour)
    check("size/quantity", ia.quantity, ib.quantity)
    if ia.condition != ib.condition:
        ok = False
        reasons.append(Reason(f"Condition differs ({ia.condition} vs {ib.condition})", "warn"))
    else:
        reasons.append(Reason(f"Both {ia.condition}", "ok"))
    if ia.accessory != ib.accessory:
        ok = False
    fam = _dice(ia.family, ib.family)
    if not ia.model and not ib.model:          # no model number → need strong wording overlap
        ok = ok and fam >= 0.75
    elif ia.family and ib.family and not (ia.family & ib.family):
        ok = False
        reasons.append(Reason("Different product line", "warn"))
    ratio = max(a.price, b.price) / max(1.0, min(a.price, b.price))
    if ratio > PRICE_RATIO_MAX:
        ok = False
        reasons.append(Reason(f"Prices too far apart for the same item ({ratio:.1f}×)", "warn"))
    else:
        reasons.append(Reason("Prices consistent", "ok"))
    score = round(0.55 + 0.25 * min(1.0, fam + 0.3) + 0.2 * (1 - (ratio - 1) / (PRICE_RATIO_MAX - 1 + 1e-9)), 4) if ok else 0.4
    return MatchResult(text_score=round(fam, 4), attribute_score=1.0 if ok else 0.0, image_score=0.0,
                       combined_score=min(score, 0.99), match_type=EXACT_MATCH if ok else "DIFFERENT", reasons=reasons)


def live_cluster(raws: list[RawListing], query: str = "") -> tuple[list[ProductGroup], list[PairMatch], dict]:
    """Group listings; one listing per store per group (cheapest kept). Returns identities too."""
    ids = {r.listing_id: identity(r.title, query) for r in raws}
    specificity = lambda r: sum(bool(getattr(ids[r.listing_id], k)) for k in ("storage", "ram", "colour", "quantity"))
    clusters: list[list[RawListing]] = []
    results: dict[tuple[str, str], MatchResult] = {}

    def fits(r: RawListing, c: list[RawListing]) -> bool:
        for m in c:
            key = (m.listing_id, r.listing_id)
            if key not in results:
                results[key] = compare(m, r, ids[m.listing_id], ids[r.listing_id])
            if results[key].match_type != EXACT_MATCH:
                return False
        return True

    # Specific listings first so variant clusters form; a vague listing joins only when
    # exactly one cluster fits (otherwise it would glue different variants together).
    for r in sorted(raws, key=lambda x: (-specificity(x), x.product_attributes.get("_position", 99))):
        options = [c for c in clusters if fits(r, c)]
        if len(options) == 1 or (options and specificity(r) > 0):
            options[0].append(r)
        else:
            clusters.append([r])
    buckets = {str(i): c for i, c in enumerate(clusters)}
    pairs: list[PairMatch] = [PairMatch(a, b, res) for (a, b), res in results.items() if res.match_type == EXACT_MATCH]

    groups: list[ProductGroup] = []
    kept: set[str] = set()
    for key, members in buckets.items():
        per_store: dict[str, RawListing] = {}
        for m in sorted(members, key=lambda x: x.price):
            per_store.setdefault(m.marketplace, m)       # cheapest offer per store
        members = list(per_store.values())
        kept.update(m.listing_id for m in members)
        lead = min(members, key=lambda m: m.product_attributes.get("_position", 99))
        idn = ids[lead.listing_id]
        pretty = lambda v: re.sub(r"(\d)(gb|tb)$", lambda m: f"{m.group(1)} {m.group(2).upper()}", v) if v else v
        attrs = {k: v for k, v in {"brand": idn.brand, "storage": pretty(idn.storage), "ram": pretty(idn.ram) and f"{pretty(idn.ram)} RAM",
                                   "colour": idn.colour, "condition": idn.condition if idn.condition != "new" else None,
                                   "quantity": idn.quantity}.items() if v}
        groups.append(ProductGroup(
            key=len(groups), listings=members, attributes=attrs, canonical_title=_clean(lead.title),
            brand=idn.brand, category=None, description="",
            canonical_image=lead.image_url, members={m.listing_id for m in members}))
    pairs = [p for p in pairs if p.a in kept and p.b in kept]
    return groups, pairs, ids


def _clean(title: str) -> str:
    t = re.sub(r"\s*\[[^\]]*\]\s*", " ", title)
    return re.sub(r"\s+", " ", t).strip(" -|,")[:200]
