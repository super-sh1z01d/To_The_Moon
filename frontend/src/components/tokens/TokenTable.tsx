import { useNavigate } from 'react-router-dom'
import type { Pool, Token } from '@/types/token'
import { formatCurrency, formatRelativeTime, getScoreColor } from '@/lib/utils'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { ArrowUpDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { SCORE_DISPLAY_DECIMALS } from '@/lib/constants'
import { useLanguage } from '@/hooks/useLanguage'
import { TokenAvatar } from '@/components/tokens/TokenAvatar'
import { getTokenIdentity } from '@/lib/token-format'
import { getPoolTypeMeta } from '@/lib/pool-types'

interface TokenTableProps {
  tokens: Token[]
  isLoading?: boolean
  onSort?: (column: string) => void
  sortColumn?: string
  sortDirection?: 'asc' | 'desc'
}

const FRESHNESS_THRESHOLD_HOURS = 6

// Format age in compact format (minutes/hours)
function formatAge(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / (1000 * 60))
  
  if (diffMins < 60) {
    return `${diffMins}m`
  }
  
  const diffHours = Math.floor(diffMins / 60)
  return `${diffHours}h`
}

// Check if token is fresh (within threshold)
function isFresh(dateString: string): boolean {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffHours = diffMs / (1000 * 60 * 60)
  return diffHours <= FRESHNESS_THRESHOLD_HOURS
}

type PoolGroup = {
  key: string
  label: string
  count: number
  badgeClass: string
}

function normalizeKey(value: string | undefined | null): string | null {
  if (typeof value !== 'string') {
    return null
  }
  const trimmed = value.trim()
  return trimmed ? trimmed : null
}

