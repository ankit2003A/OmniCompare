# OmniCompare — AI-Powered Cross-Marketplace Shopping Comparison (MVP)

> **Demo data notice.** Every marketplace listing in this project is **mock/seeded data**.
> Nothing is scraped from Amazon, Flipkart, Meesho, Myntra, Nykaa or AJIO, and **delivery
> estimates are seeded, not live** — the UI labels them "Demo delivery estimate".

Search once → see listings from six simulated Indian marketplaces → the same physical product is
**grouped into one card** → compare price, delivery, seller, rating and discount side-by-side, with
a transparent explanation of *why* the listings were grouped.

---

## 1. Product concept

A shopper searches for e.g. `black oversized hoodie` or `Maybelline Sky High mascara`. Instead of
20 near-duplicate cards, OmniCompare shows one **product group** per real-world product, with:

- **Cheapest** — lowest price and where to get it
- **Fastest** — fewest delivery days and where to get it
- **Match confidence** (`98% match`) and a checklist of ✓ / ⚠ grouping reasons
- **Similar products** shown separately (`87% similar`) — never merged into the exact group
- Sorting by price, **fastest delivery (by `delivery_days`, not price)**, rating, discount, relevance
- A pincode input (e.g. `282001`) wired through a `getDeliveryEstimate(marketplace, product, pincode)` hook

The MVP deliberately never labels a listing "best" — only *cheapest* and *fastest*, or whatever the
user sorted by.

---

## 2. Architecture

```
USER QUERY
   ↓  GET /api/search?q=&pincode=&sort=
Search / Retrieval        services/search.py      (LIKE prefilter + IDF-weighted coverage ranking)
   ↓
Marketplace Listings      adapters/mock.py        (MockAmazonAdapter … MockAjioAdapter)
   ↓
Normalize Listings        services/normalizer.py  (aliases, stopwords, brand/category canonicalisation)
   ↓
Extract Attributes        services/normalizer.py  (colour, size, material, quantity, shade, model, wattage …)
   ↓
Text Similarity           matching/engine.py      (IDF-Dice + hashed-embedding cosine)
   ↓
Image Similarity          ai/image_similarity.py  (perceptual-hash Hamming similarity; CLIP stub)
   ↓
Product Matching          matching/engine.py      (weighted hybrid score → EXACT_MATCH / SIMILAR / DIFFERENT)
   ↓
Product Clustering        matching/clustering.py  (union-find over EXACT pairs → Product groups)
   ↓
Price + Delivery Compare  services/comparison.py, services/delivery.py
   ↓
Sorting                   services/sorting.py
   ↓
UI                        Next.js frontend
```

Layer separation required by the spec:

```
Marketplace Adapter → Raw Listing → Normalizer → Product Identity Engine → Product Group → Comparison Engine → Frontend
```

Each stage is a separate module with a small, replaceable interface (see §10).

---

## 3. Folder structure

```
omnicompare/
├── README.md
├── backend/                         FastAPI + SQLAlchemy
│   ├── requirements.txt
│   ├── .env.example
│   ├── app/
│   │   ├── main.py                  app factory, CORS, /health, routers
│   │   ├── config.py                settings (weights, thresholds, providers, DB URL)
│   │   ├── db.py                    engine / session
│   │   ├── models.py                Marketplace, Product, Listing, ProductMatch, SearchHistory
│   │   ├── schemas.py               request bodies for POST endpoints
│   │   ├── adapters/
│   │   │   ├── base.py              RawListing, DeliveryEstimate, MarketplaceAdapter interface
│   │   │   └── mock.py              six Mock*Adapter classes + ADAPTERS registry
│   │   ├── ai/
│   │   │   ├── embeddings.py        EmbeddingProvider (hashing default, OpenAI stub)
│   │   │   └── image_similarity.py  calculate_image_similarity(), pHash provider, CLIP stub
│   │   ├── matching/
│   │   │   ├── engine.py            text / attribute / image scores, hybrid score, classify()
│   │   │   └── clustering.py        union-find clustering, canonical product construction
│   │   ├── services/
│   │   │   ├── normalizer.py        title normalisation + attribute extraction
│   │   │   ├── search.py            retrieval, ranking, filters, suggestions
│   │   │   ├── sorting.py           SORT_OPTIONS, sort_listings, sort_groups
│   │   │   ├── comparison.py        cheapest/fastest, ranges, group explanation
│   │   │   └── delivery.py          DeliveryInfo + get_delivery_estimate()
│   │   ├── api/
│   │   │   ├── routes.py            all /api/* endpoints
│   │   │   └── images.py            GET /images/{slug}.svg demo product images
│   │   └── seed/
│   │       ├── catalog.py           71 hand-written listings across 6 marketplaces
│   │       └── seed.py              python -m app.seed.seed
│   └── tests/
│       ├── conftest.py
│       ├── test_matching.py
│       ├── test_sorting.py
│       └── test_search_api.py
└── frontend/                        Next.js 16 (App Router) + TypeScript + Tailwind v4
    ├── .env.example
    ├── package.json
    └── src/
        ├── app/
        │   ├── layout.tsx, page.tsx           shell + landing page (hero, examples, marketplaces)
        │   ├── globals.css                    design tokens
        │   ├── search/                        results page (filters sidebar, sort, group grid)
        │   └── product/[id]/                  product detail / comparison page
        ├── components/
        │   ├── SearchBar, Header, ProductGroupCard, ComparisonTable,
        │   ├── MatchExplanation, SortControl, FilterSidebar, MarketplaceBadge,
        │   ├── DemoLabel, Rating
        │   └── ui/                            shadcn-style primitives (button, badge, card, input, tabs, select)
        └── lib/                               api client, types, formatters, usePincode hook
```

