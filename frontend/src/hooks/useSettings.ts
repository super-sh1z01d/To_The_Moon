import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Setting, SettingsMap } from '@/types/settings'
import { API_BASE_URL, REFRESH_INTERVALS } from '@/lib/constants'

function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem('authToken')
  return token ? { 'Authorization': `Bearer ${token}` } : {}
}

async function fetchAllSettings(): Promise<SettingsMap> {
  const response = await fetch(`${API_BASE_URL}/settings/`, {
    headers: getAuthHeaders()
  })

  if (!response.ok) {
    throw new Error(`Failed to fetch settings: ${response.statusText}`)
  }

  // API returns object directly, not array
  const settings: SettingsMap = await response.json()
  return settings
}

async function fetchSetting(key: string): Promise<Setting> {
  const response = await fetch(`${API_BASE_URL}/settings/${key}`, {
    headers: getAuthHeaders()
  })

  if (!response.ok) {
    throw new Error(`Failed to fetch setting: ${response.statusText}`)
  }

  return response.json()
}

async function updateSetting(key: string, value: string): Promise<Setting> {
  const response = await fetch(`${API_BASE_URL}/settings/${key}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ value }),
  })

  if (!response.ok) {
    throw new Error(`Failed to update setting: ${response.statusText}`)
  }

  return response.json()
}

export function useSettings() {
  return useQuery({
    queryKey: ['settings'],
    queryFn: fetchAllSettings,
    staleTime: Infinity, // Не перезагружать автоматически
    refetchInterval: false, // Отключить автоматическую перезагрузку
    refetchOnWindowFocus: false, // Не перезагружать при фокусе окна
  })
}

export function useSetting(key: string) {
  return useQuery({
    queryKey: ['setting', key],
    queryFn: () => fetchSetting(key),
    staleTime: 30000,
    enabled: !!key,
  })
}

export function useUpdateSetting() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      updateSetting(key, value),
    onSuccess: (data, variables) => {
      // Invalidate both the specific setting and all settings
      queryClient.invalidateQueries({ queryKey: ['setting', variables.key] })
      queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
  })
}

export function useSaveSettings() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (settings: Record<string, string>) => {
      // Update all settings in parallel
      const promises = Object.entries(settings).map(([key, value]) =>
        updateSetting(key, value)
      )
      return Promise.all(promises)
    },
    onSuccess: () => {
      // Invalidate all settings queries
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      queryClient.invalidateQueries({ queryKey: ['setting'] })
    },
  })
}
