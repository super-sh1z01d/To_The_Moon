export type TokenItem = {
  mint_address: string
  name?: string
  symbol?: string
  score?: number
  liquidity_usd?: number
  delta_p_5m?: number
  delta_p_15m?: number
  n_5m?: number
  solscan_url: string
}

export type TokensResponse = {
  total: number
  items: TokenItem[]
}

export type SettingsMap = Record<string, string>

export type PoolItem = {
  address?: string
  dex?: string
  quote?: string
  solscan_url?: string
}

export async function getTokens(minScore: number, limit=50, offset=0, sort:'score_desc'|'score_asc'='score_desc'): Promise<TokensResponse> {
  const r = await fetch(`/tokens?min_score=${encodeURIComponent(minScore)}&limit=${limit}&offset=${offset}&sort=${sort}`)
  if(!r.ok) throw new Error('tokens fetch failed')
  return r.json()
}

export async function getPools(mint: string): Promise<PoolItem[]> {
  const r = await fetch(`/tokens/${mint}/pools`)
  if(!r.ok) throw new Error('pools fetch failed')
  return r.json()
}

export async function getSettings(): Promise<SettingsMap>{
  const r = await fetch('/settings/')
  if(!r.ok) throw new Error('settings fetch failed')
  return r.json()
}

export async function putSetting(key: string, value: string): Promise<void>{
  const r = await fetch(`/settings/${encodeURIComponent(key)}`, {method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify({value})})
  if(!r.ok) throw new Error('settings update failed')
}

export async function recalc(): Promise<void>{
  await fetch('/admin/recalculate', {method:'POST'})
}
