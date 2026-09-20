/**
 * KuralAgri Frontend API Client
 * Connects to Django REST backend with auto-token management and typed interfaces.
 */

const API_BASE = '/api/v1';

export interface User {
  id: string;
  phone: string;
  full_name: string;
  role: 'FARMER' | 'BUYER' | 'ADMIN' | 'FPO';
  language: string;
}

export interface Crop {
  id: string;
  name: string;
  category: string;
  msp_per_kg: string;
  markdown_factor: string;
  perishability_class: string;
  usable_life_hours: number;
  urgency_rate_per_kg: string;
  retail_markup: string;
  default_shelf_life_days: number;
}

export interface Region {
  id: string;
  name: string;
  state: string;
  district: string;
}

export interface Listing {
  id: string;
  crop: { id: string; name: string } | string;
  grade: string;
  quantity_kg: string;
  reserved_kg: string;
  available_kg: string;
  remaining_shelf_life_hours: string;
  usable_life_hours: string;
  village: string;
  district: string;
  latitude: string;
  longitude: string;
  self_delivery: boolean;
  status: 'ACTIVE' | 'RESERVED' | 'IN_LOT' | 'COLLECTED' | 'DELIVERED' | 'CANCELLED' | 'EXPIRED';
  farmer?: {
    id: string;
    village: string;
    district: string;
    user?: { full_name: string; phone: string };
  };
  created_at: string;
}

export interface BuyerOrder {
  id: string;
  order_code: string;
  buyer: {
    id: string;
    organisation: string;
    buyer_type: string;
    district: string;
  };
  crop: { id: string; name: string } | string;
  grade: string;
  quantity_kg: string;
  delivery_deadline: string;
  max_price_per_kg: string;
  sourcing_preference: 'AGGREGATED' | 'SINGLE_SOURCE';
  allow_partial: boolean;
  min_acceptable_quantity_kg?: string;
  delivery_district: string;
  status: 'OPEN' | 'MATCHED' | 'FULFILLED' | 'CANCELLED';
  created_at: string;
}

export interface LotContribution {
  id: string;
  farmer: {
    id: string;
    village: string;
    district: string;
    user?: { full_name: string; phone: string };
  };
  committed_quantity_kg: string;
  delivered_quantity_kg: string;
  advance_amount: string;
  interest_amount: string;
  lender_claim: string;
  residual_entitlement: string;
  status: string;
}

export interface Lot {
  id: string;
  lot_code: string;
  crop: { id: string; name: string } | string;
  grade: string;
  total_quantity_kg: string;
  delivered_quantity_kg: string;
  floor_price_per_kg: string;
  minimum_viable_price_per_kg: string;
  agreed_price_per_kg?: string;
  logistics_cost: string;
  status: 'PROPOSED' | 'ACCEPTED' | 'ESCROW_FUNDED' | 'IN_TRANSIT' | 'DELIVERED' | 'ACCEPTED_FULL' | 'PARTIALLY_ACCEPTED' | 'SETTLED' | 'REJECTED';
  buyer_order?: BuyerOrder;
  contributions: LotContribution[];
  created_at: string;
}

export interface PriceBreakdown {
  lot_id: string;
  lot_code: string;
  crop: string;
  grade: string;
  quantity_kg: string;
  floor_price_per_kg: string;
  minimum_viable_lot_price: string;
  buyer_ceiling_per_kg: string;
  is_viable: boolean;
  logistics_total: string;
  logistics_per_kg: string;
  lender_claim_total: string;
  lender_claim_per_kg: string;
  platform_fee_total: string;
  risk_reserve_total: string;
  farmer_residual_pool: string;
  recommended_price_per_kg: string;
  recommended_price_range: [string, string];
  waterfall_preview: {
    lender_claim: string;
    platform_fee: string;
    logistics_cost: string;
    risk_reserve: string;
    farmer_pool: string;
    total: string;
  };
  contributors: Array<{
    farmer_name: string;
    village: string;
    quantity_kg: string;
    advance_amount: string;
    interest_amount: string;
    lender_claim: string;
    residual_entitlement: string;
    estimated_settlement: string;
    estimated_total: string;
    traditional_mandi_value: string;
    estimated_uplift_pct: string;
  }>;
}

