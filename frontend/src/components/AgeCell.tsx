import { formatAge, isTokenFresh } from '../lib/scoring-utils'

interface AgeCellProps {
  createdAt?: string
  freshnessThreshold?: number
}

export default function AgeCell({ createdAt, freshnessThreshold = 6 }: AgeCellProps) {
  if (!createdAt) return <span className="muted">—</span>

  const age = formatAge(createdAt)
  const isFresh = isTokenFresh(createdAt, freshnessThreshold)

  return (
    <div className="age-container">
      <span className={`age-value ${isFresh ? 'age-fresh' : 'age-normal'}`}>
        {age}
      </span>
      {isFresh && (
        <span className="freshness-indicator" title={`Fresh token (< ${freshnessThreshold}h old)`}>
          🆕
        </span>
      )}
    </div>
  )
}