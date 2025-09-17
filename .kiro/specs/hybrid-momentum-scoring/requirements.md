# Requirements Document

## Introduction

This specification defines the implementation of a new "Hybrid Momentum" scoring model for the To The Moon token scoring system. The new model replaces the current simple scoring algorithm with a sophisticated multi-component formula that better captures short-term arbitrage potential through transaction acceleration, volume momentum, holder growth, and orderflow imbalance analysis.

## Requirements

### Requirement 1: New Scoring Model Implementation

**User Story:** As a crypto trader, I want the system to use a more sophisticated scoring algorithm that captures transaction acceleration, volume momentum, token freshness, and orderflow imbalance, so that I can identify tokens with better short-term arbitrage potential.

#### Acceptance Criteria

1. WHEN the system calculates a token score THEN it SHALL use the formula: Score = (W_tx * Tx_Accel) + (W_vol * Vol_Momentum) + (W_fresh * Token_Freshness) + (W_oi * Orderflow_Imbalance)
2. WHEN calculating Tx_Accel THEN the system SHALL use the formula: (tx_count_5m / 5) / (tx_count_1h / 60)
3. WHEN calculating Vol_Momentum THEN the system SHALL use the formula: volume_5m / (volume_1h / 12)
4. WHEN calculating Token_Freshness THEN the system SHALL use the formula: max(0, (6 - hours_since_migration) / 6) where hours_since_migration is time since token was first added to system
5. WHEN calculating Orderflow_Imbalance THEN the system SHALL use the formula: (buys_volume_5m - sells_volume_5m) / (buys_volume_5m + sells_volume_5m) using estimated volumes based on transaction ratios
6. WHEN any component calculation results in division by zero THEN the system SHALL handle it gracefully by setting that component to 0
7. WHEN calculating Token_Freshness for tokens older than 6 hours THEN the system SHALL return 0
8. WHEN calculating Token_Freshness for tokens newer than 6 hours THEN the system SHALL return a value between 0 and 1 representing freshness

### Requirement 2: EWMA Smoothing Implementation

**User Story:** As a system administrator, I want all scoring components and the final score to be smoothed using EWMA (Exponential Weighted Moving Average), so that the scoring system produces stable results without excessive volatility.

#### Acceptance Criteria

1. WHEN calculating any scoring component (Tx_Accel, Vol_Momentum, Token_Freshness, Orderflow_Imbalance) THEN the system SHALL apply EWMA smoothing
2. WHEN calculating the final Score THEN the system SHALL apply EWMA smoothing to the result
3. WHEN applying EWMA smoothing THEN the system SHALL use a configurable alpha parameter
4. WHEN no previous EWMA value exists THEN the system SHALL initialize with the current raw value
5. WHEN applying EWMA THEN the system SHALL use the formula: EWMA_new = alpha * current_value + (1 - alpha) * EWMA_previous

### Requirement 3: Enhanced Data Collection

**User Story:** As the scoring system, I need access to detailed transaction and volume data over multiple time periods, so that I can calculate the new scoring components accurately.

#### Acceptance Criteria

1. WHEN collecting token metrics THEN the system SHALL gather tx_count_5m (transaction count in last 5 minutes from DexScreener txns.m5)
2. WHEN collecting token metrics THEN the system SHALL gather tx_count_1h (transaction count in last 1 hour from DexScreener txns.h1)
3. WHEN collecting token metrics THEN the system SHALL gather volume_5m (trading volume in last 5 minutes from DexScreener volume.m5)
4. WHEN collecting token metrics THEN the system SHALL gather volume_1h (trading volume in last 1 hour from DexScreener volume.h1)
5. WHEN collecting token metrics THEN the system SHALL calculate token_created_at from existing database records
6. WHEN collecting token metrics THEN the system SHALL calculate buys_volume_5m and sells_volume_5m using transaction ratios from DexScreener
8. WHEN historical data is not available THEN the system SHALL handle gracefully by using available data or default values
9. WHEN DexScreener API is unavailable THEN the system SHALL continue with cached data and log the issue

### Requirement 4: Configurable Scoring Parameters

**User Story:** As a system administrator, I want to configure the weights and parameters of the scoring model through the admin interface, so that I can tune the model performance without code changes.

#### Acceptance Criteria

1. WHEN accessing admin settings THEN the system SHALL provide configuration for W_tx (transaction acceleration weight)
2. WHEN accessing admin settings THEN the system SHALL provide configuration for W_vol (volume momentum weight)
3. WHEN accessing admin settings THEN the system SHALL provide configuration for W_fresh (token freshness weight)
4. WHEN accessing admin settings THEN the system SHALL provide configuration for W_oi (orderflow imbalance weight)
5. WHEN accessing admin settings THEN the system SHALL provide configuration for freshness_threshold_hours (default 6 hours)
5. WHEN accessing admin settings THEN the system SHALL provide configuration for EWMA alpha parameter
6. WHEN weight parameters are updated THEN the system SHALL apply them to subsequent score calculations
7. WHEN invalid weight values are provided THEN the system SHALL validate and reject them with appropriate error messages

### Requirement 5: Score Component Visibility

**User Story:** As a crypto trader, I want to see the breakdown of how each component contributes to the final token score, so that I can understand why a token received a particular score.

#### Acceptance Criteria

1. WHEN viewing token details THEN the system SHALL display the raw values for each scoring component
2. WHEN viewing token details THEN the system SHALL display the EWMA-smoothed values for each scoring component
3. WHEN viewing token details THEN the system SHALL display the weighted contribution of each component to the final score
4. WHEN viewing the token list THEN the system SHALL optionally show key component values in the table
5. WHEN exporting token data via API THEN the system SHALL include component breakdown in the response

### Requirement 6: Backward Compatibility and Migration

**User Story:** As a system operator, I want the new scoring model to be implemented without breaking existing functionality, so that the system continues to operate during the transition.

#### Acceptance Criteria

1. WHEN the new scoring model is deployed THEN existing token records SHALL remain accessible
2. WHEN the new scoring model is activated THEN the system SHALL continue to serve API requests without interruption
3. WHEN historical scores exist THEN the system SHALL preserve them for comparison purposes
4. WHEN the new model is enabled THEN the system SHALL clearly indicate which scoring model is active
5. WHEN migrating to the new model THEN the system SHALL handle missing historical data gracefully

### Requirement 7: Performance and Reliability

**User Story:** As a system operator, I want the new scoring calculations to perform efficiently and reliably, so that the system can handle the current token load without degradation.

#### Acceptance Criteria

1. WHEN calculating scores for active tokens THEN the system SHALL complete calculations within the existing time constraints
2. WHEN external API calls fail THEN the system SHALL handle errors gracefully and continue with available data
3. WHEN calculating components with missing data THEN the system SHALL use appropriate fallback values
4. WHEN the system encounters calculation errors THEN it SHALL log detailed error information for debugging
5. WHEN processing large numbers of tokens THEN the system SHALL maintain acceptable response times for API requests