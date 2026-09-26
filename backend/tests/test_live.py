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
    assert service._delivery(None) == (service.UNKNOWN_DAYS, "See store for delivery")
    assert service._delivery("Free 10 min delivery")[0] == 0
    assert service._delivery("Free delivery")[0] == service.UNKNOWN_DAYS
    assert service._delivery("Delivery in 2-4 days")[0] == 4


def test_store_normalisation_and_fallback_link():
    assert service._store("Amazon.in")[0] == "amazon"
    assert service._store("Reliance Digital")[0] == "reliance-digital"
    assert service.store_search_url("Flipkart", "Redmi Note 15").startswith("https://www.flipkart.com/search?q=")


def test_foreign_converted_prices_are_dropped():
    assert service._raw_from_result({"title": "Apple iPhone 16 Plus", "source": "dakauf.eu",
                                     "price": "₹1,12,779.14", "extracted_price": 112779.14}) is None
    assert service._raw_from_result({"title": "Apple iPhone 16 Plus", "source": "Zepto",
                                     "price": "₹68,459", "extracted_price": 68459}) is not None


def _r(i, title, store, price):
    return RawListing(f"id{i}", store, store, title, "", None, "", price, price, "INR", "", "", 0, 0, 99,
                      "in_stock", {"_position": i})


def test_live_grouping_real_titles():
    from app.live.matching import live_cluster
    raws = [_r(0, "Apple iPhone 16 (128 GB) - Ultramarine", "amazon", 69900),
            _r(1, "APPLE iPhone 16 (Ultramarine, 128 GB)", "flipkart", 68999),
            _r(2, "Apple iPhone 16 (256 GB) - Black", "amazon", 79900),
            _r(3, "Apple iPhone 16 Plus", "zepto", 68459),
            _r(4, "Apple iPhone 16", "93mobiles", 63999),                        # vague: fits 2 variants
            _r(5, "Refurbished Apple iPhone 16e White by Cashify", "cashify", 45099),
            _r(6, "Apple iPhone 16 Pro Max - Refurbished | 256GB | Desert Titanium - by Ovantica", "ovantica", 79999),
            _r(7, "Apple iPhone 16 Pro Max - Refurbished | 256GB | Desert Titanium - Superb", "ovantica", 94999)]
    groups, _, _ = live_cluster(raws, "iphone 16 128gb")
    by = {frozenset(l.listing_id for l in g.listings) for g in groups}
    assert frozenset({"id0", "id1"}) in by                    # same variant, two stores → one card
    assert frozenset({"id2"}) in by and frozenset({"id3"}) in by and frozenset({"id4"}) in by
    assert frozenset({"id6"}) in by                           # same-store duplicate → cheapest kept only
    assert all(len({l.marketplace for l in g.listings}) == len(g.listings) for g in groups)


def test_ranking_demotes_variants_refurbs_and_outliers():
    groups = [{"canonical_title": t, "price_min": p, "marketplaces": [{}]} for t, p in [
        ("Apple iPhone 16 (128 GB) - Ultramarine", 69900), ("Apple iPhone 16 Plus", 79900),
        ("Refurbished Apple iPhone 16e White by Cashify", 45099), ("USA AT&T iPhone 16 Series Only", 3999)]]
    service._score_groups(groups, "iphone 16 128gb")
    order = [g["canonical_title"] for g in sorted(groups, key=lambda g: -g["relevance"])]
    assert order[0].startswith("Apple iPhone 16 (128 GB)")
    assert order[-1].startswith("USA AT&T")
    assert "unusually_low_price" in groups[3]["flags"] and "refurbished" in groups[2]["flags"]


def test_same_google_id_different_title_never_overwrites_price():
    a = service._raw_from_result({"title": "Apple iPhone 16 (128 GB) - Ultramarine", "source": "Amazon.in",
                                  "price": "₹69,900", "extracted_price": 69900, "product_id": "p1"})
    b = service._raw_from_result({"title": "REDMI Note 15 5G (Mist Purple, 128 GB)", "source": "Amazon.in",
                                  "price": "₹16,999", "extracted_price": 16999, "product_id": "p1"})
    assert a.listing_id != b.listing_id


def test_vague_listings_need_close_prices():
    from app.live.matching import live_cluster
    raws = [_r(0, "Apple iPhone 16 Plus", "zepto", 68459), _r(1, "Apple iPhone 16 Plus", "reliance-digital", 79900),
            _r(2, "Apple iPhone 16 Plus", "croma", 69900)]
    groups, _, _ = live_cluster(raws, "iphone 16 plus")
    by = {frozenset(l.listing_id for l in g.listings) for g in groups}
    assert not any({"id0", "id1"} <= g for g in by)      # 68,459 vs 79,900 with no storage stated: not merged


def test_results_from_other_stores_are_dropped():
    assert service._raw_from_result({"title": "Apple iPhone 16", "source": "ubuy.co.in", "price": "₹67,000", "extracted_price": 67000}) is None
    assert service._raw_from_result({"title": "Apple iPhone 16", "price": "₹67,000", "extracted_price": 67000,
                                     "immersive_product_page_token": "t"}) is None


