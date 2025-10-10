import { useState } from 'react'
import { useSettings, useSaveSettings } from '@/hooks/useSettings'
import { SettingsGroup } from '@/components/settings/SettingsGroup'
import { SettingField } from '@/components/settings/SettingField'
import { SettingsSearch } from '@/components/settings/SettingsSearch'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { toast } from 'sonner'

export default function Settings() {
  const [search, setSearch] = useState('')
  const { data: settings, isLoading } = useSettings()
  const { mutateAsync: saveSettings, isPending: isSaving } = useSaveSettings()
  const [localSettings, setLocalSettings] = useState<Record<string, string>>({})

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-96" />
      </div>
    )
  }

  const handleChange = (key: string, value: string) => {
    setLocalSettings(prev => ({ ...prev, [key]: value }))
  }

  const handleSave = async () => {
    try {
      await saveSettings(localSettings)
      toast.success('Settings saved successfully')
      setLocalSettings({})
    } catch (error) {
      toast.error('Failed to save settings')
    }
  }

  const getValue = (key: string, defaultValue: string = '') => {
    return localSettings[key] ?? settings?.[key] ?? defaultValue
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-muted-foreground">Configure system parameters</p>
      </div>

      <SettingsSearch value={search} onChange={setSearch} />

      <div className="space-y-6">
        {/* Scoring Model Selection */}
        <SettingsGroup 
          title="Scoring Model" 
          description="Select active scoring model and configure weights"
        >
          <SettingField
            label="Active Model"
            value={getValue('scoring_model_active', 'hybrid_momentum')}
            onChange={(v) => handleChange('scoring_model_active', v)}
            type="select"
            options={[
              { value: 'hybrid_momentum', label: 'Hybrid Momentum (Recommended)' },
              { value: 'legacy', label: 'Legacy Model' }
            ]}
            description="Choose scoring algorithm"
          />
          <SettingField
            label="TX Calculation Mode"
            value={getValue('tx_calculation_mode', 'acceleration')}
            onChange={(v) => handleChange('tx_calculation_mode', v)}
            type="select"
            options={[
              { value: 'acceleration', label: 'Acceleration (Default)' },
              { value: 'arbitrage_activity', label: 'Arbitrage Activity' }
            ]}
            description="Transaction component calculation method"
          />
        </SettingsGroup>

        {/* Hybrid Momentum Weights */}
        <SettingsGroup 
          title="Hybrid Momentum Weights" 
          description="Component weights for Hybrid Momentum model (must sum to 1.0)"
        >
          <SettingField
            label="Transaction Weight (w_tx)"
            value={getValue('w_tx', '0.25')}
            onChange={(v) => handleChange('w_tx', v)}
            type="number"
            step="0.01"
            description="Weight for transaction acceleration/activity component"
          />
          <SettingField
            label="Volume Weight (w_vol)"
            value={getValue('w_vol', '0.25')}
            onChange={(v) => handleChange('w_vol', v)}
            type="number"
            step="0.01"
            description="Weight for volume momentum component"
          />
          <SettingField
            label="Freshness Weight (w_fresh)"
            value={getValue('w_fresh', '0.25')}
            onChange={(v) => handleChange('w_fresh', v)}
            type="number"
            step="0.01"
            description="Weight for token freshness component"
          />
          <SettingField
            label="Order Flow Weight (w_oi)"
            value={getValue('w_oi', '0.25')}
            onChange={(v) => handleChange('w_oi', v)}
            type="number"
            step="0.01"
            description="Weight for order flow imbalance component"
          />
          <SettingField
            label="EWMA Alpha"
            value={getValue('ewma_alpha', '0.3')}
            onChange={(v) => handleChange('ewma_alpha', v)}
            type="number"
            step="0.01"
            description="Exponential smoothing factor (0-1)"
          />
          <SettingField
            label="Freshness Threshold"
            value={getValue('freshness_threshold_hours', '6.0')}
            onChange={(v) => handleChange('freshness_threshold_hours', v)}
            type="number"
            unit="hours"
            description="Age threshold for freshness calculation"
          />
        </SettingsGroup>

        {/* Legacy Model Weights */}
        <SettingsGroup 
          title="Legacy Model Weights" 
          description="Component weights for Legacy model (must sum to 1.0)"
        >
          <SettingField
            label="Spread Weight (weight_s)"
            value={getValue('weight_s', '0.35')}
            onChange={(v) => handleChange('weight_s', v)}
            type="number"
            step="0.01"
            description="Weight for spread component"
          />
          <SettingField
            label="Liquidity Weight (weight_l)"
            value={getValue('weight_l', '0.25')}
            onChange={(v) => handleChange('weight_l', v)}
            type="number"
            step="0.01"
            description="Weight for liquidity component"
          />
          <SettingField
            label="Momentum Weight (weight_m)"
            value={getValue('weight_m', '0.20')}
            onChange={(v) => handleChange('weight_m', v)}
            type="number"
            step="0.01"
            description="Weight for momentum component"
          />
          <SettingField
            label="Transaction Weight (weight_t)"
            value={getValue('weight_t', '0.20')}
            onChange={(v) => handleChange('weight_t', v)}
            type="number"
            step="0.01"
            description="Weight for transaction component"
          />
          <SettingField
            label="Score Smoothing Alpha"
            value={getValue('score_smoothing_alpha', '0.3')}
            onChange={(v) => handleChange('score_smoothing_alpha', v)}
            type="number"
            step="0.01"
            description="Smoothing factor for score changes"
          />
          <SettingField
            label="Max Price Change 5m"
            value={getValue('max_price_change_5m', '0.5')}
            onChange={(v) => handleChange('max_price_change_5m', v)}
            type="number"
            step="0.1"
            description="Maximum allowed 5-minute price change"
          />
        </SettingsGroup>

        {/* Token Lifecycle */}
        <SettingsGroup 
          title="Token Lifecycle" 
          description="Activation, archival, and monitoring parameters"
        >
          <SettingField
            label="Minimum Score"
            value={getValue('min_score', '0.1')}
            onChange={(v) => handleChange('min_score', v)}
            type="number"
            step="0.01"
            description="Minimum score threshold for active tokens"
          />
          <SettingField
            label="Minimum Score Change"
            value={getValue('min_score_change', '0.05')}
            onChange={(v) => handleChange('min_score_change', v)}
            type="number"
            step="0.01"
            description="Minimum score change to trigger update"
          />
          <SettingField
            label="Activation Liquidity"
            value={getValue('activation_min_liquidity_usd', '200')}
            onChange={(v) => handleChange('activation_min_liquidity_usd', v)}
            type="number"
            unit="USD"
            description="Minimum liquidity to activate monitoring token"
          />
          <SettingField
            label="Archive Below Hours"
            value={getValue('archive_below_hours', '12')}
            onChange={(v) => handleChange('archive_below_hours', v)}
            type="number"
            unit="hours"
            description="Archive active tokens below min_score after this time"
          />
          <SettingField
            label="Monitoring Timeout Hours"
            value={getValue('monitoring_timeout_hours', '12')}
            onChange={(v) => handleChange('monitoring_timeout_hours', v)}
            type="number"
            unit="hours"
            description="Archive monitoring tokens after this timeout"
          />
        </SettingsGroup>

        {/* Data Filtering - Active Tokens */}
        <SettingsGroup 
          title="Data Filtering - Active Tokens" 
          description="Strict filtering thresholds for active tokens"
        >
          <SettingField
            label="Minimum Pool Liquidity"
            value={getValue('min_pool_liquidity_usd', '500')}
            onChange={(v) => handleChange('min_pool_liquidity_usd', v)}
            type="number"
            unit="USD"
            description="Minimum liquidity per pool for active tokens"
          />
          <SettingField
            label="Min TX Threshold 5m"
            value={getValue('min_tx_threshold_5m', '0')}
            onChange={(v) => handleChange('min_tx_threshold_5m', v)}
            type="number"
            description="Minimum 5-minute transaction count"
          />
          <SettingField
            label="Min TX Threshold 1h"
            value={getValue('min_tx_threshold_1h', '0')}
            onChange={(v) => handleChange('min_tx_threshold_1h', v)}
            type="number"
            description="Minimum 1-hour transaction count"
          />
          <SettingField
            label="Min Volume Threshold 5m"
            value={getValue('min_volume_threshold_5m', '0')}
            onChange={(v) => handleChange('min_volume_threshold_5m', v)}
            type="number"
            unit="USD"
            description="Minimum 5-minute volume"
          />
          <SettingField
            label="Min Volume Threshold 1h"
            value={getValue('min_volume_threshold_1h', '0')}
            onChange={(v) => handleChange('min_volume_threshold_1h', v)}
            type="number"
            unit="USD"
            description="Minimum 1-hour volume"
          />
          <SettingField
            label="Min Order Flow Volume 5m"
            value={getValue('min_orderflow_volume_5m', '0')}
            onChange={(v) => handleChange('min_orderflow_volume_5m', v)}
            type="number"
            unit="USD"
            description="Minimum 5-minute order flow volume"
          />
        </SettingsGroup>

        {/* Data Filtering - Monitoring Tokens */}
        <SettingsGroup 
          title="Data Filtering - Monitoring Tokens" 
          description="Relaxed filtering for tokens in monitoring status"
        >
          <SettingField
            label="Arbitrage Min TX 5m"
            value={getValue('arbitrage_min_tx_5m', '100')}
            onChange={(v) => handleChange('arbitrage_min_tx_5m', v)}
            type="number"
            description="Minimum 5-minute transactions for arbitrage mode"
          />
          <SettingField
            label="Arbitrage Optimal TX 5m"
            value={getValue('arbitrage_optimal_tx_5m', '200')}
            onChange={(v) => handleChange('arbitrage_optimal_tx_5m', v)}
            type="number"
            description="Optimal 5-minute transactions for arbitrage mode"
          />
          <SettingField
            label="Arbitrage Acceleration Weight"
            value={getValue('arbitrage_acceleration_weight', '0.1')}
            onChange={(v) => handleChange('arbitrage_acceleration_weight', v)}
            type="number"
            step="0.01"
            description="Weight for acceleration in arbitrage mode"
          />
        </SettingsGroup>

        {/* Component Calculation Parameters */}
        <SettingsGroup 
          title="Component Calculation" 
          description="Advanced parameters for score component calculations"
        >
          <SettingField
            label="Liquidity Factor Threshold"
            value={getValue('liquidity_factor_threshold', '100000')}
            onChange={(v) => handleChange('liquidity_factor_threshold', v)}
            type="number"
            unit="USD"
            description="Liquidity threshold for sigmoid boost calculation"
          />
          <SettingField
            label="Order Flow Significance Threshold"
            value={getValue('orderflow_significance_threshold', '500')}
            onChange={(v) => handleChange('orderflow_significance_threshold', v)}
            type="number"
            unit="USD"
            description="Volume threshold for order flow significance"
          />
          <SettingField
            label="Manipulation Detection Ratio"
            value={getValue('manipulation_detection_ratio', '3.0')}
            onChange={(v) => handleChange('manipulation_detection_ratio', v)}
            type="number"
            step="0.1"
            description="Size ratio threshold for manipulation detection"
          />
        </SettingsGroup>

        {/* System Performance */}
        <SettingsGroup 
          title="System Performance" 
          description="Update intervals and processing parameters"
        >
          <SettingField
            label="Hot Interval"
            value={getValue('hot_interval_sec', '10')}
            onChange={(v) => handleChange('hot_interval_sec', v)}
            type="number"
            unit="seconds"
            description="Update interval for hot (high-activity) tokens"
          />
          <SettingField
            label="Cold Interval"
            value={getValue('cold_interval_sec', '45')}
            onChange={(v) => handleChange('cold_interval_sec', v)}
            type="number"
            unit="seconds"
            description="Update interval for cold (low-activity) tokens"
          />
        </SettingsGroup>

        {/* Data Quality Validation */}
        <SettingsGroup 
          title="Data Quality Validation" 
          description="Configure data quality checks and warnings"
        >
          <SettingField
            label="Strict Data Validation"
            value={getValue('strict_data_validation', 'false')}
            onChange={(v) => handleChange('strict_data_validation', v)}
            type="select"
            options={[
              { value: 'true', label: 'Enabled' },
              { value: 'false', label: 'Disabled' }
            ]}
            description="Enable strict validation mode"
          />
          <SettingField
            label="Min Liquidity for Warnings"
            value={getValue('min_liquidity_for_warnings', '10000')}
            onChange={(v) => handleChange('min_liquidity_for_warnings', v)}
            type="number"
            unit="USD"
            description="Minimum liquidity to trigger zero-transaction warnings"
          />
          <SettingField
            label="Min Transactions for Warnings"
            value={getValue('min_transactions_for_warnings', '200')}
            onChange={(v) => handleChange('min_transactions_for_warnings', v)}
            type="number"
            description="Minimum transactions to trigger zero-price-change warnings"
          />
          <SettingField
            label="Max Stale Minutes"
            value={getValue('max_stale_minutes', '10')}
            onChange={(v) => handleChange('max_stale_minutes', v)}
            type="number"
            unit="minutes"
            description="Maximum age of data before considered stale"
          />
        </SettingsGroup>

        {/* NotArb Integration */}
        <SettingsGroup 
          title="NotArb Integration" 
          description="Configure NotArb bot export parameters"
        >
          <SettingField
            label="NotArb Min Score"
            value={getValue('notarb_min_score', '0.5')}
            onChange={(v) => handleChange('notarb_min_score', v)}
            type="number"
            step="0.01"
            description="Minimum score for NotArb config export"
          />
          <SettingField
            label="Max Spam Percentage"
            value={getValue('notarb_max_spam_percentage', '50')}
            onChange={(v) => handleChange('notarb_max_spam_percentage', v)}
            type="number"
            unit="%"
            description="Maximum spam percentage for NotArb export"
          />
        </SettingsGroup>
      </div>

      <div className="flex gap-4 pt-4 border-t">
        <Button 
          onClick={handleSave} 
          disabled={Object.keys(localSettings).length === 0 || isSaving}
        >
          {isSaving ? 'Saving...' : 'Save Changes'}
        </Button>
        <Button 
          variant="outline" 
          onClick={() => setLocalSettings({})}
          disabled={Object.keys(localSettings).length === 0 || isSaving}
        >
          Reset
        </Button>
      </div>
    </div>
  )
}
