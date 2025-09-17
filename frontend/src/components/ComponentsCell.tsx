import { ComponentBreakdown } from '../lib/api'
import { formatComponent, getComponentColor } from '../lib/scoring-utils'

interface ComponentsCellProps {
  components?: ComponentBreakdown
  compact?: boolean
}

export default function ComponentsCell({ components, compact = false }: ComponentsCellProps) {
  if (!components) return <span className="muted">—</span>

  if (compact) {
    return (
      <div className="components-compact">
        <span className="component-item" title="Transaction Acceleration">
          TX:{formatComponent(components.tx_accel)}
        </span>
        <span className="component-item" title="Volume Momentum">
          Vol:{formatComponent(components.vol_momentum)}
        </span>
        <span className="component-item" title="Token Freshness">
          Fresh:{formatComponent(components.token_freshness)}
        </span>
        <span className="component-item" title="Orderflow Imbalance">
          OI:{formatComponent(components.orderflow_imbalance)}
        </span>
      </div>
    )
  }

  return (
    <div className="components-detailed">
      <div className="component-row" title="Transaction Acceleration - measures transaction velocity changes">
        <span className="component-label">TX:</span>
        <div className="component-bar">
          <div 
            className="component-fill"
            style={{
              width: `${components.tx_accel * 100}%`,
              backgroundColor: getComponentColor(components.tx_accel)
            }}
          />
        </div>
        <span className="component-value">{formatComponent(components.tx_accel)}</span>
      </div>
      
      <div className="component-row" title="Volume Momentum - tracks volume trend acceleration">
        <span className="component-label">Vol:</span>
        <div className="component-bar">
          <div 
            className="component-fill"
            style={{
              width: `${components.vol_momentum * 100}%`,
              backgroundColor: getComponentColor(components.vol_momentum)
            }}
          />
        </div>
        <span className="component-value">{formatComponent(components.vol_momentum)}</span>
      </div>
      
      <div className="component-row" title="Token Freshness - rewards recently created tokens">
        <span className="component-label">Fresh:</span>
        <div className="component-bar">
          <div 
            className="component-fill"
            style={{
              width: `${components.token_freshness * 100}%`,
              backgroundColor: getComponentColor(components.token_freshness)
            }}
          />
        </div>
        <span className="component-value">{formatComponent(components.token_freshness)}</span>
      </div>
      
      <div className="component-row" title="Orderflow Imbalance - measures buy/sell pressure imbalance">
        <span className="component-label">OI:</span>
        <div className="component-bar">
          <div 
            className="component-fill"
            style={{
              width: `${components.orderflow_imbalance * 100}%`,
              backgroundColor: getComponentColor(components.orderflow_imbalance)
            }}
          />
        </div>
        <span className="component-value">{formatComponent(components.orderflow_imbalance)}</span>
      </div>
    </div>
  )
}