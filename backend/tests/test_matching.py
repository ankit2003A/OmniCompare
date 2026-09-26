from app.adapters.base import RawListing
from app.matching.engine import match_listings, classify, EXACT_MATCH, SIMILAR, DIFFERENT
from app.seed.catalog import ph


def mk(title, brand="Nike", category="sneakers", key="shoe-a", flips=0, seller="A", **attrs):
    return RawListing(
        listing_id=title[:10] + seller, marketplace="amazon", seller_name=seller, title=title,
        description="", brand=brand, category=category, price=100, mrp=120, currency="INR",
        image_url="x", image_hash=ph(key, title + seller, flips), rating=4, review_count=10,
        delivery_days=2, availability="in_stock", product_attributes=attrs,
    )


def test_same_title_same_attributes_is_exact():
    a = mk("Nike Court Vision Low White Sneakers UK 9", colour="White", size="UK 9")
    b = mk("Nike Court Vision Low White Sneakers UK 9", colour="White", size="UK 9", seller="B")
    assert match_listings(a, b).match_type == EXACT_MATCH


def test_different_brand_is_different():
    a = mk("Court Vision Low White Sneakers UK 9", brand="Nike", colour="White", size="UK 9")
    b = mk("Court Vision Low White Sneakers UK 9", brand="Adidas", colour="White", size="UK 9", seller="B")
    r = match_listings(a, b)
    assert r.match_type == DIFFERENT
    assert any("Brand differs" in x.label for x in r.reasons)


def test_same_image_different_size_is_not_exact():
    a = mk("Nike Court Vision Low White Sneakers", colour="White", size="UK 9")
    b = mk("Nike Court Vision Low White Sneakers", colour="White", size="UK 8", seller="B")
    r = match_listings(a, b)
    assert r.image_score >= 0.95
    assert r.match_type != EXACT_MATCH
    assert r.match_type == SIMILAR


def test_same_product_different_seller_is_exact():
    a = mk("Maybelline Sky High Mascara Black 7.2ml", brand="Maybelline", category="mascara", key="mascara",
           colour="Black", quantity="7.2 ml", seller="Cloudtail")
    b = mk("Maybelline New York Sky High Washable Mascara - Black", brand="Maybelline New York",
           category="mascara", key="mascara", flips=1, colour="Black", quantity="7.2 ml", seller="Nykaa Retail")
    assert match_listings(a, b).match_type == EXACT_MATCH


def test_similar_looking_products_are_similar():
    a = mk("Black Cotton Hoodie", brand=None, category="hoodie", key="hoodie", colour="Black", material="Cotton")
    b = mk("Black Cotton Blend Oversized Hoodie", brand=None, category="hoodie", key="hoodie", flips=9,
           colour="Black", material="Cotton Blend", seller="B")
    r = match_listings(a, b)
    assert r.match_type == SIMILAR


def test_cotton_hoodie_vs_polyester_sweatshirt_not_exact():
    a = mk("Black Cotton Hoodie", brand=None, category="hoodie", key="h", colour="Black", material="Cotton")
    b = mk("Black Polyester Oversized Sweatshirt", brand=None, category="sweatshirt", key="h", flips=12,
           colour="Black", material="Polyester", seller="B")
    assert match_listings(a, b).match_type != EXACT_MATCH


def test_unrelated_products_are_different():
    a = mk("Prestige 5 Litre Pressure Cooker", brand="Prestige", category="pressure cooker", key="cooker")
    b = mk("Nike Court Vision Low White Sneakers", key="shoe", seller="B")
    assert match_listings(a, b).match_type == DIFFERENT


def test_classification_thresholds_are_configurable():
    assert classify(0.95) == EXACT_MATCH
    assert classify(0.80) == SIMILAR
    assert classify(0.50) == DIFFERENT
    assert classify(0.80, thresholds=(0.75, 0.5)) == EXACT_MATCH


def test_seeded_exact_groups(db):
    """The deliberately challenging seed groups must cluster as designed."""
    from sqlalchemy import select
    from app.models import Listing
    rows = {l.listing_id: l.product_id for l in db.execute(select(Listing)).scalars()}
    exact_groups = [
        ["AMZ-1001", "NYK-2001", "FLP-3001", "MYN-4001"],   # Sky High mascara
        ["AMZ-1003", "FLP-3002", "MYN-4002", "AJO-6001"],   # Puma hoodie M
        ["AMZ-1006", "FLP-3004", "MSH-5002"],               # Spigen case iPhone 17
        ["AMZ-1008", "MYN-4006", "AJO-6003", "FLP-3006"],   # Nike CV Low UK 9
        ["AMZ-1009", "FLP-3008", "MYN-4008"],               # Airdopes 141
        ["NYK-2003", "AMZ-1011", "FLP-3009", "MYN-4009"],   # Lakme MR1
        ["AMZ-1012", "NYK-2005", "FLP-3010", "MSH-5005"],   # Ubtan 100ml
        ["AMZ-1014", "FLP-3011", "MSH-5006"],               # Samsung 25W
        ["AMZ-1016", "MYN-4010", "AJO-6005", "FLP-3012"],   # Levi's 511 W32
        ["AMZ-1018", "FLP-3013", "MYN-4012", "AJO-6006"],   # AMT Sky black
    ]
    for group in exact_groups:
        assert len({rows[i] for i in group}) == 1, f"{group} should be one product"
    must_be_separate = [("AMZ-1001", "NYK-2002"), ("AMZ-1008", "MYN-4007"), ("AMZ-1003", "AJO-6002"),
                        ("AMZ-1005", "MYN-4005"), ("AMZ-1012", "AMZ-1013"), ("AMZ-1016", "MYN-4011"),
                        ("NYK-2003", "NYK-2004"), ("AMZ-1006", "AMZ-1007")]
    for a, b in must_be_separate:
        assert rows[a] != rows[b], f"{a} and {b} must not be grouped"
