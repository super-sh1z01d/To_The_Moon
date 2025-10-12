export type PoolTypeMeta = {
  label: string
  family: string
  badgeClass: string
}

export const DEFAULT_POOL_TYPE_META: PoolTypeMeta = {
  label: 'Unknown pool',
  family: 'Unknown',
  badgeClass: 'border-muted text-muted-foreground',
}

// Mapping of normalized pool_type -> UI metadata
export const POOL_TYPE_META: Record<string, PoolTypeMeta> = {
  raydium_amm: {
    label: 'Raydium AMM',
    family: 'Raydium',
    badgeClass: 'border-blue-500 text-blue-600 dark:text-blue-300',
  },
  raydium_cpmm: {
    label: 'Raydium CPMM',
    family: 'Raydium',
    badgeClass: 'border-blue-500 text-blue-600 dark:text-blue-300',
  },
  raydium_clmm: {
    label: 'Raydium CLMM',
    family: 'Raydium',
    badgeClass: 'border-indigo-500 text-indigo-600 dark:text-indigo-300',
  },
  meteora_dlmm: {
    label: 'Meteora DLMM',
    family: 'Meteora',
    badgeClass: 'border-emerald-500 text-emerald-600 dark:text-emerald-300',
  },
  meteora_damm_v2: {
    label: 'Meteora DAMM v2',
    family: 'Meteora',
    badgeClass: 'border-emerald-500 text-emerald-600 dark:text-emerald-300',
  },
  pumpfun_amm: {
    label: 'Pump.fun AMM',
    family: 'Pump.fun',
    badgeClass: 'border-pink-500 text-pink-600 dark:text-pink-300',
  },
  orca_whirlpool: {
    label: 'Orca Whirlpool',
    family: 'Orca',
    badgeClass: 'border-purple-500 text-purple-600 dark:text-purple-300',
  },
  goosefx_gamma: {
    label: 'GooseFX Gamma',
    family: 'GooseFX',
    badgeClass: 'border-orange-500 text-orange-600 dark:text-orange-300',
  },
}

export function getPoolTypeMeta(poolType?: string | null): PoolTypeMeta {
  if (!poolType) {
    return DEFAULT_POOL_TYPE_META
  }
  return POOL_TYPE_META[poolType] ?? DEFAULT_POOL_TYPE_META
}
