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
  { value: 'all', label: 'All Tokens' },
  { value: 'active', label: 'Active' },
  { value: 'monitoring', label: 'Monitoring' },
  { value: 'archived', label: 'Archived' },
] as const

export function TokenFilters({ filters, onFilterChange }: TokenFiltersProps) {
  const [search, setSearch] = useState(filters.search || '')
  const debouncedSearch = useDebounce(search, 300)

  useEffect(() => {
    onFilterChange({ ...filters, search: debouncedSearch })
  }, [debouncedSearch])

  const handleStatusChange = (status: string) => {
    onFilterChange({ ...filters, status: status === 'all' ? undefined : status })
  }

  return (
    <div className="space-y-4">
      {/* Status Filter Buttons */}
      <div className="flex flex-wrap gap-2">
        {STATUS_OPTIONS.map((option) => (
          <Button
            key={option.value}
            variant={
              (option.value === 'all' && !filters.status) ||
              filters.status === option.value
                ? 'default'
                : 'outline'
            }
            size="sm"
            onClick={() => handleStatusChange(option.value)}
          >
            {option.label}
          </Button>
        ))}
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
