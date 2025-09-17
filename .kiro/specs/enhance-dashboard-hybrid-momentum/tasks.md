# Implementation Plan

- [x] 1. Update API types and interfaces
  - Add raw_components and smoothed_components to TokenItem interface
  - Add scoring_model field to TokenItem interface
  - Create ComponentBreakdown interface for component data
  - _Requirements: 1.1, 1.2_

- [x] 2. Create score visualization components
  - Create ScoreCell component with progress bar and color coding
  - Implement getScoreColor() and getScoreClass() utility functions
  - Add hover tooltip showing component breakdown for Hybrid Momentum
  - _Requirements: 2.1, 5.1, 5.2_

- [x] 3. Create component display functionality
  - Create ComponentsCell component for displaying TX/Vol/Fresh/OI values
  - Implement compact component display format
  - Add tooltips explaining each component metric
  - _Requirements: 1.1, 1.3, 5.3_

- [x] 4. Implement age display and freshness indicators
  - Create AgeCell component with human-readable age formatting
  - Add freshness indicator (🆕) for tokens within threshold
  - Implement formatAge() utility function
  - _Requirements: 2.2, 4.3_

- [x] 5. Add filtering and sorting capabilities
  - Add "Fresh Only" filter checkbox to filter bar
  - Implement sorting by component values (TX Accel, Vol Momentum, etc.)
  - Add compact mode toggle to filter bar
  - _Requirements: 3.1, 3.2, 3.3, 4.2_

- [x] 6. Simplify calculation time display
  - Update renderCalc function to show only score calculation time
  - Format time as "YYYY-MM-DD HH:MM" format
  - Remove DEX fetch time from display
  - _Requirements: 4.1_

- [x] 7. Implement model detection and conditional rendering
  - Fetch active scoring model from API
  - Show component columns only for Hybrid Momentum model
  - Maintain backward compatibility with Legacy model display
  - _Requirements: 1.1, 1.2_

- [x] 8. Add CSS styling for new visual elements
  - Style score progress bars with color coding
  - Style component display with compact formatting
  - Add freshness indicator styling
  - Style compact mode layout
  - _Requirements: 2.1, 2.2, 4.2_

- [x] 9. Update table headers and column management
  - Add sortable headers for new component columns
  - Update existing score header with enhanced sorting
  - Implement conditional column display based on scoring model
  - _Requirements: 3.2, 5.1_

- [x] 10. Test and validate all enhancements
  - Test with both Hybrid Momentum and Legacy models
  - Verify component breakdown display accuracy
  - Test filtering and sorting functionality
  - Validate visual indicators and color coding
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3_