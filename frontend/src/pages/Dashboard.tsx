import { useState } from 'react'
import { useTokens } from '@/hooks/useTokens'
import { TokenTable } from '@/components/tokens/TokenTable'
import { TokenFilters } from '@/components/tokens/TokenFilters'
import { TokenFilters as Filters } from '@/types/token'
import { Skeleton } from '@/components/ui/skeleton'
import { ErrorDisplay } from '@/components/ui/error-display'

export default function Dashboard() {
  const [filters, setFilters] = useState<Filters>({
    status: 'active',
    limit: 50,
  })

  const { data, isLoading, error, refetch } = useTokens(filters)

  if (error) {
    return (
      <ErrorDisplay
        title="Failed to load tokens"
        message={error instanceof Error ? error.message : 'Unknown error'}
        onRetry={() => refetch()}
      />
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Token Dashboard</h2>
        <p className="text-muted-foreground">
          Monitor and analyze Solana tokens
        </p>
      </div>

      <TokenFilters filters={filters} onFilterChange={setFilters} />

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      ) : (
        <TokenTable tokens={data?.items || []} />
      )}

      {data && (
        <div className="text-sm text-muted-foreground">
          Showing {data.items.length} of {data.total} tokens
        </div>
      )}
    </div>
  )
}
