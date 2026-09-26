from app.services.sorting import sort_listings, sort_groups


def L(price, days, rating, disc, avail=True):
    return {"price": price, "rating": rating, "review_count": 10, "discount_percentage": disc,
            "delivery": {"deliveryDays": days, "available": avail}}


LISTINGS = [L(999, 1, 4.4, 20), L(899, 2, 4.3, 35), L(699, 4, 4.1, 50), L(949, 2, 4.5, 10)]


def test_price_asc():
    assert [l["price"] for l in sort_listings(LISTINGS, "price_asc")] == [699, 899, 949, 999]


def test_price_desc():
    assert [l["price"] for l in sort_listings(LISTINGS, "price_desc")] == [999, 949, 899, 699]


def test_delivery_fastest_uses_days_not_price():
    out = sort_listings(LISTINGS, "delivery_fastest")
    assert [l["delivery"]["deliveryDays"] for l in out] == [1, 2, 2, 4]
    assert out[0]["price"] == 999   # fastest is the most expensive one — price is ignored


def test_delivery_slowest():
    assert sort_listings(LISTINGS, "delivery_slowest")[0]["delivery"]["deliveryDays"] == 4


def test_rating_desc():
    assert [l["rating"] for l in sort_listings(LISTINGS, "rating_desc")] == [4.5, 4.4, 4.3, 4.1]


def test_discount_desc():
    assert [l["discount_percentage"] for l in sort_listings(LISTINGS, "discount_desc")] == [50, 35, 20, 10]


def test_unavailable_listings_sort_last_for_fastest():
    ls = LISTINGS + [L(100, 0, 5, 90, avail=False)]
    assert sort_listings(ls, "delivery_fastest")[-1]["delivery"]["available"] is False


def test_group_sort_fastest():
    groups = [
        {"price_min": 500, "price_max": 900, "fastest": {"deliveryDays": 3}, "slowest_days": 5, "rating_max": 4, "rating_min": 3, "discount_max": 10, "listing_count": 2},
        {"price_min": 800, "price_max": 900, "fastest": {"deliveryDays": 1}, "slowest_days": 2, "rating_max": 4, "rating_min": 3, "discount_max": 10, "listing_count": 2},
    ]
    assert sort_groups(groups, "delivery_fastest")[0]["fastest"]["deliveryDays"] == 1
    assert sort_groups(groups, "price_asc")[0]["price_min"] == 500
