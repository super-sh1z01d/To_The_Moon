import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { TokenFilters as Filters } from '@/types/token'
import { useDebounce } from '@/hooks/useDebounce'
import { useEffect, useState } from 'react'

interface TokenFiltersProps {
  filters: Filters
  onFilterChange: (filters: Filters) => void
}

const STATUS_OPTIONS = [
  { value: 'active', label: 'Активные', color: 'bg-green-500 hover:bg-green-600' },
  { value: 'monitoring', label: 'Мониторинг', color: 'bg-yellow-500 hover:bg-yellow-600' },
  { value: 'archived', label: 'Архивные', color: 'bg-gray-500 hover:bg-gray-600' },
] as const

export function TokenFilters({ filters, onFilterChange }: TokenFiltersProps) {
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

  return (
    <div className="space-y-4">
      {/* Status Filter Buttons */}
      <div className="flex flex-wrap gap-2">
        {STATUS_OPTIONS.map((option) => {
          const isActive = filters.status === option.value

          return (
            <Button
              key={option.value}
              variant={isActive ? 'default' : 'outline'}
              size="sm"
              onClick={() => handleStatusChange(option.value)}
              className={isActive ? option.color : ''}
            >
              {option.label}
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
