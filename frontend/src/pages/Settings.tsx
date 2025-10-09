import { useState } from 'react'
import { useSettings } from '@/hooks/useSettings'
import { SettingsGroup } from '@/components/settings/SettingsGroup'
import { SettingField } from '@/components/settings/SettingField'
import { SettingsSearch } from '@/components/settings/SettingsSearch'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { toast } from 'sonner'

export default function Settings() {
  const [search, setSearch] = useState('')
  const { data: settings, isLoading, updateSetting, saveSettings } = useSettings()
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
        {/* Scoring Model */}
        <SettingsGroup 
          title="Scoring Model" 
          description="Configure token scoring weights and parameters"
        >
          <SettingField
            label="TX Weight"
            value={getValue('w_tx', '0.6')}
            onChange={(v) => handleChange('w_tx', v)}
            type="number"
            description="Weight for transaction acceleration component"
          />
          <SettingField
            label="Freshness Weight"
            value={getValue('w_fresh', '0.4')}
            onChange={(v) => handleChange('w_fresh', v)}
            type="number"
            description="Weight for token freshness component"
          />
        </SettingsGroup>

        {/* Token Lifecycle */}
        <SettingsGroup 
          title="Token Lifecycle" 
          description="Activation and archival parameters"
        >
          <SettingField
            label="Minimum Score"
            value={getValue('min_score', '0.15')}
            onChange={(v) => handleChange('min_score', v)}
            type="number"
            description="Minimum score threshold for active tokens"
          />
          <SettingField
            label="Activation Liquidity"
            value={getValue('activation_min_liquidity_usd', '200')}
            onChange={(v) => handleChange('activation_min_liquidity_usd', v)}
            type="number"
            unit="USD"
            description="Minimum liquidity to activate token"
          />
        </SettingsGroup>

        {/* System Performance */}
        <SettingsGroup 
          title="System Performance" 
          description="Update intervals and thresholds"
        >
          <SettingField
            label="Hot Interval"
            value={getValue('hot_interval_sec', '10')}
            onChange={(v) => handleChange('hot_interval_sec', v)}
            type="number"
            unit="seconds"
            description="Update interval for hot tokens"
          />
          <SettingField
            label="Cold Interval"
            value={getValue('cold_interval_sec', '45')}
            onChange={(v) => handleChange('cold_interval_sec', v)}
            type="number"
            unit="seconds"
            description="Update interval for cold tokens"
          />
        </SettingsGroup>
      </div>

      <div className="flex gap-4 pt-4 border-t">
        <Button onClick={handleSave} disabled={Object.keys(localSettings).length === 0}>
          Save Changes
        </Button>
        <Button 
          variant="outline" 
          onClick={() => setLocalSettings({})}
          disabled={Object.keys(localSettings).length === 0}
        >
          Reset
        </Button>
      </div>
    </div>
  )
}
