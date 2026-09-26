"""Seeded marketplace catalog — DEMO DATA ONLY.

Nothing here is scraped or live. Titles, prices, sellers, ratings and delivery
days are invented to be realistic and deliberately challenging for the matcher:
same product with different wording, same product in a different size/shade/
quantity (must NOT be exact), lookalikes with different materials, and noise.

Each listing carries a simulated 64-bit perceptual image hash. Listings of the
same physical product share a visual key with 0–2 bits flipped; lookalikes share
the key with ~8–14 bits flipped; unrelated products use a different key.
"""
import hashlib
import re
from app.adapters.base import RawListing

MARKETPLACES = {
    "amazon":   {"name": "Amazon",   "base_url": "https://www.amazon.in",   "brand_color": "#FF9900", "logo_url": "/logos/amazon.svg"},
    "flipkart": {"name": "Flipkart", "base_url": "https://www.flipkart.com", "brand_color": "#2874F0", "logo_url": "/logos/flipkart.svg"},
    "meesho":   {"name": "Meesho",   "base_url": "https://www.meesho.com",   "brand_color": "#9F2089", "logo_url": "/logos/meesho.svg"},
    "myntra":   {"name": "Myntra",   "base_url": "https://www.myntra.com",   "brand_color": "#FF3F6C", "logo_url": "/logos/myntra.svg"},
    "nykaa":    {"name": "Nykaa",    "base_url": "https://www.nykaa.com",    "brand_color": "#FC2779", "logo_url": "/logos/nykaa.svg"},
    "ajio":     {"name": "AJIO",     "base_url": "https://www.ajio.com",     "brand_color": "#2C4152", "logo_url": "/logos/ajio.svg"},
}


def ph(key: str, salt: str = "", flips: int = 0) -> str:
    """Simulated perceptual hash: sha256(key) truncated to 64 bits, with `flips`
    bits toggled deterministically by `salt`."""
    base = int(hashlib.sha256(key.encode()).hexdigest()[:16], 16)
    if flips:
        rng = int(hashlib.sha256((key + "|" + salt).encode()).hexdigest(), 16)
        used = set()
        while len(used) < flips:
            bit = rng % 64
            rng //= 64
            used.add(bit)
        for b in used:
            base ^= (1 << b)
    return f"{base:016x}"


