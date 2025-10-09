import { useParams, useNavigate } from 'react-router-dom'
import { useTokenDetail } from '@/hooks/useTokenDetail'
import { TokenMetrics } from '@/components/tokens/TokenMetrics'
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

      {/* Placeholder for charts - will be added in next tasks */}
      <div className="text-center py-12 text-muted-foreground">
        <p>Charts and additional metrics coming soon...</p>
      </div>
    </div>
  )
}
