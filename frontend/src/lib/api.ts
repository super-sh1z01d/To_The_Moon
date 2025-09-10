export type TokenItem = {
  mint_address: string
  name?: string
  symbol?: string
  score?: number
  liquidity_usd?: number
  delta_p_5m?: number
  delta_p_15m?: number
  n_5m?: number
  primary_dex?: string
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

export async function getTokens(minScore: number, limit=50, offset=0, sort:'score_desc'|'score_asc'='score_desc', statuses: string[] = ['active','monitoring']): Promise<TokensResponse> {
  const statusesParam = statuses.length ? `&statuses=${encodeURIComponent(statuses.join(','))}` : ''
  const r = await fetch(`/tokens?min_score=${encodeURIComponent(minScore)}&limit=${limit}&offset=${offset}&sort=${sort}${statusesParam}`)
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

// Logs
export type LogEntry = {
  ts: string
  level: string
  logger: string
  msg: string
  [k: string]: any
}

export type LogsMeta = { loggers: string[] }

export async function getLogs(params: {limit?: number, levels?: string[], loggers?: string[], contains?: string, since?: string} = {}): Promise<LogEntry[]> {
  const q = new URLSearchParams()
  if(params.limit!=null) q.set('limit', String(params.limit))
  if(params.levels && params.levels.length) q.set('levels', params.levels.join(','))
  if(params.loggers && params.loggers.length) q.set('loggers', params.loggers.join(','))
  if(params.contains) q.set('contains', params.contains)
  if(params.since) q.set('since', params.since)
  const r = await fetch(`/logs/?${q.toString()}`)
  if(!r.ok) throw new Error('logs fetch failed')
  return r.json()
}

export async function getLogsMeta(): Promise<LogsMeta> {
  const r = await fetch('/logs/meta')
  if(!r.ok) throw new Error('logs meta fetch failed')
  return r.json()
}
