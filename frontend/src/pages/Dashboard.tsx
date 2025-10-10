import { useState, useEffect } from 'react'
import { useTokens } from '@/hooks/useTokens'
import { TokenTable } from '@/components/tokens/TokenTable'
import { TokenFilters } from '@/components/tokens/TokenFilters'
import { Pagination } from '@/components/ui/pagination'
import { TokenFilters as Filters } from '@/types/token'
import { Skeleton } from '@/components/ui/skeleton'
import { ErrorDisplay } from '@/components/ui/error-display'

const STORAGE_KEY = 'dashboard_page_size'

export default function Dashboard() {
  // Load page size from localStorage
  const savedPageSize = localStorage.getItem(STORAGE_KEY)
  const initialPageSize = savedPageSize ? Number(savedPageSize) : 50

  const [filters, setFilters] = useState<Filters>({
    status: 'active',
    limit: initialPageSize,
    page: 1,
  })

  // Save page size to localStorage when it changes
  useEffect(() => {
    if (filters.limit) {
      localStorage.setItem(STORAGE_KEY, filters.limit.toString())
    }
  }, [filters.limit])

  const { data, isLoading, error, refetch } = useTokens(filters)

  const handlePageChange = (page: number) => {
    setFilters({ ...filters, page })
  }

  const handlePageSizeChange = (size: number) => {
    setFilters({ ...filters, limit: size, page: 1 })
  }

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
    <div className="space-y-3">
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
        <Pagination
          currentPage={filters.page || 1}
          totalItems={data.total}
          pageSize={filters.limit || 50}
          onPageChange={handlePageChange}
          onPageSizeChange={handlePageSizeChange}
        />
      )}
    </div>
  )
}
