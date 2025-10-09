import { useQuery } from '@tanstack/react-query'
import type { Token } from '@/types/token'

async function fetchToken(mint: string): Promise<Token> {
  const response = await fetch(`/tokens/${mint}`)
  if (!response.ok) {
    throw new Error('Failed to fetch token')
  }
  return response.json()
}

export function useTokenDetail(mint: string) {
  return useQuery({
    queryKey: ['token', mint],
    queryFn: () => fetchToken(mint),
    refetchInterval: 5000, // Refresh every 5 seconds
    enabled: !!mint,
  })
}
