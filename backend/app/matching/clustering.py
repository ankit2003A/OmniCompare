"""Cluster listings into product groups using union-find over EXACT_MATCH pairs.

SIMILAR pairs are kept as cross-group links used for "Similar products".
"""
from collections import Counter
from dataclasses import dataclass, field
from app.adapters.base import RawListing
from app.matching.engine import match_listings, set_corpus, MatchResult, EXACT_MATCH, SIMILAR
from app.services.normalizer import extract_attributes, tokens


@dataclass
class PairMatch:
    a: str
    b: str
    result: MatchResult


@dataclass
class ProductGroup:
    key: int
    listings: list[RawListing]
    attributes: dict
    canonical_title: str
    brand: str | None
    category: str | None
    description: str
    canonical_image: str
    members: set[str] = field(default_factory=set)


class UnionFind:
    def __init__(self, items):
        self.parent = {i: i for i in items}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def _canonical_title(listings: list[RawListing], pairs: dict[tuple[str, str], MatchResult]) -> str:
    """Title of the most 'central' listing (highest mean similarity to the others),
    then title-cased and trimmed of the marketplace-specific size suffix."""
    if len(listings) == 1:
        return _clean_title(listings[0].title)
    best, best_score = listings[0], -1.0
    for l in listings:
        s = 0.0
        for o in listings:
            if o is l:
                continue
            r = pairs.get((l.listing_id, o.listing_id)) or pairs.get((o.listing_id, l.listing_id))
            s += r.combined_score if r else 0
        if s > best_score:
            best, best_score = l, s
    return _clean_title(best.title)


def _clean_title(title: str) -> str:
    import re
    t = re.sub(r"\s*\([^)]*\)\s*", " ", title)          # drop "(UK 9)", "(3.6 g)"
    t = re.sub(r"\s*,\s*[^,]*\d+\s*(w|g|ml|l|ltrs)?\s*$", "", t, flags=re.I)  # drop trailing ", 100ml"
    return re.sub(r"\s+", " ", t).strip(" -,")


def cluster(listings: list[RawListing]) -> tuple[list[ProductGroup], list[PairMatch]]:
    set_corpus(listings)
    attrs = {l.listing_id: extract_attributes(l) for l in listings}
    uf = UnionFind([l.listing_id for l in listings])
    pairs: list[PairMatch] = []
    pair_index: dict[tuple[str, str], MatchResult] = {}

    # Cheap candidate blocking: only compare listings sharing a category or a title token.
    for i, a in enumerate(listings):
        ta = set(tokens(a.title))
        for b in listings[i + 1:]:
            if attrs[a.listing_id].get("category") != attrs[b.listing_id].get("category") and not (ta & set(tokens(b.title))):
                continue
            r = match_listings(a, b, attrs[a.listing_id], attrs[b.listing_id])
            if r.match_type in (EXACT_MATCH, SIMILAR):
                pairs.append(PairMatch(a.listing_id, b.listing_id, r))
                pair_index[(a.listing_id, b.listing_id)] = r
            if r.match_type == EXACT_MATCH:
                uf.union(a.listing_id, b.listing_id)

    groups_by_root: dict[str, list[RawListing]] = {}
    for l in listings:
        groups_by_root.setdefault(uf.find(l.listing_id), []).append(l)

    groups: list[ProductGroup] = []
    for i, (root, members) in enumerate(groups_by_root.items()):
        merged: dict = {}
        for l in members:                       # majority vote per attribute
            for k, v in attrs[l.listing_id].items():
                merged.setdefault(k, Counter())[v] += 1
        attributes = {k: c.most_common(1)[0][0] for k, c in merged.items()}
        described = max(members, key=lambda l: len(l.description or ""))
        groups.append(ProductGroup(
            key=i, listings=members, attributes=attributes,
            canonical_title=_canonical_title(members, pair_index),
            brand=attributes.get("brand"), category=attributes.get("category"),
            description=described.description or "",
            canonical_image=max(members, key=lambda l: l.review_count).image_url,
            members={l.listing_id for l in members},
        ))
    return groups, pairs
