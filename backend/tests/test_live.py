"""Live-mode (SerpApi) pipeline, with the network stubbed out."""
from app.adapters.base import RawListing
from app.matching.engine import match_listings, EXACT_MATCH
from app.services.normalizer import extract_attributes
from app.live import service


def _raw(title, source="Amazon.in"):
    return service._raw_from_result({"title": title, "source": source, "extracted_price": 16999,
                                     "product_id": title[:10], "thumbnail": ""})


def test_5g_is_not_a_quantity_and_ram_storage_split():
    a = extract_attributes(_raw("Redmi Note 15 5G (Mist Purple, 8GB RAM, 128GB Storage)"))
    assert "quantity" not in a
    assert a["ram"] == "8 gb" and a["storage"] == "128 gb"


def test_same_phone_across_stores_is_exact_but_storage_variant_is_not():
    amz = _raw("Redmi Note 15 5G (Mist Purple, 8GB RAM, 128GB Storage)")
    flp = _raw("REDMI Note 15 5G (Mist Purple, 128 GB) (8 GB RAM)", "Flipkart")
    big = _raw("REDMI Note 15 5G (Mist Purple, 256 GB) (8 GB RAM)", "Flipkart")
    for r in (amz, flp, big):
        r.image_hash = "ffff0000ffff0000"
    from app.matching.engine import set_corpus
    set_corpus([amz, flp, big])
    assert match_listings(amz, flp).match_type == EXACT_MATCH
    assert match_listings(amz, big).match_type != EXACT_MATCH


def test_delivery_text_parsing():
    assert service._delivery("Free delivery tomorrow")[0] == 1
    assert service._delivery("Delivery in 3 days")[0] == 3
    assert service._delivery(None) == (5, "See store for delivery")


def test_store_normalisation_and_fallback_link():
    assert service._store("Amazon.in")[0] == "amazon"
    assert service._store("Reliance Digital")[0] == "reliance-digital"
    assert service.store_search_url("Flipkart", "Redmi Note 15").startswith("https://www.flipkart.com/search?q=")