function formatFallbackLabel(key: string): string {
  if (!key || key === 'unknown') {
    return 'Unknown pool'
  }
  return key
    .replace(/[_-]/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

function getPoolTypeGroups(pools: Pool[] | undefined): PoolGroup[] {
  if (!Array.isArray(pools) || pools.length === 0) {
    return []
  }

  const counts = new Map<string, { count: number; poolType: string | null }>()

  pools.forEach((pool) => {
    if (!pool) {
      return
    }
    const poolType = normalizeKey(pool.pool_type)
    const fallbackDex = normalizeKey(pool.dex) ?? 'unknown'
    const key = poolType ?? fallbackDex
    const increment = typeof pool.count === 'number' && Number.isFinite(pool.count) ? pool.count : 1
    const bucket = counts.get(key)
    if (bucket) {
      bucket.count += increment
      if (!bucket.poolType && poolType) {
        bucket.poolType = poolType
      }
    } else {
      counts.set(key, { count: increment, poolType })
    }
  })

  return Array.from(counts.entries())
    .map(([key, { count, poolType }]) => {
      const meta = getPoolTypeMeta(poolType)
      const label = poolType ? meta.label : formatFallbackLabel(key)
      return {
        key,
        count,
        label,
        badgeClass: meta.badgeClass,
      }
    })
    .sort((a, b) => {
      if (b.count === a.count) {
        return a.label.localeCompare(b.label)
      }
      return b.count - a.count
    })
}

export function TokenTable({ 
  tokens, 
  isLoading,
  onSort,
  sortColumn,
  sortDirection 
}: TokenTableProps) {
  const navigate = useNavigate()
  const { t } = useLanguage()

  const handleRowClick = (mint: string) => {
    navigate(`/token/${mint}`)
  }

  const handleSort = (column: string) => {
    if (onSort) {
      onSort(column)
    }
  }

  if (isLoading) {
    return <div className="text-center py-8 text-muted-foreground">{t('Loading tokens...')}</div>
  }

  if (tokens.length === 0) {
    return <div className="text-center py-8 text-muted-foreground">{t('No tokens found')}</div>
  }

  return (
    <div className="border rounded-lg overflow-hidden">
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[180px]">
                <Button variant="ghost" size="sm" onClick={() => handleSort('symbol')} className="h-8 px-2">
                  {t('Token')}
                  <ArrowUpDown className="ml-2 h-4 w-4" />
                </Button>
              </TableHead>
              <TableHead className="w-[100px] text-right">
                <Button variant="ghost" size="sm" onClick={() => handleSort('score')} className="h-8 px-2">
                  {t('Score')}
                  <ArrowUpDown className="ml-2 h-4 w-4" />
                </Button>
              </TableHead>
              <TableHead className="w-[100px]">{t('Status')}</TableHead>
              <TableHead className="w-[80px] text-right">
                <Button variant="ghost" size="sm" onClick={() => handleSort('created_at')} className="h-8 px-2">
                  {t('Age')}
                  <ArrowUpDown className="ml-2 h-4 w-4" />
                </Button>
              </TableHead>
              <TableHead className="w-[120px] text-right">{t('Liquidity')}</TableHead>
              <TableHead className="w-[80px] text-right">{t('5m TX Count')}</TableHead>
              <TableHead className="w-[120px]">{t('Dex Pools')}</TableHead>
              <TableHead className="w-[140px]">{t('Last Update')}</TableHead>
              <TableHead className="w-[80px]">{t('Solscan')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tokens.map((token) => {
              const score = typeof token.score === 'number' ? token.score : null
              const liquidityUsd = typeof token.liquidity_usd === 'number' ? token.liquidity_usd : null
              const tokenAgeSource = token.created_at || token.fetched_at
              const tokenAge = tokenAgeSource ? formatAge(tokenAgeSource) : '—'
              const tokenIsFresh = tokenAgeSource ? isFresh(tokenAgeSource) : false
              const poolGroups = getPoolTypeGroups(token.pools)
              const lastUpdatedRaw = formatRelativeTime(token.last_processed_at || token.fetched_at)
              const lastUpdated =
                lastUpdatedRaw === 'Unknown'
                  ? t('Unknown')
                  : lastUpdatedRaw === 'Invalid date'
                  ? t('Invalid date')
                  : lastUpdatedRaw
              
              const { label, fallback, shortMint } = getTokenIdentity(
                token.symbol,
                token.name,
                token.mint_address
              )

              return (
                <TableRow
                  key={token.mint_address}
                  className="cursor-pointer hover:bg-muted/50"
                  onClick={() => handleRowClick(token.mint_address)}
                >
                  <TableCell className="font-medium">
                    <div className="flex items-start gap-3">
                      <TokenAvatar
                        imageUrl={token.image_url}
                        fallback={fallback}
                        alt={`${label} logo`}
                      />
                      <div>
                        <div className="font-semibold whitespace-pre-line">{label}</div>
                        <div className="text-xs text-muted-foreground">
                          {shortMint}
                        </div>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <span className={`font-semibold ${getScoreColor(score)}`}>
                      {score !== null ? score.toFixed(SCORE_DISPLAY_DECIMALS) : '—'}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Badge 
                      variant="outline" 
                      className={`text-xs ${
                        token.status === 'active' 
                          ? 'border-green-500 text-green-600 dark:text-green-400' 
                          : token.status === 'monitoring'
                          ? 'border-yellow-500 text-yellow-600 dark:text-yellow-400'
                          : 'border-gray-500 text-gray-600 dark:text-gray-400'
                      }`}
                    >
                      {token.status === 'active' ? t('Active') : token.status === 'monitoring' ? t('Monitoring') : t('Archived')}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <span className={`text-sm font-medium ${tokenIsFresh ? 'text-green-600 dark:text-green-400' : 'text-muted-foreground'}`}>
                      {tokenAge}
                    </span>
                  </TableCell>
                  <TableCell className="text-right">{formatCurrency(liquidityUsd)}</TableCell>
                  <TableCell className="text-right">{token.n_5m || 0}</TableCell>
                  <TableCell>
                    {poolGroups.length === 0 ? (
                      <span className="text-xs text-muted-foreground">{t('No data available')}</span>
                    ) : (
                      <div className="flex flex-col gap-1">
                        {poolGroups.map((group) => (
                          <Badge
                            key={group.key}
                            variant="outline"
                            className={`text-xs w-fit ${group.badgeClass}`}
                          >
                            {group.label} <span className="ml-1 opacity-75">({group.count})</span>
                          </Badge>
                        ))}
                      </div>
                    )}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {lastUpdated}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        window.open(`https://solscan.io/token/${token.mint_address}`, '_blank')
                      }}
                    >
                      {t('View details')}
                    </Button>
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
