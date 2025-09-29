# 🎨 Frontend Components Examples

## 🔧 Критические Обновления

### 1. Обновленные Настройки (Settings.tsx)

```typescript
// Новые предустановки с арбитражной формулой
const arbitragePresets = {
  conservative: {
    w_tx: '0.5', w_fresh: '0.3', w_vol: '0.2', w_oi: '0.0',
    arbitrage_optimal_tx_5m: '200',
    ewma_alpha: '0.6'
  },
  balanced: {
    w_tx: '0.6', w_fresh: '0.4', w_vol: '0.0', w_oi: '0.0',
    arbitrage_optimal_tx_5m: '150', 
    ewma_alpha: '0.8'
  },
  aggressive: {
    w_tx: '0.7', w_fresh: '0.3', w_vol: '0.0', w_oi: '0.0',
    arbitrage_optimal_tx_5m: '100',
    ewma_alpha: '0.9'
  }
}
```

### 2. Арбитражная Панель

```typescript
function ArbitragePanel({ tokens }) {
  const botReady = tokens.filter(t => t.score >= 0.6)
  const watchList = tokens.filter(t => t.score >= 0.4 && t.score < 0.6)
  
  return (
    <div className="arbitrage-panel">
      <h3>🤖 Арбитражная Готовность</h3>
      <div className="arb-stats">
        <div className="stat-card bot-ready">
          <span className="count">{botReady.length}</span>
          <span className="label">Готовы для бота</span>
        </div>
        <div className="stat-card watch-list">
          <span className="count">{watchList.length}</span>
          <span className="label">Список наблюдения</span>
        </div>
      </div>
    </div>
  )
}
```

### 3. Улучшенная Визуализация Скоров

```typescript
function EnhancedScoreCell({ token, score, components }) {
  const isArbitrageReady = score >= 0.6
  const txActivity = components?.tx_accel || 0
  const freshness = components?.token_freshness || 0
  
  return (
    <div className={`score-cell ${isArbitrageReady ? 'arb-ready' : ''}`}>
      <div className="score-main">
        <span className="score-value">{score.toFixed(3)}</span>
        {isArbitrageReady && <span className="bot-indicator">🤖</span>}
      </div>
      
      <div className="components-mini">
        <div className="component-bar">
          <div 
            className="tx-fill" 
            style={{ width: `${txActivity * 60}%` }}
            title={`TX: ${txActivity.toFixed(3)} (60% веса)`}
          />
          <div 
            className="fresh-fill" 
            style={{ width: `${freshness * 40}%` }}
            title={`Fresh: ${freshness.toFixed(3)} (40% веса)`}
          />
        </div>
      </div>
    </div>
  )
}
```

## 🎨 CSS Стили

```css
.arb-ready {
  background: linear-gradient(135deg, #10b981, #059669);
  color: white;
  border-radius: 8px;
  padding: 4px 8px;
}

.bot-indicator {
  font-size: 12px;
  margin-left: 4px;
}

.component-bar {
  display: flex;
  height: 4px;
  background: #e5e7eb;
  border-radius: 2px;
  overflow: hidden;
}

.tx-fill {
  background: #3b82f6;
}

.fresh-fill {
  background: #10b981;
}
```