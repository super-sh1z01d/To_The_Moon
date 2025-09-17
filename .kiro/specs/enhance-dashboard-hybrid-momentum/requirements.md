# Requirements Document

## Introduction

Enhance the token dashboard to fully support and visualize the Hybrid Momentum scoring model. The current dashboard is designed for the legacy model and needs to display the new 4-component scoring system with better visual indicators and user experience improvements.

## Requirements

### Requirement 1

**User Story:** As a trader, I want to see the breakdown of Hybrid Momentum components for each token, so that I can understand what drives the score.

#### Acceptance Criteria

1. WHEN viewing tokens THEN I SHALL see TX Acceleration, Volume Momentum, Token Freshness, and Orderflow Imbalance values
2. WHEN a token uses Hybrid Momentum model THEN component values SHALL be displayed with appropriate formatting
3. WHEN hovering over components THEN I SHALL see tooltips explaining each metric

### Requirement 2

**User Story:** As a user, I want visual indicators for token scores and freshness, so that I can quickly identify promising tokens.

#### Acceptance Criteria

1. WHEN viewing token scores THEN they SHALL be color-coded (green > 0.5, yellow 0.3-0.5, red < 0.3)
2. WHEN viewing token age THEN fresh tokens SHALL be highlighted with special indicators
3. WHEN scores change THEN trend arrows SHALL show if score is increasing or decreasing

### Requirement 3

**User Story:** As a trader, I want to filter and sort tokens by Hybrid Momentum components, so that I can find tokens with specific characteristics.

#### Acceptance Criteria

1. WHEN using filters THEN I SHALL be able to filter by token age (fresh tokens only)
2. WHEN sorting THEN I SHALL be able to sort by TX Acceleration, Volume Momentum, Token Freshness, and Orderflow Imbalance
3. WHEN filtering by freshness THEN only tokens within freshness threshold SHALL be shown

### Requirement 4

**User Story:** As a user, I want improved time display and compact viewing options, so that I can efficiently scan many tokens.

#### Acceptance Criteria

1. WHEN viewing calculation time THEN it SHALL show only score calculation date in "YYYY-MM-DD HH:MM" format
2. WHEN using compact mode THEN token display SHALL be more dense with essential information only
3. WHEN viewing token age THEN it SHALL be displayed in human-readable format (e.g., "2.3h", "45m")

### Requirement 5

**User Story:** As a user, I want to see score breakdowns and progress indicators, so that I can understand token performance at a glance.

#### Acceptance Criteria

1. WHEN viewing scores THEN they SHALL be displayed with progress bars showing relative strength
2. WHEN hovering over scores THEN I SHALL see component breakdown showing contribution of each factor
3. WHEN components are available THEN they SHALL be displayed in a compact, readable format