def test_only_main_stores():
    ok = {"Amazon.in": "amazon", "Flipkart": "flipkart", "JioMart Grocery": "jiomart", "NIKE India": "nike",
          "Foot Locker": "footlocker", "Tata CLiQ": "tatacliq", "www.tatacliq.com": "tatacliq", "Apple Store": "apple",
          "Samsung Shop": "samsung", "H&M": "hm", "Reliance Digital": "reliance-digital", "Reliance Trends": "reliance-trends",
          "Swiggy Instamart": "swiggy-instamart", "Shoppers Stop": "shoppers-stop", "Myntra": "myntra"}
    for src, slug in ok.items():
        assert service.main_store(src) and service.main_store(src)[0] == slug, src
    for src in ["Purplle.com - Beauty Online", "ubuy.co.in", "dakauf.eu", "Cashify", "iCrescent Apple Authorised Store",
                "desertcart.in", "Flipshope", "MRV electronics", "The Bank of Electronics", "e2zSTORE", "Superkicks", "farfetch.com"]:
        assert service.main_store(src) is None, src


def test_keyword_stuffed_titles_do_not_steal_the_brand():
    groups = [{"canonical_title": t, "price_min": p, "marketplaces": [{}]} for t, p in [
        ("Blue Heaven Lengthening Waterproof Mascara Black 8ml | maybelline hypercurl mascara", 381),
        ("Maybelline New York Hyper Curl Very Black Waterproof Mascara 9.3 ml", 374)]]
    service._score_groups(groups, "maybelline mascara")
    assert groups[1]["relevance"] > groups[0]["relevance"]


def test_dead_results_without_store_or_link_are_dropped():
    assert service._raw_from_result({"title": "Maybelline Colossal Mascara", "price": "₹290", "extracted_price": 290}) is None


def test_spare_parts_are_flagged_but_phones_are_not():
    from app.live.matching import identity
    q = "redmi note 14 pro 5g"
    for t in ["Redmi Note 14 Pro 5G Battery", "TrueView Display for Redmi Note 14 Pro 5G",
              "Redmi Note 14 Pro Plus 5G - Amoled Display Combo Folder", "for Xiaomi Redmi Note 14 Pro 5G Case with Magnetic",
              "LCD Screen for Xiaomi Redmi Note 14 Pro 5G"]:
        assert identity(t, q).accessory, t
    for t in ["Redmi Note 14 Pro 5G (Titan Black, 8GB RAM, 256GB Storage)",
              "XIAOMI Redmi Note 14 Pro 5G 6.67 inch AMOLED Display 8GB 256GB"]:
        assert not identity(t, q).accessory, t


def test_amazon_results_map_to_direct_links():
    r = service._raw_from_amazon({"position": 1, "asin": "B0DPQ", "title": "Redmi Note 14 Pro 5G (Titan Black, 8GB RAM, 256GB Storage)",
                                  "link_clean": "https://www.amazon.in/dp/B0DPQ", "extracted_price": 24999,
                                  "extracted_old_price": 29999, "rating": 4.1, "reviews": 812,
                                  "delivery": ["FREE delivery Tue, 30 Sep", "Or fastest delivery Tomorrow"]})
    assert r.marketplace == "amazon" and r.product_url == "https://www.amazon.in/dp/B0DPQ" and r.mrp == 29999
    assert r.delivery_days < 90


def test_galaxy_s25_page_is_clean():
    from app.live.matching import live_cluster
    raws = [_r(0, "Samsung Galaxy S25 5G (Icyblue, 12GB RAM, 128GB Storage)", "amazon", 66500),
            _r(1, "SAMSUNG Galaxy S25 5G (Icyblue, 128 GB) (12 GB RAM)", "flipkart", 67999),
            _r(2, "Samsung Galaxy S25 5G", "croma", 66999),                           # vague, price fits 128 GB
            _r(3, "Samsung Galaxy S25 5G (Navy, 12GB RAM, 256GB Storage)", "amazon", 78999),
            _r(4, "Samsung Galaxy S25 Edge 5G (Titanium Silver, 12GB, 256GB)", "reliance-digital", 99999)]
    groups, _, _ = live_cluster(raws, "samsung galaxy s25")
    by = {frozenset(l.listing_id for l in g.listings) for g in groups}
    assert frozenset({"id0", "id1", "id2"}) in by                 # vague Croma listing joined the right card
    cards = [{"canonical_title": g.canonical_title, "price_min": min(l.price for l in g.listings),
              "marketplaces": [{}] * len(g.listings)} for g in groups]
    service._score_groups(cards, "samsung galaxy s25")
    top = max(cards, key=lambda c: c["relevance"])
    edge = next(c for c in cards if "Edge" in c["canonical_title"])
    assert "Icyblue" in top["canonical_title"] and edge["relevance"] < top["relevance"]
