import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { TokenFilters as Filters } from '@/types/token'
import { useDebounce } from '@/hooks/useDebounce'
import { useEffect, useState } from 'react'

interface TokenFiltersProps {
  filters: Filters
  onFilterChange: (filters: Filters) => void
}

export function TokenFilters({ filters, onFilterChange }: TokenFiltersProps) {
  const [search, setSearch] = useState(filters.search || '')
  const debouncedSearch = useDebounce(search, 300)

  useEffect(() => {
    onFilterChange({ ...filters, search: debouncedSearch })
  }, [debouncedSearch])

  return (
    <div className="flex flex-wrap gap-4 mb-4">
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
