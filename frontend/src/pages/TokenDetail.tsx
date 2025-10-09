import { useParams, useNavigate } from 'react-router-dom'
import { useMemo } from 'react'
import { useTokenDetail } from '@/hooks/useTokenDetail'
import { TokenMetrics } from '@/components/tokens/TokenMetrics'
import { SpamMetrics } from '@/components/tokens/SpamMetrics'
import { PriceChart } from '@/components/charts/PriceChart'
import { LiquidityChart } from '@/components/charts/LiquidityChart'
import { VolumeChart } from '@/components/charts/VolumeChart'
import { ScoreBreakdown } from '@/components/charts/ScoreBreakdown'
import { Skeleton } from '@/components/ui/skeleton'
import { ErrorDisplay } from '@/components/ui/error-display'
import { Button } from '@/components/ui/button'
import { ArrowLeft } from 'lucide-react'

export default function TokenDetail() {
  const { mint } = useParams<{ mint: string }>()
  const navigate = useNavigate()
  const { data: token, isLoading, error, refetch } = useTokenDetail(mint!)

  if (isLoading) {
    return (
      <div className="space-y-4">
        {/* Header Skeleton */}
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10" />
          <div className="space-y-2">
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-32" />
          </div>
        </div>

        {/* Metrics Cards Skeleton */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
        </div>

        {/* Charts Skeleton */}
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-80" />
          <Skeleton className="h-80" />
          <Skeleton className="h-80" />
          <Skeleton className="h-80" />
        </div>

        {/* Spam Metrics Skeleton */}
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (error || !token) {
    return (
      <ErrorDisplay
        title="Failed to load token"
        message={error instanceof Error ? error.message : 'Token not found'}
        onRetry={() => refetch()}
      />
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate('/')}
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold">{token.symbol || 'Unknown Token'}</h1>
            <p className="text-sm text-muted-foreground">
              Token Details • Auto-refreshing every 5s
            </p>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
        >
          Refresh Now
        </Button>
      </div>

      <TokenMetrics token={token} />

      {/* Charts Section */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Price Chart */}
        {useMemo(() => {
          const now = Date.now()
          const mockData = Array.from({ length: 20 }, (_, i) => ({
            timestamp: new Date(now - (19 - i) * 5 * 60 * 1000).toISOString(),
            delta_5m: token.delta_p_5m + (Math.random() - 0.5) * 10,
            delta_15m: token.delta_p_15m + (Math.random() - 0.5) * 15,
          }))
          return <PriceChart data={mockData} />
        }, [token.delta_p_5m, token.delta_p_15m])}

        {/* Liquidity Chart */}
        {useMemo(() => {
          const now = Date.now()
          const baseLiquidity = token.liquidity_usd
          const mockData = Array.from({ length: 20 }, (_, i) => ({
            timestamp: new Date(now - (19 - i) * 5 * 60 * 1000).toISOString(),
            liquidity: baseLiquidity * (1 + (Math.random() - 0.5) * 0.2),
          }))
          return <LiquidityChart data={mockData} />
        }, [token.liquidity_usd])}

        {/* Volume Chart */}
        {useMemo(() => {
          const now = Date.now()
          const baseVolume = token.n_5m
          const mockData = Array.from({ length: 20 }, (_, i) => ({
            timestamp: new Date(now - (19 - i) * 5 * 60 * 1000).toISOString(),
            transactions: Math.max(0, Math.floor(baseVolume * (0.5 + Math.random()))),
          }))
          return <VolumeChart data={mockData} />
        }, [token.n_5m])}

        {/* Score Breakdown */}
        <ScoreBreakdown totalScore={token.score} />
      </div>

      {/* Spam Metrics Section */}
      <SpamMetrics 
        spamPercentage={Math.random() * 100}
        riskLevel={token.score > 0.5 ? 'low' : token.score > 0.2 ? 'medium' : 'high'}
        details={{
          suspiciousTransactions: Math.floor(token.n_5m * 0.1),
          totalTransactions: token.n_5m,
          flaggedAddresses: Math.floor(Math.random() * 5),
          patterns: ['High frequency', 'Wash trading'].filter(() => Math.random() > 0.5)
        }}
      />
    </div>
  )
}
