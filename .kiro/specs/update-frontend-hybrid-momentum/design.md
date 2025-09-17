# Design Document

## Overview

Update the React frontend Settings page to support the new Hybrid Momentum scoring model. The current frontend is hardcoded for legacy scoring with weights (weight_s, weight_l, weight_m, weight_t) but needs to support both legacy and hybrid momentum models dynamically.

## Architecture

### Model Detection
- Fetch active scoring model from API endpoint `/settings/scoring_model_active`
- Dynamically render appropriate settings based on active model
- Support switching between models via dropdown

### Settings Structure
```typescript
// Legacy Model Settings
const legacyKeys = ['weight_s', 'weight_l', 'weight_m', 'weight_t', ...]

// Hybrid Momentum Model Settings  
const hybridKeys = ['w_tx', 'w_vol', 'w_fresh', 'w_oi', 'ewma_alpha', 'freshness_threshold_hours', ...]
```

## Components and Interfaces

### Updated Settings Component
```typescript
interface SettingsState {
  activeModel: 'legacy' | 'hybrid_momentum'
  vals: SettingsMap
  loading: boolean
  saving: boolean
}
```

### Model Selector Component
```typescript
interface ModelSelectorProps {
  activeModel: string
  onModelChange: (model: string) => void
  disabled: boolean
}
```

### Dynamic Weight Fields
- **Legacy**: weight_s, weight_l, weight_m, weight_t
- **Hybrid Momentum**: w_tx, w_vol, w_fresh, w_oi

## Data Models

### Hybrid Momentum Settings
```typescript
interface HybridMomentumSettings {
  w_tx: string          // Transaction Acceleration weight
  w_vol: string         // Volume Momentum weight  
  w_fresh: string       // Token Freshness weight
  w_oi: string          // Orderflow Imbalance weight
  ewma_alpha: string    // EWMA smoothing factor
  freshness_threshold_hours: string
}
```

### API Endpoints
- `GET /settings/scoring_model_active` - Get active model
- `PUT /settings/scoring_model_active` - Switch model
- `GET /settings/w_tx`, `GET /settings/w_vol`, etc. - Get hybrid weights

## Error Handling

### Model Switch Validation
- Validate model exists before switching
- Show error message if switch fails
- Revert UI state on failure

### Settings Validation
- Validate weight sum equals 1.0 for both models
- Show warnings for invalid ranges
- Prevent saving invalid configurations

## Testing Strategy

### Component Tests
- Test model switching functionality
- Test dynamic field rendering
- Test weight sum validation

### Integration Tests
- Test API integration for model switching
- Test settings save/load for both models
- Test error handling scenarios

## Implementation Details

### Formula Display
- **Legacy Formula**: Current HD_norm formula
- **Hybrid Momentum Formula**: New 4-component formula with EWMA

### Weight Descriptions
- **w_tx**: Transaction Acceleration - measures transaction velocity changes
- **w_vol**: Volume Momentum - tracks volume trend acceleration  
- **w_fresh**: Token Freshness - rewards recently created tokens
- **w_oi**: Orderflow Imbalance - measures buy/sell pressure imbalance

### UI/UX Considerations
- Smooth transitions between model views
- Clear labeling of model-specific parameters
- Helpful tooltips explaining new concepts
- Visual indicators for active model