---

## 4. Installation

Prerequisites: **Python 3.11+**, **Node 20+** (tested on 3.12 / 22). PostgreSQL is optional.

```bash
git clone <this repo> omnicompare && cd omnicompare
```

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # optional – defaults work out of the box
python -m app.seed.seed                               # creates tables + seeds 71 listings
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local                            # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                                           # http://localhost:3000
```

Open <http://localhost:3000>, search for `hoodie`, `maybelline mascara`, `iphone 17 case` or
`white sneakers`.

---

## 5. Environment variables

### `backend/.env`

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./omnicompare.db` | SQLAlchemy URL. Use `postgresql+psycopg2://user:pass@host:5432/omnicompare` for Postgres. |
| `MATCH_WEIGHT_TEXT` | `0.40` | weight of text similarity in the hybrid score |
| `MATCH_WEIGHT_ATTRIBUTE` | `0.25` | weight of attribute agreement |
| `MATCH_WEIGHT_IMAGE` | `0.35` | weight of image similarity |
| `MATCH_THRESHOLD_EXACT` | `0.90` | score ≥ this → `EXACT_MATCH` |
| `MATCH_THRESHOLD_SIMILAR` | `0.70` | score ≥ this (and < exact) → `SIMILAR` |
| `EMBEDDING_PROVIDER` | `hashing` | `hashing` (built-in) or `openai` (stub, needs key) |
| `IMAGE_SIMILARITY_PROVIDER` | `placeholder` | `placeholder`/`phash` (built-in) or `clip` (stub) |
| `OPENAI_API_KEY` | – | only used by the OpenAI stub |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | allowed frontend origins |

Weights and thresholds are read at runtime, so retuning the matcher never requires a code change.
**Re-run the seed after changing them** — clustering is computed at seed time.

### `frontend/.env.local`

| Variable | Default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | backend base URL (also used for demo image URLs) |

---

## 6. Database setup

- **Default: SQLite.** Zero setup; `python -m app.seed.seed` creates `backend/omnicompare.db`.
- **PostgreSQL:**
  ```bash
  createdb omnicompare
  export DATABASE_URL=postgresql+psycopg2://omni:omni@localhost:5432/omnicompare
  python -m app.seed.seed
  ```
  `psycopg2-binary` is already in `requirements.txt`. Models are plain SQLAlchemy 2.0 and use
  `JSON` columns for attributes, so both engines work unchanged. Tables are created with
  `Base.metadata.create_all`; add Alembic when the schema starts evolving.

The seeder is idempotent — it drops and recreates all tables each run.

---

## 7. Seed data

`backend/app/seed/catalog.py` contains **71 hand-written listings** across Amazon, Flipkart,
Meesho, Myntra, Nykaa and AJIO, built to be deliberately hard:

