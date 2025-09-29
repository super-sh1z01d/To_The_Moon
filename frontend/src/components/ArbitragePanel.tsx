import { useMemo } from 'react'
import { TokenItem } from '../lib/api'

interface ArbitragePanelProps {
  tokens: TokenItem[]
  notarbMinScore?: number
}

function getTokenAge(createdAt?: string): number {
  if (!createdAt) return 999
  const now = new Date()
  const created = new Date(createdAt)
  return Math.round((now.getTime() - created.getTime()) / (1000 * 60 * 60))
}

function formatTime(timestamp: number): string {
  return new Date(timestamp).toLocaleTimeString('ru-RU', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

export default function ArbitragePanel({ tokens, notarbMinScore = 0.5 }: ArbitragePanelProps) {
  // Мемоизация для производительности
  const stats = useMemo(() => {
    const watchThreshold = Math.max(0.4, notarbMinScore - 0.1) // Наблюдение на 0.1 ниже порога бота
    
    return {
      botReady: tokens.filter(t => (t.score || 0) >= notarbMinScore).length,
      watchList: tokens.filter(t => {
        const score = t.score || 0
        return score >= watchThreshold && score < notarbMinScore
      }).length,
      highActivity: tokens.filter(t => (t.n_5m || 0) >= 150).length,
      freshTokens: tokens.filter(t => getTokenAge(t.created_at) <= 6).length,
      totalActive: tokens.length,
      // Для отображения порогов
      botThreshold: notarbMinScore,
      watchThreshold: watchThreshold
    }
  }, [tokens, notarbMinScore])
  
  return (
    <div className="arbitrage-panel">
      {/* Компактный заголовок */}
      <div className="panel-header">
        <h3>🤖 Арбитражная Готовность</h3>
        <div className="update-time">
          {formatTime(Date.now())}
        </div>
      </div>

      {/* Адаптивная сетка статистики */}
      <div className="stats-grid">
        <div className="stat-card bot-ready">
          <div className="stat-icon">🔥</div>
          <div className="stat-content">
            <div className="stat-number">{stats.botReady}</div>
            <div className="stat-label">Готовы для бота</div>
            <div className="stat-detail">≥ {stats.botThreshold}</div>
          </div>
        </div>
        
        <div className="stat-card watch-list">
          <div className="stat-icon">👁️</div>
          <div className="stat-content">
            <div className="stat-number">{stats.watchList}</div>
            <div className="stat-label">Наблюдение</div>
            <div className="stat-detail">{stats.watchThreshold} - {stats.botThreshold}</div>
          </div>
        </div>
        
        <div className="stat-card high-activity">
          <div className="stat-icon">⚡</div>
          <div className="stat-content">
            <div className="stat-number">{stats.highActivity}</div>
            <div className="stat-label">Высокая активность</div>
            <div className="stat-detail">150+ TX/5м</div>
          </div>
        </div>
        
        <div className="stat-card fresh-tokens">
          <div className="stat-icon">🆕</div>
          <div className="stat-content">
            <div className="stat-number">{stats.freshTokens}</div>
            <div className="stat-label">Свежие</div>
            <div className="stat-detail">&lt; 6 часов</div>
          </div>
        </div>
      </div>

      {/* Прогресс-индикатор общей готовности */}
      <div className="readiness-indicator">
        <div className="readiness-bar">
          <div 
            className="readiness-fill"
            style={{ 
              width: `${(stats.botReady / Math.max(stats.totalActive, 1)) * 100}%` 
            }}
          />
        </div>
        <div className="readiness-text">
          {((stats.botReady / Math.max(stats.totalActive, 1)) * 100).toFixed(1)}% готовы к арбитражу
        </div>
      </div>
    </div>
  )
}