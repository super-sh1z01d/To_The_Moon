import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { TokenFilters as Filters } from '@/types/token'
import { useDebounce } from '@/hooks/useDebounce'
import { useTokenStats } from '@/hooks/useTokenStats'
import { useEffect, useState } from 'react'

interface TokenFiltersProps {
  filters: Filters
  onFilterChange: (filters: Filters) => void
}

const STATUS_OPTIONS = [
  { value: 'all', label: 'All Tokens', key: 'total' },
  { value: 'active', label: 'Active', key: 'active' },
  { value: 'monitoring', label: 'Monitoring', key: 'monitoring' },
  { value: 'archived', label: 'Archived', key: 'archived' },
] as const

export function TokenFilters({ filters, onFilterChange }: TokenFiltersProps) {
  const [search, setSearch] = useState(filters.search || '')
  const debouncedSearch = useDebounce(search, 300)
  const { data: stats } = useTokenStats()

  useEffect(() => {
    onFilterChange({ ...filters, search: debouncedSearch })
  }, [debouncedSearch])

  const handleStatusChange = (status: string) => {
    onFilterChange({ ...filters, status: status === 'all' ? undefined : status })
  }

  const getCount = (key: string): number => {
    if (!stats) return 0
    return stats[key as keyof typeof stats] || 0
  }

  return (
    <div className="space-y-4">
      {/* Status Filter Buttons */}
      <div className="flex flex-wrap gap-2">
        {STATUS_OPTIONS.map((option) => {
          const isActive =
            (option.value === 'all' && !filters.status) ||
            filters.status === option.value
          const count = getCount(option.key)

          return (
            <Button
              key={option.value}
              variant={isActive ? 'default' : 'outline'}
              size="sm"
              onClick={() => handleStatusChange(option.value)}
              className="gap-2"
            >
              {option.label}
              <Badge
                variant={isActive ? 'secondary' : 'outline'}
                className="ml-1"
              >
                {count}
              </Badge>
            </Button>
          )
        })}
      </div>

      {/* Search Input */}
      <div className="flex-1 min-w-[200px]">
        <Label htmlFor="search">Search</Label>
        <Input
          id="search"
          placeholder="Search by symbol or address..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
    </div>
  )
}