export interface MarketPulse {
  benchmark_price: string;
  price_trend: 'RISING' | 'STABLE' | 'FALLING';
  supply_signal: 'HIGH' | 'NORMAL' | 'LOW';
  demand_signal: 'HIGH' | 'NORMAL' | 'LOW';
  weather_risk: 'LOW' | 'NORMAL' | 'MEDIUM' | 'HIGH';
  price_history: Array<{ recorded_date: string; modal_price: string; arrivals_kg: string }>;
}

export interface DemandForecast {
  predicted_quantity_kg: string;
  confidence_level: 'HIGH' | 'MEDIUM' | 'LOW';
  demand_level: 'HIGH' | 'NORMAL' | 'LOW';
  daily_forecast: Array<{ date: string; predicted_kg: string; historical_norm_kg: string }>;
}

export interface PriceRecommendation {
  recommended_price: string;
  price_range: [string, string];
  floor_price: string;
  mandi_benchmark: string;
  confidence_pct: number;
  explanation_bullets: string[];
  factors: Record<string, any>;
}

// Token helper
export function getStoredToken(): string | null {
  return localStorage.getItem('kuralagri_token');
}

export function setStoredToken(token: string | null) {
  if (token) {
    localStorage.setItem('kuralagri_token', token);
  } else {
    localStorage.removeItem('kuralagri_token');
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getStoredToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  const data = await response.json();
  if (!response.ok) {
    const errorMsg = data?.error?.message || data?.detail || 'Request failed';
    throw new Error(errorMsg);
  }
  // Handle paginated responses or direct objects
  return (data?.results !== undefined ? data.results : data) as T;
}

export const api = {
  // Auth
  async login(phone: string, password = 'Demo@1234'): Promise<{ access: string; user: User }> {
    const res = await request<{ access: string; refresh: string; user: User }>('/auth/login/', {
      method: 'POST',
      body: JSON.stringify({ phone, password }),
    });
    setStoredToken(res.access);
    return res;
  },

  async getMe(): Promise<User> {
    return request<User>('/auth/me/');
  },

  logout() {
    setStoredToken(null);
  },

  // Catalog
  async getCrops(): Promise<Crop[]> {
    return request<Crop[]>('/catalog/crops/');
  },
  async getRegions(): Promise<Region[]> {
    return request<Region[]>('/catalog/regions/');
  },

  // Marketplace
  async getListings(): Promise<Listing[]> {
    return request<Listing[]>('/marketplace/listings/');
  },
  async createListing(payload: {
    crop: string;
    grade: string;
    quantity_kg: number | string;
    harvest_datetime: string;
    village: string;
    district: string;
    latitude: number | string;
    longitude: number | string;
    self_delivery: boolean;
  }): Promise<Listing> {
    return request<Listing>('/marketplace/listings/', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async getBuyerOrders(): Promise<BuyerOrder[]> {
    return request<BuyerOrder[]>('/marketplace/buyer-orders/');
  },
  async createBuyerOrder(payload: {
    crop: string;
    grade: string;
    quantity_kg: number | string;
    delivery_deadline: string;
    max_price_per_kg: number | string;
    sourcing_preference: 'AGGREGATED' | 'SINGLE_SOURCE';
    allow_partial: boolean;
    min_acceptable_quantity_kg?: number | string;
    delivery_district: string;
    delivery_latitude: number | string;
    delivery_longitude: number | string;
  }): Promise<BuyerOrder> {
    return request<BuyerOrder>('/marketplace/buyer-orders/', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // Intelligence
  async getMarketPulse(cropId: string, regionId: string): Promise<MarketPulse> {
    return request<MarketPulse>(`/intelligence/market-pulse/?crop=${cropId}&region=${regionId}`);
  },
  async getDemandForecast(cropId: string, regionId: string): Promise<DemandForecast> {
    return request<DemandForecast>(`/intelligence/demand-forecast/?crop=${cropId}&region=${regionId}`);
  },
  async getPriceRecommendation(params: {
    crop: string;
    region: string;
    grade: string;
    harvest_datetime: string;
    quantity_kg: number | string;
  }): Promise<PriceRecommendation> {
    return request<PriceRecommendation>('/intelligence/recommend-price/', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  // Matching & Lots
  async matchBuyerOrder(buyerOrderId: string): Promise<{ lot: Lot; breakdown: PriceBreakdown }> {
    const lot = await request<Lot>(`/matching/orders/${buyerOrderId}/form-lot/`, {
      method: 'POST',
    });
    const breakdown = await request<PriceBreakdown>(`/matching/lots/${lot.id}/price-breakdown/`).catch(() => null as any);
    return { lot, breakdown };
  },
  async getLots(): Promise<Lot[]> {
    return request<Lot[]>('/matching/lots/');
  },
  async getLotDetail(lotId: string): Promise<Lot> {
    return request<Lot>(`/matching/lots/${lotId}/`);
  },
  async getLotPriceBreakdown(lotId: string): Promise<PriceBreakdown> {
    return request<PriceBreakdown>(`/matching/lots/${lotId}/price-breakdown/`);
  },
  async acceptLot(lotId: string, agreedPrice: number | string): Promise<{ lot: Lot; message: string }> {
    const lot = await request<Lot>(`/matching/lots/${lotId}/accept/`, {
      method: 'POST',
      body: JSON.stringify({ agreed_price: agreedPrice }),
    });
    return { lot, message: 'Lot accepted successfully' };
  },

  // Finance & Escrow
  async fundEscrow(lotId: string): Promise<{ message: string; escrow_id: string; total_received: string }> {
    return request<{ message: string; escrow_id: string; total_received: string }>(`/finance/lots/${lotId}/escrow/fund/`, {
      method: 'POST',
    });
  },
  async releaseAdvances(lotId: string): Promise<{ message: string; advances_count: number }> {
    return request<{ message: string; advances_count: number }>(`/finance/lots/${lotId}/advances/release/`, {
      method: 'POST',
    });
  },
  async getLedgerEntries(lotId?: string): Promise<any[]> {
    const url = lotId ? `/finance/lots/${lotId}/ledger/` : '/finance/ledger/';
    return request<any[]>(url);
  },

  // Logistics & Destinations
  async evaluateDestinations(lotId: string): Promise<any[]> {
    return request<any[]>(`/logistics/candidates/?lot_id=${lotId}`);
  },
  async planRoute(lotId: string, vehicleId?: string): Promise<any> {
    return request<any>('/logistics/routes/', {
      method: 'POST',
      body: JSON.stringify({ lot_id: lotId, vehicle_id: vehicleId }),
    });
  },
  async getRoutes(lotId?: string): Promise<any[]> {
    const query = lotId ? `?lot_id=${lotId}` : '';
    return request<any[]>(`/logistics/routes/${query}`);
  },
  async getVehicles(): Promise<any[]> {
    return request<any[]>('/logistics/vehicles/');
  },

  // Quality & Recovery
  async submitQualityCheck(payload: {
    lot_id: string;
    stage?: 'INTAKE' | 'HANDOVER';
    verified_grade?: string;
    verified_qty_kg?: number | string;
    notes?: string;
  }): Promise<any> {
    return request<any>(`/quality/lots/${payload.lot_id}/quality-check/`, {
      method: 'POST',
      body: JSON.stringify({
        stage: payload.stage || 'HANDOVER',
        verified_grade: payload.verified_grade || 'A',
        verified_qty_kg: payload.verified_qty_kg,
        notes: payload.notes || '',
      }),
    });
  },
  async recoverLot(payload: {
    original_lot_id: string;
    quantity_kg?: number | string;
    grade?: string;
    remaining_shelf_life_hours?: number | string;
  }): Promise<any> {
    return request<any>(`/quality/lots/${payload.original_lot_id}/recover/`, {
      method: 'POST',
      body: JSON.stringify({
        quantity_kg: payload.quantity_kg || 150,
        grade: payload.grade || 'B',
        remaining_shelf_life_hours: payload.remaining_shelf_life_hours || 6,
      }),
    });
  },

  // Settlement
  async settleLot(lotId: string): Promise<any> {
    return request<any>(`/settlement/lots/${lotId}/settle/`, {
      method: 'POST',
    });
  },
  async getSettlements(lotId: string): Promise<any[]> {
    return request<any[]>(`/settlement/lots/${lotId}/settlements/`);
  },

  // Admin Reset
  async resetDemoData(): Promise<{ status: string; message: string }> {
    return request<{ status: string; message: string }>('/admin/reset-demo/', {
      method: 'POST',
    });
  }
};
