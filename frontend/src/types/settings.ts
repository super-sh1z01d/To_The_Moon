export interface Setting {
  key: string
  value: string
}

export interface SettingsMap {
  [key: string]: string
}

export interface SettingDefinition {
  key: string
  label: string
  description: string
  category: string
  type: 'number' | 'text' | 'boolean' | 'textarea'
  min?: number
  max?: number
  step?: number
  defaultValue: string
}

export interface SettingsCategory {
  name: string
  label: string
  description: string
  settings: SettingDefinition[]
}

// Predefined setting categories
export const SETTINGS_CATEGORIES: SettingsCategory[] = [
  {
    name: 'scoring',
    label: 'Scoring Model Configuration',
    description: 'Configure scoring weights and model parameters',
    settings: [
      {
        key: 'w_tx',
        label: 'Transaction Weight',
        description: 'Weight for transaction acceleration component',
        category: 'scoring',
        type: 'number',
        min: 0,
        max: 1,
        step: 0.05,
        defaultValue: '0.25',
      },
      {
        key: 'w_vol',
        label: 'Volume Weight',
        description: 'Weight for volume momentum component',
        category: 'scoring',
        type: 'number',
        min: 0,
        max: 1,
        step: 0.05,
        defaultValue: '0.25',
      },
      {
        key: 'w_fresh',
        label: 'Freshness Weight',
        description: 'Weight for token freshness component',
        category: 'scoring',
        type: 'number',
        min: 0,
        max: 1,
        step: 0.05,
        defaultValue: '0.25',
      },
      {
        key: 'w_oi',
        label: 'Orderflow Weight',
        description: 'Weight for orderflow imbalance component',
        category: 'scoring',
        type: 'number',
        min: 0,
        max: 1,
        step: 0.05,
        defaultValue: '0.25',
      },
      {
        key: 'ewma_alpha',
        label: 'EWMA Alpha',
        description: 'Exponential weighted moving average smoothing parameter',
        category: 'scoring',
        type: 'number',
        min: 0.1,
        max: 1,
        step: 0.1,
        defaultValue: '0.3',
      },
      {
        key: 'freshness_threshold_hours',
        label: 'Freshness Threshold (hours)',
        description: 'Token freshness threshold in hours',
        category: 'scoring',
        type: 'number',
        min: 1,
        max: 24,
        step: 1,
        defaultValue: '6',
      },
    ],
  },
  {
    name: 'lifecycle',
    label: 'Token Lifecycle',
    description: 'Configure token lifecycle parameters',
    settings: [
      {
        key: 'archive_below_hours',
        label: 'Archive Below (hours)',
        description: 'Archive active tokens below threshold after this many hours',
        category: 'lifecycle',
        type: 'number',
        min: 1,
        max: 48,
        step: 1,
        defaultValue: '12',
      },
      {
        key: 'monitoring_timeout_hours',
        label: 'Monitoring Timeout (hours)',
        description: 'Archive monitoring tokens after this timeout',
        category: 'lifecycle',
        type: 'number',
        min: 1,
        max: 48,
        step: 1,
        defaultValue: '12',
      },
    ],
  },
  {
    name: 'filtering',
    label: 'Data Filtering',
    description: 'Configure data quality filters',
    settings: [
      {
        key: 'min_pool_liquidity_usd',
        label: 'Min Pool Liquidity (USD)',
        description: 'Minimum pool liquidity for inclusion',
        category: 'filtering',
        type: 'number',
        min: 0,
        max: 10000,
        step: 100,
        defaultValue: '500',
      },
      {
        key: 'activation_min_liquidity_usd',
        label: 'Activation Min Liquidity (USD)',
        description: 'Minimum liquidity for token activation',
        category: 'filtering',
        type: 'number',
        min: 0,
        max: 10000,
        step: 100,
        defaultValue: '200',
      },
    ],
  },
  {
    name: 'notarb',
    label: 'NotArb Integration',
    description: 'Configure NotArb bot export settings',
    settings: [
      {
        key: 'notarb_min_score',
        label: 'NotArb Min Score',
        description: 'Minimum score threshold for NotArb bot export',
        category: 'notarb',
        type: 'number',
        min: 0,
        max: 1,
        step: 0.1,
        defaultValue: '0.5',
      },
      {
        key: 'notarb_max_spam_percentage',
        label: 'NotArb Max Spam %',
        description: 'Maximum spam percentage for NotArb bot export',
        category: 'notarb',
        type: 'number',
        min: 0,
        max: 100,
        step: 1,
        defaultValue: '50',
      },
      {
        key: 'spam_whitelist_wallets',
        label: 'Spam Whitelist Wallets',
        description: 'Comma-separated list of wallet addresses to ignore in spam detection',
        category: 'notarb',
        type: 'textarea',
        defaultValue: '8vNwSvT1S8P99c9XmjfXfV4DSGZLfUoNFx63zngCuh54',
      },
    ],
  },
  {
    name: 'monitoring',
    label: 'Backlog Monitoring',
    description: 'Configure backlog monitoring thresholds',
    settings: [
      {
        key: 'backlog_warning_threshold',
        label: 'Warning Threshold',
        description: 'Warning threshold for backlog size',
        category: 'monitoring',
        type: 'number',
        min: 10,
        max: 500,
        step: 5,
        defaultValue: '75',
      },
      {
        key: 'backlog_error_threshold',
        label: 'Error Threshold',
        description: 'Error threshold for backlog size',
        category: 'monitoring',
        type: 'number',
        min: 20,
        max: 500,
        step: 5,
        defaultValue: '100',
      },
      {
        key: 'backlog_critical_threshold',
        label: 'Critical Threshold',
        description: 'Critical threshold for backlog size',
        category: 'monitoring',
        type: 'number',
        min: 50,
        max: 500,
        step: 10,
        defaultValue: '150',
      },
    ],
  },
]
