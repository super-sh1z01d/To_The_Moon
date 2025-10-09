// API Base URL
export const API_BASE_URL = import.meta.env.VITE_API_URL || ''

// Token statuses
export const TOKEN_STATUS = {
  ACTIVE: 'active',
  MONITORING: 'monitoring',
  ARCHIVED: 'archived',
} as const

export type TokenStatus = typeof TOKEN_STATUS[keyof typeof TOKEN_STATUS]

// Score thresholds
export const SCORE_THRESHOLDS = {
  BOT_READY: 0.9,
  WATCH_LIST: 0.7,
  LOW: 0.5,
} as const

// Spam risk levels
export const SPAM_RISK_LEVELS = {
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
} as const

export type SpamRiskLevel = typeof SPAM_RISK_LEVELS[keyof typeof SPAM_RISK_LEVELS]

// Refresh intervals (ms)
export const REFRESH_INTERVALS = {
  DASHBOARD: 10000, // 10 seconds
  TOKEN_DETAIL: 5000, // 5 seconds
  MONITORING: 5000, // 5 seconds
  SETTINGS: 30000, // 30 seconds
} as const

// Pagination
export const DEFAULT_PAGE_SIZE = 50
export const PAGE_SIZE_OPTIONS = [25, 50, 100, 200]

// Debounce delays (ms)
export const DEBOUNCE_DELAYS = {
  SEARCH: 300,
  FILTER: 300,
  RESIZE: 150,
} as const

// Date formats
export const DATE_FORMATS = {
  FULL: 'PPpp', // Jan 1, 2024, 12:00 PM
  SHORT: 'PP', // Jan 1, 2024
  TIME: 'p', // 12:00 PM
  RELATIVE: 'relative', // 2 hours ago
} as const

// Chart colors
export const CHART_COLORS = {
  PRIMARY: 'hsl(var(--primary))',
  SUCCESS: 'hsl(142.1 76.2% 36.3%)',
  WARNING: 'hsl(38 92% 50%)',
  DANGER: 'hsl(0 84.2% 60.2%)',
  INFO: 'hsl(221.2 83.2% 53.3%)',
  MUTED: 'hsl(var(--muted-foreground))',
} as const

// Component weights (for score breakdown)
export const COMPONENT_LABELS = {
  tx_accel: 'TX Accel',
  vol_momentum: 'Volume',
  freshness: 'Fresh',
  orderflow_imbalance: 'Orderflow',
} as const

// External links
export const EXTERNAL_LINKS = {
  SOLSCAN: 'https://solscan.io/token/',
  DEXSCREENER: 'https://dexscreener.com/solana/',
  BIRDEYE: 'https://birdeye.so/token/',
} as const
