import { useQuery } from '@tanstack/react-query'
import { Token } from '@/types/token'
import { API_BASE_URL, REFRESH_INTERVALS } from '@/lib/constants'

async function fetchTokenDetail(mintAddress: string): Promise<Token> {
  const response = await fetch(`${API_BASE_URL}/tokens/${mintAddress}`)
  
  if (!response.ok) {
    throw new Error(`Failed to fetch token detail: ${response.statusText}`)
  }
  
  return response.json()
}

export function useTokenDetail(mintAddress: string) {
  return useQuery({
    queryKey: ['token', mintAddress],
    queryFn: () => fetchTokenDetail(mintAddress),
    staleTime: 3000,
    refetchInterval: REFRESH_INTERVALS.TOKEN_DETAIL,
    enabled: !!mintAddress,
  })
}
