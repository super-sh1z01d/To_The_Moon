import { Button } from '@/components/ui/button'
import { TokenFilters as Filters } from '@/types/token'
import { useLanguage } from '@/hooks/useLanguage'
import { useSettings } from '@/hooks/useSettings'
import { useMemo } from 'react'

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

export function TokenFilters({ filters, onFilterChange, statusCounts }: TokenFiltersProps) {
  const { t, language } = useLanguage()
  const { data: settings } = useSettings()

  const scoreFormula = useMemo(() => {
    const getWeight = (key: string, fallback: number) => {
      const raw = settings?.[key]
      const parsed = raw !== undefined ? Number.parseFloat(raw) : Number.NaN
      return Number.isFinite(parsed) ? parsed : fallback
    }

    const wTx = getWeight('w_tx', 0.25)
    const wVol = getWeight('w_vol', 0.25)
    const wFresh = getWeight('w_fresh', 0.25)
    const wOi = getWeight('w_oi', 0.25)

    const parts =
      language === 'ru'
        ? [
            `${wTx.toFixed(2)}·Транзакции`,
            `${wVol.toFixed(2)}·Объём`,
            `${wFresh.toFixed(2)}·Свежесть`,
            `${wOi.toFixed(2)}·Дисбаланс ордеров`,
          ]
        : [
            `${wTx.toFixed(2)}·TX`,
            `${wVol.toFixed(2)}·Volume`,
            `${wFresh.toFixed(2)}·Freshness`,
            `${wOi.toFixed(2)}·Orderflow`,
          ]

    return `Score = ${parts.join(' + ')}`
  }, [language, settings])

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

      <div className="rounded-md border bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
        {scoreFormula}
      </div>
    </div>
  )
}
