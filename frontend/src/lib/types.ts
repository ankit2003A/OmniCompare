export type MarketplaceRef = { slug: string; name: string; logo_url: string; brand_color: string };

export type DeliveryInfo = {
  deliveryDays: number;
  deliveryDate: string;
  deliveryText: string;
  available: boolean;
  isDemo: boolean;
};

export type Listing = {
  id: number;
  listing_id: string;
  product_id: number;
  marketplace: MarketplaceRef;
  seller_name: string;
  title: string;
  description: string;
  brand: string | null;
  category: string | null;
  price: number;
  mrp: number;
  discount_percentage: number;
  currency: string;
  image_url: string;
  rating: number;
  review_count: number;
  availability: "in_stock" | "low_stock" | "out_of_stock";
  delivery_days: number;
  delivery_date: string;
  delivery_text: string;
  delivery: DeliveryInfo;
  product_attributes: Record<string, string>;
  product_url: string;
  is_live?: boolean;
  relevance?: number;
};

export type Reason = { label: string; status: "ok" | "warn" | "info" };

export type MatchExplanation = {
  confidence: number | null;
  reasons: Reason[];
  pair_count?: number;
  scores?: { text: number; attribute: number; image: number };
};

export type ProductGroup = {
  id: number;
  canonical_title: string;
  brand: string | null;
  category: string | null;
  description: string | null;
  canonical_image: string | null;
  attributes: Record<string, string>;
  listing_count: number;
  marketplaces: MarketplaceRef[];
  listings: Listing[];
  match: MatchExplanation;
  cheapest: { listing_id: number; price: number; marketplace: MarketplaceRef } | null;
  fastest: { listing_id: number; deliveryDays: number; deliveryText: string; marketplace: MarketplaceRef } | null;
  price_min: number;
  price_max: number;
  rating_max: number;
  rating_min: number;
  discount_max: number;
  slowest_days: number;
  relevance?: number;
  store_count?: number;
  flags?: string[];
};

export type SimilarProduct = ProductGroup & { similarity: number; reasons: Reason[] };

export type ProductDetail = ProductGroup & {
  similar_products: SimilarProduct[];
  images: string[];
  delivery_is_demo: boolean;
  pincode: string | null;
  live?: boolean;
  error?: string | null;
};

export type SearchResponse = {
  query: string;
  pincode: string | null;
  sort: string;
  groups: ProductGroup[];
  total_groups: number;
  total_listings: number;
  delivery_is_demo: boolean;
  location?: string;
  live?: boolean;
  error?: string | null;
};

export type SortOption = { value: string; label: string };
export type Marketplace = MarketplaceRef & { id: number; base_url: string };

export type SearchFilters = {
  marketplaces?: string[];
  price_min?: number;
  price_max?: number;
  max_delivery_days?: number;
  min_rating?: number;
  brands?: string[];
  in_stock_only?: boolean;
};