def img(text: str, bg: str = "f2f2f2", fg: str = "333333") -> str:
    """Relative URL served by the backend's /images router (see app/api/images.py).
    The frontend prefixes NEXT_PUBLIC_API_URL to relative image paths."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return f"/images/{slug}.svg?bg={bg}&fg={fg}"


def L(lid, mkt, seller, title, brand, category, price, mrp, rating, reviews, days,
      image_key, salt="", flips=0, image_text="", bg="f2f2f2", fg="333333",
      availability="in_stock", desc="", **attrs) -> RawListing:
    base = MARKETPLACES[mkt]["base_url"]
    return RawListing(
        listing_id=lid, marketplace=mkt, seller_name=seller, title=title,
        description=desc, brand=brand, category=category, price=price, mrp=mrp,
        currency="INR", image_url=img(image_text or image_key, bg, fg),
        image_hash=ph(image_key, salt or lid, flips), rating=rating, review_count=reviews,
        delivery_days=days, availability=availability, product_attributes=attrs,
        product_url=f"{base}/demo/{lid}",
    )


CATALOG: list[RawListing] = [
    # ───────────── EXACT GROUP 1: Maybelline Sky High mascara, black, washable, 7.2 ml ─────────────
    L("AMZ-1001", "amazon", "Cloudtail India", "Maybelline New York Sky High Mascara Black 7.2ml", "Maybelline", "mascara",
      499, 699, 4.4, 18342, 1, "mascara sky high black", flips=1, image_text="Sky High Mascara", bg="1a1a1a", fg="ffffff",
      desc="Lash-lengthening washable mascara with Flex Tower brush for limitless length.", colour="Black", quantity="7.2 ml", variant="Washable"),
    L("NYK-2001", "nykaa", "Nykaa Retail", "Maybelline Sky High Washable Mascara - Black", "Maybelline New York", "mascara",
      479, 699, 4.5, 9021, 2, "mascara sky high black", flips=0, image_text="Sky High Mascara", bg="1a1a1a", fg="ffffff",
      desc="Washable formula. Bamboo extract + fibres for full volume and length.", shade="Black", quantity="7.2 ml", variant="Washable"),
    L("FLP-3001", "flipkart", "RetailNet", "Maybelline New York Sky High Mascara 7.2 ml", "Maybelline", "mascara",
      459, 699, 4.3, 5210, 3, "mascara sky high black", flips=2, image_text="Sky High Mascara", bg="1a1a1a", fg="ffffff",
      desc="Sky High lash lengthening washable mascara, shade Very Black.", colour="Black", quantity="7.2 ml", variant="Washable"),
    L("MYN-4001", "myntra", "Myntra Beauty", "Maybelline New York Sky High Washable Mascara Black", "Maybelline", "mascara",
      524, 699, 4.4, 2760, 2, "mascara sky high black", flips=1, image_text="Sky High Mascara", bg="1a1a1a", fg="ffffff",
      colour="Black", quantity="7.2 ml", variant="Washable"),

    # SIMILAR to group 1: waterproof variant (different product), and a different mascara
    L("NYK-2002", "nykaa", "Nykaa Retail", "Maybelline Sky High Waterproof Mascara - Black", "Maybelline New York", "mascara",
      499, 699, 4.4, 4102, 2, "mascara sky high black", salt="wp", flips=9, image_text="Sky High Waterproof", bg="1f2a3a", fg="ffffff",
      desc="Waterproof formula, smudge-resistant for 24 hours.", shade="Black", quantity="7.2 ml", variant="Waterproof"),
    L("AMZ-1002", "amazon", "Beauty Hub", "Maybelline New York Lash Sensational Mascara Black 9.5ml", "Maybelline", "mascara",
      399, 599, 4.3, 22110, 1, "mascara lash sensational", image_text="Lash Sensational", bg="2a1a1a", fg="ffffff",
      colour="Black", quantity="9.5 ml"),

    # ───────────── EXACT GROUP 2: Puma Essentials men's black hoodie, size M ─────────────
    L("AMZ-1003", "amazon", "Puma Official", "Puma Men's Essentials Fleece Hoodie Black (M)", "Puma", "hoodie",
      1799, 3499, 4.3, 3401, 1, "hoodie puma ess black", flips=1, image_text="Puma Hoodie", bg="111111", fg="ffffff",
      desc="Puma ESS big logo hoodie in brushed fleece, regular fit.", colour="Black", size="M", gender="Men", material="Cotton Blend", fit="Regular"),
    L("FLP-3002", "flipkart", "Omnitech Retail", "PUMA Men Solid Hooded Sweatshirt Essentials Black M", "Puma", "hoodie",
      1749, 3499, 4.2, 1876, 2, "hoodie puma ess black", flips=2, image_text="Puma Hoodie", bg="111111", fg="ffffff",
      colour="Black", size="M", gender="Men", material="Cotton Blend"),
    L("MYN-4002", "myntra", "Myntra Jabong", "Puma Men Black Essentials Hooded Sweatshirt", "Puma", "hoodie",
      1924, 3499, 4.4, 5230, 2, "hoodie puma ess black", flips=0, image_text="Puma Hoodie", bg="111111", fg="ffffff",
      colour="Black", size="M", gender="Men", material="Cotton Blend", fit="Regular"),
    L("AJO-6001", "ajio", "Reliance Retail", "PUMA ESS Big Logo Hoodie - Black", "Puma", "hoodie",
      1679, 3499, 4.1, 612, 3, "hoodie puma ess black", flips=1, image_text="Puma Hoodie", bg="111111", fg="ffffff",
      colour="Black", size="M", gender="Men", material="Cotton Blend"),
    # SIMILAR: same hoodie, navy; same hoodie, size L
    L("AJO-6002", "ajio", "Reliance Retail", "PUMA ESS Big Logo Hoodie - Navy", "Puma", "hoodie",
      1679, 3499, 4.1, 388, 3, "hoodie puma ess black", salt="navy", flips=10, image_text="Puma Hoodie Navy", bg="1c2a4a", fg="ffffff",
      colour="Navy", size="M", gender="Men", material="Cotton Blend"),
    L("MYN-4003", "myntra", "Myntra Jabong", "Puma Men Black Essentials Hooded Sweatshirt (L)", "Puma", "hoodie",
      1924, 3499, 4.4, 5230, 2, "hoodie puma ess black", flips=0, image_text="Puma Hoodie", bg="111111", fg="ffffff",
      colour="Black", size="L", gender="Men", material="Cotton Blend"),

    # ───────────── SIMILAR GROUP: women's black oversized hoodie (unbranded / house brands) ─────────────
    L("AMZ-1004", "amazon", "Kanha Fashions", "Women's Black Oversized Cotton Hoodie", None, "hoodie",
      699, 1499, 4.0, 1204, 1, "hoodie women black oversized", flips=0, image_text="Black Oversized Hoodie", bg="151515", fg="ffffff",
      desc="Drop-shoulder oversized hoodie in 100% cotton fleece, kangaroo pocket.", colour="Black", gender="Women", fit="Oversized", material="Cotton", size="Free"),
    L("MSH-5001", "meesho", "Shree Krishna Garments", "Black Loose Fit Women's Hoodie", None, "hoodie",
      449, 999, 3.9, 8711, 4, "hoodie women black oversized", flips=6, image_text="Black Oversized Hoodie", bg="151515", fg="ffffff",
      desc="Loose fit hoodie for women, cotton blend.", colour="Black", gender="Women", fit="Oversized", size="Free"),
    L("MYN-4004", "myntra", "Myntra Jabong", "Women Black Oversized Hoodie", "Dillinger", "hoodie",
      949, 1899, 4.5, 2310, 2, "hoodie women black oversized", flips=7, image_text="Black Oversized Hoodie", bg="151515", fg="ffffff",
      colour="Black", gender="Women", fit="Oversized", material="Cotton Blend", size="Free"),
    L("FLP-3003", "flipkart", "TrueStyle", "Women Black Solid Oversized Sweatshirt", None, "sweatshirt",
      599, 1299, 4.1, 3320, 2, "hoodie women black oversized", flips=13, image_text="Black Oversized Sweatshirt", bg="1a1a1a", fg="ffffff",
      colour="Black", gender="Women", fit="Oversized", material="Cotton Blend", size="Free"),
    # Spec group 3: cotton hoodie vs polyester sweatshirt — must NOT be exact
    L("AMZ-1005", "amazon", "Urban Threads", "Black Cotton Hoodie", None, "hoodie",
      799, 1599, 4.2, 540, 2, "hoodie plain black", flips=0, image_text="Black Hoodie", bg="101010", fg="ffffff",
      colour="Black", material="Cotton", gender="Unisex", size="L"),
    L("MYN-4005", "myntra", "Myntra Jabong", "Black Polyester Oversized Sweatshirt", "Kook N Keech", "sweatshirt",
      899, 1999, 4.0, 210, 3, "hoodie plain black", salt="poly", flips=12, image_text="Black Sweatshirt", bg="141414", fg="ffffff",
      colour="Black", material="Polyester", fit="Oversized", gender="Unisex", size="L"),

    # ───────────── EXACT GROUP 3: Spigen Ultra Hybrid clear case, iPhone 17 ─────────────
    L("AMZ-1006", "amazon", "Spigen India", "Spigen Ultra Hybrid Back Cover Case for iPhone 17 - Crystal Clear", "Spigen", "phone case",
      1299, 1999, 4.5, 7120, 1, "case spigen clear iphone17", flips=0, image_text="Spigen Clear Case", bg="e8f0f8", fg="333333",
      desc="Crystal clear TPU bumper with hard PC back, Air Cushion corners.", colour="Clear", model="iPhone 17", material="TPU + PC"),
    L("FLP-3004", "flipkart", "SpigenStore", "Spigen Back Cover for Apple iPhone 17 (Ultra Hybrid, Crystal Clear)", "Spigen", "phone case",
      1199, 1999, 4.4, 3012, 2, "case spigen clear iphone17", flips=1, image_text="Spigen Clear Case", bg="e8f0f8", fg="333333",
      colour="Crystal Clear", model="iPhone 17", material="TPU + PC"),
    L("MSH-5002", "meesho", "Mobile Mart", "Spigen Ultra Hybrid Crystal Clear Case iPhone 17", "Spigen", "phone case",
      999, 1999, 4.0, 431, 5, "case spigen clear iphone17", flips=2, image_text="Spigen Clear Case", bg="e8f0f8", fg="333333",
      colour="Clear", model="iPhone 17"),
    # SIMILAR: 17 Pro model; generic clear case
    L("AMZ-1007", "amazon", "Spigen India", "Spigen Ultra Hybrid Case for iPhone 17 Pro - Crystal Clear", "Spigen", "phone case",
      1399, 2099, 4.5, 2210, 1, "case spigen clear iphone17", salt="pro", flips=8, image_text="Spigen Clear Case Pro", bg="e4ecf4", fg="333333",
      colour="Clear", model="iPhone 17 Pro", material="TPU + PC"),
    L("MSH-5003", "meesho", "CaseWala", "Transparent Soft Silicone Back Cover for iPhone 17", None, "phone case",
      149, 499, 3.7, 12030, 4, "case spigen clear iphone17", salt="generic", flips=14, image_text="Clear Case", bg="eef2f6", fg="333333",
      colour="Transparent", model="iPhone 17", material="Silicone"),
    L("FLP-3005", "flipkart", "Ringke Official", "Ringke Fusion Clear Case for iPhone 17", "Ringke", "phone case",
      1099, 1799, 4.3, 980, 2, "case ringke clear iphone17", image_text="Ringke Clear Case", bg="e6eef6", fg="333333",
      colour="Clear", model="iPhone 17"),

    # ───────────── EXACT GROUP 4: Nike Court Vision Low white sneakers, men UK 9 ─────────────
    L("AMZ-1008", "amazon", "Nike India", "Nike Men's Court Vision Low White Sneakers (UK 9)", "Nike", "sneakers",
      4495, 5695, 4.4, 2980, 2, "sneaker nike cv low white", flips=0, image_text="Nike Court Vision", bg="f7f7f7", fg="222222",
      desc="Retro basketball style, leather upper, Nike Court Vision Low Next Nature.", colour="White", size="UK 9", gender="Men", model="Court Vision Low"),
    L("MYN-4006", "myntra", "Myntra Jabong", "Nike Men White Court Vision Low Next Nature Sneakers", "Nike", "sneakers",
      4095, 5695, 4.5, 4120, 2, "sneaker nike cv low white", flips=1, image_text="Nike Court Vision", bg="f7f7f7", fg="222222",
      colour="White", size="UK 9", gender="Men", model="Court Vision Low"),
    L("AJO-6003", "ajio", "Reliance Retail", "NIKE Court Vision Low Lace-Up Sneakers - White", "Nike", "sneakers",
      3987, 5695, 4.3, 655, 4, "sneaker nike cv low white", flips=2, image_text="Nike Court Vision", bg="f7f7f7", fg="222222",
      colour="White", size="UK 9", gender="Men", model="Court Vision Low"),
    L("FLP-3006", "flipkart", "SportsHub", "NIKE Court Vision LO Sneakers For Men (White, UK 9)", "Nike", "sneakers",
      4299, 5695, 4.2, 1330, 3, "sneaker nike cv low white", flips=1, image_text="Nike Court Vision", bg="f7f7f7", fg="222222",
      colour="White", size="UK 9", gender="Men", model="Court Vision Low"),
    # SIMILAR: same shoe UK 8 (size differs → NOT exact), mid-top version, generic white sneakers
    L("MYN-4007", "myntra", "Myntra Jabong", "Nike Men White Court Vision Low Next Nature Sneakers (UK 8)", "Nike", "sneakers",
      4095, 5695, 4.5, 4120, 2, "sneaker nike cv low white", flips=0, image_text="Nike Court Vision", bg="f7f7f7", fg="222222",
      colour="White", size="UK 8", gender="Men", model="Court Vision Low"),
    L("AJO-6004", "ajio", "Reliance Retail", "NIKE Court Vision Mid Sneakers - White", "Nike", "sneakers",
      4795, 6295, 4.2, 210, 4, "sneaker nike cv low white", salt="mid", flips=11, image_text="Nike Court Vision Mid", bg="f5f5f5", fg="222222",
      colour="White", size="UK 9", gender="Men", model="Court Vision Mid"),
    L("MSH-5004", "meesho", "Fashion Feet", "White Casual Sneakers for Men Lightweight", None, "sneakers",
      499, 1299, 3.8, 15600, 5, "sneaker generic white", image_text="White Sneakers", bg="f9f9f9", fg="222222",
      colour="White", size="UK 9", gender="Men"),
    L("FLP-3007", "flipkart", "Sparx Store", "Sparx Men SM-9034 White Sneakers", "Sparx", "sneakers",
      1199, 1799, 4.1, 8900, 3, "sneaker sparx white", image_text="Sparx Sneakers", bg="fafafa", fg="222222",
      colour="White", size="UK 9", gender="Men", model="SM-9034"),

    # ───────────── EXACT GROUP 5: boAt Airdopes 141, black ─────────────
    L("AMZ-1009", "amazon", "boAt Lifestyle", "boAt Airdopes 141 TWS Earbuds, 42H Playtime, Bold Black", "boAt", "earbuds",
      1099, 4490, 4.1, 310450, 1, "earbuds boat 141 black", flips=0, image_text="Airdopes 141", bg="0f0f0f", fg="ffffff",
      desc="True wireless earbuds with 42 hours playback, ENx tech, IPX4.", colour="Bold Black", model="Airdopes 141"),
    L("FLP-3008", "flipkart", "TrueComRetail", "boAt Airdopes 141 Bluetooth Headset (Bold Black, True Wireless)", "boAt", "earbuds",
      999, 4490, 4.1, 182300, 2, "earbuds boat 141 black", flips=1, image_text="Airdopes 141", bg="0f0f0f", fg="ffffff",
      colour="Bold Black", model="Airdopes 141"),
    L("MYN-4008", "myntra", "Myntra Jabong", "boAt Airdopes 141 Black TWS Earbuds", "boAt", "earbuds",
      1199, 4490, 4.2, 4410, 3, "earbuds boat 141 black", flips=2, image_text="Airdopes 141", bg="0f0f0f", fg="ffffff",
      colour="Black", model="Airdopes 141"),
    # SIMILAR: 141 ANC (different model)
    L("AMZ-1010", "amazon", "boAt Lifestyle", "boAt Airdopes 141 ANC TWS Earbuds, 32dB ANC, Black", "boAt", "earbuds",
      1499, 4990, 4.2, 22140, 1, "earbuds boat 141 black", salt="anc", flips=9, image_text="Airdopes 141 ANC", bg="141414", fg="ffffff",
      colour="Black", model="Airdopes 141 ANC"),

    # ───────────── EXACT GROUP 6: Lakme 9to5 Primer + Matte Lipstick, MR1 Red Coat ─────────────
    L("NYK-2003", "nykaa", "Nykaa Retail", "Lakme 9to5 Primer + Matte Lipstick - MR1 Red Coat (3.6 g)", "Lakme", "lipstick",
      449, 550, 4.3, 6120, 2, "lipstick lakme 9to5 mr1", flips=0, image_text="Lakme 9to5 MR1", bg="8b0000", fg="ffffff",
      desc="Built-in primer, matte finish, 16 hour wear.", shade="MR1 Red Coat", quantity="3.6 g"),
    L("AMZ-1011", "amazon", "Cloudtail India", "Lakme 9 to 5 Primer + Matte Lip Color, Red Coat MR1, 3.6g", "Lakme", "lipstick",
      412, 550, 4.3, 24100, 1, "lipstick lakme 9to5 mr1", flips=1, image_text="Lakme 9to5 MR1", bg="8b0000", fg="ffffff",
      shade="MR1 Red Coat", quantity="3.6 g"),
    L("FLP-3009", "flipkart", "RetailNet", "LAKMÉ 9 to 5 Primer + Matte Lipstick (MR1 Red Coat, 3.6 g)", "Lakme", "lipstick",
      396, 550, 4.2, 9870, 3, "lipstick lakme 9to5 mr1", flips=2, image_text="Lakme 9to5 MR1", bg="8b0000", fg="ffffff",
      shade="Red Coat MR1", quantity="3.6 g"),
    L("MYN-4009", "myntra", "Myntra Beauty", "Lakme 9 to 5 Primer + Matte Lipstick MR1 Red Coat", "Lakme", "lipstick",
      467, 550, 4.4, 1450, 2, "lipstick lakme 9to5 mr1", flips=1, image_text="Lakme 9to5 MR1", bg="8b0000", fg="ffffff",
      shade="MR1 Red Coat", quantity="3.6 g"),
    # SIMILAR: different shade
    L("NYK-2004", "nykaa", "Nykaa Retail", "Lakme 9to5 Primer + Matte Lipstick - MP2 Pink Perfect (3.6 g)", "Lakme", "lipstick",
      449, 550, 4.2, 3010, 2, "lipstick lakme 9to5 mr1", salt="mp2", flips=8, image_text="Lakme 9to5 MP2", bg="c2185b", fg="ffffff",
      shade="MP2 Pink Perfect", quantity="3.6 g"),

    # ───────────── EXACT GROUP 7: Mamaearth Ubtan Face Wash 100 ml ─────────────
    L("AMZ-1012", "amazon", "Honasa Consumer", "Mamaearth Ubtan Natural Face Wash for All Skin Types with Turmeric & Saffron, 100ml", "Mamaearth", "face wash",
      229, 259, 4.2, 89400, 1, "facewash mamaearth ubtan", flips=0, image_text="Ubtan Face Wash", bg="e6b422", fg="333333",
      desc="Tan removal face wash with turmeric, saffron and walnut beads.", quantity="100 ml", variant="Ubtan"),
    L("NYK-2005", "nykaa", "Nykaa Retail", "Mamaearth Ubtan Face Wash With Turmeric & Saffron For Tan Removal (100 ml)", "Mamaearth", "face wash",
      233, 259, 4.3, 12300, 2, "facewash mamaearth ubtan", flips=1, image_text="Ubtan Face Wash", bg="e6b422", fg="333333",
      quantity="100 ml", variant="Ubtan"),
    L("FLP-3010", "flipkart", "OmniRetail", "Mamaearth Ubtan Face Wash 100ml Face Wash", "Mamaearth", "face wash",
      219, 259, 4.2, 45120, 2, "facewash mamaearth ubtan", flips=1, image_text="Ubtan Face Wash", bg="e6b422", fg="333333",
      quantity="100 ml", variant="Ubtan"),
    L("MSH-5005", "meesho", "Daily Needs Store", "Mamaearth Ubtan Face Wash Turmeric Saffron 100 ml", "Mamaearth", "face wash",
      199, 259, 4.0, 3900, 4, "facewash mamaearth ubtan", flips=2, image_text="Ubtan Face Wash", bg="e6b422", fg="333333",
      quantity="100 ml", variant="Ubtan"),
    # SIMILAR: 250 ml pump (quantity differs → NOT exact)
    L("AMZ-1013", "amazon", "Honasa Consumer", "Mamaearth Ubtan Face Wash with Turmeric & Saffron, 250ml", "Mamaearth", "face wash",
      449, 549, 4.2, 15400, 1, "facewash mamaearth ubtan", salt="250", flips=8, image_text="Ubtan Face Wash 250", bg="e0ad1d", fg="333333",
      quantity="250 ml", variant="Ubtan"),

    # ───────────── EXACT GROUP 8: Samsung 25W USB-C fast charger, white ─────────────
    L("AMZ-1014", "amazon", "Appario Retail", "Samsung Original 25W Type-C Super Fast Charger Adapter (White)", "Samsung", "charger",
      1299, 1799, 4.3, 41200, 1, "charger samsung 25w white", flips=0, image_text="Samsung 25W", bg="f4f4f4", fg="222222",
      desc="25W USB-C PD adaptive fast charging travel adapter, cable not included.", colour="White", wattage="25W", model="EP-TA800"),
    L("FLP-3011", "flipkart", "SuperComNet", "SAMSUNG 25 W 3 A Mobile EP-TA800 Charger (White)", "Samsung", "charger",
      1199, 1799, 4.3, 76000, 2, "charger samsung 25w white", flips=1, image_text="Samsung 25W", bg="f4f4f4", fg="222222",
      colour="White", wattage="25W", model="EP-TA800"),
    L("MSH-5006", "meesho", "Gadget Galaxy", "Samsung 25W Super Fast Charging Adapter White Type C", "Samsung", "charger",
      899, 1799, 3.9, 6100, 4, "charger samsung 25w white", flips=2, image_text="Samsung 25W", bg="f4f4f4", fg="222222",
      colour="White", wattage="25W"),
    # SIMILAR: 45W
    L("AMZ-1015", "amazon", "Appario Retail", "Samsung 45W USB-C Super Fast Charging Adapter with Cable (White)", "Samsung", "charger",
      2499, 3499, 4.4, 9800, 1, "charger samsung 25w white", salt="45", flips=9, image_text="Samsung 45W", bg="f0f0f0", fg="222222",
      colour="White", wattage="45W", model="EP-T4510"),

    # ───────────── EXACT GROUP 9: Levi's 511 slim jeans, dark indigo, W32 ─────────────
    L("AMZ-1016", "amazon", "Levi's Official", "Levi's Men's 511 Slim Fit Jeans, Dark Indigo (32W x 32L)", "Levi's", "jeans",
      2399, 3999, 4.3, 18700, 2, "jeans levis 511 dark indigo", flips=0, image_text="Levis 511", bg="1c2b4a", fg="ffffff",
      desc="Slim fit through thigh and leg, stretch denim.", colour="Dark Indigo", size="32", fit="Slim", gender="Men", model="511"),
    L("MYN-4010", "myntra", "Myntra Jabong", "Levis Men 511 Slim Fit Dark Blue Stretchable Jeans (32)", "Levis", "jeans",
      2199, 3999, 4.4, 9200, 2, "jeans levis 511 dark indigo", flips=1, image_text="Levis 511", bg="1c2b4a", fg="ffffff",
      colour="Dark Indigo", size="32", fit="Slim", gender="Men", model="511"),
    L("AJO-6005", "ajio", "Reliance Retail", "LEVI'S 511 Slim Fit Jeans - Dark Indigo", "Levi's", "jeans",
      1999, 3999, 4.2, 1300, 4, "jeans levis 511 dark indigo", flips=2, image_text="Levis 511", bg="1c2b4a", fg="ffffff",
      colour="Dark Indigo", size="32", fit="Slim", gender="Men", model="511"),
    L("FLP-3012", "flipkart", "Levi's Store", "Levi's Slim Men Dark Blue Jeans 511 (Size 32)", "Levi's", "jeans",
      2299, 3999, 4.3, 5600, 3, "jeans levis 511 dark indigo", flips=1, image_text="Levis 511", bg="1c2b4a", fg="ffffff",
      colour="Dark Indigo", size="32", fit="Slim", gender="Men", model="511"),
    # SIMILAR: size 34; 512 model
    L("MYN-4011", "myntra", "Myntra Jabong", "Levis Men 511 Slim Fit Dark Blue Stretchable Jeans (34)", "Levis", "jeans",
      2199, 3999, 4.4, 9200, 2, "jeans levis 511 dark indigo", flips=0, image_text="Levis 511", bg="1c2b4a", fg="ffffff",
      colour="Dark Indigo", size="34", fit="Slim", gender="Men", model="511"),
    L("AMZ-1017", "amazon", "Levi's Official", "Levi's Men's 512 Slim Taper Jeans, Dark Indigo (32W)", "Levi's", "jeans",
      2599, 4299, 4.3, 7100, 2, "jeans levis 511 dark indigo", salt="512", flips=9, image_text="Levis 512", bg="1a2946", fg="ffffff",
      colour="Dark Indigo", size="32", fit="Slim Taper", gender="Men", model="512"),

    # ───────────── EXACT GROUP 10: American Tourister AMT Sky 32L backpack, black ─────────────
    L("AMZ-1018", "amazon", "Samsonite India", "American Tourister AMT Sky 32 Ltrs Black Casual Backpack", "American Tourister", "backpack",
      1149, 2600, 4.3, 27300, 2, "backpack amt sky black", flips=0, image_text="AMT Sky Backpack", bg="121212", fg="ffffff",
      desc="32 litre laptop-compatible casual backpack, 3 compartments.", colour="Black", capacity="32 L", model="AMT Sky"),
    L("FLP-3013", "flipkart", "SamsoniteRetail", "AMERICAN TOURISTER AMT Sky 32 L Laptop Backpack (Black)", "American Tourister", "backpack",
      1099, 2600, 4.3, 44100, 3, "backpack amt sky black", flips=1, image_text="AMT Sky Backpack", bg="121212", fg="ffffff",
      colour="Black", capacity="32 L", model="AMT Sky"),
    L("MYN-4012", "myntra", "Myntra Jabong", "American Tourister Unisex Black AMT Sky Backpack 32L", "American Tourister", "backpack",
      1299, 2600, 4.4, 3120, 2, "backpack amt sky black", flips=2, image_text="AMT Sky Backpack", bg="121212", fg="ffffff",
      colour="Black", capacity="32 L", model="AMT Sky"),
    L("AJO-6006", "ajio", "Reliance Retail", "AMERICAN TOURISTER AMT Sky Backpack with Laptop Compartment - Black 32L", "American Tourister", "backpack",
      1039, 2600, 4.2, 480, 4, "backpack amt sky black", flips=1, image_text="AMT Sky Backpack", bg="121212", fg="ffffff",
      colour="Black", capacity="32 L", model="AMT Sky"),
    # SIMILAR: same backpack in grey
    L("AMZ-1019", "amazon", "Samsonite India", "American Tourister AMT Sky 32 Ltrs Grey Casual Backpack", "American Tourister", "backpack",
      1149, 2600, 4.3, 27300, 2, "backpack amt sky black", salt="grey", flips=10, image_text="AMT Sky Grey", bg="6b6b6b", fg="ffffff",
      colour="Grey", capacity="32 L", model="AMT Sky"),

    # ───────────── UNRELATED / NOISE (10) ─────────────
    L("MSH-5007", "meesho", "Anokhi Creations", "Women Rayon Printed Anarkali Kurta Set with Dupatta - Teal", None, "kurta set",
      649, 1999, 3.9, 21400, 5, "kurta teal anarkali", image_text="Anarkali Kurta", bg="0b7a75", fg="ffffff", colour="Teal", gender="Women", size="L"),
    L("NYK-2006", "nykaa", "Nykaa Retail", "Minimalist SPF 50 Sunscreen PA++++ with Multi-Vitamins 50 ml", "Minimalist", "sunscreen",
      399, 399, 4.4, 14200, 2, "sunscreen minimalist spf50", image_text="Minimalist SPF 50", bg="ffffff", fg="333333", quantity="50 ml"),
    L("AMZ-1020", "amazon", "Cloudtail India", "Prestige Svachh 5 Litre Aluminium Pressure Cooker", "Prestige", "pressure cooker",
      1879, 2795, 4.4, 33100, 2, "cooker prestige 5l", image_text="Pressure Cooker", bg="d9d9d9", fg="222222", capacity="5 L"),
    L("FLP-3014", "flipkart", "Flipkart", "SAMSUNG Galaxy M35 5G (Thunder Grey, 128 GB) (6 GB RAM)", "Samsung", "smartphone",
      15999, 20999, 4.3, 128400, 2, "phone galaxy m35 grey", image_text="Galaxy M35", bg="2f2f2f", fg="ffffff", colour="Thunder Grey", storage="128 GB", model="Galaxy M35"),
    L("AJO-6007", "ajio", "Reliance Retail", "TITAN Neo Analog Watch with Leather Strap - Brown", "Titan", "watch",
      3495, 4995, 4.2, 320, 4, "watch titan neo brown", image_text="Titan Neo", bg="5a3a1a", fg="ffffff", colour="Brown", gender="Men"),
    L("MYN-4013", "myntra", "Myntra Jabong", "Fossil Women Tan Textured Leather Shoulder Bag", "Fossil", "handbag",
      8995, 12995, 4.6, 140, 3, "bag fossil tan leather", image_text="Fossil Bag", bg="c98d4b", fg="ffffff", colour="Tan", gender="Women", material="Leather"),
    L("AMZ-1021", "amazon", "Milton Store", "Milton Thermosteel Flip Lid Flask 1000 ml, Silver", "Milton", "water bottle",
      749, 1195, 4.4, 51200, 1, "flask milton 1000", image_text="Milton Flask", bg="cfd3d6", fg="222222", capacity="1000 ml", colour="Silver"),
    L("NYK-2007", "nykaa", "Nykaa Retail", "The Ordinary Niacinamide 10% + Zinc 1% Serum 30 ml", "The Ordinary", "serum",
      590, 590, 4.3, 7600, 2, "serum ordinary niacinamide", image_text="Niacinamide 10%", bg="f3f3f3", fg="333333", quantity="30 ml"),
    L("FLP-3015", "flipkart", "HP Store", "HP 150 Wireless Optical Mouse (Black)", "HP", "mouse",
      599, 899, 4.2, 20100, 2, "mouse hp 150 black", image_text="HP Mouse", bg="1e1e1e", fg="ffffff", colour="Black", model="150"),
    L("MSH-5008", "meesho", "Home Decor Hub", "Cotton King Size Double Bedsheet with 2 Pillow Covers - Floral Blue", None, "bedsheet",
      399, 1499, 3.8, 42000, 6, "bedsheet floral blue king", image_text="Floral Bedsheet", bg="3a6ea5", fg="ffffff", colour="Blue", size="King", material="Cotton"),
]
