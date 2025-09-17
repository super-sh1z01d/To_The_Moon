# Implementation Plan

- [x] 1. Add model detection and state management
  - Add activeModel state to Settings component
  - Fetch scoring_model_active from API on component mount
  - Create model switching functionality
  - _Requirements: 2.1, 2.4_

- [x] 2. Create dynamic settings keys configuration
  - Define legacyKeys array with existing weight keys
  - Define hybridKeys array with new Hybrid Momentum keys
  - Create getSettingsKeys() function that returns appropriate keys based on model
  - _Requirements: 1.1, 2.2_

- [x] 3. Implement model selector component
  - Create ModelSelector component with dropdown
  - Add model switching API call functionality
  - Handle model switch success/error states
  - _Requirements: 2.1, 2.2, 2.4_

- [x] 4. Update weight fields rendering
  - Modify weight section to render fields based on active model
  - Add proper labels and hints for Hybrid Momentum weights
  - Update WeightsSum component to work with both models
  - _Requirements: 1.1, 1.3_

- [x] 5. Create Hybrid Momentum formula component
  - Create HybridMomentumFormula component
  - Add proper formula display with 4-component calculation
  - Include component descriptions and explanations
  - _Requirements: 3.1, 3.2_

- [x] 6. Update formula display logic
  - Modify Formula component to conditionally render based on model
  - Show legacy formula for legacy model
  - Show hybrid momentum formula for hybrid momentum model
  - _Requirements: 1.2, 3.1_

- [x] 7. Add hybrid momentum specific sections
  - Add EWMA configuration section for hybrid model
  - Add freshness threshold configuration
  - Include helpful descriptions and tooltips
  - _Requirements: 3.2, 3.3_

- [x] 8. Update API integration
  - Modify save function to handle both model types
  - Add model switching API calls
  - Update settings loading to fetch appropriate keys
  - _Requirements: 1.3, 2.3_

- [x] 9. Test and validate implementation
  - Test model switching functionality
  - Verify weight sum validation works for both models
  - Test settings save/load for hybrid momentum
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4_