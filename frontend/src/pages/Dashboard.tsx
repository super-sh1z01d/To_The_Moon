import { useState, useEffect, useMemo } from 'react'
import { useTokens } from '@/hooks/useTokens'
import { TokenTable } from '@/components/tokens/TokenTable'
import { TokenFilters } from '@/components/tokens/TokenFilters'
import { Pagination } from '@/components/ui/pagination'
import { TokenFilters as Filters } from '@/types/token'
import { Skeleton } from '@/components/ui/skeleton'
import { ErrorDisplay } from '@/components/ui/error-display'
import { useTokenStats } from '@/hooks/useTokenStats'
import { useLanguage } from '@/hooks/useLanguage'
import { usePageMetadata } from '@/hooks/usePageMetadata'

const STORAGE_KEY = 'dashboard_page_size'

export default function Dashboard() {
  // Load page size from localStorage
  const savedPageSize = localStorage.getItem(STORAGE_KEY)
  const initialPageSize = savedPageSize ? Number(savedPageSize) : 50
  const { t } = useLanguage()

  const dashboardMetadata = useMemo(() => {
    const origin = typeof window !== 'undefined' ? window.location.origin : 'https://tothemoon.sh1z01d.ru'
    return {
      en: {
        title: 'Dashboard | To The Moon',
        description: 'Monitor live Solana token scores, liquidity and pool activity inside the To The Moon dashboard.',
        keywords: ['solana dashboard', 'token scores', 'liquidity tracking', 'arbitrage monitoring'],
      },
      ru: {
        title: 'Дашборд | To The Moon',
        description: 'Следите за скором, ликвидностью и активностью пулов токенов Solana в рабочем интерфейсе To The Moon.',
        keywords: ['дашборд solana', 'скор токена', 'мониторинг ликвидности', 'арбитраж'],
      },
      canonical: `${origin}/app/`,
      siteName: 'To The Moon',
    }
  }, [])

  usePageMetadata(dashboardMetadata)

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
  const { data: statsData } = useTokenStats()

  const { data, isLoading, error, refetch } = useTokens(filters)

  const handlePageChange = (page: number) => {
    setFilters({ ...filters, page })
  }

  const handlePageSizeChange = (size: number) => {
    setFilters({ ...filters, limit: size, page: 1 })
  }

  if (error) {
    const message = error instanceof Error ? error.message : t('Unknown error')
    return (
      <ErrorDisplay
        title={t('Failed to load tokens')}
        message={message}
        onRetry={() => refetch()}
      />
    )
  }

  return (
    <div className="space-y-3">
      <TokenFilters 
        filters={filters} 
        onFilterChange={setFilters}
        statusCounts={
          statsData
            ? {
                active: statsData.active,
                monitoring: statsData.monitoring,
                archived: statsData.archived,
              }
            : undefined
        }
      />

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
