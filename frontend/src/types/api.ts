// Generic API response wrapper
export interface ApiResponse<T> {
  data?: T
  error?: ApiError
}

export interface ApiError {
  code: number
  message: string
  path?: string
}

// Health check response
export interface HealthResponse {
  status: 'ok' | 'error'
  version?: string
  uptime?: number
}

// Version response
export interface VersionResponse {
  version: string
  commit?: string
  build_date?: string
}

// Logs response
export interface LogEntry {
  ts: string
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL'
  logger: string
  msg: string
  module?: string
  func?: string
  line?: number
}

export interface LogsResponse {
  logs: LogEntry[]
  total: number
}

// Admin actions
export interface AdminActionResponse {
  success: boolean
  message: string
  affected?: number
}

// Monitoring metrics
export interface MonitoringMetrics {
  backlog_size: number
  processing_rate: number
  memory_usage: number
  memory_peak: number
  active_tokens: number
  monitoring_tokens: number
  archived_tokens: number
  timestamp: string
}

// NotArb pools export
export interface NotArbPool {
  mint_address: string
  symbol: string
  score: number
  liquidity_usd: number
  pools: {
    dex: string
    pair: string
    address: string
  }[]
}

export interface NotArbExportResponse {
  pools: NotArbPool[]
  metadata: {
    generated_at: string
    min_score: number
    max_spam_percentage: number
    total_tokens: number
  }
}
