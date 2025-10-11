export interface Pool {
  address?: string
  dex?: string
  quote?: string
  solscan_url?: string
  count?: number
}

export interface ScoreComponents {
  tx_accel: number
  vol_momentum: number
  freshness: number
  orderflow_imbalance: number
}

export interface SpamMetrics {
  spam_percentage: number
  risk_level: 'low' | 'medium' | 'high'
  compute_budget_ratio: number
  transactions_analyzed: number
  timestamp?: string
}

export interface Token {
  mint_address: string
  name: string | null
  symbol: string | null
  status: 'active' | 'monitoring' | 'archived'
  score: number
  liquidity_usd: number
  delta_p_5m: number
  delta_p_15m: number
  n_5m: number
  primary_dex: string
  pools?: Pool[]
  fetched_at: string
  scored_at: string
  last_processed_at: string
  solscan_url: string
  image_url?: string | null
  raw_components: ScoreComponents
  spam_metrics?: SpamMetrics
  created_at?: string
  updated_at?: string
}

export interface TokensResponse {
  total: number
  items: Token[]
}

export interface TokenFilters {
  status?: 'active' | 'monitoring' | 'archived'
  minScore?: number
  maxSpam?: number
  search?: string
  page?: number
  limit?: number
  sort?: 'score_desc' | 'score_asc'
}

export interface TokenDetailResponse extends Token {
  history?: TokenHistory[]
}

export interface TokenHistory {
  timestamp: string
  score: number
  liquidity_usd: number
  price_usd: number
  volume_5m: number
}
