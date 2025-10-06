import { SpamMetrics } from '../lib/api'

interface SpamCellProps {
  spamMetrics?: SpamMetrics
  compact?: boolean
}

export default function SpamCell({ spamMetrics, compact = false }: SpamCellProps) {
  if (!spamMetrics) {
    return <span className="muted">—</span>
  }

  const { spam_percentage, risk_level, total_instructions, compute_budget_count } = spamMetrics

  // Determine color and icon based on risk level
  const getRiskStyle = (level: string) => {
    switch (level) {
      case 'clean':
        return { color: '#22c55e', icon: '🟢' } // Green
      case 'low':
        return { color: '#eab308', icon: '🟡' } // Yellow
      case 'medium':
        return { color: '#f97316', icon: '🟠' } // Orange
      case 'high':
        return { color: '#ef4444', icon: '🔴' } // Red
      default:
        return { color: '#6b7280', icon: '⚪' } // Gray
    }
  }

  const riskStyle = getRiskStyle(risk_level)

  if (compact) {
    return (
      <span 
        style={{ color: riskStyle.color, fontWeight: '500' }}
        title={`Спам: ${spam_percentage.toFixed(1)}% (${risk_level})\nComputeBudget: ${compute_budget_count}/${total_instructions} инструкций`}
      >
        {riskStyle.icon} {spam_percentage.toFixed(1)}%
      </span>
    )
  }

  return (
    <div style={{ fontSize: '0.9em' }}>
      <div 
        style={{ 
          color: riskStyle.color, 
          fontWeight: '600',
          display: 'flex',
          alignItems: 'center',
          gap: '4px'
        }}
      >
        <span>{riskStyle.icon}</span>
        <span>{spam_percentage.toFixed(1)}%</span>
      </div>
      <div 
        className="muted" 
        style={{ fontSize: '0.8em', marginTop: '2px' }}
        title={`ComputeBudget инструкций: ${compute_budget_count} из ${total_instructions}`}
      >
        CB: {compute_budget_count}/{total_instructions}
      </div>
    </div>
  )
}