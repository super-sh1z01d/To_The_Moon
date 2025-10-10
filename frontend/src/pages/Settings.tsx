import { useState } from 'react'
import { useSettings, useSaveSettings } from '@/hooks/useSettings'
import { SettingsGroup } from '@/components/settings/SettingsGroup'
import { SettingField } from '@/components/settings/SettingField'
import { SettingsSearch } from '@/components/settings/SettingsSearch'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { toast } from 'sonner'
import { useLanguage } from '@/hooks/useLanguage'

export default function Settings() {
  const [search, setSearch] = useState('')
  const { data: settings, isLoading } = useSettings()
  const { mutateAsync: saveSettings, isPending: isSaving } = useSaveSettings()
  const [localSettings, setLocalSettings] = useState<Record<string, string>>({})
  const { t } = useLanguage()

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
      toast.success(t('Settings saved successfully'))
      setLocalSettings({})
    } catch (error) {
      toast.error(t('Failed to save settings'))
    }
  }

  const getValue = (key: string, defaultValue: string = '') => {
    return localSettings[key] ?? settings?.[key] ?? defaultValue
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">{t('Settings')}</h1>
        <p className="text-muted-foreground">{t('Configure system parameters')}</p>
      </div>

      <SettingsSearch
        value={search}
        onChange={setSearch}
        placeholder={t('Search settings...')}
      />

      <div className="space-y-6">
        {/* Scoring Model Selection */}
        <SettingsGroup 
          title={t('Scoring Model')} 
          description={t('Select active scoring model and configure weights')}
        >
          <SettingField
            label={t('Active Model')}
            value={getValue('scoring_model_active', 'hybrid_momentum')}
            onChange={(v) => handleChange('scoring_model_active', v)}
            type="select"
            options={[
              { value: 'hybrid_momentum', label: t('Hybrid Momentum (Recommended)') },
              { value: 'legacy', label: t('Legacy Model') }
            ]}
            description={t('Choose scoring algorithm')}
          />
          <SettingField
            label={t('TX Calculation Mode')}
            value={getValue('tx_calculation_mode', 'acceleration')}
            onChange={(v) => handleChange('tx_calculation_mode', v)}
            type="select"
            options={[
              { value: 'acceleration', label: t('Acceleration (Default)') },
              { value: 'arbitrage_activity', label: t('Arbitrage Activity') }
            ]}
            description={t('Transaction component calculation method')}
          />
        </SettingsGroup>

        {/* Hybrid Momentum Weights */}
        <SettingsGroup 
          title={t('Hybrid Momentum Weights')} 
          description={t('Component weights for Hybrid Momentum model (must sum to 1.0)')}
        >
          <SettingField
            label={t('Transaction Weight (w_tx)')}
            value={getValue('w_tx', '0.25')}
            onChange={(v) => handleChange('w_tx', v)}
            type="number"
            step="0.01"
            description={t('Weight for transaction acceleration/activity component')}
          />
          <SettingField
            label={t('Volume Weight (w_vol)')}
            value={getValue('w_vol', '0.25')}
            onChange={(v) => handleChange('w_vol', v)}
            type="number"
            step="0.01"
            description={t('Weight for volume momentum component')}
          />
          <SettingField
            label={t('Freshness Weight (w_fresh)')}
            value={getValue('w_fresh', '0.25')}
            onChange={(v) => handleChange('w_fresh', v)}
            type="number"
            step="0.01"
            description={t('Weight for token freshness component')}
          />
          <SettingField
            label={t('Order Flow Weight (w_oi)')}
            value={getValue('w_oi', '0.25')}
            onChange={(v) => handleChange('w_oi', v)}
            type="number"
            step="0.01"
            description={t('Weight for order flow imbalance component')}
          />
          <SettingField
            label={t('EWMA Alpha')}
            value={getValue('ewma_alpha', '0.3')}
            onChange={(v) => handleChange('ewma_alpha', v)}
            type="number"
            step="0.01"
            description={t('Exponential smoothing factor (0-1)')}
          />
          <SettingField
            label={t('Freshness Threshold')}
            value={getValue('freshness_threshold_hours', '6.0')}
            onChange={(v) => handleChange('freshness_threshold_hours', v)}
            type="number"
            unit={t('hours')}
            description={t('Age threshold for freshness calculation')}
          />
        </SettingsGroup>

        {/* Legacy Model Weights */}
        <SettingsGroup 
          title={t('Legacy Model Weights')} 
          description={t('Component weights for Legacy model (must sum to 1.0)')}
        >
          <SettingField
            label={t('Spread Weight (weight_s)')}
            value={getValue('weight_s', '0.35')}
            onChange={(v) => handleChange('weight_s', v)}
            type="number"
            step="0.01"
            description={t('Weight for spread component')}
          />
          <SettingField
            label={t('Liquidity Weight (weight_l)')}
            value={getValue('weight_l', '0.25')}
            onChange={(v) => handleChange('weight_l', v)}
            type="number"
            step="0.01"
            description={t('Weight for liquidity component')}
          />
          <SettingField
            label={t('Momentum Weight (weight_m)')}
            value={getValue('weight_m', '0.20')}
            onChange={(v) => handleChange('weight_m', v)}
            type="number"
            step="0.01"
            description={t('Weight for momentum component')}
          />
          <SettingField
            label={t('Transaction Weight (weight_t)')}
            value={getValue('weight_t', '0.20')}
            onChange={(v) => handleChange('weight_t', v)}
            type="number"
            step="0.01"
            description={t('Weight for transaction component')}
          />
          <SettingField
            label={t('Score Smoothing Alpha')}
            value={getValue('score_smoothing_alpha', '0.3')}
            onChange={(v) => handleChange('score_smoothing_alpha', v)}
            type="number"
            step="0.01"
            description={t('Smoothing factor for score changes')}
          />
          <SettingField
            label={t('Max Price Change 5m')}
            value={getValue('max_price_change_5m', '0.5')}
            onChange={(v) => handleChange('max_price_change_5m', v)}
            type="number"
            step="0.1"
            description={t('Maximum allowed 5-minute price change')}
          />
        </SettingsGroup>

        {/* Token Lifecycle */}
        <SettingsGroup 
          title={t('Token Lifecycle')} 
          description={t('Activation, archival, and monitoring parameters')}
        >
          <SettingField
            label={t('Minimum Score')}
            value={getValue('min_score', '0.1')}
            onChange={(v) => handleChange('min_score', v)}
            type="number"
            step="0.01"
            description={t('Minimum score threshold for active tokens')}
          />
          <SettingField
            label={t('Minimum Score Change')}
            value={getValue('min_score_change', '0.05')}
            onChange={(v) => handleChange('min_score_change', v)}
            type="number"
            step="0.01"
            description={t('Minimum score change to trigger update')}
          />
          <SettingField
            label={t('Activation Liquidity')}
            value={getValue('activation_min_liquidity_usd', '200')}
            onChange={(v) => handleChange('activation_min_liquidity_usd', v)}
            type="number"
            unit="USD"
            description={t('Minimum liquidity to activate monitoring token')}
          />
          <SettingField
            label={t('Archive Below Hours')}
            value={getValue('archive_below_hours', '12')}
            onChange={(v) => handleChange('archive_below_hours', v)}
            type="number"
            unit={t('hours')}
            description={t('Archive active tokens below min_score after this time')}
          />
          <SettingField
            label={t('Monitoring Timeout Hours')}
            value={getValue('monitoring_timeout_hours', '12')}
            onChange={(v) => handleChange('monitoring_timeout_hours', v)}
            type="number"
            unit={t('hours')}
            description={t('Archive monitoring tokens after this timeout')}
          />
        </SettingsGroup>

        {/* Data Filtering - Active Tokens */}
        <SettingsGroup 
          title={t('Data Filtering - Active Tokens')} 
          description={t('Strict filtering thresholds for active tokens')}
        >
          <SettingField
            label={t('Minimum Pool Liquidity')}
            value={getValue('min_pool_liquidity_usd', '500')}
            onChange={(v) => handleChange('min_pool_liquidity_usd', v)}
            type="number"
            unit="USD"
            description={t('Minimum liquidity per pool for active tokens')}
          />
          <SettingField
            label={t('Min TX Threshold 5m')}
            value={getValue('min_tx_threshold_5m', '0')}
            onChange={(v) => handleChange('min_tx_threshold_5m', v)}
            type="number"
            description={t('Minimum 5-minute transaction count')}
          />
          <SettingField
            label={t('Min TX Threshold 1h')}
            value={getValue('min_tx_threshold_1h', '0')}
            onChange={(v) => handleChange('min_tx_threshold_1h', v)}
            type="number"
            description={t('Minimum 1-hour transaction count')}
          />
          <SettingField
            label={t('Min Volume Threshold 5m')}
            value={getValue('min_volume_threshold_5m', '0')}
            onChange={(v) => handleChange('min_volume_threshold_5m', v)}
            type="number"
            unit="USD"
            description={t('Minimum 5-minute volume')}
          />
          <SettingField
            label={t('Min Volume Threshold 1h')}
            value={getValue('min_volume_threshold_1h', '0')}
            onChange={(v) => handleChange('min_volume_threshold_1h', v)}
            type="number"
            unit="USD"
            description={t('Minimum 1-hour volume')}
          />
          <SettingField
            label={t('Min Order Flow Volume 5m')}
            value={getValue('min_orderflow_volume_5m', '0')}
            onChange={(v) => handleChange('min_orderflow_volume_5m', v)}
            type="number"
            unit="USD"
            description={t('Minimum 5-minute order flow volume')}
          />
        </SettingsGroup>

        {/* Data Filtering - Monitoring Tokens */}
        <SettingsGroup 
          title={t('Data Filtering - Monitoring Tokens')} 
          description={t('Relaxed filtering for tokens in monitoring status')}
        >
          <SettingField
            label={t('Arbitrage Min TX 5m')}
            value={getValue('arbitrage_min_tx_5m', '100')}
            onChange={(v) => handleChange('arbitrage_min_tx_5m', v)}
            type="number"
            description={t('Minimum 5-minute transactions for arbitrage mode')}
          />
          <SettingField
            label={t('Arbitrage Optimal TX 5m')}
            value={getValue('arbitrage_optimal_tx_5m', '200')}
            onChange={(v) => handleChange('arbitrage_optimal_tx_5m', v)}
            type="number"
            description={t('Optimal 5-minute transactions for arbitrage mode')}
          />
          <SettingField
            label={t('Arbitrage Acceleration Weight')}
            value={getValue('arbitrage_acceleration_weight', '0.1')}
            onChange={(v) => handleChange('arbitrage_acceleration_weight', v)}
            type="number"
            step="0.01"
            description={t('Weight for acceleration in arbitrage mode')}
          />
        </SettingsGroup>

        {/* Component Calculation Parameters */}
        <SettingsGroup 
          title={t('Component Calculation')} 
          description={t('Advanced parameters for score component calculations')}
        >
          <SettingField
            label={t('Liquidity Factor Threshold')}
            value={getValue('liquidity_factor_threshold', '100000')}
            onChange={(v) => handleChange('liquidity_factor_threshold', v)}
            type="number"
            unit="USD"
            description={t('Liquidity threshold for sigmoid boost calculation')}
          />
          <SettingField
            label={t('Order Flow Significance Threshold')}
            value={getValue('orderflow_significance_threshold', '500')}
            onChange={(v) => handleChange('orderflow_significance_threshold', v)}
            type="number"
            unit="USD"
            description={t('Volume threshold for order flow significance')}
          />
          <SettingField
            label={t('Manipulation Detection Ratio')}
            value={getValue('manipulation_detection_ratio', '3.0')}
            onChange={(v) => handleChange('manipulation_detection_ratio', v)}
            type="number"
            step="0.1"
            description={t('Size ratio threshold for manipulation detection')}
          />
        </SettingsGroup>

        {/* System Performance */}
        <SettingsGroup 
          title={t('System Performance')} 
          description={t('Update intervals and processing parameters')}
        >
          <SettingField
            label={t('Hot Interval')}
            value={getValue('hot_interval_sec', '10')}
            onChange={(v) => handleChange('hot_interval_sec', v)}
            type="number"
            unit={t('seconds')}
            description={t('Update interval for hot (high-activity) tokens')}
          />
          <SettingField
            label={t('Cold Interval')}
            value={getValue('cold_interval_sec', '45')}
            onChange={(v) => handleChange('cold_interval_sec', v)}
            type="number"
            unit={t('seconds')}
            description={t('Update interval for cold (low-activity) tokens')}
          />
        </SettingsGroup>

        {/* Data Quality Validation */}
        <SettingsGroup 
          title={t('Data Quality Validation')} 
          description={t('Configure data quality checks and warnings')}
        >
          <SettingField
            label={t('Strict Data Validation')}
            value={getValue('strict_data_validation', 'false')}
            onChange={(v) => handleChange('strict_data_validation', v)}
            type="select"
            options={[
              { value: 'true', label: t('Enabled') },
              { value: 'false', label: t('Disabled') }
            ]}
            description={t('Enable strict validation mode')}
          />
          <SettingField
            label={t('Min Liquidity for Warnings')}
            value={getValue('min_liquidity_for_warnings', '10000')}
            onChange={(v) => handleChange('min_liquidity_for_warnings', v)}
            type="number"
            unit="USD"
            description={t('Minimum liquidity to trigger zero-transaction warnings')}
          />
          <SettingField
            label={t('Min Transactions for Warnings')}
            value={getValue('min_transactions_for_warnings', '200')}
            onChange={(v) => handleChange('min_transactions_for_warnings', v)}
            type="number"
            description={t('Minimum transactions to trigger zero-price-change warnings')}
          />
          <SettingField
            label={t('Max Stale Minutes')}
            value={getValue('max_stale_minutes', '10')}
            onChange={(v) => handleChange('max_stale_minutes', v)}
            type="number"
            unit={t('minutes')}
            description={t('Maximum age of data before considered stale')}
          />
        </SettingsGroup>

        {/* NotArb Integration */}
        <SettingsGroup 
          title={t('NotArb Integration')} 
          description={t('Configure NotArb bot export parameters')}
        >
          <SettingField
            label={t('NotArb Min Score')}
            value={getValue('notarb_min_score', '0.5')}
            onChange={(v) => handleChange('notarb_min_score', v)}
            type="number"
            step="0.01"
            description={t('Minimum score for NotArb config export')}
          />
          <SettingField
            label={t('Max Spam Percentage')}
            value={getValue('notarb_max_spam_percentage', '50')}
            onChange={(v) => handleChange('notarb_max_spam_percentage', v)}
            type="number"
            unit="%"
            description={t('Maximum spam percentage for NotArb export')}
          />
        </SettingsGroup>
      </div>

      <div className="flex gap-4 pt-4 border-t">
        <Button 
          onClick={handleSave} 
          disabled={Object.keys(localSettings).length === 0 || isSaving}
        >
          {isSaving ? t('Saving...') : t('Save changes')}
        </Button>
        <Button 
          variant="outline" 
          onClick={() => setLocalSettings({})}
          disabled={Object.keys(localSettings).length === 0 || isSaving}
        >
          {t('Reset')}
        </Button>
      </div>
    </div>
  )
}
