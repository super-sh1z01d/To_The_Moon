import { Button } from '@/components/ui/button'
import { TokenFilters as Filters } from '@/types/token'
import { useLanguage } from '@/hooks/useLanguage'
import { useState } from 'react'
import { Copy, Check } from 'lucide-react'
import { toast } from 'sonner'

interface TokenFiltersProps {
  filters: Filters
  onFilterChange: (filters: Filters) => void
  statusCounts?: {
    active: number
    monitoring: number
    archived: number
  }
}

const STATUS_OPTIONS = [
  { value: 'active', labelKey: 'Active', color: 'bg-green-500 hover:bg-green-600' },
  { value: 'monitoring', labelKey: 'Monitoring', color: 'bg-yellow-500 hover:bg-yellow-600' },
  { value: 'archived', labelKey: 'Archived', color: 'bg-gray-500 hover:bg-gray-600' },
] as const

const WALLET_ADDRESS = 'DpStbQPHnZwHGw1nfxmnWai4e5unpBrUrhjsAkxL5zTq'

export function TokenFilters({ filters, onFilterChange, statusCounts }: TokenFiltersProps) {
  const { t } = useLanguage()
  const [copied, setCopied] = useState(false)

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(WALLET_ADDRESS)
      setCopied(true)
      toast.success(t('Wallet address copied!'))
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      toast.error(t('Failed to copy'))
    }
  }

  const handleStatusChange = (status: string) => {
    onFilterChange({ ...filters, status: status === 'all' ? undefined : status })
  }

  const getCount = (status: string) => {
    if (!statusCounts) return null
    return statusCounts[status as keyof typeof statusCounts] || 0
  }

  return (
    <div className="space-y-4">
      {/* Status Filter Buttons */}
      <div className="flex flex-wrap gap-2">
        {STATUS_OPTIONS.map((option) => {
          const isActive = filters.status === option.value
          const count = getCount(option.value)

          return (
            <Button
              key={option.value}
              variant={isActive ? 'default' : 'outline'}
              size="sm"
              onClick={() => handleStatusChange(option.value)}
              className={isActive ? option.color : ''}
            >
              {t(option.labelKey)}
              {count !== null && <span className="ml-1.5 opacity-75">({count})</span>}
            </Button>
          )
        })}
      </div>

      {/* System Description */}
      <div className="rounded-md border bg-muted/40 px-4 py-3 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold">{t('How It Works')}</h3>
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
        </div>

        <ul className="text-sm space-y-1.5 list-disc list-inside text-muted-foreground">
          <li>{t('New Pump.Fun tokens that migrated to Pump.Fun AMM pool automatically appear in the system with Monitoring status')}</li>
          <li>{t('When minimum liquidity on external DEXs is reached, token transitions to Active status and starts receiving score')}</li>
          <li>{t('Score (0-3) shows current token activity based on transactions, trading volume, data freshness and buy/sell balance')}</li>
          <li>{t('Tokens with low score (<0.3) for more than 5 hours are automatically archived')}</li>
        </ul>

        <p className="text-xs text-muted-foreground italic border-l-2 border-yellow-500 pl-3 py-1">
          {t('Higher score indicates more active trading right now and arbitrage opportunities, but does not guarantee profitability. Always do your own research!')}
        </p>

        {/* Donation Section */}
        <div className="pt-3 border-t space-y-2">
          <h4 className="text-sm font-semibold">{t('Support the Project')}</h4>
          <p className="text-xs text-muted-foreground">
            {t('The service is free and under active development. If you find it useful, we would appreciate your support:')}
          </p>

          <div className="flex items-center gap-2 bg-background border rounded-md px-3 py-2">
            <code className="flex-1 text-xs font-mono break-all">{WALLET_ADDRESS}</code>
            <button
              onClick={copyToClipboard}
              className="flex-shrink-0 p-1.5 hover:bg-muted rounded transition-colors"
              title={t('Copy')}
            >
              {copied ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