| Bucket | Examples |
|---|---|
| **10 exact-match groups** (2–4 listings each) | Maybelline Sky High mascara 7.2 ml (Amazon / Nykaa / Flipkart with different phrasings); Puma ESS black hoodie M; Spigen Ultra Hybrid iPhone 17 case; Nike Court Vision Low white UK 9; boAt Airdopes 141; Lakmé 9to5 MR1 lipstick; Mamaearth Ubtan face wash 100 ml; Samsung 25 W charger; Levi's 511 W32; American Tourister AMT Sky 32 L |
| **Similar-but-not-same** | Sky High *Waterproof* mascara; navy / size-L hoodie; unbranded women's oversized hoodies; **black cotton hoodie vs black polyester oversized sweatshirt**; iPhone 17 *Pro* case; generic clear case; UK 8 sneakers; Court Vision *Mid*; Airdopes 141 *ANC*; MP2 lipstick shade; 250 ml face wash; 45 W charger; W34 / 512 jeans |
| **10 unrelated noise items** | Anarkali kurta set, SPF 50 sunscreen, pressure cooker, Galaxy M35, Titan watch, Fossil bag, Milton flask, niacinamide serum, HP mouse, king-size bedsheet |

Seeding result: 6 marketplaces, 71 listings, **44 products, 10 multi-listing groups, 112 stored
pairwise matches**. All ten intended exact groups cluster correctly (lowest exact-pair score 0.91).

Demo product images are generated SVGs served by the backend (`GET /images/{slug}.svg`), so the
app has no external image dependency. Marketplace logos are intentionally not bundled (trademarks);
the UI uses text badges in each marketplace's brand colour.

---

## 8. AI matching methodology

For every candidate pair of listings the engine (`app/matching/engine.py`) computes:

1. **Text similarity** (`0.40`) — on `normalized title + brand + category + key attributes`:
   `0.5 × IDF-weighted Dice` (rare tokens like *skyhigh* or *ultrahybrid* count more than
   *black*) `+ 0.5 × cosine` of embeddings from the `EmbeddingProvider`
   (default `HashingEmbeddingProvider`: 512-dim token + character-trigram hashing).
2. **Attribute similarity** (`0.25`) — weighted agreement over extracted attributes (brand, model,
   size, colour, quantity, shade, material, gender, wattage, …). Each comparison emits a human-readable
   `Reason` (`✓ Same colour`, `⚠ Material differs`, `⚠ Size unavailable on one listing`) which
   powers the "Why these products were grouped" panel.
3. **Image similarity** (`0.35`) — `calculate_image_similarity(a, b)` → Hamming similarity of
   64-bit perceptual hashes. Seed listings ship a simulated pHash; the `PerceptualHashProvider`
   will use the real `imagehash` library if installed and images are reachable.

```
match_score = text × 0.40 + attribute × 0.25 + image × 0.35
≥ 0.90 → EXACT_MATCH   |   0.70 – 0.89 → SIMILAR   |   < 0.70 → DIFFERENT
```

**Hard caps** (guard rails on top of the score, also configurable in code):
- different brand or different category → `DIFFERENT`
- conflict on an identity-defining attribute (size, quantity, shade, model, wattage, capacity,
  colour, storage, variant) → **at most `SIMILAR`** (same image + different size is never exact)
- related-but-distinct categories (hoodie vs sweatshirt) → never exact

**Clustering** (`app/matching/clustering.py`): candidate blocking by brand/category tokens,
union-find over `EXACT_MATCH` edges, majority-vote canonical attributes, canonical title taken
from the most central listing (with size/quantity suffixes stripped). Group confidence = mean of
in-group pair scores; similar-product suggestions = highest `SIMILAR` score between any listing in
the group and any listing outside it.

Every pair score is persisted in `product_matches` with its reasons, so explanations are served
without recomputation. `POST /api/match` exposes the engine for ad-hoc pairs (by id or raw payload).

---

## 9. API

| Method | Path | Notes |
|---|---|---|
| GET | `/api/search?q=&pincode=&sort=&marketplaces=&price_min=&price_max=&max_delivery_days=&min_rating=&brands=&in_stock_only=` | normalized product groups |
| GET | `/api/search/suggestions?q=` | history + product title suggestions |
| GET | `/api/sort-options` | the sort keys below |
| GET | `/api/marketplaces` | six marketplaces + brand colours |
| GET | `/api/products/{id}` | group, listings, explanation, similar products |
| GET | `/api/products/{id}/listings?sort=&marketplaces=` | |
| GET | `/api/products/{id}/similar` | with `% similar` and reasons |
| POST | `/api/match` | `{listing_a_id, listing_b_id}` or `{listing_a:{…}, listing_b:{…}}` |
| POST | `/api/compare` | `{listing_ids:[…], pincode?, sort?}` → cheapest / fastest / ranges |
| POST | `/api/delivery-estimate` | `{marketplace, listing_id, pincode}` → `DeliveryInfo` (demo) |
| GET | `/health` | |

Sort keys: `relevance`, `price_asc`, `price_desc`, `delivery_fastest`, `delivery_slowest`,
`rating_desc`, `rating_asc`, `discount_desc`. Delivery sorts use `delivery_days`, never price.

