# Changelog

## [2.0.0] - 2025-09-17

### 🧹 Code Cleanup

#### Parameter Removal
- **REMOVED**: `max_price_change_5m` parameter from Hybrid Momentum model
- **REASON**: Parameter not used in new scoring components (TX Accel, Vol Momentum, etc.)
- **IMPACT**: Simplified settings UI, cleaner code, no functional changes
- **LEGACY**: Parameter still used in legacy scoring model for backward compatibility

### 🎯 Major Features

#### Hybrid Momentum Scoring Model
- **NEW**: Advanced 4-component scoring model for better arbitrage potential assessment
- **Components**: Transaction Acceleration, Volume Momentum, Token Freshness, Orderflow Imbalance
- **EWMA Smoothing**: Exponential weighted moving average for all components to reduce volatility
- **Configurable Weights**: API-based configuration of component weights
- **Multiple Models**: Support for both Legacy and Hybrid Momentum models with runtime switching

#### Enhanced Dashboard
- **Adaptive UI**: Table automatically adapts based on active scoring model
- **Component Visualization**: Individual component display with sorting capabilities
- **Advanced Filtering**: "Fresh Only" filter for tokens < 6 hours old
- **Visual Indicators**: Color-coded scores, progress bars, freshness indicators (🆕)
- **Compact Mode**: Toggle for compact component display
- **Smart Sorting**: Sort by any component (TX, Vol, Fresh, OI) or overall score

### 🔧 Technical Improvements

#### API Enhancements
- **NEW Fields**: `raw_components`, `smoothed_components`, `scoring_model`, `created_at`
- **Component Breakdown**: Detailed component data in API responses
- **Model Detection**: Automatic active model detection and conditional rendering
- **Enhanced Validation**: Comprehensive settings validation with error reporting

#### Frontend Improvements
- **React Components**: ScoreCell, ComponentsCell, AgeCell for modular UI
- **Utility Functions**: Scoring utilities for formatting, color coding, age calculation
- **State Management**: Persistent user preferences in localStorage
- **Performance**: Optimized rendering and reduced DOM complexity

#### Database Schema
- **New Fields**: Added `raw_components`, `smoothed_components`, `scoring_model` to `token_scores`
- **Migration Support**: Seamless migration from legacy to new schema
- **Backward Compatibility**: Full support for existing data

### 🎨 UI/UX Improvements

#### Table Optimization
- **Removed Columns**: Eliminated redundant "Δ 5м / 15м" and "Транз. 5м" columns
- **Focused Layout**: Streamlined table for better readability
- **Responsive Design**: Better mobile and desktop experience
- **Interactive Headers**: Clickable headers with sort indicators

#### Visual Enhancements
- **Color Coding**: Green/Yellow/Red score indicators
- **Progress Bars**: Visual score representation
- **Freshness Badges**: 🆕 indicator for new tokens
- **Component Tooltips**: Detailed explanations for each component

### 🧪 Testing & Quality

#### Comprehensive Test Suite
- **27 Unit Tests**: Full coverage of ComponentCalculator and EWMAService
- **Integration Tests**: API endpoints and database operations
- **Test Data**: Realistic test scenarios with component data
- **Error Handling**: Graceful handling of edge cases and invalid data

#### Development Tools
- **Test Scripts**: Utilities for creating test data and validating functionality
- **Documentation**: Comprehensive guides and API documentation
- **Deployment**: Updated deployment scripts and configuration

### 📊 Performance & Reliability

#### Optimizations
- **Efficient Calculations**: Optimized component calculation algorithms
- **Memory Usage**: Reduced memory footprint through better data structures
- **API Performance**: Faster response times with optimized queries
- **Frontend Performance**: Reduced bundle size and improved rendering

#### Stability Improvements
- **Error Handling**: Robust error handling throughout the application
- **Data Validation**: Comprehensive input validation and sanitization
- **Graceful Degradation**: Fallback behavior for missing or invalid data
- **Monitoring**: Enhanced logging and debugging capabilities

### 🔄 Migration Guide

#### From Legacy to Hybrid Momentum
1. **Automatic Migration**: Database schema updates applied automatically
2. **Settings Migration**: Legacy settings preserved and mapped to new structure
3. **API Compatibility**: All existing API endpoints remain functional
4. **UI Adaptation**: Interface automatically adapts to active scoring model

#### Configuration Updates
- **New Settings**: Added Hybrid Momentum specific configuration options
- **Weight Configuration**: Configurable component weights via API
- **EWMA Parameters**: Adjustable smoothing parameters
- **Freshness Threshold**: Configurable token freshness detection

### 📈 Business Impact

#### Improved Analytics
- **Better Insights**: 4 detailed components vs single score
- **Early Detection**: Fresh token filtering for opportunity discovery
- **Flexible Analysis**: Sort and filter by any component
- **Visual Clarity**: Immediate understanding through color coding

#### User Experience
- **Faster Decisions**: Visual indicators enable quick assessment
- **Customizable Views**: User preferences and filtering options
- **Professional Interface**: Modern, clean design
- **Responsive Design**: Works well on all devices

### 🚀 Deployment

#### Production Ready
- **Zero Downtime**: Seamless deployment with backward compatibility
- **Configuration**: Environment-based configuration management
- **Monitoring**: Enhanced logging and health checks
- **Scalability**: Optimized for production workloads

#### Documentation
- **Updated README**: Comprehensive setup and usage instructions
- **API Documentation**: Complete API reference with examples
- **Deployment Guides**: Step-by-step deployment instructions
- **Troubleshooting**: Common issues and solutions

---

## [1.x.x] - Previous Versions

### Legacy Features
- Basic scoring model with 4 components (l, s, m, t)
- Simple dashboard with basic filtering
- PostgreSQL/SQLite support
- WebSocket integration with Pump.fun
- DexScreener API integration
- Basic API endpoints

---

## Migration Notes

### Breaking Changes
- None - Full backward compatibility maintained

### Deprecated Features
- Legacy scoring model (still supported but not recommended for new deployments)

### New Dependencies
- No new external dependencies added
- All changes use existing technology stack

### Configuration Changes
- New optional settings for Hybrid Momentum model
- Existing settings remain unchanged and functional