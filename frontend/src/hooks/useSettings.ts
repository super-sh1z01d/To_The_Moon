import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Setting, SettingsMap } from '@/types/settings'
import { API_BASE_URL, REFRESH_INTERVALS } from '@/lib/constants'

async function fetchAllSettings(): Promise<SettingsMap> {
  const response = await fetch(`${API_BASE_URL}/settings`)
  
  if (!response.ok) {
    throw new Error(`Failed to fetch settings: ${response.statusText}`)
  }
  
  const settings: Setting[] = await response.json()
  
  // Convert array to map
  return settings.reduce((acc, setting) => {
    acc[setting.key] = setting.value
    return acc
  }, {} as SettingsMap)
}

async function fetchSetting(key: string): Promise<Setting> {
  const response = await fetch(`${API_BASE_URL}/settings/${key}`)
  
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
    staleTime: 30000,
    refetchInterval: REFRESH_INTERVALS.SETTINGS,
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
