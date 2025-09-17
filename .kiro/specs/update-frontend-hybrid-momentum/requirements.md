# Requirements Document

## Introduction

Update the frontend settings page to support the new Hybrid Momentum scoring model. The current frontend shows legacy scoring settings (weight_s, weight_l, weight_m, weight_t) but the backend now uses Hybrid Momentum model with new weights (w_tx, w_vol, w_fresh, w_oi).

## Requirements

### Requirement 1

**User Story:** As a system administrator, I want to see and configure Hybrid Momentum model settings in the web interface, so that I can manage the new scoring system.

#### Acceptance Criteria

1. WHEN I open the settings page THEN I SHALL see Hybrid Momentum weights (w_tx, w_vol, w_fresh, w_oi)
2. WHEN I view the scoring formula THEN it SHALL display the Hybrid Momentum formula instead of legacy formula
3. WHEN I change weight values THEN they SHALL be saved to the correct Hybrid Momentum settings

### Requirement 2

**User Story:** As a user, I want to switch between scoring models (legacy/hybrid_momentum), so that I can choose the appropriate scoring algorithm.

#### Acceptance Criteria

1. WHEN I access settings THEN I SHALL see a model selector dropdown
2. WHEN I select "hybrid_momentum" THEN the interface SHALL show Hybrid Momentum weights
3. WHEN I select "legacy" THEN the interface SHALL show legacy weights
4. WHEN I switch models THEN the active model SHALL be updated via API

### Requirement 3

**User Story:** As a user, I want to see the correct scoring formula and parameter descriptions, so that I understand how the scoring works.

#### Acceptance Criteria

1. WHEN viewing Hybrid Momentum settings THEN I SHALL see descriptions for Transaction Acceleration, Volume Momentum, Token Freshness, and Orderflow Imbalance
2. WHEN viewing the formula THEN it SHALL show the correct Hybrid Momentum calculation
3. WHEN hovering over parameters THEN I SHALL see helpful tooltips explaining each component