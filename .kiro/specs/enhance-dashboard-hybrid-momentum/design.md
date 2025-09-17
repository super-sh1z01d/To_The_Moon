# Design Document

## Overview

Enhance the Dashboard component to provide rich visualization and interaction capabilities for the Hybrid Momentum scoring model. The design focuses on displaying component breakdowns, visual indicators, improved filtering, and better UX without mobile adaptations.

## Architecture

### Component Structure
```
Dashboard
├── TokenTable
│   ├── TokenRow
│   │   ├── ScoreCell (with progress bar and breakdown)
│   │   ├── ComponentsCell (TX/Vol/Fresh/OI display)
│   │   ├── AgeCell (human-readable age with freshness indicator)
│   │   └── existing cells...
│   └── TableHeader (with new sortable columns)
├── FilterBar (enhanced with age filter and compact mode)
└── existing components...
```

### Data Flow
- Fetch active scoring model to determine display mode
- For Hybrid Momentum: show component breakdown
- For Legacy: show traditional metrics
- Add client-side calculations for age, trends, etc.

## Components and Interfaces

### Enhanced TokenItem Interface
```typescript
interface TokenItem {
  // Existing fields...
  raw_components?: {
    tx_accel: number
    vol_momentum: number  
    token_freshness: number
    orderflow_imbalance: number
  }
  smoothed_components?: {
    tx_accel: number
    vol_momentum: number
    token_freshness: number
    orderflow_imbalance: number
  }
  scoring_model?: string
  created_at?: string
}
```

### New Component Props
```typescript
interface ScoreCellProps {
  score: number
  components?: ComponentBreakdown
  model: string
}

interface ComponentsCellProps {
  components: ComponentBreakdown
  compact?: boolean
}

interface AgeCellProps {
  createdAt: string
  freshnessThreshold: number
}
```

## Data Models

### Component Breakdown Display
```typescript
interface ComponentBreakdown {
  tx_accel: number      // 0.0-1.0
  vol_momentum: number  // 0.0-1.0
  token_freshness: number // 0.0-1.0
  orderflow_imbalance: number // 0.0-1.0
}
```

### Filter State
```typescript
interface FilterState {
  // Existing filters...
  freshOnly: boolean
  compactMode: boolean
  sortBy: 'score' | 'tx_accel' | 'vol_momentum' | 'token_freshness' | 'orderflow_imbalance'
}
```

## Visual Design

### Color Scheme
- **High Score (>0.5)**: `#22c55e` (green)
- **Medium Score (0.3-0.5)**: `#eab308` (yellow)  
- **Low Score (<0.3)**: `#ef4444` (red)
- **Fresh Token**: `#3b82f6` (blue accent)
- **Component bars**: Gradient from light to dark based on value

### Score Display
```
[████████░░] 0.8234
```
- Progress bar showing score strength
- Hover shows component breakdown

### Component Display (Compact)
```
TX:0.85 Vol:0.72 Fresh:1.0 OI:0.43
```
- Abbreviated labels with values
- Color-coded based on strength

### Age Display
```
2.3h 🆕  (for fresh tokens)
1.2d     (for older tokens)
```

## Error Handling

### Missing Data
- Show "—" for missing components
- Graceful fallback to legacy display
- Handle API errors without breaking table

### Model Detection
- Auto-detect scoring model from API
- Fallback to legacy if model unknown
- Show appropriate columns based on model

## Testing Strategy

### Component Tests
- Test score color coding
- Test component breakdown display
- Test age calculation and formatting
- Test filter and sort functionality

### Integration Tests
- Test with both scoring models
- Test API integration for components
- Test performance with large token lists

## Implementation Details

### Score Progress Bar
```tsx
<div className="score-container">
  <div className="score-bar">
    <div 
      className="score-fill" 
      style={{width: `${score * 100}%`, backgroundColor: getScoreColor(score)}}
    />
  </div>
  <span className={`score-value ${getScoreClass(score)}`}>
    {score.toFixed(4)}
  </span>
</div>
```

### Component Breakdown Tooltip
```tsx
<div className="component-breakdown">
  <div>TX Acceleration: {components.tx_accel.toFixed(3)}</div>
  <div>Volume Momentum: {components.vol_momentum.toFixed(3)}</div>
  <div>Token Freshness: {components.token_freshness.toFixed(3)}</div>
  <div>Orderflow Imbalance: {components.orderflow_imbalance.toFixed(3)}</div>
</div>
```

### Age Calculation
```typescript
function formatAge(createdAt: string): string {
  const now = new Date()
  const created = new Date(createdAt)
  const diffMs = now.getTime() - created.getTime()
  const diffHours = diffMs / (1000 * 60 * 60)
  
  if (diffHours < 1) return `${Math.round(diffMs / (1000 * 60))}m`
  if (diffHours < 24) return `${diffHours.toFixed(1)}h`
  return `${(diffHours / 24).toFixed(1)}d`
}
```

### Simplified Calculation Time Display
```typescript
function renderCalcTime(scoredAt?: string): string {
  if (!scoredAt) return '—'
  try {
    const date = new Date(scoredAt)
    return date.toLocaleString('sv-SE', {
      year: 'numeric',
      month: '2-digit', 
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    }).replace('T', ' ')
  } catch {
    return '—'
  }
}
```

## Performance Considerations

### Rendering Optimization
- Memoize component calculations
- Virtualize table for large datasets
- Debounce filter changes

### Data Fetching
- Cache component data
- Batch API requests
- Implement incremental updates