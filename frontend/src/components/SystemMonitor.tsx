import { useState, useEffect } from 'react'

interface SystemConfig {
  formula: string
  txOptimum: number
  ewmaAlpha: number
  mode: string
  components: {
    tx: { active: boolean, weight: number }
    vol: { active: boolean, weight: number }
    fresh: { active: boolean, weight: number }
    oi: { active: boolean, weight: number }
  }
}

export default function SystemMonitor() {
  const [config, setConfig] = useState<SystemConfig | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  
  useEffect(() => {
    // Симуляция загрузки конфигурации
    // В реальности здесь будет API вызов
    setTimeout(() => {
      setConfig({
        formula: "Score = 0.6×TX + 0.4×FRESH",
        txOptimum: 150,
        ewmaAlpha: 0.8,
        mode: "arbitrage_activity",
        components: {
          tx: { active: true, weight: 60 },
          vol: { active: false, weight: 0 },
          fresh: { active: true, weight: 40 },
          oi: { active: false, weight: 0 }
        }
      })
      setIsLoading(false)
    }, 500)
  }, [])

  if (isLoading) {
    return <div className="monitor-skeleton" />
  }

  if (!config) return null

  return (
    <div className="system-monitor">
      {/* Компактная формула */}
      <div className="formula-card">
        <div className="formula-header">
          <span className="formula-title">Активная формула</span>
          <div className="status-dot healthy" />
        </div>
        
        <div className="formula-display">
          Score = <span className="weight-tx">0.6</span>×TX + <span className="weight-fresh">0.4</span>×FRESH
        </div>
        
        <div className="formula-meta">
          <span className="meta-item">TX оптимум: {config.txOptimum}</span>
          <span className="meta-item">EWMA α: {config.ewmaAlpha}</span>
          <span className="meta-item">Режим: {config.mode}</span>
        </div>
      </div>

      {/* Компоненты статуса */}
      <div className="components-status">
        <div className={`component-item ${config.components.tx.active ? 'active' : 'disabled'}`}>
          <div className={`component-indicator ${config.components.tx.active ? 'active' : 'disabled'}`} />
          <span className="component-name">TX Activity</span>
          <span className="component-weight">{config.components.tx.weight}%</span>
        </div>
        
        <div className={`component-item ${config.components.fresh.active ? 'active' : 'disabled'}`}>
          <div className={`component-indicator ${config.components.fresh.active ? 'active' : 'disabled'}`} />
          <span className="component-name">Freshness</span>
          <span className="component-weight">{config.components.fresh.weight}%</span>
        </div>
        
        <div className={`component-item ${config.components.vol.active ? 'active' : 'disabled'}`}>
          <div className={`component-indicator ${config.components.vol.active ? 'active' : 'disabled'}`} />
          <span className="component-name">Volume</span>
          <span className="component-weight">{config.components.vol.weight}%</span>
        </div>
        
        <div className={`component-item ${config.components.oi.active ? 'active' : 'disabled'}`}>
          <div className={`component-indicator ${config.components.oi.active ? 'active' : 'disabled'}`} />
          <span className="component-name">Orderflow</span>
          <span className="component-weight">{config.components.oi.weight}%</span>
        </div>
      </div>
    </div>
  )
}