import { useQuery } from '@tanstack/react-query'
import { Token, TokensResponse, TokenFilters } from '@/types/token'
import { API_BASE_URL, REFRESH_INTERVALS } from '@/lib/constants'

async function fetchTokens(filters: TokenFilters = {}): Promise<TokensResponse> {
  const params = new URLSearchParams()
  
  if (filters.status) params.append('status', filters.status)
  if (filters.minScore !== undefined) params.append('min_score', filters.minScore.toString())
  if (filters.search) params.append('search', filters.search)
  if (filters.limit) params.append('limit', filters.limit.toString())
  if (filters.sort) params.append('sort', filters.sort)
  
  // Convert page to offset
  if (filters.page && filters.limit) {
    const offset = (filters.page - 1) * filters.limit
    params.append('offset', offset.toString())
  }
  
  const url = `${API_BASE_URL}/tokens${params.toString() ? `?${params}` : ''}`
  const response = await fetch(url)
  
  if (!response.ok) {
    throw new Error(`Failed to fetch tokens: ${response.statusText}`)
  }
  
  return response.json()
}

export function useTokens(filters: TokenFilters = {}) {
  return useQuery({
    queryKey: ['tokens', filters],
    queryFn: () => fetchTokens(filters),
    staleTime: 5000,
    refetchInterval: REFRESH_INTERVALS.DASHBOARD,
  })
}
