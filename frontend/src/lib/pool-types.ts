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
    badgeClass: 'border-blue-500',
  },
  raydium_cpmm: {
    label: 'Raydium CPMM',
    family: 'Raydium',
    badgeClass: 'border-blue-500',
  },
  raydium_clmm: {
    label: 'Raydium CLMM',
    family: 'Raydium',
    badgeClass: 'border-indigo-500',
  },
  meteora_dlmm: {
    label: 'Meteora DLMM',
    family: 'Meteora',
    badgeClass: 'border-emerald-500',
  },
  meteora_damm_v2: {
    label: 'Meteora DAMM v2',
    family: 'Meteora',
    badgeClass: 'border-emerald-500',
  },
  pumpfun_amm: {
    label: 'Pump.fun AMM',
    family: 'Pump.fun',
    badgeClass: 'border-pink-500',
  },
  orca_whirlpool: {
    label: 'Orca Whirlpool',
    family: 'Orca',
    badgeClass: 'border-purple-500',
  },
  goosefx_gamma: {
    label: 'GooseFX Gamma',
    family: 'GooseFX',
    badgeClass: 'border-orange-500',
  },
}

export function getPoolTypeMeta(poolType?: string | null): PoolTypeMeta {
  if (!poolType) {
    return DEFAULT_POOL_TYPE_META
  }
  return POOL_TYPE_META[poolType] ?? DEFAULT_POOL_TYPE_META
}
