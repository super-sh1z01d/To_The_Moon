import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { TokenFilters as Filters } from '@/types/token'
import { useDebounce } from '@/hooks/useDebounce'
import { useEffect, useState } from 'react'

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
  { value: 'active', label: 'Active', color: 'bg-green-500 hover:bg-green-600' },
  { value: 'monitoring', label: 'Monitoring', color: 'bg-yellow-500 hover:bg-yellow-600' },
  { value: 'archived', label: 'Archived', color: 'bg-gray-500 hover:bg-gray-600' },
] as const

export function TokenFilters({ filters, onFilterChange, statusCounts }: TokenFiltersProps) {
  const [search, setSearch] = useState(filters.search || '')
  const debouncedSearch = useDebounce(search, 300)

  useEffect(() => {
    if (debouncedSearch !== filters.search) {
      onFilterChange({ ...filters, search: debouncedSearch })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch])

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
              {option.label}
              {count !== null && <span className="ml-1.5 opacity-75">({count})</span>}
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
