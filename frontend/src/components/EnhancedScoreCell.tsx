import { TokenItem, ComponentBreakdown } from '../lib/api'

interface EnhancedScoreCellProps {
  token: TokenItem
  score: number
  components?: ComponentBreakdown
  compact?: boolean
}

function getScoreClass(score: number): string {
  if (score >= 0.6) return 'score-bot-ready'
  if (score >= 0.4) return 'score-watch-list'
  if (score >= 0.2) return 'score-low'
  return 'score-very-low'
}

function getTokenAge(createdAt?: string): number {
  if (!createdAt) return 999
  const now = new Date()
  const created = new Date(createdAt)
  return Math.round((now.getTime() - created.getTime()) / (1000 * 60 * 60))
}

export default function EnhancedScoreCell({ 
  token, 
  score, 
  components, 
  compact = false 
}: EnhancedScoreCellProps) {
  
  const isArbitrageReady = score >= 0.6
  const isWatchList = score >= 0.4 && score < 0.6
  
  // Все компоненты с их весами (по умолчанию 0.25 каждый)
  const txAccel = components?.tx_accel || 0
  const volMomentum = components?.vol_momentum || 0
  const tokenFreshness = components?.token_freshness || 0
  const orderflowImbalance = components?.orderflow_imbalance || 0
  
  // Веса компонентов (захардкожены для стабильности отображения)
  const weights = {
    tx: 0.25,
    vol: 0.25, 
    fresh: 0.25,
    oi: 0.25
  }
  
  return (
    <div className={`score-cell ${getScoreClass(score)} ${compact ? 'compact' : ''}`}>
      
      {/* Основной скор - ЧИСЛО + индикаторы */}
      <div className="score-main">
        <div className="score-number">
          {score.toFixed(3)}
        </div>
        
        <div className="score-indicators">
          {isArbitrageReady && <span className="indicator bot" title="Готов для бота">🤖</span>}
          {isWatchList && <span className="indicator watch" title="Наблюдение">👁️</span>}
          {(token.n_5m || 0) >= 150 && <span className="indicator activity" title={`${token.n_5m} TX`}>⚡</span>}
        </div>
      </div>

      {/* Визуальный прогресс-бар */}
      <div className="score-visual">
        <div className="score-bar">
          <div 
            className="score-fill"
            style={{ width: `${Math.min(score * 100, 100)}%` }}
          />
        </div>
      </div>

      {/* Компоненты (только в полном режиме) */}
      {!compact && components && (
        <div className="components-mini">
          <div className="component-row">
            <span className="comp-label">TX</span>
            <span className="comp-number">{txAccel.toFixed(2)}</span>
            <span className="comp-percent">({((txAccel * weights.tx) / score * 100).toFixed(0)}%)</span>
            <div className="comp-bar">
              <div 
                className="comp-fill tx-fill"
                style={{ width: `${txAccel * 100}%` }}
              />
            </div>
          </div>
          
          <div className="component-row">
            <span className="comp-label">VOL</span>
            <span className="comp-number">{volMomentum.toFixed(2)}</span>
            <span className="comp-percent">({((volMomentum * weights.vol) / score * 100).toFixed(0)}%)</span>
            <div className="comp-bar">
              <div 
                className="comp-fill vol-fill"
                style={{ width: `${volMomentum * 100}%` }}
              />
            </div>
          </div>
          
          <div className="component-row">
            <span className="comp-label">FR</span>
            <span className="comp-number">{tokenFreshness.toFixed(2)}</span>
            <span className="comp-percent">({((tokenFreshness * weights.fresh) / score * 100).toFixed(0)}%)</span>
            <div className="comp-bar">
              <div 
                className="comp-fill fresh-fill"
                style={{ width: `${tokenFreshness * 100}%` }}
              />
            </div>
          </div>
          
          <div className="component-row">
            <span className="comp-label">OI</span>
            <span className="comp-number">{orderflowImbalance.toFixed(2)}</span>
            <span className="comp-percent">({((Math.abs(orderflowImbalance) * weights.oi) / score * 100).toFixed(0)}%)</span>
            <div className="comp-bar">
              <div 
                className="comp-fill oi-fill"
                style={{ width: `${Math.abs(orderflowImbalance) * 100}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Hover tooltip - только важная информация */}
      <div className="score-tooltip">
        <div className="tooltip-content">
          <div className="tooltip-score">
            <strong>{score.toFixed(4)}</strong>
          </div>
          
          <div className="tooltip-breakdown">
            <div className="breakdown-row">
              <span>TX:</span>
              <span>{txAccel.toFixed(3)}</span>
              <span>({(txAccel * weights.tx).toFixed(3)})</span>
              <span>{((txAccel * weights.tx) / score * 100).toFixed(0)}%</span>
            </div>
            <div className="breakdown-row">
              <span>VOL:</span>
              <span>{volMomentum.toFixed(3)}</span>
              <span>({(volMomentum * weights.vol).toFixed(3)})</span>
              <span>{((volMomentum * weights.vol) / score * 100).toFixed(0)}%</span>
            </div>
            <div className="breakdown-row">
              <span>Fresh:</span>
              <span>{tokenFreshness.toFixed(3)}</span>
              <span>({(tokenFreshness * weights.fresh).toFixed(3)})</span>
              <span>{((tokenFreshness * weights.fresh) / score * 100).toFixed(0)}%</span>
            </div>
            <div className="breakdown-row">
              <span>OI:</span>
              <span>{orderflowImbalance.toFixed(3)}</span>
              <span>({(Math.abs(orderflowImbalance) * weights.oi).toFixed(3)})</span>
              <span>{((Math.abs(orderflowImbalance) * weights.oi) / score * 100).toFixed(0)}%</span>
            </div>
          </div>
          
          <div className="tooltip-meta">
            <span>{token.n_5m || 0} TX/5м</span>
            <span>{getTokenAge(token.created_at)}ч</span>
          </div>
        </div>
      </div>
    </div>
  )
}