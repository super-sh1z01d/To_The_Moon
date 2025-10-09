import { useParams, useNavigate } from 'react-router-dom'
import { useMemo } from 'react'
import { useTokenDetail } from '@/hooks/useTokenDetail'
import { TokenMetrics } from '@/components/tokens/TokenMetrics'
import { PriceChart } from '@/components/charts/PriceChart'
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
        <Skeleton className="h-10 w-32" />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
        </div>
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
          <p className="text-sm text-muted-foreground">Token Details</p>
        </div>
      </div>

      <TokenMetrics token={token} />

      {/* Generate mock price history data for demonstration */}
      {useMemo(() => {
        const now = Date.now()
        const mockData = Array.from({ length: 20 }, (_, i) => ({
          timestamp: new Date(now - (19 - i) * 5 * 60 * 1000).toISOString(),
          delta_5m: token.delta_p_5m + (Math.random() - 0.5) * 10,
          delta_15m: token.delta_p_15m + (Math.random() - 0.5) * 15,
        }))
        return <PriceChart data={mockData} />
      }, [token.delta_p_5m, token.delta_p_15m])}

      {/* Placeholder for additional charts */}
      <div className="text-center py-8 text-muted-foreground text-sm">
        <p>Additional charts (liquidity, volume, score breakdown) coming soon...</p>
      </div>
    </div>
  )
}