Interactive docs: <http://localhost:8000/docs>.

---

## 10. How to replace the mock marketplace adapters

1. Implement the interface in `app/adapters/base.py`:
   ```python
   class MarketplaceAdapter:
       name: str
       def search(self, query: str) -> list[RawListing]: ...
       def get_product(self, product_id: str) -> RawListing | None: ...
       def get_delivery_estimate(self, product_id: str, pincode: str) -> DeliveryEstimate: ...
   ```
   Map the partner API response into `RawListing` (the only shape the rest of the system knows).
2. Register it in the `ADAPTERS` dict in `app/adapters/mock.py` (or a new module) under the
   marketplace key (`amazon`, `flipkart`, …).
3. Nothing downstream changes: the normalizer, matcher, clustering, comparison and UI only consume
   `RawListing` / `DeliveryEstimate`. `services/delivery.py::get_delivery_estimate()` already routes
   pincode lookups to the adapter, and `POST /api/delivery-estimate` calls it.
4. To move from seed-time to query-time matching, call `adapter.search(q)` inside
   `services/search.py` and run `cluster_listings()` on the fresh results (the functions are pure).

Only use official APIs / affiliate feeds / licensed data sources — scraping these marketplaces is
out of scope by design.

Swapping AI providers is analogous: subclass `EmbeddingProvider` or `ImageSimilarityProvider`
(CLIP / SigLIP / OpenAI stubs are already sketched) and select it via `EMBEDDING_PROVIDER` /
`IMAGE_SIMILARITY_PROVIDER`.

---

## 11. Tests

```bash
cd backend && python -m pytest -q        # 29 tests
```

- `test_matching.py` — same title + attributes → EXACT; different brand → DIFFERENT; same image +
  different size → not exact; same product different seller → EXACT; look-alikes → SIMILAR;
  weights/thresholds honoured.
- `test_sorting.py` — `price_asc`, `price_desc`, `delivery_fastest`, `delivery_slowest`,
  `rating_desc`, `discount_desc`.
- `test_search_api.py` — `hoodie`, `black hoodie`, `maybelline mascara`, `iphone case`, `sneakers`
  return the expected groups; product/similar/compare/match/delivery endpoints.

Frontend: `npm run lint`, `npx tsc --noEmit`, `npm run build` all pass.

---

## 12. What is mocked / what needs real integrations

| Component | MVP state | Real integration needed |
|---|---|---|
| Marketplace listings | seeded catalog via `Mock*Adapter` | official marketplace / affiliate APIs behind `MarketplaceAdapter` |
| Delivery estimates | seeded `delivery_days`; pincode accepted but ignored | serviceability APIs per marketplace + pincode |
| Product images | generated SVG placeholders | real image URLs (CDN) |
| Marketplace logos | text badges | licensed logo assets |
| Text embeddings | hashing (lexical, not semantic) | OpenAI / sentence-transformers |
| Image similarity | simulated perceptual hashes | CLIP / SigLIP embeddings over real images |
| Search | SQLite `LIKE` prefilter + Python ranking | Postgres `tsvector` or Elasticsearch/OpenSearch |
| Product URLs | realistic-looking demo URLs | live deep links |

---

## 13. Known limitations

- Hashing embeddings capture lexical overlap only; true paraphrases ("loose fit" vs "oversized")
  rely on the alias table in `normalizer.py`.
- Image hashes are simulated per seed listing; real photos with different backgrounds/angles will
  need CLIP-style embeddings, not pHash.
- Clustering and match scores are computed at seed time (O(n²) within blocks); for large catalogs
  move to ANN retrieval + incremental clustering.
- Pincode is captured and passed through but does not change delivery output.
- Single-listing groups show no match confidence (there is nothing to compare against).
- Search history is global (no user accounts, per spec).
- UI primitives are hand-written in shadcn style rather than pulled from the shadcn registry;
  fonts use the system stack.
- No pagination — fine for 71 listings.

---

## 14. Future roadmap

1. **Real adapters** for one marketplace via an official API, including live delivery estimates by pincode.
2. **Semantic embeddings + CLIP image similarity** behind the existing provider interfaces; retune weights on a labelled pair set.
3. **Query-time matching** with vector index (pgvector / OpenSearch k-NN) and incremental clustering.
4. PostgreSQL full-text search, then OpenSearch.
5. Human-in-the-loop match review (accept/reject pairs → training data).
6. Price history, alerts, accounts — explicitly out of MVP scope.
