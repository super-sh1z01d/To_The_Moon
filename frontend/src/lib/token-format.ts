const normalize = (value?: string | null): string => {
  if (typeof value !== 'string') return ''
  return value.trim()
}

const areEqualIgnoreCase = (a: string, b: string): boolean => {
  return a.localeCompare(b, undefined, { sensitivity: 'accent', usage: 'search' }) === 0
}

export function getTokenIdentity(
  symbol?: string | null,
  name?: string | null,
  mint?: string
) {
  const symbolNormalized = normalize(symbol)
  const nameNormalized = normalize(name)
  const shortMint =
    typeof mint === 'string' && mint.length > 8
      ? `${mint.slice(0, 4)}…${mint.slice(-4)}`
      : mint ?? ''

  let label = ''
  if (symbolNormalized && nameNormalized) {
    label = areEqualIgnoreCase(symbolNormalized, nameNormalized)
      ? symbolNormalized
      : `${symbolNormalized} ${nameNormalized}`
  } else {
    label = symbolNormalized || nameNormalized || shortMint || ''
  }

  const fallback = symbolNormalized || nameNormalized || mint || label

  return {
    label: label || fallback || '',
    fallback: fallback || '',
    shortMint: shortMint || (mint ?? ''),
  }
}
