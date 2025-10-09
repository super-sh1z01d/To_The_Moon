import { useQuery } from '@tanstack/react-query'
import { API_BASE_URL, REFRESH_INTERVALS } from '@/lib/constants'

export interface TokenStats {
  total: number
  active: number
  monitoring: number
  archived: number
}

async function fetchTokenStats(): Promise<TokenStats> {
  const response = await fetch(`/tokens/stats`)
  
  if (!response.ok) {
    throw new Error(`Failed to fetch token stats: ${response.statusText}`)
  }
  
  return response.json()
}

export function useTokenStats() {
  return useQuery({
    queryKey: ['token-stats'],
    queryFn: fetchTokenStats,
    staleTime: 5000,
    refetchInterval: REFRESH_INTERVALS.DASHBOARD,
  })
}
