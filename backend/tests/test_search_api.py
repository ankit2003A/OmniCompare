import pytest


@pytest.mark.parametrize("query,expect_in_titles", [
    ("hoodie", "hoodie"),
    ("black hoodie", "hoodie"),
    ("maybelline mascara", "mascara"),
    ("iphone case", "iphone 17"),
    ("sneakers", "sneakers"),
])
def test_search_returns_relevant_groups(client, query, expect_in_titles):
    r = client.get("/api/search", params={"q": query})
    assert r.status_code == 200
    groups = r.json()["groups"]
    assert groups, f"no groups for {query}"
    for g in groups[:3]:
        haystack = (g["canonical_title"] + " " + (g["category"] or "") + " "
                    + " ".join(l["title"] for l in g["listings"])).lower()
        assert expect_in_titles in haystack, f"{query}: {g['canonical_title']}"


def test_search_groups_duplicates(client):
    groups = client.get("/api/search", params={"q": "maybelline sky high mascara"}).json()["groups"]
    top = groups[0]
    assert top["listing_count"] == 4
    assert {m["slug"] for m in top["marketplaces"]} == {"amazon", "nykaa", "flipkart", "myntra"}
    assert top["cheapest"]["price"] == min(l["price"] for l in top["listings"])
    assert top["fastest"]["deliveryDays"] == min(l["delivery_days"] for l in top["listings"])
    assert top["match"]["confidence"] >= 90


def test_search_sort_fastest_and_price(client):
    fast = client.get("/api/search", params={"q": "hoodie", "sort": "delivery_fastest"}).json()["groups"]
    days = [g["fastest"]["deliveryDays"] for g in fast]
    assert days == sorted(days)
    cheap = client.get("/api/search", params={"q": "hoodie", "sort": "price_asc"}).json()["groups"]
    prices = [g["price_min"] for g in cheap]
    assert prices == sorted(prices)


def test_search_with_pincode_and_filters(client):
    r = client.get("/api/search", params={"q": "hoodie", "pincode": "282001", "marketplaces": "amazon,myntra",
                                          "max_delivery_days": 2}).json()
    assert r["pincode"] == "282001"
    assert r["delivery_is_demo"] is True
    for g in r["groups"]:
        for l in g["listings"]:
            assert l["marketplace"]["slug"] in ("amazon", "myntra")
            assert l["delivery_days"] <= 2


def test_bad_sort_rejected(client):
    assert client.get("/api/search", params={"q": "hoodie", "sort": "best"}).status_code == 400


def test_product_detail_similar_and_explanation(client):
    pid = client.get("/api/search", params={"q": "nike court vision"}).json()["groups"][0]["id"]
    d = client.get(f"/api/products/{pid}").json()
    assert d["listing_count"] == 4
    assert d["match"]["confidence"] >= 90
    assert any(r["status"] == "ok" for r in d["match"]["reasons"])
    assert d["similar_products"], "UK 8 and Mid variants should show as similar"
    assert all(70 <= s["similarity"] < 90 for s in d["similar_products"])
    assert all(l["product_url"].startswith("https://") for l in d["listings"])
    assert client.get(f"/api/products/{pid}/listings").status_code == 200
    assert client.get(f"/api/products/{pid}/similar").status_code == 200
    assert client.get("/api/products/999999").status_code == 404


def test_match_endpoint_adhoc_and_by_id(client):
    r = client.post("/api/match", json={
        "listing_a": {"title": "boAt Airdopes 141 TWS Earbuds Black", "brand": "boAt", "category": "earbuds"},
        "listing_b": {"title": "boAt Airdopes 141 Bluetooth Headset Bold Black", "brand": "boAt", "category": "earbuds"},
    }).json()
    assert r["match_type"] in ("EXACT_MATCH", "SIMILAR")
    assert set(r["weights"]) == {"text", "attribute", "image"}
    ids = [l["id"] for l in client.get("/api/search", params={"q": "airdopes"}).json()["groups"][0]["listings"][:2]]
    r2 = client.post("/api/match", json={"listing_a_id": ids[0], "listing_b_id": ids[1]}).json()
    assert r2["match_type"] == "EXACT_MATCH"


def test_compare_delivery_marketplaces_suggestions(client):
    ids = [l["id"] for l in client.get("/api/search", params={"q": "levi's 511"}).json()["groups"][0]["listings"]]
    c = client.post("/api/compare", json={"listing_ids": ids, "pincode": "282001", "sort": "delivery_fastest"}).json()
    assert len(c["listings"]) == len(ids) and c["cheapest"] and c["fastest"]
    d = client.post("/api/delivery-estimate", json={"marketplace": "meesho", "listing_id": "MSH-5001", "pincode": "282001"}).json()
    assert d["isDemo"] is True and d["deliveryDays"] == 4
    assert len(client.get("/api/marketplaces").json()) == 6
    s = client.get("/api/search/suggestions", params={"q": "hoo"}).json()
    assert "hoodie" in s["history"] and s["products"]
