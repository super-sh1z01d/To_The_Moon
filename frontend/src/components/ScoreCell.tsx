import { ComponentBreakdown } from '../lib/api'
import { getScoreColor, getScoreClass, formatComponent } from '../lib/scoring-utils'

interface ScoreCellProps {
  score?: number
  components?: ComponentBreakdown
  model?: string
}

export default function ScoreCell({ score, components, model }: ScoreCellProps) {
  if (score == null) return <span>—</span>

  const showBreakdown = model === 'hybrid_momentum' && components

  return (
    <div className="score-container" title={showBreakdown ? getBreakdownTooltip(components!) : undefined}>
      <div className="score-bar">
        <div 
          className="score-fill" 
          style={{
            width: `${Math.min(score * 100, 100)}%`, 
            backgroundColor: getScoreColor(score)
          }}
        />
      </div>
      <span className={`score-value ${getScoreClass(score)}`}>
        {score.toFixed(4)}
      </span>
      {showBreakdown && (
        <div className="component-breakdown-hover">
          <div className="breakdown-content">
            <div className="breakdown-item">
              <span className="breakdown-label">TX Acceleration:</span>
              <span className="breakdown-value">{formatComponent(components!.tx_accel)}</span>
            </div>
            <div className="breakdown-item">
              <span className="breakdown-label">Volume Momentum:</span>
              <span className="breakdown-value">{formatComponent(components!.vol_momentum)}</span>
            </div>
            <div className="breakdown-item">
              <span className="breakdown-label">Token Freshness:</span>
              <span className="breakdown-value">{formatComponent(components!.token_freshness)}</span>
            </div>
            <div className="breakdown-item">
              <span className="breakdown-label">Orderflow Imbalance:</span>
              <span className="breakdown-value">{formatComponent(components!.orderflow_imbalance)}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function getBreakdownTooltip(components: ComponentBreakdown): string {
  return `TX Acceleration: ${formatComponent(components.tx_accel)}
Volume Momentum: ${formatComponent(components.vol_momentum)}
Token Freshness: ${formatComponent(components.token_freshness)}
Orderflow Imbalance: ${formatComponent(components.orderflow_imbalance)}`
}